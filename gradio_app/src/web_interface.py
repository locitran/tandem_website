import os
import json
import gradio as gr
from datetime import datetime
from zoneinfo import ZoneInfo

from .update_input import upload_file, on_clear_file, on_clear_param
from .settings import GRADIO_DIR
from .update_output import on_sav_set_select
from .logger import LOGGER

basedir = os.path.dirname(__file__)
parentdir = os.path.dirname(basedir)
figure_1 = os.path.join(parentdir, 'assets/images/figure_1.jpg')

time_zone = ZoneInfo("Asia/Taipei")

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
    gr.Markdown(f"""### What is TANDEM-DIMPLE?\n{intro}""")
    gr.Image(value=figure_1, label="", show_label=False, width=None)

def session():

    with gr.Group():
        gr.Markdown("### User session", elem_classes="h3")
        placeholder = "Start a new session or paste an existing session ID"
        session_id = gr.Textbox(label=" ", show_label=True, placeholder=placeholder,  interactive=True, show_copy_button=True, elem_classes="gr-textbox")
        # session_id = gr.Textbox(label=" ", show_label=True, placeholder=placeholder,  interactive=True, buttons=['copy'], elem_classes="gr-textbox")
        session_btn = gr.Button("▶️ Start / Resume Session", elem_classes="gr-button")
        session_mkd = gr.Markdown("##### Please find the input/output examples by clicking this 'Start / Resume a Session'")
        session_status = gr.Markdown("")
        job_dropdown = gr.Dropdown(label="Old jobs", visible=False, filterable=False, allow_custom_value=False, preserved_by_key=None)
    
    return session_id, session_btn, session_mkd, session_status, job_dropdown

def on_auto_fill(mode, param):
    
    param_udt = param.copy()
    str_file_udt = gr.update()

    if mode == "Inferencing":
        inf_test_SAVs = (
            f"O00189 R271H\n"
            f"O00194 P138L\n"
            f"O00194 A92T\n"
            f"O00204 V240I\n"
            f"O00204 L51S\n"
            f"O00206 T175A\n"
            f"O00206 Q188R\n"
            f"O00206 C246S\n"
            f"O00206 E287D\n"
            f"O00206 E287G\n"
            f"O00206 C306W\n"
        )
        sav_txt_udt = gr.update(value=inf_test_SAVs)
        job_name_udt = gr.update(value='Inference_test')
        str_btn_udt = gr.update(visible=True)
        str_file_udt = gr.update(value=None, visible=False)
        str_check_udt = gr.update(value=False)
    elif mode == "Transfer Learning":
        tf_test_SAVs = (
            f"P29033 Y217D 0\n"
            f"P29033 I215M 0\n"
            f"P29033 L214V 0\n"
            f"P29033 L210V 0\n"
            f"P29033 I203T 0\n"
            f"P29033 A197T 0\n"
            f"P29033 N170K 0\n"
            f"P29033 N170S 0\n"
            f"P29033 K168R 0\n"
            f"P29033 V156I 0\n"
            f"P29033 V153I 0\n"
            f"P29033 R127H 0\n"
            f"P29033 T123N 0\n"
            f"P29033 I121V 0\n"
            f"P29033 F115V 0\n"
            f"P29033 E114G 0\n"
            f"P29033 I111T 0\n"
            f"P29033 I107L 0\n"
            f"P29033 H100Q 0\n"
            f"P29033 F83L 0\n"
            f"P29033 V27I 0\n"
            f"P29033 H16Y 0\n"
            f"P29033 G4V 0\n"
            f"P29033 G4D 0\n"
            f"P29033 R165W 0\n"
            f"P29033 M34T 1\n"
            f"P29033 V37I 1\n"
            f"P29033 W44C 1\n"
            f"P29033 W44S 1\n"
            f"P29033 D50N 1\n"
            f"P29033 G59A 1\n"
            f"P29033 R75Q 1\n"
            f"P29033 R75W 1\n"
            f"P29033 V84L 1\n"
            f"P29033 L90P 1\n"
            f"P29033 V95M 1\n"
            f"P29033 R143W 1\n"
            f"P29033 R143Q 1\n"
            f"P29033 F161S 1\n"
            f"P29033 M163T 1\n"
            f"P29033 D179N 1\n"
            f"P29033 R184Q 1\n"
            f"P29033 M195T 1\n"
            f"P29033 A197S 1\n"
            f"P29033 C202F 1\n"
            f"P29033 L205V 1\n"
            f"P29033 N206S 1\n"
        )
        sav_txt_udt = gr.update(value=tf_test_SAVs)
        param_udt['GJB2_test'] = True
        job_name_udt = gr.update(value='GJB2_test')

        # STR
        str_check_udt = gr.update(value=True)
        str_btn_udt = gr.update(visible=False)
        str_file_udt = os.path.join(GRADIO_DIR, 'test/8qa2_opm_25Apr03.pdb')
        str_file_udt = gr.update(value=str_file_udt, visible=True)
    else:
        raise KeyError(f"Unknown mode: {mode}")

    return sav_txt_udt, str_check_udt, str_btn_udt, str_file_udt, job_name_udt, param_udt

