import requests
import os
import json
from pathlib import Path
import httpx
from mindstream_project.models.global_config import CrawlerDefaults
from mindstream_project.utils.logging_config import get_logger

logger = get_logger(__name__)

class DataCrawler:
    def __init__(self, output_folder, crawler_config: CrawlerDefaults):
        logger.debug("Initializing DataCrawler")
        if not crawler_config.api_key:
            logger.error("API key is required but not provided")
            raise ValueError("API key is required")
        if not crawler_config.crawl_url:
            logger.error("Crawl URL is required but not provided")
            raise ValueError("Crawl URL is required")
        
        self.output_folder = Path(output_folder)
        self.headers = {
            'Authorization': f'Bearer {crawler_config.api_key}',
            'Content-Type': 'application/json',
        }
        self.json_data = crawler_config.get_api_payload()
        self.output_folder.mkdir(parents=True, exist_ok=True)
        logger.debug(f"DataCrawler initialized with output folder: {self.output_folder}")

    async def crawl(self):
        """Make the crawl method asynchronous for better performance"""
        logger.debug("Starting crawl process")
        async with httpx.AsyncClient() as client:
            try:
                logger.debug("Sending POST request to crawl URL")
                response = await client.post(
                    'https://api.spider.cloud/crawl',
                    headers=self.headers,
                    json=self.json_data,
                    timeout=300  # 5-minute timeout
                )
                response.raise_for_status()
                logger.debug("Crawl request successful")
            except httpx.HTTPError as e:
                logger.error(f"Error during crawl request: {e}", exc_info=True)
                raise

            data = response.json()
            logger.debug("Crawl data received")

            output_file = self.output_folder / "data.json"
            logger.debug(f"Writing data to {output_file}")
            with open(output_file, "w", encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            logger.debug(f"Data written to {output_file}")

            return output_file
