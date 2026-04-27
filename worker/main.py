import concurrent.futures
import copy
import json
import os
import time
import traceback
from datetime import datetime
from urllib.parse import urlparse, urlunparse
from zoneinfo import ZoneInfo

import requests
from pymongo import MongoClient, ReturnDocument

from logger import LOGGER


TANDEM_WEBSITE_ROOT = os.path.dirname(os.path.dirname(__file__))  # ./tandem_website
jobs_folder = os.path.join(TANDEM_WEBSITE_ROOT, "tandem/jobs")

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

time_zone = ZoneInfo("Asia/Taipei")
POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "2"))
WORKER_ID = os.environ.get("HOSTNAME", "worker")

DEFAULT_TANDEM_URL = "http://tandem:5000/run_tandem_job"
TANDEM_URLS = [
    url.strip()
    for url in os.environ.get("TANDEM_URLS", DEFAULT_TANDEM_URL).split(",")
    if url.strip()
]
if not TANDEM_URLS:
    TANDEM_URLS = [DEFAULT_TANDEM_URL]


def available_url(tandem_url):
    parsed = urlparse(tandem_url)
    return urlunparse(parsed._replace(path="/available", params="", query="", fragment=""))


def container_is_available(tandem_url, inflight):
    if tandem_url in inflight:
        return False

    try:
        response = requests.get(available_url(tandem_url), timeout=5)
        return response.status_code == 200
    except requests.RequestException as exc:
        LOGGER.warning(f"Tandem container unavailable at {tandem_url}: {exc}")
        return False


def claim_pending_job(tandem_url):
    job_start = time.time()
    job_start_str = datetime.now(time_zone).strftime("%Y-%m-%d_%H-%M-%S")
    return collections.find_one_and_update(
        {"status": "pending"},
        {
            "$set": {
                "status": "processing",
                "job_start": job_start,
                "job_start_str": job_start_str,
                "worker_id": WORKER_ID,
                "tandem_url": tandem_url,
            }
        },
        sort=[("_id", 1)],
        return_document=ReturnDocument.BEFORE,
    )


def dispatch_job(task, tandem_url):
    task_to_send = copy.deepcopy(task)
    task_to_send.pop("_id", None)
    response = requests.post(tandem_url, json=task_to_send)
    response.raise_for_status()
    return response.json()


def mark_finished(task):
    session_id = task.get("session_id")
    job_name = task.get("job_name")
    job_end = time.time()
    job_end_str = datetime.now(time_zone).strftime("%Y-%m-%d_%H-%M-%S")

    collections.update_one(
        {"_id": task["_id"]},
        {"$set": {"status": "finished", "job_end": job_end, "job_end_str": job_end_str}},
    )

    updated_task = collections.find_one({"_id": task["_id"]}, {"_id": 0})
    params_path = os.path.join(jobs_folder, session_id, job_name, "params.json")
    with open(params_path, "w") as f:
        json.dump(updated_task, f, indent=4)

    LOGGER.info(f"✅ Finished job {session_id}/{job_name}")


def return_to_pending(task):
    collections.update_one(
        {"_id": task["_id"]},
        {
            "$set": {"status": "pending"},
            "$unset": {
                "job_start": "",
                "job_start_str": "",
                "job_end": "",
                "job_end_str": "",
                "worker_id": "",
                "tandem_url": "",
            },
        },
    )


def handle_done_slot(tandem_url, slot):
    task = slot["task"]
    session_id = task.get("session_id")
    job_name = task.get("job_name")

    try:
        slot["future"].result()
        mark_finished(task)
    except Exception:
        LOGGER.warning(traceback.format_exc())
        LOGGER.warning(f"Job failed, returning to pending: {session_id}/{job_name}")
        return_to_pending(task)
    finally:
        LOGGER.info(f"Released Tandem container: {tandem_url}")


def fill_free_slots(executor, inflight):
    for tandem_url in TANDEM_URLS:
        if not container_is_available(tandem_url, inflight):
            continue

        task = claim_pending_job(tandem_url)
        if not task:
            continue

        session_id = task.get("session_id")
        job_name = task.get("job_name")
        LOGGER.info(f"🚀 Dispatching job {session_id}/{job_name} to {tandem_url}")

        inflight[tandem_url] = {
            "task": task,
            "future": executor.submit(dispatch_job, task, tandem_url),
        }


def main():
    LOGGER.info(f"Worker started with Tandem containers: {TANDEM_URLS}")

    inflight = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(TANDEM_URLS)) as executor:
        while True:
            for tandem_url, slot in list(inflight.items()):
                if slot["future"].done():
                    inflight.pop(tandem_url)
                    handle_done_slot(tandem_url, slot)

            fill_free_slots(executor, inflight)

            if not inflight:
                LOGGER.debug("No running jobs.")

            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
