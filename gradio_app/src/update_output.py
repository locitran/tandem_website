import shutil
import math
import os 
import json

from yattag import Doc
import pandas as pd 
import gradio as gr

from .logger import LOGGER

def on_fold(fold_id, folds_state):
    fold = folds_state[fold_id]
    return (
        ",".join(fold["train"]),
        ",".join(fold["val"]),
        ",".join(fold["test"]),
    )
    
def safe(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "-"
    return v

def fmt_prob(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "-"
    return f"{float(v):.3f}"

def render_test_evaluation(df):
    """
    df columns: ['metric', 'TANDEM', 'TANDEM-DIMPLE']
    """
    doc, tag, text = Doc().tagtext()

    with tag("table", klass="pred-table"):
        # ===== THEAD =====
        with tag("thead"):
            with tag("tr"):
                for col in df.columns:
                    with tag("th"):
                        text(col)

        # ===== TBODY =====
        with tag("tbody"):
            for _, row in df.iterrows():
                with tag("tr"):
                    with tag("td"):
                        text(row["metric"])
                    with tag("td"):
                        text(f"{row['TANDEM']:.2f}")
                    with tag("td"):
                        text(f"{row['TANDEM-DIMPLE']:.2f}")

    return doc.getvalue()

def multindex_DataFrame(df):
    
    df.columns = pd.MultiIndex.from_tuples(
        tuple(col.split("::", 1)) if "::" in col else (col, "")
        for col in df.columns
    )
        
    rows = df.to_dict("records")
    has_tf = ('TANDEM-DIMPLE', 'probability') in rows[0].keys()

    # ---------- build HTML ----------
    doc, tag, text = Doc().tagtext()

    with tag("table", klass="pred-table"):
        # ===== THEAD =====
        with tag("thead"):
            # --- header row 1 ---
            with tag("tr"):
                with tag("th", rowspan="2"):
                    text("Index")
                with tag("th", rowspan="2"):
                    text("SAV")
                with tag("th", colspan="2"):
                    text("TANDEM")
                if has_tf:
                    with tag("th", colspan="2"):
                        text("TANDEM-DIMPLE")

            # --- header row 2 ---
            with tag("tr"):
                with tag("th"):
                    text("probability")
                with tag("th"):
                    text("classification")
                if has_tf:
                    with tag("th"):
                        text("probability")
                    with tag("th"):
                        text("classification")

        # ===== TBODY =====
        with tag("tbody"):
            for i, row in enumerate(rows):
                with tag("tr"):
                    with tag("td"):
                        text(i)
                    with tag("td"):
                        text(safe(row.get(('SAV', 'SAV'))))

                    # TANDEM
                    with tag("td"):
                        text(fmt_prob(row.get(('TANDEM', 'probability'))))
                    with tag("td"):
                        text(safe(row.get(('TANDEM', 'classification'))))

                    # TANDEM-DIMPLE (optional)
                    if has_tf:
                        with tag("td"):
                            text(fmt_prob(row.get(('TANDEM-DIMPLE', 'probability'))))
                        with tag("td"):
                            text(safe(row.get(('TANDEM-DIMPLE', 'classification'))))

    # ---------- final HTML ----------
    html_str = doc.getvalue()
    return html_str

def zip_folder(folder):
    zip_path = os.path.join(folder, 'result.zip')
    zip_base = os.path.join(folder, 'result')
    if not os.path.exists(zip_path):
        shutil.make_archive(zip_base, "zip")
        LOGGER.info(f"Creating Zip {zip_path}")
    return zip_path

def on_select_image(image_name, folder, _param_state):
    if not image_name:
        return gr.update(visible=False)

    path = os.path.join(
        folder, _param_state["session_id"], _param_state["job_name"], 'tandem_shap', image_name)
    return gr.update(value=path, visible=True)

def render_finished_job(_mode, job_folder):

    # ----------- defaults (IMPORTANT) -----------
    output_section_udt = gr.update(visible=True)
    result_zip_udt = gr.update(value=None, interactive=False, visible=False)

    inf_output_secion_udt = gr.update(visible=False)
    pred_table_udt = gr.update(visible=False)
    image_selector_udt = gr.update(visible=False)
    image_viewer_udt = gr.update(visible=False)

    tf_output_secion_udt = gr.update(visible=False)
    folds_state_udt = None
    fold_dropdown_udt = gr.update(visible=False)
    train_box_udt = gr.update(visible=False)
    val_box_udt = gr.update(visible=False)
    test_box_udt = gr.update(visible=False)
    loss_image_udt = gr.update(visible=False)
    test_eval_udt = gr.update(visible=False)

    # ----------- common outputs -----------
    zip_path = zip_folder(job_folder)
    result_zip_udt = gr.update(
        value=zip_path,
        interactive=True,
        visible=bool(zip_path)
    )

    # ----------- Inferencing mode -----------
    if _mode == "Inferencing":
        inf_output_secion_udt = gr.update(visible=True)

        pred_file = os.path.join(job_folder, "predictions.csv")
        df_pred = pd.read_csv(pred_file)
        pred_table_udt = gr.update(
            value=multindex_DataFrame(df_pred),
            visible=True
        )

        tandem_shap = os.path.join(job_folder, "tandem_shap")
        list_images = os.listdir(tandem_shap) if os.path.isdir(tandem_shap) else []

        image_selector_udt = gr.update(
            choices=list_images,
            value=list_images[0] if list_images else None,
            visible=bool(list_images),
        )

        image_viewer_udt = gr.update(
            value=os.path.join(tandem_shap, list_images[0]) if list_images else None,
            visible=bool(list_images),
        )

    # ----------- Transfer Learning mode -----------
    elif _mode == "Transfer Learning":
        tf_output_secion_udt = gr.update(visible=True)

        folds_path = os.path.join(job_folder, "cross_validation_SAVs.json")
        with open(folds_path) as f:
            folds = json.load(f)

        fold_ids = sorted(folds.keys())
        init_train, init_val, init_test = on_fold(fold_ids[0], folds)

        folds_state_udt = folds
        fold_dropdown_udt = gr.update(choices=fold_ids, value=fold_ids[0], visible=True)

        train_box_udt = gr.update(value=init_train, visible=True)
        val_box_udt = gr.update(value=init_val, visible=True)
        test_box_udt = gr.update(value=init_test, visible=True)

        loss_img = os.path.join(job_folder, "loss.png")
        loss_image_udt = gr.update(value=loss_img, visible=os.path.exists(loss_img))

        test_eval = os.path.join(job_folder, "test_evaluation.csv")
        df_test_eval = pd.read_csv(test_eval)
        html_str = render_test_evaluation(df_test_eval)
        test_eval_udt = gr.update(value=html_str, visible=True)

    # ----------- return (SAFE) -----------
    return (
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
    )

def render_output(param_state, folder):
    ""
    _job_status = param_state.get('status', None)
    _mode = param_state.get("mode", None)

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

    if _job_status != "finished":
        return (
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
        )

    _session_id = param_state["session_id"]
    _job_name   = param_state["job_name"]
    job_folder = os.path.join(folder, _session_id, _job_name) 
    return render_finished_job(_mode, job_folder)

if __name__ == "__main__":
    pass