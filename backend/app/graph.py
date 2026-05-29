from typing import TypedDict, Dict, List, Any, Optional
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
import requests
import redis.asyncio as redis
import os
import logging
import asyncio, hashlib
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
load_dotenv(override=True)
from langchain_core.tools import tool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Validate essential environment variables early
required_vars = ["EMBEDDING_API_URL", "GRAPH_API_URL", "REDIS_URL1", "REDIS_URL2"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.warning(f"Missing environment variables: {', '.join(missing_vars)}. Application may not function correctly.")

llm = ChatGroq(model='openai/gpt-oss-120b', temperature=0)

class State(TypedDict):
    query: str
    user: int
    answer: Dict[str, Any]
    fans: str
    needs_refactor: bool
    tries: int
    headers: Dict[str, str]


def refactorQuery(query: str) -> str:
    sysmsg = SystemMessage("You are a query refactoring assistant working in a RAG Pipeline" 
    "Rewrite the user query into a concise, factual search query. " 
    "Remove explanations, opinions, and conversation history. "
    "Focus only on entities, constraints, and relationships. " 
    "place some keywords in the query and maybe their synonyms too"
    "Focus on rewording the query to make it align with the legal terminology and proffessional Terminology and language. Use Different words for the same intent." 
    "use different synonyms for the main words and attach it to query." 
    "sometimes we may need rewrite query into multiple queries to retrieve the best chunkes to answer that query. so you can rewrite query into multiple queries. " 
    "Return only the rewritten query." )
    hummsg = HumanMessage(
        f"User query: {query}\n"
    )

    response = llm.invoke([sysmsg, hummsg])
    query = response.content.strip()
    return query

llm_with_tools = llm.bind_tools([refactorQuery])

async def makeQueryCall(state: State) -> State:
    """Makes query calls to embedding and graph APIs."""
    query = state.get('query')
    user = state.get('user')
    
    if not query or not user:
        logger.error("Missing query or user in state")
        return state

    payload = {
        "query": query,
        "userid": user
    }
    
    embedding_url = os.getenv('EMBEDDING_API_URL')
    graph_url = os.getenv('GRAPH_API_URL')

    if not embedding_url or not graph_url:
        logger.error("API URLs not configured.")
        return state

    url1 = f"{embedding_url}/search"
    url2 = f"{graph_url}/retrieve"

    async def call_api(name, url):
        try:
            logger.info(f"Calling {name}: {url}")
            headers = state.get('headers', {})
            response = await asyncio.to_thread(requests.post, url=url, data=payload, headers=headers, timeout=60)
            response.raise_for_status()
            logger.info(f"{name} response: {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"Error calling {name}: {e}")
            if 'response' in locals() and response is not None:
                 logger.error(f"{name} Error Response: {response.text}")

    await asyncio.gather(
        call_api("Embedding API", url1),
        call_api("Graph API", url2)
    )

    return state

async def fetchData(state: State) -> State:
    """Fetches data from Redis instances."""
    state.setdefault("answer", {})
    user = str(state.get('user'))
    query = state.get('query', '')
    query_hash = hashlib.sha256(query.encode('utf-8')).hexdigest()

    async def fetch_from_redis(redis_url_env, is_vector=False):
        redis_url = os.getenv(redis_url_env)
        if not redis_url:
            logger.warning(f"{redis_url_env} not set, skipping.")
            return []
            
        try:
            r = redis.from_url(redis_url, decode_responses=True)
            responses = []
            
            # Fetch exactly the cache key for this specific query
            suffix = "_vector" if is_vector else ""
            key = f"user:{user}:{query_hash}{suffix}"
            
            value = await r.get(key)
            if value:
                responses.append(value)
                
            await r.close()
            return responses
        except Exception as e:
            logger.error(f"Error fetching from {redis_url_env}: {e}")
            return []

    graph_responses, vector_db_responses = await asyncio.gather(
        fetch_from_redis("REDIS_URL1", is_vector=False),
        fetch_from_redis("REDIS_URL2", is_vector=True)
    )
    
    state["answer"]["graphResponse"] = graph_responses
    state["answer"]["vectorDBResponse"] = vector_db_responses
    
    return state

def llmCall(state: State) -> State:
    """Invokes the LLM to generate an answer."""
    try:
        if not state.get("query"):
             return state

        if state['tries'] < 3:
            system_msg = SystemMessage(
                content=("""
                    You are a legal reasoning assistant answering questions about a closed, fully indexed legal document.

                    Rules:
                    1. Answer strictly using the provided reference information.
                    2. First, identify all relevant clauses present in the reference information.
                    3. If a relevant clause or condition IS present, reason over it and answer.
                    4. Apply exception precedence: exception clauses override default rules.
                    5. If and only if no relevant clause exists anywhere in the reference information, state definitively that no such provision exists.
                    6. Do NOT mention retrieval, tools, missing context, or uncertainty.
                    7. Do NOT infer unstated obligations.
                    8. If the user query is verbose or unclear, you may rewrite it into a concise factual query before answering.
                    """
                )
            )
        else:
            system_msg = SystemMessage(
                content=("""You are a legal reasoning assistant answering questions about a closed, fully indexed legal document.
                                Rules:
                                1. Answer strictly using the provided reference information.
                                2. Identify and reason over any relevant clauses that are present.
                                3. Apply exception precedence where applicable.
                                4. If no relevant clause exists in the document, state definitively that no such provision exists.
                                5. Do NOT mention retrieval, tools, missing context, or uncertainty.
                                6. Do NOT infer unstated obligations.
                                7. Provide a direct, final answer only.
                                8. If you are saying No or denying the query you must give a proper explaination and reason more before answering.
                        """
                    )
            )
        llm_to_use = llm_with_tools if state["tries"] < 3 else llm
        human_msg = HumanMessage(content=state["query"])

        answer_context = state.get("answer", {})
        context_str = f"Graph Responses: {answer_context.get('graphResponse', [])}\nVector DB Responses: {answer_context.get('vectorDBResponse', [])}"

        context_msg = HumanMessage(
            content=f"Reference information:\n{context_str}"
        )

        response = llm_to_use.invoke([system_msg, context_msg, human_msg])
        
        
        if response.tool_calls and state['tries']<3:
            tool_call = response.tool_calls[0]
            logger.info("Refactoring Query")
            new_query = refactorQuery(**tool_call["args"])
            logger.info("Query Refactored")
            state["query"] = new_query
            state["tries"] +=1
            state["needs_refactor"] = True
            return state

            
        state["fans"] = response.content
        state["needs_refactor"] = False
    except Exception as e:
        logger.error(f"Error in LLM call: {e}")
        state["fans"] = "I encountered an error while processing your request."
    
    return state


def llm_decision(state: State):
    if state.get("needs_refactor"):
        return "query_call"
    return END



graph = StateGraph(State)

graph.add_node("query_call", makeQueryCall)
graph.add_node("fetch_data", fetchData)
graph.add_node("llm_call", llmCall)


graph.add_edge(START, "query_call")
graph.add_edge("query_call", "fetch_data")
graph.add_edge("fetch_data", "llm_call")
graph.add_conditional_edges(
    "llm_call",
    llm_decision,
    {
        "query_call": "query_call",
        END: END
    }
)

app = graph.compile()

async def queryHandler(query: str, user: int, auth_token: Optional[str] = None) -> str:
    # Prepare headers for downstream calls
    headers = {}
    if auth_token:
        headers["Authorization"] = auth_token

    try:
        s = await app.ainvoke({
        "query": query,
        "user": user,
        "tries": 0,
        "needs_refactor": False,
        "headers": headers
        })
        return s.get('fans', "No response generated.")
    except Exception as e:
        logger.error(f"Error in queryHandler: {e}")
        return "An internal error occurred."

async def explainHandler(text: str) -> str:
    """Explains a piece of text in simple terms."""
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        sys_msg = SystemMessage("You are a helpful legal assistant. Explain the provided legal text in very simple language that can be easily understood by common people and non-techies.")
        hum_msg = HumanMessage(f"Text to explain: {text}")
        response = llm.invoke([sys_msg, hum_msg])
        return response.content
    except Exception as e:
        logger.error(f"Error in explainHandler: {e}")
        return "An error occurred while trying to explain the text. Please try again later."
