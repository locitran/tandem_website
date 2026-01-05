import pandas as pd 
from datetime import datetime
import time
import json
import gradio as gr 
import os 

from pymongo import MongoClient

from .logger import LOGGER
from .update_output import render_finished_job
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

    """
        If job status is pending:
            - hide output_section
            - render submit_section: only submit_status
            - hide input_section

        If job status is None: (parameter defining)
            - hide output_section
            - render submit_section
            - render input_section
"""
    _job_status = _param_state.get('status', None)

    if _job_status != 'pending':
        return

    collections.insert_one(_param_state)
    LOGGER.info(f"✅ Submitted with payload: {_param_state}")
    return _param_state

def on_job(_job_dropdown, _param_state, folder):
    """Switch among existing jobs
    Stimulate the effect of dropdown button of job, where it saves old jobs 
    from a given session id.

    on_job event is triggered when user select new job_name (same session id)
        - Update and load _param_state (from jobs/session_id/job_name/params.json)
        - Check status to decide rendering
            + If finished: render submit_section, output_section
            + If processing/pending: render submit_section
            + No the other way --> Only submitted job has record

    New task:
        - Remove old job(s)
    """
    
    _session_id = _param_state['session_id']
    _job_name   = _job_dropdown

    param_udt = collections.find_one(
        {'session_id': _session_id, 'job_name'  : _job_name}, {"_id": 0}
    )
    if not param_udt:
        raise LookupError("Cannot find job from on_job function")

    _job_status = param_udt.get('status', None)
    job_start = param_udt.get("job_start", None)
    job_end   = param_udt.get("job_end", None)
    _mode = param_udt.get("mode", None)

    input_section_udt = gr.update(visible=False)   

    output_section_udt  = gr.update(visible=False)
    inf_output_secion_udt = gr.update(visible=False)
    tf_output_secion_udt = gr.update(visible=False)

    pred_table_udt      = gr.update(visible=False)
    result_zip_udt      = gr.update(visible=False) 
    image_selector_udt  = gr.update(visible=False)
    image_viewer_udt    = gr.update(visible=False)

    folds_state_udt     = gr.update(visible=False)
    fold_dropdown_udt   = gr.update(visible=False)
    train_box_udt       = gr.update(visible=False)
    val_box_udt         = gr.update(visible=False)
    test_box_udt        = gr.update(visible=False)
    loss_image_udt      = gr.update(visible=False)
    test_eval_udt       = gr.update(visible=False)

    process_status_udt = gr.update(visible=False)
    submit_btn_udt     = gr.update(visible=False)
    reset_btn_udt      = gr.update(visible=True)
    submit_section_udt = gr.update(visible=True)
    timer_udt = gr.update(active=True)

    if _job_status == 'finished':
        job_folder = os.path.join(folder, _session_id, _job_name) 

        (
            output_section_udt,
            result_zip_udt,
            inf_output_secion_udt, 
            pred_table_udt, 
            image_selector_udt, 
            image_viewer_udt,
            tf_output_secion_udt,
            folds_state_udt,
            fold_dropdown_udt,
            train_box_udt,
            val_box_udt,
            test_box_udt,
            loss_image_udt,
            test_eval_udt,
        ) = render_finished_job(_mode, job_folder)

        runtime = int(job_end - job_start)
        msg = f"📦 Payload collected for job: {_job_name}"
        msg += f"\n{json.dumps(param_udt, indent=2, sort_keys=True)}"
        msg += f"\n✅ Finished in {runtime}s"
        submit_status_udt = gr.update(value=msg, visible=True)
        process_status_udt = gr.update(visible=False)
        timer_udt = gr.update(active=False)

    elif _job_status == 'pending':
        msg = f"📦 Payload collected for job: {_job_name}"
        msg += f"\n{json.dumps(_param_state, indent=2, sort_keys=True)}"
        submit_status_udt  = gr.update(value=msg, visible=True)
        process_status_udt = gr.update(value="⏳ Waiting in queue...", visible=True)
    
    elif _job_status == 'processing' and job_start:
        msg = f"📦 Payload collected for job: {_job_name}"
        msg += f"\n{json.dumps(_param_state, indent=2, sort_keys=True)}"
        submit_status_udt  = gr.update(value=msg, visible=True)

        elapsed = int(time.time() - job_start)
        emoji_frames = ["⏳", "🔄", "🔁", "🔃"]
        icon = emoji_frames[elapsed % len(emoji_frames)]
        process_status_udt = gr.update(value=f"{icon} Model is running... {elapsed} second{'s' if elapsed != 1 else ''} elapsed.", visible=True)
          
    else: # _job_status is None:
        input_section_udt  = gr.update(visible=True)   
        submit_btn_udt     = gr.update(visible=True)
        reset_btn_udt      = gr.update(visible=False) # Unblind submit button
        submit_status_udt   = gr.update(visible=False)
        timer_udt           = gr.update(active=False)
        
    return (
        input_section_udt,
        submit_section_udt,
        output_section_udt,
        process_status_udt,

        result_zip_udt,
        inf_output_secion_udt, 
        pred_table_udt, 
        image_selector_udt, 
        image_viewer_udt,
        tf_output_secion_udt,
        folds_state_udt,
        fold_dropdown_udt,
        train_box_udt,
        val_box_udt,
        test_box_udt,
        loss_image_udt,
        test_eval_udt,
        
        submit_status_udt,
        submit_btn_udt,
        reset_btn_udt,
        param_udt,
        timer_udt,
    )

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

    param_udt = {
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
        param_udt,
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

def check_status(_param_state, _submit_status):
    """
    This function is mainly to regulate timer, activating it when job_status is processing.
    This activation needs to be search db through time.
    """
    process_status_udt = gr.update()
    timer_udt = gr.update()
    _submit_status_udt = gr.update()
    param_udt = _param_state.copy()

    if not _param_state:
        return process_status_udt, timer_udt, _submit_status_udt, param_udt

    session_id = _param_state.get("session_id", None)
    job_name   = _param_state.get("job_name", None)

    if not session_id or not job_name:
        return process_status_udt, timer_udt, _submit_status_udt, param_udt

    # Look for record in db in which it is updated from worker every second
    param_udt = collections.find_one(
        {"session_id": session_id, "job_name": job_name}, {"_id": 0}
    )

    if not param_udt:
        return process_status_udt, timer_udt, _submit_status_udt, param_udt

    _job_status = param_udt.get('status', None)
    job_start = param_udt.get("job_start", None)

    if _job_status == "pending":
        process_status_udt = gr.update(value="⏳ Waiting in queue...", visible=True)
    elif _job_status == "processing" and job_start:
        elapsed = int(time.time() - job_start)
        emoji_frames = ["⏳", "🔄", "🔁", "🔃"]
        icon = emoji_frames[elapsed % len(emoji_frames)]
        process_status_udt = gr.update(value=f"{icon} Model is running... {elapsed} second{'s' if elapsed != 1 else ''} elapsed.", visible=True)
    elif _job_status == "finished":
        job_end   = param_udt.get("job_end")
        runtime = int(job_end - job_start)
        process_status_udt = gr.update(visible=False)
        msg = _submit_status + f"\n✅ Finished in {runtime}s"
        _submit_status_udt = gr.update(value=msg)
        timer_udt = gr.update(active=False)

    return process_status_udt, timer_udt, _submit_status_udt, param_udt