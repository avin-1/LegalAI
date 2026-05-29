import requests
import time
import sys

URL = "http://127.0.0.1:5000/retrieve"
DATA = {"query": "test query", "userid": "1"}

def test_caching():
    print("Sending first request...")
    start_time = time.time()
    try:
        response1 = requests.post(URL, data=DATA)
        response1.raise_for_status()
        print(f"Response 1: {response1.status_code} in {time.time() - start_time:.4f}s")
    except Exception as e:
        print(f"Request 1 failed: {e}")
        return

    print("\nSending second request (should be faster if cached)...")
    start_time = time.time()
    try:
        response2 = requests.post(URL, data=DATA)
        response2.raise_for_status()
        print(f"Response 2: {response2.status_code} in {time.time() - start_time:.4f}s")
    except Exception as e:
        print(f"Request 2 failed: {e}")

if __name__ == "__main__":
    test_caching()
