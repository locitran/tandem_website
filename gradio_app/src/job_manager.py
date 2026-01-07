import jsonyx, json, os, shutil

import gradio as gr
from pymongo import MongoClient

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

ADMIN_PASSWORD = "yanglab"
JOBS_ROOT = "/tandem/jobs"

def on_save_job(session_id, job_name, json_text):
    status_msg_udt = "⚠️ No job selected."
    if not session_id or not job_name:
        return status_msg_udt

    try:
        
        data = json.loads(json_text) # Parse JSON
        collections.update_one( # Update MongoDB
            {"session_id": session_id, "job_name": job_name},
            {"$set": data}
        )

        # ---- Write params.json ----
        path = f"{JOBS_ROOT}/{session_id}/{job_name}/params.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        status_msg_udt = "✅ Job updated successfully"
        return status_msg_udt

    except Exception as e:
        status_msg_udt = f"❌ Error: {e}"
        return status_msg_udt

def on_delete_job(session_id, job_name, df_jobs):
    df_jobs_udt = gr.update()
    if not session_id or not job_name:
        status_msg_udt = f"🗑 Deleted {session_id}/{job_name}"
        return status_msg_udt, df_jobs_udt

    try:
        # ---- Remove from MongoDB ----
        collections.delete_one({"session_id": session_id, "job_name": job_name})
        # ---- Remove job folder ----
        job_dir = f"{JOBS_ROOT}/{session_id}/{job_name}"
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir)

        removed_idx = df_jobs[(df_jobs['session_id'] == session_id) & (df_jobs['job_name'] == job_name)].index
        df_jobs_udt = df_jobs.drop(removed_idx)

        status_msg_udt = f"🗑 Deleted {session_id}/{job_name}"
        return status_msg_udt, df_jobs_udt

    except Exception as e:
        status_msg_udt = f"❌ Error deleting job: {e}"
        return status_msg_udt, df_jobs_udt

def on_refresh(status, keyword):
    q = {}
    if status != "All":
        q["status"] = status

    if keyword:
        q["$or"] = [
            {"session_id": {"$regex": keyword, "$options": "i"}},
            {"job_name": {"$regex": keyword, "$options": "i"}}
        ]

    jobs = list(collections.find(q, {"_id": 0}))
    seen = set()
    unique_jobs = []

    for j in jobs:
        key = (j.get("session_id"), j.get("job_name"))
        if key not in seen:
            seen.add(key)
            unique_jobs.append(j)
            
    unique_jobs = [
        [
            j.get("session_id", ""),
            j.get("job_name", ""),
            j.get("mode", ""),
            j.get("status", ""),
        ]
        for j in unique_jobs
    ]
    params_box_udt = gr.update(value=None, lines=1)
    status_msg_udt = gr.update(value=None)
    return unique_jobs, params_box_udt, status_msg_udt

def on_select_job(evt: gr.SelectData, df):
    """This parameter evt is injected automatically by Gradio"""

    # ---- Normalize row index ----
    row_idx, col_idx = evt.index
    session_id = df.iloc[row_idx]['session_id']
    job_name = df.iloc[row_idx]['job_name']

    job = collections.find_one(
        {"session_id": session_id, "job_name": job_name},
        {"_id": 0}
    )
    if job:
        params = jsonyx.dumps(job, indent=2, indent_leaves=False, separators=(",", ": "))
    else:
        params = {}
    
    params_box_udt = gr.update(value=params, lines=len(job)+3)
    status_msg_udt = gr.update(value=None)
    return session_id, job_name, params_box_udt, status_msg_udt

def on_authentication(pw):
    if pw == ADMIN_PASSWORD:
        authenticated_udt = True
        password_gate_udt = gr.update(visible=False)
        job_manager_ui = gr.update(visible=True)
        login_msg_udt = "✅ Access granted"
    else:
        authenticated_udt = False,
        password_gate_udt = gr.update(visible=True),
        job_manager_ui = gr.update(visible=False),
        login_msg_udt = "❌ Incorrect password"
    return authenticated_udt, password_gate_udt, job_manager_ui, login_msg_udt

def manager_tab():
    authenticated = gr.State(False)
    with gr.Group(visible=True) as password_gate:
        gr.Markdown("### 🔒 Admin Authentication")
        password_box = gr.Textbox(type="password", label="Enter password")
        login_btn = gr.Button("Unlock")
        login_msg = gr.Markdown()

    with gr.Group(visible=False) as job_manager_ui:
        gr.Markdown("## 🗂️ Job Manager")
        # ---- Filters ----
        with gr.Row():
            label="Search (session_id or job_name)"
            placeholder="Type to filter…"
            choices = ["All", "pending", "processing", "finished"]
            search = gr.Textbox(label=label, placeholder=placeholder, scale=2)
            status_filter = gr.Dropdown(choices=choices, value="All", label="Status", scale=1)

        # ---- Job Table ----
        headers = ["session_id","job_name","mode","status",]
        df_jobs = gr.Dataframe(headers=headers, interactive=False, wrap=True)
        # ---- State: selected job ----
        selected_session = gr.State(None)
        selected_job = gr.State(None)
        params_box = gr.Code(label="Job Parameters (Editable JSON")

        with gr.Row():
            save_btn = gr.Button("💾 Save Changes")
            delete_btn = gr.Button("🗑 Delete Job")
        status_msg = gr.Markdown()

        # =========================================================
        # Events
        # =========================================================
        search.change(on_refresh,           inputs=[status_filter, search], outputs=[df_jobs, params_box, status_msg])
        status_filter.change(on_refresh,    inputs=[status_filter, search], outputs=[df_jobs, params_box, status_msg])
        df_jobs.select(on_select_job,       inputs=[df_jobs], outputs=[selected_session, selected_job, params_box, status_msg])
        save_btn.click(on_save_job,         inputs=[selected_session, selected_job, params_box], outputs=status_msg)
        delete_btn.click(on_delete_job,     inputs=[selected_session, selected_job, df_jobs], outputs=[status_msg, df_jobs])
    password_box.submit(on_authentication,  inputs=password_box, outputs=[authenticated, password_gate, job_manager_ui, login_msg])
    login_btn.click(on_authentication,      inputs=password_box, outputs=[authenticated, password_gate, job_manager_ui, login_msg])

if __name__ == "__main__":
    pass
