import os
import click
import asyncio
from mindstream_project.converter.json_to_csv_converter import JSONToCSVConverter
from mindstream_project.ingestor.data_cloud_bulk_ingest import DataCloudBulkIngest
from mindstream_project.crawler.data_crawler import DataCrawler
from mindstream_project.auth.jwt_auth import (
    generate_access_token, 
    generate_certificates
)
from mindstream_project.utils.config_manager import ConfigManager
import json

# Initialize ConfigManager at module level
config_manager = ConfigManager()

@click.group()
def cli():
    """MindStream Project CLI"""
    pass

@cli.group()
def org():
    """Manage Salesforce orgs"""
    pass

@org.command()
@click.argument('username')
def add(username):
    """Add a new Salesforce org"""
    org_dir = config_manager.init_org(username)  # Using global config_manager
    click.echo(f"Initialized org directory for {username}")

@org.command()
@click.argument('username')
def use(username):
    """Set the current working org"""
    config_manager = ConfigManager()
    if not (config_manager.orgs_dir / username).exists():
        click.echo(f"Org {username} not found. Please add it first using 'mindstream org add {username}'")
        return
    
    # Store current org in global config
    config_manager.set_global_config({'current_org': username})
    click.echo(f"Now using org: {username}")

@cli.group()
def config():
    """Manage global configuration"""
    pass

@config.command()
def show():
    """Show current global configuration"""
    config_manager = ConfigManager()
    global_config = config_manager.get_global_config()
    click.echo(json.dumps(global_config, indent=2))

@config.command()
@click.option('--page-limit', type=int, help='Set default page limit')
@click.option('--object-api-name', help='Set default object API name')
@click.option('--source-name', help='Set default source name')
@click.option('--max-concurrent-jobs', type=int, help='Set default max concurrent jobs')
@click.option('--crawl-url', help='Set default crawl URL')
@click.option('--api-key', help='Set default API key')
@click.option('--whitelist', help='Set default whitelist (comma-separated values)')
def set(page_limit, object_api_name, source_name, max_concurrent_jobs, crawl_url, api_key, whitelist):
    """Set global configuration values"""
    config_manager = ConfigManager()
    
    if page_limit is not None:
        config_manager.set_default('page_limit', page_limit)
        click.echo(f"Set default page_limit to {page_limit}")
    
    if object_api_name is not None:
        config_manager.set_default('object_api_name', object_api_name)
        click.echo(f"Set default object_api_name to {object_api_name}")
    
    if source_name is not None:
        config_manager.set_default('source_name', source_name)
        click.echo(f"Set default source_name to {source_name}")
    
    if max_concurrent_jobs is not None:
        config_manager.set_default('max_concurrent_jobs', max_concurrent_jobs)
        click.echo(f"Set default max_concurrent_jobs to {max_concurrent_jobs}")
    
    if crawl_url is not None:
        config_manager.set_default('crawl_url', crawl_url)
        click.echo(f"Set default crawl_url to {crawl_url}")
        
    if api_key is not None:
        config_manager.set_default('api_key', api_key)
        click.echo(f"Set default api_key to {api_key}")
        
    if whitelist is not None:
        # Convert comma-separated string to list
        whitelist_list = [item.strip() for item in whitelist.split(',')]
        config_manager.set_default('whitelist', whitelist_list)
        click.echo(f"Set default whitelist to {whitelist_list}")

