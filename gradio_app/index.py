import gradio as gr
import secrets
import base64
import logging
import time
from pymongo import MongoClient

from tutorial import tutorial

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

client = MongoClient("localhost:27017")
db = client["app_db"]
input_col = db["input_queue"]

# Check database
logging.info(f"✅ Connected. Collections: {db.list_collection_names()}")

# --- BACKEND LOGIC ---

def generate_session_id(length=10):
    return secrets.token_urlsafe(length)[:length]  # e.g., 'Xyz82Gk4vB'

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
            gr.update(visible=True)
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
            gr.update(visible=False)
        )

    # Case 3: Valid existing session
    return (
        gr.update(label="Session ID in use", interactive=False, elem_classes="session-frozen"),
        gr.update(interactive=False),
        session_id_input,
        True,
        f"✅ Session ({session_id_input}) resumed.",
        gr.update(visible=True),
        gr.update(visible=True)
    )

def submit_input(session_id, text_input, file_input):
    if not session_id:
        return "❌ No session ID"

    file_content_b64 = None
    if file_input is not None:
        file_content_b64 = base64.b64encode(file_input).decode("utf-8")

    payload = {
        "session_id": session_id,
        "text": text_input,
        "file": file_content_b64,
        "status": "pending",
        "result": None
    }
    input_col.insert_one(payload)

    logging.info(f"✅ Submitted input: {payload}")

    return f"✅ Submitted with payload: {payload}"

def check_result(session_id, processing_start_time):
    """
    Returns:
        - result_msg (str): display in frontend textbox
        - result_table (List[List[Any]]): A list of rows parsed from report.txt, 
                                          shown in a Gradio Dataframe with columns:
                                        ["SAVs", "Probability", "Decision", "Voting"]
        - zip_file_path (str): Path to the zipped folder containing all result files,
                               returned to a Gradio File component for download.
        - timer_value (float or None): Time interval to wait before the next polling.
                                       If None, polling is stopped (i.e., job is complete).
        - processing_start_time (float): for tracking elapsed time
    """
    if not session_id:
        return "❌ No session ID", [], None, 10.0, None

    data = input_col.find_one({"session_id": session_id})

    if data is None:
        return "❌ Input for this session ID not found.", [], None, 10.0, None
    elif data["status"] == "pending":
        return "⏳ Waiting in queue...", [], None, 3.0, None
    elif data["status"] == "processing":
        # Start timer
        if processing_start_time is None:
            processing_start_time = time.time()

        elapsed = int(time.time() - processing_start_time)
        emoji_frames = ["⏳", "🔄", "🔁", "🔃"]
        icon = emoji_frames[elapsed % len(emoji_frames)]

        animated_msg = f"{icon} Model is running... {elapsed} second{'s' if elapsed != 1 else ''} elapsed."

        return animated_msg, [], None, 1.0, processing_start_time

    # Status == finished
    logging.info(f"✅ Result found for session ID {session_id}: {data}")
    table_data = data["result"]
    zip_path = f"/shared/results/{session_id}_results.zip"

    return "✅ Inference complete. You may download the results below.", table_data, zip_path, None, None

# --- FRONTEND UI ---

def update_visibility(choice):
    return (
        gr.update(visible=(choice == "Text input")),
        gr.update(visible=(choice == "Upload file"))
    )

def toggle_custom_pdb(use_custom):
    enabled = use_custom is True
    return (
        gr.update(interactive=enabled),  # textbox
        gr.update(interactive=enabled),  # file
        gr.update(interactive=enabled),  # env checkbox
    )    

# === CSS Styling ===
with open("style.css", "r") as f:
    custom_css = f.read()
  
