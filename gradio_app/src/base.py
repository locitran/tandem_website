import os
from datetime import datetime
import gradio as gr

from . import js
from .settings import HTML_DIR, TITLE, MOUNT_POINT, TAIPEI_TIME_ZONE

def build_header(title, current_page="home"):
    filepath = os.path.join(HTML_DIR, "header.html")
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
    return gr.HTML(html)

def build_footer():
    filepath = os.path.join(HTML_DIR, "footer.html")
    html = js.build_html_text(filepath)
    return gr.HTML(html, elem_classes="footer")

def build_qa():
    filepath = os.path.join(HTML_DIR, "QA.html")
    html = js.build_html_text(filepath)
    return gr.HTML(html, elem_classes="qa")

def build_tutorial():
    filepath = os.path.join(HTML_DIR, "tutorial.html")
    html = js.build_html_text(filepath)
    return gr.HTML(html, elem_classes="tutorial")

def build_licence():
    filepath = os.path.join(HTML_DIR, "licence.html")
    html = js.build_html_text(filepath)
    return gr.HTML(html, elem_classes="tutorial")

def build_last_updated():
    latest_ts = max(
        os.path.getmtime(os.path.join(HTML_DIR, "header.html")),
        os.path.getmtime(os.path.join(HTML_DIR, "footer.html")),
        os.path.getmtime(__file__),
    )
    updated = datetime.fromtimestamp(latest_ts, tz=TAIPEI_TIME_ZONE).strftime("%Y-%m-%d %H:%M")
    return gr.Markdown(f"<div class='last-updated'>Last updated of the website: {updated}</div>")

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