def on_auto_view(mode, jobs_folder, param):
    test_session = 'test'
    if mode == "Inferencing":
        job_name = "inference_test"
    elif mode == "Transfer Learning":
        job_name = "GJB2_test"
    else:
        raise InterruptedError()
    test_param_file = os.path.join(jobs_folder, test_session, job_name, 'params.json')
    with open(test_param_file, 'r') as f:
        test_param = json.load(f)
    
    # Copy test_param to main_param
    param_udt = test_param.copy()
    param_udt['session_id'] = param['session_id']
    return test_param, param_udt

def on_mode(mode, param):
    param_udt = param.copy()
    param_udt['GJB2_test'] = False

    inf_mode = gr.update(visible=(mode == "Inferencing"))
    tf_mode = gr.update(visible=(mode == "Transfer Learning"))

    return (inf_mode, tf_mode, param_udt)

def on_structure(checked: bool):
    structure_section_udt = gr.update(visible=checked)
    return structure_section_udt

def tandem_input(param):
    """
    Next try: DeletedFileData, Error, ParamViewer
    https://www.gradio.app/docs/gradio/deletedfiledata
    https://www.gradio.app/docs/gradio/error
    https://www.gradio.app/docs/gradio/paramviewer

    """
    with gr.Group(visible=False) as input_section:

        ####### Start
        mode = gr.Radio(["Inferencing", "Transfer Learning"], value="Inferencing", label="Mode of Actions")
        # Inferencing input mode
        with gr.Group(visible=True) as inf_section:
            with gr.Row():
                label = "Paste single amino acid variants"
                placeholder="O14508 S52N\nP29033 Y217D\n..."
                inf_sav_txt = gr.Textbox(value='', interactive=True, max_lines=5, lines=4, elem_id="sav-txt", label=label, placeholder=placeholder, scale=6, elem_classes="gr-textbox")
                inf_sav_btn = gr.UploadButton(label="Upload SAVs", file_count="single", file_types=[".txt"], elem_classes="gr-button", scale=3)
                inf_sav_file = gr.File(visible=False, file_types=[".txt"], height=145, scale=3)
            
            with gr.Row():
                inf_auto_fill = gr.Button(elem_id="inf_auto_fill")
                inf_auto_view = gr.Button(elem_id="inf_auto_view")
                inf_clear_btn = gr.Button(elem_id="inf_clear_btn")
                gr.HTML("""
                    <button class="load-input-btn"
                        onclick="document.getElementById('inf_auto_fill').click()">
                        Load input example
                    </button>

                    <button class="view-output-btn"
                        onclick="document.getElementById('inf_auto_view').click()">
                        View output example
                    </button>
                    
                    <button class="clear-input-btn"
                        onclick="document.getElementById('inf_clear_btn').click()">
                        Clear all
                    </button>
                    """)
            choices = ["TANDEM", "TANDEM-DIMPLE for GJB2", "TANDEM-DIMPLE for RYR1"]
            model_dropdown = gr.Dropdown(value="TANDEM", label="Select model for prediction", choices=choices, interactive=True, filterable=False)

        # Transfer Learning input mode
        with gr.Group(visible=False) as tf_section:
            with gr.Row():
                label="Paste single amino acid variants and the corresponding labels"
                placeholder="O14508 S52N 1\nP29033 Y217D 0\n..."
                tf_sav_txt = gr.Textbox(value='', interactive=True, max_lines=5, lines=4, elem_id="sav-txt", label=label, placeholder=placeholder, scale=6, elem_classes="gr-textbox")
                tf_sav_btn = gr.UploadButton(label="Upload SAVs", file_count="single", file_types=[".txt"], elem_classes="gr-button", scale=3)
                tf_sav_file = gr.File(visible=False, file_types=[".txt"], height=145, scale=3)
            with gr.Row():
                tf_auto_fill = gr.Button(elem_id="tf_auto_fill")
                tf_auto_view = gr.Button(elem_id="tf_auto_view")
                tf_clear_btn = gr.Button(elem_id="tf_clear_btn")
                gr.HTML("""
                    <button class="load-input-btn"
                        onclick="document.getElementById('tf_auto_fill').click()">
                        Load input example
                    </button>

                    <button class="view-output-btn"
                        onclick="document.getElementById('tf_auto_view').click()">
                        View output example
                    </button>
                    
                    <button class="clear-input-btn"
                        onclick="document.getElementById('tf_clear_btn').click()">
                        Clear all
                    </button>
                    """)

        # Assign/Upload your structure
        str_check = gr.Checkbox(value=False, label="Provide PDB/AF2 ID or upload coordinate file", interactive=True)
        with gr.Row(visible=False) as structure_section:
            str_txt = gr.Textbox(value=None, label="Structure", placeholder="PDB ID (e.g., 1GOD) or AF2 ID (e.g., 014508)", interactive=True, show_label=False, scale=6)
            str_btn = gr.UploadButton("Upload file", file_count="single", elem_id="sav-btn", file_types=[".cif", ".pdb"], scale=3)
            str_file = gr.File(visible=False, scale=3, height=145)
        str_check.change(on_structure, str_check, [structure_section])

        # General info
        job_name = datetime.now(time_zone).strftime("%Y-%m-%d_%H-%M-%S")
        job_name_txt = gr.Textbox(value=job_name, label="Job name", placeholder="Enter job name", interactive=True, elem_classes="gr-textbox")
        email_txt = gr.Textbox(value=None, label="Email (Optional)", placeholder="Enter your email", interactive=True, visible=False, type='email', elem_classes="gr-textbox")
        submit_btn = gr.Button("Submit", elem_classes="gr-button")

    # Fill test case
    inf_auto_fill.click(fn=on_auto_fill, inputs=[mode, param], outputs=[inf_sav_txt, str_check, str_btn, str_file, job_name_txt, param])
    tf_auto_fill.click(fn=on_auto_fill, inputs=[mode, param], outputs=[tf_sav_txt, str_check, str_btn, str_file, job_name_txt, param])

    # Select mode (1) Inferencing or (2) Transfer Learning
    mode.change(fn=on_mode, inputs=[mode, param], outputs=[inf_section, tf_section, param])

    # Upload
    inf_sav_btn.upload(fn=upload_file, inputs=[inf_sav_btn], outputs=[inf_sav_btn, inf_sav_file])
    tf_sav_btn.upload(fn=upload_file, inputs=[tf_sav_btn], outputs=[tf_sav_btn, tf_sav_file])
    str_btn.upload(fn=upload_file, inputs=[str_btn], outputs=[str_btn, str_file])

    # Delete file
    inf_sav_file.clear(fn=on_clear_file, inputs=[], outputs=[inf_sav_btn, inf_sav_file])
    tf_sav_file.clear(fn=on_clear_file, inputs=[], outputs=[tf_sav_btn, tf_sav_file])
    str_file.clear(fn=on_clear_file, inputs=[], outputs=[str_btn, str_file])
    
    # Clear parameters
    inf_clear_btn.click(fn=on_clear_param, inputs=[], outputs=[inf_sav_txt, inf_sav_btn, inf_sav_file, tf_sav_txt, tf_sav_btn, tf_sav_file, str_txt, str_btn, str_file, job_name_txt, email_txt,])
    tf_clear_btn.click(fn=on_clear_param, inputs=[], outputs=[inf_sav_txt, inf_sav_btn, inf_sav_file, tf_sav_txt, tf_sav_btn, tf_sav_file, str_txt, str_btn, str_file, job_name_txt, email_txt,])
    return (
        param,
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
    )

