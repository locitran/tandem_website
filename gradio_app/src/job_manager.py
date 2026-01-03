import json, os, shutil

import gradio as gr
from pymongo import MongoClient

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

ADMIN_PASSWORD = "yanglab"
JOBS_ROOT = "/tandem/jobs"

def save_job(session_id, job_name, json_text):
    try:
        data = json.loads(json_text)
        collections.update_one(
            {"session_id": session_id, "job_name": job_name},
            {"$set": data}
        )

        path = f"{JOBS_ROOT}/{session_id}/{job_name}/params.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

        return "✅ Job updated successfully"
    except Exception as e:
        return f"❌ Error: {e}"

def delete_job(session_id, job_name):
    collections.delete_one(
        {"session_id": session_id, "job_name": job_name}
    )

    job_dir = f"{JOBS_ROOT}/{session_id}/{job_name}"
    if os.path.exists(job_dir):
        shutil.rmtree(job_dir)

    return f"🗑 Deleted {session_id}/{job_name}"

def manager_tab():
    authenticated = gr.State(False)
    with gr.Tab("🗂️ Job Manager"):
        with gr.Group(visible=True) as password_gate:
            gr.Markdown("### 🔒 Admin Authentication")
            password = gr.Textbox(
                type="password",
                label="Enter password"
            )
            login_btn = gr.Button("Unlock")
            login_msg = gr.Markdown()

        with gr.Group(visible=False) as job_manager_ui:
            gr.Markdown("## 🗂️ Job Manager")
            # ---- Filters ----
            with gr.Row():
                label="Search (session_id or job_name)"
                placeholder="Type to filter…"
                search = gr.Textbox(label=label, placeholder=placeholder,scale=2)
                status_filter = gr.Dropdown(
                    ["All", "pending", "processing", "finished"],
                    value="All",
                    label="Status",
                    scale=1
                )

            # ---- Job Table ----
            jobs_df = gr.Dataframe(
                headers=["session_id","job_name","mode","status",],
                interactive=False,
                wrap=True,
            )
            # ---- State: selected job ----
            selected_session = gr.State(None)
            selected_job = gr.State(None)

            params_box = gr.Code(
                label="Job Parameters (Editable JSON)",
                language="json",
                lines=20
            )

            with gr.Row():
                save_btn = gr.Button("💾 Save Changes")
                delete_btn = gr.Button("🗑 Delete Job")

            status_msg = gr.Markdown()

            # =========================================================
            # Events
            # =========================================================

            # ---- Refresh table ----
            def refresh(status, keyword):
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
                        
                return [
                    [
                        j.get("session_id", ""),
                        j.get("job_name", ""),
                        j.get("mode", ""),
                        j.get("status", ""),
                    ]
                    for j in unique_jobs
                ]

            search.change(refresh, [status_filter, search], jobs_df)
            status_filter.change(refresh, [status_filter, search], jobs_df)

            # ---- Row selection ----
            def select_job(evt: gr.SelectData):
                table = jobs_df.value

                # ---- Normalize row index ----
                idx = evt.index
                if isinstance(idx, (list, tuple)):
                    row_idx = idx[0]
                else:
                    row_idx = idx

                if not isinstance(row_idx, int):
                    return None, None, ""

                # ---- Case 1: table is list-of-lists ----
                if isinstance(table, list):
                    if row_idx < 0 or row_idx >= len(table):
                        return None, None, ""

                    row = table[row_idx]
                    session_id = row[0]
                    job_name   = row[1]

                # ---- Case 2: table is dict-of-columns ----
                elif isinstance(table, dict):
                    if "session_id" not in table or "job_name" not in table:
                        return None, None, ""

                    if row_idx < 0 or row_idx >= len(table["session_id"]):
                        return None, None, ""

                    session_id = table["session_id"][row_idx]
                    job_name   = table["job_name"][row_idx]

                else:
                    return None, None, ""

                job = collections.find_one(
                    {"session_id": session_id, "job_name": job_name},
                    {"_id": 0}
                )

                params = json.dumps(job, indent=4) if job else "{}"
                return session_id, job_name, params

            jobs_df.select(
                select_job,
                None,
                outputs=[selected_session, selected_job, params_box]
            )

            # ---- Save ----
            def save_wrapper(session_id, job_name, params):
                if not session_id or not job_name:
                    return "⚠️ No job selected."
                return save_job(session_id, job_name, params)

            save_btn.click(
                save_wrapper,
                inputs=[selected_session, selected_job, params_box],
                outputs=status_msg
            )

            # ---- Delete ----
            def delete_wrapper(session_id, job_name):
                if not session_id or not job_name:
                    return "⚠️ No job selected."
                return delete_job(session_id, job_name)

            delete_btn.click(
                delete_wrapper,
                inputs=[selected_session, selected_job],
                outputs=status_msg
            )

        ########
        def unlock(pw):
            if pw == ADMIN_PASSWORD:
                return (
                    True,                            # authenticated
                    gr.update(visible=False),        # hide password gate
                    gr.update(visible=True),         # show job manager
                    "✅ Access granted"
                )
            return (
                False,
                gr.update(visible=True),
                gr.update(visible=False),
                "❌ Incorrect password"
            )

        login_btn.click(
            unlock,
            inputs=password,
            outputs=[authenticated, password_gate, job_manager_ui, login_msg]
        )