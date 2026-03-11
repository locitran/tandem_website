import os
import json
import gradio as gr

from . import js
from .update_input import upload_file, on_clear_file, on_clear_param
from .logger import LOGGER
from .settings import FIGURE_1, HTML_DIR, EXAMPLES_JSON, MOUNT_POINT
from .request import build_job_url, passthrough_url

with open(EXAMPLES_JSON, 'r') as f:
    EXAMPLES = json.load(f)

def on_sav_set_select(selection, folds):
    return folds[selection]

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
    gr.Image(value=FIGURE_1, label="", show_label=False, width=None)

def on_load_example(example_name):
    ex = EXAMPLES.get(example_name, "")
    if ex == "":
        return (gr.update(),) * 5
    
    SAV = ex["SAV"]
    SAV_txt = "\n".join(SAV)

    sav_txt_udt = gr.update(value=SAV_txt)
    str_check_value = bool(ex.get("str_check", False))
    str_file_value = ex.get("str_file")
    str_check_udt = gr.update(value=str_check_value)
    str_btn_udt = gr.update(visible=not str_check_value)
    str_file_udt = gr.update(value=str_file_value, visible=bool(str_check_value and str_file_value))
    job_name_udt = gr.update(value=ex['job_name'])
    return sav_txt_udt, str_check_udt, str_btn_udt, str_file_udt, job_name_udt

def on_tandem_refresh(param, job_name):
    param_udt = param.copy()
    param_udt["refresh"] = True
    if job_name == "GJB2_demo":
        param_udt["GJB2_test"] = True
    return param_udt

