import argparse
import json
import os
import sys

from pymongo import MongoClient

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GRADIO_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(GRADIO_ROOT)
sys.path.insert(0, GRADIO_ROOT)

from src.logger import LOGGER
from src.settings import JOB_DIR, MOUNT_POINT

DEFAULT_JOBS_DIR = os.environ.get("JOBS_DIR", JOB_DIR)

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]


def _load_params(params_path):
    """Read one params.json file and return a dict or None."""
    try:
        with open(params_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        LOGGER.warning(f"Skipping {params_path}: failed to read params.json ({exc})")
        return None

    if not isinstance(data, dict):
        LOGGER.warning(f"Skipping {params_path}: params.json is not a JSON object")
        return None
    return data


def _infer_session_job(params_path, jobs_dir, data):
    """Infer session_id and job_name from params.json or folder structure."""
    session_id = str(data.get("session_id", "") or "").strip()
    job_name = str(data.get("job_name", "") or "").strip()

    rel_dir = os.path.relpath(os.path.dirname(params_path), jobs_dir)
    parts = [] if rel_dir == "." else rel_dir.split(os.sep)

    if not session_id or not job_name:
        if len(parts) == 2:
            session_id = session_id or parts[0]
            job_name = job_name or parts[1]
        elif len(parts) > 2:
            session_id = session_id or parts[0]
            job_name = job_name or parts[1]
        elif len(parts) == 1:
            session_id = session_id or parts[0]
            job_name = job_name or parts[0]

    session_id = session_id.strip()
    job_name = job_name.strip()
    if not session_id or not job_name:
        return "", ""
    return session_id, job_name


def _build_urls(session_id, job_name):
    """Build session and results URLs for one imported job."""
    session_url = f"/{MOUNT_POINT}/session/?session_id={session_id}"
    job_url = f"/{MOUNT_POINT}/results/?session_id={session_id}&job_name={job_name}"
    return session_url, job_url


def import_old_jobs(jobs_dir=DEFAULT_JOBS_DIR, session_id=None):
    """Scan tandem/jobs recursively and upsert every job with params.json."""
    jobs_dir = os.path.abspath(jobs_dir)
    if not os.path.isdir(jobs_dir):
        raise FileNotFoundError(f"Jobs folder not found: {jobs_dir}")

    scan_root = jobs_dir
    if session_id:
        scan_root = os.path.join(jobs_dir, session_id)
        if not os.path.isdir(scan_root):
            raise FileNotFoundError(f"Session folder not found: {scan_root}")

    LOGGER.info(f"Importing old jobs from {scan_root} into mongodb")

    imported = 0
    skipped = 0
    failed = 0

    for dirpath, dirnames, filenames in os.walk(scan_root):
        if "params.json" not in filenames:
            continue

        params_path = os.path.join(dirpath, "params.json")
        data = _load_params(params_path)
        if data is None:
            failed += 1
            continue

        session_id_udt, job_name_udt = _infer_session_job(params_path, jobs_dir, data)
        if not session_id_udt or not job_name_udt:
            skipped += 1
            LOGGER.warning(f"Skipping {params_path}: cannot infer session_id/job_name")
            continue

        if session_id and session_id_udt != session_id:
            skipped += 1
            LOGGER.info(
                f"Skipping {params_path}: params session_id={session_id_udt} does not match requested session_id={session_id}"
            )
            continue

        session_url, job_url = _build_urls(session_id_udt, job_name_udt)

        data.pop("_id", None)
        data["session_id"] = session_id_udt
        data["job_name"] = job_name_udt
        data["session_url"] = session_url
        data["job_url"] = job_url

        try:
            collections.update_one(
                {"session_id": session_id_udt, "job_name": job_name_udt},
                {"$set": data},
                upsert=True,
            )
        except Exception as exc:
            failed += 1
            LOGGER.warning(f"Failed to upsert {session_id_udt}/{job_name_udt}: {exc}")
            continue

        imported += 1
        LOGGER.info(f"Upserted {session_id_udt}/{job_name_udt}")

    LOGGER.info(f"Done. Imported={imported}, skipped={skipped}, failed={failed}")


def main():
    description = "Import all old tandem jobs with params.json into MongoDB."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--jobs-dir",
        default=DEFAULT_JOBS_DIR,
        help=f"Jobs root folder. Default: {DEFAULT_JOBS_DIR}",
    )
    parser.add_argument(
        "--session-id",
        default="",
        help="Optional session folder name under tandem/jobs. If omitted, import all sessions.",
    )
    args = parser.parse_args()
    import_old_jobs(jobs_dir=args.jobs_dir, session_id=args.session_id or None)


if __name__ == "__main__":
    main()
    # Import all jobs:
    # docker exec -it gradio_app_dev python /gradio_app/scripts/importOLDjobs.py
    # Import one session only:
    # docker exec -it gradio_app_dev python /gradio_app/scripts/importOLDjobs.py --session-id test
