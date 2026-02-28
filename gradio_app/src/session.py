import os
import shutil
import gradio as gr
from pymongo import MongoClient
from datetime import datetime, timezone
from urllib.parse import quote

from .settings import JOB_DIR, MOUNT_POINT, TITLE
from .web_interface import build_footer, build_header
from .QA import qa
from .job_manager import manager_tab
from .tutorial import tutorial
from .web_interface import left_column
from .web_interface import tandem_input, left_column
from .web_interface import session, tandem_input, tandem_output, left_column, on_auto_view
from .logger import LOGGER

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]
TANDEM_WEBSITE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) # ./tandem_website
jobs_folder = os.path.join(TANDEM_WEBSITE_ROOT, 'tandem/jobs')
tmp_folder = os.path.join(TANDEM_WEBSITE_ROOT, 'gradio_app/tmp')

def session_exists(session_id) -> bool:
    sid = session_id.strip()
    if not sid:
        return False
    return collections.count_documents({"session_id": sid}) > 0

class SessionPage:
    def __init__(self, folder):
        self.folder = folder

    def build(self):
        self.job_folder = gr.State()
        self.session_url_state = gr.State("")

        with gr.Row() as self.input_page:
            with gr.Column(scale=1):
                left_column()
            with gr.Column(scale=1):
                self.param_state = gr.State({})
                self.jobs_folder_state = gr.State(self.folder)
                self.job_url = gr.Textbox(value="", visible=False)

                with gr.Group():
                    gr.Markdown("### User session", elem_classes="h3")
                    placeholder = "Start a new session or paste an existing session ID"
                    self.session_id = gr.Textbox(label=" ", show_label=True, placeholder=placeholder, interactive=True, buttons=["copy"], elem_classes="gr-textbox",)
                    self.session_btn = gr.Button("▶️ Start / Resume a Session", elem_classes="gr-button")
                    self.session_status = gr.Markdown("")
                    self.job_dropdown = gr.Dropdown(label="Old jobs", visible=False, filterable=False, allow_custom_value=False, preserved_by_key=None)
                
                # Input UI
                (
                    self.param_state,
                    self.input_section,
                    self.mode,
                    self.inf_section,
                    self.tf_section,
                    self.inf_sav_txt,
                    self.inf_sav_btn,
                    self.inf_sav_file,
                    self.inf_auto_view,

                    self.model_dropdown,
                    
                    self.tf_sav_txt,
                    self.tf_sav_btn,
                    self.tf_sav_file,
                    self.tf_auto_view,
                    self.structure_section,
                    self.str_check,
                    self.str_txt,
                    self.str_btn,
                    self.str_file,

                    self.job_name_txt,
                    self.email_txt,
                    self.submit_btn,
                ) = tandem_input(self.param_state)

        self._bind_events()
        return self

    def _bind_events(self):
        direct2joburl_js = """
            (url) => {
                if (!url) return;
                window.location.assign(url);
            }
        """
        # Collect parameters and submit to MongoDB.
        self.submit_btn.click(
               fn=self.update_input_param, outputs=[self.param_state, self.job_url], inputs=[self.session_id, self.mode, self.inf_sav_txt, self.inf_sav_file, self.model_dropdown, self.tf_sav_txt, self.tf_sav_file, self.str_txt, self.str_file, self.job_name_txt, self.email_txt, self.param_state,],
        ).then(fn=self.send_job, inputs=[self.param_state], outputs=[self.param_state],
        ).then(fn=None, inputs=[self.job_url], outputs=[], js=direct2joburl_js
        )

        self.job_dropdown.select(fn=self.build_job_url, inputs=[self.session_id, self.job_dropdown], outputs=[self.job_url],
        ).then(fn=None, inputs=[self.job_url], outputs=[], js=direct2joburl_js
        )

    def build_job_url(self, session_id, job_name):
        sid = (session_id or "").strip()
        jn = (job_name or "").strip()
        if not sid or not jn:
            return ""
        root_url = os.getenv("ROOT_URL", "").strip().rstrip("/")
        if root_url:
            return f"{root_url}/{quote(sid, safe='')}/{quote(jn, safe='')}"
        return f"/{quote(sid, safe='')}/{quote(jn, safe='')}"

    def update_input_param(self, session_id, mode, inf_sav_txt, inf_sav_file,
        model_dropdown, tf_sav_txt, tf_sav_file, str_txt, str_file, job_name_txt, email_txt, param, request: gr.Request
    ):
        from .update_input import handle_SAV, handle_STR

        param_udt = (param or {}).copy()
        session_id = (session_id or "").strip()
        job_name = (job_name_txt or "").strip()
        job_url = ""

        # 1) Validate job name first
        if not job_name:
            gr.Warning("Job name cannot be empty.")
            return param_udt, job_url
        if not session_id:
            gr.Warning("Session ID is required.")
            return param_udt, job_url
        if session_id:
            existed_job = collections.find_one({"session_id": session_id, "job_name": job_name}, {"_id": 1},)
            if existed_job is not None:
                gr.Warning(f'Job name "{job_name}" already exists in this session. Please use a different job name.')
                return param_udt, job_url

        # 2) Validate SAV
        if mode == "Inferencing":
            SAV_input = inf_sav_file if (inf_sav_file and os.path.isfile(inf_sav_file)) else (inf_sav_txt or "")
        elif mode == "Transfer Learning":
            SAV_input = tf_sav_file if (tf_sav_file and os.path.isfile(tf_sav_file)) else (tf_sav_txt or "")
        else:
            gr.Warning(f"Unknown mode: {mode}")
            return param_udt, job_url

        SAV_data = handle_SAV(mode, SAV_input)
        if SAV_data is None:
            return param_udt, job_url

        SAV = [f"{ele['acc']} {ele['wt_resid_mt']}" for ele in SAV_data]
        label = None if mode == "Inferencing" else SAV_data["label"].tolist()

        # 3) Validate STR
        if str_file and os.path.isfile(str_file):
            basename = os.path.basename(str_file)
            tmpfile = os.path.join(tmp_folder, basename)
            shutil.copy2(str_file, tmpfile)
            STR_value = tmpfile
        elif str_txt is None or str_txt.strip() == "":
            STR_value = None
        else:
            STR_value = handle_STR(str_txt)
            if STR_value is None:
                return param_udt, job_url

        # 4) Attach IP (from previous getip flow)
        ip = None
        if request is not None:
            ip = request.client.host if request.client else None
            forwarded = request.headers.get("x-forwarded-for") if request.headers else None
            if forwarded:
                ip = forwarded.split(",")[0].strip()

        root_url = os.getenv("ROOT_URL", "").strip().rstrip("/")
        if not root_url and request is not None and request.base_url is not None:
            root_url = str(request.base_url).rstrip("/")
        session_url = ""
        if root_url:
            session_url = f"{root_url}/{quote(session_id, safe='')}"
        job_url = ""
        if root_url:
            job_url = f"{root_url}/{quote(session_id, safe='')}/{quote(job_name, safe='')}"

        param_udt["status"] = "pending"
        param_udt["session_id"] = session_id
        param_udt["session_url"] = session_url
        param_udt["mode"] = mode
        param_udt["SAV"] = SAV
        param_udt["label"] = label
        param_udt["model"] = model_dropdown
        param_udt["job_name"] = job_name
        param_udt["email"] = email_txt
        param_udt["STR"] = STR_value
        param_udt["IP"] = ip
        param_udt["job_url"] = job_url

        return param_udt, job_url

    def send_job(self, _param):
        _job_status = _param.get('status', None)
        if _job_status != 'pending':
            return _param
        collections.insert_one(_param)
        LOGGER.info(f"✅ Submitted with payload: {_param}")
        return _param

