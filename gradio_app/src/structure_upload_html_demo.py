import os

import gradio as gr


UPLOAD_STYLE = """
<style>
    .structure-upload-demo {
        width: 100%;
        align-self: flex-end;
    }

    #str-upload-btn {
        position: absolute !important;
        inset: 0 !important;
        opacity: 0 !important;
        z-index: 2 !important;
        min-height: 42px !important;
    }

    #str-upload-btn button,
    #str-upload-btn label,
    #str-upload-btn input {
        width: 100% !important;
        min-height: 42px !important;
        cursor: pointer !important;
    }

    #str-upload-file,
    #str-clear-btn {
        display: none !important;
    }

    .native-file-shell {
        width: 100%;
        min-height: 42px;
        display: flex;
        align-items: stretch;
        overflow: hidden;
        box-sizing: border-box;
        border: 1px solid #b8b8b8;
        border-radius: 4px;
    }

    .native-file-button {
        display: inline-flex;
        align-items: center;
        padding: 0 14px;
        font-size: 14px;
        white-space: nowrap;
        border-right: 1px solid #b8b8b8;
    }

    .native-file-name {
        flex: 1;
        display: inline-flex;
        align-items: center;
        padding: 0 12px;
        font-size: 14px;
        min-width: 0;
    }

    .file-card {
        width: 100%;
        min-height: 42px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 0 12px;
        box-sizing: border-box;
    }

    .file-name {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 14px;
        min-width: 0;
    }
</style>
"""


UPLOAD_ROW_HTML = UPLOAD_STYLE + """
<div class="structure-upload-demo">
    <div class="native-file-shell">
        <span class="native-file-button">Choose File</span>
        <span class="native-file-name">No file chosen</span>
    </div>
</div>
"""


def uploaded_row_html(filename: str) -> str:
    return UPLOAD_STYLE + f"""
<div class="structure-upload-demo">
    <div class="native-file-shell">
        <button class="clear-input-btn native-file-button" type="button" onclick="document.getElementById('str-clear-btn')?.click();">
            Clear file
        </button>
        <span class="native-file-name">{filename}</span>
    </div>
</div>
"""


def on_str_upload(file):
    upload_html_udt = gr.update(value=UPLOAD_ROW_HTML, visible=True)
    str_upload_btn_udt = gr.update(visible=True)
    str_upload_file_udt = gr.update(value="")

    if file is None:
        return (
            upload_html_udt,
            str_upload_btn_udt,
            str_upload_file_udt,
        )

    filepath = str(file)
    if not os.path.exists(filepath):
        return (
            upload_html_udt,
            str_upload_btn_udt,
            str_upload_file_udt,
        )

    filename = os.path.basename(filepath)
    upload_html_udt = gr.update(value=uploaded_row_html(filename), visible=True)
    str_upload_btn_udt = gr.update(visible=False)
    str_upload_file_udt = gr.update(value=filepath)
    return (
        upload_html_udt,
        str_upload_btn_udt,
        str_upload_file_udt,
    )


def on_str_clear():
    upload_html_udt = gr.update(value=UPLOAD_ROW_HTML, visible=True)
    str_upload_btn_udt = gr.update(value=None, visible=True)
    str_upload_file_udt = gr.update(value="")
    return (
        upload_html_udt,
        str_upload_btn_udt,
        str_upload_file_udt,
    )

def build_demo():
    with gr.Blocks() as page:
        with gr.Group():

            with gr.Group():
                label = "Paste single amino acid variants for one or multiple proteins (≤4) and the corresponding labels"
                info = "using the format - (UniProt_ID)(space)(WT_AA|ResidueID|Mutant_AA)(space)(Label)"
                placeholder = "O14508 S52N 1\nP29033 Y217D 0\n..."
                tf_sav_txt = gr.Textbox(max_lines=5, lines=5,elem_id="tf-sav-txt",label=label,placeholder=placeholder,elem_classes="gr-textbox",info=info,)

            with gr.Row():
                label = "Provide PDB/AF2 ID or upload coordinate file (pdb/cif)"
                placeholder="PDB ID (e.g., 1GOD) or AF2 ID (e.g., 014508)"
                str_upload_text = gr.Textbox(value=None,label=label,placeholder=placeholder,interactive=True,scale=2, show_label=True)

                upload_html = gr.HTML(UPLOAD_ROW_HTML)
                str_upload_btn = gr.UploadButton("str_upload_btn",file_count="single",elem_id="str-upload-btn",file_types=[".cif", ".pdb"])
                str_upload_file = gr.Markdown(value="", elem_id="str-upload-file")
                str_clear_btn = gr.Button(elem_id="str-clear-btn")

            outputs=[upload_html, str_upload_btn, str_upload_file]
            str_upload_btn.upload(fn=on_str_upload,inputs=[str_upload_btn],outputs=outputs,)
            str_clear_btn.click(fn=on_str_clear,inputs=[],outputs=outputs,)

    return page

demo = build_demo()
demo.launch(server_name="127.0.0.1", server_port=7900)
