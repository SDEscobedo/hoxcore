"""
Configuration management for HXC
"""
import os
import json
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Configuration manager for HXC"""
    
    DEFAULT_CONFIG_DIR = '~/.hxc'
    DEFAULT_CONFIG_FILE = 'config.json'
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            config_dir: Configuration directory (uses DEFAULT_CONFIG_DIR if not specified)
        """
        self.config_dir = Path(config_dir or self.DEFAULT_CONFIG_DIR).expanduser()
        self.config_file = self.config_dir / self.DEFAULT_CONFIG_FILE
        self._config_cache: Optional[Dict[str, Any]] = None
    
    def ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists"""
        os.makedirs(self.config_dir, exist_ok=True)
    
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from file
        
        Returns:
            Configuration dictionary
        """
        if self._config_cache is not None:
            return self._config_cache
            
        if not self.config_file.exists():
            self._config_cache = {}
            return {}
            
        try:
            with open(self.config_file, 'r') as f:
                self._config_cache = json.load(f)
                return self._config_cache
        except (json.JSONDecodeError, IOError):
            self._config_cache = {}
            return {}
    
    def save(self, config: Dict[str, Any]) -> None:
        """
        Save configuration to file
        
        Args:
            config: Configuration dictionary
        """
        self.ensure_config_dir()
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        self._config_cache = config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        config = self.load()
        return config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        config = self.load()
        config[key] = value
        self.save(config)