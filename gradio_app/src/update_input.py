import os 
import re
import requests
import shutil

import gradio as gr
import numpy as np
from io import StringIO
from datetime import datetime
from pymongo import MongoClient
from .logger import LOGGER
from .settings import time_zone

TANDEM_WEBSITE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) # ./tandem_website
jobs_folder = os.path.join(TANDEM_WEBSITE_ROOT, 'tandem/jobs')
tmp_folder = os.path.join(TANDEM_WEBSITE_ROOT, 'gradio_app/tmp')
client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

VALID_AA = set("ACDEFGHIKLMNPQRSTVWY")
INF_PATTERN = re.compile(r"^(?P<acc>\S+)\s+(?P<wt>[ACDEFGHIKLMNPQRSTVWY])(?P<resid>[0-9]+)(?P<mt>[ACDEFGHIKLMNPQRSTVWY])$")
TL_PATTERN = re.compile(r"^(?P<acc>\S+)\s+(?P<wt>[ACDEFGHIKLMNPQRSTVWY])(?P<resid>[0-9]+)(?P<mt>[ACDEFGHIKLMNPQRSTVWY])\s+(?P<label>[01])$")

# --- ID patterns ---
AF_PATTERN = re.compile(r'^AF-([A-Za-z0-9]{6,10})-F\d+(?:-model_v\d+)?(?:\.(?:pdb|cif))?$', re.I)
UNIPROT_PATTERN = re.compile(r'(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})$', re.I)
PDB_PATTERN = re.compile(r'^[1-9][A-Za-z0-9]{3}$')  # classic 4-char PDB ID

# --- endpoints ---
AF_API      = "https://alphafold.ebi.ac.uk/api/prediction/"
AF_FILE_URL = "https://alphafold.ebi.ac.uk/files/AF-{uniprot}-F1-model_v{ver}.{ext}"

def upload_file(file):
    """Upload file and return message
    file is a gradio.utils.NamedString object
    """
    button_udt = gr.update(visible=True)
    button_file = gr.update(value=None, visible=False)
    if file is None:
        return button_udt, button_file

    filepath = str(file)
    if os.path.exists(filepath):
        button_udt = gr.update(visible=False)
        button_file = gr.update(value=filepath, visible=True)
        
    return button_udt, button_file

def on_clear_file():
    button_udt = gr.update(visible=True)
    button_file = gr.update(value=None, visible=False)
    return button_udt, button_file

def clean(text):
    """
    Normalize SAV text:
    - remove literal '\\n'
    - strip whitespace
    - collapse multiple spaces
    - remove empty lines
    """
    cleaned = []
    for raw in text.splitlines():
        line = raw.replace("\\n", "").strip()
        if not line:
            continue
        line = " ".join(line.split())
        cleaned.append(line)
    return "\n".join(cleaned)

def handle_SAV(mode: str, SAV_input: str):
    """
    Validate SAV input (text or file path) and load into NumPy.

    Returns
    -------
    (bool, str, np.ndarray | None)
    """

    
    data = None

    if mode not in {"Inferencing", "Transfer Learning"}:
        gr.Warning(message=f"Unknown mode: {mode}")
        return data

    if mode == "Inferencing":
        pattern = INF_PATTERN
        dtype = [("acc", "U20"), ("wt_resid_mt", "U10")]
    else:
        pattern = TL_PATTERN
        dtype = [("acc", "U20"), ("wt_resid_mt", "U10"), ("label", int)]

    # ---------- normalize input ----------
    if os.path.isfile(SAV_input):
        with open(SAV_input, "r") as f:
            raw_text = f.read()
    else:
        raw_text = SAV_input

    clean_text = clean(raw_text)
    lines = clean_text.splitlines()

    if not lines or all(not l.strip() for l in lines):
        gr.Warning("You provide no input, please provide uniprot ID and SAV.")
        return data

    # ---------- validation ----------
    for line in lines:
        line = line.strip()
        if not line:
            continue

        m = pattern.match(line)
        if not m:
            expected = (
                "<UniprotID> <WT><resid><MT>"
                if mode == "Inferencing"
                else "<UniprotID> <WT><resid><MT> <label>\n label must be 0 or 1"
            )
            message = (
                f"{line}: Wrong format\n"
                f"  Expected: {expected}"
            )
            gr.Warning(message=message)
            return data
        
        resid = int(m.group("resid"))
        if resid <= 0:
            gr.Warning(f"{line}: residue index must be positive")
            return data

        if m.group("wt") == m.group("mt"):
            gr.Warning(f"{line}: WT and mutant are identical")
            return data

        if mode == "Transfer Learning":
            if int(m.group("label")) not in (0, 1):
                gr.Warning(f"{line}: label must be 0 or 1")
                return data

    # ---------- NumPy load (ONCE) ----------
    try:
        data = np.loadtxt(
            StringIO(clean_text),
            dtype=dtype,
            comments=None,
            ndmin=1,
        )
        data = np.atleast_1d(data)
        data["acc"] = np.char.upper(data["acc"])
        data["wt_resid_mt"] = np.char.upper(data["wt_resid_mt"])
        return data
    except Exception as e:
        gr.Warning(message=f"NumPy parsing failed: {e}")
        return data

