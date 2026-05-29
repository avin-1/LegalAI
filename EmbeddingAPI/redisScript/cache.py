import os, sys, json, hashlib
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE_DIR)
from dotenv import load_dotenv
load_dotenv()
import redis 
from chromaDB.store import ChromaStore

# Strict redis connection can cause import-time crashes if redis is not available
# Switching to lazy/function-based access could be better, but for minimal change let's just make it robust
# or keep it simple. Actually, top level connection is bad pattern.

r = None

def get_redis():
    global r
    if r is None:
        try:
            r = redis.from_url(os.getenv("REDIS_URL"))
            r.ping() # check connection
        except Exception as e:
            print(f"Warning: Redis connection failed: {e}")
            r = None
    return r

def cache_search_result(user_id: int, query: str, k: int = 3):
    client = get_redis()
    if not user_id:
        print("Error: user_id is missing")
        return {"error": "user_id is missing"}
        
    if not client:
        print("Redis unavailable, skipping cache")
        return {"error": "Redis unavailable"}

    result = ChromaStore.search(user_id, query, k)

    chunks = result["chunks"]
    print(f"Caching search result for user {user_id}: {chunks}")

    payload = {
        "chunks": chunks, # Store directly inside JSON payload
        "description": "retrieved context from database, LLMs kindly refer this"
    }

    query_hash = hashlib.sha256(query.encode()).hexdigest()
    cache_key = f"user:{user_id}:{query_hash}_vector"

    try:
        client.set(cache_key, json.dumps(payload), ex=3600)
    except Exception as e:
        print(f"Failed to cache to Redis: {e}")

    return payload

