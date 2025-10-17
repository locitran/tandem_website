import os 
from pathlib import Path
import gradio as gr

# from ..main import tandem_dimple
from .SAV_handler import _read_text_file_safely, process_sav_txt, handle_sav_input
from .STR_handler import process_structure_txt

MAX_BYTES = 8 * 1e+6 # 8M 

def upload_file(filepath, _type='SAV'):
    """
    Input: Gradio UploadedFile or a path str (depends on version).
    Output: (UploadButton update, DownloadButton update, message string)
    """
    
    if not os.path.exists(filepath):
        return [gr.update(visible=True, label="Re-upload file"),
                f"❌ No file received.", False]

    # Size guard
    try:
        size = os.path.getsize(filepath)
        if size > MAX_BYTES:
            return [gr.update(visible=True, label="Re-upload file"),
                    f"❌ File too large ({size} bytes). Max allowed is 8M bytes.", False]
    except OSError:
        pass
    
    if _type == 'SAV':
        # Read & parse
        txt = _read_text_file_safely(filepath)
        _, msg, state = process_sav_txt(txt)
    elif _type == 'STR': # structure file
        msg, state = f"✅ Received 1 file.", True
        pass
    
    filename = os.path.basename(filepath)
    return [gr.update(visible=True, label="Re-upload file"),
            f"✅ **{filename}** uploaded!\n{msg}", state]

def UI_SAVinput():
    with gr.Row(elem_classes="sav-query"):
        
        sav_txt_state = gr.State(False)
        sav_btn_state = gr.State(False)
        
        with gr.Column(scale=5, min_width=320):
            sav_txt = gr.Textbox(
                label="Paste UniProt ID with Single Amino Acid Variant (SAV)",
                placeholder="O14508 S52N\nP29033 Y217D\n...",
                max_lines=5,
                lines=4,
                elem_id="sav-txt",
            )
            sav_txt_msg = gr.Markdown()
            sav_txt.change(process_sav_txt, sav_txt, [gr.State(False), sav_txt_msg, sav_txt_state])

        with gr.Column(scale=3, min_width=200):
            gr.Markdown("Or")
            sav_btn = gr.UploadButton(
                label="Choose file",
                file_count="single",
                elem_id="sav-btn",
                file_types=[".txt"],
                
            )
            sav_btn_msg = gr.Markdown("File size limit: 150KB", elem_id="btn-msg")
            sav_btn.upload(upload_file, [sav_btn, gr.State('SAV')], [sav_btn, sav_btn_msg, sav_btn_state])
    
    return sav_txt, sav_txt_state, sav_btn, sav_btn_state

def UI_STRinput():
    
    with gr.Row(elem_classes="custom-str") as custom_str:

        str_txt_state = gr.State(False)
        str_btn_state = gr.State(False)
        with gr.Column(scale=5, min_width=320):
            str_txt = gr.Textbox(
                label="Paste PDB/AF2 ID",
                placeholder="PDB ID (e.g., 1G0D) or AF2 ID (e.g., O14508)\nLeave blank to let us generate structure for you",
                lines=4,
                elem_id="custom-str-txt",
            )
            str_txt_msg = gr.Markdown()
            str_txt.change(process_structure_txt, str_txt, [str_txt_msg, str_txt_state])
            
        with gr.Column(scale=3, min_width=200):
            gr.Markdown("Or")
            str_btn = gr.UploadButton(
                label="Upload a .cif/.pdb file",
                file_count="single",
                file_types=[".cif", ".pdb"],
                elem_id="button",
            )
            str_btn_msg = gr.Markdown("Upload a .cif/.pdb file (≤8MB)", elem_id="btn-msg")
            str_btn.upload(upload_file, [str_btn, gr.State('STR')], [str_btn, str_btn_msg, str_btn_state])
    
    return str_txt, str_txt_state, str_btn, str_btn_state

# def submit_job(
#         session_id,
#         sav_txt, sav_txt_state, sav_btn, sav_btn_state,
#         str_txt, str_txt_state, str_btn, str_btn_state
#     ):
    
#     if sav_btn_state:
#         SAV_input = sav_btn
#     elif sav_txt_state:
#         SAV_input = sav_txt
#     else:
#         SAV_input = None
    
#     SAV_input = handle_sav_input(SAV_input)
    
#     if str_btn_state:
#         STR_input = str_btn
#     elif str_txt_state:
#         STR_input = str_txt
#     else:
#         STR_input = None
    
#     td = tandem_dimple(
#         query=SAV_input,
#         job_name=str(session_id),
#         custom_PDB=STR_input,
#         refresh=False,
#     )  