def on_view_example(example_name):
    ex = EXAMPLES.get(example_name, "")
    if ex == "":
        gr.Warning("Please select an example first.")
        return ""

    session_id = ex.get("session_id", "")
    job_name = ex.get("job_name", "")
    if not session_id or not job_name:
        gr.Warning(f"No output example is configured for '{example_name}'.")
        return ""

    return build_job_url(session_id, job_name)

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
    with gr.Group() as input_section:

        ####### Start
        mode = gr.Radio(["Inferencing", "Transfer Learning"], value="Inferencing", label="Mode of Actions")
        # Inferencing input mode
        with gr.Group(visible=True) as inf_section:
            with gr.Row():
                label = "Paste single amino acid variants for one or multiple proteins (≤4)"
                info = "using the format - (UniProt_ID)(space)(WT_AA|ResidueID|Mutant_AA)"
                placeholder="O14508 S52N\nP29033 Y217D\n..."
                inf_sav_txt = gr.Textbox(value='', interactive=True, max_lines=5, lines=4, elem_id="inf-sav-txt", label=label, placeholder=placeholder, scale=8, elem_classes="gr-textbox", info=info)
                inf_sav_btn = gr.UploadButton(label="Upload SAVs", file_count="single", file_types=[".txt"], elem_classes="gr-button", scale=3)
                inf_sav_file = gr.File(visible=False, file_types=[".txt"], height=145, scale=3)
            
            with gr.Row():
                inf_input_example = gr.Markdown(elem_id="inf_input_example")
                inf_input_load = gr.Button(elem_id="inf_input_load")
                inf_auto_view = gr.Button(elem_id="inf_auto_view")
                inf_clear_btn = gr.Button(elem_id="inf_clear_btn")
                inf_output_url = gr.Textbox(value="", visible=False)

                filepath = os.path.join(HTML_DIR, 'inf_input_output_examples.html')
                inf_examples_html = js.build_html_text(filepath)
                inf_examples_html = gr.HTML(inf_examples_html)
            choices = ["TANDEM", "TANDEM-DIMPLE for GJB2", "TANDEM-DIMPLE for RYR1"]
            model_dropdown = gr.Dropdown(value="TANDEM", label="Select model for prediction", choices=choices, interactive=True, filterable=False)

        # Transfer Learning input mode
        with gr.Group(visible=False) as tf_section:
            with gr.Row():
                label = "Paste single amino acid variants for one or multiple proteins (≤4) and the corresponding labels"
                info = "using the format - (UniProt_ID)(space)(WT_AA|ResidueID|Mutant_AA)(space)(Label)"
                placeholder="O14508 S52N 1\nP29033 Y217D 0\n..."
                tf_sav_txt = gr.Textbox(value='', interactive=True, max_lines=5, lines=4, elem_id="tf-sav-txt", label=label, placeholder=placeholder, scale=8, elem_classes="gr-textbox", info=info)
                tf_sav_btn = gr.UploadButton(label="Upload SAVs", file_count="single", file_types=[".txt"], elem_classes="gr-button", scale=3)
                tf_sav_file = gr.File(visible=False, file_types=[".txt"], height=145, scale=3)

            with gr.Row():
                tf_input_example = gr.Markdown(elem_id="tf_input_example") # temporary name (bridge)
                tf_input_load    = gr.Button(elem_id="tf_input_load")
                tf_output_view   = gr.Button(elem_id="tf_output_view")
                tf_clear_btn     = gr.Button(elem_id="tf_clear_btn")
                tf_output_url    = gr.Textbox(value="", visible=False)
                
                filepath = os.path.join(HTML_DIR, 'tf_input_output_examples.html')
                tf_examples_html = js.build_html_text(filepath)
                tf_examples_html = gr.HTML(tf_examples_html)

        # Assign/Upload your structure
        str_check = gr.Checkbox(value=False, label="Provide PDB/AF2 ID or upload coordinate file (pdb/cif)", interactive=True)
        with gr.Row(visible=False) as structure_section:
            str_txt = gr.Textbox(value=None, label="Structure", placeholder="PDB ID (e.g., 1GOD) or AF2 ID (e.g., 014508)", interactive=True, show_label=False, scale=8)
            str_btn = gr.UploadButton("Upload file", file_count="single", elem_id="sav-btn", file_types=[".cif", ".pdb"], scale=3)
            str_file = gr.File(visible=False, scale=3, height=145)
        str_check.change(on_structure, str_check, [structure_section])

        # General info
        job_name_txt = gr.Textbox(value="", label="Job name", placeholder="Enter job name", interactive=True, elem_classes="gr-textbox")
        email_txt = gr.Textbox(value=None, label="Email (Optional)", placeholder="Enter your email", interactive=True, visible=False, type='email', elem_classes="gr-textbox")
        submit_btn = gr.Button("Submit", elem_classes="gr-button")

    # Fill test case
    inf_input_load.click(
           fn=on_load_example, inputs=[inf_input_example], outputs=[inf_sav_txt, str_check, str_btn, str_file, job_name_txt], js=js.load_inf_input
    ).then(fn=on_tandem_refresh, inputs=[param, job_name_txt], outputs=[param],)
    tf_input_load.click(
           fn=on_load_example, inputs=[tf_input_example], outputs=[tf_sav_txt, str_check, str_btn, str_file, job_name_txt], js=js.load_tf_input
    ).then(fn=on_tandem_refresh, inputs=[param, job_name_txt], outputs=[param],)

    inf_auto_view.click(
            fn=on_view_example, inputs=[inf_input_example], outputs=[inf_output_url], js=js.load_inf_input
    ).then(fn=passthrough_url, inputs=[inf_output_url], outputs=[inf_output_url], js=js.direct2url_open)
    tf_output_view.click(
            fn=on_view_example, inputs=[tf_input_example], outputs=[tf_output_url], js=js.load_tf_input
    ).then(fn=passthrough_url, inputs=[tf_output_url], outputs=[tf_output_url], js=js.direct2url_open)

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
        inf_section,
        tf_section,
        inf_sav_txt,
        inf_sav_btn,
        inf_sav_file,
        inf_auto_view,

        model_dropdown,
        
        tf_sav_txt,
        tf_sav_btn,
        tf_sav_file,
        tf_output_view,
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
                    pred_table = gr.Dataframe(interactive=False, max_height=340, show_label=False, column_widths=[60, 150, "auto", "auto"],)
                with gr.Column():
                    image_viewer = gr.Image(height=340, show_label=False, buttons=["fullscreen"])
        
        with gr.Group(visible=False) as tf_output_secion:
            with gr.Row():
                with gr.Column():
                    folds_state = gr.State(value={})
                    fold_dropdown = gr.Dropdown(label="View SAV set", choices=[], interactive=True, elem_classes="gr-button", elem_id="sav_dropdown", show_label=False)
                    sav_textbox = gr.Textbox(lines=1, interactive=False, show_label=False, elem_classes="gr-textbox", elem_id="sav_textbox", autoscroll=False)
                    fold_dropdown.change(fn=on_sav_set_select, inputs=[fold_dropdown, folds_state], outputs=sav_textbox)
                    test_evaluation = gr.Dataframe(interactive=False, max_height=250, show_label=False)
                loss_image = gr.Image(label="", show_label=False, height=364, buttons=["fullscreen"])
                # loss_image = gr.Image(label="", show_label=False, height=393)
            model_save = gr.Markdown(elem_classes="gr-p")
        result_zip = gr.File(label="Download Results")
        focus_refresh_btn = gr.Button(elem_id="focus_refresh_btn", visible=False)
        gr.HTML("""
        <script>
        (() => {
            if (window.__tandem_focus_refresh_bound__) return;
            window.__tandem_focus_refresh_bound__ = true;

            let lastTrigger = 0;
            const throttleMs = 500;
            const triggerRefresh = () => {
            const now = Date.now();
            if (now - lastTrigger < throttleMs) return;
            lastTrigger = now;

            const btn = document.getElementById("focus_refresh_btn");
            if (btn) btn.click();
            };

            document.addEventListener("visibilitychange", () => {
            if (!document.hidden) triggerRefresh();
            });
            window.addEventListener("focus", triggerRefresh);
        })();
        </script>
        """)
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
        focus_refresh_btn,
    )

