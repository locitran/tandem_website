import os
import sys
import importlib.util
import time
import logging
import zipfile
import base64

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

    start_time = time.time()

    # Extract info from inputs
    text = inputs.get("text", "")
    submission_id = inputs.get("submission_id", "")

    # Make text into list of SAVs
    # Assuming the input is a string of SAVs separated by commas
    if isinstance(text, str):
        query = [s.strip() for s in text.split(",")]
    else:
        query = text
    # query = ['O14508 52 S N']

    td = tandem_dimple(
        query = query, # List of SAVs to be analyzed
        job_name = submission_id, # Define where the job will be saved
        custom_PDB = None, # Path to the custom PDB file (if any)
        refresh = False, # Set to True to refresh the calculation
    )

    logging.info(f"✅ Inference results saved to job name: {submission_id}")

    # Zip all the result files
    result_folder = "./external_infer/jobs"

    zip_path = f"/shared/results/{submission_id}_results.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in os.listdir(os.path.join(result_folder, submission_id)):
            file_path = os.path.join(result_folder, submission_id, file)
            zipf.write(file_path, os.path.basename(file_path))

    # Load result files
    with open(os.path.join(result_folder, submission_id, f"{submission_id}-report.txt"), "r") as f:
        lines = f.readlines()

    header = lines[0].strip().split() # ["SAVs", "Probability", "Decision", "Voting"]

    # Parse the lines into a list of lists
    lines = [line.strip() for line in lines[1:]]

    results = []
    for line in lines:
        # Split the line by whitespace and convert to a list
        parts = line.split()

        voting = float(parts[-1])
        decision = parts[-2]
        probability = float(parts[-3])
        sav = " ".join(parts[:-3])

        # Create a list of the parts
        parts = [sav, probability, decision, voting]

        # Append the list to the results
        results.append(parts)

    logging.info(f"Total inference time: {time.time() - start_time:.2f} seconds")

    return results


def tandem(inputs):
    logging.info(f"✅ Received input: {inputs}")

    start_time = time.time()

    # Extract info from inputs
    submission_id = inputs.get("submission_id", "")
    SAV_input = inputs.get("SAV_input", "")
    STR_input = inputs.get("STR_input", "")

    logging.info(f"STR_input: {STR_input}")
    job_directory = os.path.join(main_module.ROOT_DIR, 'jobs', submission_id)

    if STR_input:
        custom_pdb = os.path.join(job_directory, STR_input)
        logging.info(f"custom_pdb: {custom_pdb}")
        if not os.path.isfile(custom_pdb):
            custom_pdb = STR_input
    else:
        custom_pdb = None

    tandem_dimple(
        query=SAV_input,
        job_name=submission_id,
        custom_PDB=custom_pdb,
        refresh=False,
    )

    logging.info(f"✅ Inference results saved to job name: {submission_id}")

    # Zip all the result files
    result_folder = "./external_infer/jobs"

    zip_path = f"/shared/results/{submission_id}_results.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in os.listdir(os.path.join(result_folder, submission_id)):
            file_path = os.path.join(result_folder, submission_id, file)
            zipf.write(file_path, os.path.basename(file_path))

    # Load result files
    with open(os.path.join(result_folder, submission_id, f"predictions.txt"), "r") as f:
        lines = f.readlines()

    header = lines[0].strip().split() # ["SAVs", "Voting", "Probability", "Decision"]

    # Parse the lines into a list of lists
    lines = [line.strip() for line in lines[1:]]

    results = []
    for line in lines:
        # Split the line by whitespace and convert to a list
        parts = line.split()

        decision = parts[-1]
        probability = parts[-2]
        voting = parts[-3]

        sav = " ".join(parts[:-3])

        # Create a list of the parts
        parts = [sav, probability, decision, voting]

        # Append the list to the results
        results.append(parts)

    logging.info(f"Total inference time: {time.time() - start_time:.2f} seconds")
    return results



# Function use for API (should choose which function to use, and parse input?)
def inference_result(inputs):

    return inference_result_input_as_list_SAVs(inputs)
