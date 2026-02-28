import gradio as gr

from .settings import JOB_DIR, MOUNT_POINT, TITLE
from .web_interface import build_footer, build_header
from .QA import qa
from .job_manager import manager_tab
from .tutorial import tutorial
from .web_interface import left_column
from .update_session import on_session_id
from .web_interface import tandem_input, left_column

class SessionPage:
    def __init__(self, folder):
        self.folder = folder

    def build(self):
        self.timer = gr.Timer(value=1, active=True) # Timer to check result
        self.job_folder = gr.State()
        self.session_url_state = gr.State("")

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
        pass

def _read_session_id(request: gr.Request):
    return request.query_params.get("session_id").strip()

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
