import gradio as gr
import uuid
import base64
from pymongo import MongoClient

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
input_col = db["input_queue"]

# Check database
print("✅ Connected. Collections:", db.list_collection_names())


# --- BACKEND LOGIC ---

def generate_new_session():
    new_id = str(uuid.uuid4())
    return (
        gr.update(value=new_id, label="Session ID in use", interactive=False, elem_classes="session-frozen"),
        gr.update(interactive=False),
        gr.update(interactive=False),
        new_id,
        True,
        "✅ New session ID generated and confirmed.",
        gr.update(visible=True),
        gr.update(visible=True)
    )

def confirm_session(session_id):
    if not session_id:
        return (
            gr.update(label="❌ Invalid Session ID", interactive=True, elem_classes=""),
            gr.update(interactive=True),
            gr.update(interactive=True),
            "",
            False,
            "❌ Please enter a valid session ID.",
            gr.update(visible=False),
            gr.update(visible=False)
        )
    return (
        gr.update(label="Session ID in use", interactive=False, elem_classes="session-frozen"),
        gr.update(interactive=False),
        gr.update(interactive=False),
        session_id,
        True,
        "✅ Session ID confirmed.",
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

    return f"✅ Submitted with payload: {payload}"

def check_result(session_id):
    if not session_id:
        return "❌ No session ID", 10.0

    result = input_col.find_one({"session_id": session_id})

    if result is None:
        return "❌ Input for this session ID not found.", 10.0
    elif result["status"] == "pending":
        return "⏳ Result not ready yet. (Still pending ... would update if finished)", 3.0
    elif result["status"] == "processing":
        return "⏳ Result not ready yet. (Still processing ... would update if finished)", 3.0
    
    return result, None if result else "⏳ Result not ready yet."

# --- FRONTEND UI ---

with gr.Blocks(css=".session-frozen { background-color: #f0f0f0; color: #666 !important; }") as demo:
    gr.Markdown("## 🧪 Tandem-Dimple App with Session Control")

    session_id_state = gr.State("")
    session_locked_state = gr.State(False)

    with gr.Row():
        session_id_box = gr.Textbox(label="Enter your Session ID", placeholder="Paste or generate one", interactive=True, elem_id="session-box")
        session_status = gr.Markdown("")  # Inline status message

    with gr.Row():
        new_session_btn = gr.Button("🔄 New Session ID", interactive=True)
        confirm_session_btn = gr.Button("✅ Confirm Session ID", interactive=True)

    # --- Conditional Visibility Wrappers ---
    with gr.Column(visible=False) as input_section:
        gr.Markdown("### Step 1: Submit Your Input")
        text_input = gr.Textbox(label="Text Input")
        file_input = gr.File(label="Optional File Upload", type="binary")
        submit_btn = gr.Button("Submit")
        submit_status = gr.Textbox(label="Submission Status", interactive=False)

        submit_btn.click(fn=submit_input,
                         inputs=[session_id_state, text_input, file_input],
                         outputs=submit_status)

    with gr.Column(visible=False) as result_section:
        gr.Markdown("### Step 2: Check Your Result")
        check_btn = gr.Button("Check Result")
        result_output = gr.Textbox(label="Result Output", interactive=False)

        # Timer to check result every 3 seconds
        timer = gr.Timer(value=3.0, active=True)
        timer.tick(
            fn=check_result,
            inputs=[session_id_box],
            outputs=[result_output, timer]
        )

        timer_control = gr.State()  # dummy variable to catch the second output

        check_btn.click(fn=check_result,
                        inputs=session_id_state,
                        outputs=[result_output, timer_control])

    # --- Event hooks ---

    new_session_btn.click(
        fn=generate_new_session,
        outputs=[
            session_id_box,
            new_session_btn,
            confirm_session_btn,
            session_id_state,
            session_locked_state,
            session_status,
            input_section,
            result_section
        ]
    )

    confirm_session_btn.click(
        fn=confirm_session,
        inputs=session_id_box,
        outputs=[
            session_id_box,
            new_session_btn,
            confirm_session_btn,
            session_id_state,
            session_locked_state,
            session_status,
            input_section,
            result_section
        ]
    )

# debug=True for auto-reload
demo.launch(server_name="0.0.0.0", debug=True)