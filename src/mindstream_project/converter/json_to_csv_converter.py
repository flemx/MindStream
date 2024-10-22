import os
import json
import csv
from datetime import datetime
from bs4 import BeautifulSoup, Tag, Doctype, NavigableString
import re
import logging

class JSONToCSVConverter:
    def __init__(self, json_folder, csv_output_folder, max_csv_file_size=100 * 1024 * 1024):
        self.json_folder = json_folder
        self.csv_output_folder = csv_output_folder
        self.max_csv_file_size = max_csv_file_size
        self.fieldnames = ["content", "id", "last_updated", "title", "url"]

        if not os.path.exists(self.csv_output_folder):
            os.makedirs(self.csv_output_folder)

        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    def get_current_time_iso(self):
        return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    def clean_html(self, content):
        if not content:
            logging.warning("clean_html received empty or None content")
            return ""

        try:
            # Remove script and style elements
            content = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', content, flags=re.DOTALL | re.IGNORECASE)
            
            # Parse the HTML content
            soup = BeautifulSoup(content, "html.parser")

            # Define allowed tags
            allowed_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p',
                            'ul', 'ol', 'li', 'blockquote', 'pre', 'code']

            # Create a new BeautifulSoup object to build the cleaned HTML
            new_soup = BeautifulSoup('<body></body>', 'html.parser')
            new_body = new_soup.body

            # Function to recursively process nodes
            def process_node(node, parent):
                if isinstance(node, NavigableString):
                    # Append text nodes directly
                    parent.append(NavigableString(node))
                elif isinstance(node, Tag):
                    if node.name in allowed_tags:
                        # Create a new tag without attributes
                        new_tag = new_soup.new_tag(node.name)
                        parent.append(new_tag)
                        # Recursively process child nodes
                        for child in node.children:
                            process_node(child, new_tag)
                    else:
                        # If tag is not allowed, process its children directly under the current parent
                        for child in node.children:
                            process_node(child, parent)
                # Ignore other types like Comments, Doctype, etc.

            # Start processing from the soup's body or the entire soup if body is not present
            start_node = soup.body if soup.body else soup
            process_node(start_node, new_body)

            # Remove empty tags
            for tag in new_soup.find_all():
                if not tag.get_text(strip=True):
                    tag.decompose()

            # Convert the cleaned soup to string
            cleaned_html = str(new_soup.body)

            # Clean up extra whitespace and newlines
            cleaned_html = re.sub(r'\s+', ' ', cleaned_html).strip()

            return cleaned_html

        except Exception as e:
            logging.error(f"Error in clean_html: {str(e)}")
            return ""

    def convert(self):
        try:
            csv_file_counter = 1
            csv_file_path = os.path.join(self.csv_output_folder, f"data_{csv_file_counter}.csv")
            csv_file = open(csv_file_path, "w", newline='', encoding='utf-8')
            csv_writer = csv.DictWriter(csv_file, fieldnames=self.fieldnames)
            csv_writer.writeheader()

            for filename in os.listdir(self.json_folder):
                if filename.endswith(".json"):
                    file_path = os.path.join(self.json_folder, filename)
                    logging.info(f"Processing file: {file_path}")
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            chunk_data = json.load(f)

                        if not isinstance(chunk_data, list):
                            logging.warning(f"Skipping {filename}: data is not a list")
                            continue

                        for obj in chunk_data:
                            try:
                                raw_content = obj.get('content')
                    
                                cleaned_content = self.clean_html(raw_content)
                                 # Skip this row if raw_content is None or empty
                                if not cleaned_content or cleaned_content == "None" or cleaned_content is None or cleaned_content.strip() == "":
                                    logging.info(f"Skipping row in {filename}: empty or None content")
                                    continue


                                title = obj.get('metadata', {}).get('title', "")
                                doc_url = obj.get('url', "")
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
                            except Exception as e:
                                logging.error(f"Error processing object in {filename}: {str(e)}")

                    except Exception as e:
                        logging.error(f"Error processing {filename}: {str(e)}")

            csv_file.close()
            logging.info("Conversion completed")
        except Exception as e:
            logging.error(f"Error in convert method: {str(e)}")
