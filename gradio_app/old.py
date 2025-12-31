import gradio as gr
import secrets
import base64
import logging
import time
import os
import shutil
import stat
from pymongo import MongoClient

from src.SAV_handler import handle_sav_input

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
input_col = db["input_queue"]

JOB_DIR = '/inference/external_infer/jobs'

# Check database
logging.info(f"✅ Connected. Collections: {db.list_collection_names()}")

# --- BACKEND LOGIC ---

def generate_session_id(length=10):
    while True:
        sid = secrets.token_urlsafe(length)[:length]    # e.g., 'Xyz82Gk4vB'
        if "_" not in sid and "-" not in sid:
            break
    return sid

def start_session(session_id_input):
    session_id_input = session_id_input.strip()

    # Case 1: Empty input → Generate a new unique session ID
    if not session_id_input:
        # loop until finding an unused ID (guaranteed uniqueness)
        while True:
            new_id = generate_session_id()
            if input_col.find_one({"session_id": new_id}) is None:
                break

        return (
            gr.update(value=new_id, label="Session ID in use", interactive=False, elem_classes="session-frozen"),
            gr.update(interactive=False),
            new_id,
            True,
            f"🔄 New user session ID ({new_id}) has been generated. <br>ℹ️ Please save the session ID for future reference.",
            gr.update(visible=True),
        )

    # Case 2: User-provided input, check validity
    existing = input_col.find_one({"session_id": session_id_input})
    if existing is None:
        return (
            gr.update(label="❌ Session ID not found", interactive=True, elem_classes=""),
            gr.update(interactive=True),
            "",
            False,
            f"❌ Session ID ({session_id_input}) does not exist. Please generate or paste a valid one.",
            gr.update(visible=False),
        )

    # Case 3: Valid existing session
    return (
        gr.update(label="Session ID in use", interactive=False, elem_classes="session-frozen"),
        gr.update(interactive=False),
        session_id_input,
        True,
        f"✅ Session ({session_id_input}) resumed.",
        gr.update(visible=True),
    )

