from flask import Flask, request, jsonify

app = Flask(__name__)

# Dummy inference function
def inference_result(input_data):
    text = input_data.get("text", "")
    return f"🔮 Inference result based on: {text[:30]}..."

@app.route("/infer", methods=["POST"])
def infer():
    input_data = request.get_json()
    result = inference_result(input_data)
    return jsonify({"output": result})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
