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
from mindstream_project.models.org_config import OrgDetails
from mindstream_project.utils.config_manager import ConfigManager
import json
from mindstream_project.utils.salesforce_cli import SalesforceCLI
from datetime import datetime
from typing import List, Dict, Any, Optional
from mindstream_project.models.global_config import CrawlerDefaults, IngestorDefaults, GlobalConfig
from pathlib import Path
from mindstream_project.utils.logging_config import get_logger, setup_logging
import platform
import logging

# Initialize the logger
logger = get_logger(__name__)

# Initialize ConfigManager at module level
config_manager = ConfigManager()

@click.group()
@click.version_option()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--log-file', type=click.Path(), help='Log file path')
def cli(debug: bool, log_file: Optional[str]):
    """MindStream CLI - Data Pipeline Management Tool"""
    log_file_path = Path(log_file) if log_file else None
    setup_logging(debug=debug, log_file=log_file_path)

@cli.group()
def org():
    """Manage Salesforce orgs and authentication
    
    Commands:
      add               Add and authenticate a new org
      use               Set the current working org
      list              List all connected orgs
      login             Re-authenticate an existing org
      regenerate-certs  Regenerate certificates for org(s)
    """
    pass

@org.command()
@click.option('--alias', default=None, help='Alias for the Salesforce org')
@click.option('--default', is_flag=True, help='Set this org as the default org')
def add(alias, default):
    """Add and authenticate a new Salesforce org"""
    try:
        logger.debug(f"Starting org add with alias: {alias}, default: {default}")
        
        # Check if the org is already authenticated in SF CLI
        if alias and SalesforceCLI.is_org_authenticated(alias):
            # Get username from the authenticated org
            username = SalesforceCLI.get_username_from_alias(alias)
            if username:
                # Check if we have local config for this org
                if (config_manager.orgs_dir / config_manager._sanitize_username(username)).exists():
                    click.echo(f"Org with alias '{alias}' is already authenticated and configured.")
                    return
                else:
                    # Get org info to create local config
                    org_info = SalesforceCLI.get_org_info(alias)
                    if org_info:
                        click.echo(f"Found authenticated org. Creating local configuration...")
                        result = org_info
                    else:
                        click.echo("Failed to get org info.", err=True)
                        return
            else:
                click.echo("Failed to get username for authenticated org.", err=True)
                return
        else:
            # Authenticate the org using Salesforce CLI
            print("Authenticating org with Salesforce CLI, please wait after successful login...")
            result = SalesforceCLI.authenticate_org(alias)
            if result:
                click.echo("Authentication successful.")
                logger.debug(f"Org info received: {result}")
            else:
                click.echo("Authentication failed.", err=True)
                return

        # Get username from the org info
        username = result.get('username')
        print(f"Result check from org info: { result}")
        if not username:
            # Try to get username from the authorization message
            auth_result = result.get('result', {})
            if isinstance(auth_result, str) and 'Successfully authorized' in auth_result:
                # Extract username from authorization message
                import re
                match = re.search(r'Successfully authorized (.*?) with org ID', auth_result)
                if match:
                    username = match.group(1)
        
        if not username:
            click.echo("Failed to get username from org info.", err=True)
            return
            
        logger.debug(f"Username from org info: {username}")
        
        # Create OrgDetails instance
        logger.debug("Creating OrgDetails instance")
        org_details = OrgDetails(
            username=username,
            instance_url=result.get('result', {}).get('instanceUrl', ''),
            login_url=result.get('result', {}).get('loginUrl', 'https://login.salesforce.com'),
            org_id=result.get('result', {}).get('orgId', ''),
            alias=alias
        )
        logger.debug(f"Created org_details: {org_details.to_dict()}")
        
        # Initialize org directory and configuration
        logger.debug("Initializing org directory")
        org_dir = config_manager.init_org(username, org_details)
        print(f"Initialized org directory for {username}")

        # Generate certificates and deploy metadata
        logger.debug("Starting certificate generation")
        generate_certificates(org_dir)
        click.echo("Certificates generated and metadata deployed successfully.")

        # Optionally set as default org
        if default:
            logger.debug(f"Setting {username} as default org")
            config_manager.set_default_org(username)
            click.echo(f"Set {username} as the default org")

        click.echo(f"Successfully added and authenticated org: {username}")
    except Exception as e:
        logger.error(f"Error in add command: {str(e)}", exc_info=True)
        click.echo(f"Error adding org: {str(e)}", err=True)

