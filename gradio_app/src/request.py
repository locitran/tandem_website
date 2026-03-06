import gradio as gr
from zoneinfo import ZoneInfo

from .settings import TAIPEI_TIME_ZONE, MOUNT_POINT
from .logger import LOGGER

def build_session_url(session_id):
    url = f"/{MOUNT_POINT}/session/?session_id={session_id}"
    LOGGER.info(url)
    return f"/{MOUNT_POINT}/session/?session_id={session_id}"

def build_job_url(session_id, job_name):
    return f"/{MOUNT_POINT}/results/?session_id={session_id}&job_name={job_name}"

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