from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
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
    access_token: Optional[str] = None  # Add this field
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    crawler: Optional[CrawlerDefaults] = None
    ingestor: Optional[IngestorDefaults] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OrgDetails':
        if not data:
            return cls(username="", instance_url="", login_url="", org_id="")
        
        # Initialize default configurations if not present
        crawler_data = data.get('crawler', {})
        ingestor_data = data.get('ingestor', {})
        
        # Create CrawlerDefaults and IngestorDefaults instances
        crawler = CrawlerDefaults.from_dict(crawler_data)
        ingestor = IngestorDefaults.from_dict(ingestor_data)
        
        # Parse datetime strings if present
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        updated_at = datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        
        return cls(
            username=data.get('username', ''),
            instance_url=data.get('instance_url', ''),
            org_id=data.get('org_id', ''),
            login_url=data.get('login_url', 'https://login.salesforce.com'),
            alias=data.get('alias'),
            consumer_key=data.get('consumer_key'),
            access_token=data.get('access_token'),
            created_at=created_at,
            updated_at=updated_at,
            crawler=crawler,
            ingestor=ingestor
        )

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
