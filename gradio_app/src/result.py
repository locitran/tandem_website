import gradio as gr
from pymongo import MongoClient

from .settings import JOB_DIR, MOUNT_POINT, TITLE
from .web_interface import build_footer, build_header, tandem_output
from .QA import qa
from .job_manager import manager_tab
from .tutorial import tutorial
from .update_output import on_select_sav, update_finished_job

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]


class ResultPage:
    def __init__(self, folder):
        self.folder = folder

    def build(self):
        self.param_state = gr.State({})
        self.jobs_folder_state = gr.State(self.folder)
        self.page_status = gr.Markdown("")

        (
            self.output_section,
            self.inf_output_secion,
            self.tf_output_secion,
            self.pred_table,
            self.image_viewer,
            self.folds_state,
            self.fold_dropdown,
            self.sav_textbox,
            self.loss_image,
            self.test_evaluation,
            self.model_save,
            self.result_zip,
            self.focus_refresh_btn,
        ) = tandem_output()

        self.job_folder = gr.State()
        self.pred_table.select(
            on_select_sav,
            inputs=[self.pred_table, self.job_folder],
            outputs=[self.image_viewer],
        )
        return self


def _read_session_id_and_job_name(request: gr.Request):
    if request is None:
        return "", ""
    session_id = (request.query_params.get("session_id", "") or "").strip()
    job_name = (request.query_params.get("job_name", "") or "").strip()
    return session_id, job_name


def _load_result_param(session_id, job_name):
    sid = (session_id or "").strip()
    jn = (job_name or "").strip()
    if not sid or not jn:
        return {}, "Missing session_id or job_name in URL."

    doc = collections.find_one({"session_id": sid, "job_name": jn}, {"_id": 0})
    if doc is None:
        return {}, f"Job not found: session_id={sid}, job_name={jn}"
    return doc, ""


def result_page():
    with gr.Blocks(title=TITLE) as page:
        build_header(TITLE)
        with gr.Column(elem_id="main-content"):
            with gr.Tab("Result"):
                session_id_tb = gr.Textbox(visible=False)
                job_name_tb = gr.Textbox(visible=False)
                result_ui = ResultPage(JOB_DIR).build()
                
            with gr.Tab(label="🗂️ Job Manager", id="job"):
                manager_tab()
            with gr.Tab(label="Q & A"):
                qa(MOUNT_POINT)
            with gr.Tab(label="Tutorial"):
                tutorial(MOUNT_POINT)
        build_footer(MOUNT_POINT)

        page.load(
            fn=_read_session_id_and_job_name, inputs=None, outputs=[session_id_tb, job_name_tb], queue=False,
        ).then(fn=_load_result_param, inputs=[session_id_tb, job_name_tb], outputs=[result_ui.param_state, result_ui.page_status], queue=False,
        ).then(fn=update_finished_job,inputs=[result_ui.param_state, result_ui.jobs_folder_state],
            outputs=[
                result_ui.output_section,
                result_ui.result_zip,
                result_ui.inf_output_secion,
                result_ui.pred_table,
                result_ui.image_viewer,
                result_ui.tf_output_secion,
                result_ui.folds_state,
                result_ui.fold_dropdown,
                result_ui.sav_textbox,
                result_ui.loss_image,
                result_ui.test_evaluation,
                result_ui.model_save,
                result_ui.job_folder,
            ],
            queue=False,
        )

    return page


if __name__ == "__main__":
    pass
