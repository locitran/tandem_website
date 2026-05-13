import argparse
import json
import os
import re
import sys
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pymongo import MongoClient


SCRIPT_DIR = Path(__file__).resolve().parent
GRADIO_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = GRADIO_ROOT.parent
sys.path.insert(0, str(GRADIO_ROOT))

from src.settings import EXAMPLES_JSON, JOB_DIR, JOB_RETENTION_SECONDS, MOUNT_POINT


SESSION_ID = "test"
TIME_ZONE = ZoneInfo("Asia/Taipei")
DEFAULT_MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017/")
BASE_MODELS = ["TANDEM", "TANDEM-DIMPLE for GJB2", "TANDEM-DIMPLE for RYR1"]

INF_PATTERN = re.compile(
    r"^(?P<acc>\S+)\s+(?P<wt>[ACDEFGHIKLMNPQRSTVWY])(?P<resid>[0-9]+)(?P<mt>[ACDEFGHIKLMNPQRSTVWY])$"
)
TRAINING_PATTERN = re.compile(
    r"^(?P<acc>\S+)\s+(?P<wt>[ACDEFGHIKLMNPQRSTVWY])(?P<resid>[0-9]+)(?P<mt>[ACDEFGHIKLMNPQRSTVWY])\s+(?P<label>[01])$"
)


def clean_sav_line(line):
    return " ".join(str(line).replace("\\n", "").strip().split())


def validate_and_split_savs(example_name, mode, sav_lines):
    pattern = INF_PATTERN if mode == "Inferencing" else TRAINING_PATTERN
    savs = []
    labels = []

    for raw_line in sav_lines:
        line = clean_sav_line(raw_line)
        if not line:
            continue

        match = pattern.fullmatch(line)
        if not match:
            raise ValueError(f"{example_name}: invalid {mode} SAV line: {raw_line!r}")

        resid = int(match.group("resid"))
        if resid <= 0:
            raise ValueError(f"{example_name}: residue index must be positive: {raw_line!r}")
        if match.group("wt") == match.group("mt"):
            raise ValueError(f"{example_name}: WT and mutant are identical: {raw_line!r}")

        savs.append(f"{match.group('acc').upper()} {match.group('wt').upper()}{resid}{match.group('mt').upper()}")
        if mode == "Training":
            labels.append(int(match.group("label")))

    if not savs:
        raise ValueError(f"{example_name}: no SAV lines found")

    return savs, (labels if mode == "Training" else None)


def build_session_url(session_id):
    return f"/{MOUNT_POINT}/session/?session_id={session_id}"


def build_job_url(session_id, job_name):
    return f"/{MOUNT_POINT}/results/?session_id={session_id}&job_name={job_name}"


def build_payload(example_name, example_config, session_id):
    mode = example_config.get("mode", "Inferencing")
    if mode not in {"Inferencing", "Training"}:
        raise ValueError(f"{example_name}: unsupported mode: {mode!r}")

    job_name = str(example_config.get("job_name", "")).strip()
    if not job_name:
        raise ValueError(f"{example_name}: missing job_name")

    savs, labels = validate_and_split_savs(example_name, mode, example_config.get("SAV", []))
    submission_dt = datetime.now(TIME_ZONE)
    delete_after_ts = time.time() + JOB_RETENTION_SECONDS

    flags = deepcopy(example_config.get("flags", {}))
    if not isinstance(flags, dict):
        raise ValueError(f"{example_name}: flags must be a JSON object when provided")

    payload = {
        "status": "pending",
        "session_id": session_id,
        "session_url": build_session_url(session_id),
        "mode": mode,
        "SAV": savs,
        "label": labels,
        "model": example_config.get("model", BASE_MODELS[0]),
        "job_name": job_name,
        "submission_time": submission_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "submission_timestamp": submission_dt.timestamp(),
        "delete_after_ts": delete_after_ts,
        "delete_after_str": datetime.fromtimestamp(delete_after_ts, tz=TIME_ZONE).strftime("%Y-%m-%d %H:%M"),
        "email": None,
        "STR": example_config.get("str_file") if example_config.get("str_check", False) else None,
        "IP": "script",
        "geo_info": {},
        "city": "",
        "region": "",
        "country": "",
        "continent": "",
        "job_url": build_job_url(session_id, job_name),
        "refresh": bool(example_config.get("refresh", True)),
        "example_name": example_name,
        "submitted_by": "submit_example_jobs.py",
    }
    payload.update(flags)

    # Keep the historical behavior from SessionPage.on_load_examples.
    payload["GJB2_test"] = bool(payload.get("GJB2_test")) or example_name == "GJB2 SAVs for transfer learning"

    return payload


