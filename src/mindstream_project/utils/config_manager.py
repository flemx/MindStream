import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from mindstream_project.models.org_config import OrgDetails
from mindstream_project.models.global_config import GlobalConfig, GlobalDefaults

class ConfigManager:
    def __init__(self):
        self.base_dir = Path.home() / '.mindstream'
        self.orgs_dir = self.base_dir / 'orgs'
        self.global_config_path = self.base_dir / 'global_config.json'
        
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
        self.base_dir.mkdir(mode=0o700, exist_ok=True)  # Secure permissions
        self.orgs_dir.mkdir(mode=0o700, exist_ok=True)
        
        if not self.global_config_path.exists():
            self._save_json(self.global_config_path, GlobalConfig(None, GlobalDefaults()).to_dict())
            os.chmod(self.global_config_path, 0o600)  # Secure permissions for config file

    def _ensure_default_global_config(self):
        """Ensure default global configuration exists"""
        defaults = GlobalConfig(None, GlobalDefaults())
        
        if not self.global_config_path.exists():
            self._save_json(self.global_config_path, defaults.to_dict())
            os.chmod(self.global_config_path, 0o600)
        else:
            # Update existing config with any missing defaults
            current_config = GlobalConfig.from_dict(self._load_json(self.global_config_path))
            if not current_config.defaults:
                current_config.defaults = defaults.defaults
            else:
                # Ensure new default values are added
                for key, value in defaults.defaults.__dict__.items():
                    if getattr(current_config.defaults, key) is None:
                        setattr(current_config.defaults, key, value)
            self._save_json(self.global_config_path, current_config.to_dict())

    def init_org(self, username: str, org_details: OrgDetails) -> Path:
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
            (org_dir / 'mdapi').mkdir(mode=0o700, exist_ok=True)
            
            # Initialize org config with org details
            config_path = org_dir / 'config.json'
            self._save_json(config_path, org_details.to_dict())
            os.chmod(config_path, 0o600)  # Secure permissions for config file
            
            return org_dir
            
        except Exception as e:
            logging.error(f"Failed to initialize org directory for {username}: {str(e)}")
            raise

    def get_org_path(self, username: str) -> Path:
        """Get the path for an org's directory"""
        return self.orgs_dir / self._sanitize_username(username)

    def set_org_config(self, username: str, config: OrgDetails):
        """Update configuration for a specific org"""
        config_path = self.get_org_path(username) / 'config.json'
        existing_config = OrgDetails.from_dict(self._load_json(config_path)) if config_path.exists() else OrgDetails(username=username, instance_url='', login_url='', org_id='')
        existing_config.updated_at = datetime.now()
        self._save_json(config_path, existing_config.to_dict())

    def get_org_config(self, username: str) -> OrgDetails:
        """Get configuration for a specific org"""
        config_path = self.get_org_path(username) / 'config.json'
        return OrgDetails.from_dict(self._load_json(config_path)) if config_path.exists() else OrgDetails(username=username, instance_url='', login_url='', org_id='')

    def set_default_org(self, username: str):
        """Set the default org in the global config"""
        if not username:
            raise ValueError("Username cannot be empty")
        global_config = self.get_global_config()
        global_config.current_org = username
        self._save_json(self.global_config_path, global_config.to_dict())

    def list_orgs(self) -> Dict[str, OrgDetails]:
        """List all orgs and indicate the default one"""
        orgs = {}
        for org_dir in self.orgs_dir.iterdir():
            if org_dir.is_dir():
                config_path = org_dir / 'config.json'
                if config_path.exists():
                    config = OrgDetails.from_dict(self._load_json(config_path))
                    orgs[config.username] = config
        return orgs

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

    def get_global_config(self) -> GlobalConfig:
        """Get global configuration"""
        return GlobalConfig.from_dict(self._load_json(self.global_config_path))

    def set_global_config(self, config: GlobalConfig):
        """Update global configuration"""
        current_config = self.get_global_config()
        current_config.current_org = config.current_org
        current_config.version = config.version
        current_config.defaults = config.defaults
        self._save_json(self.global_config_path, current_config.to_dict())

    def get_default(self, key: str, default=None):
        """Get a default value from global config"""
        config = self.get_global_config()
        return getattr(config.defaults, key, default)

    def set_default(self, key: str, value):
        """Set a default value in global config"""
        config = self.get_global_config()
        if not hasattr(config.defaults, key):
            raise ValueError(f"Invalid default key: {key}")
        setattr(config.defaults, key, value)
        self._save_json(self.global_config_path, config.to_dict())
