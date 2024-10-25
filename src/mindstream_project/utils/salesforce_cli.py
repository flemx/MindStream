import subprocess
import json
from typing import Optional, Dict, List

class SalesforceCLI:
    @staticmethod
    def _run_sf_command(command: List[str]) -> Optional[Dict]:
        """Run a Salesforce CLI command and return JSON result."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Error running Salesforce CLI command: {e}")
            return None

    @staticmethod
    def _get_org_list() -> Optional[List[Dict]]:
        """Get list of all orgs from Salesforce CLI."""
        result = SalesforceCLI._run_sf_command(['sf', 'org', 'list', '--json'])
        return result.get('result') if result else None

    @staticmethod
    def is_org_authenticated(alias: Optional[str] = None) -> bool:
        """Check if the org is already authenticated."""
        orgs = SalesforceCLI._get_org_list()
        if not orgs:
            return False
        
        for org in orgs:
            if alias and org.get('alias') == alias:
                return True
        return False

    @staticmethod
    def authenticate_org(alias: Optional[str] = None) -> bool:
        """Authenticate the org using Salesforce CLI."""
        try:
            auth_command = ['sf', 'org', 'login', 'web']
            if alias:
                auth_command.extend(['--alias', alias])
            subprocess.run(auth_command, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error authenticating the org: {e}")
            return False

    @staticmethod
    def get_username_from_alias(alias: str) -> Optional[str]:
        """Get username associated with an alias."""
        orgs = SalesforceCLI._get_org_list()
        if not orgs:
            return None
        
        for org in orgs:
            if org.get('alias') == alias:
                return org.get('username')
        return None

    @staticmethod
    def get_org_info() -> Optional[Dict]:
        """Get information about the current org."""
        return SalesforceCLI._run_sf_command(['sf', 'org', 'display', '--json'])

    @staticmethod
    def deploy_metadata(mdapi_dir: str, target_org: str, wait_time: str = '10') -> bool:
        """Deploy metadata to a Salesforce org."""
        try:
            deploy_command = [
                'sf', 'project', 'deploy', 'start',
                '--metadata-dir', mdapi_dir,
                '--target-org', target_org,
                '--wait', wait_time
            ]
            SalesforceCLI._run_sf_command(deploy_command)
            return True
        except Exception as e:
            print(f"Error deploying metadata: {e}")
            return False
