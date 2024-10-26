import json
import jwt
from pathlib import Path
import httpx
import sys
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from ..utils.config_manager import ConfigManager
import shutil
import re
from mindstream_project.utils.salesforce_cli import SalesforceCLI
from mindstream_project.utils.logging_config import get_logger, log_function_call

logger = get_logger(__name__)

config_manager = ConfigManager()

@dataclass
class Config:
    username: str
    consumer_key: str
    private_key_path: Path

def generate_certificates(org_dir: Path):
    """Generate SSL certificates and update connected app XML for a specific org."""
    try:
        logger.debug(f"Starting certificate generation for org directory: {org_dir}")
        CERT_DIR = org_dir / 'certificates'
        KEY_PATH = CERT_DIR / 'salesforce.key'
        CERT_PATH = CERT_DIR / 'salesforce.crt'
        MDAPI_DIR = org_dir / 'mdapi'
        CONNECTED_APP_DIR = MDAPI_DIR / 'connectedApps'
        CONNECTED_APP_PATH = CONNECTED_APP_DIR / 'dc_injest.connectedApp'
        
        logger.debug(f"Working with org directory: {org_dir}")
        logger.debug("Creating certificates directory if it doesn't exist")
        
        # Create certificates directory if it doesn't exist
        CERT_DIR.mkdir(exist_ok=True)

        print("Generating SSL certificates...")
        logger.debug("Running OpenSSL command to generate certificates")
        # Generate certificate and key
        try:
            subprocess.run([
                'openssl', 'req', '-x509', '-sha256', '-nodes',
                '-days', '36500', '-newkey', 'rsa:2048',
                '-keyout', str(KEY_PATH),
                '-out', str(CERT_PATH),
                '-subj', '/CN=MindstreamCert'  # Automatically fill certificate info
            ], check=True)
            print("Certificates generated successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error generating certificates: {e}")
            raise

        # Copy MDAPI files to org directory
        source_mdapi_dir = Path('salesforce_metadata') / 'mindstream' / 'mdapi'
        if not source_mdapi_dir.exists():
            logger.error(f"Error: MDAPI source directory does not exist at: {source_mdapi_dir}")
            raise FileNotFoundError(f"MDAPI source directory not found: {source_mdapi_dir}")
        
        # Create parent directories if they don't exist
        MDAPI_DIR.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove existing MDAPI directory if it exists
        if MDAPI_DIR.exists():
            shutil.rmtree(MDAPI_DIR)
        
        # Copy the directory
        try:
            shutil.copytree(source_mdapi_dir, MDAPI_DIR)
            logger.debug(f"MDAPI files copied from {source_mdapi_dir} to {MDAPI_DIR}")
        except Exception as e:
            logger.error(f"Error copying MDAPI files: {e}")
            raise

        logger.debug("Updating Connected App XML with certificate...")
        # Update XML file with certificate
        try:
            cert_content = CERT_PATH.read_text().strip()
            connected_app_path = CONNECTED_APP_PATH
            xml_content = connected_app_path.read_text()
            
            # Insert certificate into <certificate></certificate> tag
            new_xml_content = re.sub(
                r'<certificate>.*?</certificate>',
                f'<certificate>{cert_content}</certificate>',
                xml_content,
                flags=re.DOTALL
            )
            
            connected_app_path.write_text(new_xml_content)
            logger.debug("Connected App XML updated successfully")
        except Exception as e:
            logger.error(f"Error updating Connected App XML file: {e}")
            raise

        # Deploy the updated Connected App to Salesforce
        try:
            # Read the org config to get the actual username
            config_path = org_dir / 'config.json'
            if not config_path.exists():
                raise FileNotFoundError(f"Org config file not found at: {config_path}")
            
            with open(config_path, 'r') as f:
                org_config = json.load(f)
                
            username = org_config.get('username')
            if not username:
                raise ValueError("Username not found in org config")
                
            logger.debug(f"Deploying Connected App to Salesforce org: {username}")
            
            if SalesforceCLI.deploy_metadata(str(MDAPI_DIR), username):
                logger.info("Connected App deployed successfully")
                print("Connected App deployed successfully")
            else:
                raise Exception("Failed to deploy Connected App")
        except Exception as e:
            logger.error(f"Error deploying Connected App: {e}")
            raise

    except Exception as e:
        logger.error(f"Error in generate_certificates: {str(e)}")
        raise

