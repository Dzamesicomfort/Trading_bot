#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logger Setup

This module provides functionality for setting up logging in the trading bot.
"""

import os
import sys
from pathlib import Path

from loguru import logger


def setup_logger(log_level: str = "INFO", log_file: str = None, file_enabled: bool = True) -> None:
    """
    Set up the logger for the trading bot.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
        file_enabled: Whether to enable file logging
    """
    # Remove default logger
    logger.remove()
    
    # Add console logger
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Add file logger if enabled
    if file_enabled and log_file:
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # Add file logger with rotation
        logger.add(
            log_file,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="1 day",  # Rotate logs daily
            retention="30 days",  # Keep logs for 30 days
            compression="zip"  # Compress rotated logs
        )
    
    logger.info(f"Logger initialized with level {log_level}")
    if file_enabled and log_file:
        logger.info(f"File logging enabled at {log_file}")