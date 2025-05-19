import os
import sys
import importlib.util
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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

def inference_result_dummy(inputs):
    logging.info(f"✅ Received input: {inputs}")

    # Adapt to the expected format of external repo
    result = dummy_module.dummy_inference(inputs)  # or pass a file path, etc.

    # simulate processing time
    time.sleep(5)

    logging.info(f"✅ Inference result: {result}")

    return result

# --- Locate main.py in external_infer/src ---
external_root = os.path.join(os.path.dirname(__file__), "external_infer")
if external_root not in sys.path:
    sys.path.insert(0, external_root)

# --- Step 2: Import src.main (relative imports will work!) ---
main_module = importlib.import_module("src.main")
tandem_dimple = main_module.tandem_dimple
logging.info("✅ Successfully imported tandem_dimple() from external_infer/src/main.py")


def inference_result_input_as_list_SAVs(inputs):
    logging.info(f"✅ Received input: {inputs}")
    
    # Extract info from inputs
    text = inputs.get("text", "")
    session_id = inputs.get("session_id", "")

    # Make text into list of SAVs
    # Assuming the input is a string of SAVs separated by commas
    if isinstance(text, str):
        query = [s.strip() for s in text.split(",")]
    else:
        query = text
    # query = ['O14508 52 S N']

    td = tandem_dimple(
        query = query, # List of SAVs to be analyzed
        job_name = session_id, # Define where the job will be saved
        custom_PDB = None, # Path to the custom PDB file (if any)
        refresh = False, # Set to True to refresh the calculation
    )

    logging.info(f"✅ Inference results saved to job name: {session_id}")

    return "✅ Inference results saved to job name: {session_id}"

# Function use for API (should choose which function to use, and parse input?)
def inference_result(inputs):

    return inference_result_input_as_list_SAVs(inputs)