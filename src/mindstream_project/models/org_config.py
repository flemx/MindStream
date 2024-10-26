from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from mindstream_project.utils.logging_config import get_logger, log_function_call
import logging

from mindstream_project.models.global_config import CrawlerDefaults, IngestorDefaults

logger = logging.getLogger(__name__)

@dataclass
class OrgDetails:
    username: str
    instance_url: str
    org_id: str
    login_url: str = "https://login.salesforce.com"  # Default value
    alias: Optional[str] = None
    consumer_key: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    crawler: Optional[CrawlerDefaults] = None
    ingestor: Optional[IngestorDefaults] = None

    @classmethod
    @log_function_call
    def from_dict(cls, data: dict) -> 'OrgDetails':
        """Create an OrgDetails instance from a dictionary"""
        logger.debug(f"Creating OrgDetails from dictionary: {data}")
        
        try:
            # Handle datetime conversions
            if 'created_at' in data and isinstance(data['created_at'], str):
                logger.debug(f"Converting created_at from string: {data['created_at']}")
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            
            if 'updated_at' in data and isinstance(data['updated_at'], str):
                logger.debug(f"Converting updated_at from string: {data['updated_at']}")
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            
            # Convert crawler and ingestor settings
            if 'crawler' in data:
                logger.debug("Converting crawler settings to CrawlerDefaults")
                data['crawler'] = CrawlerDefaults(**data['crawler'])
            
            if 'ingestor' in data:
                logger.debug("Converting ingestor settings to IngestorDefaults")
                data['ingestor'] = IngestorDefaults(**data['ingestor'])
            
            instance = cls(**data)
            logger.debug(f"Successfully created OrgDetails instance: {instance}")
            return instance
            
        except Exception as e:
            logger.error(f"Error creating OrgDetails from dictionary: {str(e)}")
            raise

    @log_function_call
    def to_dict(self) -> dict:
        """Convert the instance to a dictionary"""
        logger.debug(f"Converting OrgDetails to dictionary for username: {self.username}")
        
        try:
            result = {
                'username': self.username,
                'instance_url': self.instance_url,
                'login_url': self.login_url,
                'org_id': self.org_id,
                'alias': self.alias,
                'consumer_key': self.consumer_key
            }
            
            # Add optional datetime fields if present
            if self.created_at:
                logger.debug(f"Including created_at: {self.created_at}")
                result['created_at'] = self.created_at.isoformat()
            
            if self.updated_at:
                logger.debug(f"Including updated_at: {self.updated_at}")
                result['updated_at'] = self.updated_at.isoformat()
            
            # Add optional configuration objects if present
            if self.crawler:
                logger.debug("Including crawler configuration")
                result['crawler'] = self.crawler.to_dict()
            
            if self.ingestor:
                logger.debug("Including ingestor configuration")
                result['ingestor'] = self.ingestor.to_dict()
            
            logger.debug(f"Successfully converted OrgDetails to dictionary: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error converting OrgDetails to dictionary: {str(e)}")
            raise

    def __post_init__(self):
        """Validate the OrgDetails instance after initialization"""
        logger.debug(f"Validating OrgDetails instance for username: {self.username}")
        
        # Validate required fields
        if not self.username:
            logger.error("Username cannot be empty")
            raise ValueError("Username cannot be empty")
        
        if not self.instance_url:
            logger.debug(f"Instance URL is empty for username: {self.username}")
        
        if not self.login_url:
            logger.debug(f"Login URL is empty for username: {self.username}")
        
        if not self.org_id:
            logger.debug(f"Org ID is empty for username: {self.username}")
        
        logger.debug("OrgDetails instance validation completed successfully")
