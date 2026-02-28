import os
import secrets
import string
from urllib.parse import quote

import gradio as gr
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from starlette.convertors import Convertor, register_url_convertor  # Starlette routing converters

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "7863"))
ROOT_URL = os.getenv("ROOT_URL", f"http://{HOST}:{PORT}")


def generate_token(length=10):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def session_id2url(root_url: str, session_id: str) -> str:
    root = (root_url or "").strip().rstrip("/")
    sid = (session_id or "").strip()
    if not root or not sid:
        return ""
    return f"{root}/{quote(sid, safe='')}"


def create_session_url(root_url: str):
    sid = generate_token(10)
    url = session_id2url(root_url, sid)
    return sid, url, f"Generated session: `{sid}`"


def render_session_page(request: gr.Request):
    sid = "unknown"
    if request is not None:
        sid = request.query_params.get("session_id", "unknown")
    return f"# Session Page\nCurrent session ID: `{sid}`"


with gr.Blocks(title="Session Redirect Test") as home_demo:
    gr.Markdown("## Home Page")
    gr.Markdown("Click the button to generate a session ID and jump to its URL.")
    root_url = gr.Textbox(label="Root URL", value=ROOT_URL)
    session_id = gr.Textbox(label="Session ID", interactive=False)
    session_url = gr.Textbox(label="Session URL", interactive=False)
    status = gr.Markdown()
    start_btn = gr.Button("▶️ Start / Resume a Session", variant="primary")

    (
        start_btn.click(
            fn=create_session_url,
            inputs=[root_url],
            outputs=[session_id, session_url, status],
        ).then(
            fn=None,
            inputs=[session_url],
            outputs=[],
            js="""
            (url) => {
                if (!url) return;
                window.location.assign(url);
            }
            """,
        )
    )


with gr.Blocks(title="Session Page") as session_demo:
    session_markdown = gr.Markdown()
    session_demo.load(fn=render_session_page, inputs=None, outputs=[session_markdown])


# 1) Register a converter that matches ONLY your generated session IDs.
#    Starlette supports custom converters with a regex. citeturn1view0
class SessionIDConvertor(Convertor):
    # exactly 10 chars from [A-Za-z0-9], consistent with generate_token(10)
    regex = r"[A-Za-z0-9]{10}"

    def convert(self, value: str) -> str:
        return value

    def to_string(self, value: str) -> str:
        return value


register_url_convertor("sid", SessionIDConvertor())

app = FastAPI()

# 2) Mount session UI first (specific prefix).
app = gr.mount_gradio_app(app, session_demo, path="/session")

# 3) Dispatcher: only matches /{session_id} if it fits the converter regex.
@app.get("/{session_id:sid}")
def session_route(session_id: str):
    return RedirectResponse(
        url=f"/session/?session_id={quote(session_id, safe='')}",
        status_code=307,
    )

# 4) Mount home UI at "/" last so it becomes the default for everything else.
app = gr.mount_gradio_app(app, home_demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
