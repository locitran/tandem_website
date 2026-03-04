import gradio as gr
from zoneinfo import ZoneInfo

from .settings import TAIPEI_TIME_ZONE

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
