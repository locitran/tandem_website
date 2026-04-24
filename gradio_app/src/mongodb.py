from copy import deepcopy

from pymongo import MongoClient

MONGODB_URI = "mongodb://mongodb:27017/"
DATABASE_NAME = "app_db"
COLLECTION_NAME = "input_queue"

client = MongoClient(MONGODB_URI)
db = client[DATABASE_NAME]
collections = db[COLLECTION_NAME]


def get_collection():
    """Return the MongoDB collection used by the Gradio app.

    Output:
    - pymongo collection object for `app_db.input_queue`.
    """
    return collections


def _clean_record(record):
    """Return a copy of a MongoDB record without the internal `_id` field.

    Input:
    - record: MongoDB document dict or None.

    Output:
    - Cleaned dict without `_id`, or None if record is missing.
    """
    if record is None:
        return None
    record_udt = deepcopy(record)
    record_udt.pop("_id", None)
    return record_udt


def find_record(session_id, job_name, projection=None):
    """Find one unique job record by `session_id` and `job_name`.

    Inputs:
    - session_id: session identifier string.
    - job_name: job name string.
    - projection: optional MongoDB projection dict.

    Output:
    - Cleaned record dict, or None if no match is found.
    """
    query = {"session_id": session_id, "job_name": job_name}
    record = collections.find_one(query, projection)
    return _clean_record(record)


def find_created_record(session_id, projection=None):
    """Find the special session-level `created` record.

    Inputs:
    - session_id: session identifier string.
    - projection: optional MongoDB projection dict.

    Output:
    - Cleaned created-record dict, or None if it does not exist.
    """
    query = {"session_id": session_id, "status": "created"}
    record = collections.find_one(query, projection)
    return _clean_record(record)


def find_records_by_session(session_id, projection=None, sort_by=None):
    """Find all records that belong to one session.

    Inputs:
    - session_id: session identifier string.
    - projection: optional MongoDB projection dict.
    - sort_by: optional list of `(field, direction)` tuples for sorting.

    Output:
    - List of cleaned record dicts.
    """
    cursor = collections.find({"session_id": session_id}, projection)
    if sort_by:
        cursor = cursor.sort(sort_by)
    return [_clean_record(record) for record in cursor]


def find_records(query, projection=None, sort_by=None, limit=None):
    """Run a general record search against the input queue collection.

    Inputs:
    - query: MongoDB query dict.
    - projection: optional MongoDB projection dict.
    - sort_by: optional list of `(field, direction)` tuples for sorting.
    - limit: optional integer to limit returned records.

    Output:
    - List of cleaned record dicts.
    """
    cursor = collections.find(query, projection)
    if sort_by:
        cursor = cursor.sort(sort_by)
    if limit is not None:
        cursor = cursor.limit(limit)
    return [_clean_record(record) for record in cursor]


def list_session_ids(query=None):
    """List distinct session ids.

    Input:
    - query: optional MongoDB filter dict.

    Output:
    - Sorted list of distinct session ids.
    """
    values = collections.distinct("session_id", query or {})
    return sorted(value for value in values if value)


def list_session_job_names(session_id, statuses=None):
    """List distinct job names for one session.

    Inputs:
    - session_id: session identifier string.
    - statuses: optional list of status strings to filter jobs.

    Output:
    - Sorted list of distinct job names.
    """
    query = {"session_id": session_id}
    if statuses:
        query["status"] = {"$in": list(statuses)}
    values = collections.distinct("job_name", query)
    return sorted(value for value in values if value)


def list_finished_training_models(session_id):
    """List finished training-model job names that can be reused as models.

    Input:
    - session_id: session identifier string.

    Output:
    - Sorted list of finished training/transfer-learning job names.
    """
    query = {
        "session_id": session_id,
        "status": "finished",
        "mode": {"$in": ["Training", "Transfer Learning"]},
    }
    values = collections.distinct("job_name", query)
    return sorted(value for value in values if value)


def insert_record(record):
    """Insert one record into MongoDB.

    Input:
    - record: dict to insert.

    Output:
    - The inserted MongoDB object id.
    """
    result = collections.insert_one(deepcopy(record))
    return result.inserted_id


def upsert_record(query, values, set_on_insert=None):
    """Upsert a record using `$set` and optional `$setOnInsert`.

    Inputs:
    - query: MongoDB query dict.
    - values: dict assigned through `$set`.
    - set_on_insert: optional dict assigned through `$setOnInsert`.

    Output:
    - pymongo update result object.
    """
    update_doc = {"$set": deepcopy(values or {})}
    if set_on_insert:
        update_doc["$setOnInsert"] = deepcopy(set_on_insert)
    return collections.update_one(query, update_doc, upsert=True)


def upsert_session_created_record(session_id, values=None):
    """Ensure a session has its `created` placeholder record.

    Inputs:
    - session_id: session identifier string.
    - values: optional extra fields to set on the created record.

    Output:
    - pymongo update result object.
    """
    values_udt = {"session_id": session_id, "status": "created"}
    if values:
        values_udt.update(deepcopy(values))
    return collections.update_one(
        {"session_id": session_id, "status": "created"},
        {"$set": values_udt},
        upsert=True,
    )


def upsert_job_record(record):
    """Upsert one job record by `session_id` and `job_name`.

    Input:
    - record: job metadata dict containing `session_id` and `job_name`.

    Output:
    - pymongo update result object.
    """
    session_id = record.get("session_id")
    job_name = record.get("job_name")
    if not session_id or not job_name:
        raise ValueError("record must contain both 'session_id' and 'job_name'")

    record_udt = deepcopy(record)
    record_udt.pop("_id", None)
    query = {"session_id": session_id, "job_name": job_name}
    return collections.update_one(query, {"$set": record_udt}, upsert=True)


def update_record(session_id, job_name, values):
    """Update one job record by `session_id` and `job_name`.

    Inputs:
    - session_id: session identifier string.
    - job_name: job name string.
    - values: dict of fields to update.

    Output:
    - pymongo update result object.
    """
    query = {"session_id": session_id, "job_name": job_name}
    return collections.update_one(query, {"$set": deepcopy(values or {})})


def update_records(query, values):
    """Update multiple records matching a MongoDB query.

    Inputs:
    - query: MongoDB query dict.
    - values: dict of fields to update.

    Output:
    - pymongo update-many result object.
    """
    return collections.update_many(query, {"$set": deepcopy(values or {})})


def remove_record(session_id, job_name):
    """Remove one job record by `session_id` and `job_name`.

    Inputs:
    - session_id: session identifier string.
    - job_name: job name string.

    Output:
    - pymongo delete result object.
    """
    query = {"session_id": session_id, "job_name": job_name}
    return collections.delete_one(query)


def remove_records_by_session(session_id):
    """Remove all records for one session.

    Input:
    - session_id: session identifier string.

    Output:
    - pymongo delete-many result object.
    """
    return collections.delete_many({"session_id": session_id})


def remove_records(query):
    """Remove multiple records that match a MongoDB query.

    Input:
    - query: MongoDB query dict.

    Output:
    - pymongo delete-many result object.
    """
    return collections.delete_many(query)


def count_records(query=None):
    """Count records matching a query.

    Input:
    - query: optional MongoDB query dict.

    Output:
    - Integer count.
    """
    return collections.count_documents(query or {})
