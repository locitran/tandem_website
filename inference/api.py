from flask import Flask, request, jsonify
import time

app = Flask(__name__)

# Dummy inference function
def inference_result(input_data):
    text = input_data.get("text", "")

    # simulate processing time
    time.sleep(5)

    return f"🔮 Inference result based on: {text[:30]}..."

@app.route("/infer", methods=["POST"])
def infer():
    input_data = request.get_json()
    if not input_data:
        return jsonify({"error": "No JSON received"}), 400
    try:
        result = inference_result(input_data)
        return jsonify({"output": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
