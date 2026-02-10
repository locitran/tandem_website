import pandas as pd 
from datetime import datetime
import time
import json
import gradio as gr 
import os 

from pymongo import MongoClient

from .logger import LOGGER
from .settings import time_zone
from .update_input import on_clear_param, on_clear_file

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

def send_job(_param, jobs_folder):
    _job_status = _param.get('status', None)
    if _job_status != 'pending':
        return _param
    collections.insert_one(_param)
    LOGGER.info(f"✅ Submitted with payload: {_param}")
    return _param

def on_job(job_dropdown, param):
    _session_id = param["session_id"]
    _job_name   = job_dropdown

    param_udt = collections.find_one(
        {"session_id": _session_id, "job_name": _job_name},
        {"_id": 0},
    )
    if not param_udt:
        raise LookupError("Cannot find job from on_job function")

    return param_udt

# Freezing mode when clicking submit button
def on_submit():
    """
    Click submit will trigger:
        1. Freeze the submit button
        2. Update submit status
    """
    submit_status_udt = gr.update(value="✅ Your job is just submitted.", visible=True)
    return submit_status_udt

def load_jobs(_session_id):
    # List out existing jobs of this _session_id and status not None
    if _session_id is not None:
        existing_jobs = collections.distinct(
            "job_name",
            {
                "session_id": _session_id,
                "status": {"$in": ["pending", "processing", "finished"]}
            }
        )

        job_dropdown_upt = gr.update(
            visible=bool(existing_jobs), value=None, choices=existing_jobs, interactive=True,)
    else:
        job_dropdown_upt = gr.update()
    return job_dropdown_upt

def on_reset(_param):
    job_name_udt = datetime.now(time_zone).strftime("%Y-%m-%d_%H-%M-%S")
    _session_id = _param.get('session_id', None)
    job_dropdown_upt = load_jobs(_session_id)
    
    param_udt = {
        'session_id': _session_id,
        'job_name': job_name_udt,
        'status': None
    }

    input_page_udt      = gr.update(visible=True)
    input_section_udt   = gr.update(visible=True)
    output_section_udt  = gr.update(visible=False)
    # Parameters
    (
        inf_sav_txt_udt, inf_sav_btn_udt, inf_sav_file_udt,
        tf_sav_txt_udt, tf_sav_btn_udt, tf_sav_file_udt,
        str_txt_udt, str_btn_udt, str_file_udt,
        job_name_txt_udt, email_txt_udt,
    ) = on_clear_param()

    return (
        input_page_udt,
        param_udt,
        job_dropdown_upt,
        input_section_udt,
        output_section_udt,
        inf_sav_txt_udt,
        inf_sav_btn_udt,
        inf_sav_file_udt,
        tf_sav_txt_udt,
        tf_sav_btn_udt,
        tf_sav_file_udt,
        str_txt_udt,
        str_btn_udt,
        str_file_udt,
        job_name_txt_udt,
        email_txt_udt,
    )

def _prepare_back_sav(param_state):
    input_section_udt = gr.update(visible=True)
    input_page_udt = gr.update(visible=True)
    output_page_udt = gr.update(visible=False)

    SAV = param_state['SAV']
    label = param_state['label']
    mode = param_state['mode']
    if mode == 'Inferencing':
        inf_section_udt = gr.update(visible=True)
        tf_section_udt = gr.update(visible=False)
        sav_text = '\n'.join(SAV)
        inf_sav_txt_udt = gr.update(value=sav_text)
        tf_sav_txt_udt = gr.update(value='')
    elif mode == 'Transfer Learning':
        inf_section_udt = gr.update(visible=False)
        tf_section_udt = gr.update(visible=True)
        if label is None:
            raise ValueError("Transfer Learning mode requires labels")
        lines = [f"{sav} {lab}" for sav, lab in zip(SAV, label)]
        sav_text = "\n".join(lines)
        inf_sav_txt_udt = gr.update(value='')
        tf_sav_txt_udt = gr.update(value=sav_text)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    mode_udt = gr.update(value=mode)
    job_name_txt_udt = gr.update(value=param_state['job_name'])
    _session_id = param_state.get('session_id', None)
    job_dropdown_upt = load_jobs(_session_id)

    return (
        input_section_udt,
        input_page_udt,
        output_page_udt,
        inf_section_udt,
        tf_section_udt,
        inf_sav_txt_udt,
        tf_sav_txt_udt,
        mode_udt,
        job_name_txt_udt,
        job_dropdown_upt,
    )

