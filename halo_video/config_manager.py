"""
Configuration manager for HALO Video package
Handles API key storage and retrieval
"""
import os
import json
from pathlib import Path
from rich.console import Console

console = Console()

class ConfigManager:
    """Manages configuration for HALO Video CLI"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".halo-video"
        self.config_file = self.config_dir / "config.json"
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist"""
        self.config_dir.mkdir(exist_ok=True)
    
    def has_api_key(self) -> bool:
        """Check if API key is already configured"""
        if not self.config_file.exists():
            return False
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return bool(config.get('gemini_api_key'))
        except (json.JSONDecodeError, FileNotFoundError):
            return False
    
    def get_api_key(self) -> str:
        """Get the stored API key"""
        if not self.config_file.exists():
            raise ValueError("No API key configured. Please run halo-video and enter your API key.")
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                api_key = config.get('gemini_api_key')
                if not api_key:
                    raise ValueError("No API key found in configuration.")
                return api_key
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise ValueError(f"Error reading configuration: {e}")
    
    def save_api_key(self, api_key: str):
        """Save the API key to configuration"""
        config = {}
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            except json.JSONDecodeError:
                config = {}
        
        config['gemini_api_key'] = api_key
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Set restrictive permissions (readable only by user)
        self.config_file.chmod(0o600)
    
    def clear_config(self):
        """Clear all configuration"""
        if self.config_file.exists():
            self.config_file.unlink()
            console.print("[green]✅ Configuration cleared.[/green]")
