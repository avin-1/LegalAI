from langchain_groq import ChatGroq
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
load_dotenv()
import os
from langchain_neo4j import Neo4jGraph
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Make llm from chatgroq
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    max_tokens=None,
    timeout=None,
)

graphTransformer = LLMGraphTransformer(
    llm=llm,

    allowed_nodes=[
        "Person",          
        "Organization",    
        "Document",        
        "Clause",          
        "Technology",      
        "Concept",         
        "Date",
        "Party",
        "Compensation"   
    ],

    allowed_relationships=[
        "AUTHORED",        
        "BELONGS_TO",      
        "MENTIONS",        
        "USES",            
        "ASSOCIATED_WITH", 
        "DEFINED_ON",      
        "DEPENDS_ON",
        "REPRESENTED_BY",  
        "PARTY_TO",        
        "SPECIFIED_IN"     
    ],

    node_properties={
        "Document": ["title", "type"],
        "Clause": ["text"],
        "Person": ["name", "role"],
        "Organization": ["name"],
        "Technology": ["name"],
        "Date": ["value"],
        "Party": ["type"],                   
        "Compensation": ["amount", "currency", "period"]
    },

    relationship_properties={
        "BELONGS_TO": ["section"],
        "DEFINED_ON": ["confidence"],
        "SPECIFIED_IN": ["confidence"]
    }
)


graph = Neo4jGraph()
#graph only contains explicitly stated facts; absence of edges is treated as missing evidence, not model failure
def addInGraph(userid: int):
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))   
    if os.environ.get('SPACE_ID'):
        upload_dir = "/data/upload"
    else:
        upload_dir = os.path.join(BASE_DIR, "upload")
    
    filePath = os.path.join(upload_dir, str(userid), "output.txt")

    try:
        with open(filePath, 'r', encoding='utf-8', errors='ignore') as file:
            document = file.read()
    except FileNotFoundError:
        print(f"Error: The file {filePath} was not found.")
        return
    except Exception as e:
        print(f"An error occurred reading {filePath}: {e}")
        return

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    split_docs = text_splitter.create_documents([document])
    
    logger.info(f"Split document into {len(split_docs)} chunks for graph extraction.")

    try:
        # Process in batches to avoid overwhelming rate limits
        for i, chunk in enumerate(split_docs):
            logger.info(f"Extracting graph nodes for chunk {i+1}/{len(split_docs)}...")
            graph_docs = graphTransformer.convert_to_graph_documents([chunk])
            if graph_docs:
                graph.add_graph_documents(graph_docs, include_source=True)
                logger.info(f"Chunk {i+1} successfully inserted into AuraDB.")
            else:
                logger.warning(f"Chunk {i+1} yielded zero graph elements.")
        logger.info(f"Completed AuraDB ingestion for user {userid}")
    except Exception as e:
        logger.error(f"Failed during AuraDB Graph ingestion: {e}")
    
    
def user_query_to_cypher(user_query: str):
    system_message = SystemMessage(
    content="""
You are a Neo4j Cypher query generator.

Graph schema (STRICT):

Nodes and properties:
- Person(name, role)
- Organization(name)
- Party(type)                 // Employer | Employee
- Document(title, type)
- Clause(text)
- Compensation(amount, currency, period)
- Technology(name)
- Concept(name)
- Date(value)

Relationships:
- (Party)-[:REPRESENTED_BY]->(Person | Organization)
- (Party)-[:PARTY_TO]->(Document)
- (Clause)-[:BELONGS_TO]->(Document)
- (Compensation)-[:SPECIFIED_IN]->(Clause)
- (Clause)-[:DEFINED_ON]->(Date)
- (Document)-[:MENTIONS]->(Concept)
- (Document)-[:USES]->(Technology)
- (Concept)-[:DEPENDS_ON]->(Concept)

IMPORTANT SEMANTIC RULES:
- Prefer structured nodes when available:
  - Use Party for questions about parties, employer, employee
  - Use Compensation for salary / CTC / pay questions
- If Compensation nodes do NOT exist, fallback to searching Clause.text
- Clause.text may still contain raw legal facts

QUERY RULES:
- Use ONLY MATCH and RETURN
- Use ONLY labels, relationships, and properties defined above
- Do NOT invent schema
- Generate READ-ONLY Cypher
- Return ONLY the Cypher query
"""
)

    human_message = HumanMessage(
        content=f"""
Convert the following user question into a Cypher query:

{user_query}
"""
    )

    response = llm.invoke([system_message, human_message])
    cypher = response.content.strip()

    # minimal safety check
    if not cypher.lower().startswith("match"):
        raise ValueError("Unsafe or invalid Cypher generated")

    return cypher


def rewrite_query_on_null(user_query: str, failed_cypher: str):
    system_message = SystemMessage(
        content="""
You are a Cypher query rewriter.

The previous query returned NO RESULTS.

Rewrite the query using FALLBACK RULES:

FALLBACK RULES:
- If Party / Compensation / Date nodes fail, search Clause.text
- Prefer:
  MATCH (c:Clause)-[:BELONGS_TO]->(d:Document)
  WHERE c.text CONTAINS <keyword>
- Do NOT invent schema
- Use only MATCH and RETURN
- Return ONLY Cypher

Graph schema remains STRICT.
"""
    )

    human_message = HumanMessage(
        content=f"""
User question:
{user_query}

Failed Cypher:
{failed_cypher}
"""
    )

    response = llm.invoke([system_message, human_message])
    cypher = response.content.strip()

    if not cypher.lower().startswith("match"):
        raise ValueError("Unsafe rewritten Cypher")

    return cypher


def retrieve(user_query: str):
    cypher_query = user_query_to_cypher(user_query)
    result = graph.query(cypher_query)
    
# sometimes it returns non-empty metadata with no rows so check with len also!!
    if result and len(result) > 0:
        return {
            "mode": "structured",
            "cypher": cypher_query,
            "data": result
        }

    fallback_cypher = rewrite_query_on_null(user_query, cypher_query)
    fallback_result = graph.query(fallback_cypher)

    return {
        "mode": "fallback",
        "cypher": fallback_cypher,
        "data": fallback_result
    }
