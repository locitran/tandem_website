import os 

import gradio as gr
from pymongo import MongoClient

from src.web_interface import session, tandem_input, tandem_output, header, footer, left_column
from src.update_session import then_session, on_session
from src.update_input import update_input_param
from src.job import on_submit, on_job, on_reset, send_job, check_status
from src.update_output import render_output, on_select_image
from src.job_manager import manager_tab

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

ADMIN_PASSWORD = "yanglab"

TANDEM_WEBSITE_ROOT = os.path.dirname(os.path.dirname(__file__)) # ./tandem_website
jobs_folder = os.path.join(TANDEM_WEBSITE_ROOT, 'tandem/jobs')
figure_1 = os.path.join(TANDEM_WEBSITE_ROOT, 'gradio_app/images/figure_1.jpg')
cssfile = os.path.join(TANDEM_WEBSITE_ROOT, 'gradio_app/css/font.css')

css_interface = os.path.join(TANDEM_WEBSITE_ROOT, 'gradio_app/css/interface.css')
custom_css = ''
with open(css_interface, "r") as f:
    custom_css += f.read() + '\n'
with open(cssfile, "r") as f:
    custom_css += f.read() + '\n'

def right_column(param_state: gr.State, jobs_folder_state: gr.State):
    
    # Session UI
    (
        session_id, 
        session_btn, 
        session_status, 
        job_dropdown

    ) = session()
    
    # Input UI
    (
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

    ) = tandem_input()

    # Result UI
    (
        output_section,
        pred_table,
        image_selector,
        image_viewer,
        result_zip

    ) = tandem_output()

    ################-------------Simulate session event----------------################
    # Generate/resume session
    session_click_event = session_btn.click(
        fn=on_session,
        inputs=[session_id, param_state],
        outputs=[session_id, session_status, job_dropdown, param_state, model_dropdown]
    )
    session_submit_event = session_id.submit(
        fn=on_session,
        inputs=[session_id, param_state],
        outputs=[session_id, session_status, job_dropdown, param_state, model_dropdown]
    )

    # Visualize input section
    session_event = [session_click_event, session_submit_event]
    for i, event in enumerate(session_event):
        session_event[i] = event.then(
            fn=then_session,
            inputs=[param_state, jobs_folder_state, submit_status],
            outputs=[
                input_section,
                submit_section,
                output_section,
                pred_table,
                result_zip,
                image_selector,
                image_viewer,
                submit_status,
                submit_btn,
                reset_btn
            ]
        )
        
    ###############---input_section following job selection--------################
    job_dropdown.select(
        fn=on_job, 
        inputs=[job_dropdown, param_state, jobs_folder_state], 
        outputs=[
            input_section,
            submit_section,
            output_section,
            process_status,
            pred_table,
            result_zip,
            image_selector,
            image_viewer,
            submit_status,
            submit_btn,
            reset_btn,
            param_state,
            timer,
        ]
    )

    ###############---input_section following job selection--------################
    submit_event = submit_btn.click(
        fn=on_submit, 
        inputs=[mode, inf_sav_txt, inf_sav_file, tf_sav_txt, tf_sav_file, str_file], 
        outputs=[mode, inf_sav_txt, inf_sav_file, tf_sav_txt, tf_sav_file, str_file, submit_status,  submit_btn]
    ).then( 
        # Start timer after submission
        fn=lambda: gr.update(active=True),
        inputs=[],
        outputs=timer
    )

    reset_event = reset_btn.click(
        # Stop timer after reset
        fn=lambda: gr.update(active=False),
        inputs=[],
        outputs=timer
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

    submit_event = submit_event.then(
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
        outputs=[param_state, input_section, submit_status, submit_btn, reset_btn, timer],
    )

    ###############--------Submission event, send job---------################
    submit_event = submit_event.then(
            fn=send_job,
            inputs=[param_state, jobs_folder_state],
            outputs=param_state,
        )

    # ###############--------Timer, report job status---------################
    # Check job status and update submit_status
    # timer = gr.Timer(value=1, active=False) # Timer to check result
    timer.tick(
        fn=check_status,
        inputs=[param_state, submit_status],
        outputs=[process_status, timer, submit_status, param_state]
    ).then( 
    # Visualize results based on param_state['status']
        fn=render_output,
        inputs=[param_state, jobs_folder_state],
        outputs=[output_section, pred_table, result_zip, image_selector, image_viewer]
    )
    
    image_selector.change(
        fn=on_select_image,
        inputs=[image_selector, jobs_folder_state, param_state],
        outputs=image_viewer,
    )

with gr.Blocks(css=custom_css,) as demo:
    # Now we define the list of components to be used as the input (params)
    # This is the return value where the gradio app will use to send to the backend
    param_state = gr.State({})
    jobs_folder_state = gr.State(jobs_folder)

    # ---------- HEADER ----------
    header()

    # ---------- MAIN CONTENT (with tabs) ----------
    with gr.Tab("Home"):
        with gr.Row():
            with gr.Column(scale=1):
                left_column()
            with gr.Column(scale=1):
                right_column(param_state, jobs_folder_state)
    
    manager_tab()
    
    footer()

# -debug=True for auto-reload
# demo.launch(server_name="0.0.0.0")
demo.queue()
demo.launch(
    server_name="0.0.0.0",
    server_port=7861,
    allowed_paths=["/tandem/jobs"],
    root_path="/TANDEM-Tsunami",
    # share=True
)


# app, local_url, share_url = demo.launch(
#     server_name="0.0.0.0",
#     server_port=7861,
#     share=True,
#     prevent_thread_lock=True
# )

# print("Public URL:", share_url)