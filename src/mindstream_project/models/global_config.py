from dataclasses import dataclass
from typing import List, Optional

@dataclass
class GlobalDefaults:
    page_limit: int = 50
    object_api_name: str = 'Document'
    source_name: str = 'mindstream_data'
    max_concurrent_jobs: int = 5
    crawl_url: str = ""
    api_key: str = ""
    whitelist: List[str] = None

    def __post_init__(self):
        if self.whitelist is None:
            self.whitelist = []

    def to_dict(self) -> dict:
        """Convert GlobalDefaults instance to a dictionary."""
        return {
            'page_limit': self.page_limit,
            'object_api_name': self.object_api_name,
            'source_name': self.source_name,
            'max_concurrent_jobs': self.max_concurrent_jobs,
            'crawl_url': self.crawl_url,
            'api_key': self.api_key,
            'whitelist': self.whitelist
        }

@dataclass
class GlobalConfig:
    current_org: Optional[str]
    defaults: GlobalDefaults

    @classmethod
    def from_dict(cls, data: dict) -> 'GlobalConfig':
        defaults = GlobalDefaults(**data.get('defaults', {}))
        return cls(
            current_org=data.get('current_org'),
            defaults=defaults
        )

    def to_dict(self) -> dict:
        """Convert GlobalConfig instance to a dictionary."""
        return {
            'current_org': self.current_org,
            'defaults': self.defaults.to_dict() if self.defaults else None
        }
