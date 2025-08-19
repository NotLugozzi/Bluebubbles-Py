"""
Configuration Manager
Handles loading and saving configuration from/to bb.toml in user's config directory
"""

import os
import toml
from pathlib import Path
from typing import Dict, Optional, Any

class ConfigManager:
    """Manages application configuration stored in bb.toml."""
    
    def __init__(self):
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "bb.toml"
        self._config_data = {}
        self._load_config()
    
    def _get_config_dir(self) -> Path:
        """Get the user's configuration directory."""
        # Use XDG_CONFIG_HOME if set, otherwise default to ~/.config
        config_home = os.environ.get('XDG_CONFIG_HOME')
        if config_home:
            return Path(config_home) / "bluebubbles"
        else:
            return Path.home() / ".config" / "bluebubbles"
    
    def _load_config(self):
        """Load configuration from bb.toml file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config_data = toml.load(f)
            except (toml.TomlDecodeError, IOError) as e:
                # print(f"Error loading config: {e}")
                self._config_data = {}
        else:
            self._config_data = {}
    
    def _save_config(self):
        """Save current configuration to bb.toml file."""
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                toml.dump(self._config_data, f)
        except IOError as e:
            # print(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        keys = key.split('.')
        value = self._config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set a configuration value."""
        keys = key.split('.')
        config = self._config_data
        
        # Navigate to the parent of the final key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the final value
        config[keys[-1]] = value
        self._save_config()
    
    def has_valid_config(self) -> bool:
        """Check if we have a valid configuration for connecting to BlueBubbles."""
        server_url = self.get('server.url')
        password = self.get('server.password')
        
        return bool(server_url and password)
    
    def get_server_config(self) -> Dict[str, Optional[str]]:
        """Get server configuration."""
        return {
            'url': self.get('server.url'),
            'password': self.get('server.password')
        }
    
    def set_server_config(self, url: str, password: str):
        """Set server configuration."""
        self.set('server.url', url)
        self.set('server.password', password)
    
    def clear_server_config(self):
        """Clear server configuration."""
        if 'server' in self._config_data:
            del self._config_data['server']
            self._save_config()
    
    def get_appearance_config(self) -> Dict[str, Any]:
        """Get appearance configuration."""
        return {
            'dark_mode': self.get('appearance.dark_mode', False),
            'text_width': self.get('appearance.text_width', 80)
        }
    
    def set_appearance_config(self, dark_mode: bool = None, text_width: int = None):
        """Set appearance configuration."""
        if dark_mode is not None:
            self.set('appearance.dark_mode', dark_mode)
        if text_width is not None:
            self.set('appearance.text_width', text_width)
    
    def get_text_width(self) -> int:
        """Get the text width preference."""
        return self.get('appearance.text_width', 80)
    
    def get_api_method(self) -> str:
        """Get the API method preference (applescript or private)."""
        return self.get('advanced.api_method', 'applescript')
    
    def set_api_method(self, method: str):
        """Set the API method preference."""
        if method not in ['applescript', 'private']:
            raise ValueError("API method must be 'applescript' or 'private'")
        self.set('advanced.api_method', method)
