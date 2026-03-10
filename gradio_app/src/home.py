import os
import gradio as gr
import secrets
import string
from datetime import datetime

from .settings import JOB_DIR, TITLE, TAIPEI_TIME_ZONE
from .web_interface import build_footer, build_header
from .web_interface import build_qa, build_licence, build_tutorial
from .web_interface import left_column
from .request import request2info, build_session_url

from pymongo import MongoClient

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

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
                    self.session_btn = gr.Button("▶️ Start / Resume a Session", elem_classes="gr-button")
                    self.session_mkd = gr.Markdown("##### Please find the input/output examples by clicking this 'Start / Resume a Session'")
                    self.session_status = gr.Markdown("")
                
        self._bind_events()
        return self

    def _bind_events(self):
        direct2sessionurl_js = """
            (url) => {
                if (!url) return;
                window.location.assign(url);
            }
        """
        # Generate/resume session
        self.session_btn.click(fn=self.on_home_session, inputs=[self.session_id, self.param_state], outputs=[self.session_id, self.param_state, self.session_url_state],
        ).then(fn=None, inputs=[self.session_url_state], outputs=[], js=direct2sessionurl_js
        )

        self.session_id.submit(fn=self.on_home_session, inputs=[self.session_id, self.param_state], outputs=[self.session_id, self.param_state, self.session_url_state],
        ).then(fn=None, inputs=[self.session_url_state], outputs=[], js=direct2sessionurl_js
        )
    
    def save_session_id(self, session_id, ip=None) -> None:
        collections.update_one(
            {"session_id": session_id},
            {
                "$setOnInsert": {
                    "session_id": session_id,
                    "status": "created",
                    "IP": ip,
                    "created_at": datetime.now(TAIPEI_TIME_ZONE).strftime('%H%M%S%d%m%Y'),
                }
            },
            upsert=True,
        )
        
    def generate_token(self, length=10):
        alphabet = string.ascii_letters + string.digits  # A–Z, a–z, 0–9
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def on_home_session(self, _session_id, param, request: gr.Request):
        old_session_ids = collections.distinct("session_id")
        _session_id = _session_id.strip()
        ip, _ = request2info(request)
        param_udt = param.copy()
        param_udt['status'] = None
        param_udt["session_id"] = None
        param_udt["session_url"] = ""
        param_udt["IP"] = ip
        session_url_udt = ""

        # Case 1: Empty input → Generate a new unique session ID
        if not _session_id:
            # loop until finding an unused ID (guaranteed uniqueness)
            while True:
                new_id = self.generate_token(length=10) 
                # if new_id overlap with old one --> redo
                if new_id not in old_session_ids:
                    self.save_session_id(new_id, ip=ip)
                    session_id_udt = gr.update(value=new_id, interactive=False)
                    param_udt["session_id"] = new_id
                    session_url_udt = build_session_url(new_id)
                    param_udt["session_url"] = session_url_udt
                    break
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
        build_header(TITLE)
        with gr.Column(elem_id="main-content"):
            with gr.Tab("Home"):
                HomeTab(JOB_DIR).build()
            with gr.Tab(label="Q & A"):
                build_qa()
            with gr.Tab(label="Tutorial"):
                build_tutorial()
            with gr.Tab(label="License"):
                build_licence()
        build_footer()

    return page

if __name__ == "__main__":
    pass
