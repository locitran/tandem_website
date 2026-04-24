import html
import os

from pymongo import MongoClient

from .. import js
from ..request import build_job_url, build_session_url
from ..settings import HTML_DIR

TOPBAR_TEMPLATE = os.path.join(HTML_DIR, "results_topbar.html")

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]


def build_topbar_html(param, session_id, job_name, job_status):
    """Build the right-side results metadata panel.

    Inputs:
    - param: current job metadata dict.
    - session_id: current session id string.
    - job_name: current job name string.
    - job_status: current job status string.

    Output:
    - HTML string for the results-side panel.
    """
    param_udt = param.copy() if isinstance(param, dict) else {}
    session_id_udt = session_id or param_udt.get("session_id", "")
    current_job = job_name or param_udt.get("job_name", "")
    job_status_udt = job_status or param_udt.get("status", "")

    if not session_id_udt:
        return js.build_html_text(
            TOPBAR_TEMPLATE,
            session_id="-",
            options='<option value="">No jobs</option>',
            new_job_html="",
            cancel_job_html="",
        )

    job_list = collections.distinct(
        "job_name",
        {"session_id": session_id_udt, "status": {"$in": ["pending", "processing", "finished"]}},
    )
    job_list = sorted(job_list)

    option_html = []
    for item in job_list:
        selected = " selected" if item == current_job else ""
        url = build_job_url(session_id_udt, item)
        safe_url = html.escape(url, quote=True)
        safe_label = html.escape(item)
        option_html.append(f'<option value="{safe_url}"{selected}>{safe_label}</option>')

    options = "\n".join(option_html) if option_html else '<option value="">No jobs</option>'

    new_job_html = ""
    cancel_job_html = ""
    launch_session_id = param_udt.get("launch_session_id", "")
    target_session_id = launch_session_id or session_id_udt
    if target_session_id != "test":
        session_url = build_session_url(target_session_id)
        safe_session_url = html.escape(session_url, quote=True)
        new_job_html = f"""
        <div class="action-row">
            <a class="mini-action-link" href="{safe_session_url}">New job</a>
        </div>
        """
        if job_status_udt in {"pending", "processing"}:
            cancel_job_html = """
            <div class="action-row">
                <button
                    type="button"
                    class="mini-action-link mini-action-button cancel-job-link"
                    onclick="document.querySelector('#cancel_job_btn button, #cancel_job_btn')?.click();"
                >Cancel job</button>
            </div>
            """

    return js.build_html_text(
        TOPBAR_TEMPLATE,
        session_id=html.escape(session_id_udt),
        options=options,
        new_job_html=new_job_html,
        cancel_job_html=cancel_job_html,
    )
