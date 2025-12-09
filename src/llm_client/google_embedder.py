from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_google_embeddings(model_id='text-embedding-004'):
    '''
    Initialize Google Generative AI embeddings client.
    '''
    # Get API key from environment variables
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")
    
    # Initialize Google embeddings client with specified model
    # text-embedding-004 provides 768-dimensional vectors for vector search
    embeddings = GoogleGenerativeAIEmbeddings(model=f"models/{model_id}", google_api_key=api_key)
    return embeddings
