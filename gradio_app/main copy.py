import os
import re

import gradio as gr
import sass
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from src.QA import qa
from gradio_app.src.home import HomeTab
from src.job_manager import manager_tab
from src.settings import ASSETS_DIR, JOB_DIR, MOUNT_POINT, SASS_DIR, TITLE
from src.tutorial import tutorial
from src.web_interface import build_footer, build_header
from gradio_app.src.session import SessionPage

sass.compile(dirname=(str(SASS_DIR), str(ASSETS_DIR)), output_style="expanded")
with open(os.path.join(ASSETS_DIR, "main.css")) as f:
    custom_css = f.read()

SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
RESERVED_PATHS = {"home", "session", "job-manager", "qa", "tutorial"}

def home_page():
    with gr.Blocks() as page:
        gr.Navbar(visible=True)
        with gr.Column(elem_id="main-content"):
            build_header(TITLE)
            HomeTab(JOB_DIR).build()
            build_footer(MOUNT_POINT)
    
    with page.route("🗂️ Job Manager"):
        gr.Navbar(visible=True)
        with gr.Column(elem_id="main-content"):
            build_header(TITLE)
            manager_tab()
            build_footer(MOUNT_POINT)

    with page.route("Q & A"):
        gr.Navbar(visible=True)
        with gr.Column(elem_id="main-content"):
            build_header(TITLE)
            qa(MOUNT_POINT)
            build_footer(MOUNT_POINT)

    with page.route("Tutorial"):
        gr.Navbar(visible=True)
        with gr.Column(elem_id="main-content"):
            build_header(TITLE)
            tutorial(MOUNT_POINT)
            build_footer(MOUNT_POINT)
                
    return page

# def session_page(folder):
    # with gr.Blocks() as page:
    #     gr.Navbar(visible=True)
    #     with gr.Column(elem_id="main-content"):
    #         build_header(TITLE)
    #         SessionPage(folder).build()
    #         build_footer(MOUNT_POINT)

    # return page

def session_page(request: gr.Request):
    sid = "unknown"
    if request is not None:
        sid = request.query_params.get("session_id", "unknown")
    return f"# Session Page\nCurrent session ID: `{sid}`"

app = FastAPI()
app = gr.mount_gradio_app(app, home_page(), path="/home", allowed_paths=["/tandem/jobs", "assets/images"], css=custom_css)
app = gr.mount_gradio_app(app, session_page(), path="/session", allowed_paths=["/tandem/jobs", "assets/images"], css=custom_css)

@app.get("/")
def root():
    return RedirectResponse(url="/home/", status_code=307)

@app.get("/{session_id}")
def session_url(session_id: str):
    cleaned = session_id.strip()
    if not cleaned:
        return RedirectResponse(url="/home/", status_code=307)
    if cleaned in RESERVED_PATHS:
        return RedirectResponse(url=f"/{cleaned}/", status_code=307)
    return RedirectResponse(url=f"/session/?session_id={cleaned}", status_code=307)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7861)
