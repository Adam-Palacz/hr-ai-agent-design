"""Logging configuration."""
import logging
import sys
from pathlib import Path
from typing import Optional

from config.settings import settings


def setup_logger(
    name: str = "cv_parser",
    log_level: Optional[str] = None,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    Set up and configure logger.
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set log level
    level = log_level or settings.log_level
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Default logger instance
logger = setup_logger()

