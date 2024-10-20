import os
from config import ACCESS_TOKEN, INSTANCE_URL, OBJECT_API_NAME, SOURCE_NAME, MAX_CONCURRENT_JOBS, API_KEY, CRAWL_URL, WHITELIST
from json_to_csv_converter import JSONToCSVConverter
from data_cloud_bulk_ingest import DataCloudBulkIngest
from crawler import DataCrawler

if __name__ == "__main__":
    # Crawl data
    output_folder = "./results/"
    crawler = DataCrawler(output_folder, API_KEY, CRAWL_URL, WHITELIST)
    crawler.crawl()

    # Convert JSON to CSV
    csv_output_folder = "./csv_files/"
    converter = JSONToCSVConverter(output_folder, csv_output_folder)
    converter.convert()

    # Bulk Ingest to Data Cloud
    csv_files = [os.path.join(csv_output_folder, f) for f in os.listdir(csv_output_folder) if f.endswith('.csv')]
    bulk_ingest = DataCloudBulkIngest(ACCESS_TOKEN, INSTANCE_URL, OBJECT_API_NAME, SOURCE_NAME, MAX_CONCURRENT_JOBS)
    bulk_ingest.execute_bulk_ingest(csv_files)