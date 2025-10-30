from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from pathlib import Path
import logging
import re
import json

# Initialize logger for this module
logger=logging.getLogger(__name__)

class DocumentChunking:
    '''
    Document chunking class for intelligent text splitting strategies.

    1. Header-based splitting: Splits documents by markdown headers (##)
    2. Character-based splitting: Further splits header sections into smaller chunks
    '''
    def __init__(self, output_folder):
        # Define output directories for different split types
        self.header_splits_folder=Path(output_folder) / "doc_header_splits"
        self.char_splits_folder=Path(output_folder) / "doc_char_splits"
        self.logger=logger
        # Make sure output folders exist
        self.header_splits_folder.mkdir(parents=True, exist_ok=True)
        self.char_splits_folder.mkdir(parents=True, exist_ok=True)

    def doc_header_split(self, md_path):
        '''
        Split markdown document by headers to create semantic sections.
        '''
        self.logger.info(f"Creating splits based on headings for: {md_path}")
        # Load the markdown document
        with open(md_path, 'r', encoding='utf-8') as f:
            markdown_document=f.read()

        # Define header hierarchy for splitting
        # Currently splitting on ## headers (level 2 headers)
        headers_to_split_on = [
            ("##", "Header 1"),
        ]

        # Initialize markdown header splitter
        # strip_headers=False preserves header
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on, strip_headers=False
        )
        # Perform header-based splitting
        md_header_splits = markdown_splitter.split_text(markdown_document)
        self.logger.info(f"Completed header split: {len(md_header_splits)} chunks created.")
        return md_header_splits

    def doc_chunk_splits(self, header_splits, chunk_size=1000, chunk_overlap=100):
        self.logger.info(f"Starting chunk splits with chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
        
        # Page number detection and metadata enhancement
        # This preserves page information across chunks for better source attribution
        page_name = None
        for doc in header_splits:
            # Look inside the text content for a page header
            match = re.search(r'#\s*Page\s*(\d+)', doc.page_content)

            if match:
                # If found, update current page name
                page_name = f"Page {match.group(1)}"
                doc.metadata["Page"] = page_name
            else:
                # Otherwise, inherit from previous document
                doc.metadata["Page"] = page_name
        
        # Initialize recursive character text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        # header_splits is list of Document objects
        # Apply character-based splitting to header-split documents
        chunked_docs = text_splitter.split_documents(header_splits)
        self.logger.info(f"Completed chunk splitting: {len(chunked_docs)} chunks created.")
        return chunked_docs

    def save_splits_jsonl(self, documents, filename, folder_path: Path):
        '''
        Save document chunks to JSONL format for persistence and analysis.
        '''
        save_path = folder_path / filename
        # Write documents to JSON format
        with open(save_path, "w", encoding="utf-8") as f:
            for doc in documents:
                # Only include fields that have values
                data = {
                    "page_content": doc.page_content,  # The actual text content
                    "metadata": doc.metadata
                }
                if getattr(doc, "id", None):  # only add ID if exists and not None
                    data["id"] = doc.id
                # Write each document as a separate JSON line
                f.write(json.dumps(data) + "\n")
        self.logger.info(f"Successfully saved documents to {save_path}")
        return save_path