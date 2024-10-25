import os
import click
import asyncio
import subprocess
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
    """Manage Salesforce orgs and authentication"""
    pass

@org.command()
@click.option('--alias', default=None, help='Alias for the Salesforce org')
@click.option('--default', is_flag=True, help='Set this org as the default org')
def add(alias, default):
    """Add and authenticate a new Salesforce org"""
    # Authenticate the org using Salesforce CLI first
    try:
        auth_command = ['sf', 'org', 'login', 'web']
        if alias:
            auth_command.extend(['--alias', alias])
        click.echo("Opening browser to authenticate the org, please wait a while after you've logged in...")
        subprocess.run(auth_command, check=True)
        click.echo("Authentication successful.")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error authenticating the org: {e}", err=True)
        return

    # Get username from the authenticated org
    try:
        result = subprocess.run(
            ['sf', 'org', 'display', '--json'],
            capture_output=True,
            text=True,
            check=True
        )
        org_info = json.loads(result.stdout)
        username = org_info['result']['username']
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        click.echo(f"Error getting org information: {e}", err=True)
        return

    # Initialize org directory and configuration
    org_dir = config_manager.init_org(username, alias)
    click.echo(f"Initialized org directory for {username}")

    # Optionally set as default org
    if default:
        config_manager.set_default_org(username)
        click.echo(f"Set {username} as the default org")

    # Generate certificates and deploy metadata
    generate_certificates(org_dir)
    click.echo("Certificates generated and metadata deployed successfully.")

    click.echo(f"Successfully added and authenticated org: {username}")

@org.command()
@click.argument('username')
def use(username):
    """Set the current working org"""
    if not (config_manager.orgs_dir / config_manager._sanitize_username(username)).exists():
        click.echo(f"Org {username} not found. Please add it first using 'mindstream org add {username}'")
        return
    
    # Store current org in global config
    config_manager.set_default_org(username)
    click.echo(f"Now using org: {username}")

@org.command()
def list():
    """List all connected orgs and the default one"""
    orgs = config_manager.list_orgs()
    default_org = config_manager.get_global_config().get('current_org')
    for org_username, config in orgs.items():
        alias = config.get('alias', '')
        default_marker = '(Default)' if org_username == default_org else ''
        click.echo(f"Username: {org_username}, Alias: {alias} {default_marker}")

@org.command()
@click.option('--username', help='Username of the org to regenerate certificates for')
@click.option('--all-orgs', is_flag=True, help='Regenerate certificates for all orgs')
def regenerate_certs(username, all_orgs):
    """Regenerate certificates for specified org(s)"""
    if all_orgs:
        orgs = config_manager.list_orgs()
        for org_username in orgs:
            org_dir = config_manager.get_org_path(org_username)
            generate_certificates(org_dir)
            click.echo(f"Regenerated certificates for {org_username}")
        return

    if username:
        org_dir = config_manager.get_org_path(username)
        if not org_dir.exists():
            click.echo(f"Org {username} not found. Please add it first using 'mindstream org add {username}'")
            return
        generate_certificates(org_dir)
        click.echo(f"Regenerated certificates for {username}")
    else:
        current_org = config_manager.get_global_config().get('current_org')
        if not current_org:
            click.echo("No org selected. Please specify --username or use 'mindstream org use <username>'")
            return
        org_dir = config_manager.get_org_path(current_org)
        generate_certificates(org_dir)
        click.echo(f"Regenerated certificates for {current_org}")

@org.command()
@click.argument('username')
def login(username):
    """Re-authenticate an existing org"""
    if not (config_manager.orgs_dir / config_manager._sanitize_username(username)).exists():
        click.echo(f"Org {username} not found. Please add it first using 'mindstream org add {username}'")
        return
    
    try:
        auth_command = ['sf', 'org', 'login', 'web', '--set-default-username']
        click.echo("Opening browser to authenticate the org...")
        subprocess.run(auth_command, check=True)
        click.echo("Authentication successful.")
        
        # Generate new access token using JWT
        asyncio.run(generate_access_token())
        click.echo("JWT authentication successful")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error authenticating the org: {e}", err=True)
        return

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
