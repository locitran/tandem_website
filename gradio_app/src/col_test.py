from pymongo import MongoClient

client = MongoClient()
db = client["job_db"]
collections = db["input_queue"]

# Session A has 3 jobs
job_001 = {
    "status": "finished",
    "session_id": "loci",
    "mode": "Inferencing",
    "inf_sav_txt": "P29033 Y217D",
    "inf_sav_btn": "Uploadasdasdasdasdasdasdasd",
    "inf_model_select": "TANDEM",
    "tf_sav_txt": "",
    "tf_sav_btn": "Upload",
    "str_txt": "",
    "str_btn": "Upload",
    "job_name": "Tue_Dec_9_13-28-04_2025",
    "email": ""
}

job_002 = {
    "status": "finished",
    "session_id": "loci",
    "mode": "Inferencing",
    "inf_sav_txt": "P29033 Y217D",
    "inf_sav_btn": "Upload",
    "inf_model_select": "TANDEM",
    "tf_sav_txt": "",
    "tf_sav_btn": "Upload",
    "str_txt": "",
    "str_btn": "Upload",
    "job_name": "Tue_Dec_9_13-55-29_2025",
    "email": ""
}

job_003 = {
    "status": "finished",
    "session_id": "sr96mwH7UK",
    "mode": "Inferencing",
    "inf_sav_txt": "P29033 Y217D",
    "inf_sav_btn": "Upload",
    "inf_model_select": "TANDEM",
    "tf_sav_txt": "",
    "tf_sav_btn": "Upload",
    "str_txt": "",
    "str_btn": "Upload",
    "job_name": "2025-12-15_14-58-07",
    "email": ""
}

job_004 = {
    "status": "finished",
    "session_id": "sr96mwH7UK",
    "mode": "Transfer learning",
    "inf_sav_txt": "P29033 Y217D",
    "inf_sav_btn": "Upload",
    "inf_model_select": "TANDEM",
    "tf_sav_txt": "",
    "tf_sav_btn": "Upload",
    "str_txt": "",
    "str_btn": "Upload",
    "job_name": "2025-12-15_14-58-07",
    "email": ""
}

# Session B has 2 jobs
job_101 = {
    "status": "finished",
    "session_id": "4FdmMHWI8z",
    "mode": "Inferencing",
    "inf_sav_txt": "P29033 Y217D",
    "inf_sav_btn": "Upload",
    "inf_model_select": "TANDEM",
    "tf_sav_txt": "",
    "tf_sav_btn": "Upload",
    "str_txt": "",
    "str_btn": "Upload",
    "job_name": "2025-12-15_15-03-01",
    "email": ""
}

job_102 = {
    "status": "finished",
    "session_id": "lq0xnALopo",
    "mode": "Inferencing",
    "inf_sav_txt": "P29033 Y217D",
    "inf_sav_btn": "Upload",
    "inf_model_select": "TANDEM",
    "tf_sav_txt": "",
    "tf_sav_btn": "Upload",
    "str_txt": "",
    "str_btn": "Upload",
    "job_name": "2025-12-15_14-52-21",
    "email": ""
}

collections.insert_one(job_001)
collections.insert_one(job_002)
collections.insert_one(job_003)
collections.insert_one(job_004)
collections.insert_one(job_101)
collections.insert_one(job_102)

# Drop all jobs of db
# db.drop_collection("input_queue")

# List all records
# docs = list(collections.find())

# Delete a specific job
# collections.delete_one(
#     {
#         "session_id": session_id,
#         "job_name": job_name
#     }
# )

# Delete all records of one session:
# collections.delete_many({"session_id": "loci"})