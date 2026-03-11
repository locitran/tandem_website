import json
import os
import shutil
from datetime import datetime

import gradio as gr
from pymongo import MongoClient

from . import js
from .logger import LOGGER
from .request import (
    build_job_url,
    build_session_url,
    passthrough_url,
    request2info,
    request2session_id,
    session_exists,
)
from .settings import EXAMPLES_JSON, HTML_DIR, JOB_DIR, TITLE
from .update_input import handle_SAV, handle_STR, on_clear_file, on_clear_param, upload_file
from .web_interface import build_footer, build_header, left_column

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

TANDEM_WEBSITE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
tmp_folder = os.path.join(TANDEM_WEBSITE_ROOT, "gradio_app/tmp")
READ_ONLY_SESSION_ID = "test"

with open(EXAMPLES_JSON, "r", encoding="utf-8") as f:
    EXAMPLES = json.load(f)


class SessionPage:
    def __init__(self, folder):
        self.folder = folder

    def build(self):
        self.job_folder = gr.State()
        self.error_url = gr.Textbox(value="", visible=False)

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
                    self.session_id = gr.Textbox(label=" ",show_label=True,placeholder=placeholder,interactive=False,buttons=["copy"],elem_classes="gr-textbox",)
                    self.job_dropdown = gr.Dropdown(label="Old jobs",visible=False,filterable=False,allow_custom_value=False,preserved_by_key=None,)
                    self.session_status = gr.Markdown("")
                self._build_input_section()

        self._bind_events()
        return self

    def _build_input_section(self):
        with gr.Group() as self.input_section:
            self.mode = gr.Radio(["Inferencing", "Transfer Learning"], value="Inferencing",label="Mode of Actions",)
            with gr.Group(visible=True) as self.inf_section:
                with gr.Row():
                    label = "Paste single amino acid variants for one or multiple proteins (≤4)"
                    info = "using the format - (UniProt_ID)(space)(WT_AA|ResidueID|Mutant_AA)"
                    placeholder = "O14508 S52N\nP29033 Y217D\n..."
                    self.inf_sav_txt = gr.Textbox(value="",interactive=True,max_lines=5,lines=4,elem_id="inf-sav-txt",label=label,placeholder=placeholder,scale=8,elem_classes="gr-textbox",info=info,)
                    self.inf_sav_btn = gr.UploadButton(label="Upload SAVs",file_count="single",file_types=[".txt"],elem_classes="gr-button",scale=3,)
                    self.inf_sav_file = gr.File(visible=False,file_types=[".txt"],height=145,scale=3,)

                with gr.Row():
                    self.inf_input_example = gr.Markdown(elem_id="inf_input_example")
                    self.inf_input_load = gr.Button(elem_id="inf_input_load")
                    self.inf_auto_view = gr.Button(elem_id="inf_auto_view")
                    self.inf_clear_btn = gr.Button(elem_id="inf_clear_btn")
                    self.inf_output_url = gr.Textbox(value="", visible=False)

                    filepath = os.path.join(HTML_DIR, "inf_input_output_examples.html")
                    inf_examples_html = js.build_html_text(filepath)
                    self.inf_examples_html = gr.HTML(inf_examples_html)

                choices = ["TANDEM", "TANDEM-DIMPLE for GJB2", "TANDEM-DIMPLE for RYR1"]
                self.model_dropdown = gr.Dropdown(value="TANDEM", label="Select model for prediction", choices=choices, interactive=True, filterable=False,)

            with gr.Group(visible=False) as self.tf_section:
                with gr.Row():
                    label = "Paste single amino acid variants for one or multiple proteins (≤4) and the corresponding labels"
                    info = "using the format - (UniProt_ID)(space)(WT_AA|ResidueID|Mutant_AA)(space)(Label)"
                    placeholder = "O14508 S52N 1\nP29033 Y217D 0\n..."
                    self.tf_sav_txt = gr.Textbox(value="",interactive=True,max_lines=5,lines=4,elem_id="tf-sav-txt",label=label,placeholder=placeholder,scale=8,elem_classes="gr-textbox",info=info,)
                    self.tf_sav_btn = gr.UploadButton(label="Upload SAVs",file_count="single",file_types=[".txt"],elem_classes="gr-button",scale=3,)
                    self.tf_sav_file = gr.File(visible=False, file_types=[".txt"], height=145, scale=3,)

                with gr.Row():
                    self.tf_input_example = gr.Markdown(elem_id="tf_input_example") # temporary name (bridge)
                    self.tf_input_load = gr.Button(elem_id="tf_input_load")
                    self.tf_output_view = gr.Button(elem_id="tf_output_view")
                    self.tf_clear_btn = gr.Button(elem_id="tf_clear_btn")
                    self.tf_output_url = gr.Textbox(value="", visible=False)

                    filepath = os.path.join(HTML_DIR, "tf_input_output_examples.html")
                    tf_examples_html = js.build_html_text(filepath)
                    self.tf_examples_html = gr.HTML(tf_examples_html)

            self.str_check = gr.Checkbox(value=False,label="Provide PDB/AF2 ID or upload coordinate file (pdb/cif)",interactive=True,)
            with gr.Row(visible=False) as self.structure_section:
                self.str_txt = gr.Textbox(value=None, label="Structure", placeholder="PDB ID (e.g., 1GOD) or AF2 ID (e.g., 014508)", interactive=True, show_label=False, scale=8,)
                self.str_btn = gr.UploadButton("Upload file", file_count="single", elem_id="sav-btn", file_types=[".cif", ".pdb"], scale=3,)
                self.str_file = gr.File(visible=False, scale=3, height=145)

            self.job_name_txt = gr.Textbox(value="",label="Job name",placeholder="Enter job name",interactive=True,elem_classes="gr-textbox",)
            self.email_txt = gr.Textbox(value=None,label="Email (Optional)",placeholder="Enter your email",interactive=True,visible=False,type="email",elem_classes="gr-textbox",)
            self.submit_btn = gr.Button("Submit", elem_classes="gr-button")

    def _bind_events(self):
        self.str_check.change(self.on_structure, self.str_check, [self.structure_section])

        self.inf_input_load.click(fn=self.on_load_example, inputs=[self.inf_input_example], outputs=[self.inf_sav_txt, self.str_check, self.str_btn, self.str_file, self.job_name_txt], js=js.load_inf_input
        ).then(fn=self.on_tandem_refresh, inputs=[self.param_state, self.job_name_txt], outputs=[self.param_state],
        )
        self.tf_input_load.click(fn=self.on_load_example, inputs=[self.tf_input_example], outputs=[self.inf_sav_txt, self.str_check, self.str_btn, self.str_file, self.job_name_txt], js=js.load_tf_input
        ).then(fn=self.on_tandem_refresh, inputs=[self.param_state, self.job_name_txt], outputs=[self.param_state],
        )

        self.inf_auto_view.click(fn=self.on_view_example,inputs=[self.inf_input_example],outputs=[self.inf_output_url],js=js.load_inf_input,
        ).then(fn=passthrough_url,inputs=[self.inf_output_url],outputs=[self.inf_output_url],js=js.direct2url_open,
        )
        self.tf_output_view.click(fn=self.on_view_example,inputs=[self.tf_input_example],outputs=[self.tf_output_url],js=js.load_tf_input,
        ).then(fn=passthrough_url,inputs=[self.tf_output_url],outputs=[self.tf_output_url],js=js.direct2url_open,
        )

        self.mode.change(fn=self.on_mode,inputs=[self.mode, self.param_state],outputs=[self.inf_section, self.tf_section, self.param_state],)

        self.inf_sav_btn.upload(fn=upload_file, inputs=[self.inf_sav_btn], outputs=[self.inf_sav_btn, self.inf_sav_file])
        self.tf_sav_btn.upload(fn=upload_file, inputs=[self.tf_sav_btn], outputs=[self.tf_sav_btn, self.tf_sav_file])
        self.str_btn.upload(fn=upload_file, inputs=[self.str_btn], outputs=[self.str_btn, self.str_file])

        self.inf_sav_file.clear(fn=on_clear_file, inputs=[], outputs=[self.inf_sav_btn, self.inf_sav_file])
        self.tf_sav_file.clear(fn=on_clear_file, inputs=[], outputs=[self.tf_sav_btn, self.tf_sav_file])
        self.str_file.clear(fn=on_clear_file, inputs=[], outputs=[self.str_btn, self.str_file])

        self.inf_clear_btn.click(fn=on_clear_param, inputs=[],
            outputs=[self.inf_sav_txt,self.inf_sav_btn,self.inf_sav_file,self.tf_sav_txt,self.tf_sav_btn,self.tf_sav_file,self.str_txt,self.str_btn,self.str_file,self.job_name_txt,self.email_txt,],
        )
        self.tf_clear_btn.click(fn=on_clear_param, inputs=[],
            outputs=[self.inf_sav_txt,self.inf_sav_btn,self.inf_sav_file,self.tf_sav_txt,self.tf_sav_btn,self.tf_sav_file,self.str_txt,self.str_btn,self.str_file,self.job_name_txt,self.email_txt,],
        )

        self.submit_btn.click(fn=self.update_input_param, outputs=[self.param_state, self.job_url],
            inputs=[self.session_id,self.mode,self.inf_sav_txt,self.inf_sav_file,self.model_dropdown,self.tf_sav_txt,self.tf_sav_file,self.str_txt,self.str_file,self.job_name_txt,self.email_txt,self.param_state,],
        ).then(fn=self.send_job,inputs=[self.param_state],outputs=[self.param_state],
        ).then(fn=self.refresh_job_dropdown,inputs=[self.param_state],outputs=[self.job_dropdown],
        ).then(fn=None,inputs=[self.job_url],outputs=[],js=js.direct2url_refresh,
        )

        self.job_dropdown.select(fn=build_job_url,inputs=[self.session_id, self.job_dropdown],outputs=[self.job_url],
        ).then(fn=None,inputs=[self.job_url],outputs=[],js=js.direct2url_refresh,
        )

    def on_load_example(self, example_name):
        ex = EXAMPLES.get(example_name, "")
        if ex == "":
            return (gr.update(),) * 5

        sav_txt_udt = gr.update(value="\n".join(ex["SAV"]))
        str_check_value = bool(ex.get("str_check", False))
        str_file_value = ex.get("str_file")
        str_check_udt = gr.update(value=str_check_value)
        str_btn_udt = gr.update(visible=not str_check_value)
        str_file_udt = gr.update(value=str_file_value, visible=bool(str_check_value and str_file_value))
        job_name_udt = gr.update(value=ex["job_name"])
        return sav_txt_udt, str_check_udt, str_btn_udt, str_file_udt, job_name_udt

    def on_tandem_refresh(self, param, example_name):
        param_udt = param.copy()
        param_udt["refresh"] = True
        param_udt["GJB2_test"] = example_name == "GJB2 demo"
        return param_udt

    def on_view_example(self, example_name):
        ex = EXAMPLES.get(example_name, "")
        if ex == "":
            gr.Warning("Please select an example first.")
            return ""

        session_id = ex.get("session_id", "")
        job_name = ex.get("job_name", "")
        if not session_id or not job_name:
            gr.Warning(f"No output example is configured for '{example_name}'.")
            return ""

        return build_job_url(session_id, job_name)

    def on_mode(self, mode, param):
        param_udt = param.copy()
        param_udt["GJB2_test"] = False
        return (
            gr.update(visible=(mode == "Inferencing")),
            gr.update(visible=(mode == "Transfer Learning")),
            param_udt,
        )

    def on_structure(self, checked: bool):
        return gr.update(visible=checked)

    def update_input_param(
        self,
        session_id,
        mode,
        inf_sav_txt,
        inf_sav_file,
        model_dropdown,
        tf_sav_txt,
        tf_sav_file,
        str_txt,
        str_file,
        job_name_txt,
        email_txt,
        param,
        request: gr.Request,
    ):
        ip, tz_final = request2info(request)
        if session_id == READ_ONLY_SESSION_ID:
            gr.Warning("Session 'test' is read-only. Please start a new session to submit jobs.")
            param_udt = param.copy()
            param_udt["status"] = None
            return param_udt, ""

        job_name_raw = (job_name_txt or "").strip()
        timestamp = datetime.now(tz_final).strftime("%H%M%S%d%m%Y")
        job_name_full = timestamp if not job_name_raw else f"{job_name_raw}_{timestamp}"

        param_udt = param.copy()
        param_udt["status"] = None
        job_url = build_job_url(session_id, job_name_full)
        session_url = build_session_url(session_id)

        if mode == "Inferencing":
            sav_input = inf_sav_file if (inf_sav_file and os.path.isfile(inf_sav_file)) else (inf_sav_txt or "")
        elif mode == "Transfer Learning":
            sav_input = tf_sav_file if (tf_sav_file and os.path.isfile(tf_sav_file)) else (tf_sav_txt or "")
        else:
            gr.Warning(f"Unknown mode: {mode}")
            return param_udt, job_url

        sav_data = handle_SAV(mode, sav_input)
        if sav_data is None:
            return param_udt, job_url

        sav = [f"{ele['acc']} {ele['wt_resid_mt']}" for ele in sav_data]
        label = None if mode == "Inferencing" else sav_data["label"].tolist()

        if str_file and os.path.isfile(str_file):
            basename = os.path.basename(str_file)
            tmpfile = os.path.join(tmp_folder, basename)
            shutil.copy2(str_file, tmpfile)
            str_value = tmpfile
        elif str_txt is None or str_txt.strip() == "":
            str_value = None
        else:
            str_value = handle_STR(str_txt)
            if str_value is None:
                return param_udt, job_url

        param_udt["status"] = "pending"
        param_udt["session_id"] = session_id
        param_udt["session_url"] = session_url
        param_udt["mode"] = mode
        param_udt["SAV"] = sav
        param_udt["label"] = label
        param_udt["model"] = model_dropdown
        param_udt["job_name"] = job_name_full
        param_udt["email"] = email_txt
        param_udt["STR"] = str_value
        param_udt["IP"] = ip
        param_udt["job_url"] = job_url
        return param_udt, job_url

    def send_job(self, _param):
        if _param.get("status") != "pending":
            return _param
        param_udt = _param.copy()
        param_udt.pop("_id", None)
        collections.update_one(
            {"session_id": param_udt.get("session_id"), "job_name": param_udt.get("job_name")},
            {"$set": param_udt},
            upsert=True,
        )
        LOGGER.info(f"✅ Submitted with payload: {param_udt}")
        return param_udt

    def refresh_job_dropdown(self, param):
        session_id = param.get("session_id")
        current_job = param.get("job_name")
        if not session_id or not current_job:
            return gr.update()

        job_names = collections.distinct(
            "job_name",
            {"session_id": session_id, "status": {"$in": ["pending", "processing", "finished"]}},
        )
        if current_job not in job_names:
            job_names.append(current_job)
        return gr.update(visible=True, choices=sorted(job_names), value=current_job, interactive=True)