def build_header(title, current_page="home"):
    filepath = os.path.join(HTML_DIR, 'header.html')
    nav_state = {
        "home_active": "is-active" if current_page == "home" else "",
        "tutorial_active": "is-active" if current_page == "tutorial" else "",
        "qa_active": "is-active" if current_page == "qa" else "",
        "licence_active": "is-active" if current_page == "licence" else "",
        "home_url": f"/{MOUNT_POINT}/",
        "tutorial_url": f"/{MOUNT_POINT}/tutorial/",
        "qa_url": f"/{MOUNT_POINT}/QA/",
        "licence_url": f"/{MOUNT_POINT}/licence/",
    }
    html = js.build_html_text(filepath, title=title, **nav_state)
    header = gr.HTML(html)
    return header

def build_footer():
    filepath = os.path.join(HTML_DIR, 'footer.html')
    html = js.build_html_text(filepath)
    footer = gr.HTML(html, elem_classes="footer")
    return footer

def build_qa():
    filepath = os.path.join(HTML_DIR, "QA.html")
    html = js.build_html_text(filepath)
    qa_page = gr.HTML(html, elem_classes="qa")
    return qa_page

def build_tutorial():
    filepath = os.path.join(HTML_DIR, "tutorial.html")
    html = js.build_html_text(filepath)
    tutorial_page = gr.HTML(html, elem_classes="tutorial")
    return tutorial_page

def build_licence():
    filepath = os.path.join(HTML_DIR, "licence.html")
    html = js.build_html_text(filepath)
    licence_page = gr.HTML(html, elem_classes="tutorial")
    return licence_page

if __name__ == "__main__":
    pass



"""
def on_tandem_refresh(param, example_name):
    param_udt = param.copy()
    param_udt["refresh"] = True
    LOGGER.info(f"example_name 1 {example_name}")
    if example_name == "GJB2 demo":
        LOGGER.info(f"example_name 2 {example_name}")
        param_udt["GJB2_test"] = True

    return param_udt


    # Fill test case
    inf_input_load.click(
           fn=on_load_example, inputs=[inf_input_example], outputs=[inf_sav_txt, str_check, str_btn, str_file, job_name_txt], js=js.load_inf_input
    ).then(fn=on_tandem_refresh, inputs=[param, inf_input_example], outputs=[param],)
    tf_input_load.click(
           fn=on_load_example, inputs=[tf_input_example], outputs=[tf_sav_txt, str_check, str_btn, str_file, job_name_txt], js=js.load_tf_input
    ).then(fn=on_tandem_refresh, inputs=[param, tf_input_example], outputs=[param],)

I want to check this function.

Why clicking submit button an input example, `example_name` return None
"INFO:     172.31.99.98:58602 - "POST /TANDEM-dev/session/gradio_api/queue/join?session_id=lS3KuxQxaW HTTP/1.1" 200 OK
@> example_name 1 None
INFO:     172.31.99.98:58602 - "GET /TANDEM-dev/session/gradio_api/queue/data?session_hash=9j2ft6l3u HTTP/1.1" 200 OK
INFO:     172.31.99.98:58602 - "POST /TANDEM-dev/session/gradio_api/queue/join?session_id=lS3KuxQxaW HTTP/1.1" 200 OK
INFO:     172.31.99.98:58602 - "GET /TANDEM-dev/session/gradio_api/queue/data?session_hash=9j2ft6l3u HTTP/1.1" 200 OK
INFO:     172.31.99.98:58602 - "POST /TANDEM-dev/session/gradio_api/queue/join?session_id=lS3KuxQxaW HTTP/1.1" 200 OK
@> ✅ Submitted with payload: {'refresh': True, 'status': 'pending', 'session_id': 'lS3KuxQxaW', 'session_url': '/TANDEM-dev/session/?session_id=lS3KuxQxaW', 'mode': 'Inferencing', 'SAV': ['O00187 R118C', 'O00187 D120G', 'O00187 T128M', 'O00187 H155R'], 'label': None, 'model': 'TANDEM', 'job_name': 'Inference_test_1p_11575411032026', 'email': None, 'STR': None, 'IP': '140.114.123.87', 'job_url': '/TANDEM-dev/results/?session_id=lS3KuxQxaW&job_name=Inference_test_1p_11575411032026'}
INFO:     172.31.99.98:58602 - "GET /TANDEM-dev/se"

please look for the reason first.

"""
