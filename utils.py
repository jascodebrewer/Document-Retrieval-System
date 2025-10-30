import logging
import sys
from pathlib import Path

def setup_logging(output_folder):
    log_file = Path(output_folder) / "app.log"
    
    # Create the output directory if it doesn't exist
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Get the root logger
    logger = logging.getLogger()
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Set the level
    logger.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Create and add file handler
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Create and add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)