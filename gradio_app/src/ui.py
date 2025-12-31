import os 
import gradio as gr

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
        # msg, state = f"✅ Received 1 file.", True
        msg = ""
        state = True
        pass
    
    filename = os.path.basename(filepath)
    return [gr.update(visible=True, 
                    #   label="Re-upload file"
                      ),
            f"✅ **{filename}** uploaded!\n\n{msg}", state]

def UI_SAVinput():
    gr.Markdown("UniProt ID with Single Amino Acid Variant (SAV)", elem_classes="boxed-markdown")
    with gr.Row(elem_classes="sav-query"):
        
        sav_txt_state = gr.State(False)
        sav_btn_state = gr.State(False)
        
        with gr.Column(scale=5, min_width=320):
            sav_txt = gr.Textbox(
                show_label=False,
                placeholder="O14508 52 S N\nP29033 217 Y D\n...",
                max_lines=5,
                lines=4,
                elem_id="textbox",
            )
            sav_txt_msg = gr.Markdown(elem_classes="boxed-markdown")
            sav_txt.change(process_sav_txt, sav_txt, [gr.State(False), sav_txt_msg, sav_txt_state])

        with gr.Column(scale=3, min_width=200):
            sav_btn = gr.UploadButton(
                label="Upload SAVs",
                file_count="single",
                elem_id="upload-btn",
                file_types=[".txt"],
            )
            # sav_btn_msg = gr.Markdown("Upload a text file (≤150KB)", elem_id="btn-msg")
            sav_btn_msg = gr.Markdown(elem_classes="boxed-markdown")
            sav_btn.upload(upload_file, [sav_btn, gr.State('SAV')], [sav_btn, sav_btn_msg, sav_btn_state])
    
    return sav_txt, sav_txt_state, sav_btn, sav_btn_state

def UI_STRinput():
    
    def _toggle(checked: bool):
        return [
            gr.update(visible=checked),
            gr.update(visible=checked),
            gr.update(interactive=True),
            gr.update(interactive=True),
        ]
        
    checkbox = gr.Checkbox(
        label="Assign or upload your structure",
        value=False, # unchecked by default
        elem_classes="checkbox",
    )
    gr_markdown = gr.Markdown("PDB ID or AlphaFoldF2 ID", visible=False, elem_classes="boxed-markdown")
    with gr.Row(visible=False, elem_classes="custom-str") as custom_str:

        str_txt_state = gr.State(False)
        str_btn_state = gr.State(False)
        with gr.Column(scale=5, min_width=320):
            
            str_txt = gr.Textbox(
                show_label=False,
                placeholder="1G0D or O14508",
                lines=1,
                elem_id="textbox",
                interactive=False,
            )
            str_txt_msg = gr.Markdown()
            str_txt.change(process_structure_txt, str_txt, [str_txt_msg, str_txt_state])
            
        with gr.Column(scale=3, min_width=200):
            str_btn = gr.UploadButton(
                label="Upload structure",
                file_count="single",
                file_types=[".cif", ".pdb"],
                elem_id="upload-btn",
                interactive=False,
            )
            # str_btn_msg = gr.Markdown("Upload a customized structure file (.cif/.pdb, ≤150KB)", elem_id="btn-msg")
            str_btn_msg = gr.Markdown(elem_classes="boxed-markdown")
            str_btn.upload(upload_file, [str_btn, gr.State('STR')], [str_btn, str_btn_msg, str_btn_state])
    
    checkbox.change(_toggle, checkbox, [gr_markdown, custom_str, str_txt, str_btn])
    return str_txt, str_txt_state, str_btn, str_btn_state

upload_file('/mnt/nas_1/YangLab/loci/tandem/test.txt')