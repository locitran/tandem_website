import os
import re

import gradio as gr
import sass
import uvicorn
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, RedirectResponse
from starlette.convertors import Convertor, register_url_convertor

from src.home import home_page
from src.session import session_page
from src.settings import ASSETS_DIR, JOB_DIR, MOUNT_POINT, SASS_DIR, TITLE
from src.web_interface import build_footer, build_header
from src.logger import LOGGER 
from src.update_session import collections, save_session_id, session_exists
from src.QA import qa
from src.job_manager import manager_tab
from src.tutorial import tutorial
from src.web_interface import tandem_input, left_column

sass.compile(dirname=(str(SASS_DIR), str(ASSETS_DIR)), output_style="expanded")
with open(os.path.join(ASSETS_DIR, "main.css")) as f:
    custom_css = f.read()

app = FastAPI()
app = gr.mount_gradio_app(app, session_page(), path="/session", allowed_paths=["/tandem/jobs", "assets/images"], css=custom_css)

class SessionIDConvertor(Convertor):
    regex = r"[A-Za-z0-9]{10}"

    def convert(self, value: str) -> str:
        return value

    def to_string(self, value: str) -> str:
        return value

register_url_convertor("sid", SessionIDConvertor())

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
app = gr.mount_gradio_app(app, home_page(), path="/", allowed_paths=["/tandem/jobs", "assets/images"], css=custom_css)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7861)