def handle_STR(_str_txt: str):
    """
    Validate input structure ID:
    - AlphaFold (AF-<UniProt>-F1 or UniProt)
    - PDB ID (4-character)

    Returns
    -------
    (str, bool)
    """

    s = _str_txt.strip()

    # ---------- AlphaFold / UniProt ----------
    match_af = AF_PATTERN.fullmatch(s)
    match_uni = UNIPROT_PATTERN.fullmatch(s)

    uniprot = None
    if match_af:
        uniprot = match_af.group(1).upper()
    elif match_uni:
        uniprot = s.upper()

    # ---------- uniprot/AlphaFold2 ----------
    if uniprot:
        # 1) API check
        try:
            r = requests.get(f"{AF_API}{uniprot}", timeout=10)
            if r.ok:
                try:
                    out = r.json()
                    if isinstance(out, list) and len(out) > 0:
                        LOGGER.info(f"✅ Valid AlphaFold UniProt ID: {uniprot}")
                        return uniprot
                except ValueError:
                    pass
        except requests.RequestException:
            pass

        # 2) File server HEAD check (fallback)
        for ver in (4, 3, 2, 1):
            url = AF_FILE_URL.format(uniprot=uniprot, ver=ver, ext="cif")
            try:
                h = requests.head(url, allow_redirects=True, timeout=10)
                if h.ok:
                    LOGGER.info(f"✅ Valid AlphaFold UniProt ID: {uniprot}")
                    return uniprot
            except requests.RequestException:
                continue
        
        gr.Warning(f"❌ AlphaFold structure not found for UniProt ID: {uniprot}")
        return None

    # ---------- PDB ----------
    if PDB_PATTERN.fullmatch(s):
        pdb_id = s.upper()
        url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id.lower()}"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                LOGGER.info(f"✅ Valid PDB ID: {pdb_id}")
            else:
                gr.Warning(f"❌ PDB ID not found in RCSB: {pdb_id}")
                pdb_id = None
            return pdb_id
        except requests.RequestException:
            gr.Warning(f"❌ Failed to reach RCSB for PDB ID: {pdb_id}")
            return None

    # ---------- Invalid ----------
    gr.Warning("❌ Invalid input: not a UniProt / AlphaFold / PDB ID")
    return None

def on_clear_param():
    job_name_udt = datetime.now(time_zone).strftime("%Y-%m-%d_%H-%M-%S")
    inf_sav_txt_udt     = gr.update(value='')
    (inf_sav_btn_udt, inf_sav_file_udt) = on_clear_file()

    tf_sav_txt_udt      = gr.update(value='')
    (tf_sav_btn_udt, tf_sav_file_udt) = on_clear_file()

    str_txt_udt         = gr.update(value='')
    (str_btn_udt, str_file_udt) = on_clear_file()
    job_name_txt_udt    = gr.update(value=job_name_udt)
    email_txt_udt       = gr.update('')

    return (
        inf_sav_txt_udt, inf_sav_btn_udt, inf_sav_file_udt,
        tf_sav_txt_udt, tf_sav_btn_udt, tf_sav_file_udt,
        str_txt_udt, str_btn_udt, str_file_udt,
        job_name_txt_udt, email_txt_udt,
    )

