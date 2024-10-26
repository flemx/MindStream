from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from mindstream_project.utils.logging_config import get_logger, log_function_call

logger = get_logger(__name__)

@dataclass
class CrawlerDefaults:
    page_limit: int = 50
    crawl_url: str = ""
    api_key: str = ""
    whitelist: List[str] = None
    additional_params: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values for None fields"""
        logger.debug("Initializing CrawlerDefaults")
        if self.whitelist is None:
            logger.debug("Setting default empty whitelist")
            self.whitelist = []
        if self.additional_params is None:
            logger.debug("Setting default empty additional_params")
            self.additional_params = {}

    @log_function_call
    def to_dict(self) -> dict:
        """Convert CrawlerDefaults instance to a dictionary."""
        logger.debug("Converting CrawlerDefaults to dictionary")
        result = {
            'page_limit': self.page_limit,
            'crawl_url': self.crawl_url,
            'api_key': '***' if self.api_key else '',  # Mask API key in logs
            'whitelist': self.whitelist,
            'additional_params': self.additional_params
        }
        logger.debug(f"CrawlerDefaults dictionary (with masked api_key): {result}")
        return result

    @log_function_call
    def get_api_payload(self) -> dict:
        """Get the complete API payload including additional parameters"""
        logger.debug("Building API payload")
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
        logger.debug(f"Created API payload (with masked sensitive data): {payload}")
        return payload

@dataclass
class IngestorDefaults:
    object_api_name: str = 'Document'
    source_name: str = 'mindstream_data'
    max_concurrent_jobs: int = 5

    @log_function_call
    def to_dict(self) -> dict:
        """Convert IngestorDefaults instance to a dictionary."""
        logger.debug(f"Converting IngestorDefaults to dictionary for object: {self.object_api_name}")
        result = {
            'object_api_name': self.object_api_name,
            'source_name': self.source_name,
            'max_concurrent_jobs': self.max_concurrent_jobs
        }
        logger.debug(f"Created IngestorDefaults dictionary: {result}")
        return result

@dataclass
class GlobalConfig:
    current_org: Optional[str]
    crawler: CrawlerDefaults
    ingestor: IngestorDefaults

    @classmethod
    @log_function_call
    def from_dict(cls, data: dict) -> 'GlobalConfig':
        """Create a GlobalConfig instance from a dictionary."""
        logger.debug("Creating GlobalConfig from dictionary")
        try:
            logger.debug("Processing crawler configuration")
            crawler = CrawlerDefaults(**data.get('crawler', {}))
            
            logger.debug("Processing ingestor configuration")
            ingestor = IngestorDefaults(**data.get('ingestor', {}))
            
            logger.debug(f"Creating GlobalConfig with current_org: {data.get('current_org')}")
            instance = cls(
                current_org=data.get('current_org'),
                crawler=crawler,
                ingestor=ingestor
            )
            logger.debug("Successfully created GlobalConfig instance")
            return instance
            
        except Exception as e:
            logger.error(f"Error creating GlobalConfig from dictionary: {str(e)}")
            raise

    @log_function_call
    def to_dict(self) -> dict:
        """Convert GlobalConfig instance to a dictionary."""
        logger.debug("Converting GlobalConfig to dictionary")
        try:
            result = {
                'current_org': self.current_org,
                'crawler': self.crawler.to_dict(),
                'ingestor': self.ingestor.to_dict()
            }
            logger.debug(f"Created GlobalConfig dictionary: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error converting GlobalConfig to dictionary: {str(e)}")
            raise

    def __post_init__(self):
        """Validate the GlobalConfig instance after initialization"""
        logger.debug("Validating GlobalConfig instance")
        
        # Validate crawler instance
        if not isinstance(self.crawler, CrawlerDefaults):
            logger.error("Invalid crawler configuration type")
            raise TypeError("crawler must be an instance of CrawlerDefaults")
        
        # Validate ingestor instance
        if not isinstance(self.ingestor, IngestorDefaults):
            logger.error("Invalid ingestor configuration type")
            raise TypeError("ingestor must be an instance of IngestorDefaults")
        
        # Validate current_org if present
        if self.current_org is not None and not isinstance(self.current_org, str):
            logger.error("Invalid current_org type")
            raise TypeError("current_org must be None or a string")
        
        logger.debug("GlobalConfig validation completed successfully")
