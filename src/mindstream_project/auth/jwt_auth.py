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

config_manager = ConfigManager()

@dataclass
class Config:
    username: str
    consumer_key: str
    private_key_path: Path

def generate_certificates(org_dir: Path):
    """Generate SSL certificates and update connected app XML for a specific org."""
    CERT_DIR = org_dir / 'certificates'
    KEY_PATH = CERT_DIR / 'salesforce.key'
    CERT_PATH = CERT_DIR / 'salesforce.crt'
    MDAPI_DIR = org_dir / 'mdapi'
    CONNECTED_APP_DIR = MDAPI_DIR / 'connectedApps'
    CONNECTED_APP_PATH = CONNECTED_APP_DIR / 'dc_injest.connectedApp'
    PACKAGE_XML_PATH = MDAPI_DIR / 'package.xml'

    # Create certificates directory if it doesn't exist
    CERT_DIR.mkdir(exist_ok=True)

    print("Generating SSL certificates...")
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
        print(f"Error generating certificates: {e}")
        sys.exit(1)

    # Copy MDAPI files to org directory
    source_mdapi_dir = Path('salesforce_metadata') / 'mindstream' / 'mdapi'
    if not source_mdapi_dir.exists():
        print(f"Error: MDAPI source directory does not exist at: {source_mdapi_dir}")
        sys.exit(1)
    
    # Create parent directories if they don't exist
    MDAPI_DIR.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing MDAPI directory if it exists
    if MDAPI_DIR.exists():
        shutil.rmtree(MDAPI_DIR)
    
    # Copy the directory
    try:
        shutil.copytree(source_mdapi_dir, MDAPI_DIR)
        print(f"MDAPI files copied from {source_mdapi_dir} to {MDAPI_DIR}")
    except Exception as e:
        print(f"Error copying MDAPI files: {e}")
        sys.exit(1)

    print("Updating Connected App XML with certificate...")
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
        print("Connected App XML updated successfully.")
    except Exception as e:
        print(f"Error updating Connected App XML file: {e}")
        sys.exit(1)

    # Deploy metadata to Salesforce org
    org_config = config_manager.get_org_config(org_dir.name.replace('_at_', '@').replace('_dot_', '.'))
    alias = org_config.get('alias') or org_config.get('username')
    deploy_command = [
        'sf', 'project', 'deploy', 'start',
        '--metadata-dir', str(MDAPI_DIR),
        '--target-org', alias,
        '--wait', '10'
    ]
    print("Deploying metadata to Salesforce org...")
    try:
        subprocess.run(deploy_command, check=True)
        print("Metadata deployed successfully to org.")
    except subprocess.CalledProcessError as e:
        print(f"Error deploying metadata to Salesforce org: {e}")
        sys.exit(1)

async def generate_access_token(username: str = None):
    """Generate access token for specified org or current org"""
    if not username:
        global_config = config_manager.get_global_config()
        username = global_config.get('current_org')
        if not username:
            raise ValueError("No org specified and no current org set")

    org_dir = config_manager.get_org_path(username)
    org_config = config_manager.get_org_config(username)
    
    if not org_config:
        raise ValueError(f"No configuration found for org: {username}")
    
    # Get required configuration
    consumer_key = org_config.get('consumer_key')
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

    # Generate JWT and sign it with Private Key
    token = jwt.encode(
        payload={
            'exp': int(exp.timestamp()),
            'sub': config.username,
            'iss': config.consumer_key,
            'aud': 'https://login.salesforce.com'
        },
        key=private_key,
        algorithm='RS256'
    )

    print(f"Generated JWT token for {username}")

    async with httpx.AsyncClient() as client:
        # Get Salesforce Auth Token
        try:
            response_sf = await client.post(
                'https://login.salesforce.com/services/oauth2/token',
                headers={'content-type': 'application/x-www-form-urlencoded'},
                data={
                    'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                    'assertion': token
                }
            )
            response_sf.raise_for_status()
        except httpx.HTTPError as e:
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
        except httpx.HTTPError as e:
            raise Exception(f"Error getting Data Cloud token: {e}")

        auth_dc = response_dc.json()
        if 'error' in auth_dc:
            raise Exception(auth_dc.get('error_description', 'Unknown error'))
        
        return auth_dc

async def main():
    try:
        auth = await generate_access_token()
        print(auth)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
