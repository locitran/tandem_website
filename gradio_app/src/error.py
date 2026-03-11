import gradio as gr

from .settings import TITLE, MOUNT_POINT
from .web_interface import build_footer, build_header


def _error_content(request: gr.Request):
    kind = (request.query_params.get("kind", "") or "").strip()
    session_id = (request.query_params.get("session_id", "") or "").strip()
    job_name = (request.query_params.get("job_name", "") or "").strip()

    home_url = f"/{MOUNT_POINT}/"
    session_url = f"/{MOUNT_POINT}/session/?session_id={session_id}" if session_id else home_url

    title = "Invalid link"
    message = "The link is incomplete or no longer valid."

    if kind == "missing_session":
        title = "Session ID is missing"
        message = "This URL does not include a session ID."
    elif kind == "session_not_found":
        title = "Session not found"
        message = f'Session ID "{session_id}" does not exist in the database.'
    elif kind == "missing_job":
        title = "Job name is missing"
        message = f'The results URL for session "{session_id}" does not include a job name.'
    elif kind == "job_not_found":
        title = "Job not found"
        message = f'Job "{job_name}" was not found under session "{session_id}".'

    actions = [
        f'<a class="primary-link" href="{home_url}">Go to Home</a>',
    ]
    if kind in {"missing_job", "job_not_found"} and session_id:
        actions.append(f'<a class="secondary-link" href="{session_url}">Open Session</a>')

    body = f"""
    <div class="error-page">
        <div class="error-card">
            <h2>{title}</h2>
            <p>{message}</p>
            <div class="error-actions">{''.join(actions)}</div>
        </div>
    </div>
    """
    return gr.update(value=body)


def error_page():
    with gr.Blocks(title=TITLE) as page:
        build_header(TITLE, current_page="home")
        with gr.Column(elem_id="main-content"):
            error_body = gr.HTML()
        build_footer()

        page.load(fn=_error_content, inputs=None, outputs=[error_body], queue=False)

    return page
