import gradio as gr
import ipaddress
from functools import lru_cache
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from pymongo import MongoClient
import requests

from .settings import TAIPEI_TIME_ZONE, MOUNT_POINT
from .logger import LOGGER

client = MongoClient("mongodb://mongodb:27017/")
db = client["app_db"]
collections = db["input_queue"]
IPWHOIS_URL = "https://ipwho.is/{ip}"

def build_session_url(session_id, example_name="", example_action=""):
    params = {"session_id": session_id}
    if example_name:
        params["example_name"] = example_name
    if example_action:
        params["example_action"] = example_action
    return f"/{MOUNT_POINT}/session/?{urlencode(params)}"

def build_job_url(session_id, job_name, example_name="", example_action=""):
    params = {"session_id": session_id}
    if job_name:
        params["job_name"] = job_name
    if example_name:
        params["example_name"] = example_name
    if example_action:
        params["example_action"] = example_action
    return f"/{MOUNT_POINT}/results/?{urlencode(params)}"

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

def _header_geo_info(request: gr.Request):
    geo_info = {
        "city": (
            request.headers.get("cf-ipcity")
            or request.headers.get("x-vercel-ip-city")
            or request.headers.get("x-city")
        ),
        "region": (
            request.headers.get("cf-region")
            or request.headers.get("x-vercel-ip-country-region")
            or request.headers.get("x-region")
        ),
        "country": (
            request.headers.get("cf-ipcountry")
            or request.headers.get("x-vercel-ip-country")
            or request.headers.get("x-country")
            or request.headers.get("x-country-code")
        ),
        "continent": request.headers.get("cf-ipcontinent"),
    }
    return {k: v for k, v in geo_info.items() if v}

def _is_public_ip(ip: str | None) -> bool:
    if not ip:
        return False
    try:
        parsed = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_reserved
        or parsed.is_multicast
        or parsed.is_unspecified
        or parsed.is_link_local
    )

@lru_cache(maxsize=2048)
def _lookup_geo_info(ip: str):
    if not _is_public_ip(ip):
        return {}
    try:
        response = requests.get(IPWHOIS_URL.format(ip=ip), timeout=3)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        LOGGER.info(f"GeoIP lookup failed for {ip}: {exc}")
        return {}
    except ValueError:
        LOGGER.info(f"GeoIP lookup returned invalid JSON for {ip}")
        return {}

    if not payload.get("success", False):
        return {}

    geo_info = {
        "city": payload.get("city", "") or "",
        "region": payload.get("region", "") or "",
        "country": payload.get("country_code", "") or payload.get("country", "") or "",
        "continent": payload.get("continent_code", "") or payload.get("continent", "") or "",
    }
    return {k: v for k, v in geo_info.items() if v}

def request2info(request: gr.Request):
    # Timezone and location hints from request headers (with fallback to server timezone)
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
    geo_info = _header_geo_info(request)
    if not geo_info:
        geo_info = _lookup_geo_info(ip)
    return ip, time_zone, geo_info

def request2session_id(request: gr.Request):
    return request.query_params.get("session_id", "").strip()

def request2session_payload(request: gr.Request):
    session_id = (request.query_params.get("session_id", "") or "").strip()
    example_name = (request.query_params.get("example_name", "") or "").strip()
    example_action = (request.query_params.get("example_action", "") or "").strip()
    return session_id, example_name, example_action

def request2session_and_job(request: gr.Request):
    session_id = (request.query_params.get("session_id", "") or "").strip()
    job_name = (request.query_params.get("job_name", "") or "").strip()
    return session_id, job_name

def request2result_payload(request: gr.Request):
    session_id = (request.query_params.get("session_id", "") or "").strip()
    job_name = (request.query_params.get("job_name", "") or "").strip()
    example_name = (request.query_params.get("example_name", "") or "").strip()
    example_action = (request.query_params.get("example_action", "") or "").strip()
    return session_id, job_name, example_name, example_action

def passthrough_url(url):
    return url
