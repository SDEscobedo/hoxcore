# src/hxc/utils/helpers.py
"""
Helper utilities for HXC
"""
import os
import logging
from typing import Optional


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Set up logging for the application
    
    Args:
        verbose: Whether to enable verbose logging
        
    Returns:
        Logger instance
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    logger = logging.getLogger('hxc')
    logger.setLevel(log_level)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def get_project_root(start_dir: Optional[str] = None) -> Optional[str]:
    """
    Find the project root directory by looking for a specific marker file/directory
    
    Args:
        start_dir: Starting directory (defaults to current directory)
        
    Returns:
        Project root directory path or None if not found
    """
    current_dir = os.path.abspath(start_dir or os.getcwd())
    
    # Look for .hxc directory as a marker
    marker = '.hxc'
    
    while True:
        if os.path.exists(os.path.join(current_dir, marker)):
            return current_dir
        
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:  # Reached filesystem root
            return None
            
        current_dir = parent_dir