@org.command()
@click.argument('identifier')
def use(identifier):
    """Set the current working org using username or alias
    
    Examples:
        mindstream org use user@example.com
        mindstream org use myorg
    
    Arguments:
        identifier  Username or alias of the org to use
    """
    # First, try to find username if an alias was provided
    username = SalesforceCLI.get_username_from_alias(identifier)
    if username:
        # Found a matching alias
        if not (config_manager.orgs_dir / config_manager._sanitize_username(username)).exists():
            click.echo(f"Org with alias '{identifier}' (username: {username}) not found in local config. "
                      f"Please add it first using 'mindstream org add --alias {identifier}'")
            return
        config_manager.set_default_org(username)
        click.echo(f"Now using org: {username} (alias: {identifier})")
        return

    # If no alias found, treat the identifier as a username
    if not (config_manager.orgs_dir / config_manager._sanitize_username(identifier)).exists():
        click.echo(f"Org {identifier} not found. Please add it first using 'mindstream org add {identifier}'")
        return
    
    # Store current org in global config
    config_manager.set_default_org(identifier)
    click.echo(f"Now using org: {identifier}")

@org.command()
def list():
    """List all connected orgs and the default one
    
    Shows username, alias (if set), and marks the default org.
    
    Example:
        mindstream org list
    
    Output format:
        Username: user@example.com, Alias: myorg (Default)
        Username: other@example.com, Alias: otherorg
    """
    orgs = config_manager.list_orgs()
    global_config = config_manager.get_global_config()
    default_org = global_config.current_org
    for org_username, config in orgs.items():
        alias = config.get('alias', '')
        default_marker = '(Default)' if org_username == default_org else ''
        click.echo(f"Username: {org_username}, Alias: {alias} {default_marker}")

@org.command()
@click.option('--username', help='Username of the org to regenerate certificates for')
@click.option('--all-orgs', is_flag=True, help='Regenerate certificates for all orgs')
def regenerate_certs(username, all_orgs):
    """Regenerate certificates for specified org(s)
    
    Examples:
        mindstream org regenerate-certs --username user@example.com
        mindstream org regenerate-certs --all-orgs
    
    Options:
        --username   Username of specific org to regenerate certs for
        --all-orgs  Regenerate certificates for all connected orgs
    """
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
        global_config = config_manager.get_global_config()
        current_org = global_config.current_org
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
    
    # Re-authenticate using Salesforce CLI
    if SalesforceCLI.authenticate_org():
        click.echo("Authentication successful.")
        
        # Get updated org info
        org_info = SalesforceCLI.get_org_info()
        if org_info and 'result' in org_info:
            # Update org details in config
            org_details = {
                'instance_url': org_info['result'].get('instanceUrl'),
                'login_url': org_info['result'].get('loginUrl'),
                'org_id': org_info['result'].get('orgId'),
                'updated_at': datetime.now().isoformat()
            }
            config_manager.set_org_config(username, org_details)
            
        # Generate new access token using JWT
        asyncio.run(generate_access_token())
        click.echo("JWT authentication successful")
    else:
        click.echo("Authentication failed.", err=True)

def parse_additional_params(params: List[str]) -> Dict[str, Any]:
    """Parse additional parameters from CLI input"""
    result = {}
    for param in params:
        try:
            key, value = param.split('=')
            # Try to convert to appropriate type
            try:
                value = json.loads(value.lower())  # Handles true/false/null/numbers
            except json.JSONDecodeError:
                pass  # Keep as string if not a special value
            result[key] = value
        except ValueError:
            click.echo(f"Warning: Skipping invalid parameter format: {param}")
    return result

