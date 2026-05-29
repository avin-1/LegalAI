from flask import Flask, request, g, jsonify
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import os
import redis
import json
import hashlib
from extract import extract
from neo4jDB.graphBuilder import retrieve, addInGraph
from auth_middleware import jwt_required
load_dotenv(override=True)
PORT = os.getenv('PORT', 8001)
app = Flask(__name__)


@app.route('/')
def hello():
    return {"Message": "GraphAPI is running"}


redis_client = redis.from_url(
    os.environ["REDIS_URL"],
    decode_responses=True
)

# Use SPACE_ID to detect HuggingFace Spaces (os.path.exists('/data') is unreliable on Windows)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.environ.get('SPACE_ID'):
    Dest = "/data/upload"
else:
    Dest = os.path.join(BASE_DIR, "upload")
    
os.makedirs(Dest, exist_ok=True)


@app.route('/upload', methods=['POST'])
@jwt_required
def upload():
    user_id = g.user_claims.get("sub")
    file = request.files.get('file')
    if not file:
        return {"Message": "Please Upload File — check key('file') too"}
    path = os.path.join(Dest, str(user_id))
    os.makedirs(path, exist_ok=True)

    filename = secure_filename(file.filename)
    savePath = os.path.join(path, filename)
    if os.path.isfile(savePath):
        return {"message": "File already exists"}
    file.save(savePath)
    extract(user_id, base_upload_dir=Dest)
    addInGraph(user_id)

    return {"Message": "File Saved Successfully"}


@app.route('/retrieve', methods=['POST'])
@jwt_required
def getInfo():
    query = request.form.get('query')
    user_id = g.user_claims.get("sub")

    if not query:
        return {"message": "Missing query"}, 400

    try:
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        cache_key = f"user:{user_id}:{query_hash}"
        cached = redis_client.get(cache_key)

        if cached:
            return {"message": "success", "data": json.loads(cached), "source": "cache"}
    except Exception as e:
        print(f"Redis Error: {e}")

    try:
        result = retrieve(query)

        redis_client.set(
            cache_key,
            json.dumps(result),
            ex=3600
        )

        return {"message": "success", "data": result, "source": "db"}
    except Exception as e:
        return {"message": "Failed", "error": str(e)}, 404


if __name__ == "__main__":
    app.run(port=PORT, debug=True)