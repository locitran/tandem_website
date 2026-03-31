import os
import gradio as gr
import secrets
import string
import json
from datetime import datetime
from . import js
from .settings import EXAMPLES_JSON, FIGURE_1, HTML_DIR, JOB_DIR, TITLE, TAIPEI_TIME_ZONE
from .base import build_footer, build_header, build_last_updated
from .request import request2info, build_job_url, build_session_url

from pymongo import MongoClient

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

with open(EXAMPLES_JSON, "r", encoding="utf-8") as f:
    EXAMPLES = json.load(f)

def left_column():
    overall_acc = 83.6
    gjb2_acc = 98.7
    ryr1_acc = 97.0

    intro = (
        "A DNN-based foundation model designed for disease-specific pathogenicity prediction of missense variants. "
        "It integrates protein dynamics with sequence, chemical, and structural features and uses transfer learning "
        "to refine models for specific diseases. Trained on ~20,000 variants, it achieves high accuracy in general "
        f"predictions ({overall_acc:.1f}%) and excels in disease-specific contexts, reaching {gjb2_acc:.1f}% accuracy "
        f"for GJB2 and {ryr1_acc:.1f}% for RYR1, surpassing tools like Rhapsody and AlphaMissense. TANDEM-DIMPLE "
        "supports clinicians and geneticists in classifying new variants and improving diagnostic tools for genetic disorders."
    )
    gr.Markdown(f"### What is TANDEM-DIMPLE?\n{intro}")
    gr.Image(value=FIGURE_1, label="", show_label=False, width=None)