# Update parameters in param to param
def update_input_param(
    
    _mode,
    _inf_sav_txt,
    _inf_sav_file,
    _model_dropdown,
    _tf_sav_txt,
    _tf_sav_file,
    str_txt,
    _str_file,
    _job_name_txt,
    _email_txt,
    param,
    request: gr.Request,
):  
    """Validate user inputs after clicking Submit, normalize them into a job payload, 
    update UI states, and decide whether the job can enter the queue.

    After the submit button is clicked, this function:
	1.	Selects the correct input sources (uploaded files take priority)
	2.	Validates SAV (variant) input
	3.	Validates structure (STR) input
	4.	Builds a clean job parameter dictionary
	6.	Updates UI state based on success or failure
	7.	Starts or stops the polling timer

    | UI Component      | Validation Success | Validation Failure |
    |-------------------|--------------------|--------------------|
    | Input section     | Hidden             | Visible            |
    | Submit button     | Hidden             | Visible            |
    | Reset button      | Visible            | Hidden             |
    | Status message    | Payload preview    | Error message      |
    | Polling timer     | Activated          | Deactivated        |
    """
    def _fail():
        param_udt = param.copy()
        param_udt["status"] = None
        input_section_udt = gr.update(visible=True)
        reset_btn_udt = gr.update(visible=False)
        timer_udt = gr.update(active=False)
        return param_udt, input_section_udt, reset_btn_udt, timer_udt

    param_udt = param.copy()
    session_id = param_udt.get("session_id")
    job_name = (_job_name_txt or "").strip()

    # 1) Validate job name first
    if not job_name:
        gr.Warning("Job name cannot be empty.")
        return _fail()
    if session_id:
        existed_job = collections.find_one(
            {"session_id": session_id, "job_name": job_name},
            {"_id": 1},
        )
        if existed_job is not None:
            gr.Warning(f'Job name "{job_name}" already exists in this session. Please use a different job name.')
            return _fail()

    # 2) Validate SAV
    if _mode == "Inferencing":
        SAV_input = _inf_sav_file if (_inf_sav_file and os.path.isfile(_inf_sav_file)) else (_inf_sav_txt or "")
    elif _mode == "Transfer Learning":
        SAV_input = _tf_sav_file if (_tf_sav_file and os.path.isfile(_tf_sav_file)) else (_tf_sav_txt or "")
    else:
        gr.Warning(f"Unknown mode: {_mode}")
        return _fail()

    SAV_data = handle_SAV(_mode, SAV_input)
    if SAV_data is None:
        return _fail()

    SAV = [f"{ele['acc']} {ele['wt_resid_mt']}" for ele in SAV_data]
    label = None if _mode == "Inferencing" else SAV_data["label"].tolist()

    # 3) Validate STR
    if _str_file and os.path.isfile(_str_file):
        basename = os.path.basename(_str_file)
        tmpfile = os.path.join(tmp_folder, basename)
        shutil.copy2(_str_file, tmpfile)
        STR_value = tmpfile
    elif str_txt is None or str_txt.strip() == "":
        STR_value = None
    else:
        STR_value = handle_STR(str_txt)
        if STR_value is None:
            return _fail()

    # 4) Attach IP (from previous getip flow)
    ip = None
    if request is not None:
        ip = request.client.host if request.client else None
        forwarded = request.headers.get("x-forwarded-for") if request.headers else None
        if forwarded:
            ip = forwarded.split(",")[0].strip()

    param_udt["status"] = "pending"
    param_udt["mode"] = _mode
    param_udt["SAV"] = SAV
    param_udt["label"] = label
    param_udt["model"] = _model_dropdown
    param_udt["job_name"] = job_name
    param_udt["email"] = _email_txt
    param_udt["STR"] = STR_value
    param_udt["IP"] = ip

    return (
        param_udt,
        gr.update(visible=False),
        gr.update(visible=True, interactive=True),
        gr.update(active=True),
    )

if __name__ == "__main__":
    pass