# --- FRONTEND UI ---
with gr.Blocks(css=".session-frozen { background-color: #f0f0f0; color: #666 !important; } .boxed-markdown { padding: 5px;} .large-info .gr-info {font-size: 22px !important; color: #666;}") as demo:

    with gr.Tabs():

        with gr.Tab("Home"):
            gr.Markdown("## TANDEM-DIMPLE: Transfer-leArNing-ready \
                    and Dynamics-Empowered Model for Disease-specific \
                    Missense Pathogenicity Level Estimation")

            session_id_state = gr.State("")
            submission_id_state = gr.State("")
            session_locked_state = gr.State("")

            with gr.Row():
                # --- LEFT COLUMN ---
                with gr.Column(scale=1):
                    from src.introduction import introduction
                    introduction()

                # --- RIGHT COLUMN ---
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown("### User Session", elem_classes="boxed-markdown")

                        session_id_box = gr.Textbox(label="Session ID", placeholder="Start a new session or paste an existing session ID", interactive=True)
                        with gr.Row():
                            start_session_btn = gr.Button("▶️ Start / Resume Session")
                        session_status = gr.Markdown("", elem_classes="boxed-markdown")

                    # --- Conditional Visibility Wrappers ---
                    with gr.Column(visible=False) as workspace:

                        gr.Markdown("## Task Type Selection", elem_classes="boxed-markdown")

                        with gr.Tabs():
                            with gr.Tab("Inference"):
                                from src.queryUI import UI_SAVinfo, UI_STRinfo

                                page_pred = {}

                                with gr.Group():
                                    gr.Markdown("### SAV Queries", elem_classes="boxed-markdown")
                                    page_pred["sav_info"] = UI_SAVinfo()

                                with gr.Group():
                                    page_pred["str_activate"] = gr.Button("✢	Assign or upload your structure")

                                    with gr.Group(visible=False) as str_input_group:
                                        gr.Markdown("### Assign or upload your structure", elem_classes="boxed-markdown")
                                        page_pred["str_info"] = UI_STRinfo()

                                    page_pred["str_activate"].click(
                                        fn=lambda: (gr.update(visible=False), gr.update(visible=True)),
                                        inputs=[],
                                        outputs=[page_pred["str_activate"], str_input_group]
                                    )

                                with gr.Group():
                                    gr.Markdown("### Select a Model for Inference", elem_classes="boxed-markdown")
                                    page_pred["model_select"] = gr.Dropdown(
                                        choices = ["Foundation-Model"],
                                        value = "Foundation-Model",
                                        interactive=True,
                                        label="Model Selection"
                                    )

                                with gr.Group():
                                    page_pred["submit_btn"] = gr.Button("Submit an inference task")
                                    page_pred["submit_status"] = gr.Textbox(label="Submission Status", interactive=False, visible=False)

                                # --- Conditional Visibility Wrappers ---
                                with gr.Column(visible=False) as result_section:
                                    page_pred["result"] = {"section": result_section}

                                    with gr.Group():
                                        gr.Markdown("### Results", elem_classes="boxed-markdown")
                                        page_pred["result"]["select"] = gr.Dropdown(
                                            choices = [],
                                            interactive=True,
                                            label = "Submission Select"
                                        )
                                        page_pred["result"]["output"] = gr.Textbox(label="Result Output", lines=6)
                                        page_pred["result"]["table"] = gr.Dataframe(headers=["SAVs", "Probability", "Decision", "Voting (%)"])
                                        page_pred["result"]["zip"] = gr.File(label="Download Results (.zip)")
                                        # processing_start_time = gr.State(None)
                                        # page_pred["result"]["check_btn"] = gr.Button("Check Results")

                                def submit_job_pred(
                                        session_id,
                                        sav_txt, sav_txt_state, sav_btn, sav_btn_state,
                                        str_txt, str_txt_state, str_btn, str_btn_state,
                                        model_select
                                    ):

                                    if not session_id:
                                        return gr.update(visible=True, value="❌ No session ID"), gr.State("")

                                    if sav_btn_state:
                                        SAV_input = sav_btn
                                    elif sav_txt_state:
                                        SAV_input = sav_txt
                                    else:
                                        SAV_input = None

                                    if not SAV_input:
                                        return gr.update(visible=True, value="❌ No SAV input provided"), gr.State("")

                                    while True:
                                        submission_id = f"{session_id}-{generate_session_id()}"
                                        if input_col.find_one({"submission_id": submission_id}) is None:
                                            break

                                    if str_btn_state:
                                        folder = os.path.join(JOB_DIR, submission_id)
                                        os.makedirs(folder, exist_ok=True)
                                        shutil.copy(str_btn, folder)

                                        filename = os.path.basename(str_btn)
                                        filepath = os.path.join(folder, filename)
                                        os.chmod(filepath, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)

                                        STR_input = filename
                                    elif str_txt_state:
                                        STR_input = str_txt
                                    else:
                                        STR_input = None

                                    SAV_input = handle_sav_input(SAV_input)

                                    models = model_select if model_select else "Foundation-Model"

                                    payload = {
                                        "session_id": session_id,
                                        "submission_id": submission_id,
                                        "ts": time.time_ns(),
                                        "SAV_input": SAV_input,
                                        "STR_input": STR_input,
                                        "models": None if models=="Foundation-Model" else f"{session_id}-{models}",
                                        "status": "pending",
                                        "result": None
                                    }
                                    input_col.insert_one(payload)

                                    logging.info(f"✅ Submitted input: {payload}")

                                    return gr.update(visible=True, value=f"✅ Submitted with payload: {payload}"), submission_id


                                def refresh_msg_pred(submission_id):
                                    """
                                    Returns:
                                        - result_msg (str): display in frontend textbox
                                        - timer_value (float or None): Time interval to wait before the next polling.
                                                                    If None, polling is stopped (i.e., job is complete).
                                    """
                                    if not submission_id:
                                        return "❌ No submission ID", 10.0, None

                                    data = input_col.find_one({"submission_id": submission_id}) or input_col.find_one({"session_id": submission_id})

                                    if data is None:
                                        return "❌ Input for this submission ID not found.",  10.0, None
                                    elif data["status"] == "pending":
                                        return "⏳ Waiting in queue...", 3.0, None
                                    elif data["status"] == "processing":
                                        elapsed = int(time.time_ns() - data.get("ts", time.time_ns())) // 1_000_000_000
                                        emoji_frames = ["⏳", "🔄", "🔁", "🔃"]
                                        icon = emoji_frames[elapsed % len(emoji_frames)]

                                        animated_msg = f"{icon} Model is running... {elapsed} second{'s' if elapsed != 1 else ''} since queued."

                                        return animated_msg, 1.0

                                    return "✅ Inference complete. You may download the results below.", 10.0, None


                                def check_result_pred(submission_id):
                                    """
                                    Returns:
                                        - result_table (List[List[Any]]): A list of rows parsed from report.txt,
                                                                        shown in a Gradio Dataframe with columns:
                                                                        ["SAVs", "Probability", "Decision", "Voting"]
                                        - zip_file_path (str): Path to the zipped folder containing all result files,
                                                            returned to a Gradio File component for download.
                                        - timer_value (float or None): Time interval to wait before the next polling.
                                                                    If None, polling is stopped (i.e., job is complete).
                                    """
                                    if not submission_id:
                                        return [], None, 10.0

                                    data = input_col.find_one({"submission_id": submission_id}) or input_col.find_one({"session_id": submission_id})

                                    if data is None:
                                        return [], None, 10.0
                                    elif data["status"] in ("pending", "processing", ):
                                        return [], None, 10.0

                                    # Status == finished
                                    logging.info(f"✅ Result found for submission ID {submission_id}: {data}")
                                    table_data = data["result"]
                                    zip_path = f"/shared/results/{submission_id}_results.zip"

                                    return table_data, zip_path, 10.0


                                def refresh_results_pred(session_id, result_section):
                                    if not session_id:
                                        return

                                    history = list(input_col.find({"session_id": session_id}))
                                    # if not history:
                                    #     return

                                    models = [h["submission_id"].split("-")[-1] for h in history if h.get("with_labels", False)]
                                    logging.info(f"Detected models from history: {models}")

                                    model_args = {
                                        "choices": ["Foundation-Model"],
                                    }
                                    if models:
                                        model_args["choices"] += list(set(models))

                                    logging.info(f"History for session {session_id}: {[h['submission_id'] for h in history]}")

                                    runs = [h for h in history if not h.get("with_labels", False)]
                                    hist = list(sorted(runs, key=lambda x: -x.get("ts",0)))
                                    # if not hist:
                                    #     return

                                    if not hist:
                                        return gr.update(visible=False), gr.update(**model_args), gr.update(choices=[], value=None), [], None, 10.0

                                    output_args = {
                                        "visible": True,
                                        "choices": [s.get("submission_id", session_id) for s in hist],
                                        "value": result_section if result_section else hist[0].get("submission_id", session_id)
                                    }

                                    return gr.update(visible=True), gr.update(**model_args), gr.update(**output_args), *check_result_pred(output_args["value"])


                                # Timer to check result every 10 seconds
                                page_pred["timer"] = gr.Timer(value=10.0, active=True)
                                page_pred["timer_msg"] = gr.Timer(value=3.0, active=True)

                                page_pred["timer"].tick(
                                    fn=refresh_results_pred,
                                    inputs=[session_id_state, page_pred["result"]["select"]],
                                    outputs=[page_pred["result"]["section"], page_pred["model_select"], page_pred["result"]["select"], page_pred["result"]["table"], page_pred["result"]["zip"], page_pred["timer"]]
                                )
                                page_pred["timer_msg"].tick(
                                    fn=refresh_msg_pred,
                                    inputs=[page_pred["result"]["select"]],
                                    outputs=[page_pred["result"]["output"], page_pred["timer_msg"]]
                                )

                                # timer_control = gr.State()  # dummy variable to catch the second output

                                # 1. First run submit_input()
                                page_pred["submit_btn"].click(
                                    fn=submit_job_pred,
                                    inputs=[
                                        session_id_state,
                                        page_pred["sav_info"]["text"]["data"], page_pred["sav_info"]["text"]["stat"], page_pred["sav_info"]["file"]["data"], page_pred["sav_info"]["file"]["stat"],
                                        page_pred["str_info"]["text"]["data"], page_pred["str_info"]["text"]["stat"], page_pred["str_info"]["file"]["data"], page_pred["str_info"]["file"]["stat"],
                                        page_pred["model_select"],
                                    ],
                                    outputs=[page_pred["submit_status"], submission_id_state]
                                # ).then( # 2. Reset processing timer after submission
                                #     fn=lambda: None,
                                #     inputs=[],
                                #     outputs=processing_start_time
                                ).then(# 3. Call check_result()
                                    fn=refresh_results_pred,
                                    inputs=[session_id_state, submission_id_state],
                                    outputs=[page_pred["result"]["section"], page_pred["model_select"], page_pred["result"]["select"], page_pred["result"]["table"], page_pred["result"]["zip"], page_pred["timer"]]
                                ).then(
                                    fn=refresh_msg_pred,
                                    inputs=[page_pred["result"]["select"]],
                                    outputs=[page_pred["result"]["output"], page_pred["timer_msg"]]
                                )

                                page_pred["result"]["select"].change(
                                    fn=refresh_results_pred,
                                    inputs=[session_id_state, page_pred["result"]["select"]],
                                    outputs=[page_pred["result"]["section"], page_pred["model_select"], page_pred["result"]["select"], page_pred["result"]["table"], page_pred["result"]["zip"], page_pred["timer"]]
                                ).then(
                                    fn=refresh_msg_pred,
                                    inputs=[page_pred["result"]["select"]],
                                    outputs=[page_pred["result"]["output"], page_pred["timer_msg"]]
                                )

                                # page_pred["result"]["check_btn"].click(
                                #     fn=refresh_results_pred,
                                #     inputs=[session_id_state, page_pred["result"]["select"]],
                                #     outputs=[page_pred["result"]["section"], page_pred["model_select"], page_pred["result"]["select"], page_pred["result"]["table"], page_pred["result"]["zip"], page_pred["timer"]]
                                # ).then(
                                #     fn=refresh_msg_pred,
                                #     inputs=[page_pred["result"]["select"]],
                                #     outputs=[page_pred["result"]["output"], page_pred["timer_msg"]]
                                # )

                                # --- Event hooks ---

                            with gr.Tab("Transfer Learning"):
                                from src.queryUI import UI_SAVLABELinput, UI_STRinfo

                                page_trans = {}

                                with gr.Group():
                                    gr.Markdown("### SAV Training Dataset", elem_classes="boxed-markdown")
                                    page_trans["sav_info"] = UI_SAVLABELinput()

                                with gr.Group():
                                    page_trans["str_activate"] = gr.Button("✢	Assign or upload your structure")

                                    with gr.Group(visible=False) as str_input_group:
                                        gr.Markdown("### Assign or upload your structure", elem_classes="boxed-markdown")
                                        page_trans["str_info"] = UI_STRinfo()

                                    page_trans["str_activate"].click(
                                        fn=lambda: (gr.update(visible=False), gr.update(visible=True)),
                                        inputs=[],
                                        outputs=[page_trans["str_activate"], str_input_group]
                                    )

                                with gr.Group():
                                    page_trans["submit_btn"] = gr.Button("Submit a transfer learning task")
                                    page_trans["submit_status"] = gr.Textbox(label="Submission Status", interactive=False, visible=False)

                                # --- Conditional Visibility Wrappers ---
                                with gr.Column(visible=False) as result_section:
                                    page_trans["result"] = {"section": result_section}

                                    with gr.Group():
                                        gr.Markdown("### Results", elem_classes="boxed-markdown")
                                        page_trans["result"]["select"] = gr.Dropdown(
                                            choices = [],
                                            interactive=True,
                                            label = "Submission Select"
                                        )
                                        page_trans["result"]["output"] = gr.Textbox(label="Result Output", lines=6)
                                        page_trans["result"]["table"] = gr.Dataframe(headers=["SAVs", "Probability", "Decision", "Voting (%)"])
                                        page_trans["result"]["zip"] = gr.File(label="Download Results (.zip)")
                                        # processing_start_time = gr.State(None)
                                        # check_btn = gr.Button("Check Results")

                                def submit_job_trans(
                                        session_id,
                                        sav_txt, sav_txt_state, sav_btn, sav_btn_state,
                                        str_txt, str_txt_state, str_btn, str_btn_state
                                    ):

                                    if not session_id:
                                        return gr.update(visible=True, value="❌ No session ID"), gr.State("")

                                    if sav_btn_state:
                                        SAV_input = sav_btn
                                    elif sav_txt_state:
                                        SAV_input = sav_txt
                                    else:
                                        SAV_input = None

                                    if not SAV_input:
                                        return gr.update(visible=True, value="❌ No SAV input provided"), gr.State("")

                                    while True:
                                        submission_id = f"{session_id}-{generate_session_id()}"
                                        if input_col.find_one({"submission_id": submission_id}) is None:
                                            break

                                    if str_btn_state:
                                        folder = os.path.join(JOB_DIR, submission_id)
                                        os.makedirs(folder, exist_ok=True)
                                        shutil.copy(str_btn, folder)

                                        filename = os.path.basename(str_btn)
                                        filepath = os.path.join(folder, filename)
                                        os.chmod(filepath, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)

                                        STR_input = filename
                                    elif str_txt_state:
                                        STR_input = str_txt
                                    else:
                                        STR_input = None

                                    SAV_input = handle_sav_input(SAV_input, with_labels=True)

                                    payload = {
                                        "session_id": session_id,
                                        "submission_id": submission_id,
                                        "ts": time.time_ns(),
                                        "with_labels": True,
                                        "SAV_input": SAV_input,
                                        "STR_input": STR_input,
                                        "status": "pending",
                                        "result": None
                                    }
                                    input_col.insert_one(payload)

                                    logging.info(f"✅ Submitted input: {payload}")

                                    return gr.update(visible=True, value=f"✅ Submitted with payload: {payload}"), submission_id


                                def refresh_msg_trans(submission_id):
                                    """
                                    Returns:
                                        - result_msg (str): display in frontend textbox
                                        - timer_value (float or None): Time interval to wait before the next polling.
                                                                    If None, polling is stopped (i.e., job is complete).
                                    """
                                    if not submission_id:
                                        return "❌ No submission ID", 10.0, None

                                    data = input_col.find_one({"submission_id": submission_id}) or input_col.find_one({"session_id": submission_id})

                                    if data is None:
                                        return "❌ Input for this submission ID not found.",  10.0, None
                                    elif data["status"] == "pending":
                                        return "⏳ Waiting in queue...", 3.0, None
                                    elif data["status"] == "processing":
                                        elapsed = int(time.time_ns() - data.get("ts", time.time_ns())) // 1_000_000_000
                                        emoji_frames = ["⏳", "🔄", "🔁", "🔃"]
                                        icon = emoji_frames[elapsed % len(emoji_frames)]

                                        animated_msg = f"{icon} Model is running... {elapsed} second{'s' if elapsed != 1 else ''} since queued."

                                        return animated_msg, 1.0

                                    return "✅ Transfer Learning complete. You may download the results below.", 10.0, None


                                def check_result_trans(submission_id):
                                    """
                                    Returns:
                                        - result_table (List[List[Any]]): A list of rows parsed from report.txt,
                                                                        shown in a Gradio Dataframe with columns:
                                                                        ["SAVs", "Probability", "Decision", "Voting"]
                                        - zip_file_path (str): Path to the zipped folder containing all result files,
                                                            returned to a Gradio File component for download.
                                        - timer_value (float or None): Time interval to wait before the next polling.
                                                                    If None, polling is stopped (i.e., job is complete).
                                    """
                                    if not submission_id:
                                        return [], None, 10.0

                                    data = input_col.find_one({"submission_id": submission_id}) or input_col.find_one({"session_id": submission_id})

                                    if data is None:
                                        return [], None, 10.0
                                    elif data["status"] in ("pending", "processing", ):
                                        return [], None, 10.0

                                    # Status == finished
                                    logging.info(f"✅ Result found for submission ID {submission_id}: {data}")
                                    table_data = data["result"]
                                    zip_path = f"/shared/results/{submission_id}_results.zip"

                                    return table_data, zip_path, 10.0


                                def refresh_results_trans(session_id, result_section):
                                    if not session_id:
                                        return

                                    history = input_col.find({"session_id": session_id, "with_labels": True})
                                    if not history:
                                        return

                                    hist = list(sorted(history, key=lambda x: -x.get("ts",0)))
                                    if not hist:
                                        return

                                    args = {
                                        "visible": True,
                                        "choices": [s.get("submission_id", session_id) for s in hist],
                                        "value": result_section if result_section else hist[0].get("submission_id", session_id)
                                    }

                                    return gr.update(visible=True), gr.update(**args), *check_result_pred(args["value"])


                                # Timer to check result every 10 seconds
                                page_trans["timer"] = gr.Timer(value=2.0, active=True)
                                page_trans["timer_msg"] = gr.Timer(value=3.0, active=True)

                                page_trans["timer"].tick(
                                    fn=refresh_results_trans,
                                    inputs=[session_id_state, page_trans["result"]["select"]],
                                    outputs=[page_trans["result"]["section"], page_trans["result"]["select"], page_trans["result"]["table"], page_trans["result"]["zip"], page_trans["timer"]]
                                )
                                page_trans["timer_msg"].tick(
                                    fn=refresh_msg_trans,
                                    inputs=[page_trans["result"]["select"]],
                                    outputs=[page_trans["result"]["output"], page_trans["timer_msg"]]
                                )

                                # timer_control = gr.State()  # dummy variable to catch the second output

                                # 1. First run submit_input()
                                page_trans["submit_btn"].click(
                                    fn=submit_job_trans,
                                    inputs=[
                                        session_id_state,
                                        page_trans["sav_info"]["text"]["data"], page_trans["sav_info"]["text"]["stat"], page_trans["sav_info"]["file"]["data"], page_trans["sav_info"]["file"]["stat"],
                                        page_trans["str_info"]["text"]["data"], page_trans["str_info"]["text"]["stat"], page_trans["str_info"]["file"]["data"], page_trans["str_info"]["file"]["stat"],
                                    ],
                                    outputs=[page_trans["submit_status"], submission_id_state]
                                # ).then( # 2. Reset processing timer after submission
                                #     fn=lambda: None,
                                #     inputs=[],
                                #     outputs=processing_start_time
                                ).then(# 3. Call check_result()
                                    fn=refresh_results_trans,
                                    inputs=[session_id_state, submission_id_state],
                                    outputs=[page_trans["result"]["section"], page_trans["result"]["select"], page_trans["result"]["table"], page_trans["result"]["zip"], page_trans["timer"]]
                                ).then(
                                    fn=refresh_msg_trans,
                                    inputs=[page_trans["result"]["select"]],
                                    outputs=[page_trans["result"]["output"], page_trans["timer_msg"]]
                                )

                                page_trans["result"]["select"].change(
                                    fn=refresh_results_trans,
                                    inputs=[session_id_state, page_trans["result"]["select"]],
                                    outputs=[page_trans["result"]["section"], page_trans["result"]["select"], page_trans["result"]["table"], page_trans["result"]["zip"], page_trans["timer"]]
                                ).then(
                                    fn=refresh_msg_trans,
                                    inputs=[page_trans["result"]["select"]],
                                    outputs=[page_trans["result"]["output"], page_trans["timer_msg"]]
                                )


        start_session_btn.click(
            fn=start_session,
            inputs=session_id_box,
            outputs=[
                session_id_box,  # updated textbox (with UUID or frozen)
                start_session_btn,  # disable button
                session_id_state,   # store session_id
                session_locked_state,  # set to True
                session_status,     # update message
                workspace,
            ]
        ).then(
            fn=refresh_results_pred,
            inputs=[session_id_state, page_pred["result"]["select"]],
            outputs=[page_pred["result"]["section"], page_pred["model_select"], page_pred["result"]["select"], page_pred["result"]["table"], page_pred["result"]["zip"], page_pred["timer"]]
        ).then(
            fn=refresh_msg_pred,
            inputs=[page_pred["result"]["select"]],
            outputs=[page_pred["result"]["output"], page_pred["timer_msg"]]
        )

        with gr.Tab("Tutorial"):
            with open("src/tutorial.md") as f:
                md = f.read()
            gr.Markdown(md)

        with gr.Tab("Source Code"):
            with open("src/open_source.md") as f:
                md = f.read()
            gr.Markdown(md)

# debug=True for auto-reload
demo.launch(
    server_name="0.0.0.0",
    allowed_paths=["/shared/results"],
    root_path="/TANDEM")