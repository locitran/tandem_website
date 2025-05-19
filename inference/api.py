from flask import Flask, request, jsonify
from adapter import inference_result
import time
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

app = Flask(__name__)

@app.route("/infer", methods=["POST"])
def infer():
    input_data = request.get_json()

    logging.info(f"Received input: {input_data}")

    if not input_data:
        logging.error("No JSON received")

        return jsonify({"error": "No JSON received"}), 400

    try:
        result = inference_result(input_data)
        logging.info(f"Inference result: {result}")

        return jsonify({"output": result})
    except Exception as e:
        logging.error(f"Error in inference: {e}")

        return jsonify({"error": str(e)}), 500

@app.route("/health")
def health():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