class HomeTab:
    def __init__(self, folder):
        self.folder = folder

    def build(self):
        self.timer = gr.Timer(value=1, active=True) # Timer to check result
        self.job_folder = gr.State()
        self.session_url_state = gr.Textbox(value="", visible=False)

        with gr.Row() as self.input_page:
            with gr.Column(scale=1):
                left_column()
            with gr.Column(scale=1):
                self.param_state = gr.State({})
                self.jobs_folder_state = gr.State(self.folder)

                with gr.Group():
                    gr.Markdown("### User session", elem_classes="h3")
                    placeholder = "Start a new session or paste an existing session ID"
                    self.session_id = gr.Textbox(label=" ", show_label=True, placeholder=placeholder, interactive=True, buttons=["copy"], elem_classes="gr-textbox",)
                    self.session_btn = gr.Button("▶️ Start or Resume a Session", elem_classes="gr-button")
                    self.session_status = gr.Markdown("")

                with gr.Row():
                    self.input_example = gr.Markdown(elem_id="input_example", container=True)
                    self.input_load = gr.Button(elem_id="input_load")
                    self.output_view = gr.Button(elem_id="output_view")

                    filepath = os.path.join(HTML_DIR, "home_examples.html")
                    examples_html = js.build_html_text(filepath)
                    self.examples_html = gr.HTML(examples_html, container=True)
                
        self._bind_events()
        return self

    def _bind_events(self):
        self.session_btn.click(fn=self.on_home_session, inputs=[self.session_id, self.param_state], outputs=[self.session_id, self.param_state, self.session_url_state],
        ).then(fn=None, inputs=[self.session_url_state], outputs=[], js=js.direct2url_refresh
        )

        self.session_id.submit(fn=self.on_home_session, inputs=[self.session_id, self.param_state], outputs=[self.session_id, self.param_state, self.session_url_state],
        ).then(fn=None, inputs=[self.session_url_state], outputs=[], js=js.direct2url_refresh
        )

        self.input_load.click(fn=self.on_load_example, inputs=[self.input_example], outputs=[self.session_url_state], js=js.load_home_input,
        ).then(fn=None, inputs=[self.session_url_state], outputs=[], js=js.direct2url_refresh)

        self.output_view.click(fn=self.on_view_example, inputs=[self.input_example], outputs=[self.session_url_state], js=js.load_home_input,
        ).then(fn=None, inputs=[self.session_url_state], outputs=[], js=js.direct2url_refresh)
    
    def save_session_id(self, session_id, ip=None, geo_info=None) -> None:
        geo_info = geo_info or {}
        collections.update_one({"session_id": session_id},
            {
                "$setOnInsert": {
                    "session_id": session_id,
                    "status": "created",
                    "IP": ip,
                    "geo_info": geo_info,
                    "city": geo_info.get("city", ""),
                    "region": geo_info.get("region", ""),
                    "country": geo_info.get("country", ""),
                    "continent": geo_info.get("continent", ""),
                    "created_at": datetime.now(TAIPEI_TIME_ZONE).strftime('%H%M%S%d%m%Y'),
                }
            },
            upsert=True,
        )
        
    def generate_token(self, length=10):
        alphabet = string.ascii_letters + string.digits  # A–Z, a–z, 0–9
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def create_new_session(self, ip=None, geo_info=None):
        old_session_ids = collections.distinct("session_id")
        while True:
            new_id = self.generate_token(length=10)
            if new_id not in old_session_ids:
                self.save_session_id(new_id, ip=ip, geo_info=geo_info)
                return new_id

    def on_load_example(self, selected_example, request: gr.Request):
        example_name = (selected_example or "").strip()
        if not example_name:
            gr.Warning("Please select an example first.")
            return ""

        ex = EXAMPLES.get(example_name)
        if not ex:
            gr.Warning(f"No example configuration is available for '{example_name}'.")
            return ""

        ip, _, geo_info = request2info(request)
        session_id = self.create_new_session(ip=ip, geo_info=geo_info)
        return build_session_url(session_id, example_name=example_name, example_action="load_input")

    def on_view_example(self, selected_example, request: gr.Request):
        example_name = (selected_example or "").strip()
        if not example_name:
            gr.Warning("Please select an example first.")
            return ""

        ex = EXAMPLES.get(example_name)
        if not ex:
            gr.Warning(f"No example configuration is available for '{example_name}'.")
            return ""

        ip, _, geo_info = request2info(request)
        session_id = self.create_new_session(ip=ip, geo_info=geo_info)
        return build_job_url(session_id, "", example_name=example_name, example_action="view_output")

    def on_home_session(self, _session_id, param, request: gr.Request):
        old_session_ids = collections.distinct("session_id")
        _session_id = _session_id.strip()
        ip, _, geo_info = request2info(request)
        param_udt = param.copy()
        param_udt['status'] = None
        param_udt["session_id"] = None
        param_udt["session_url"] = ""
        param_udt["IP"] = ip
        param_udt["geo_info"] = geo_info
        param_udt["city"] = geo_info.get("city", "")
        param_udt["region"] = geo_info.get("region", "")
        param_udt["country"] = geo_info.get("country", "")
        param_udt["continent"] = geo_info.get("continent", "")
        session_url_udt = ""

        # Case 1: Empty input → Generate a new unique session ID
        if not _session_id:
            new_id = self.create_new_session(ip=ip, geo_info=geo_info)
            session_id_udt = gr.update(value=new_id, interactive=False)
            param_udt["session_id"] = new_id
            session_url_udt = build_session_url(new_id)
            param_udt["session_url"] = session_url_udt
        # Case 2: User-provided input, invalid format
        elif _session_id not in old_session_ids:
            session_id_udt = gr.update(value="", interactive=True)
            gr.Warning("Please enter a valid session ID")
        # Case 3: Valid existing/new session ID
        elif _session_id in old_session_ids:
            param_udt["session_id"] = _session_id
            session_url_udt = build_session_url(_session_id)
            param_udt["session_url"] = session_url_udt
            session_id_udt = gr.update(value=_session_id, interactive=False)
        else:
            session_id_udt = gr.update(value="", interactive=True)
            gr.Warning("Unexpected error. Please try again.")
        
        return (session_id_udt, param_udt, session_url_udt)

def home_page():
    with gr.Blocks(title=TITLE) as page:
        build_header(TITLE, current_page="home")
        with gr.Column(elem_id="main-content"):
            HomeTab(JOB_DIR).build()
            build_last_updated()
        build_footer()

    return page

if __name__ == "__main__":
    pass
