import html
import os

from pymongo import MongoClient

from .popup import build_event_popup
from ..settings import JOB_DIR, HTML_DIR, MOUNT_POINT
from ..mongodb import count_records
from .. logger import LOGGER

PROCESS_STATUS_TEMPLATE = os.path.join(HTML_DIR, "results_process_status.html")

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

STAGE_LABELS = [
    "Validating SAVs",
    "Mapping SAVs to structures",
    "Feature calculation",
    "Model inferencing/Training",
    "Summary",
]

def build_process_status_html(param, userlog, session_id, job_name, job_status):
    """Build the staged process-status table HTML."""
    events = userlog.get("events", []) if isinstance(userlog, dict) else []
    job_folder = os.path.join(JOB_DIR, session_id, job_name) if session_id and job_name else ""

    stage_cells, popup_html = _build_stage_cells(events, job_folder, job_status)
    stage_labels = _build_stage_labels(events)
    with open(PROCESS_STATUS_TEMPLATE, "r", encoding="utf-8") as handle:
        template_text = handle.read()
    # variable dictionary contains all variables that fill up template
    var_dict = {
        "submission_time": (param or {}).get("submission_time", "-"),
        "estimated_time": "-",
        "pending_count": count_records({"status": "pending"}),
        "running_count": count_records({"status": "processing"}),
    }
    var_dict.update(stage_cells)
    var_dict.update(stage_labels)
    return template_text.format(**var_dict) + popup_html
     
def file2link(filepath):
    if not os.path.exists(filepath):
        LOGGER.warn(f"{filepath} does not exist")

    filename = os.path.splitext(os.path.basename(filepath))[0]
    href = f"/{MOUNT_POINT}/results/gradio_api/file={filepath}"
    safe_href = html.escape(href, quote=True)
    safe_label = html.escape(filename)
    return f'<a href="{safe_href}" target="_blank" rel="noopener"><font size="-1">{safe_label}</font></a>'

def _build_stage_cells(events, job_folder, job_status):
    results = {}
    previous_stage_done = False
    previous_stage_failed = False
    popup_html_parts = []

    for i, label in enumerate(STAGE_LABELS):
        main_event = next((event for event in reversed(events) if event.get("stage") == label and event.get("level") == "info"),None)
        warning_events = [event for event in events if event.get("stage") == label and event.get("level") == "warning"]
        error_events = [event for event in events if event.get("stage") == label and event.get("level") == "error"]
        n_warning = len(warning_events)
        n_error = len(error_events)

        if previous_stage_failed:
            status = "Failed"
            results[f"file_{i}"] = ""
            results[f"time_{i}"] = ""
        elif main_event is None:
            # If pending job, status: "Pend"
            # IF processing job, status depends previous event. 
            # If previous event is Done, status is "Process", else "Pend"
            if job_status == "processing":
                status = "Process" if previous_stage_done else "Pend"
                if status == "Process":
                    previous_stage_done = False
            else:
                status = "Pend"
            results[f"file_{i}"] = ""
            results[f"time_{i}"] = ""
        else:
            status = "Done"
            previous_stage_done = True
            context = main_event.get("context", {})
            file_value = context.get("file")
            filepath = os.path.join(job_folder, file_value) if file_value else ""
            results[f"file_{i}"] = file2link(filepath) if filepath else ""
            results[f"time_{i}"] = context.get("duration_text")

        if n_error:
            status = "Failed"
            previous_stage_failed = True

        status_parts = [html.escape(status)]
        popup_parts = []
        if n_warning or n_error:
            if n_warning:
                w = "Warning" if n_warning == 1 else "Warnings"
                popup_parts.append(f"{n_warning} {w}")
            if n_error:
                e = "Error" if n_error == 1 else "Errors"
                popup_parts.append(f"{n_error} {e}")

            popup_trigger, popup_modal = build_event_popup(
                modal_id=f"popup-stage-{i}",
                trigger_text=" ".join(popup_parts),
                title="{}: {}".format(label, " ".join(popup_parts)),
                event_groups=[
                    {"level": "WARNING", "events": warning_events},
                    {"level": "ERROR", "events": error_events},
                ],
            )
            popup_html_parts.append(popup_modal)
            popup_parts = [popup_trigger]

        if popup_parts:
            status_parts.append("({})".format(" ".join(popup_parts)))

        results[f"status_{i}"] = "<span>{}</span>".format(" ".join(status_parts))
    return results, "".join(popup_html_parts)


def _build_stage_labels(events):
    r = {}
    for i, label in enumerate(STAGE_LABELS):
        mapping_event = next((event for event in reversed(events) if event.get("stage") == label and event.get("level") == "important"), None)
        msg = mapping_event.get("message", {}) if mapping_event else label
        r[f"stage_{i}_label"] = msg
    return r
