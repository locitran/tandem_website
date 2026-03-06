import os
import gradio as gr
import sass
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from pymongo import MongoClient

from src.home import home_page
from src.session import session_page
from src.results import results_page
from src.settings import ASSETS_DIR, SASS_DIR, MOUNT_POINT
from src.job_manager import job_page

allowed_paths = ["/tandem/jobs", "assets/images"]
sass.compile(dirname=(str(SASS_DIR), str(ASSETS_DIR)), output_style="expanded")
with open(os.path.join(ASSETS_DIR, "main.css")) as f:
    custom_css = f.read()

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

app = FastAPI()
app = gr.mount_gradio_app(app, session_page(), path=f"/{MOUNT_POINT}/session", allowed_paths=allowed_paths, css=custom_css)
app = gr.mount_gradio_app(app, results_page(), path=f"/{MOUNT_POINT}/results", allowed_paths=allowed_paths, css=custom_css)
app = gr.mount_gradio_app(app, job_page(), path=f"/{MOUNT_POINT}/jobs", allowed_paths=allowed_paths, css=custom_css)

@app.get(f"/{MOUNT_POINT}/jobs")
def job_page_redirect():
    return RedirectResponse(url=f"/{MOUNT_POINT}/jobs/", status_code=307) # url=f"./jobs/" is also fine

app = gr.mount_gradio_app(app, home_page(), path=f"/{MOUNT_POINT}", allowed_paths=allowed_paths, css=custom_css)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7861)
    # https://dyn.life.nthu.edu.tw/TANDEM-dev/jobs/
    # root_path=MOUNT_POINT
    # http://localhost:7862/TANDEM-dev/
    # https://dyn.life.nthu.edu.tw/TANDEM-dev/session?session_id=Sq1wvtriTw
    # https://dyn.life.nthu.edu.tw/TANDEM-dev/result?session_id=Sq1wvtriTw&job_name=abc