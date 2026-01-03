import os
import gradio as gr
from datetime import datetime
from zoneinfo import ZoneInfo

from .update_input import upload_file, on_delete_file
from .settings import GRADIO_APP_ROOT

basedir = os.path.dirname(__file__)
parentdir = os.path.dirname(basedir)
figure_1 = os.path.join(parentdir, 'images/figure_1.jpg')

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
        gr.Markdown("### User session", elem_classes="boxed-markdown")
        # gr.Markdown("### Session")
        _session_id = gr.Textbox(
            # label="Session ID", show_label=False,
            label=" ", show_label=True,
            placeholder="Start a new session or paste an existing session ID", 
            interactive=True, 
            show_copy_button=True,
        )
        _session_btn = gr.Button("▶️ Start / Resume Session")
        # _session_status = gr.Markdown("", elem_classes="boxed-markdown")
        _session_status = gr.Markdown("")
        _job_dropdown = gr.Dropdown(label="Old jobs", visible=False, filterable=False, allow_custom_value=False, preserved_by_key=None)
    
    return _session_id, _session_btn, _session_status, _job_dropdown

def on_auto_fill(mode, auto_fill):
    if not auto_fill:
        sav_txt = gr.update(value="")
        str_file = gr.update()
        return sav_txt, str_file
    
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
        sav_txt = gr.update(value=inf_test_SAVs)
        str_file = gr.update()
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
        sav_txt = gr.update(value=tf_test_SAVs)
        str_file = os.path.join(GRADIO_APP_ROOT, 'test/8qa2_opm_25Apr03.pdb')
    else:
        raise KeyError(f"Unknown mode: {mode}")

    return sav_txt, str_file

def on_mode(mode):
    inf_mode = gr.update(visible=(mode == "Inferencing"))
    tf_mode = gr.update(visible=(mode == "Transfer Learning"))
    return (inf_mode, tf_mode)

def on_structure(checked: bool):
    structure_section_udt = gr.update(visible=checked)
    return structure_section_udt