@cli.group()
def config():
    """Manage global and org-specific configuration.
    """
    pass

@config.group()
def crawler():
    """Manage crawler configuration.

    Options:
      --page-limit    INT     Number of pages to crawl
      --crawl-url     TEXT    URL to crawl
      --api-key       TEXT    API key for crawler service
      --whitelist     TEXT    Comma-separated list of allowed domains
      --param, -p     TEXT    Additional parameters (key=value format)
      --org           TEXT    Username or alias of org to configure

    Examples:
      mindstream config crawler set --page-limit 100
      mindstream config crawler set --crawl-url "https://example.com" --org myorg
      mindstream config crawler set -p respect_robots=true -p custom_param=value
    """
    pass

@config.group()
def ingestor():
    """Manage ingestor configuration.

    Options:
      --object-api-name      TEXT    Salesforce object API name
      --source-name          TEXT    Source name for ingested data
      --max-concurrent-jobs  INT     Maximum concurrent ingestion jobs
      --org                  TEXT    Username or alias of org to configure

    Examples:
      mindstream config ingestor set --object-api-name "CustomDoc"
      mindstream config ingestor set --source-name "custom_source" --org myorg
    """
    pass

@config.command()
@click.option('--crawler', is_flag=True, help='Show only crawler configuration')
@click.option('--ingestor', is_flag=True, help='Show only ingestor configuration')
@click.option('--org', help='Username or alias of the org to show configuration for')
def show(crawler, ingestor, org):
    """Show current configuration settings.

    Display global defaults or org-specific configuration.

    Examples:
      mindstream config show
      mindstream config show --crawler
      mindstream config show --ingestor
      mindstream config show --org myorg

    Options:
      --crawler   Show only crawler settings
      --ingestor  Show only ingestor settings
      --org       Show config for specific org (username or alias)
    """
    try:
        config_manager = ConfigManager()
        
        if org:
            target_username = resolve_username(org)
            config = config_manager.get_org_config(target_username)
            config_type = f"org configuration for {target_username}"
        else:
            config = config_manager.get_global_config()
            config_type = "global configuration"
        
        if crawler:
            if config.crawler:
                click.echo(f"Crawler {config_type}:")
                click.echo(json.dumps(config.crawler.to_dict(), indent=2))
            else:
                click.echo(f"No crawler configuration set for {config_type}")
        elif ingestor:
            if config.ingestor:
                click.echo(f"Ingestor {config_type}:")
                click.echo(json.dumps(config.ingestor.to_dict(), indent=2))
            else:
                click.echo(f"No ingestor configuration set for {config_type}")
        else:
            click.echo(f"Complete {config_type}:")
            click.echo(json.dumps(config.to_dict(), indent=2))
            
    except click.UsageError as e:
        click.echo(str(e), err=True)

