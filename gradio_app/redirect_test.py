import os
import re
import uuid
from urllib.parse import quote

import gradio as gr
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

ROOT_URL = os.getenv("ROOT_URL", "http://127.0.0.1:7890").rstrip("/")
RESERVED_PATHS = {"docs", "redoc", "openapi.json", "favicon.ico", "create", "u"}
USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def build_user_url(root_url: str, user_id: str):
    root = (root_url or "").strip().rstrip("/")
    identifier = (user_id or "").strip()

    if not root:
        return "", "Please provide a root URL."
    if not identifier:
        return "", "Please provide a user identifier."

    target_url = f"{root}/{quote(identifier, safe='')}"
    return target_url, f"Ready: {target_url}"


def generate_user_id() -> tuple[str, str]:
    # Example output: user_a1b2c3d4e5f6
    new_id = f"user_{uuid.uuid4().hex[:12]}"
    return new_id, f"Generated user ID: `{new_id}`"


with gr.Blocks() as demo:
    with gr.Row():
        root_url = gr.Textbox(label="Root URL", value=ROOT_URL, placeholder="http://127.0.0.1:7890",)
        user_id = gr.Textbox(label="User Identifier", value="user_123", placeholder="e.g. user_123",)

    with gr.Row():
        gen_id_btn = gr.Button("Generate User ID")
        go_btn = gr.Button("Open User URL", variant="primary")
    target_url = gr.Textbox(label="Generated URL", interactive=False)
    status = gr.Markdown()

    gen_id_btn.click(fn=generate_user_id, inputs=[], outputs=[user_id, status],)
    
    go_btn.click(
        fn=build_user_url, inputs=[root_url, user_id], outputs=[target_url, status],
    ).then(fn=None,inputs=[target_url],outputs=[],
        js="""
            (url) => {
                if (!url) return;
                window.open(url, "_self");
            }
            """,)

with gr.Blocks() as user_demo:
    user_markdown = gr.Markdown()
    user_id_box = gr.Textbox(label="User Identifier", interactive=False)
    def render_user_page(request: gr.Request):
        user_id = "guest"
        if request is not None:
            user_id = request.query_params.get("user_id", "guest")
        user_id = (user_id or "guest").strip()
        return (
            f"# User Gradio Page\nThis page is created for: `{user_id}`",
            user_id,
        )
    user_demo.load(fn=render_user_page, inputs=None, outputs=[user_markdown, user_id_box])


app = FastAPI()
@app.get("/")
def root():
    return RedirectResponse(url="/create/", status_code=307)

@app.get("/{user_id}")
def user_route(user_id: str):
    cleaned_user_id = user_id.strip()

    if not cleaned_user_id or cleaned_user_id in RESERVED_PATHS:
        raise HTTPException(status_code=404, detail="Not found")
    if not USER_ID_PATTERN.fullmatch(cleaned_user_id):
        raise HTTPException(status_code=404, detail="Not found")

    encoded = quote(cleaned_user_id, safe="")
    return RedirectResponse(url=f"/u/?user_id={encoded}", status_code=307)

app = gr.mount_gradio_app(app, demo, path="/create")
app = gr.mount_gradio_app(app, user_demo, path="/u")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7890)
