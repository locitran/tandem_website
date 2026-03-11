import os
import shutil
import json
import html
import pandas as pd 
import gradio as gr
from pymongo import MongoClient

from . import js
from .settings import JOB_DIR, TITLE
from .request import build_session_url, build_job_url, passthrough_url, job_exists, request2session_and_job
from .job import update_submit_status, update_process_status, update_timer
from .web_interface import build_footer, build_header, tandem_output
from .web_interface import build_qa, build_licence, build_tutorial
from .logger import LOGGER

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

class ResultPage:
    def __init__(self, folder):
        self.folder = folder


    def build(self):
        self.timer = gr.Timer(value=1, active=False)

        self.session_id = gr.Textbox(value="", visible=False)
        self.job_name = gr.Textbox(value="", visible=False)
        self.session_url = gr.Textbox(value="", visible=False)
        self.error_url = gr.Textbox(value="", visible=False)
        self.job_folder = gr.Textbox(value="", visible=False)

        self.param_state = gr.State({})
        self.jobs_folder_state = gr.State(self.folder)
        with gr.Row(elem_classes="bg-row-column"):
            with gr.Column(scale=4):
                self.submit_status = gr.Textbox(label="Submission Status",lines=2,interactive=False,elem_classes="gr-textbox",autoscroll=False,)
            with gr.Column(scale=4):
                self.process_status = gr.Textbox(label="Processing Status",lines=2,interactive=False,elem_classes="gr-textbox",autoscroll=False,)
            with gr.Column(scale=2, elem_classes="results-side-panel"):
                self.session_box = gr.HTML()
                self.job_dropdown = gr.HTML()
                self.new_job_btn = gr.HTML()
        (self.output_section, self.inf_output_secion, self.tf_output_secion, self.pred_table, self.image_viewer, self.folds_state, self.fold_dropdown, self.sav_textbox, self.loss_image, self.test_evaluation, self.model_save, self.result_zip, self.focus_refresh_btn,
        ) = tandem_output()
        
        self._bind_events()
        return self

    def _bind_events(self):
        self.pred_table.select(self.on_select_sav, inputs=[self.pred_table, self.job_folder], outputs=[self.image_viewer])

        self.session_box.click(None, js=js.session_box) # Click = copy to clipboard

        self.focus_refresh_btn.click(fn=update_submit_status, inputs=[self.param_state], outputs=[self.submit_status],
        ).then(fn=update_process_status, inputs=[self.param_state, gr.State(True)], outputs=[self.process_status, self.param_state],
        ).then(fn=self.update_finished_job, inputs=[self.param_state, self.jobs_folder_state],
            outputs=[self.output_section,self.result_zip,self.inf_output_secion,self.pred_table,self.image_viewer,self.tf_output_secion,self.folds_state,self.fold_dropdown,self.sav_textbox,self.loss_image,self.test_evaluation,self.model_save,self.job_folder,],
        ).then(fn=self.update_timer, inputs=[self.param_state], outputs=[self.timer],
        )

        self.timer.tick(fn=update_process_status, inputs=[self.param_state, gr.State(True)], outputs=[self.process_status, self.param_state],
        ).then(fn=self.update_finished_job, inputs=[self.param_state, self.jobs_folder_state],
            outputs=[self.output_section, self.result_zip, self.inf_output_secion, self.pred_table, self.image_viewer, self.tf_output_secion, self.folds_state, self.fold_dropdown, self.sav_textbox, self.loss_image, self.test_evaluation, self.model_save, self.job_folder,],
        ).then(fn=self.update_timer,inputs=[self.param_state],outputs=[self.timer],
        )
    
    def update_timer(self, param):
        _job_status = param.get('status', None)
        if _job_status == "finished":
            timer_udt = gr.update(active=False)
        elif _job_status is None:
            timer_udt = gr.update(active=False)
        else:
            timer_udt = gr.update(active=True)
        return timer_udt
    
    def render_job_html(self, param):
        if not isinstance(param, dict):
            return ""

        session_id = param.get("session_id", "")
        current_job = param.get("job_name", "")

        if not session_id:
            return """
            <div class="job-row">
                <span class="job-label">Job:</span>
                <span class="job-name">-</span>
            </div>
            """

        job_names = collections.distinct(
            "job_name",
            {"session_id": session_id, "status": {"$in": ["pending", "processing", "finished"]}},
        )
        job_names = sorted(job_names)

        option_html = []
        for job_name in job_names:
            selected = " selected" if job_name == current_job else ""
            url = build_job_url(session_id, job_name)
            option_html.append(
                f'<option value="{html.escape(url, quote=True)}"{selected}>{html.escape(job_name)}</option>'
            )

        options = "\n".join(option_html) if option_html else '<option value="">No jobs</option>'

        return f"""
        <div class="job-row">
            <label class="job-label" for="job-select">Job:</label>
            <select id="job-select" class="example-select" onchange="if (this.value) window.location.assign(this.value);">
                {options}
            </select>
        </div>
        """
    
    def render_session_html(self, id):
        if isinstance(id, dict):
            id = id.get("session_id", "")

        return f"""
        <div class="session-row">
            <span class="session-label">Session:</span>
            <span class="session-id" id="session-id" style="padding:4px 6px; border-radius:4px;">{id}</span>
            <span style="font-size:12px; color:var(--body-text-color-subdued);">(click to copy)</span>
        </div>
        """

    def render_new_job_html(self, session_id):
        if isinstance(session_id, dict):
            session_id = session_id.get("session_id", "")

        if not session_id:
            return ""

        session_url = build_session_url(session_id)
        safe_url = html.escape(session_url, quote=True)
        return f"""
        <div class="new-job-row">
            <a class="mini-action-link" href="{safe_url}">New job</a>
        </div>
        """

    def on_select_sav(self, evt: gr.SelectData, df, job_folder):
        row_idx, col_idx = evt.index
        sav = df.iloc[row_idx]['SAV']
        shap_img = os.path.join(job_folder, "tandem_shap", f"{sav}.png")
        if os.path.exists(shap_img):
            return gr.update(value=shap_img)
        return gr.update(value=None)

    def on_sav_set_select(self, selection, folds):
        return folds[selection]

    def zip_folder(self, folder):
        folder = os.path.abspath(folder)
        base_dir = os.path.basename(folder)
        root_dir = os.path.dirname(folder)

        temp_base_name = os.path.join(root_dir, base_dir) # 1️⃣ Create zip NEXT TO the folder (safe)
        temp_zip_path = temp_base_name + ".zip"
        final_zip_path = os.path.join(folder, "result.zip") # 2️⃣ Move zip INTO the folder

        if not os.path.exists(final_zip_path):
            shutil.make_archive(base_name=temp_base_name, format="zip", root_dir=root_dir, base_dir=base_dir)
            shutil.move(temp_zip_path, final_zip_path)
        return final_zip_path

    def on_select_image(self, image_name, folder, param):
        if not image_name:
            return gr.update(visible=False)

        path = os.path.join(
            folder, param["session_id"], param["job_name"], 'tandem_shap', image_name)
        return gr.update(value=path, visible=True)

    def render_finished_job(self, param, _mode, job_folder, _job_name):

        # ----------- defaults (IMPORTANT) -----------
        output_section_udt = gr.update(visible=True)
        result_zip_udt = gr.update(value=None, interactive=False, visible=False)

        inf_output_secion_udt = gr.update(visible=False)
        pred_table_udt = gr.update(visible=False)
        image_viewer_udt = gr.update(visible=False)

        tf_output_secion_udt = gr.update(visible=False)
        folds_state_udt = None
        fold_dropdown_udt = gr.update()
        SAV_textbox_udt = gr.update()
        loss_image_udt = gr.update()
        test_eval_udt = gr.update()
        model_saved_udt = gr.update()
        job_folder_udt = job_folder

        # ----------- common outputs -----------
        zip_path = self.zip_folder(job_folder)
        result_zip_udt = gr.update(value=zip_path, interactive=True, visible=bool(zip_path))

        # ----------- Inferencing mode -----------
        if _mode == "Inferencing":
            inf_output_secion_udt = gr.update(visible=True)

            pred_file = os.path.join(job_folder, "Main_Predictions.csv")
            df_pred = pd.read_csv(pred_file)

            # Change column name TANDEM-DIMPLE to model
            model = param.get("model", 'TANDEM')
            if "TANDEM-DIMPLE" in df_pred.columns:
                df_pred = df_pred.rename(columns={"TANDEM-DIMPLE": model})

            # ---- Add index column FIRST ----
            df_pred = df_pred.reset_index(drop=True)
            df_pred.insert(0, "#", df_pred.index + 1)

            # ---- Send to Gradio ----
            pred_table_udt = gr.update(value=df_pred, visible=True)

            tandem_shap = os.path.join(job_folder, "tandem_shap")
            list_images = os.listdir(tandem_shap) if os.path.isdir(tandem_shap) else []

            first_image = os.path.join(tandem_shap, list_images[0]) if list_images else None
            image_viewer_udt = gr.update(value=first_image, visible=bool(list_images))
        # ----------- Transfer Learning mode -----------
        elif _mode == "Transfer Learning":
            tf_output_secion_udt = gr.update(visible=True)

            folds_path = os.path.join(job_folder, "cross_validation_SAVs.json")
            with open(folds_path) as f:
                folds = json.load(f)

            folds_state_udt = {}
            folds_state_udt['Test set'] = folds["1"]['test']
            for fold_id in sorted(k for k in folds.keys() if k != "test"):
                fold_num = fold_id.replace("fold_", "")
                folds_state_udt[f"Fold {fold_num} - Training set"] = folds[str(fold_num)]['train']
                folds_state_udt[f"Fold {fold_num} - Validation set"] = folds[str(fold_num)]['val']
            choices = folds_state_udt.keys()

            fold_dropdown_udt = gr.update(choices=choices, value='Test set', visible=True)
            SAV_textbox_udt = gr.update(value=folds_state_udt['Test set'], visible=True)

            loss_img = os.path.join(job_folder, "loss.png")
            loss_image_udt = gr.update(value=loss_img, visible=os.path.exists(loss_img))

            test_eval = os.path.join(job_folder, "test_evaluation.csv")
            df_test_eval = pd.read_csv(test_eval)
            test_eval_udt = gr.update(value=df_test_eval, visible=True)
            model_saved_udt = gr.update(value=f"Your models have been saved under name '{_job_name}'!", visible=True)
        return (
            output_section_udt,
            result_zip_udt,

            inf_output_secion_udt,
            pred_table_udt,
            image_viewer_udt,

            tf_output_secion_udt,
            folds_state_udt,
            
            fold_dropdown_udt,
            SAV_textbox_udt,

            loss_image_udt,
            test_eval_udt,
            model_saved_udt,
            job_folder_udt
        )

    def update_finished_job(self, param, folder):
        """
        Handle output-related UI updates:
        - output section visibility
        - prediction table
        - images
        - training / evaluation artifacts
        """
        _session_id = param.get("session_id")
        _job_status = param.get("status")
        _job_name   = param.get("job_name")
        _mode       = param.get("mode")
        # Defaults: hide everything
        def hide_all(n):
            return [gr.update(visible=False) for _ in range(n)]

        if _job_status == "finished":
            job_folder = os.path.join(folder, _session_id, _job_name)
            return self.render_finished_job(param, _mode, job_folder, _job_name)
        else:
            return hide_all(13)

    def update_submit_status(self, param):
        _session_id = param.get("session_id")
        _job_status = param.get("status", None)

        if _session_id is None or _job_status is None:
            submit_status_udt  = gr.update()
        else:
            msg = ""
            for k in ["SAV", "label", "model", "STR"]:
                v = param.get(k, None)
                if v is not None:
                    msg += f"{k}: {v}"
                    if k != "STR":
                        msg += '\n'
            
            submit_status_udt  = gr.update(value=msg, visible=True, lines=2)
        return submit_status_udt