@crawler.command()
@click.option('--page-limit', type=int, help='Set page limit')
@click.option('--crawl-url', help='Set crawl URL')
@click.option('--api-key', help='Set API key')
@click.option('--whitelist', help='Set whitelist (comma-separated values)')
@click.option('--param', '-p', multiple=True, help='Additional parameters in key=value format')
@click.option('--org', help='Username or alias of the org to configure')
def set_crawler(page_limit, crawl_url, api_key, whitelist, param, org):
    """Configure crawler settings
    
    Set crawler configuration globally or for a specific org.
    
    Examples:
        mindstream config crawler set --page-limit 100
        mindstream config crawler set --crawl-url "https://example.com" --api-key "key"
        mindstream config crawler set --whitelist "domain1.com,domain2.com"
        mindstream config crawler set -p respect_robots=true -p custom_param=value
        mindstream config crawler set --page-limit 200 --org myorg
    
    Options:
        --page-limit  Number of pages to crawl
        --crawl-url   URL to crawl
        --api-key     API key for crawler service
        --whitelist   Comma-separated list of allowed domains
        --param, -p   Additional parameters (key=value format)
        --org         Configure for specific org (username or alias)
    
    Additional Parameters:
        Additional parameters can be set using -p or --param option.
        Format: -p key=value
        
        Common additional parameters:
        - respect_robots=true/false
        - metadata=true/false
        - readability=true/false
        - custom parameters as needed
    """
    try:
        target_username = resolve_username(org) if org else None
        config_manager = ConfigManager()
        
        # Determine if we're setting global or org-specific config
        if target_username:
            config = config_manager.get_org_config(target_username)
            if not config.crawler:
                config.crawler = CrawlerDefaults()
        else:
            config = config_manager.get_global_config()

        # Update values if provided
        if page_limit is not None:
            config.crawler.page_limit = page_limit
        if crawl_url is not None:
            config.crawler.crawl_url = crawl_url
        if api_key is not None:
            config.crawler.api_key = api_key
        if whitelist is not None:
            config.crawler.whitelist = [x.strip() for x in whitelist.split(',')]
        if param:
            config.crawler.additional_params.update(parse_additional_params(param))

        # Save the configuration
        if target_username:
            config_manager.set_org_config(target_username, config)
            click.echo(f"Updated crawler configuration for org: {target_username}")
        else:
            config_manager.set_global_config(config)
            click.echo("Updated global crawler configuration")
            
    except click.UsageError as e:
        click.echo(str(e), err=True)

@ingestor.command()
@click.option('--object-api-name', help='Set object API name')
@click.option('--source-name', help='Set source name')
@click.option('--max-concurrent-jobs', type=int, help='Set max concurrent jobs')
@click.option('--org', help='Username or alias of the org to configure')
def set_ingestor(object_api_name, source_name, max_concurrent_jobs, org):
    """Configure ingestor settings
    
    Set ingestor configuration globally or for a specific org.
    
    Examples:
        mindstream config ingestor set --object-api-name "CustomDoc"
        mindstream config ingestor set --source-name "custom_source"
        mindstream config ingestor set --max-concurrent-jobs 10
        mindstream config ingestor set --source-name "org_source" --org myorg
    
    Options:
        --object-api-name      Salesforce object API name
        --source-name         Source name for ingested data
        --max-concurrent-jobs Maximum concurrent ingestion jobs
        --org                Configure for specific org (username or alias)
    """
    try:
        target_username = resolve_username(org) if org else None
        config_manager = ConfigManager()
        
        # Determine if we're setting global or org-specific config
        if target_username:
            config = config_manager.get_org_config(target_username)
            if not config.ingestor:
                config.ingestor = IngestorDefaults()
        else:
            config = config_manager.get_global_config()

        # Update values if provided
        if object_api_name is not None:
            config.ingestor.object_api_name = object_api_name
        if source_name is not None:
            config.ingestor.source_name = source_name
        if max_concurrent_jobs is not None:
            config.ingestor.max_concurrent_jobs = max_concurrent_jobs

        # Save the configuration
        if target_username:
            config_manager.set_org_config(target_username, config)
            click.echo(f"Updated ingestor configuration for org: {target_username}")
        else:
            config_manager.set_global_config(config)
            click.echo("Updated global ingestor configuration")
            
    except click.UsageError as e:
        click.echo(str(e), err=True)

