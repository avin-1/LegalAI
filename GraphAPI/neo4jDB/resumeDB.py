import os
import time
import requests
from requests.auth import HTTPBasicAuth
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load your .env variables
load_dotenv()

# Configuration from your provided details
CLIENT_ID = os.getenv("ClientID")
CLIENT_SECRET = os.getenv("ClientSecret")
INSTANCE_ID = os.getenv("AURA_INSTANCEID")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

def get_aura_token():
    """Obtains an OAuth2 bearer token from Neo4j Aura."""
    url = "https://api.neo4j.io/oauth/token"
    payload = {"grant_type": "client_credentials"}
    response = requests.post(url, auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET), data=payload)
    response.raise_for_status()
    return response.json()["access_token"]

def resume_instance(token):
    """Sends the resume command to the Aura API."""
    url = f"https://api.neo4j.io/v1/instances/{INSTANCE_ID}/resume"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json={})
    
    if response.status_code == 202:
        print(f"Resumption initiated for instance {INSTANCE_ID}...")
    elif response.status_code == 403:
        # Handled in case it's already running based on your previous error
        print("Instance is already running or action is not allowed.")
    else:
        print(f"Unexpected status: {response.status_code} - {response.text}")

def wait_for_running(token):
    """Polls the API until the instance status is 'running'."""
    url = f"https://api.neo4j.io/v1/instances/{INSTANCE_ID}"
    headers = {"Authorization": f"Bearer {token}"}
    
    print("Waiting for instance to reach 'running' state...")
    while True:
        response = requests.get(url, headers=headers)
        status = response.json().get("data", {}).get("status")
        if status == "running":
            print("Instance is now ONLINE.")
            break
        time.sleep(15)  # Wait 15 seconds between checks

def verify_driver_connection():
    """Verifies that the Neo4j Python driver can connect."""
    print(f"Connecting to {NEO4J_URI}...")
    try:
        with GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
            driver.verify_connectivity()
            print("Successfully connected to the database!")
    except Exception as e:
        print(f"Connection failed: {e}")
