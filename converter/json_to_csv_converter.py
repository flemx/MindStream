import os
import json
import csv
from datetime import datetime
from bs4 import BeautifulSoup

class JSONToCSVConverter:
    def __init__(self, json_folder, csv_output_folder, max_csv_file_size=100 * 1024 * 1024):
        self.json_folder = json_folder
        self.csv_output_folder = csv_output_folder
        self.max_csv_file_size = max_csv_file_size
        self.fieldnames = ["content", "id", "last_updated", "title", "url"]

        if not os.path.exists(self.csv_output_folder):
            os.makedirs(self.csv_output_folder)

    def get_current_time_iso(self):
        return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    def clean_html(self, content):
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style", "meta", "link"]):
            tag.decompose()
        return str(soup)

    def convert(self):
        csv_file_counter = 1
        csv_file_path = os.path.join(self.csv_output_folder, f"data_{csv_file_counter}.csv")
        csv_file = open(csv_file_path, "w", newline='', encoding='utf-8')
        csv_writer = csv.DictWriter(csv_file, fieldnames=self.fieldnames)
        csv_writer.writeheader()

        for filename in os.listdir(self.json_folder):
            if filename.endswith(".json"):
                file_path = os.path.join(self.json_folder, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    chunk_data = json.load(f)

                if not isinstance(chunk_data, list):
                    continue

                for obj in chunk_data:
                    raw_content = obj.get('content', "")
                    cleaned_content = self.clean_html(raw_content)
                    title = obj.get('metadata', {}).get('title', "")
                    doc_url = obj.get('metadata', {}).get('url', "")
                    last_updated = self.get_current_time_iso()

                    row = {
                        "content": cleaned_content,
                        "id": doc_url,
                        "last_updated": last_updated,
                        "title": title,
                        "url": doc_url
                    }

                    csv_writer.writerow(row)

                    if csv_file.tell() >= self.max_csv_file_size:
                        csv_file.close()
                        csv_file_counter += 1
                        csv_file_path = os.path.join(self.csv_output_folder, f"data_{csv_file_counter}.csv")
                        csv_file = open(csv_file_path, "w", newline='', encoding='utf-8')
                        csv_writer = csv.DictWriter(csv_file, fieldnames=self.fieldnames)
                        csv_writer.writeheader()

        csv_file.close()