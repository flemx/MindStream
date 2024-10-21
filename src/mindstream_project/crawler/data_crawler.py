import requests
import os
import json

class DataCrawler:
    def __init__(self, output_folder, api_key, crawl_url, whitelist, limit):
        self.output_folder = output_folder
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        self.crawl_url = crawl_url
        self.whitelist = whitelist
        self.limit = limit
        self.json_data = {
            "limit": self.limit,
            "return_format": "raw",
            "request": "smart_mode",
            "metadata": True,
            "respect_robots": False,
            "readability": True,
            "url": self.crawl_url,
            "whitelist": self.whitelist
        }

        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

    def crawl(self):
        response = requests.post('https://api.spider.cloud/crawl', headers=self.headers, json=self.json_data)
        response.raise_for_status()
        data = response.json()
        output_file = os.path.join(self.output_folder, "data.json")
        with open(output_file, "w", encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Saved data to {output_file}")

