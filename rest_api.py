import shutil
from src.llm_client.gemini_llm import get_answer, get_google_llm, get_prompt_template
from src.database.mongo_utils import create_vector_index, search_result_for_llm, upsert_data
from src.data_processing.pdf_processor import DocumentProcessor
from src.chunking.data_chunking import DocumentChunking
from pathlib import Path
from src.llm_client.google_embedder import get_google_embeddings
from utils import setup_logging
from fastapi import FastAPI, UploadFile, HTTPException
import os
from pydantic import BaseModel
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# Configuration paths
pdf_folder = Path('data')
output_folder = Path('output')
prompt_path='src/prompts/llm_prompt.txt'

# Initialize logging system
setup_logging(output_folder=output_folder)

# Initialize Google embeddings client (used for vector search)
embeddings=get_google_embeddings()

# Create FastAPI application
app = FastAPI(title="Task Rest APIs",
              description="APIS for the Task",)


@app.get("/")
async def root():
    return {"message": "Welcome to Task Rest APIs! Visit /docs to view the interactive API documentation"}

@app.post("/upload")
async def upload_file(file: UploadFile):
    '''
    Upload and process PDF files

    Pipeline Steps:
    1. Validate PDF file format
    2. Save file to data directory
    3. Convert PDF to markdown using Docling (CPU-intensive)
    4. Split document by headers and characters
    5. Generate embeddings for each chunk
    6. Store in MongoDB with vector search index
    '''
    try:
        # Check the file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only pdf file allowed")
        # Ensure data folder exists
        if not os.path.exists(pdf_folder):
            os.makedirs(pdf_folder, exist_ok=True)

        # Save uploaded file to data directory
        file_path=os.path.join(pdf_folder, file.filename)
        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        pdf_stem = Path(file_path).stem 
        
        # Step 1: Convert PDF to markdown using Docling
        processor=DocumentProcessor(output_folder=output_folder)
        md_path=processor.convert_to_markdown(pdf_path=file_path)

        # Step 2: Intelligent document chunking
        # First split by headers, then by character chunks for optimal retrieval 
        chunker=DocumentChunking(output_folder=output_folder)
        doc_header_splits=chunker.doc_header_split(md_path=md_path)
        doc_char_splits=chunker.doc_chunk_splits(header_splits=doc_header_splits)
        

        # Step 3: Saving these splits in the output folder for future use (if any)
        header_filename = f"{pdf_stem}_header_splits.jsonl"
        char_filename = f"{pdf_stem}_char_splits.jsonl"

        header_splits_path=chunker.save_splits_jsonl(documents=doc_header_splits,
                            filename=header_filename, folder_path=chunker.header_splits_folder)
        char_splits_path=chunker.save_splits_jsonl(documents=doc_char_splits, 
                            filename=char_filename, folder_path=chunker.char_splits_folder)
        
        # Step 4: Generate embeddings for vector search
        # Extract text from the splits for embedding
        docs = [split.page_content for split in doc_char_splits]
        vectors = embeddings.embed_documents(
            docs
        )
        logger.info(f"Generated {len(vectors)} embeddings with dimension {len(vectors[0])}")
        
        # Step 5: Store in MongoDB with vector search capabilities
        create_vector_index() # Ensure vector search index exists
        upsert_data(chunks=doc_char_splits, vectors=vectors, pdf_path=Path(file_path))
        return {
                "message": "File processed successfully",
                "filename": file.filename,
                "embeddings_count": len(vectors),
                "chunks_count": len(doc_char_splits)
            }
    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

class QueryRequest(BaseModel):
    """Request model for user queries"""
    query: str

@app.post('/user_query')
async def ask_llm(request: QueryRequest):
    '''
    Pipeline:
    1. Convert user query to embedding vector
    2. Search MongoDB for relevant document chunks
    3. Use retrieved context with Gemini AI to generate answer
    4. Return answer with source citations
    '''
    try:
        # Step 1: Retrieve relevant context using vector search
        context=search_result_for_llm(query=request.query, top_k=3, embeddings=embeddings)
        
        # Step 2: Initialize Gemini AI model
        llm=get_google_llm()
        
        # Step 3: Load prompt template for structured responses
        prompt=get_prompt_template(prompt_path=prompt_path)
        
        # Step 4: Generate answer using retrieved context
        response=get_answer(query=request.query, llm=llm, prompt=prompt, content=context)
        
        return {'answer': response}
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")