@cli.command()
@click.option('--org', help='Username or alias of the org to use')
@click.option('--output-path', type=click.Path(), help='Custom path to store crawled data')
@click.option('--page-limit', type=int, help='Override page limit')
@click.option('--crawl-url', help='Override crawl URL')
@click.option('--api-key', help='Override API key')
@click.option('--whitelist', help='Override whitelist (comma-separated)')
@click.option('--param', '-p', multiple=True, help='Additional parameters (key=value)')
def crawl(org, output_path, page_limit, crawl_url, api_key, whitelist, param):
    """Execute the crawler to fetch data"""
    try:
        config = get_effective_config(org)
        
        # Create override crawler config with existing values from config
        crawler_config = CrawlerDefaults(
            page_limit=page_limit or config.crawler.page_limit,
            crawl_url=crawl_url or config.crawler.crawl_url,
            api_key=api_key or config.crawler.api_key,
            whitelist=whitelist.split(',') if whitelist else config.crawler.whitelist,
            additional_params=config.crawler.additional_params.copy()
        )
        
        if param:
            crawler_config.additional_params.update(parse_additional_params(param))
        
        # Determine output path
        output_folder = Path(output_path) if output_path else config_manager.get_org_path(config.username) / "results"
        
        # Execute crawler
        crawler = DataCrawler(output_folder, crawler_config)
        result = asyncio.run(crawler.crawl())  # Use asyncio.run to execute the coroutine
        click.echo(f"Crawl completed. Results stored in: {result}")
        
    except Exception as e:
        logger.error(f"Crawl error: {str(e)}", exc_info=True)
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.option('--org', help='Username or alias of the org to use')
@click.option('--input-path', type=click.Path(exists=True), help='Path to JSON file or directory')
@click.option('--output-path', type=click.Path(), help='Custom path to store CSV files')
def convert(org, input_path, output_path):
    """Convert JSON data to CSV format
    
    Converts crawled JSON data to CSV format suitable for Data Cloud ingestion.
    Can process a single file or an entire directory.
    
    Examples:
        mindstream convert
        mindstream convert --org myorg
        mindstream convert --input-path ./data.json
        mindstream convert --input-path ./json_dir --output-path ./csv_dir
    
    Options:
        --org           Username or alias of the org to use
        --input-path    Path to JSON file or directory to convert
        --output-path   Custom path to store converted CSV files
    
    Default Paths:
        Input:  ~/.mindstream/orgs/<username>/results/
        Output: ~/.mindstream/orgs/<username>/csv_files/
    """
    try:
        config = get_effective_config(org)
        org_dir = config_manager.get_org_path(config.username)
        
        # Determine paths
        input_folder = Path(input_path) if input_path else org_dir / "results"
        output_folder = Path(output_path) if output_path else org_dir / "csv_files"
        
        converter = JSONToCSVConverter(input_folder, output_folder)
        converter.convert()
        click.echo(f"Conversion completed. CSV files stored in: {output_folder}")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.option('--org', help='Username or alias of the org to use')
@click.option('--input-path', type=click.Path(exists=True), help='Path to CSV file or directory')
@click.option('--object-api-name', help='Override object API name')
@click.option('--source-name', help='Override source name')
@click.option('--max-concurrent-jobs', type=int, help='Override max concurrent jobs')
def upload(org, input_path, object_api_name, source_name, max_concurrent_jobs):
    """Upload CSV data to Data Cloud
    
    Bulk uploads CSV files to Salesforce Data Cloud using configured
    or overridden settings. Can process a single file or directory.
    
    Examples:
        mindstream upload
        mindstream upload --org myorg
        mindstream upload --input-path ./data.csv
        mindstream upload --object-api-name "CustomDoc"
        mindstream upload --source-name "custom_source"
    
    Options:
        --org                  Username or alias of the org to use
        --input-path          Path to CSV file or directory to upload
        --object-api-name     Override configured object API name
        --source-name         Override configured source name
        --max-concurrent-jobs Override configured max concurrent jobs
    
    Default Path:
        Input: ~/.mindstream/orgs/<username>/csv_files/
    """
    try:
        config = get_effective_config(org)
        org_dir = config_manager.get_org_path(config.username)
        
        # Determine input path
        input_folder = Path(input_path) if input_path else org_dir / "csv_files"
        
        # Create bulk ingest with potential overrides
        bulk_ingest = DataCloudBulkIngest(
            config.access_token,
            config.instance_url,
            object_api_name or config.ingestor.object_api_name,
            source_name or config.ingestor.source_name,
            max_concurrent_jobs or config.ingestor.max_concurrent_jobs
        )
        
        # Get CSV files
        if input_folder.is_file():
            csv_files = [input_folder]
        else:
            csv_files = list(input_folder.glob("*.csv"))
        
        if not csv_files:
            raise click.UsageError(f"No CSV files found in {input_folder}")
        
        bulk_ingest.execute_bulk_ingest(csv_files)
        click.echo(f"Upload completed for {len(csv_files)} files")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.option('--org', help='Username or alias of the org to use')