def _read_session_id(request: gr.Request):
    if request is None:
        return ""
    return (request.query_params.get("session_id", "") or "").strip()

def on_session_id(_session_id):
    session_id_udt = gr.update(value=_session_id, interactive=False)
    session_btn_udt = gr.update(interactive=False)
    session_status_udt = "ℹ️ Please save the session ID for future reference."
    base_model_choices = ["TANDEM", "TANDEM-DIMPLE for GJB2", "TANDEM-DIMPLE for RYR1"]
    existing_jobs = collections.distinct("job_name", {"session_id": _session_id, "status": {"$in": ["pending", "processing", "finished"]}},)
    has_jobs = len(existing_jobs) > 0

    if has_jobs:
        job_dropdown_udt = gr.update(visible=True, value=None, choices=existing_jobs, interactive=True)
        pre_trained_models = collections.distinct("job_name", {"session_id": _session_id, "status": "finished", "mode": "Transfer Learning"},)
        model_dropdown_udt = gr.update(choices=base_model_choices + pre_trained_models)
    else:
        collections.update_one(
            {"session_id": _session_id},
            {"$set": {"session_id": _session_id, "status": "created"}},
            upsert=True,
        )
        job_dropdown_udt = gr.update(visible=False, value=None, choices=[])
        model_dropdown_udt = gr.update(choices=base_model_choices)
    return session_id_udt, session_btn_udt, session_status_udt, job_dropdown_udt, model_dropdown_udt

def session_page():
    with gr.Blocks(title=TITLE) as page:
        build_header(TITLE)
        with gr.Column(elem_id="main-content"):
            with gr.Tab("Home"):
                session_ui = SessionPage(JOB_DIR).build()
            with gr.Tab(label="🗂️ Job Manager", id='job'):
                manager_tab()
            with gr.Tab(label="Q & A"):
                qa(MOUNT_POINT)
            with gr.Tab(label="Tutorial"):
                tutorial(MOUNT_POINT)
        build_footer(MOUNT_POINT)

        page.load(fn=_read_session_id, inputs=None, outputs=[session_ui.session_id], queue=False,
        ).then(fn=on_session_id, inputs=session_ui.session_id, outputs=[session_ui.session_id, session_ui.session_btn, session_ui.session_status, session_ui.job_dropdown, session_ui.model_dropdown], queue=False,
        )

    return page

if __name__ == "__main__":
    pass
