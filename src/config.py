"""Configuration management for the analysis project."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any

# Load environment variables (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, continue without it
    pass


class Config:
    """Configuration manager for the project."""
    
    def __init__(self, config_path: str = None):
        """Initialize configuration from YAML file and environment variables."""
        if config_path is None:
            # Try to find config.yaml relative to project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._apply_env_overrides()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            # Return default config if file doesn't exist
            return self._default_config()
        
        with open(self.config_path, 'r') as f:
            loaded = yaml.safe_load(f)
            if loaded is None:
                return self._default_config()
            return loaded
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            'data_collection': {
                'github': {
                    'repository': {
                        'owner': 'bitcoin',
                        'name': 'bitcoin'
                    },
                    'batch_size': 100,
                    'rate_limit_buffer': 0.9
                },
                'mailing_lists': {
                    'bitcoin_dev': {
                        'archive_url': 'https://lists.linuxfoundation.org/pipermail/bitcoin-dev/'
                    },
                    'bitcoin_core_dev': {
                        'archive_url': 'https://lists.linuxfoundation.org/pipermail/bitcoin-core-dev/'
                    }
                },
                'luke_case': {
                    'date_range': {
                        'start': '2022-06-01',
                        'end': '2023-06-01'
                    },
                    'keywords': ['maintainer', 'Luke', 'Dashjr', 'access', 'remove', 'revoke']
                }
            },
            'paths': {
                'data': 'data',
                'analysis': 'analysis',
                'visualizations': 'visualizations',
                'findings': 'findings'
            }
        }
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to config."""
        # GitHub token
        if os.getenv('GITHUB_TOKEN'):
            if 'data_collection' not in self.config:
                self.config['data_collection'] = {}
            if 'github' not in self.config['data_collection']:
                self.config['data_collection']['github'] = {}
            self.config['data_collection']['github']['token'] = os.getenv('GITHUB_TOKEN')
        
        # Data directories
        if os.getenv('DATA_DIR'):
            self.config['paths'] = self.config.get('paths', {})
            self.config['paths']['data'] = os.getenv('DATA_DIR')
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated path.
        
        Example: config.get('data_collection.github.batch_size')
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_path(self, key_path: str, default: str = None) -> Path:
        """Get a path configuration value as a Path object."""
        path_str = self.get(key_path, default)
        if path_str:
            return Path(path_str)
        return None
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate configuration.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required paths
        required_paths = ['paths.data', 'paths.analysis', 'paths.visualizations']
        for path_key in required_paths:
            if not self.get(path_key):
                errors.append(f"Missing required path configuration: {path_key}")
        
        # Check GitHub config
        if not self.get('data_collection.github.repository.owner'):
            errors.append("Missing GitHub repository owner")
        if not self.get('data_collection.github.repository.name'):
            errors.append("Missing GitHub repository name")
        
        # Check batch size is reasonable
        batch_size = self.get('data_collection.github.batch_size', 100)
        if batch_size < 1 or batch_size > 1000:
            errors.append(f"GitHub batch_size must be between 1 and 1000, got {batch_size}")
        
        # Check rate limit buffer
        rate_buffer = self.get('data_collection.github.rate_limit_buffer', 0.9)
        if rate_buffer <= 0 or rate_buffer > 1:
            errors.append(f"rate_limit_buffer must be between 0 and 1, got {rate_buffer}")
        
        return len(errors) == 0, errors


# Global config instance
config = Config()

