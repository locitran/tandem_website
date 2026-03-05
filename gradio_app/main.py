import os
import re
from urllib.parse import quote

import gradio as gr
import sass
import uvicorn
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, RedirectResponse
from pymongo import MongoClient
from starlette.convertors import Convertor, register_url_convertor

from src.home import home_page
from src.session import session_page, session_exists
from src.result import result_page
from src.settings import ASSETS_DIR, SASS_DIR, MOUNT_POINT
from src.logger import LOGGER 
from src.job_manager import job_page

sass.compile(dirname=(str(SASS_DIR), str(ASSETS_DIR)), output_style="expanded")
with open(os.path.join(ASSETS_DIR, "main.css")) as f:
    custom_css = f.read()

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

app = FastAPI()
app = gr.mount_gradio_app(app, session_page(), path="/session", allowed_paths=["/tandem/jobs", "assets/images"], css=custom_css)
app = gr.mount_gradio_app(app, result_page(), path="/result", allowed_paths=["/tandem/jobs", "assets/images"], css=custom_css)
app = gr.mount_gradio_app(app, job_page(), path="/jobs", allowed_paths=["/tandem/jobs", "assets/images"], css=custom_css)

class SessionIDConvertor(Convertor):
    regex = r"[A-Za-z0-9]{10}"

    def convert(self, value: str) -> str:
        return value

    def to_string(self, value: str) -> str:
        return value

register_url_convertor("sid", SessionIDConvertor())

@app.get("/jobs")
def job_page_redirect():
    return RedirectResponse(url=f"/jobs/", status_code=307)

@app.get("/{session_id:sid}/{job_name}")
def job_url(session_id: str, job_name: str):
    sid = session_id.strip()
    jn = job_name.strip()
    LOGGER.info(f"Received job URL request with session_id='{sid}', job_name='{jn}'")
    if not sid or not jn:
        return PlainTextResponse("Invalid job URL.", status_code=404)
    if not session_exists(sid):
        return PlainTextResponse("Session is down: session_id not found in MongoDB.", status_code=404)

    found = collections.find_one({"session_id": sid, "job_name": jn}, {"_id": 1})
    if found is None:
        return PlainTextResponse("Job is down: job_name not found in MongoDB.", status_code=404)

    return RedirectResponse(
        url=f"/result/?session_id={quote(sid, safe='')}&job_name={quote(jn, safe='')}", status_code=307,
    )

@app.get("/{session_id:sid}")
def session_url(session_id: str):
    cleaned = session_id.strip()
    LOGGER.info(f"Received session URL request with session_id: '{session_id}', cleaned: '{cleaned}'")
    if not cleaned:
        return RedirectResponse(url="/", status_code=307)
    if not session_exists(cleaned):
        return PlainTextResponse("Session is down: session_id not found in MongoDB.", status_code=404)
    return RedirectResponse(url=f"/session/?session_id={cleaned}", status_code=307)

# Mount home UI at "/" last so it becomes the default for everything else.
app = gr.mount_gradio_app(app, home_page(), path="/", allowed_paths=["/tandem/jobs", "assets/images"], css=custom_css, root_path=MOUNT_POINT)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7890)
