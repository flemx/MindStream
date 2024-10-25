import json
import jwt
from pathlib import Path
import httpx
import sys
import subprocess  # Add this import
from dataclasses import dataclass
from ..config import SF_USERNAME, SF_CONSUMER_KEY
from datetime import datetime, timedelta
from ..utils.config_manager import ConfigManager

CERT_DIR = Path('./certificates')
KEY_PATH = CERT_DIR / 'salesforce.key'
CERT_PATH = CERT_DIR / 'salesforce.crt'
XML_PATH = Path('./salesforce_metadata/mindstream/force-app/main/default/connectedApps/dc_injest.connectedApp-meta.xml')

@dataclass
class Config:
    username: str
    consumer_key: str


def generate_certificates():
    """Generate SSL certificates and update connected app XML."""
    # Create certificates directory if it doesn't exist
    CERT_DIR.mkdir(exist_ok=True)
    
    # Generate certificate and key
    try:
        subprocess.run([
            'openssl', 'req', '-x509', '-sha256', '-nodes',
            '-days', '36500', '-newkey', 'rsa:2048',
            '-keyout', str(KEY_PATH),
            '-out', str(CERT_PATH),
            '-subj', '/CN=MindstreamCert'  # Automatically fill certificate info
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error generating certificates: {e}")
        sys.exit(1)

    # Update XML file with certificate
    try:
        cert_content = CERT_PATH.read_text()
        xml_content = XML_PATH.read_text()
        
        # Find the position to insert the certificate
        oauth_config_pos = xml_content.find('<oauthConfig>')
        if oauth_config_pos == -1:
            raise ValueError("Could not find <oauthConfig> in XML file")
        
        # Insert certificate after <oauthConfig>
        insert_pos = oauth_config_pos + len('<oauthConfig>')
        new_xml_content = (
            xml_content[:insert_pos] + 
            f'\n        <certificate>{cert_content}</certificate>' +
            xml_content[insert_pos:]
        )
        
        XML_PATH.write_text(new_xml_content)
                    
        print("Certificates generated and XML updated successfully")
        
    except Exception as e:
        print(f"Error updating XML file: {e}")
        sys.exit(1)

async def generate_access_token():
    config = Config(
        username=SF_USERNAME,
        consumer_key=SF_CONSUMER_KEY
    )
    # Read private key
    try:
        private_key = KEY_PATH.read_text('utf-8')
    except FileNotFoundError:
        print(f"Error: private key not found at {KEY_PATH}")
        sys.exit(1)

    # Calculate expiration time (2 hours from now)
    exp = datetime.utcnow() + timedelta(hours=2)

    # Generate JWT and sign it with Private Key
    token = jwt.encode(
        payload={
            'exp': int(exp.timestamp()),  # Expiration time as Unix timestamp
            'sub': config.username,
            'iss': config.consumer_key,
            'aud': 'https://login.salesforce.com'
        },
        key=private_key,
        algorithm='RS256'
    )

    print(f"Generated JWT token: {token}")

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
            print(f"Error getting Salesforce token: {e}")
            sys.exit(1)

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
            print(f"Error getting Data Cloud token: {e}")
            sys.exit(1)

        auth_dc = response_dc.json()
        if 'error' in auth_dc:
            raise Exception(auth_dc.get('error_description', 'Unknown error'))

        # Store the new configuration
        config_manager.set_org_config(config.username, {
            'access_token': auth_dc['access_token'],
            'instance_url': auth_dc['instance_url']
        })
        
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
