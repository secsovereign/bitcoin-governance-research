"""Logging utilities."""

import logging
import sys
import os
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "bitcoin_governance_analysis",
    log_level: str = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with console and optional file output.
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). If None, uses env var or defaults to INFO
        log_file: Optional path to log file. If None, uses default from config
    
    Returns:
        Configured logger instance
    """
    # Get log level from env or config
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler (if specified or from config)
    if log_file is None:
        log_file = os.getenv('LOG_FILE')
        if log_file:
            log_path = Path(log_file)
        else:
            # Default to logs directory in project root
            project_root = Path(__file__).parent.parent.parent
            logs_dir = project_root / 'logs'
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_path = logs_dir / f"{name}.log"
    else:
        log_path = Path(log_file)
    
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    return logger

