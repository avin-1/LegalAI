from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
import redis
import json
from resumeDB import get_aura_token,resume_instance,wait_for_running,verify_driver_connection
load_dotenv()

redis_client = redis.from_url(
    os.environ["REDIS_URL"],
    decode_responses=True
)

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")

def resumeDB():
    try:
        # 1. Authenticate
        token = get_aura_token()
        
        # 2. Resume
        resume_instance(token)
        
        # 3. Wait for it to be ready
        wait_for_running(token)
        
        # 4. Final Verification
        verify_driver_connection()
        
    except Exception as err:
        print(f"Automation failed: {err}")


driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

def connectDB():
    try:
        with driver.session() as session:
            session.run("RETURN 1")   
        print("Connection successful")
    except Exception as e:
        print("Connection failed:", e)
    
resumeDB()