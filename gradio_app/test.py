import gradio as gr
import uvicorn
from fastapi import FastAPI

def second_page():
    with gr.Blocks() as page:
        gr.Markdown("This is the second page")
    return page

def home_page():
    with gr.Blocks() as page:
        gr.Markdown("This is the home page")
    return page

app = FastAPI(root_path="/TANDEM-dev")

app = gr.mount_gradio_app(app, home_page(), path="/home")
app = gr.mount_gradio_app(app, second_page(), path="/second")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7890)
    # http://localhost:7890/
    # http://localhost:7890/TANDEM-dev
    # http://localhost:7890/TANDEM-dev/second