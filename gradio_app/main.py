import os 
import sass 
import gradio as gr
from pymongo import MongoClient

from src.web_interface import session, tandem_input, tandem_output, build_header, left_column, build_footer, on_auto_view
from src.web_interface import render_job_html, render_session_html
from src.update_session import on_session
from src.update_input import update_input_param
from src.job import on_job, on_reset, send_job, update_sections, update_timer
from src.job import update_process_status, update_submit_status, on_going_back
from src.update_output import update_finished_job, on_select_sav
from src.job_manager import manager_tab
from src.QA import qa
from src.tutorial import tutorial
from src.logger import LOGGER

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

MOUNT_POINT = '/TANDEM-dev' # https://dyn.life.nthu.edu.tw/TANDEM-dev
TITLE = 'TANDEM-DIMPLE-DEV'
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

def getip(request: gr.Request, param_state):
    # Direct client IP
    ip = request.client.host

    # If behind proxy (nginx / cloudflare)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()

    param_state_udt = param_state.copy()
    param_state_udt['IP'] = ip
    return param_state_udt

def home_tab(folder):

    timer = gr.Timer(value=1, active=True) # Timer to check result
    job_folder = gr.State()

    with gr.Row() as input_page:
        with gr.Column(scale=1):
            left_column()
        with gr.Column(scale=1):
            param_state = gr.State({})
            jobs_folder_state = gr.State(folder)

            # Session UI
            (session_id, session_btn, session_mkd, session_status, job_dropdown) = session()
            
            # Input UI
            (
                param_state,
                input_section,
                mode,
                inf_sav_txt,
                inf_sav_btn,
                inf_sav_file,
                inf_auto_view,

                model_dropdown,
                
                tf_sav_txt,
                tf_sav_btn,
                tf_sav_file,
                tf_auto_view,
                structure_section,
                str_check,
                str_txt,
                str_btn,
                str_file,

                job_name_txt,
                email_txt,
                submit_btn,
            ) = tandem_input(param_state)

    ##### Result page
    with gr.Group(visible=False) as output_page:    
        with gr.Row(elem_classes="bg-row-column"):
            with gr.Column(scale=4):
                submit_status = gr.Textbox(label="Submission Status", lines=2, interactive=False, elem_classes="gr-textbox", autoscroll=False)
            with gr.Column(scale=4):
                process_status = gr.Textbox(label="Processing Status", lines=2, interactive=False, elem_classes="gr-textbox", autoscroll=False)
            with gr.Column(scale=2):
                session_box = gr.HTML(render_session_html(session_id))
                job_box = gr.HTML(render_job_html(job_name_txt))
                with gr.Row():
                    back_btn = gr.Button(elem_id="going_back_btn")
                    
                    gr.HTML("""
                    <button class="going-back-btn"
                        onclick="document.getElementById('going_back_btn').click()">
                        ← Going back
                    </button>
                    """)
            
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
            session_box.click(None, js=session_box_js) # Click = copy to clipboard
            back_btn.click(
                fn=on_going_back, inputs=[param_state], 
                outputs=[input_section, input_page, output_page, inf_sav_txt, tf_sav_txt, structure_section, str_check, str_txt, str_btn, str_file, mode, job_name_txt, job_dropdown])

        # Result UI
        (
            output_section,
            inf_output_secion,
            tf_output_secion,

            pred_table,
            image_viewer,

            folds_state,
            fold_dropdown,
            sav_textbox,
            loss_image,
            test_evaluation,
            model_save,

            result_zip,

        ) = tandem_output()
        reset_btn = gr.Button("New job", elem_classes="gr-button")

    # Stop timer after reset
    reset_btn.click(fn=lambda: gr.update(active=False), inputs=[], outputs=timer
    ).then(fn=on_reset, inputs=[param_state], 
        outputs=[input_page, param_state, job_dropdown, input_section, output_page, inf_sav_txt, inf_sav_btn, inf_sav_file, tf_sav_txt, tf_sav_btn, tf_sav_file, str_txt, str_btn, str_file, job_name_txt, email_txt])
    
    ################-------------Simulate session event----------------################ 
    # Generate/resume session
    session_click_event = session_btn.click(fn=on_session, inputs=[session_id, param_state], outputs=[session_id, session_btn, session_mkd, session_status, job_dropdown, param_state, model_dropdown])
    session_submit_event = session_id.submit(fn=on_session, inputs=[session_id, param_state], outputs=[session_id, session_btn, session_mkd, session_status, job_dropdown, param_state, model_dropdown])

    # Visualize input section
    session_event = [session_click_event, session_submit_event]
    for i, event in enumerate(session_event):
        session_event[i] = event.then(
               fn=update_sections, inputs=[param_state], outputs=[input_section, input_page, output_page]
        ).then(fn=update_submit_status, inputs=[param_state], outputs=[submit_status]
        ).then(fn=update_process_status, inputs=[param_state, gr.State(False)], outputs=[process_status, param_state]
        ).then(fn=update_timer, inputs=[param_state], outputs=[timer]
        ).then(fn=update_finished_job, inputs=[param_state, jobs_folder_state],
            outputs=[output_section, result_zip, inf_output_secion, pred_table, image_viewer, tf_output_secion, folds_state, fold_dropdown, sav_textbox, loss_image, test_evaluation, model_save, job_folder]
        ).then(fn=render_session_html, inputs=[param_state], outputs=[session_box]
        ).then(fn=render_job_html, inputs=[param_state], outputs=[job_box]
        )
        
    #############---input_section following job selection--------################
    job_dropdown.select(
           fn=on_job, inputs=[job_dropdown, param_state], outputs=[param_state]
    ).then(fn=update_sections, inputs=[param_state], outputs=[input_section, input_page, output_page]
    ).then(fn=update_submit_status, inputs=[param_state], outputs=[submit_status]
    ).then(fn=update_process_status, inputs=[param_state, gr.State(False)], outputs=[process_status, param_state]
    ).then(fn=update_timer, inputs=[param_state], outputs=[timer]
    ).then(fn=update_finished_job, inputs=[param_state, jobs_folder_state],
        outputs=[output_section, result_zip, inf_output_secion, pred_table, image_viewer, tf_output_secion, folds_state, fold_dropdown, sav_textbox, loss_image, test_evaluation, model_save, job_folder]
    ).then(fn=render_session_html, inputs=[param_state], outputs=[session_box]
    ).then(fn=render_job_html, inputs=[param_state], outputs=[job_box]
    )

    ###############---input_section following job selection--------################
    submit_btn.click(inputs=[mode, inf_sav_txt, inf_sav_file, model_dropdown, tf_sav_txt, tf_sav_file, str_txt, str_file, job_name_txt, email_txt, param_state],
           fn=update_input_param, outputs=[param_state, input_section, reset_btn, timer],
    ).then(fn=getip, inputs=[param_state], outputs=[param_state]
    ).then(fn=send_job, inputs=[param_state, jobs_folder_state], outputs=[param_state],
    ).then(fn=update_sections, inputs=[param_state], outputs=[input_section, input_page, output_page]
    ).then(fn=update_submit_status, inputs=[param_state], outputs=[submit_status]
    ).then(fn=update_process_status, inputs=[param_state, gr.State(False)], outputs=[process_status, param_state]
    ).then(fn=update_timer, inputs=[param_state], outputs=[timer]
    ).then(fn=render_session_html, inputs=[param_state], outputs=[session_box]
    ).then(fn=render_job_html, inputs=[param_state], outputs=[job_box]
    ).then(fn=getip, inputs=[param_state], outputs=[param_state]
    )

    # ###############--------Timer, report job status---------################
    timer.tick(fn=update_process_status, inputs=[param_state, gr.State(True)], outputs=[process_status, param_state]
    ).then(fn=update_finished_job, inputs=[param_state, jobs_folder_state],
        outputs=[output_section, result_zip, inf_output_secion, pred_table, image_viewer, tf_output_secion, folds_state, fold_dropdown, sav_textbox, loss_image, test_evaluation, model_save, job_folder]
    ).then(fn=update_timer, inputs=[param_state], outputs=[timer])

    # ###############--------View output examples---------################
    # Store test parameters 
    test_param_state = gr.State({})
    inf_auto_view.click(fn=on_auto_view, inputs=[mode, jobs_folder_state, param_state], outputs=[test_param_state, param_state]
    ).then(fn=update_sections, inputs=[test_param_state], outputs=[input_section, input_page, output_page]
    ).then(fn=update_submit_status, inputs=[test_param_state], outputs=[submit_status]
    ).then(fn=update_process_status, inputs=[test_param_state, gr.State(False)], outputs=[process_status, test_param_state]
    ).then(fn=update_finished_job, inputs=[test_param_state, jobs_folder_state],
        outputs=[output_section, result_zip, inf_output_secion, pred_table, image_viewer, tf_output_secion, folds_state, fold_dropdown, sav_textbox, loss_image, test_evaluation, model_save, job_folder]
    ).then(fn=render_session_html, inputs=[param_state], outputs=[session_box]
    ).then(fn=render_job_html, inputs=[param_state], outputs=[job_box]
    )
    
    tf_auto_view.click(fn=on_auto_view, inputs=[mode, jobs_folder_state, param_state], outputs=[test_param_state, param_state]
    ).then(fn=update_sections, inputs=[test_param_state], outputs=[input_section, input_page, output_page]
    ).then(fn=update_submit_status, inputs=[test_param_state], outputs=[submit_status]
    ).then(fn=update_process_status, inputs=[test_param_state, gr.State(False)], outputs=[process_status, test_param_state]
    ).then(fn=update_finished_job, inputs=[test_param_state, jobs_folder_state],
        outputs=[output_section, result_zip, inf_output_secion, pred_table, image_viewer, tf_output_secion, folds_state, fold_dropdown, sav_textbox, loss_image, test_evaluation, model_save, job_folder]
    ).then(fn=render_session_html, inputs=[param_state], outputs=[session_box]
    ).then(fn=render_job_html, inputs=[param_state], outputs=[job_box]
    )
    
    pred_table.select(on_select_sav, inputs=[pred_table, job_folder], outputs=[image_viewer])

if __name__ == "__main__":

    with gr.Blocks(css=custom_css,) as demo:
        # ---------- HEADER ---------- uXXF0nC3qJ QVP4GRh26k
        header = build_header(TITLE)

        # ---------- MAIN CONTENT (with tabs) ----------
        with gr.Column(elem_id="main-content"):
            with gr.Tab("Home"):
                home_tab(JOB_DIR)
            with gr.Tab(label="🗂️ Job Manager", id='job'):
                manager_tab()
            with gr.Tab(label="Q & A"):
                qa_page = qa(MOUNT_POINT)
            with gr.Tab(label="Tutorial"):
                tutorial_page = tutorial(MOUNT_POINT)
                
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
    # QVP4GRh26k
    # TANDEM-dev