def on_session_id(session_id):
    base_model_choices = ["TANDEM", "TANDEM-DIMPLE for GJB2", "TANDEM-DIMPLE for RYR1"]
    session_id_udt = gr.update(value=session_id, interactive=False)
    is_read_only = session_id == READ_ONLY_SESSION_ID
    session_status_udt = "ℹ️ Please save the session ID for future reference."
    if is_read_only:
        session_status_udt = "\n⚠️ Demo session 'test' is read-only. Job submission is disabled."

    existing_jobs = collections.distinct(
        "job_name",
        {"session_id": session_id, "status": {"$in": ["pending", "processing", "finished"]}},
    )

    if existing_jobs:
        job_dropdown_udt = gr.update(visible=True, value=None, choices=existing_jobs, interactive=True)
        pre_trained_models = collections.distinct(
            "job_name",
            {"session_id": session_id, "status": "finished", "mode": "Transfer Learning"},
        )
        model_dropdown_udt = gr.update(choices=base_model_choices + pre_trained_models)
    else:
        collections.update_one(
            {"session_id": session_id},
            {"$set": {"session_id": session_id, "status": "created"}},
            upsert=True,
        )
        job_dropdown_udt = gr.update(visible=False, value=None, choices=[])
        model_dropdown_udt = gr.update(choices=base_model_choices)

    submit_btn_udt = gr.update(interactive=not is_read_only)
    return session_id_udt, session_status_udt, job_dropdown_udt, model_dropdown_udt, submit_btn_udt


def session_page():
    with gr.Blocks(title=TITLE) as page:
        build_header(TITLE, current_page="home")
        with gr.Column(elem_id="main-content"):
            ui = SessionPage(JOB_DIR).build()
        build_footer()

        page.load(fn=request2session_id, inputs=None, outputs=[ui.session_id], queue=False,
        ).then(fn=session_exists,inputs=[ui.session_id],outputs=[ui.error_url],queue=False,
        ).then(fn=passthrough_url,inputs=[ui.error_url],outputs=[ui.error_url],js=js.direct2url_refresh,queue=False,
        ).then(fn=on_session_id,inputs=ui.session_id,outputs=[ui.session_id, ui.session_status, ui.job_dropdown, ui.model_dropdown, ui.submit_btn],queue=False,
        )

    return page


if __name__ == "__main__":
    pass
