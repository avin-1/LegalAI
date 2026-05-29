from flask import Flask, request, jsonify, g
from dotenv import load_dotenv
import os
load_dotenv()
PORT = os.getenv('PORT', 8000)
app = Flask(__name__)
from redisScript.cache import cache_search_result
from auth_middleware import jwt_required


@app.route('/')
def home():
    return {"message": "EmbeddingAPI is running"}

# Use SPACE_ID to detect HuggingFace Spaces (os.path.exists('/data') is unreliable on Windows)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.environ.get('SPACE_ID'):
    UPLOAD_DIR = "/data/uploads"
else:
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

@app.post("/upload")
@jwt_required
def upload():
    user_id = g.user_claims.get("sub")

    if "file" not in request.files:
        return jsonify({"error": "no file provided"}), 400

    file = request.files["file"]

    user_dir = os.path.join(UPLOAD_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)

    dest = os.path.join(user_dir, file.filename)
    file.save(dest)
    saved_size = os.path.getsize(dest)
    print(f"[upload] Saved '{file.filename}' to {dest} ({saved_size} bytes)")
    if saved_size == 0:
        return jsonify({"error": "Uploaded file is empty"}), 400

    # Trigger the embedding process
    try:
        from graph import start
        start_res = start(user_id)
        print(f"Graph execution result: {start_res}")
    except Exception as e:
        print(f"Error running graph: {e}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"status": "ok", "path": dest, "message": "File processed and embedded."})


@app.route('/search', methods=['POST'])
@jwt_required
def search():
    query = request.form.get('query')
    user_id = g.user_claims.get("sub")

    if not query:
        return jsonify({"error": "Missing query"}), 400

    cache_search_result(user_id, query, 7)
    return {"message": "Retrieved data stored in redis"}


if __name__ == "__main__":
    app.run(port=PORT, debug=True)