def load_examples(examples_path):
    with Path(examples_path).open("r", encoding="utf-8") as handle:
        examples = json.load(handle)
    if not isinstance(examples, dict):
        raise ValueError(f"Examples file must contain a JSON object: {examples_path}")
    return examples


def selected_examples(examples, names):
    if not names:
        return examples.items()

    missing = [name for name in names if name not in examples]
    if missing:
        available = ", ".join(examples)
        raise ValueError(f"Unknown example(s): {missing}. Available examples: {available}")

    return [(name, examples[name]) for name in names]


def connect_collection(mongo_uri):
    client = MongoClient(mongo_uri)
    client.admin.command("ping")
    return client["app_db"]["input_queue"]


def ensure_session(collection, session_id):
    collection.update_one(
        {"session_id": session_id, "job_name": {"$exists": False}},
        {
            "$setOnInsert": {
                "session_id": session_id,
                "status": "created",
                "refresh": False,
                "created_at": datetime.now(TIME_ZONE).strftime("%H%M%S%d%m%Y"),
                "submitted_by": "submit_example_jobs.py",
            }
        },
        upsert=True,
    )


def submit_payload(collection, payload, force_processing=False):
    query = {"session_id": payload["session_id"], "job_name": payload["job_name"]}
    existing = collection.find_one(query, {"_id": 0, "status": 1})
    existing_status = (existing or {}).get("status")

    if existing_status == "processing" and not force_processing:
        return "skipped_processing"

    collection.update_one(query, {"$set": payload}, upsert=True)
    return "submitted"


def wait_for_jobs(collection, jobs, timeout_seconds, poll_seconds):
    deadline = time.time() + timeout_seconds
    pending = {(payload["session_id"], payload["job_name"]) for payload in jobs}

    while pending and time.time() < deadline:
        for session_id, job_name in list(pending):
            row = collection.find_one(
                {"session_id": session_id, "job_name": job_name},
                {"_id": 0, "status": 1, "job_end_str": 1},
            )
            if row and row.get("status") == "finished":
                pending.remove((session_id, job_name))
                print(f"finished: {session_id}/{job_name}")

        if pending:
            print(f"waiting: {len(pending)} job(s) still not finished")
            time.sleep(poll_seconds)

    return pending


def parse_args():
    parser = argparse.ArgumentParser(
        description="Submit all configured website example jobs under the read-only test session."
    )
    parser.add_argument(
        "--examples-json",
        default=EXAMPLES_JSON,
        help=f"Path to examples.json. Default: {EXAMPLES_JSON}",
    )
    parser.add_argument(
        "--session-id",
        default=SESSION_ID,
        help="Session ID to use for regenerated examples. Default: test",
    )
    parser.add_argument(
        "--mongo-uri",
        default=DEFAULT_MONGO_URI,
        help=f"MongoDB URI. Default: {DEFAULT_MONGO_URI}",
    )
    parser.add_argument(
        "--example",
        action="append",
        default=[],
        help="Submit only this example name. Can be repeated. Default: submit all examples.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print payloads without writing to MongoDB.",
    )
    parser.add_argument(
        "--force-processing",
        action="store_true",
        help="Overwrite an example even if its current status is processing.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait until submitted jobs become finished.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=60 * 60 * 6,
        help="Maximum time to wait with --wait. Default: 21600.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=15,
        help="Polling interval for --wait. Default: 15.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    examples = load_examples(args.examples_json)
    payloads = [
        build_payload(name, config, args.session_id)
        for name, config in selected_examples(examples, args.example)
    ]

    if args.dry_run:
        print(json.dumps(payloads, indent=2))
        return 0

    collection = connect_collection(args.mongo_uri)
    ensure_session(collection, args.session_id)

    submitted = []
    for payload in payloads:
        result = submit_payload(collection, payload, force_processing=args.force_processing)
        job_ref = f"{payload['session_id']}/{payload['job_name']}"
        if result == "submitted":
            submitted.append(payload)
            print(f"submitted: {job_ref}")
        else:
            print(f"skipped processing job: {job_ref}")

    print(f"queued {len(submitted)} job(s) for regeneration under session '{args.session_id}'")
    print(f"job output root: {Path(JOB_DIR) / args.session_id}")

    if args.wait and submitted:
        unfinished = wait_for_jobs(collection, submitted, args.timeout_seconds, args.poll_seconds)
        if unfinished:
            for session_id, job_name in sorted(unfinished):
                print(f"not finished before timeout: {session_id}/{job_name}")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
