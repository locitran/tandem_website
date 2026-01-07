import os 
import sass 
import gradio as gr
from pymongo import MongoClient

from src.web_interface import session, tandem_input, tandem_output, build_header, left_column, build_footer
from src.update_session import on_session
from src.update_input import update_input_param
from src.job import on_submit, on_job, on_reset, send_job, check_status, update_sections, update_timer, update_process_status
from src.update_output import update_output_sections, on_select_image
from src.job_manager import manager_tab

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

MOUNT_POINT = '/TANDEM-Tsunami' # https://dyn.life.nthu.edu.tw/TANDEM-Tsunami

ROOT = os.path.dirname(os.path.dirname(__file__)) # ./tandem_website

TANDEM_DIR = os.path.join(ROOT, 'tandem')
GRADIO_DIR = os.path.join(ROOT, 'gradio_app')
TMP_DIR = os.path.join(GRADIO_DIR, 'tmp')
JOB_DIR = os.path.join(TANDEM_DIR, 'jobs')

SASS_DIR = os.path.join(GRADIO_DIR, "sass")
ASSETS_DIR = os.path.join(GRADIO_DIR, "assets")

figure_1 = os.path.join(ASSETS_DIR, 'images/figure_1.jpg')

sass.compile(dirname=(str(SASS_DIR), str(ASSETS_DIR)), output_style="expanded")
with open(os.path.join(ASSETS_DIR, "main.css")) as f:
    custom_css = f.read()

def right_column(folder):
    
    param_state = gr.State({})
    jobs_folder_state = gr.State(folder)

    # Session UI
    (
        session_id, 
        session_btn, 
        session_status, 
        job_dropdown

    ) = session()
    
    # Input UI
    (
        param_state,
        input_section,
        mode,
        inf_section,
        inf_sav_txt,
        inf_sav_file,
        model_dropdown,
        
        tf_section,
        tf_sav_txt,
        tf_sav_file,

        str_txt,
        str_file,

        job_name_txt,
        email_txt,

        submit_section,
        submit_status,
        process_status,
        submit_btn,
        reset_btn,

        timer,

    ) = tandem_input(param_state)

    # Result UI
    (
        output_section,
        inf_output_secion,
        tf_output_secion,

        pred_table,
        image_selector,
        image_viewer,

        folds_state,
        fold_dropdown,
        train_box,
        val_box,
        test_box,
        loss_image,
        test_evaluation,

        result_zip,

    ) = tandem_output()

    ################-------------Simulate session event----------------################
    # Generate/resume session
    session_click_event = session_btn.click(
        fn=on_session, inputs=[session_id, param_state],
        outputs=[session_id, session_btn, session_status, job_dropdown, param_state, model_dropdown]
    )
    session_submit_event = session_id.submit(
        fn=on_session, inputs=[session_id, param_state],
        outputs=[session_id, session_btn, session_status, job_dropdown, param_state, model_dropdown]
    )

    # Visualize input section
    session_event = [session_click_event, session_submit_event]
    for i, event in enumerate(session_event):
        session_event[i] = event.then(
            fn=update_sections, inputs=[param_state],
            outputs=[input_section, submit_section, submit_status, submit_btn,reset_btn,]
        ).then(
            fn=update_process_status, inputs=[param_state, gr.State(False)],
            outputs=[process_status, param_state]
        ).then(
            fn=update_output_sections, inputs=[param_state, jobs_folder_state],
            outputs=[
                output_section,
                result_zip,
                inf_output_secion,
                pred_table,
                image_selector,
                image_viewer,
                tf_output_secion,
                folds_state,
                fold_dropdown,
                train_box,
                val_box,
                test_box,
                loss_image,
                test_evaluation,
            ]
        ).then(
            fn=update_timer, inputs=[param_state], outputs=[timer]
        )
        
    ###############---input_section following job selection--------################
    job_dropdown.select(
        fn=on_job, inputs=[job_dropdown, param_state], outputs=[param_state]
    ).then(
        fn=update_sections, inputs=[param_state], 
        outputs=[input_section, submit_section, submit_status, submit_btn, reset_btn]
    ).then(
        fn=update_process_status, inputs=[param_state, gr.State(False)],
        outputs=[process_status, param_state]
    ).then(
        fn=update_output_sections, inputs=[param_state, jobs_folder_state],
        outputs=[
            output_section,
            result_zip,
            inf_output_secion,
            pred_table,
            image_selector,
            image_viewer,
            tf_output_secion,
            folds_state,
            fold_dropdown,
            train_box,
            val_box,
            test_box,
            loss_image,
            test_evaluation,
        ]
    ).then(
        fn=update_timer, inputs=[param_state], outputs=[timer]
    )

    ###############---input_section following job selection--------################
    submit_btn.click(
        fn=on_submit, 
        inputs=[], 
        outputs=[submit_status, submit_btn]
    ).then(
        fn=update_input_param,
        inputs=[
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
            param_state,
            submit_status,
        ],
        outputs=[param_state, input_section, submit_btn, reset_btn, timer],
    ).then( ###############--------Submission event, send job---------################
        fn=send_job, inputs=[param_state, jobs_folder_state], outputs=[param_state],
    ).then(
        fn=update_sections,
        inputs=[param_state],
        outputs=[input_section, submit_section, submit_status, submit_btn, reset_btn]
    ).then(
        fn=update_timer, inputs=[param_state], outputs=[timer]
    )

    # Stop timer after reset
    reset_btn.click(fn=lambda: gr.update(active=False), inputs=[], outputs=timer
    ).then(
        fn=on_reset, inputs=[param_state], 
        outputs=[
            param_state,
            job_dropdown,
            input_section,
            output_section,
            inf_sav_txt,
            inf_sav_file,
            tf_sav_txt,
            tf_sav_file,
            str_txt,
            str_file,
            job_name_txt,
            email_txt,
            submit_status,
            submit_btn,
            reset_btn,
            process_status,
        ]
    )

    # ###############--------Timer, report job status---------################
    timer.tick(
        fn=update_process_status, inputs=[param_state, gr.State(True)], outputs=[process_status, param_state]
    ).then(
        fn=update_output_sections, inputs=[param_state, jobs_folder_state],
        outputs=[
            output_section,
            result_zip,
            inf_output_secion,
            pred_table,
            image_selector,
            image_viewer,
            tf_output_secion,
            folds_state,
            fold_dropdown,
            train_box,
            val_box,
            test_box,
            loss_image,
            test_evaluation,
        ]
    ).then(
        fn=update_timer, inputs=[param_state], outputs=[timer]
    )
    image_selector.change(fn=on_select_image, inputs=[image_selector, jobs_folder_state, param_state], outputs=[image_viewer],)

if __name__ == "__main__":

    with gr.Blocks(css=custom_css,) as demo:
        # ---------- HEADER ---------- uXXF0nC3qJ QVP4GRh26k
        header = build_header()

        # ---------- MAIN CONTENT (with tabs) ----------
        with gr.Column(elem_id="main-content"):
            with gr.Tab("Home"):
                with gr.Row():
                    with gr.Column(scale=1):
                        left_column()
                    with gr.Column(scale=1):
                        right_column(JOB_DIR)
            with gr.Tab(label="🗂️ Job Manager", id='job'):
                manager_tab()

        footer_html = build_footer(MOUNT_POINT)

    demo.queue()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,
        allowed_paths=[
            "/tandem/jobs", 
            "assets/images",
        ],
        root_path=MOUNT_POINT,
    )