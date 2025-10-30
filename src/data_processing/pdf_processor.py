from docling.document_converter import DocumentConverter
from pathlib import Path
import sys
import logging

# Initialize logging for this module
logger=logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, output_folder):
        # Folder Configurations
        self.markdown_folder=Path(output_folder) / "markdown"
        self.markdown_folder.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        

    def convert_to_markdown(self, pdf_path):
        """Convert PDF to markdown using Docling and return the Markdown file path (in markdown/ subfolder)."""
        try:
            self.logger.info(f"Starting Docling conversion for: {pdf_path}")
            converter=DocumentConverter()
            result=converter.convert(str(pdf_path))

            # Enhanced markdown export with page breaks and formatting options
            markdown_output = result.document.export_to_markdown(
                    page_break_placeholder="<!-- Page Break -->",
                    image_placeholder="<!-- image -->",
                    enable_chart_tables=True,
                    indent=4,
                )
            
            # In Docling's markdown "Page Numbers" are missing
            # Adding page numbers
            lines=markdown_output.split("<!-- Page Break -->")
            numbered_output=''
            for i, segment in enumerate(lines, 1):
                if segment.strip():
                    numbered_output+=f'\n\n# Page {i}\n\n {segment.strip()}\n'

            # Saving this output to a folder
            md_path = self.markdown_folder/f'{Path(pdf_path).stem}.md'
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(numbered_output)
            
            self.logger.info(f"Successfully converted to Markdown with page numbers: {md_path}")
            return md_path
        except Exception as e:
            logging.error(f"Error converting {pdf_path} to Markdown: {e}")
            raise
        