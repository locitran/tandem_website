import pandas as pd 
from datetime import datetime
import time
import json
import gradio as gr 
import os 

from pymongo import MongoClient

from .logger import LOGGER
from .web_interface import time_zone

GRADIO_APP_ROOT = os.path.dirname(os.path.dirname(__file__)) # ./tandem_website

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

def toSAV_coords(SAVs):
    """
    >>> a = ['P29033 Y217E', 'P29033 Y217F', 'P29033 Y217T']
    >>> toSAV_coords(a)
    ['P29033 217 Y E', 'P29033 217 Y F', 'P29033 217 Y T']
    """
    out = []
    for s in SAVs:
        acc, wt_resid_mt = s.split()
        wt = wt_resid_mt[0]
        mt = wt_resid_mt[-1]
        resid = wt_resid_mt[0+1:-1]
        out.append(f"{acc} {resid} {wt} {mt}")
    return out

def send_job(_param_state, jobs_folder):
    _job_status = _param_state.get('status', None)
    if _job_status != 'pending':
        return
    collections.insert_one(_param_state)
    LOGGER.info(f"✅ Submitted with payload: {_param_state}")
    return _param_state

def on_job(job_dropdown, param_state):
    _session_id = param_state["session_id"]
    _job_name   = job_dropdown

    param_state_udt = collections.find_one(
        {"session_id": _session_id, "job_name": _job_name},
        {"_id": 0},
    )
    if not param_state_udt:
        raise LookupError("Cannot find job from on_job function")

    return param_state_udt

# Freezing mode when clicking submit button
def on_submit():
    """
    Click submit will trigger:
        1. Freeze the submit button
        2. Update submit status
    """
    submit_status_udt = gr.update(value="✅ Your job is just submitted.", visible=True)
    submit_btn_udt = gr.update(interactive=False)
    return (submit_status_udt, submit_btn_udt)

def on_reset(_param_state):
    """
    Render input_section, submit_section, Hide result_section
    Reset all buttons and textbox

    In case, we are at current session with some existing jobs, 
    then we need to render these jobs.

    """
    job_name_udt = datetime.now(time_zone).strftime("%Y-%m-%d_%H-%M-%S")

    _session_id = _param_state['session_id']

    # List out existing jobs of this _session_id and status not None
    existing_jobs = collections.distinct(
        "job_name",
        {
            "session_id": _session_id,
            "status": {"$in": ["pending", "processing", "finished"]}
        }
    )

    job_dropdown_upt = gr.update(
        visible=bool(existing_jobs),
        value=None,                  # ✅ no selection
        choices=existing_jobs,
        interactive=True,
    )

    param_state_udt = {
        'session_id': _session_id,
        'job_name': job_name_udt,
        'status': None
    }

    input_section_udt   = gr.update(visible=True)
    output_section_udt  = gr.update(visible=False)

    inf_sav_txt_udt     = gr.update(value='')
    inf_sav_btn_udt     = gr.update(label='Upload SAVs', value=None)
    tf_sav_txt_udt      = gr.update(value='')
    tf_sav_btn_udt      = gr.update(label='Upload SAVs', value=None)

    str_txt_udt         = gr.update(value='')
    str_btn_udt         = gr.update(label='Upload structure', value=None)
    job_name_txt_udt    = gr.update(value=job_name_udt)
    email_txt_udt       = gr.update('')
    submit_status_udt   = gr.update(visible=False)
    submit_btn_udt      = gr.update(visible=True, interactive=True)
    reset_btn_udt       = gr.update(visible=False)
    process_status_udt  = gr.update(value='', visible=False)

    return (
        param_state_udt,
        job_dropdown_upt,
        input_section_udt,
        output_section_udt,
        inf_sav_txt_udt,
        inf_sav_btn_udt,
        tf_sav_txt_udt,
        tf_sav_btn_udt,
        str_txt_udt,
        str_btn_udt,
        job_name_txt_udt,
        email_txt_udt,
        submit_status_udt,
        submit_btn_udt,
        reset_btn_udt,
        process_status_udt,
    )

def update_sections(param_state):
    """
    Handle submit / processing UI:
    - input section
    - submit section
    - status text
    - buttons
    """

    _session_id = param_state.get("session_id")
    _job_status = param_state.get("status")
    job_start = param_state.get("job_start")

    # ---- Only dump these fields ----
    payload_view = {
        "SAV": param_state.get("SAV"),
        "label": param_state.get("label"),
        "model": param_state.get("model"),
        "job_name": param_state.get("job_name"),
        "STR": param_state.get("STR"),
    }

    input_section_udt  = gr.update(visible=False)
    submit_section_udt = gr.update(visible=True)

    submit_status_udt  = gr.update(visible=False)
    submit_btn_udt     = gr.update(visible=False)
    reset_btn_udt      = gr.update(visible=True)

    if _job_status == "finished":
        msg = f"{json.dumps(payload_view, indent=2, sort_keys=True)}"
        submit_status_udt  = gr.update(value=msg, visible=True)

    elif _job_status == "pending":
        msg = f"{json.dumps(payload_view, indent=2, sort_keys=True)}"
        submit_status_udt  = gr.update(value=msg, visible=True)

    elif _job_status == "processing" and job_start:
        msg = f"{json.dumps(payload_view, indent=2, sort_keys=True)}"
        submit_status_udt  = gr.update(value=msg, visible=True)

    elif _session_id is None:
        reset_btn_udt      = gr.update(visible=False)
        pass

    elif _job_status is None:
        input_section_udt  = gr.update(visible=True)
        submit_btn_udt     = gr.update(visible=True)
        reset_btn_udt      = gr.update(visible=False)

    return (
        input_section_udt,
        submit_section_udt,
        submit_status_udt,
        submit_btn_udt,
        reset_btn_udt,
    )

def update_process_status(param_state, search_db: bool):
    process_status_udt = gr.update()
    param_state_udt = param_state.copy() if param_state else param_state

    if not param_state:
        return process_status_udt, param_state_udt

    session_id = param_state.get("session_id", None)
    job_name   = param_state.get("job_name", None)

    if not session_id or not job_name:
        return process_status_udt, param_state_udt

    # ---- Conditionally refresh from DB ----
    if search_db:
        updated = collections.find_one({"session_id": session_id, "job_name": job_name}, {"_id": 0})
        if not updated:
            return process_status_udt, param_state_udt
        param_state_udt = updated

    _job_status = param_state_udt.get("status")
    job_start   = param_state_udt.get("job_start")

    if _job_status == "pending":
        process_status_udt = gr.update(value="⏳ Waiting in queue...", visible=True)
    elif _job_status == "processing" and job_start:
        elapsed = int(time.time() - job_start)
        emoji_frames = ["⏳", "🔄", "🔁", "🔃"]
        icon = emoji_frames[elapsed % len(emoji_frames)]
        msg = f"{icon} Model is running... {elapsed} second{'s' if elapsed != 1 else ''} elapsed."
        process_status_udt = gr.update(value=msg, visible=True)
    elif _job_status == "finished":
        job_end = param_state_udt.get("job_end")
        if job_start and job_end:
            runtime = int(job_end - job_start)
            process_status_udt = gr.update(value=f"✅ Finished in {runtime}s", visible=True)

    return process_status_udt, param_state_udt

def update_timer(param_state):
    _job_status = param_state.get('status', None)
    
    if _job_status == "finished":
        timer_udt = gr.update(active=False)
    elif _job_status is None:
        timer_udt = gr.update(active=False)
    else:
        timer_udt = gr.update(active=True)
    
    return timer_udt