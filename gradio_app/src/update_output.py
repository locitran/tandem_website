import shutil
import math
import os 
import json

from yattag import Doc
import pandas as pd 
import gradio as gr

from .logger import LOGGER

def on_sav_set_select(selection, folds):
    return folds[selection]

def zip_folder(folder):
    zip_path = os.path.join(folder, 'result.zip')
    zip_base = os.path.join(folder, 'result')
    if not os.path.exists(zip_path):
        shutil.make_archive(zip_base, "zip")
        LOGGER.info(f"Creating Zip {zip_path}")
    return zip_path

def on_select_image(image_name, folder, param):
    if not image_name:
        return gr.update(visible=False)

    path = os.path.join(
        folder, param["session_id"], param["job_name"], 'tandem_shap', image_name)
    return gr.update(value=path, visible=True)

def on_select_sav(evt: gr.SelectData, df, job_folder):
    row_idx, col_idx = evt.index
    sav = df.iloc[row_idx]['SAV']
    shap_img = os.path.join(job_folder, "tandem_shap", f"{sav}.png")
    if os.path.exists(shap_img):
        return gr.update(value=shap_img)
    return gr.update(value=None)

def render_finished_job(_mode, job_folder, _job_name):

    # ----------- defaults (IMPORTANT) -----------
    output_section_udt = gr.update(visible=True)
    result_zip_udt = gr.update(value=None, interactive=False, visible=False)

    inf_output_secion_udt = gr.update(visible=False)
    pred_table_udt = gr.update(visible=False)
    image_viewer_udt = gr.update(visible=False)

    tf_output_secion_udt = gr.update(visible=False)
    folds_state_udt = None
    fold_dropdown_udt = gr.update()
    SAV_textbox_udt = gr.update()
    loss_image_udt = gr.update()
    test_eval_udt = gr.update()
    model_saved_udt = gr.update()
    job_folder_udt = job_folder

    # ----------- common outputs -----------
    zip_path = zip_folder(job_folder)
    result_zip_udt = gr.update(value=zip_path, interactive=True, visible=bool(zip_path))

    # ----------- Inferencing mode -----------
    if _mode == "Inferencing":
        inf_output_secion_udt = gr.update(visible=True)

        pred_file = os.path.join(job_folder, "predictions.csv")
        df_pred = pd.read_csv(pred_file)

        # ---- Add index column FIRST ----
        df_pred = df_pred.reset_index(drop=True)
        df_pred.insert(0, "#", df_pred.index)

        # ---- Send to Gradio ----
        pred_table_udt = gr.update(value=df_pred, visible=True)

        tandem_shap = os.path.join(job_folder, "tandem_shap")
        list_images = os.listdir(tandem_shap) if os.path.isdir(tandem_shap) else []

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

        folds_state_udt = {}
        folds_state_udt['Test set'] = folds["1"]['test']
        for fold_id in sorted(k for k in folds.keys() if k != "test"):
            fold_num = fold_id.replace("fold_", "")
            folds_state_udt[f"Fold {fold_num} - Training set"] = folds[str(fold_num)]['train']
            folds_state_udt[f"Fold {fold_num} - Validation set"] = folds[str(fold_num)]['val']
        choices = folds_state_udt.keys()

        fold_dropdown_udt = gr.update(choices=choices, value='Test set', visible=True)
        SAV_textbox_udt = gr.update(value=folds_state_udt['Test set'], visible=True)

        loss_img = os.path.join(job_folder, "loss.png")
        loss_image_udt = gr.update(value=loss_img, visible=os.path.exists(loss_img))

        test_eval = os.path.join(job_folder, "test_evaluation.csv")
        df_test_eval = pd.read_csv(test_eval)
        test_eval_udt = gr.update(value=df_test_eval, visible=True)
        model_saved_udt = gr.update(value=f"Your models have been saved under name '{_job_name}'!", visible=True)
    return (
        output_section_udt,
        result_zip_udt,

        inf_output_secion_udt,
        pred_table_udt,
        image_viewer_udt,

        tf_output_secion_udt,
        folds_state_udt,
        
        fold_dropdown_udt,
        SAV_textbox_udt,

        loss_image_udt,
        test_eval_udt,
        model_saved_udt,
        job_folder_udt
    )

def update_finished_job(param, folder):
    """
    Handle output-related UI updates:
    - output section visibility
    - prediction table
    - images
    - training / evaluation artifacts
    """
    _session_id = param.get("session_id")
    _job_status = param.get("status")
    _job_name   = param.get("job_name")
    _mode       = param.get("mode")
    # Defaults: hide everything
    def hide_all(n):
        return [gr.update(visible=False) for _ in range(n)]

    if _job_status == "finished":
        job_folder = os.path.join(folder, _session_id, _job_name)
        return render_finished_job(_mode, job_folder, _job_name)
    else:
        return hide_all(13)
    
if __name__ == "__main__":
    pass