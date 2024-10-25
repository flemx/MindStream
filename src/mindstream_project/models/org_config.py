from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from mindstream_project.models.global_config import CrawlerDefaults, IngestorDefaults

@dataclass
class OrgDetails:
    username: str
    instance_url: str
    login_url: str
    org_id: str
    alias: Optional[str] = None
    consumer_key: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Add new fields using the same dataclasses as GlobalConfig
    crawler: Optional[CrawlerDefaults] = None
    ingestor: Optional[IngestorDefaults] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'OrgDetails':
        """Create an OrgDetails instance from a dictionary"""
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            
        # Convert crawler and ingestor settings to their respective dataclasses
        if 'crawler' in data:
            data['crawler'] = CrawlerDefaults(**data['crawler'])
        if 'ingestor' in data:
            data['ingestor'] = IngestorDefaults(**data['ingestor'])
            
        return cls(**data)

    def to_dict(self) -> dict:
        """Convert the instance to a dictionary"""
        result = {
            'username': self.username,
            'instance_url': self.instance_url,
            'login_url': self.login_url,
            'org_id': self.org_id,
            'alias': self.alias,
            'consumer_key': self.consumer_key
        }
        if self.created_at:
            result['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            result['updated_at'] = self.updated_at.isoformat()
        if self.crawler:
            result['crawler'] = self.crawler.to_dict()
        if self.ingestor:
            result['ingestor'] = self.ingestor.to_dict()
        return result
