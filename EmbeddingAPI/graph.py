from langgraph.graph import StateGraph,START,END
from extraction.extract import extract_user_docs
from chromaDB.store import ChromaStore
from redisScript.cache import cache_search_result
from typing import TypedDict
class State(TypedDict):
    user_id: int
    user: str
    
def createVectors(state:State):
    user_id = state["user_id"]
    user = ChromaStore(user_id)
    user.create_embeddings()
    return state
    
def extract(state:State):
    userid = state["user"]
    extract_user_docs(userid)
    return state
    

graph = StateGraph(State)
graph.add_node("extract",extract)
graph.add_node("createVectorStore",createVectors)


graph.add_edge(START,"extract")
graph.add_edge("extract","createVectorStore")
graph.add_edge("createVectorStore",END)

app = graph.compile()
def start(user_id: int):
    return app.invoke({"user_id": user_id, "user": str(user_id)})