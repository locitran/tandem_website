import gradio as gr
import secrets
import base64
import logging
import time
import os
import shutil
import stat
from pymongo import MongoClient

from src.tutorial import tutorial
from src.queryUI import UI_SAVinput, UI_STRinput
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
            f"🔄 New session ID ({new_id}) has been generated. <br>ℹ️ Please save the session ID for future reference.",
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

# def submit_input(submission_id, text_input, file_input):
#     if not submission_id:
#         return "❌ No submission ID"

#     file_content_b64 = None
#     if file_input is not None:
#         file_content_b64 = base64.b64encode(file_input).decode("utf-8")

#     payload = {
#         "submission_id": submission_id,
#         "text": text_input,
#         "file": file_content_b64,
#         "status": "pending",
#         "result": None
#     }
#     input_col.insert_one(payload)

#     logging.info(f"✅ Submitted input: {payload}")

#     return f"✅ Submitted with payload: {payload}"

def submit_job(
        session_id,
        sav_txt, sav_txt_state, sav_btn, sav_btn_state,
        str_txt, str_txt_state, str_btn, str_btn_state
    ):
    
    if not session_id:
        return "❌ No session ID"

    while True:
        submission_id = f"{session_id}-{generate_session_id()}"
        if input_col.find_one({"submission_id": submission_id}) is None:
            break
    
    if sav_btn_state:
        SAV_input = sav_btn
    elif sav_txt_state:
        SAV_input = sav_txt
    else:
        SAV_input = None
    
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

    payload = {
        "session_id": session_id,
        "submission_id": submission_id,
        "ts": time.time_ns(),
        "SAV_input": SAV_input,
        "STR_input": STR_input,
        "status": "pending",
        "result": None
    }
    input_col.insert_one(payload)

    logging.info(f"✅ Submitted input: {payload}")

    return f"✅ Submitted with payload: {payload}", submission_id


def refresh_msg(submission_id, processing_start_time):
    """
    Returns:
        - result_msg (str): display in frontend textbox
        - timer_value (float or None): Time interval to wait before the next polling.
                                       If None, polling is stopped (i.e., job is complete).
        - processing_start_time (float): for tracking elapsed time
    """
    if not submission_id:
        return "❌ No submission ID", 10.0, None

    data = input_col.find_one({"submission_id": submission_id}) or input_col.find_one({"session_id": submission_id})

    if data is None:
        return "❌ Input for this submission ID not found.",  10.0, None
    elif data["status"] == "pending":
        return "⏳ Waiting in queue...", 3.0, None
    elif data["status"] == "processing":
        # Start timer
        if processing_start_time is None:
            processing_start_time = time.time()

        elapsed = int(time.time() - processing_start_time)
        emoji_frames = ["⏳", "🔄", "🔁", "🔃"]
        icon = emoji_frames[elapsed % len(emoji_frames)]

        animated_msg = f"{icon} Model is running... {elapsed} second{'s' if elapsed != 1 else ''} elapsed."

        return animated_msg, 1.0, processing_start_time

    return "✅ Inference complete. You may download the results below.", 10.0, None


def check_result(submission_id):
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


