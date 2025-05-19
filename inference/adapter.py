import os
import importlib.util
import time

# Construct the full path to dummy.py
DUMMY_PATH = os.path.join(
    os.path.dirname(__file__),
    "external_infer",
    "test",
    "dummy.py"
)

# Dynamically import dummy.py
spec = importlib.util.spec_from_file_location("dummy_module", DUMMY_PATH)
dummy_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dummy_module)

def inference_result(input_text):
    # Extract what you need
    # text = input_data.get("text", "")

    # Adapt to the expected format of external repo
    result = dummy_module.dummy_inference(input_text)  # or pass a file path, etc.

    # simulate processing time
    time.sleep(5)

    return result