def _load_result_param(session_id, job_name):
    doc = collections.find_one({"session_id": session_id, "job_name": job_name}, {"_id": 0})
    new_job_btn = gr.update(visible=False) if session_id == "test" else gr.update(visible=True)
    return doc, new_job_btn

def results_page():
    with gr.Blocks(title=TITLE) as page:
        build_header(TITLE, current_page="home")
        with gr.Column(elem_id="main-content"):
            ui = ResultPage(JOB_DIR).build()
        build_footer()

        page.load(fn=request2session_and_job, inputs=None, outputs=[ui.session_id, ui.job_name], queue=False,
        ).then(fn=job_exists, inputs=[ui.session_id, ui.job_name], outputs=[ui.error_url], queue=False,
        ).then(fn=passthrough_url, inputs=[ui.error_url], outputs=[ui.error_url], js=js.direct2url_refresh, queue=False,
        ).then(fn=_load_result_param, inputs=[ui.session_id, ui.job_name], outputs=[ui.param_state, ui.new_job_btn], queue=False,
        ).then(fn=ui.update_submit_status, inputs=[ui.param_state], outputs=[ui.submit_status], queue=False,
        ).then(fn=update_process_status, inputs=[ui.param_state, gr.State(False)], outputs=[ui.process_status, ui.param_state], queue=False,
        ).then(fn=ui.render_session_html, inputs=[ui.param_state], outputs=[ui.session_box]
        ).then(fn=ui.render_new_job_html, inputs=[ui.param_state], outputs=[ui.new_job_btn]
        ).then(fn=ui.render_job_html, inputs=[ui.param_state], outputs=[ui.job_dropdown]
        ).then(fn=ui.update_finished_job,inputs=[ui.param_state, ui.jobs_folder_state],# queue=False,
            outputs=[ui.output_section, ui.result_zip, ui.inf_output_secion, ui.pred_table, ui.image_viewer, ui.tf_output_secion, ui.folds_state, ui.fold_dropdown, ui.sav_textbox, ui.loss_image, ui.test_evaluation, ui.model_save, ui.job_folder,],
        ).then(fn=update_timer, inputs=[ui.param_state], outputs=[ui.timer], queue=False,
        )

    return page


if __name__ == "__main__":
    pass
