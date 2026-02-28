import gradio as gr
import secrets
import string
from urllib.parse import quote
from pymongo import MongoClient
from .logger import LOGGER

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

def generate_token(length=10):
    alphabet = string.ascii_letters + string.digits  # A–Z, a–z, 0–9
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def session_id2url(session_id):
    sid = session_id.strip()
    if not sid:
        return ""
    return f"/{quote(sid, safe='')}"

def save_session_id(session_id) -> None:
    sid = session_id.strip()
    if not sid:
        return
    collections.update_one(
        {"session_id": sid},
        {"$setOnInsert": {"session_id": sid, "status": "created"}},
        upsert=True,
    )

def session_exists(session_id) -> bool:
    sid = session_id.strip()
    if not sid:
        return False
    return collections.count_documents({"session_id": sid}) > 0

def on_home_session(_session_id, param):
    old_session_ids = collections.distinct("session_id")
    _session_id = _session_id.strip()
    param_udt = param.copy()
    param_udt['status'] = None
    param_udt["session_id"] = None
    param_udt["session_url"] = ""
    session_url_udt = ""

    # Case 1: Empty input → Generate a new unique session ID
    if not _session_id:
        # loop until finding an unused ID (guaranteed uniqueness)
        while True:
            new_id = generate_token(length=10) 
            # if new_id overlap with old one --> redo
            if new_id not in old_session_ids:
                save_session_id(new_id)
                session_id_udt = gr.update(value=new_id, interactive=False)
                param_udt["session_id"] = new_id
                session_url_udt = session_id2url(new_id)
                param_udt["session_url"] = session_url_udt
                break
    # Case 2: User-provided input, invalid format
    elif _session_id not in old_session_ids:
        session_id_udt = gr.update(value="", interactive=True)
        gr.Warning("Please enter a valid session ID")
    # Case 3: Valid existing/new session ID
    elif _session_id in old_session_ids:
        param_udt["session_id"] = _session_id
        session_url_udt = session_id2url(_session_id)
        param_udt["session_url"] = session_url_udt
        session_id_udt = gr.update(value=_session_id, interactive=False)
    else:
        session_id_udt = gr.update(value="", interactive=True)
        gr.Warning("Unexpected error. Please try again.")
    
    return (session_id_udt, param_udt, session_url_udt)

def on_session_id(_session_id):
    session_id_udt = gr.update(value=_session_id, interactive=False)
    session_btn_udt = gr.update(interactive=False)
    session_status_udt = "ℹ️ Please save the session ID for future reference."
    base_model_choices = ["TANDEM", "TANDEM-DIMPLE for GJB2", "TANDEM-DIMPLE for RYR1"]
    existing_jobs = collections.distinct("job_name", {"session_id": _session_id, "status": {"$in": ["pending", "processing", "finished"]}},)
    has_jobs = len(existing_jobs) > 0

    if has_jobs:
        job_dropdown_udt = gr.update(visible=True, value=None, choices=existing_jobs, interactive=True)
        pre_trained_models = collections.distinct("job_name", {"session_id": _session_id, "status": "finished", "mode": "Transfer Learning"},)
        model_dropdown_udt = gr.update(choices=base_model_choices + pre_trained_models)
    else:
        collections.update_one({"session_id": _session_id}, {"$set": {"status": "created"}})
        job_dropdown_udt = gr.update(visible=False, value=None, choices=[])
        model_dropdown_udt = gr.update(choices=base_model_choices)
    return session_id_udt, session_btn_udt, session_status_udt, job_dropdown_udt, model_dropdown_udt

if __name__ == "__main__":
    pass