with gr.Blocks(css=custom_css) as demo:
    
    with gr.Tabs():
        
        with gr.Tab("Home"):
            gr.Markdown("## TANDEM-DIMPLE: Transfer-leArNing-ready \
                    and Dynamics-Empowered Model for Disease-specific \
                    Missense Pathogenicity Level Estimation")

            session_id_state = gr.State("")
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

                        session_id_box = gr.Textbox(label="Session ID", 
                                placeholder="Start a new session or paste an existing session ID", 
                                interactive=True)
                        with gr.Row():
                            start_session_btn = gr.Button("▶️ Start / Resume Session")
                        session_status = gr.Markdown("", elem_classes="boxed-markdown")


                    # --- Conditional Visibility Wrappers ---
                    with gr.Column(visible=False) as input_section:
                        with gr.Group():
                            gr.Markdown("### User input", elem_classes="boxed-markdown")
 
                            # Create two tags
                            # 1: Batch of SAVs
                            # 2: Mutagenesis study
                            with gr.Tabs(elem_classes=["input-tags"]):
                                with gr.TabItem("Batch of SAVs"):
                                    SAVs_input = gr.Radio(
                                        ["Text input", "Upload file"],
                                        label="""Batch of Single Amino Acid Variants (SAVs) \n \
                                            SAV format: [UniProt ID] [position] \
                                            [wild-type amino acid] [mutated amino acid]
                                            """,
                                        value="Text input",
                                        elem_classes=["input-SAVs"]
                                    )
                                    text_input = gr.Textbox(
                                        label="", 
                                        placeholder="O14508 52 S N\nP29033 217 Y D\n...", 
                                        info=None, 
                                        elem_classes=["large-info"],
                                        lines=4
                                    )
                                    file_input = gr.File(
                                        label="Upload SAV list (.txt, .csv, .xlsx)",
                                        file_types=[".txt", ".csv", ".xlsx"],
                                        visible=False,
                                    )
                                    SAVs_input.change(fn=update_visibility, inputs=SAVs_input, 
                                                    outputs=[text_input, file_input])
                                    
                                with gr.TabItem("Saturation Mutagenesis"):
                                    text_input = gr.Textbox(
                                        label="UniProt ID (w/wo position)",
                                        placeholder="P29033", 
                                        info="type the Uniprot accession number of a human sequence", 
                                        elem_classes=["large-info"],
                                        lines=1
                                    )

                            customPDB = gr.Checkbox(label="🧩 Use custom structure", value=False)
                            method = gr.Radio(["Type a PDB ID", "Upload protein structure"], 
                                label="""
                                If provided, the custom structure will be used to map the SAV(s) \
                                and calculate structural dynamics features.\n \
                                Otherwise, a structure will be automatically selected from the UniProt database.""",
                                value="Type a PDB code", 
                                interactive=False, visible=True,
                                elem_classes=["input-customPDB"])
                            pdb_code = gr.Textbox(label="PDB ID...", 
                                                  placeholder="e.g., 2ZW3", 
                                                  interactive=False, visible=True)
                            pdb_file = gr.File(label="Upload a .pdb or .cif file",
                                               file_types=[".pdb", ".cif"], 
                                               interactive=False, visible=True)
                            customPDB.change(fn=toggle_custom_pdb, inputs=customPDB, 
                                             outputs=[method, pdb_code, pdb_file])

                            submit_btn = gr.Button("Submit")
                            submit_status = gr.Textbox(label="Submission Status", interactive=False)

                    # --- Conditional Visibility Wrappers ---
                    with gr.Column(visible=False) as result_section:
                        with gr.Group():
                            gr.Markdown("### Results", elem_classes="boxed-markdown")
                            result_output = gr.Textbox(label="Result Output", lines=6)
                            result_table = gr.Dataframe(headers=["SAVs", "Probability", "Decision", "Voting (%)"])
                            result_zip = gr.File(label="Download Results (.zip)")
                            processing_start_time = gr.State(None)

                            check_btn = gr.Button("Check Result")

            # Timer to check result every 3 seconds
            timer = gr.Timer(value=3.0, active=True)
            timer.tick(
                fn=check_result,
                inputs=[session_id_state, processing_start_time],
                outputs=[result_output, result_table, result_zip, timer, processing_start_time]
            )

            timer_control = gr.State()  # dummy variable to catch the second output

            # 1. First run submit_input()
            submit_btn.click(
                fn=submit_input,
                inputs=[session_id_state, text_input, file_input],
                outputs=submit_status
            ).then(
                # 2. Reset processing timer after submission
                fn=lambda: None,
                inputs=[],
                outputs=processing_start_time
            ).then(
                # 3. Call check_result()
                fn=check_result,
                inputs=[session_id_state, processing_start_time],
                outputs=[result_output, result_table, result_zip, timer, processing_start_time]
            )

            check_btn.click(fn=check_result,
                            inputs=[session_id_state, processing_start_time],
                            outputs=[result_output, result_table, result_zip, timer_control, processing_start_time])

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
                    result_section
                ]
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

        with gr.Tab("About"):
            gr.Markdown("### About TANDEM-DIMPLE")
            gr.Markdown("""
            TANDEM-DIMPLE is a DNN-based foundation model designed for disease-specific pathogenicity prediction of missense variants. It integrates protein dynamics with sequence, chemical, and structural features and uses transfer learning to refine models for specific diseases. Trained on ~20,000 variants, it achieves high accuracy in general predictions (83.6%) and excels in disease-specific contexts, reaching 98.7% accuracy for GJB2 and 97.0% for RYR1, surpassing tools like Rhapsody and AlphaMissense. TANDEM-DIMPLE supports clinicians and geneticists in classifying new variants and improving diagnostic tools for genetic disorders.
            """)
            gr.Image(value="3.1.png", label="", show_label=False, width=None)
            
            gr.Markdown("""
            **Reference:** Loci Tran, Lee-Wei Yang, Transfer-leArNing-ready and Dynamics-Empowered Model for Disease-specific Missense Pathogenicity Level Estimation. (In preparation)
            **Contact:** The server is maintained by the Yang Lab at the Institute of Bioinformatics and Structural Biology at National Tsing Hua University, Taiwan.
            **Email:** locitran0521@gmail.com""")

        with gr.Tab("Github"):
            gr.Markdown("""
            👉 [Click here to open the GitHub repository](https://github.com/locitran/tandem-dimple)
            """)
            # Click -> link to GitHub repository
            # How to click to this tag -> link to GitHub repository
        

    
# debug=True for auto-reload
demo.launch(share=True, server_name="0.0.0.0", allowed_paths=["/shared/results"], root_path="/TANDEM")