def tandem_output():

    with gr.Group(visible=False) as output_section:
        gr.Markdown("### Results", elem_classes="h3")    
        
        with gr.Group(visible=False) as inf_output_secion:
            with gr.Row():
                with gr.Column():
                    pred_table = gr.Dataframe(interactive=False, max_height=340, show_label=False)
                with gr.Column():
                    image_viewer = gr.Image(height=340, show_download_button=False, show_label=False)
                    # image_viewer = gr.Image(height=340, show_label=False)
        
        with gr.Group(visible=False) as tf_output_secion:
            with gr.Row():
                with gr.Column():
                    folds_state = gr.State(value={})
                    fold_dropdown = gr.Dropdown(label="View SAV set", choices=[], interactive=True, elem_classes="gr-button", elem_id="sav_dropdown", show_label=False)
                    sav_textbox = gr.Textbox(lines=1, interactive=False, show_label=False, elem_classes="gr-textbox", elem_id="sav_textbox", autoscroll=False)
                    fold_dropdown.change(fn=on_sav_set_select, inputs=[fold_dropdown, folds_state], outputs=sav_textbox)
                    test_evaluation = gr.Dataframe(interactive=False, max_height=250, show_label=False)
                loss_image = gr.Image(label="", show_download_button=False, show_label=False, height=364)
                # loss_image = gr.Image(label="", show_label=False, height=393)
            model_save = gr.Markdown(elem_classes="gr-p")
        result_zip = gr.File(label="Download Results")
    return (
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
    )