def refresh_results(session_id, result_section):
    if not session_id:
        return

    history = input_col.find({"session_id": session_id})
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

    return gr.update(visible=True), gr.update(**args), *check_result(args["value"])


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
                    gr.Markdown("""
                    ### What is TANDEM-DIMPLE?
                    A DNN-based foundation model designed for disease-specific pathogenicity prediction of missense variants. It integrates protein dynamics with sequence, chemical, and structural features and uses transfer learning to refine models for specific diseases. Trained on ~20,000 variants, it achieves high accuracy in general predictions (83.6%) and excels in disease-specific contexts, reaching 98.7% accuracy for GJB2 and 97.0% for RYR1, surpassing tools like Rhapsody and AlphaMissense. TANDEM-DIMPLE supports clinicians and geneticists in classifying new variants and improving diagnostic tools for genetic disorders.
                    """)
                    gr.Image(value="3.1.png", label="", show_label=False, width=None)
                    gr.Markdown("""
                    **Reference:** Loci Tran, Lee-Wei Yang, Transfer-leArNing-ready and Dynamics-Empowered Model for Disease-specific Missense Pathogenicity Level Estimation. (In preparation)  
                    **Contact:** The server is maintained by the Yang Lab at the Institute of Bioinformatics and Structural Biology at National Tsing Hua University, Taiwan.  
                    **Email:** locitran0521@gmail.com
                    """)

                # --- RIGHT COLUMN ---
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown("### Session", elem_classes="boxed-markdown")

                        session_id_box = gr.Textbox(label="Session ID", placeholder="Start a new session or paste an existing session ID", interactive=True)
                        with gr.Row():
                            start_session_btn = gr.Button("▶️ Start / Resume Session")
                        session_status = gr.Markdown("", elem_classes="boxed-markdown")

                    # --- Conditional Visibility Wrappers ---
                    with gr.Column(visible=False) as input_section:
                        with gr.Group():
                            gr.Markdown("### User input", elem_classes="boxed-markdown")
                            
                            sav_txt, sav_txt_state, sav_btn, sav_btn_state = UI_SAVinput()
                            str_txt, str_txt_state, str_btn, str_btn_state = UI_STRinput()
                            
                            model_select = gr.Dropdown(
                                choices = ["Foundation-Model"],
                                value = "Foundation-Model",
                                interactive=True
                            )
                            submit_btn = gr.Button("Submit")
                            submit_status = gr.Textbox(label="Submission Status", interactive=False)

                    # --- Conditional Visibility Wrappers ---
                    with gr.Column(visible=False) as result_section:
                        with gr.Group():
                            gr.Markdown("### Results", elem_classes="boxed-markdown")
                            result_select = gr.Dropdown(
                                choices = [],
                                interactive=True,
                                label = "Submission Select"
                            )
                            result_output = gr.Textbox(label="Result Output", lines=6)
                            result_table = gr.Dataframe(headers=["SAVs", "Probability", "Decision", "Voting (%)"])
                            result_zip = gr.File(label="Download Results (.zip)")
                            processing_start_time = gr.State(None)

                            check_btn = gr.Button("Check Results")

            # Timer to check result every 10 seconds
            timer = gr.Timer(value=10.0, active=True)
            timer_msg = gr.Timer(value=3.0, active=True)
            
            timer.tick(
                fn=refresh_results,
                inputs=[session_id_state, result_select],
                outputs=[result_section, result_select, result_table, result_zip, timer]
            )
            timer_msg.tick(
                fn=refresh_msg,
                inputs=[result_select, processing_start_time],
                outputs=[result_output, timer_msg, processing_start_time]
            )

            timer_control = gr.State()  # dummy variable to catch the second output

            # 1. First run submit_input()
            submit_btn.click(
                fn=submit_job,
                inputs=[
                    session_id_state,
                    sav_txt, sav_txt_state, sav_btn, sav_btn_state,
                    str_txt, str_txt_state, str_btn, str_btn_state,
                ],
                outputs=[submit_status, submission_id_state]
            ).then( # 2. Reset processing timer after submission
                fn=lambda: None,
                inputs=[],
                outputs=processing_start_time
            ).then(# 3. Call check_result()
                fn=refresh_results,
                inputs=[session_id_state, submission_id_state],
                outputs=[result_section, result_select, result_table, result_zip, timer]
            ).then(
                fn=refresh_msg,
                inputs=[result_select, processing_start_time],
                outputs=[result_output, timer_msg, processing_start_time]
            )

            result_select.change(
                fn=refresh_results,
                inputs=[session_id_state, result_select],
                outputs=[result_section, result_select, result_table, result_zip, timer]
            ).then(
                fn=refresh_msg,
                inputs=[result_select, processing_start_time],
                outputs=[result_output, timer_msg, processing_start_time]
            )

            check_btn.click(
                fn=refresh_results,
                inputs=[session_id_state, result_select],
                outputs=[result_section, result_select, result_table, result_zip, timer]
            ).then(
                fn=refresh_msg,
                inputs=[result_select, processing_start_time],
                outputs=[result_output, timer_msg, processing_start_time]
            )

            # --- Event hooks ---

            start_session_btn.click(
                fn=start_session,
                inputs=session_id_box,
                outputs=[
                    session_id_box,  # updated textbox (with UUID or frozen)
                    start_session_btn,  # disable button
                    session_id_state,   # store session_id
                    session_locked_state,  # set to True
                    session_status,     # update message
                    input_section,
                ]
            ).then(
                fn=refresh_results,
                inputs=[session_id_state, result_select],
                outputs=[result_section, result_select, result_table, result_zip, timer]
            ).then(
                fn=refresh_msg,
                inputs=[result_select, processing_start_time],
                outputs=[result_output, timer_msg, processing_start_time]
            )
            
        with gr.Tab("Transfer learning"):
                gr.Markdown("## Transfer learning")
                gr.Markdown("""
                TANDEM-DIMPLE uses transfer learning to adapt a general model to specific diseases. 
                It refines the model using disease-specific data, improving accuracy for variants associated with those diseases.
                """)
            
        with gr.Tab("Tutorial"):
            gr.Markdown("# Tutorial")
            tutorial()

        with gr.Tab("Github"):
            gr.Markdown("""
            👉 [Click here to open the GitHub repository](https://github.com/locitran/tandem-dimple)
            """)
        
# debug=True for auto-reload
demo.launch(server_name="0.0.0.0", allowed_paths=["/shared/results"], root_path="/TANDEM")