@cli.command()
def pipeline():
    """Run the complete pipeline: crawl, convert, and ingest"""
    config_manager = ConfigManager()
    current_org = config_manager.get_global_config().get('current_org')
    
    if not current_org:
        click.echo("No org selected. Please select an org using 'mindstream org use <username>'")
        return
    
    org_dir = config_manager.get_org_path(current_org)
    org_config = config_manager.get_org_config(current_org)
    
    # Get crawl URL with validation
    crawl_url = org_config.get('crawl_url', config_manager.get_default('crawl_url'))
    if not crawl_url:
        click.echo("Error: No crawl URL specified. Please set it using 'mindstream config set --crawl-url URL' or in org config")
        return
        
    # Get API key with validation
    api_key = org_config.get('api_key', config_manager.get_default('api_key'))
    if not api_key:
        click.echo("Error: No API key specified. Please set it using 'mindstream config set --api-key KEY' or in org config")
        return
    
    # Update paths to use org-specific directories
    output_folder = org_dir / "results"
    csv_output_folder = org_dir / "csv_files"
    
    # Use org-specific configuration with global defaults
    try:
        crawler = DataCrawler(
            output_folder,
            api_key,
            crawl_url,
            org_config.get('whitelist', config_manager.get_default('whitelist', [])),
            org_config.get('page_limit', config_manager.get_default('page_limit', 50))
        )
        
        crawler.crawl()
    except ValueError as e:
        click.echo(f"Error: {str(e)}")
        return
    except Exception as e:
        click.echo(f"Error during crawl: {str(e)}")
        return

    # Convert JSON to CSV
    converter = JSONToCSVConverter(output_folder, csv_output_folder)
    converter.convert()

    # Bulk Ingest to Data Cloud
    csv_files = [
        f for f in csv_output_folder.glob("*.csv")
    ]
    
    bulk_ingest = DataCloudBulkIngest(
        org_config['access_token'],
        org_config['instance_url'],
        org_config.get('object_api_name', config_manager.get_default('object_api_name', 'Document')),
        org_config.get('source_name', config_manager.get_default('source_name', 'sfdc_ai_documents')),
        org_config.get('max_concurrent_jobs', config_manager.get_default('max_concurrent_jobs', 5))
    )
    bulk_ingest.execute_bulk_ingest(csv_files)

@cli.command()
@click.option('--generate-cert', is_flag=True, help="Generate new certificates")
@click.option('--use-cli', is_flag=True, help="Use Salesforce CLI for authentication")
@click.option('--alias', help="Salesforce CLI org alias to use")
def auth(generate_cert, use_cli, alias):
    """Authentication management commands"""
    try:
        if generate_cert:
            generate_certificates()
            click.echo("Certificates generated successfully")
        else:
            token = asyncio.run(generate_access_token())
            click.echo(f"Successfully generated token using JWT: {token}")
    except Exception as e:
        click.echo(f"Error in auth command: {e}", err=True)

def main():
    current_org = config_manager.get_global_config().get('current_org')  # Using global config_manager
    
    if not current_org:
        click.echo("No org selected. Please select an org using 'mindstream org use <username>'")
        return
    
    org_dir = config_manager.get_org_path(current_org)
    org_config = config_manager.get_org_config(current_org)
    
    # Get configuration values with defaults
    api_key = org_config.get('api_key', config_manager.get_default('api_key'))
    crawl_url = org_config.get('crawl_url', config_manager.get_default('crawl_url'))
    whitelist = org_config.get('whitelist', config_manager.get_default('whitelist', []))
    page_limit = org_config.get('page_limit', config_manager.get_default('page_limit', 50))
    
    # Update paths to use org-specific directories
    output_folder = org_dir / "results"
    csv_output_folder = org_dir / "csv_files"
    
    # Crawl data
    crawler = DataCrawler(output_folder, api_key, crawl_url, whitelist, page_limit)
    crawler.crawl()

    # Convert JSON to CSV
    converter = JSONToCSVConverter(output_folder, csv_output_folder)
    converter.convert()

    # Bulk Ingest to Data Cloud
    csv_files = [
        f for f in csv_output_folder.glob("*.csv")
    ]
    
    bulk_ingest = DataCloudBulkIngest(
        org_config['access_token'],
        org_config['instance_url'],
        org_config.get('object_api_name', config_manager.get_default('object_api_name', 'Document')),
        org_config.get('source_name', config_manager.get_default('source_name', 'sfdc_ai_documents')),
        org_config.get('max_concurrent_jobs', config_manager.get_default('max_concurrent_jobs', 5))
    )
    bulk_ingest.execute_bulk_ingest(csv_files)

if __name__ == "__main__":
    cli()
