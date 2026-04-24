import os
import shutil
import json
import html
import time
import pandas as pd 
import gradio as gr
from pymongo import MongoClient

from . import js
from .components.process_status import build_process_status_html
from .components.topbar import build_topbar_html
from .settings import JOB_DIR, TITLE, HTML_DIR
from .request import build_session_url, passthrough_url, job_exists, request2result_payload
from .base import build_footer, build_header
from .logger import LOGGER
from .settings import EXAMPLES_JSON

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

with open(EXAMPLES_JSON, "r", encoding="utf-8") as f:
    EXAMPLES = json.load(f)

class ResultPage:
    """Container for results UI and callbacks."""
    def __init__(self, folder):
        self.folder = folder

    def update_timer(self, job_status):
        """Enable or disable the refresh timer based on job status."""
        decide = False if job_status == 'finished' else True
        return gr.update(active=decide)

    def build(self):
        """Create UI components and layout."""
        self.timer = gr.Timer(value=10, active=False)
        self.session_id = gr.Textbox(value="", visible=False)
        self.job_name = gr.Textbox(value="", visible=False)
        self.job_status = gr.Textbox(value="", visible=False)
        self.mode = gr.Textbox(value="", visible=False)

        self.launch_session_id = gr.Textbox(value="", visible=False)
        self.example_name = gr.Textbox(value="", visible=False)
        self.example_action = gr.Textbox(value="", visible=False)
        self.session_url = gr.Textbox(value="", visible=False)
        self.error_url = gr.Textbox(value="", visible=False)
        self.job_folder = gr.Textbox(value="", visible=False)

        self.param_state = gr.State({})
        self.userlog = gr.State({})
        self.jobs_folder_state = gr.State(self.folder)
        self.cancel_job_btn = gr.Button("Cancel current job", elem_id="cancel_job_btn", elem_classes="visually-hidden-action")
        self.cancel_url = gr.Textbox(value="", visible=False)
        with gr.Row(elem_classes="results-status-layout"):
            with gr.Column(scale=3, elem_classes="results-status-left"):
                self.process_status = gr.HTML(elem_classes="results-userlog")
            with gr.Column(scale=2, elem_classes="results-status-right"):
                self.top_bar = gr.HTML(elem_classes="results-top-row")
        
        with gr.Group(visible=False) as self.output_section:
            self.results_heading = gr.HTML()

            with gr.Group(visible=False) as self.inf_output_secion:
                with gr.Row():
                    with gr.Column():
                        self.pred_table = gr.Dataframe(interactive=False,max_height=340,show_label=False,column_widths=[60, 150, "auto", "auto"],)
                    with gr.Column():
                        self.image_viewer = gr.Image(height=340, show_label=False, buttons=["fullscreen"])

            with gr.Group(visible=False) as self.tf_output_secion:
                with gr.Row():
                    with gr.Column():
                        self.folds_state = gr.State(value={})
                        self.fold_dropdown = gr.Dropdown(label="View SAV set", choices=[], interactive=True, elem_classes="gr-button", elem_id="sav_dropdown", show_label=False,)
                        self.sav_textbox = gr.Textbox(lines=1,interactive=False,show_label=False,elem_classes="gr-textbox",elem_id="sav_textbox",autoscroll=False,)
                        self.test_evaluation = gr.Dataframe(interactive=False, max_height=250, show_label=False)
                    self.loss_image = gr.Image(label="", show_label=False, height=364, buttons=["fullscreen"])
                self.model_save = gr.Markdown(elem_classes="gr-p")

            self.result_zip = gr.File(label="Download Results")
            self.focus_refresh_btn = gr.Button(elem_id="focus_refresh_btn", visible=False)
            gr.HTML(js.focus_refresh)

        self._bind_events()
        return self

    def render_results_heading(self, mode):
        """Render the results heading with a mode-specific tooltip.
        Input: mode: job mode, e.g. 'Inferencing' or 'Training'.
        Output: HTML string for the Results title and help tooltip.
        """
        filepath = os.path.join(HTML_DIR, "results_help.html")
        inferencing_text = (
            "Pathogenicity prediction estimates how likely a SAV is to be harmful. "
            "SHAP analysis explains which features most influenced the prediction, "
            "helping users understand the possible biological drivers of pathogenicity."
        )
        training_text = (
            "The results compare the gene-specific TANDEM-DIMPLE model with the "
            "gene-general TANDEM model on the test set (to evaluate whether transfer "
            "learning provides performance improvement for individual genes). The loss "
            "curves help assess convergence and possible overfitting during training, "
            "(where training is stopped when the validation loss no longer declines "
            "over 50 epochs). These outputs provide users with convenient guidance on "
            "whether to confidently take the transfer-learning model."
        )
        help_text = training_text if mode == "Training" else inferencing_text
        return js.build_html_text(filepath,tooltip_id="results-help-note",help_text=html.escape(help_text),)

    def _bind_events(self):
        """Wire UI events to callbacks."""
        self.pred_table.select(self.on_select_sav, inputs=[self.pred_table, self.job_folder], outputs=[self.image_viewer])

        self.cancel_job_btn.click(fn=self.cancel_job, inputs=[self.param_state, self.jobs_folder_state, self.session_id, self.job_name, self.job_status], outputs=[self.param_state, self.timer, self.cancel_url], queue=False, 
        ).then(fn=passthrough_url, inputs=[self.cancel_url], outputs=[self.cancel_url], js=js.direct2url_refresh, queue=False,
        )

        self.focus_refresh_btn.click(fn=self.__update__, inputs=[self.param_state, self.job_folder, self.userlog, gr.State(True)], outputs=[self.param_state, self.userlog, self.session_id, self.job_name, self.job_status, self.mode],
        ).then(fn=build_topbar_html, inputs=[self.param_state, self.session_id, self.job_name, self.job_status], outputs=[self.top_bar],
        ).then(fn=self.update_process_status, inputs=[self.param_state, self.userlog, self.session_id, self.job_name, self.job_status, self.mode], outputs=[self.process_status],
        ).then(fn=self.update_finished_job, inputs=[self.param_state, self.jobs_folder_state, self.userlog],
            outputs=[self.output_section,self.results_heading,self.result_zip,self.inf_output_secion,self.pred_table,self.image_viewer,self.tf_output_secion,self.folds_state,self.fold_dropdown,self.sav_textbox,self.loss_image,self.test_evaluation,self.model_save,self.job_folder,],
        ).then(fn=self.update_timer, inputs=[self.job_status], outputs=[self.timer],
        )

        self.timer.tick(fn=self.__update__,inputs=[self.param_state, self.job_folder, self.userlog, gr.State(True)],outputs=[self.param_state, self.userlog, self.session_id, self.job_name, self.job_status, self.mode],
        ).then(fn=build_topbar_html, inputs=[self.param_state, self.session_id, self.job_name, self.job_status], outputs=[self.top_bar],
        ).then(fn=self.update_process_status, inputs=[self.param_state, self.userlog, self.session_id, self.job_name, self.job_status, self.mode], outputs=[self.process_status],
        ).then(fn=self.update_finished_job, inputs=[self.param_state, self.jobs_folder_state, self.userlog],
            outputs=[self.output_section, self.results_heading, self.result_zip, self.inf_output_secion, self.pred_table, self.image_viewer, self.tf_output_secion, self.folds_state, self.fold_dropdown, self.sav_textbox, self.loss_image, self.test_evaluation, self.model_save, self.job_folder,],
        ).then(fn=self.update_timer,inputs=[self.job_status],outputs=[self.timer],
        )

        self.fold_dropdown.change(fn=self.on_select_sav_set, inputs=[self.fold_dropdown, self.folds_state], outputs=self.sav_textbox)
    
    def __update__(self, param, job_folder, userlog, search_db: bool):
        """Update param_state, userlog, and other simple variables.
        If the job hits an error, we mark the job as finished in MongoDB and update the local job_status_udt.
        
        Argument
        --------
        param: current job metadata (dict) from param_state.
        job_folder: folder path for the job (used to read user_log.jsonl).
        userlog: cached userlog state (used for mtime cache).
        search_db: boolean flag to refresh param from MongoDB.
        """
        param_udt = param.copy() if isinstance(param, dict) else param
        if search_db and isinstance(param_udt, dict):
            session_id = param_udt.get("session_id")
            job_name = param_udt.get("job_name")
            if session_id and job_name:
                # Find job
                updated = collections.find_one({"session_id": session_id, "job_name": job_name}, {"_id": 0},)
                if updated:
                    param_udt = updated
        userlog_udt = self.update_userlog(job_folder, userlog)
        session_id_udt = ""
        job_name_udt = ""
        job_status_udt = ""
        mode_udt = ""
        if isinstance(param_udt, dict):
            session_id_udt = param_udt.get("session_id", "")
            job_name_udt = param_udt.get("job_name", "")
            job_status_udt = param_udt.get("status", "")
            mode_udt = param_udt.get("mode", "")
            # Mark the job as finished in MongoDB.
            last_event = None
            if isinstance(userlog_udt, dict):
                events = userlog_udt.get("events", [])
                last_event = events[-1] if events else last_event
            last_event_level = str((last_event or {}).get("level", "")).lower()
            if last_event_level == "error":
                job_status_udt = "finished"
                if session_id_udt and job_name_udt:
                    now = time.time()
                    collections.update_one(
                        {"session_id": session_id_udt, "job_name": job_name_udt},
                        {"$set": {"status": "finished", "job_end": now}},
                    )
        return param_udt, userlog_udt, session_id_udt, job_name_udt, job_status_udt, mode_udt
    
    def update_userlog(self, job_folder, userlog):
        """Refresh cached user-log state (mtime-aware).
        
        Inputs:
        - job_folder: path to the job directory that contains user_log.jsonl.
        - userlog: previous cached state dict (used to skip re-reading if unchanged).

        Output: A dict with:
          - mtime: last modified time of user_log.jsonl
          - events: parsed list of log events (dicts)
          - history: formatted multi-line HTML-ready message string
        """
        if not job_folder:
            return userlog or {}

        userlog_path = os.path.join(job_folder, "user_log.jsonl")
        if not os.path.exists(userlog_path):
            return {}

        mtime = os.path.getmtime(userlog_path)
        if isinstance(userlog, dict) and userlog.get("mtime") == mtime:
            return userlog

        events = []
        with open(userlog_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return {"mtime": mtime, "events": events}

    def update_process_status(self, param, userlog, session_id, job_name, job_status, mode):
        """Refresh the status panel using cached user-log data."""
        process_status_udt = gr.update()
        param_udt = param.copy() if isinstance(param, dict) else {}
        session_id = session_id or param_udt.get("session_id", "")
        job_name = job_name or param_udt.get("job_name", "")
        job_status = job_status or param_udt.get("status", "")
        mode = mode or param_udt.get("mode", "")

        if not session_id or not job_name or not param_udt:
            return process_status_udt

        process_status_html = build_process_status_html(param_udt, userlog, session_id, job_name, job_status)
        process_status_udt = gr.update(value=process_status_html, visible=True)
        return process_status_udt

    def cancel_job(self, param, folder, session_id, job_name, job_status):
        """Cancel the active job and prepare redirect state.

        Inputs:
        - param: current job metadata dict.
        - folder: jobs root folder.
        - session_id: current session id string.
        - job_name: current job name string.
        - job_status: current job status string.

        Output:
        - param_udt: updated param state after cancellation.
        - timer_udt: timer update to stop polling.
        - cancel_url_udt: URL used for redirect back to the session page.
        """
        param_udt = param.copy() if isinstance(param, dict) else {}
        session_id = session_id or param_udt.get("session_id", "")
        job_name = job_name or param_udt.get("job_name", "")
        job_status = job_status or param_udt.get("status", "")
        timer_udt = gr.update(active=False)
        cancel_url_udt = ""

        if not session_id or not job_name or not param_udt:
            return param_udt, timer_udt, cancel_url_udt

        if session_id == "test":
            gr.Warning("Demo jobs cannot be cancelled.")
            return param_udt, timer_udt, cancel_url_udt

        if job_status not in {"pending", "processing"}:
            gr.Warning("Only pending or processing jobs can be cancelled from the website.")
            return param_udt, timer_udt, cancel_url_udt

        try:
            collections.delete_one({"session_id": session_id, "job_name": job_name})
            job_dir = os.path.join(folder, session_id, job_name)
            if os.path.exists(job_dir):
                shutil.rmtree(job_dir)

            param_udt = {}
            if job_status == "processing":
                value = (
                    f"Removed {job_name} from the website and database. "
                    "If tandem has already started running it, that backend execution may continue briefly."
                )
            else:
                value = f"Cancelled {job_name}. Redirecting back to the session page ..."
            gr.Warning(value)
            cancel_url_udt = build_session_url(session_id)
            LOGGER.info(f"Cancelled job {session_id}/{job_name} from results page")
            return param_udt, timer_udt, cancel_url_udt
        except Exception:
            gr.Warning(f"Failed to cancel job {session_id}/{job_name}")
            return param_udt, timer_udt, cancel_url_udt

    def on_select_sav(self, evt: gr.SelectData, df, job_folder):
        """Update the SHAP image for the selected SAV row."""
        row_idx, col_idx = evt.index
        sav = df.iloc[row_idx]['SAV']
        shap_img = os.path.join(job_folder, "tandem_shap", f"{sav}.png")
        if os.path.exists(shap_img):
            return gr.update(value=shap_img)
        return gr.update(value=None)

    def on_select_sav_set(self, selection, folds):
        """Update the SAV list for the selected fold."""
        return folds[selection]

    def zip_folder(self, folder):
        """Create a zip archive for download."""
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

    def update_finished_job(self, param, folder, userlog):
        """Load and render result artifacts when a job finishes."""
        _session_id = param.get("session_id")
        _job_status = param.get("status")
        _job_name = param.get("job_name")
        _mode = param.get("mode")

        last_event = None
        if isinstance(userlog, dict):
            events = userlog.get("events", [])
            last_event = events[-1] if events else last_event
        last_event_level = str((last_event or {}).get("level", "")).lower()
            
        # ----------- defaults (IMPORTANT) -----------
        if _job_status != "finished" or last_event_level == "error":
            return [gr.update(visible=False) for _ in range(14)]

        job_folder = os.path.join(folder, _session_id, _job_name)

        output_section_udt = gr.update(visible=True)
        results_heading_udt = gr.update(value=self.render_results_heading(_mode), visible=True)
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

            pred_file = os.path.join(job_folder, "Main_Predictions.txt")
            df_pred = pd.read_csv(pred_file)

            # Change column name TANDEM-DIMPLE to model
            model = param.get("model", 'TANDEM')
            if "TANDEM-DIMPLE" in df_pred.columns:
                df_pred = df_pred.rename(columns={"TANDEM-DIMPLE": model})

            prediction_cols = [col for col in df_pred.columns if col != "SAV"]
            if prediction_cols:
                predicted_mask = df_pred[prediction_cols].apply(
                    lambda row: any(str(value).strip() != "Not available" for value in row),
                    axis=1,
                )
                df_pred = df_pred[predicted_mask].copy()

            # ---- Add index column FIRST ----
            df_pred = df_pred.reset_index(drop=True)
            df_pred.insert(0, "#", df_pred.index + 1)

            # ---- Send to Gradio ----
            pred_table_udt = gr.update(value=df_pred, visible=not df_pred.empty)

            tandem_shap = os.path.join(job_folder, "tandem_shap")
            predicted_savs = set(df_pred["SAV"].tolist()) if not df_pred.empty else set()
            list_images = []
            if os.path.isdir(tandem_shap):
                for image_name in sorted(os.listdir(tandem_shap)):
                    sav_name, ext = os.path.splitext(image_name)
                    if sav_name in predicted_savs:
                        list_images.append(image_name)

            first_image = os.path.join(tandem_shap, list_images[0]) if list_images else None
            image_viewer_udt = gr.update(value=first_image, visible=bool(list_images))
        # ----------- Transfer Learning mode -----------
        elif _mode == "Training":
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

            test_eval = os.path.join(job_folder, "test_evaluation.txt")
            df_test_eval = pd.read_csv(test_eval)
            test_eval_udt = gr.update(value=df_test_eval, visible=True)
            model_saved_udt = gr.update(value=f"Your models have been saved under name '{_job_name}'!", visible=True)
        return (
            output_section_udt, results_heading_udt, result_zip_udt, inf_output_secion_udt, pred_table_udt, image_viewer_udt,
            tf_output_secion_udt, folds_state_udt, fold_dropdown_udt, SAV_textbox_udt,
            loss_image_udt, test_eval_udt, model_saved_udt, job_folder_udt
        )

    def search_param(self, session_id, job_name):
        """Fetch a job record and compute the job folder path."""
        param = collections.find_one({"session_id": session_id, "job_name": job_name}, {"_id": 0})
        job_folder = os.path.join(JOB_DIR, session_id, job_name)
        return param, job_folder

def resolve_result_request(session_id, job_name, example_name, example_action):
    """Resolve example links into session/job identifiers.

    Inputs:
    - session_id: requested session id.
    - job_name: requested job name.
    - example_name: example label from the URL payload.
    - example_action: example action from the URL payload.

    Output:
    - Resolved session_id, job_name, and launch_session_id.
    """
    if job_name:
        return session_id, job_name, ""

    if example_action != "view_output" or not example_name:
        return session_id, job_name, ""

    ex = EXAMPLES.get(example_name, "")
    if ex == "":
        return session_id, job_name, ""

    return ex.get("session_id", ""), ex.get("job_name", ""), session_id

def results_page():
    """Build the full Gradio results page and initial load chain.

    Output:
    - A Gradio Blocks page for the mounted results route.
    """
    with gr.Blocks(title=TITLE) as page:
        build_header(TITLE, current_page="home")
        with gr.Column(elem_id="main-content"):
            ui = ResultPage(JOB_DIR).build()
        build_footer()

        page.load(fn=request2result_payload, inputs=None, outputs=[ui.session_id, ui.job_name, ui.example_name, ui.example_action], queue=False,
        ).then(fn=resolve_result_request, inputs=[ui.session_id, ui.job_name, ui.example_name, ui.example_action], outputs=[ui.session_id, ui.job_name, ui.launch_session_id], queue=False,
        ).then(fn=job_exists, inputs=[ui.session_id, ui.job_name], outputs=[ui.error_url], queue=False,
        ).then(fn=passthrough_url, inputs=[ui.error_url], outputs=[ui.error_url], js=js.direct2url_refresh, queue=False,
        ).then(fn=ui.search_param, inputs=[ui.session_id, ui.job_name], outputs=[ui.param_state, ui.job_folder], queue=False,
        ).then(fn=lambda param, launch_session_id: ({**param, "launch_session_id": launch_session_id} if param else param), inputs=[ui.param_state, ui.launch_session_id], outputs=[ui.param_state], queue=False,
        ).then(fn=ui.__update__, inputs=[ui.param_state, ui.job_folder, ui.userlog, gr.State(False)], outputs=[ui.param_state, ui.userlog, ui.session_id, ui.job_name, ui.job_status, ui.mode], queue=False,
        ).then(fn=build_topbar_html, inputs=[ui.param_state, ui.session_id, ui.job_name, ui.job_status], outputs=[ui.top_bar], queue=False,
        ).then(fn=ui.update_process_status, inputs=[ui.param_state, ui.userlog, ui.session_id, ui.job_name, ui.job_status, ui.mode], outputs=[ui.process_status], queue=False,
        ).then(fn=ui.update_finished_job,inputs=[ui.param_state, ui.jobs_folder_state, ui.userlog],
            outputs=[ui.output_section, ui.results_heading, ui.result_zip, ui.inf_output_secion, ui.pred_table, ui.image_viewer, ui.tf_output_secion, ui.folds_state, ui.fold_dropdown, ui.sav_textbox, ui.loss_image, ui.test_evaluation, ui.model_save, ui.job_folder,],
        ).then(fn=ui.update_timer, inputs=[ui.job_status], outputs=[ui.timer], queue=False,
        )

    return page


if __name__ == "__main__":
    pass
