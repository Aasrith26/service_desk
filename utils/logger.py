"""
Logging configuration for Clinic Voice Assistant
Provides structured logging with file and console output
"""

import logging
import sys
from pathlib import Path
from config.settings import LOG_LEVEL, LOG_FILE

def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, LOG_LEVEL))
        
        # Ensure log directory exists
        log_path = Path(LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
        
        # File handler (detailed)
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        
        # Custom Safe Stream Handler for Windows Console
        class SafeStreamHandler(logging.StreamHandler):
            def emit(self, record):
                try:
                    msg = self.format(record)
                    stream = self.stream
                    # Write bytes directly to avoid encoding issues
                    stream.buffer.write(msg.encode('utf-8', 'replace') + b'\n')
                    self.flush()
                except Exception:
                    self.handleError(record)

        # Console handler (safe)
        console_handler = SafeStreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, LOG_LEVEL))
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
    
    return logger
