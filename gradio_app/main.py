import os
import sass
import uvicorn
import gradio as gr
from fastapi import FastAPI
from pymongo import MongoClient
from fastapi.responses import RedirectResponse

from src.home import home_page
from src.session import session_page
from src.results import results_page
from src.error import error_page
from src.job_manager import job_page
from src.base import qa_page, tutorial_page, licence_page
from src.settings import ASSETS_DIR, SASS_DIR, MOUNT_POINT

allowed_paths = ["/tandem/jobs", "assets/images"]
sass.compile(dirname=(str(SASS_DIR), str(ASSETS_DIR)), output_style="expanded")
with open(os.path.join(ASSETS_DIR, "main.css")) as f:
    custom_css = f.read()

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

app = FastAPI()
app = gr.mount_gradio_app(app, error_page(), path=f"/{MOUNT_POINT}/error", allowed_paths=allowed_paths, css=custom_css, root_path=f"/{MOUNT_POINT}/error")
app = gr.mount_gradio_app(app, session_page(), path=f"/{MOUNT_POINT}/session", allowed_paths=allowed_paths, css=custom_css, root_path=f"/{MOUNT_POINT}/session")
app = gr.mount_gradio_app(app, results_page(), path=f"/{MOUNT_POINT}/results", allowed_paths=allowed_paths, css=custom_css, root_path=f"/{MOUNT_POINT}/results")
app = gr.mount_gradio_app(app, job_page(), path=f"/{MOUNT_POINT}/jobs", allowed_paths=allowed_paths, css=custom_css, root_path=f"/{MOUNT_POINT}/jobs")

app = gr.mount_gradio_app(app, qa_page(), path=f"/{MOUNT_POINT}/QA", allowed_paths=allowed_paths, css=custom_css, root_path=f"/{MOUNT_POINT}/QA")
app = gr.mount_gradio_app(app, tutorial_page(), path=f"/{MOUNT_POINT}/tutorial", allowed_paths=allowed_paths, css=custom_css, root_path=f"/{MOUNT_POINT}/tutorial")
app = gr.mount_gradio_app(app, licence_page(), path=f"/{MOUNT_POINT}/licence", allowed_paths=allowed_paths, css=custom_css, root_path=f"/{MOUNT_POINT}/licence")


@app.get(f"/{MOUNT_POINT}/jobs")
def job_page_redirect():
    return RedirectResponse(url=f"/{MOUNT_POINT}/jobs/", status_code=307) # url=f"./jobs/" is also fine

@app.get(f"/{MOUNT_POINT}/QA")
def qa_page_redirect():
    return RedirectResponse(url=f"/{MOUNT_POINT}/QA/", status_code=307) # url=f"./qa/" is also fine

@app.get(f"/{MOUNT_POINT}/tutorial")
def tutorial_page_redirect():
    return RedirectResponse(url=f"/{MOUNT_POINT}/tutorial/", status_code=307) # url=f"./tutorial/" is also fine

@app.get(f"/{MOUNT_POINT}/licence")
def licence_page_redirect():
    return RedirectResponse(url=f"/{MOUNT_POINT}/licence/", status_code=307) # url=f"./licence/" is also fine

app = gr.mount_gradio_app(app, home_page(), path=f"/{MOUNT_POINT}", allowed_paths=allowed_paths, css=custom_css, root_path=f"/{MOUNT_POINT}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7861)
    # https://dyn.life.nthu.edu.tw/TANDEM-dev/jobs/
    # root_path=MOUNT_POINT
    # http://localhost:7862/TANDEM-dev/
    # https://dyn.life.nthu.edu.tw/TANDEM-dev/session?session_id=Sq1wvtriTw
    # https://dyn.life.nthu.edu.tw/TANDEM-dev/result?session_id=Sq1wvtriTw&job_name=abc
