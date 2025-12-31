import pandas as pd 
import shutil
import gradio as gr
import math
import os 
from .logger import LOGGER
from yattag import Doc

def safe(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "-"
    return v

def fmt_prob(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "-"
    return f"{float(v):.3f}"

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

def render_output(_param_state, folder):
    ""
    _job_status = _param_state.get('status', None)
    output_section_udt = gr.update(visible=False)
    pred_table_udt = gr.update(visible=False)
    result_zip_udt = gr.update(visible=False)
    image_selector_udt = gr.update(visible=False)
    image_viewer_udt = gr.update(visible=False)

    if _job_status != "finished":
        return output_section_udt, pred_table_udt, result_zip_udt, image_selector_udt, image_viewer_udt

    output_section_udt = gr.update(visible=True)
    session_id = _param_state["session_id"]
    job_name   = _param_state["job_name"]
    job_folder = os.path.join(folder, session_id, job_name) 
    pred_file = os.path.join(job_folder, "predictions.csv")
    df_pred   = pd.read_csv(pred_file)
    pred_table_udt = gr.update(value=multindex_DataFrame(df_pred), visible=True)
    
    zip_path = zip_folder(job_folder)
    result_zip_udt = gr.update(value=zip_path, interactive=True, visible=bool(zip_path))

    tandem_shap = os.path.join(job_folder, 'tandem_shap') 
    list_images = os.listdir(tandem_shap)

    image_selector_udt = gr.update(
        choices=list_images,
        value=list_images[0] if list_images else None,
        visible=bool(list_images),
    )

    image_viewer_udt = gr.update(
        value=os.path.join(tandem_shap, list_images[0]) if list_images else None,
        visible=bool(list_images),
    )

    return output_section_udt, pred_table_udt, result_zip_udt, image_selector_udt, image_viewer_udt

if __name__ == "__main__":
    pass