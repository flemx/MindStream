import logging
import sys
from pathlib import Path
from typing import Optional
from functools import wraps

# Create logger
logger = logging.getLogger('mindstream')
logger.setLevel(logging.INFO)

# Create formatters
default_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
debug_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)

def setup_logging(debug: bool = False, log_file: Optional[Path] = None):
    """Configure logging settings globally
    
    Args:
        debug: Enable debug logging if True
        log_file: Optional path to log file
    """
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Set log level based on debug flag
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(debug_formatter if debug else default_formatter)
    logger.addHandler(console_handler)
    
    # File handler if log_file is provided
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(debug_formatter if debug else default_formatter)
        logger.addHandler(file_handler)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(f'mindstream.{name}')

def log_function_call(func):
    """Decorator to log function entry and exit"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_logger = get_logger(func.__module__)
        func_logger.debug(f"Entering {func.__name__}")
        try:
            result = func(*args, **kwargs)
            func_logger.debug(f"Exiting {func.__name__}")
            return result
        except Exception as e:
            func_logger.exception(f"Exception in {func.__name__}: {str(e)}")
            raise
    return wrapper