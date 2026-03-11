import os
import gradio as gr
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from pymongo import MongoClient

from .settings import TAIPEI_TIME_ZONE, MOUNT_POINT, JOB_DIR
from .logger import LOGGER

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]

def build_session_url(session_id):
    return f"/{MOUNT_POINT}/session/?session_id={session_id}"

def build_job_url(session_id, job_name):
    return f"/{MOUNT_POINT}/results/?session_id={session_id}&job_name={job_name}"

def build_error_url(kind, session_id="", job_name=""):
    params = {"kind": kind}
    if session_id:
        params["session_id"] = session_id
    if job_name:
        params["job_name"] = job_name
    return f"/{MOUNT_POINT}/error/?{urlencode(params)}"

def session_exists(session_id):
    """Check https://{root_path}/session/?session_id={session_id} is valid
    """
    if not session_id:
        return build_error_url("missing_session")
    exists = collections.count_documents({"session_id": session_id}) > 0
    if exists:
        return ""
    return build_error_url("session_not_found", session_id=session_id)

def job_exists(session_id, job_name):
    """Check https://{root_path}/results/?session_id={session_id}&job_name={job_name} is valid
    """
    if not session_id:
        return build_error_url("missing_session")
    
    if not job_name:
        return build_error_url("missing_job", session_id=session_id)
    
    error_url = session_exists(session_id)
    if error_url:
        return error_url
    
    exists = collections.count_documents({"session_id": session_id, "job_name": job_name}) > 0
    if exists:
        return ""
    return build_error_url("job_not_found", session_id=session_id, job_name=job_name,)

def request2info(request: gr.Request):
    # Timezone and timestamp from request (with fallback to server timezone)
    ip = request.client.host if request.client else None
    forwarded = request.headers.get("x-forwarded-for") if request.headers else None
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    
    tz_header = (
        request.headers.get("x-timezone")
        or request.headers.get("cf-timezone")
        or request.headers.get("x-client-timezone")
    )
    time_zone = ZoneInfo(tz_header.strip()) if tz_header else TAIPEI_TIME_ZONE

    return ip, time_zone

def request2session_id(request: gr.Request):
    return request.query_params.get("session_id", "").strip()

def request2session_and_job(request: gr.Request):
    session_id = (request.query_params.get("session_id", "") or "").strip()
    job_name = (request.query_params.get("job_name", "") or "").strip()
    return session_id, job_name

def passthrough_url(url):
    return url
