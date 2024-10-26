import subprocess
import json
from typing import Optional, Dict, List
from mindstream_project.utils.logging_config import get_logger, log_function_call

logger = get_logger(__name__)

class SalesforceCLI:
    @staticmethod
    @log_function_call
    def _run_sf_command(command: List[str]) -> Optional[Dict]:
        """Run a Salesforce CLI command and return JSON result."""
        try:
            logger.debug(f"Running SF command: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            # Check if the output is valid JSON
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as json_error:
                 # Handle non-JSON output
                if "Status: Succeeded" in result.stdout:
                    logger.debug("Deployment succeeded based on command output.")
                    return {"status": "Succeeded"}
                logger.error(f"JSON decode error: {json_error}")
                logger.error(f"Command output was: {result.stdout}")
                return None

        except subprocess.CalledProcessError as e:
            logger.error(f"Error running Salesforce CLI command: {e}")
            return None

    @staticmethod
    def _get_org_list() -> Optional[List[Dict]]:
        """Get list of all orgs from Salesforce CLI."""
        result = SalesforceCLI._run_sf_command(['sf', 'org', 'list', '--json'])
        logger.debug(f"Org list result: {result}")
        if isinstance(result, dict) and 'result' in result:
            return result.get('result')
        else:
            logger.error("Unexpected result format, expected a dictionary with a 'result' key.")
            return None

    @staticmethod
    def is_org_authenticated(alias: Optional[str] = None) -> bool:
        """Check if the org is already authenticated."""
        if not alias:
            logger.error("Alias must be provided to check authentication status.")
            return False

        try:
            result = SalesforceCLI.get_org_info(alias)
            if result and 'status' in result and result['status'] == 'Active':
                return True
        except Exception as e:
            logger.error(f"Error in is_org_authenticated: {e}", exc_info=True)
            return False

        return False

    @staticmethod
    def authenticate_org(alias: Optional[str] = None) -> Optional[Dict]:
        """Authenticate the org using Salesforce CLI and return org info."""
        try:
            auth_command = ['sf', 'org', 'login', 'web']
            if alias:
                auth_command.extend(['--alias', alias])
            subprocess.run(auth_command, check=True)
            
            # After successful authentication, get org info
            return SalesforceCLI.get_org_info(alias)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error authenticating the org: {e}")
            return None

    @staticmethod
    def get_username_from_alias(alias: str) -> Optional[str]:
        """Get username associated with an alias."""
        org_info = SalesforceCLI.get_org_info(alias)
        if org_info:
            return org_info.get('username')
        return None

    @staticmethod
    def get_org_info(alias: Optional[str] = None) -> Optional[Dict]:
        """Get information about the specified org."""
        command = ['sf', 'org', 'display', '--json']
        if alias:
            command.extend(['-o', alias])
        
        result = SalesforceCLI._run_sf_command(command)
        
        # Ensure the result is a dictionary and contains the expected keys
        if isinstance(result, dict) and 'result' in result:
            return result['result']
        else:
            logger.error("Unexpected result format, expected a dictionary with a 'result' key.")
            return None

    @staticmethod
    def deploy_metadata(mdapi_dir: str, target_org: str, wait_time: str = '10') -> bool:
        """Deploy metadata to a Salesforce org."""
        try:
            deploy_command = [
                'sf', 'project', 'deploy', 'start',
                '--metadata-dir', mdapi_dir,
                '--target-org', target_org,
                '--wait', wait_time,
                '--ignore-conflicts',
                '--ignore-warnings'
            ]
            result = SalesforceCLI._run_sf_command(deploy_command)
            if result:
                return True
            else:
                logger.error("Deployment failed.")
                return False
        except Exception as e:
            print(f"Error deploying metadata: {e}")
            return False