async def generate_access_token(username: str = None):
    """Generate access token for specified org or current org"""
    logger.debug(f"Generating access token for username: {username}")
    if not username:
        global_config = config_manager.get_global_config()
        username = global_config.current_org
        if not username:
            raise ValueError("No org specified and no current org set")

    org_dir = config_manager.get_org_path(username)
    org_config = config_manager.get_org_config(username)
    
    if not org_config:
        raise ValueError(f"No configuration found for org: {username}")
    
    # Get required configuration
    consumer_key = org_config.get('consumer_key')
    login_url = org_config.get('login_url', 'https://login.salesforce.com')  # Get login_url with fallback
    if not consumer_key:
        raise ValueError(f"No consumer key found for org: {username}")

    config = Config(
        username=username,
        consumer_key=consumer_key,
        private_key_path=org_dir / 'certificates' / 'salesforce.key'
    )

    # Read private key
    try:
        private_key = config.private_key_path.read_text('utf-8')
    except FileNotFoundError:
        raise FileNotFoundError(f"Private key not found at {config.private_key_path}")

    # Calculate expiration time (2 hours from now)
    exp = datetime.utcnow() + timedelta(hours=2)

    # Update JWT payload with dynamic login_url
    token = jwt.encode(
        payload={
            'exp': int(exp.timestamp()),
            'sub': config.username,
            'iss': config.consumer_key,
            'aud': login_url  # Use dynamic login_url instead of hardcoded value
        },
        key=private_key,
        algorithm='RS256'
    )

    print(f"Generated JWT token for {username}")
    logger.debug(f"JWT token generated for {username}")

    async with httpx.AsyncClient() as client:
        # Get Salesforce Auth Token using dynamic login_url
        try:
            response_sf = await client.post(
                f'{login_url}/services/oauth2/token',  # Use dynamic login_url
                headers={'content-type': 'application/x-www-form-urlencoded'},
                data={
                    'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                    'assertion': token
                }
            )
            response_sf.raise_for_status()
            logger.debug("Salesforce Auth Token obtained successfully")
        except httpx.HTTPError as e:
            logger.error(f"Error getting Salesforce token: {e}", exc_info=True)
            raise Exception(f"Error getting Salesforce token: {e}")

        auth_sf = response_sf.json()
        if 'error' in auth_sf:
            raise Exception(auth_sf.get('error_description', 'Unknown error'))

        # Get Data Cloud Auth Token
        try:
            response_dc = await client.post(
                f"{auth_sf['instance_url']}/services/a360/token",
                headers={'content-type': 'application/x-www-form-urlencoded'},
                data={
                    'grant_type': 'urn:salesforce:grant-type:external:cdp',
                    'subject_token': auth_sf['access_token'],
                    'subject_token_type': 'urn:ietf:params:oauth:token-type:access_token'
                }
            )
            response_dc.raise_for_status()
            logger.debug("Data Cloud Auth Token obtained successfully")
        except httpx.HTTPError as e:
            logger.error(f"Error getting Data Cloud token: {e}", exc_info=True)
            raise Exception(f"Error getting Data Cloud token: {e}")

        auth_dc = response_dc.json()
        if 'error' in auth_dc:
            raise Exception(auth_dc.get('error_description', 'Unknown error'))
        
        return auth_dc

async def main():
    try:
        logger.debug("Starting main function")
        auth = await generate_access_token()
        print(auth)
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
