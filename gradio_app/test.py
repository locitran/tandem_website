import json
import gradio as gr
from pathlib import Path

JSON_PATH = "/home/loci/tandem_website/tandem/jobs/tf_GJB2/cross_validation_SAVs.json"

# ---------- Load JSON ----------
with open(JSON_PATH) as f:
    cv_data = json.load(f)

# Normalize fold names (string-safe)
fold_names = list(cv_data.keys())


# ---------- Helper ----------
def format_savs(savs):
    if not savs:
        return "_(Empty)_"
    return "\n".join(savs)


# ---------- Callback ----------
def load_fold(fold_name):
    fold = cv_data[fold_name]
    return (
        format_savs(fold.get("train", [])),
        format_savs(fold.get("val", [])),
        format_savs(fold.get("test", [])),
    )


# ---------- UI ----------
with gr.Blocks() as demo:
    gr.Markdown("## 🔬 Cross-Validation SAV Viewer")

    gr.Markdown(
        "Select a **fold** to inspect which SAVs were used for "
        "**training**, **validation**, and **testing**."
    )

    fold_selector = gr.Dropdown(
        choices=fold_names,
        value=fold_names[0],
        label="Select Fold",
        interactive=True,
    )

    with gr.Accordion("🟦 Training SAVs", open=True):
        train_box = gr.Textbox(lines=10, interactive=False)

    with gr.Accordion("🟨 Validation SAVs", open=False):
        val_box = gr.Textbox(lines=6, interactive=False)

    with gr.Accordion("🟥 Test SAVs", open=False):
        test_box = gr.Textbox(lines=6, interactive=False)

    fold_selector.change(
        fn=load_fold,
        inputs=fold_selector,
        outputs=[train_box, val_box, test_box],
    )

    # Load initial fold
    demo.load(
        fn=lambda: load_fold(fold_names[0]),
        outputs=[train_box, val_box, test_box],
    )

demo.launch(share=True)