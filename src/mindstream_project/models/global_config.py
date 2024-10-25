from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class CrawlerDefaults:
    page_limit: int = 50
    crawl_url: str = ""
    api_key: str = ""
    whitelist: List[str] = None
    additional_params: Dict[str, Any] = None

    def __post_init__(self):
        if self.whitelist is None:
            self.whitelist = []
        if self.additional_params is None:
            self.additional_params = {}

    def to_dict(self) -> dict:
        """Convert CrawlerDefaults instance to a dictionary."""
        return {
            'page_limit': self.page_limit,
            'crawl_url': self.crawl_url,
            'api_key': self.api_key,
            'whitelist': self.whitelist,
            'additional_params': self.additional_params
        }

    def get_api_payload(self) -> dict:
        """Get the complete API payload including additional parameters"""
        payload = {
            "limit": self.page_limit,
            "url": self.crawl_url,
            "whitelist": self.whitelist,
            "return_format": "raw",
            "request": "smart_mode",
            "metadata": True,
            "respect_robots": False,
            "readability": True,
            **self.additional_params
        }
        return payload

@dataclass
class IngestorDefaults:
    object_api_name: str = 'Document'
    source_name: str = 'mindstream_data'
    max_concurrent_jobs: int = 5

    def to_dict(self) -> dict:
        """Convert IngestorDefaults instance to a dictionary."""
        return {
            'object_api_name': self.object_api_name,
            'source_name': self.source_name,
            'max_concurrent_jobs': self.max_concurrent_jobs
        }

@dataclass
class GlobalConfig:
    current_org: Optional[str]
    crawler: CrawlerDefaults
    ingestor: IngestorDefaults

    @classmethod
    def from_dict(cls, data: dict) -> 'GlobalConfig':
        crawler = CrawlerDefaults(**data.get('crawler', {}))
        ingestor = IngestorDefaults(**data.get('ingestor', {}))
        return cls(
            current_org=data.get('current_org'),
            crawler=crawler,
            ingestor=ingestor
        )

    def to_dict(self) -> dict:
        """Convert GlobalConfig instance to a dictionary."""
        return {
            'current_org': self.current_org,
            'crawler': self.crawler.to_dict(),
            'ingestor': self.ingestor.to_dict()
        }