def _prepare_back_str(param_state):
    STR = param_state['STR']
    str_txt_udt = gr.update(value="")
    str_check_udt = gr.update(value=True)
    structure_section_udt = gr.update(visible=True)

    def _resolve_str_path(value):
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple)) and len(value) == 1 and isinstance(value[0], str):
            return value[0]
        if isinstance(value, dict):
            path = value.get("path") or value.get("name")
            if isinstance(path, str):
                return path
        return None

    str_path = _resolve_str_path(STR)
    if STR is None:  # Case 1: No structure provided
        str_btn_udt = gr.update(visible=True)
        str_file_udt = gr.update(value=None, visible=False)
    elif str_path and os.path.isfile(str_path):  # Case 2: File-based STR
        # IMPORTANT: Gradio file input expects a list
        str_file_udt = gr.update(value=[str_path], visible=True)
        str_btn_udt = gr.update(visible=False)
    else:  # Case 3: Text-based STR
        str_txt_udt = gr.update(value=str(STR))
        str_btn_udt = gr.update(visible=True)
        str_file_udt = gr.update(value=None, visible=False)

    return (
        structure_section_udt,
        str_check_udt,
        str_txt_udt,
        str_btn_udt,
        str_file_udt,
    )

def update_sections(param):
    _session_id = param.get("session_id")
    _job_status = param.get("status", None)

    # ---- Only dump these fields ----
    input_section_udt   = gr.update(visible=False)   
    input_page_udt      = gr.update(visible=False)   
    output_page_udt     = gr.update(visible=False)

    if _session_id is None:
        pass
    elif _job_status is None:
        input_section_udt  = gr.update(visible=True)   
        input_page_udt      = gr.update(visible=True)

    elif _job_status in ["finished", "pending", "processing"]:
        output_page_udt     = gr.update(visible=True)

    return input_section_udt, input_page_udt, output_page_udt

def update_submit_status(param):
    _session_id = param.get("session_id")
    _job_status = param.get("status", None)

    if _session_id is None or _job_status is None:
        submit_status_udt  = gr.update()
    else:
        msg = ""
        for k in ["SAV", "label", "model", "STR"]:
            v = param.get(k, None)
            if v is not None:
                msg += f"{k}: {v}"
                if k != "STR":
                    msg += '\n'
        
        submit_status_udt  = gr.update(value=msg, visible=True, lines=2)
    return submit_status_udt

def update_process_status(param, search_db: bool):
    process_status_udt = gr.update()
    param_udt = param.copy() if param else param

    if not param:
        return process_status_udt, param_udt

    session_id = param.get("session_id", None)
    job_name   = param.get("job_name", None)

    if not session_id or not job_name:
        return process_status_udt, param_udt
    
    # ---- Conditionally refresh from DB ----
    if search_db:
        updated = collections.find_one({"session_id": session_id, "job_name": job_name}, {"_id": 0})
        if not updated:
            return process_status_udt, param_udt
        param_udt = updated

    _job_status = param_udt.get("status")
    job_start   = param_udt.get("job_start")

    if _job_status == "pending":
        process_status_udt = gr.update(value="⏳ Waiting in queue...", visible=True)
    elif _job_status == "processing" and job_start:
        elapsed = int(time.time() - job_start)
        emoji_frames = ["⏳", "🔄", "🔁", "🔃"]
        icon = emoji_frames[elapsed % len(emoji_frames)]
        msg = f"{icon} Model is running... {elapsed} second{'s' if elapsed != 1 else ''} elapsed."
        process_status_udt = gr.update(value=msg, visible=True)
    elif _job_status == "finished":
        job_end = param_udt.get("job_end")
        if job_start and job_end:
            runtime = int(job_end - job_start)
            process_status_udt = gr.update(value=f"✅ Finished in {runtime}s", visible=True)

    return process_status_udt, param_udt

def update_timer(param):
    _job_status = param.get('status', None)
    if _job_status == "finished":
        timer_udt = gr.update(active=False)
    elif _job_status is None:
        timer_udt = gr.update(active=False)
    else:
        timer_udt = gr.update(active=True)
    return timer_udt

if __name__ == "__main__":
    pass
