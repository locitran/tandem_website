import argparse
import json
import os
import sys
from pathlib import Path
from pymongo import MongoClient

SCRIPT_DIR = Path(__file__).resolve().parent
GRADIO_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = GRADIO_ROOT.parent
sys.path.insert(0, str(GRADIO_ROOT))

from src.logger import LOGGER

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017/")
DB_NAME = os.environ.get("MONGO_DB", "app_db")
COLLECTION_NAME = os.environ.get("MONGO_COLLECTION", "input_queue")
JOBS_DIR = Path(os.environ.get("JOBS_DIR", str(PROJECT_ROOT / "tandem" / "jobs")))

def import_session_jobs(session_id: str) -> None:
    session_dir = JOBS_DIR / session_id
    if not session_dir.is_dir():
        raise FileNotFoundError(f"Session folder not found: {session_dir}")

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collections = db[COLLECTION_NAME]

    LOGGER.info(f"Importing jobs from {session_dir} into {DB_NAME}.{COLLECTION_NAME}")

    imported = 0
    skipped = 0
    for job_dir in sorted(session_dir.iterdir()):
        if not job_dir.is_dir():
            continue

        params_path = job_dir / "params.json"
        if not params_path.is_file():
            skipped += 1
            LOGGER.warning(f"Skipping {job_dir.name}: missing params.json")
            continue

        with params_path.open() as f:
            data = json.load(f)

        data.pop("_id", None)
        data["session_id"] = session_id
        data["job_name"] = job_dir.name
        data["session_url"] = f"/TANDEM-dev/session/?session_id={session_id}"
        data["job_url"] = f"/TANDEM-dev/results/?session_id={session_id}&job_name={job_dir.name}"

        collections.update_one({"session_id": session_id, "job_name": job_dir.name}, {"$set": data}, upsert=True,)
        imported += 1
        LOGGER.info(f"Upserted {session_id}/{job_dir.name}")
    LOGGER.info(f"Done. Imported={imported}, skipped={skipped}")


def main():
    description="Import all params.json files from one tandem jobs session folder into MongoDB."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--session-id", default="test", help="Session folder name under tandem/jobs. Default: test",)
    args = parser.parse_args()
    import_session_jobs(args.session_id)

if __name__ == "__main__":
    main()
    # docker exec -it gradio_app python /gradio_app/scripts/import_jobs2db.py --session-id test
    # docker exec -it gradio_app_dev python /gradio_app/scripts/import_jobs2db.py --session-id test

