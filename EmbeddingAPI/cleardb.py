"""
cleardb.py — Wipe ChromaDB collections and/or uploaded files.

Usage:
    uv run cleardb.py          # clears all chroma collections
    uv run cleardb.py --all    # also deletes uploads folder
"""

import sys
import shutil
import os
from chromadb import PersistentClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chromadb_store")
UPLOADS_PATH = os.path.join(BASE_DIR, "uploads")

def clear_chroma():
    if not os.path.exists(CHROMA_PATH):
        print("ChromaDB store not found — nothing to clear.")
        return
    client = PersistentClient(path=CHROMA_PATH)
    collections = client.list_collections()
    if not collections:
        print("No collections found in ChromaDB.")
        return
    for col in collections:
        client.delete_collection(col.name)
        print(f"  Deleted collection: {col.name}")
    print(f"✓ Cleared {len(collections)} collection(s) from ChromaDB.")

def clear_uploads():
    if not os.path.exists(UPLOADS_PATH):
        print("Uploads folder not found — nothing to clear.")
        return
    shutil.rmtree(UPLOADS_PATH)
    os.makedirs(UPLOADS_PATH, exist_ok=True)
    print(f"✓ Cleared uploads folder: {UPLOADS_PATH}")

if __name__ == "__main__":
    clear_all = "--all" in sys.argv
    print("=== EmbeddingAPI DB Cleaner ===")
    clear_chroma()
    if clear_all:
        clear_uploads()
    print("Done.")
