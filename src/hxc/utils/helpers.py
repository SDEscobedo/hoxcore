"""
Helper utilities for HXC
"""
import os
import logging
from pathlib import Path
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
    current_dir = Path(start_dir or os.getcwd()).resolve()
    
    # Look for .hxc directory as a marker
    marker = '.hxc'
    
    # Also check for the registry structure
    registry_markers = ["config.yml", "programs", "projects", "missions", "actions"]
    
    while True:
        # Check for .hxc directory marker
        if (current_dir / marker).exists() and (current_dir / marker).is_dir():
            return str(current_dir)
            
        # Check for the registry structure
        if all((current_dir / rm).exists() for rm in registry_markers):
            return str(current_dir)
        
        parent_dir = current_dir.parent
        if parent_dir == current_dir:  # Reached filesystem root
            return None
            
        current_dir = parent_dir


def is_valid_registry(path: str) -> bool:
    """
    Check if the given path is a valid HXC registry
    
    Args:
        path: Path to check
        
    Returns:
        True if path is a valid registry, False otherwise
    """
    registry_path = Path(path)
    
    # Check for required directories and files
    required_paths = [
        registry_path / "config.yml",
        registry_path / "programs",
        registry_path / "projects",
        registry_path / "missions",
        registry_path / "actions"
    ]
    
    return all(p.exists() for p in required_paths)