@click.option('--page-limit', type=int, help='Override page limit')
@click.option('--crawl-url', help='Override crawl URL')
@click.option('--api-key', help='Override API key')
@click.option('--whitelist', help='Override whitelist')
@click.option('--param', '-p', multiple=True, help='Additional crawler parameters')
@click.option('--object-api-name', help='Override object API name')
@click.option('--source-name', help='Override source name')
@click.option('--max-concurrent-jobs', type=int, help='Override max concurrent jobs')
async def pipeline(org, page_limit, crawl_url, api_key, whitelist, param, 
                  object_api_name, source_name, max_concurrent_jobs):
    """Run the complete pipeline with optional overrides
    
    Executes all steps: crawl, convert, and upload.
    Uses stored configuration with optional overrides.
    
    Examples:
        mindstream pipeline
        mindstream pipeline --org myorg
        mindstream pipeline --crawl-url "https://example.com" --source-name "custom"
        mindstream pipeline --page-limit 100 --max-concurrent-jobs 3
    
    Crawler Options:
        --page-limit    Override configured page limit
        --crawl-url     Override configured crawl URL
        --api-key       Override configured API key
        --whitelist     Override configured whitelist
        --param, -p     Additional crawler parameters
    
    Ingestor Options:
        --object-api-name     Override configured object API name
        --source-name         Override configured source name
        --max-concurrent-jobs Override configured max concurrent jobs
    
    General Options:
        --org    Username or alias of the org to use
    """
    try:
        # Execute each step with the provided options
        await crawl(org, None, page_limit, crawl_url, api_key, whitelist, param)
        convert(org, None, None)
        upload(org, None, object_api_name, source_name, max_concurrent_jobs)
        
    except Exception as e:
        click.echo(f"Pipeline failed: {str(e)}", err=True)

@cli.command()
@click.option('--org', help='Username or alias of the org to open')
def open(org):
    """Open the org's directory in file explorer"""
    try:
        # Resolve the username from the org identifier
        target_username = resolve_username(org) if org else None
        if not target_username:
            global_config = config_manager.get_global_config()
            target_username = global_config.current_org
            if not target_username:
                raise click.UsageError("No org selected. Please specify --org or use 'mindstream org use <username>'")
        
        # Get the org path
        org_dir = config_manager.get_org_path(target_username)
        
        # Ensure org_dir is a Path object
        if isinstance(org_dir, str):
            org_dir = Path(org_dir)
        
        # Open the directory in the file explorer
        if platform.system() == "Windows":
            subprocess.Popen(["explorer", str(org_dir)])
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(org_dir)])
        else:
            subprocess.Popen(["xdg-open", str(org_dir)])
        
        click.echo(f"Opened directory for org: {target_username}")
    except Exception as e:
        click.echo(f"Error opening org directory: {str(e)}", err=True)

