import json 
import pandas as pd 
import gradio as gr
import os 
import secrets
import gradio as gr
import string

from .logger import LOGGER
from .update_output import multindex_DataFrame, zip_folder
from .update_output import render_finished_job


from pymongo import MongoClient

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

def generate_token(length=10):
    alphabet = string.ascii_letters + string.digits  # A–Z, a–z, 0–9
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def on_session(_session_id, _param_state):
    """
    1. Start session by generating new id or providing old id
    2. Update parameter state (status and session_id)
    3. Update dropdown of pre-trained models to include trained models from user
        Look up all jobs of session_id to find inference jobs which were finished.

    If id is not valid, no session id is recorded
    """
    old_session_ids = collections.distinct("session_id")
    _session_id = _session_id.strip()
    param_udt = _param_state.copy()
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
                break
    # Case 2: User-provided input, check validity
    elif _session_id not in old_session_ids:
        session_id_udt = gr.update(value="", interactive=True)
        session_status_udt = f"Please generate or paste a valid one."
    # Case 3: Valid existing session
    else:
        session_id_udt = gr.update(value=_session_id, interactive=False)
        session_status_udt = f"✅ Session resumed."

        # List out existing jobs of this _session_id and status not None
        existing_jobs = collections.distinct(
            "job_name",
            {
                "session_id": _session_id, 
                "status": {"$in": ["pending", "processing", "finished"]}
            }
        )

        if len(existing_jobs) == 0:
            job_dropdown_upt = gr.update(visible=False, value=None, choices=[], 
                interactive=False,label="No jobs in this session yet",)
        else:
            first_job = existing_jobs[0]
            param_udt = collections.find_one(
                {'session_id': _session_id,'job_name'  : first_job,}, {"_id": 0}
            )
            job_dropdown_upt = gr.update(
                visible=True, value=first_job, choices=existing_jobs, interactive=True, label='Old jobs',)

            # List out pretrained model saved from job_name, status, and mode 
            pre_trained_models = collections.distinct(
                "job_name",
                {
                    "session_id": _session_id, 
                    "status": "finished",
                    "mode": "Transfer learning"
                }
            )
            model_choices += pre_trained_models
            model_dropdown_udt = gr.update(choices=model_choices)

    return session_id_udt, session_btn_udt, session_status_udt, job_dropdown_upt, param_udt, model_dropdown_udt


def then_session(param_state, folder, _submit_status):
    """
    1. User click/enter old session id --> _job_status: procession/finished
    2. User click to generate new session id --> _job_status: pending
    3. User click/enter non-exist session id --> No _job_status

    If job status is finished,:
        - render output_section
        - render submit_section: only submit_status
        - hide input_section

    If job status is processing/pending:
        - hide output_section
        - render submit_section: only submit_status
        - hide input_section

    If job status is None: (parameter defining)
        - hide output_section
        - render submit_section
        - render input_section
    
    _job_status: {'finished', 'processing', 'pending', None}
    """    
    _session_id = param_state.get('session_id', None)
    _job_status = param_state.get('status', None)
    _job_name   = param_state.get("job_name", None)
    _mode = param_state.get("mode", None)

    input_section_udt   = gr.update(visible=False)   
    submit_section_udt  = gr.update(visible=False)
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

    submit_status_udt   = gr.update(visible=False)
    submit_btn_udt      = gr.update(visible=False)
    reset_btn_udt       = gr.update(visible=False) # Unblind submit button

    if _job_status == 'finished':
        submit_section_udt = gr.update(visible=True)
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

        msg = (_submit_status or "") + f"\n📦 Payload collected for job: {_job_name}"
        msg += f"\n{json.dumps(param_state, indent=2, sort_keys=True)}"
        submit_status_udt = gr.update(value=msg, visible=True)
        reset_btn_udt      = gr.update(visible=True)

    elif _job_status in {'processing', 'pending'}:
        submit_section_udt = gr.update(visible=True)
        msg = (_submit_status or "") + f"\n📦 Payload collected for job: {_job_name}"
        msg += f"\n{json.dumps(param_state, indent=2, sort_keys=True)}"
        submit_status_udt  = gr.update(value=msg, visible=True)
        reset_btn_udt      = gr.update(visible=True)
    elif _session_id is None:
        pass
    elif _job_status is None:
        input_section_udt  = gr.update(visible=True)   
        submit_section_udt = gr.update(visible=True)
        submit_btn_udt     = gr.update(visible=True)

    return (
        input_section_udt,
        submit_section_udt,
        output_section_udt,
        inf_output_secion_udt,
        tf_output_secion_udt,
        
        pred_table_udt,
        result_zip_udt,
        image_selector_udt,
        image_viewer_udt,

        folds_state_udt,
        fold_dropdown_udt,
        train_box_udt,
        val_box_udt,
        test_box_udt,
        loss_image_udt,
        test_eval_udt,

        submit_status_udt,
        submit_btn_udt,
        reset_btn_udt
    )


if __name__ == "__main__":
    pass