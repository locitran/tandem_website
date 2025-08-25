from pymongo import MongoClient
import requests
import time
import copy
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
input_col = db["input_queue"]

logging.info(f"✅ Connected. Collections: {db.list_collection_names()}")

while True:
    task = input_col.find_one_and_update(
        {"status": "pending"},
        {"$set": {"status": "processing"}},
        sort=[("_id", 1)]
    )

    if task:
        logging.info(f"✅ Found task: {task}")
    else:
        logging.debug("No pending tasks found.")

    if task:
        try:
            logging.info(f"Processing session: {task['session_id']}")

             # Remove _id field (or deep copy + pop)
            task_to_send = copy.deepcopy(task)
            task_to_send.pop("_id", None)

            response = requests.post("http://inference:5000/infer", json=task_to_send)
            logging.info(response)

            output = response.json().get("output", "❌ No output returned")

            input_col.update_one(
                {"_id": task["_id"]},
                {"$set": {"status": "finished", "result": output}}
            )

        except Exception as e:
            logging.error(f"⚠️ Error processing task: {e}")
            input_col.update_one(
                {"_id": task["_id"]},
                {"$set": {"status": "pending"}}
            )
    else:
        time.sleep(2)
