import json 
import pandas as pd 
import gradio as gr
import os 
import secrets
import gradio as gr
import string

from .logger import LOGGER


from pymongo import MongoClient

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

def generate_token(length=10):
    alphabet = string.ascii_letters + string.digits  # A–Z, a–z, 0–9
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def on_session(_session_id, param):
    """
    1. Start session by generating new id or providing old id
    2. Update parameter state (status and session_id)
    3. Update dropdown of pre-trained models to include trained models from user
        Look up all jobs of session_id to find inference jobs which were finished.

    If id is not valid, no session id is recorded
    """
    old_session_ids = collections.distinct("session_id")
    _session_id = _session_id.strip()
    param_udt = param.copy()
    param_udt['status'] = None
    param_udt["session_id"] = None
    job_dropdown_upt = gr.update(visible=False)
    model_dropdown_udt = gr.update()
    model_choices = ["TANDEM", "TANDEM-DIMPLE for GJB2", "TANDEM-DIMPLE for RYR1"]
    session_btn_udt = gr.update(interactive=False)

    # Case 1: Empty input → Generate a new unique session ID
    if not _session_id:
        # loop until finding an unused ID (guaranteed uniqueness)
        while True:
            new_id = generate_token(length=10) 
            # if new_id overlap with old one --> redo
            if new_id not in old_session_ids:
                session_id_udt = gr.update(value=new_id, interactive=False)
                session_status_udt = f"🔄 New session ID has been generated. <br>ℹ️ Please save the session ID for future reference."
                param_udt["session_id"] = new_id
                session_mkd_udt = gr.update(visible=False, value="")
                break
    # Case 2: User-provided input, check validity
    elif _session_id not in old_session_ids:
        session_id_udt = gr.update(value="", interactive=True)
        session_status_udt = f"Please generate or paste a valid one."
        session_btn_udt = gr.update(interactive=True)
        session_mkd_udt = gr.update()
        gr.Warning(session_status_udt)
    # Case 3: Valid existing session
    else:
        param_udt["session_id"] = _session_id
        session_id_udt = gr.update(value=_session_id, interactive=False)
        session_status_udt = f"✅ Session resumed."
        session_mkd_udt = gr.update(visible=False, value="")

        # List out existing jobs of this _session_id and status not None
        existing_jobs = collections.distinct(
            "job_name",
            {
                "session_id": _session_id, 
                "status": {"$in": ["pending", "processing", "finished"]}
            }
        )

        if len(existing_jobs) == 0:
            job_dropdown_upt = gr.update(visible=False, value=None, choices=[])
        else:
            job_dropdown_upt = gr.update(visible=True, value=None, choices=existing_jobs, interactive=True)
            # List out pretrained model saved from job_name, status, and mode 
            pre_trained_models = collections.distinct(
                "job_name",
                {
                    "session_id": _session_id, 
                    "status": "finished",
                    "mode": "Transfer Learning"
                }
            )
            model_choices += pre_trained_models
            model_dropdown_udt = gr.update(choices=model_choices)

    return session_id_udt, session_btn_udt, session_mkd_udt, session_status_udt, job_dropdown_upt, param_udt, model_dropdown_udt

if __name__ == "__main__":
    pass
