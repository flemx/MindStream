import requests
import os
import json
from pathlib import Path
import httpx
from src.mindstream_project.models.global_config import CrawlerDefaults

class DataCrawler:
    def __init__(self, output_folder, crawler_config: CrawlerDefaults):
        if not crawler_config.api_key:
            raise ValueError("API key is required")
        if not crawler_config.crawl_url:
            raise ValueError("Crawl URL is required")
            
        self.output_folder = Path(output_folder)
        self.headers = {
            'Authorization': f'Bearer {crawler_config.api_key}',
            'Content-Type': 'application/json',
        }
        self.json_data = crawler_config.get_api_payload()
        self.output_folder.mkdir(parents=True, exist_ok=True)

    async def crawl(self):
        """Make the crawl method asynchronous for better performance"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://api.spider.cloud/crawl',
                headers=self.headers,
                json=self.json_data,
                timeout=300  # 5-minute timeout
            )
            response.raise_for_status()
            data = response.json()
            
            output_file = self.output_folder / "data.json"
            with open(output_file, "w", encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            return output_file
