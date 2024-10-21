import os
from mindstream_project.config import (
    ACCESS_TOKEN,
    INSTANCE_URL,
    OBJECT_API_NAME,
    SOURCE_NAME,
    MAX_CONCURRENT_JOBS,
    API_KEY,
    CRAWL_URL,
    WHITELIST,
    PAGE_LIMIT,
)
from mindstream_project.converter.json_to_csv_converter import JSONToCSVConverter
from mindstream_project.ingestor.data_cloud_bulk_ingest import DataCloudBulkIngest
from mindstream_project.crawler.data_crawler import DataCrawler

def main():
    # Crawl data
    output_folder = "./results/"
    crawler = DataCrawler(output_folder, API_KEY, CRAWL_URL, WHITELIST, PAGE_LIMIT)
    crawler.crawl()

    # Convert JSON to CSV
    csv_output_folder = "./csv_files/"
    converter = JSONToCSVConverter(output_folder, csv_output_folder)
    converter.convert()

    # Bulk Ingest to Data Cloud
    csv_files = [
        os.path.join(csv_output_folder, f)
        for f in os.listdir(csv_output_folder)
        if f.endswith(".csv")
    ]
    bulk_ingest = DataCloudBulkIngest(
        ACCESS_TOKEN,
        INSTANCE_URL,
        OBJECT_API_NAME,
        SOURCE_NAME,
        MAX_CONCURRENT_JOBS,
    )
    bulk_ingest.execute_bulk_ingest(csv_files)

if __name__ == "__main__":
    main()