def main():
    global_config = config_manager.get_global_config()
    current_org = global_config.current_org
    
    if not current_org:
        click.echo("No org selected. Please select an org using 'mindstream org use <username>'")
        return
    
    org_dir = config_manager.get_org_path(current_org)
    org_config = config_manager.get_org_config(current_org)
    
    # Get configuration values with defaults
    api_key = org_config.get('api_key', global_config.crawler.api_key)
    crawl_url = org_config.get('crawl_url', global_config.crawler.crawl_url)
    whitelist = org_config.get('whitelist', global_config.crawler.whitelist)
    page_limit = org_config.get('page_limit', global_config.crawler.page_limit)
    
    # Update paths to use org-specific directories
    output_folder = org_dir / "results"
    csv_output_folder = org_dir / "csv_files"
    
    # Crawl data
    crawler_config = CrawlerDefaults(
        page_limit=page_limit,
        crawl_url=crawl_url,
        api_key=api_key,
        whitelist=whitelist
    )
    crawler = DataCrawler(output_folder, crawler_config)
    crawler.crawl()

    # Convert JSON to CSV
    converter = JSONToCSVConverter(output_folder, csv_output_folder)
    converter.convert()

    # Bulk Ingest to Data Cloud
    csv_files = [f for f in csv_output_folder.glob("*.csv")]
    
    bulk_ingest = DataCloudBulkIngest(
        org_config['access_token'],
        org_config['instance_url'],
        org_config.get('object_api_name', global_config.ingestor.object_api_name),
        org_config.get('source_name', global_config.ingestor.source_name),
        org_config.get('max_concurrent_jobs', global_config.ingestor.max_concurrent_jobs)
    )
    bulk_ingest.execute_bulk_ingest(csv_files)

def resolve_username(identifier: str) -> str:
    """Resolve username from identifier (username or alias)"""
    if not identifier:
        # Try to get current org from global config
        global_config = config_manager.get_global_config()
        if not global_config.current_org:
            raise click.UsageError("No org selected. Please specify --username or use 'mindstream org use <username>'")
        return global_config.current_org
        
    # Try to find username if an alias was provided
    username = SalesforceCLI.get_username_from_alias(identifier)
    if username:
        if not (config_manager.orgs_dir / config_manager._sanitize_username(username)).exists():
            raise click.UsageError(f"Org with alias '{identifier}' (username: {username}) not found in local config")
        return username
        
    # If no alias found, treat the identifier as a username
    if not (config_manager.orgs_dir / config_manager._sanitize_username(identifier)).exists():
        raise click.UsageError(f"Org {identifier} not found")
    
    return identifier

def get_effective_config(org_identifier: Optional[str] = None):
    """Get effective configuration for an org"""
    if org_identifier:
        target_username = resolve_username(org_identifier)
    else:
        global_config = config_manager.get_global_config()
        if not global_config.current_org:
            raise click.UsageError("No org selected. Please specify --org or use 'mindstream org use'")
        target_username = global_config.current_org
    
    return config_manager.get_org_config(target_username)

@cli.command()
def help():
    """Show detailed help information"""
    ctx = click.get_current_context()
    click.echo(ctx.parent.get_help())
    click.echo("\nDetailed command structure:")
    click.echo("""
Commands:
  org
    ── add                 Add and authenticate a new Salesforce org
    ├── use                 Set the current working org
    ├── list               List all connected orgs
    ├── login              Re-authenticate an existing org
    └── regenerate-certs   Regenerate certificates for org(s)
    
  config
    ├── show               Show current configuration
    ├── crawler
    │   └── set           Configure crawler settings
    └── ingestor
        └─ set           Configure ingestor settings
    
  pipeline                 Run the complete pipeline (crawl, convert, ingest)

Common Configuration Options:
  Crawler:
    --page-limit          Number of pages to crawl
    --crawl-url          URL to crawl
    --api-key            API key for crawler service
    --whitelist          Comma-separated list of allowed domains
    -p, --param          Additional parameters (key=value format)
    
  Ingestor:
    --object-api-name    Salesforce object API name
    --source-name        Source name for ingested data
    --max-concurrent-jobs Maximum concurrent ingestion jobs
    
  General:
    --org               Target specific org (username or alias)

Examples:
  1. Set up a new org:
     mindstream org add --alias myorg
     mindstream org use myorg
  
  2. Configure crawler:
     mindstream config crawler set --crawl-url "https://example.com" --api-key "key"
     mindstream config crawler set --page-limit 100 --org myorg
  
  3. Configure ingestor:
     mindstream config ingestor set --object-api-name "CustomDoc"
     mindstream config ingestor set --source-name "custom_source" --org myorg
  
  4. Run pipeline:
     mindstream pipeline
""")

if __name__ == "__main__":
    cli()

