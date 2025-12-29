from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path

from src.config import OUTPUT_DIR
from src.pipeline import run_query

app = Flask(__name__)

@app.get("/")
def home():
    # Simply return a brief explanation for now.
    return "Server is running. POST /chat with JSON."


@app.post("/chat")
def chat():
    data = request.get_json(force=True)
    query = data.get("query", "")

    res = run_query(query=query, model="mistral")

    return jsonify({
        "status": "success",
        "message": f"Place: {res['place']}\nChosen tag: {res['chosen_tag']}\nExtracted nodes: {res['count']}\nLLM used: {res['llm_ok']}",
        "geojson_url": "/output/output.geojson",
        "evidence": res["evidence"],
    })


@app.get("/output/<path:filename>")
def output_files(filename):
    return send_from_directory(str(OUTPUT_DIR), filename)
from flask import send_file

#Place chat.html in the project root directory.
@app.get("/ui")
def ui():
    return send_file("chat.html")

if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host="127.0.0.1", port=8000, debug=True)
