from pathlib import Path
from dotenv import load_dotenv
import os
import logging
import pymongo
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.operations import SearchIndexModel

# Initialize Logging
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

# MongoDB configuration from environment
uri = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION")
INDEX_NAME = os.getenv("MONGO_VECTOR_INDEX")

# Create a new Mongodb client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
db     = client[DB_NAME]
coll   = db[COLLECTION_NAME]

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# Create vector search index
def create_vector_index():
    """Create MongoDB Atlas vector search index for semantic search."""
    vector_index = SearchIndexModel(
        definition={
            "fields": [
                # ---------- VECTOR ----------
                {
                    "type": "vector",
                    "path": "embedding",          
                    "numDimensions": 768,         
                    "similarity": "cosine"
                },

                # ---------- METADATA FILTERS ----------
                {
                    "type": "filter",
                    "path": "metadata.Header 1"   # top-level section title
                },
                {
                    "type": "filter",
                    "path": "metadata.Page"       # page number 
                },
                {
                    "type": "filter",
                    "path": "metadata.source"     # PDF filename 
                }
            ]
        },
        name=INDEX_NAME,
        type="vectorSearch"
    )
    # Check if index already exists
    existing_indexes=[idx["name"] for idx in coll.list_search_indexes()]
    if INDEX_NAME not in existing_indexes:
        logger.info(f"Creating vector index '{INDEX_NAME}'...")
        coll.create_search_indexes([vector_index])
    else:
        logger.info(f"Vector index '{INDEX_NAME}' already exists.")

# Adding Data to MongoDB
def upsert_data(chunks, vectors, pdf_path):
    """Store document chunks with embeddings in MongoDB using upsert operation."""
    # Ensure pdf_path is a Path object
    if isinstance(pdf_path, str):
        pdf_path = Path(pdf_path)
    docs_to_insert=[]
    for chunk, vector in zip(chunks, vectors):
        doc={
            "text": chunk.page_content,
            "embedding": vector,
            "metadata":{
                "source":pdf_path.name,
                "page": chunk.metadata.get("Page", None),
                "header": chunk.metadata.get("Header 1", None),
                "chunk_id":f"{pdf_path.stem}_{hash(chunk.page_content)}"
            }
        }
        docs_to_insert.append(doc)

    # Bulk upsert operation (insert new or update existing)
    if docs_to_insert:
        result=coll.bulk_write([
            pymongo.ReplaceOne(
                {"metadata.chunk_id":doc["metadata"]["chunk_id"]},
                doc,
                upsert=True
            ) for doc in docs_to_insert
        ])
        logger.info(f"Upserted {result.upserted_count + result.modified_count} chunks.")
    else:
        logger.info("No chunks to upsert.")

def search_result_for_llm(query, top_k, embeddings):
    """Perform vector search and return formatted context for LLM."""
    # Convert query to embedding vector
    query_emb=embeddings.embed_query(query)
    # MongoDB aggregation pipeline for vector search
    pipeline=[
        {
            "$vectorSearch":{
                "index": INDEX_NAME,
                "path": "embedding",
                "queryVector": query_emb,
                "numCandidates": top_k * 20, # Search more candidates for better results
                "limit": top_k
            }
        },
        {
            "$project":
            {
                "text":1,
                "metadata":1,
                "_id":0,
                "score": { "$meta": "vectorSearchScore" }, # Include similarity score

            }
        }
    ]
    # Execute search and format results
    results=coll.aggregate(pipeline)
    context=[]
    for i, result in enumerate(results, 1):
        page=result['metadata'].get("page", "Unknown")
        text=result['text'].strip()
        source = result['metadata'].get("source", "Unknown")
        header = result['metadata'].get("header", "Unknown")
        context.append(f"[{i}] {source} | {header} | {page}:{text} ")
    logger.info(f"Search result for LLM:\n" + "\n\n".join(context))
    return "\n\n".join(context)