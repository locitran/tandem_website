import gradio as gr

from .web_interface import session, tandem_input, tandem_output, left_column, on_auto_view
from .web_interface import render_job_html, render_session_html
from .update_session import on_session
from .update_input import update_input_param
from .job import on_job, on_reset, send_job, update_sections, update_timer
from .job import update_process_status, update_submit_status, _prepare_back_sav, _prepare_back_str
from .update_output import update_finished_job, on_select_sav

class HomeTab:
    def __init__(self, folder):
        self.folder = folder

    def build(self):
        self.timer = gr.Timer(value=1, active=True) # Timer to check result
        self.job_folder = gr.State()

        with gr.Row() as self.input_page:
            with gr.Column(scale=1):
                left_column()
            with gr.Column(scale=1):
                self.param_state = gr.State({})
                self.jobs_folder_state = gr.State(self.folder)

                # Session UI
                (
                    self.session_id,
                    self.session_btn,
                    self.session_mkd,
                    self.session_status,
                    self.job_dropdown,
                ) = session()
                
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

        ##### Result page
        with gr.Group(visible=False) as self.output_page:    
            with gr.Row(elem_classes="bg-row-column"):
                with gr.Column(scale=4):
                    self.submit_status = gr.Textbox(label="Submission Status", lines=2, interactive=False, elem_classes="gr-textbox", autoscroll=False)
                with gr.Column(scale=4):
                    self.process_status = gr.Textbox(label="Processing Status", lines=2, interactive=False, elem_classes="gr-textbox", autoscroll=False)
                with gr.Column(scale=2):
                    self.session_box = gr.HTML(render_session_html(self.session_id))
                    self.job_box = gr.HTML(render_job_html(self.job_name_txt))
                    with gr.Row():
                        self.back_btn = gr.Button(elem_id="going_back_btn")
                        
                        gr.HTML("""
                        <button class="going-back-btn"
                            onclick="document.getElementById('going_back_btn').click()">
                            ← Going back
                        </button>
                        """)
                
            # Result UI
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
            self.reset_btn = gr.Button("New job", elem_classes="gr-button")

        self._bind_events()
        return self

    def _bind_events(self):
        session_box_js = """
        () => {
            const el = document.getElementById("session-id");
            if (!el) return;

            const text = el.innerText.trim();
            navigator.clipboard.writeText(text);

            // Optional visual feedback
            el.style.background = "#d1fae5";
            setTimeout(() => {el.style.background = "";}, 600);
        }
        """
        self.session_box.click(None, js=session_box_js) # Click = copy to clipboard
        self.back_btn.click(outputs=[self.input_section, self.input_page, self.output_page, self.inf_section, self.tf_section, self.inf_sav_txt, self.tf_sav_txt, self.mode, self.job_name_txt, self.job_dropdown],
            fn=_prepare_back_sav, inputs=[self.param_state],
        ).then(fn=_prepare_back_str, inputs=[self.param_state], outputs=[self.structure_section, self.str_check, self.str_txt, self.str_btn, self.str_file],
        )

        # Stop timer after reset
        self.reset_btn.click(fn=lambda: gr.update(active=False), inputs=[], outputs=self.timer
        ).then(fn=on_reset, inputs=[self.param_state], 
            outputs=[self.input_page, self.param_state, self.job_dropdown, self.input_section, self.output_page, self.inf_sav_txt, self.inf_sav_btn, self.inf_sav_file, self.tf_sav_txt, self.tf_sav_btn, self.tf_sav_file, self.str_txt, self.str_btn, self.str_file, self.job_name_txt, self.email_txt])
        
        ################-------------Simulate session event----------------################ 
        # Generate/resume session
        session_click_event = self.session_btn.click(fn=on_session, inputs=[self.session_id, self.param_state], outputs=[self.session_id, self.session_btn, self.session_mkd, self.session_status, self.job_dropdown, self.param_state, self.model_dropdown])
        session_submit_event = self.session_id.submit(fn=on_session, inputs=[self.session_id, self.param_state], outputs=[self.session_id, self.session_btn, self.session_mkd, self.session_status, self.job_dropdown, self.param_state, self.model_dropdown])

        # Visualize input section
        session_event = [session_click_event, session_submit_event]
        for i, event in enumerate(session_event):
            session_event[i] = event.then(
                   fn=update_sections, inputs=[self.param_state], outputs=[self.input_section, self.input_page, self.output_page]
            ).then(fn=update_submit_status, inputs=[self.param_state], outputs=[self.submit_status]
            ).then(fn=update_process_status, inputs=[self.param_state, gr.State(False)], outputs=[self.process_status, self.param_state]
            ).then(fn=update_timer, inputs=[self.param_state], outputs=[self.timer]
            ).then(fn=update_finished_job, inputs=[self.param_state, self.jobs_folder_state],
                outputs=[self.output_section, self.result_zip, self.inf_output_secion, self.pred_table, self.image_viewer, self.tf_output_secion, self.folds_state, self.fold_dropdown, self.sav_textbox, self.loss_image, self.test_evaluation, self.model_save, self.job_folder]
            ).then(fn=render_session_html, inputs=[self.param_state], outputs=[self.session_box]
            ).then(fn=render_job_html, inputs=[self.param_state], outputs=[self.job_box]
            )
            
        #############---input_section following job selection--------################
        self.job_dropdown.select(
               fn=on_job, inputs=[self.job_dropdown, self.param_state], outputs=[self.param_state]
        ).then(fn=update_sections, inputs=[self.param_state], outputs=[self.input_section, self.input_page, self.output_page]
        ).then(fn=update_submit_status, inputs=[self.param_state], outputs=[self.submit_status]
        ).then(fn=update_process_status, inputs=[self.param_state, gr.State(False)], outputs=[self.process_status, self.param_state]
        ).then(fn=update_timer, inputs=[self.param_state], outputs=[self.timer]
        ).then(fn=update_finished_job, inputs=[self.param_state, self.jobs_folder_state],
            outputs=[self.output_section, self.result_zip, self.inf_output_secion, self.pred_table, self.image_viewer, self.tf_output_secion, self.folds_state, self.fold_dropdown, self.sav_textbox, self.loss_image, self.test_evaluation, self.model_save, self.job_folder]
        ).then(fn=render_session_html, inputs=[self.param_state], outputs=[self.session_box]
        ).then(fn=render_job_html, inputs=[self.param_state], outputs=[self.job_box]
        )

        ###############---input_section following job selection--------################
        self.submit_btn.click(inputs=[self.mode, self.inf_sav_txt, self.inf_sav_file, self.model_dropdown, self.tf_sav_txt, self.tf_sav_file, self.str_txt, self.str_file, self.job_name_txt, self.email_txt, self.param_state],
               fn=update_input_param, outputs=[self.param_state, self.input_section, self.reset_btn, self.timer],
        ).then(fn=send_job, inputs=[self.param_state, self.jobs_folder_state], outputs=[self.param_state],
        ).then(fn=update_sections, inputs=[self.param_state], outputs=[self.input_section, self.input_page, self.output_page]
        ).then(fn=update_submit_status, inputs=[self.param_state], outputs=[self.submit_status]
        ).then(fn=update_process_status, inputs=[self.param_state, gr.State(False)], outputs=[self.process_status, self.param_state]
        ).then(fn=update_timer, inputs=[self.param_state], outputs=[self.timer]
        ).then(fn=render_session_html, inputs=[self.param_state], outputs=[self.session_box]
        ).then(fn=render_job_html, inputs=[self.param_state], outputs=[self.job_box]
        )

        # ###############--------Timer, report job status---------################
        self.timer.tick(fn=update_process_status, inputs=[self.param_state, gr.State(True)], outputs=[self.process_status, self.param_state]
        ).then(fn=update_finished_job, inputs=[self.param_state, self.jobs_folder_state],
            outputs=[self.output_section, self.result_zip, self.inf_output_secion, self.pred_table, self.image_viewer, self.tf_output_secion, self.folds_state, self.fold_dropdown, self.sav_textbox, self.loss_image, self.test_evaluation, self.model_save, self.job_folder]
        ).then(fn=update_timer, inputs=[self.param_state], outputs=[self.timer])

        # -------- Focus catch-up refresh --------
        self.focus_refresh_btn.click(
            fn=update_submit_status, inputs=[self.param_state], outputs=[self.submit_status]
        ).then(fn=update_process_status, inputs=[self.param_state, gr.State(False)], outputs=[self.process_status, self.param_state]
        ).then(fn=update_timer, inputs=[self.param_state], outputs=[self.timer]
        ).then(fn=update_finished_job, inputs=[self.param_state, self.jobs_folder_state],
            outputs=[self.output_section, self.result_zip, self.inf_output_secion, self.pred_table, self.image_viewer, self.tf_output_secion, self.folds_state, self.fold_dropdown, self.sav_textbox, self.loss_image, self.test_evaluation, self.model_save, self.job_folder]
        ).then(fn=render_session_html, inputs=[self.param_state], outputs=[self.session_box]
        ).then(fn=render_job_html, inputs=[self.param_state], outputs=[self.job_box]
        )

        # ###############--------View output examples---------################
        # Store test parameters 
        self.test_param_state = gr.State({})
        self.inf_auto_view.click(fn=on_auto_view, inputs=[self.mode, self.jobs_folder_state, self.param_state], outputs=[self.test_param_state, self.param_state]
        ).then(fn=update_sections, inputs=[self.test_param_state], outputs=[self.input_section, self.input_page, self.output_page]
        ).then(fn=update_submit_status, inputs=[self.test_param_state], outputs=[self.submit_status]
        ).then(fn=update_process_status, inputs=[self.test_param_state, gr.State(False)], outputs=[self.process_status, self.test_param_state]
        ).then(fn=update_finished_job, inputs=[self.test_param_state, self.jobs_folder_state],
            outputs=[self.output_section, self.result_zip, self.inf_output_secion, self.pred_table, self.image_viewer, self.tf_output_secion, self.folds_state, self.fold_dropdown, self.sav_textbox, self.loss_image, self.test_evaluation, self.model_save, self.job_folder]
        ).then(fn=render_session_html, inputs=[self.param_state], outputs=[self.session_box]
        ).then(fn=render_job_html, inputs=[self.param_state], outputs=[self.job_box]
        )
        
        self.tf_auto_view.click(fn=on_auto_view, inputs=[self.mode, self.jobs_folder_state, self.param_state], outputs=[self.test_param_state, self.param_state]
        ).then(fn=update_sections, inputs=[self.test_param_state], outputs=[self.input_section, self.input_page, self.output_page]
        ).then(fn=update_submit_status, inputs=[self.test_param_state], outputs=[self.submit_status]
        ).then(fn=update_process_status, inputs=[self.test_param_state, gr.State(False)], outputs=[self.process_status, self.test_param_state]
        ).then(fn=update_finished_job, inputs=[self.test_param_state, self.jobs_folder_state],
            outputs=[self.output_section, self.result_zip, self.inf_output_secion, self.pred_table, self.image_viewer, self.tf_output_secion, self.folds_state, self.fold_dropdown, self.sav_textbox, self.loss_image, self.test_evaluation, self.model_save, self.job_folder]
        ).then(fn=render_session_html, inputs=[self.param_state], outputs=[self.session_box]
        ).then(fn=render_job_html, inputs=[self.param_state], outputs=[self.job_box]
        )
        
        self.pred_table.select(on_select_sav, inputs=[self.pred_table, self.job_folder], outputs=[self.image_viewer])

if __name__ == "__main__":
    pass
