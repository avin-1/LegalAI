import os, json
from dotenv import load_dotenv
import redis

load_dotenv()

r = redis.from_url(os.getenv("REDIS_URL"))

user_id = 1   # change as needed

if not r.exists(str(user_id)):
    print("No cache entry found for user:", user_id)
else:
    data = r.hgetall(str(user_id))

    # Decode bytes
    decoded = {k.decode(): v.decode() for k, v in data.items()}

    print("CACHE ENTRY:")
    print(json.dumps(decoded, indent=2))

    # optional: show chunks parsed back to list
    chunks = json.loads(decoded["chunks"])
    print("\nFirst chunk preview:\n", chunks[0][:200])


# from extraction.extract import extract_user_docs

# extract_user_docs("1")



# Script to clear redis
# import os
# from dotenv import load_dotenv
# import redis

# load_dotenv()

# r = redis.from_url(os.getenv("REDIS_URL"))

# confirm = input("This will DELETE ALL DATA in Redis. Continue? (yes/no): ")

# if confirm.lower() == "yes":
#     r.flushdb()
#     print("Redis cleared.")
# else:
#     print("Cancelled.")

# from chromaDB.store import ChromaStore

# retrieved = ChromaStore.search(1, "python developer machine learning", 7)
# print(retrieved)