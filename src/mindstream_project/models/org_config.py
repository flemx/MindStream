from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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

    @classmethod
    def from_dict(cls, data: dict) -> 'OrgDetails':
        """Create an OrgDetails instance from a dictionary"""
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
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
        return result