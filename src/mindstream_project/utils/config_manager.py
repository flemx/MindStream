import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

class ConfigManager:
    def __init__(self):
        self.base_dir = Path.home() / '.mindstream'
        self.orgs_dir = self.base_dir / 'orgs'
        self.global_config_path = self.base_dir / 'global_config.json'
        self.current_org: Optional[str] = None
        
        try:
            self._ensure_base_structure()
            self._ensure_default_global_config()
        except PermissionError:
            logging.error(f"Permission denied when creating directory structure at {self.base_dir}")
            raise
        except Exception as e:
            logging.error(f"Failed to create directory structure: {str(e)}")
            raise

    def _ensure_base_structure(self):
        """Ensure the base directory structure exists"""
        # Create base directory if it doesn't exist
        self.base_dir.mkdir(mode=0o700, exist_ok=True)  # Secure permissions
        self.orgs_dir.mkdir(mode=0o700, exist_ok=True)
        
        # Create global config if it doesn't exist
        if not self.global_config_path.exists():
            self._save_json(self.global_config_path, {
                'current_org': None,
                'version': '1.0'
            })
            os.chmod(self.global_config_path, 0o600)  # Secure permissions for config file

    def _ensure_default_global_config(self):
        """Ensure default global configuration exists"""
        defaults = {
            'current_org': None,
            'version': '1.0',
            'defaults': {
                'page_limit': 50,
                'object_api_name': 'Document',
                'source_name': 'mindstream_data',
                'max_concurrent_jobs': 5,
                'crawl_url': "",  # Empty default
                'api_key': "",    # Empty default
                'whitelist': []   # Empty default list
            }
        }
        
        if not self.global_config_path.exists():
            self._save_json(self.global_config_path, defaults)
            os.chmod(self.global_config_path, 0o600)
        else:
            # Update existing config with any missing defaults
            current_config = self._load_json(self.global_config_path)
            if 'defaults' not in current_config:
                current_config['defaults'] = defaults['defaults']
            else:
                # Ensure new default values are added
                for key, value in defaults['defaults'].items():
                    if key not in current_config['defaults']:
                        current_config['defaults'][key] = value
            self._save_json(self.global_config_path, current_config)

    def init_org(self, username: str) -> Path:
        """Initialize directory structure for a new org"""
        if not username:
            raise ValueError("Username cannot be empty")
            
        org_dir = self.orgs_dir / self._sanitize_username(username)
        
        try:
            # Create org directory with secure permissions
            org_dir.mkdir(mode=0o700, exist_ok=True)
            
            # Create subdirectories
            (org_dir / 'certificates').mkdir(mode=0o700, exist_ok=True)
            (org_dir / 'csv_files').mkdir(mode=0o700, exist_ok=True)
            (org_dir / 'results').mkdir(mode=0o700, exist_ok=True)
            
            # Initialize org config if it doesn't exist
            config_path = org_dir / 'config.json'
            if not config_path.exists():
                self._save_json(config_path, {
                    'username': username,
                    'access_token': None,
                    'instance_url': None,
                    'consumer_key': None,
                    'created_at': datetime.now().isoformat()
                })
                os.chmod(config_path, 0o600)  # Secure permissions for config file
            
            return org_dir
            
        except Exception as e:
            logging.error(f"Failed to initialize org directory for {username}: {str(e)}")
            raise

    def get_org_path(self, username: str) -> Path:
        """Get the path for an org's directory"""
        return self.orgs_dir / self._sanitize_username(username)

    def set_org_config(self, username: str, config: Dict):
        """Update configuration for a specific org"""
        config_path = self.get_org_path(username) / 'config.json'
        existing_config = self._load_json(config_path) if config_path.exists() else {}
        existing_config.update(config)
        existing_config['updated_at'] = datetime.now().isoformat()
        self._save_json(config_path, existing_config)

    def get_org_config(self, username: str) -> Dict:
        """Get configuration for a specific org"""
        config_path = self.get_org_path(username) / 'config.json'
        return self._load_json(config_path) if config_path.exists() else {}

    @staticmethod
    def _save_json(path: Path, data: Dict):
        """Save data to JSON file"""
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def _load_json(path: Path) -> Dict:
        """Load data from JSON file"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            logging.error(f"Error reading config file {path}: {str(e)}")
            return {}

    @staticmethod
    def _sanitize_username(username: str) -> str:
        """Sanitize username for use in filesystem paths"""
        return username.replace('@', '_at_').replace('.', '_dot_')

    def get_global_config(self) -> Dict:
        """Get global configuration"""
        return self._load_json(self.global_config_path)

    def set_global_config(self, config: Dict):
        """Update global configuration"""
        current_config = self.get_global_config()
        current_config.update(config)
        self._save_json(self.global_config_path, current_config)

    def get_default(self, key: str, default=None):
        """Get a default value from global config"""
        config = self.get_global_config()
        return config.get('defaults', {}).get(key, default)

    def set_default(self, key: str, value):
        """Set a default value in global config"""
        config = self.get_global_config()
        if 'defaults' not in config:
            config['defaults'] = {}
        config['defaults'][key] = value
        self._save_json(self.global_config_path, config)
