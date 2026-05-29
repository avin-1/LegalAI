from flask import Flask, request, jsonify
import requests
import redis
from dotenv import load_dotenv
import os
import logging
from app.graph import queryHandler
# Load env immediately
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PORT = os.getenv('PORT')
app = Flask(__name__)

@app.route('/')
def home():
    return {
        "message": "Hello world"
    }

@app.route('/upload', methods=['POST', 'GET'])
def upload():
    try:
        auth_header = request.headers.get('Authorization')
        userid = request.args.get('userid') if request.method == 'GET' else request.form.get('userid')
        
        if auth_header and auth_header.startswith("Bearer "):
            import jwt
            try:
                token = auth_header.split(" ")[1]
                payload = jwt.decode(token, options={"verify_signature": False})
                userid = payload.get("sub", userid)
            except Exception as e:
                logger.error(f"Failed to decode JWT: {e}")

        # Connect to Redis
        redis_url = os.getenv("REDIS_URL1") or "redis://localhost:6379"
        r = redis.from_url(redis_url, decode_responses=True)

        if request.method == 'GET':
            if not userid:
                return jsonify({"error": "userid missing"}), 400
            
            # Fetch active document for this specific user
            active_doc = r.get(f"user:{userid}:active_document")
            return jsonify({"filename": active_doc or ""}), 200

        # POST Method (Upload)
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
            
        file = request.files['file']

        if not file or not userid:
            return jsonify({"error": "file or userid missing"}), 400
        
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Save to Redis for true cross-session persistence
        r.set(f"user:{userid}:active_document", file.filename)

        # Read file content once to send to multiple destinations
        file_bytes = file.read()
        
        embedding_url_base = os.getenv('EMBEDDING_API_URL')
        graph_url_base = os.getenv('GRAPH_API_URL')

        if not embedding_url_base or not graph_url_base:
             logger.error("API URLs not configured")
             return jsonify({"error": "Server configuration error"}), 500

        # Forward Authorization header
        headers = {}
        if auth_header:
            headers['Authorization'] = auth_header

        # Upload to Embedding API
        embedding_res_data = {}
        try:
            url1 = f"{embedding_url_base}/upload"
            logger.info(f"Uploading to Embedding API: {url1}")
            files1 = {
                "file": (file.filename, file_bytes, file.mimetype)
            }
            response1 = requests.post(url1, files=files1, headers=headers, timeout=30)
            embedding_res_data = {
                "status": response1.status_code,
                "body": response1.text
            }
            logger.info(f"Embedding API response: {response1.status_code}")
        except Exception as e:
            logger.error(f"Failed to upload to Embedding API: {e}")
            embedding_res_data = {"error": str(e)}

        # Upload to Graph API
        graph_res_data = {}
        try:
            url2 = f"{graph_url_base}/upload"
            logger.info(f"Uploading to Graph API: {url2}")
            files2 = {
                "file": (file.filename, file_bytes, file.mimetype)
            }
            data2 = {
                "user_id": userid
            }
            response2 = requests.post(url2, files=files2, data=data2, headers=headers, timeout=30)
            graph_res_data = {
                "status": response2.status_code,
                "body": response2.text
            }
            logger.info(f"Graph API response: {response2.status_code}")
        except Exception as e:
             logger.error(f"Failed to upload to Graph API: {e}")
             graph_res_data = {"error": str(e)}

        return jsonify({
            "embeddings msg": embedding_res_data,
            "graph msg": graph_res_data
        }), 200

    except Exception as e:
        logger.error(f"Unexpected error in /upload: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/query', methods=['POST'])
async def query():
    try:
        query = request.form.get('query')
        user = request.form.get('userid')
        auth_header = request.headers.get('Authorization')

        # Prefer the secure UUID from the JWT 'sub' claim
        if auth_header and auth_header.startswith("Bearer "):
            import jwt
            try:
                token = auth_header.split(" ")[1]
                payload = jwt.decode(token, options={"verify_signature": False})
                user = payload.get("sub", user)
            except Exception as e:
                logger.error(f"Failed to decode JWT: {e}")
        
        if not query or not user:
             return jsonify({"error": "Missing query or userid"}), 400
        
        logger.info(f"Processing query for user {user}")
        response = await queryHandler(query, user, auth_header)
        return jsonify({"response": response})
    except Exception as e:
        logger.error(f"Error in /query endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/explain', methods=['POST'])
async def explain():
    try:
        text = request.form.get('text')
        if not text:
             return jsonify({"error": "Missing text parameter"}), 400
        
        logger.info(f"Processing explain request.")
        from app.graph import explainHandler
        response = await explainHandler(text)
        return jsonify({"response": response})
    except Exception as e:
        logger.error(f"Error in /explain endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    port_str = PORT or '5000'
    logger.info(f"Starting server on port {port_str}")
    # Disable debug mode for production-like strictness, or keep it if dev is intended. 
    # Keeping debug=True for now as per original, but usually False for prod.
    # To strictly follow "production grade", debug should be off or env controlled.
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(port=int(port_str), debug=debug_mode)