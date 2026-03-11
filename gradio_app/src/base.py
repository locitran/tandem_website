import gradio as gr

from .settings import TITLE
from .web_interface import build_footer, build_header
from .web_interface import build_qa, build_licence, build_tutorial

def qa_page():
    with gr.Blocks(title=TITLE) as page:
        build_header(TITLE, current_page="qa")
        with gr.Column(elem_id="main-content"):
            build_qa()
        build_footer()
    return page

def tutorial_page():
    with gr.Blocks(title=TITLE) as page:
        build_header(TITLE, current_page="tutorial")
        with gr.Column(elem_id="main-content"):
            build_tutorial()
        build_footer()
    return page

def licence_page():
    with gr.Blocks(title=TITLE) as page:
        build_header(TITLE, current_page="licence")
        with gr.Column(elem_id="main-content"):
            build_licence()
        build_footer()
    return page