def tandem_input(time_interval=1):
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
                label = "Paste single amino acid variants (leave empty to run the test case)"
                placeholder="O14508 S52N\nP29033 Y217D\n..."
                inf_sav_txt = gr.Textbox(value='', interactive=True, max_lines=5, lines=4, elem_id="sav-txt", label=label, placeholder=placeholder, scale=6)
                inf_sav_btn = gr.UploadButton(label="Upload SAVs", file_count="single", file_types=[".txt"], elem_id="sav-btn", scale=3)
                inf_sav_file = gr.File(visible=False, file_types=[".txt"], height=145, scale=3)
            
            inf_auto_fill = gr.Checkbox(label="Do you want to load the test input?", interactive=True)
            choices = ["TANDEM", "TANDEM-DIMPLE for GJB2", "TANDEM-DIMPLE for RYR1"]
            model_dropdown = gr.Dropdown(value="TANDEM", label="Model", choices=choices, interactive=True, filterable=False)

        # Transfer Learning input mode
        with gr.Group(visible=False) as tf_section:
            with gr.Row():
                label="Paste single amino acid variants and the corresponding labels (leave empty to run the test case)"
                placeholder="O14508 S52N 1\nP29033 Y217D 0\n..."
                tf_sav_txt = gr.Textbox(value='', interactive=True, max_lines=5, lines=4, elem_id="sav-txt", label=label, placeholder=placeholder, scale=6)
                tf_sav_btn = gr.UploadButton(label="Upload SAVs", file_count="single", file_types=[".txt"], elem_id="sav-btn", scale=3)
                tf_sav_file = gr.File(visible=False, file_types=[".txt"], height=145, scale=3)
            tf_auto_fill = gr.Checkbox(label="Do you want to load the test input?", interactive=True)

        # Assign/Upload your structure
        str_check = gr.Checkbox(value=False, label="Provide PDB/AF2 ID or upload coordinate file", interactive=True)
        with gr.Row(visible=False) as structure_section:
            str_txt = gr.Textbox(value=None, label="Structure", placeholder="PDB ID (e.g., 1GOD) or AF2 ID (e.g., 014508)", interactive=True, show_label=False, scale=6)
            str_btn = gr.UploadButton("Upload file", file_count="single", elem_id="sav-btn", file_types=[".cif", ".pdb"], scale=3)
            str_file = gr.File(visible=False, scale=3, height=145)
        str_check.change(on_structure, str_check, [structure_section])

        # General info
        job_name = datetime.now(time_zone).strftime("%Y-%m-%d_%H-%M-%S")
        job_name_txt = gr.Textbox(value=job_name, label="Job name", placeholder="Enter job name", interactive=True)
        email_txt = gr.Textbox(value=None, label="Email (Optional)", placeholder="Enter your email", interactive=True, visible=False, type='email')

    with gr.Group(visible=False) as submit_section:
        # Submit job
        submit_status = gr.Textbox(label="Submission Status", visible=False, lines=10, interactive=False, elem_id="submit-status")
        process_status = gr.Textbox(label="Processing Status", visible=False, lines=1, interactive=False, elem_id="process-status")
        submit_btn = gr.Button("Submit")
        reset_btn = gr.Button("New job", visible=False)
    
    timer = gr.Timer(value=time_interval, active=False) # Timer to check result

    # Fill test case
    inf_auto_fill.change(fn=on_auto_fill, inputs=[mode, inf_auto_fill], outputs=[inf_sav_txt, str_file])
    tf_auto_fill.change(fn=on_auto_fill, inputs=[mode, tf_auto_fill], outputs=[tf_sav_txt, str_file])

    # Select mode (1) Inferencing or (2) Transfer Learning
    mode.change(fn=on_mode, inputs=mode, outputs=[inf_section, tf_section])

    # Upload
    inf_sav_btn.upload(fn=upload_file, inputs=[inf_sav_btn], outputs=[inf_sav_btn, inf_sav_file])
    tf_sav_btn.upload(fn=upload_file, inputs=[tf_sav_btn], outputs=[tf_sav_btn, tf_sav_file])
    str_btn.upload(fn=upload_file, inputs=[str_btn], outputs=[str_btn, str_file])

    # Delete file
    inf_sav_file.delete(fn=on_delete_file, inputs=[inf_sav_file], outputs=[inf_sav_btn, inf_sav_file])
    tf_sav_file.delete(fn=on_delete_file, inputs=[tf_sav_file], outputs=[tf_sav_btn, tf_sav_file])
    str_file.delete(fn=on_delete_file, inputs=[str_file], outputs=[str_btn, str_file])

    return (
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
    )

def tandem_output():

    with gr.Group(visible=False) as _output_section:
        gr.Markdown("### Results", elem_classes="boxed-markdown")
        _pred_table = gr.HTML()
        
        # Image selector (top bar)
        _image_selector = gr.Dropdown(
            label="Select visualization",
            choices=[],
            value=None,
            interactive=True,
            visible=False,
        )

        # Image display (single image)
        _image_viewer = gr.Image(
            label="Visualization",
            visible=False,
        )
        _result_zip = gr.File(label="Download Results (.zip)")

    return (
        _output_section,
        _pred_table,
        _image_selector,
        _image_viewer,
        _result_zip
    )


def header():
    header_text = (
        "# TANDEM-DIMPLE: Transfer-leArNing-ready and Dynamics-Empowered Model "
        "for Disease-specific Missense Pathogenicity Level Estimation"
    )
    gr.Markdown(value=header_text, elem_classes='header')

def footer():
    footer_text = (
        "### **Reference:** Loci Tran, Lee-Wei Yang, Transfer-leArNing-ready and Dynamics-Empowered Model for "
        "Disease-specific Missense Pathogenicity Level Estimation. (In preparation)<br>"
        "**Contact:** The server is maintained by the Yang Lab at the Institute of Bioinformatics and Structural "
        "Biology at National Tsing Hua University, Taiwan.<br>"
        "**Email:** locitran0521@gmail.com"
    )
    gr.Markdown(value=footer_text, elem_classes="footer")

if __name__ == "__main__":
    pass