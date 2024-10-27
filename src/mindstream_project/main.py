import os
import click
import asyncio
import json

from mindstream_project.converter.json_to_csv_converter import JSONToCSVConverter
from mindstream_project.ingestor.data_cloud_bulk_ingest import DataCloudBulkIngest
from mindstream_project.crawler.data_crawler import DataCrawler

@click.group()
def cli():
    """MindStream Project CLI"""
    pass

@cli.command()
@click.option('--config-file', type=click.Path(exists=True), help='Path to JSON configuration file')
@click.option('--bulk-params', help='Bulk ingestion configuration parameters')
@click.option('--crawler-params', help='Crawler configuration parameters')
@click.option('--sfdc-params', help='Salesforce authentication parameters')
def pipeline(config_file, bulk_params, crawler_params, sfdc_params):
    """Run the complete pipeline: crawl, convert, and ingest"""
    try:
        if config_file:
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            if not any([bulk_params, crawler_params, sfdc_params]):
                click.echo("Error: Either --config-file or configuration parameters must be provided", err=True)
                return

            bulk_config = parse_key_value_pairs(bulk_params)
            crawler_config = parse_key_value_pairs(crawler_params)
            sfdc_config = parse_key_value_pairs(sfdc_params)

            config = {
                'bulk_ingest': bulk_config,
                'crawler': crawler_config,
                'sfdc_access_token': sfdc_config.get('access_token')
            }
        main(config)
    except json.JSONDecodeError as e:
        click.echo(f"Error parsing JSON configuration: {e}", err=True)
        return

def main(config):
    # Extract configuration
    bulk_ingest_config = config.get('bulk_ingest', {})
    crawler_config = config.get('crawler', {})
    sfdc_access_token = config.get('sfdc_access_token')

    # Crawl data
    output_folder = "./results/"
    crawler = DataCrawler(
        output_folder,
        crawler_config.get('api_key'),
        crawler_config.get('crawl_url'),
        crawler_config.get('whitelist'),
        crawler_config.get('page_limit')
    )
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
        bulk_ingest_config.get('access_token'),
        bulk_ingest_config.get('instance_url'),
        bulk_ingest_config.get('object_api_name'),
        bulk_ingest_config.get('source_name'),
        bulk_ingest_config.get('max_concurrent_jobs'),
    )
    bulk_ingest.execute_bulk_ingest(csv_files)

def parse_key_value_pairs(params_string):
    if not params_string:
        return {}
    return dict(pair.split('=') for pair in params_string.split(','))


if __name__ == "__main__":
    cli()
