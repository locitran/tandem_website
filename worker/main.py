import requests
import time
import copy
import os 
import json
import shutil
import traceback

from logger import LOGGER
from datetime import datetime 
from zoneinfo import ZoneInfo
from pymongo import MongoClient

TANDEM_WEBSITE_ROOT = os.path.dirname(os.path.dirname(__file__)) # ./tandem_website
jobs_folder = os.path.join(TANDEM_WEBSITE_ROOT, 'tandem/jobs')

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

LOGGER.info(f"✅ Connected. Collections: {db.list_collection_names()}")

time_zone = ZoneInfo("Asia/Taipei")
JOB_RETENTION_DAYS = 60


def cleanup_expired_jobs():
    now_ts = time.time()
    expired_jobs = list(
        collections.find(
            {
                "session_id": {"$ne": "test"},
                "job_name": {"$exists": True},
                "delete_after_ts": {"$lte": now_ts},
                "status": {"$in": ["pending", "finished"]},
            },
            {"_id": 1, "session_id": 1, "job_name": 1},
        )
    )

    for job in expired_jobs:
        session_id = job.get("session_id")
        job_name = job.get("job_name")
        if session_id and job_name:
            job_dir = os.path.join(jobs_folder, session_id, job_name)
            if os.path.exists(job_dir):
                shutil.rmtree(job_dir, ignore_errors=True)
        collections.delete_one({"_id": job["_id"]})
        LOGGER.info(f"🧹 Removed expired job {session_id}/{job_name} after {JOB_RETENTION_DAYS} days")

while True:
    cleanup_expired_jobs()
    job_start = time.time()
    job_start_str = datetime.now(time_zone).strftime("%Y-%m-%d_%H-%M-%S")
    # 🔑 Atomically pick job AND set job_start
    task = collections.find_one_and_update(
        {"status": "pending"},
        {
            "$set": {
                "status": "processing", "job_start": job_start, "job_start_str": job_start_str
            }
        },
       sort=[("_id", 1)],
        return_document=False  # return OLD document (before update)
    )

    if task:
        session_id = task.get("session_id")
        job_name = task.get("job_name")
        LOGGER.info(f"🚀 Picked job {session_id}/{job_name} at {job_start_str}")
        try:
             # Remove _id field (or deep copy + pop)
            task_to_send = copy.deepcopy(task)
            task_to_send.pop("_id", None)
            
            response = requests.post("http://tandem:5000/run_tandem_job", json=task_to_send)
            # LOGGER.info(f'response {response}')
            # @> <Response [200]> if ok

            # ✅ Mark finished + record job_end
            job_end = time.time()
            job_end_str = datetime.now(time_zone).strftime("%Y-%m-%d_%H-%M-%S")
            collections.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {"status": "finished", "job_end": job_end, "job_end_str": job_end_str}
                }
            )
            updated_task = collections.find_one(
                {"_id": task["_id"]},
                {"_id": 0}  # remove MongoDB ObjectId (JSON cannot serialize it)
            )
            with open(f"{jobs_folder}/{session_id}/{job_name}/params.json", "w") as f:
                json.dump(updated_task, f, indent=4)
            LOGGER.info(f"✅ Finished job {session_id}/{job_name}")

        except Exception as e:
            msg = traceback.format_exc()
            LOGGER.error(msg)
            # Roll back so it can be retried
            collections.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {"status": "pending"},
                    "$unset": {"job_start": ""}
                }
            )
    else:
        LOGGER.debug("No pending tasks found.")
        time.sleep(2)
