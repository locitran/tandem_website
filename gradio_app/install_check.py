import importlib
import os
import shutil
import subprocess
import sys


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

PYTHON_IMPORTS = [
    ("gradio", "gradio"),
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("pymongo", "pymongo"),
    ("requests", "requests"),
    ("yattag", "yattag"),
    ("jsonyx", "jsonyx"),
    ("sass", "libsass"),
]

MODULE_IMPORTS = [
    ("src.home", "src.home"),
    ("src.session", "src.session"),
    ("src.results", "src.results"),
    ("src.error", "src.error"),
    ("src.job_manager", "src.job_manager"),
    ("src.base", "src.base"),
]

CLI_COMMANDS = [
    "python",
]

REQUIRED_PATHS = [
    os.path.join(ROOT_DIR, "main.py"),
    os.path.join(ROOT_DIR, "src"),
    os.path.join(ROOT_DIR, "assets"),
    os.path.join(ROOT_DIR, "sass"),
    os.path.join(ROOT_DIR, "src", "html", "home_examples.html"),
    os.path.join(ROOT_DIR, "src", "html", "inf_examples.html"),
    os.path.join(ROOT_DIR, "src", "html", "tf_examples.html"),
]


def check_import(module_name, label):
    try:
        importlib.import_module(module_name)
        return True, f"OK import: {label}"
    except Exception as exc:
        return False, f"FAIL import: {label} -> {exc}"


def check_command(command_name):
    resolved = shutil.which(command_name)
    if resolved:
        return True, f"OK command: {command_name} -> {resolved}"
    return False, f"FAIL command: {command_name} not found on PATH"


def check_required_path(path):
    relative_path = os.path.relpath(path, ROOT_DIR)
    if os.path.exists(path):
        return True, f"OK path: {relative_path}"
    return False, f"FAIL path: {relative_path} is missing"


def run_checks():
    print("=== Gradio app installation check ===")
    failures = []

    for module_name, label in PYTHON_IMPORTS:
        ok, message = check_import(module_name, label)
        print(message)
        if not ok:
            failures.append(message)

    for module_name, label in MODULE_IMPORTS:
        ok, message = check_import(module_name, label)
        print(message)
        if not ok:
            failures.append(message)

    for command_name in CLI_COMMANDS:
        ok, message = check_command(command_name)
        print(message)
        if not ok:
            failures.append(message)

    for path in REQUIRED_PATHS:
        ok, message = check_required_path(path)
        print(message)
        if not ok:
            failures.append(message)

    pip_check = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True,
        text=True,
    )
    if pip_check.returncode == 0:
        print("OK dependency check: pip check")
    else:
        message = "FAIL dependency check: pip check\n" + (pip_check.stdout or pip_check.stderr).strip()
        print(message)
        failures.append(message)

    if failures:
        print("\nGradio app installation check failed.")
        print("The Docker image is missing one or more required imports, files, or executables.")
        return 1

    print("\nGradio app installation successful.")
    print("All checked Python imports, source files, and dependencies are available.")
    return 0


if __name__ == "__main__":
    sys.exit(run_checks())