def build_header(title):
    header_html = f"""
    <div class="header">
        <div class="header-bg"></div>

        <div class="header-content">
            <div class="header-text">
                <div class="header-title">{title}</div>
                <div class="header-subtitle">Transfer-leArNing-ready and Dynamics-Empowered Model for Disease-specific Missense Pathogenicity Estimation</div>
            </div>
        </div>
    </div>
    """   
    header = gr.HTML(header_html)
    return header

def build_footer(mount_point):
    footer_html = f"""
    <div class="footer-container">
        <div class="footer-logo">
            <img src="{mount_point}/gradio_api/file=assets/images/nthu_logo.png" alt="NTHU Logo">
        </div>

        <div class="footer-text">
            <div class="footer-title">
                Reference:
            </div>
            <div>
                Loc Dinh Quang Tran, Chen-Hua Lu, Cheng-Yu Tsai, Wei-Hsiang Shen,
                Chun-Biu Li, Tong-You Lin, Chi-Chun Lee, Pei-Lung Chen,
                Chen-Chi Wu, Lee-Wei Yang*<br>
                <em>Transfer-leArNing-ready and Dynamics-Empowered Model for
                Disease-specific Missense Pathogenicity Level Estimation</em>.
                (In preparation)
            </div>
            <div>
                <strong>Contact:</strong> The server is maintained by the Yang Lab at the Institute of
                Bioinformatics and Structural Biology, National Tsing Hua University, Taiwan.
            </div>
            <div>
                <strong>Email:</strong> <a href="mailto:locitran0521@gmail.com">locitran0521@gmail.com</a>
            </div>
        </div>
    </div>
    """
    footer = gr.HTML(footer_html, elem_classes="footer")
    return footer

def render_job_html(name):
    if isinstance(name, dict):
        name = name.get("job_name", "")
    return f"""
    <div class="job-row">
        <span class="job-label">Job:</span>
        <span class="job-name" id="job-name">{name}</span>
    </div>
    """

def render_session_html(id):
    if isinstance(id, dict):
        id = id.get("session_id", "")

    return f"""
    <div class="session-row">
        <span class="session-label">Session:</span>
        <span class="session-id" id="session-id" style="padding:4px 6px; border-radius:4px;">{id}</span>
        <span style="font-size:12px; color:var(--body-text-color-subdued);">(click to copy)</span>
    </div>
    """

if __name__ == "__main__":
    pass