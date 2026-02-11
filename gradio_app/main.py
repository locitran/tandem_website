import os

import sass
import gradio as gr

from src.home import HomeTab
from src.web_interface import build_footer, build_header
from src.job_manager import manager_tab
from src.QA import qa
from src.tutorial import tutorial
from src.settings import (
    ASSETS_DIR,
    JOB_DIR,
    MOUNT_POINT,
    SASS_DIR,
    TITLE,
)

sass.compile(dirname=(str(SASS_DIR), str(ASSETS_DIR)), output_style="expanded")
with open(os.path.join(ASSETS_DIR, "main.css")) as f:
    custom_css = f.read()

class TandemApp:
    def __init__(self, css, job_dir, mount_point, title):
        self.css = css
        self.job_dir = job_dir
        self.mount_point = mount_point
        self.title = title

    def build(self):
        with gr.Blocks(title=self.title) as self.demo:
            # ---------- HEADER ---------- uXXF0nC3qJ QVP4GRh26k
            build_header(self.title)

            # ---------- MAIN CONTENT (with tabs) ----------
            with gr.Column(elem_id="main-content"):
                with gr.Tab("Home"):
                    self.home_tab = HomeTab(self.job_dir).build()
                with gr.Tab(label="🗂️ Job Manager", id='job'):
                    manager_tab()
                with gr.Tab(label="Q & A"):
                    qa(self.mount_point)
                with gr.Tab(label="Tutorial"):
                    tutorial(self.mount_point)
                    
            build_footer(self.mount_point)

        return self.demo

if __name__ == "__main__":
    app = TandemApp(
        css=custom_css,
        job_dir=JOB_DIR,
        mount_point=MOUNT_POINT,
        title=TITLE,
    )
    demo = app.build()
    demo.queue()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,
        css=custom_css,
        allowed_paths=[
            "/tandem/jobs", 
            "assets/images",
        ],
        root_path=MOUNT_POINT,
        favicon_path=os.path.join(ASSETS_DIR, "images", "nthu_favicon.png")
    )
