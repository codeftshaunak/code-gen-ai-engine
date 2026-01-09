"""Supabase project provisioning and management."""

import logging
import httpx
import secrets
import string
from typing import Dict, List, Optional, Any
from app.config.settings import settings


logger = logging.getLogger(__name__)


class SupabaseProvisioner:
    """Handles Supabase project creation and management via Management API."""

    def __init__(self):
        """Initialize Supabase provisioner."""
        self.base_url = settings.SUPABASE_API_BASE_URL
        self.access_token = settings.SUPABASE_ACCESS_TOKEN
        
        if not self.access_token:
            logger.warning("SUPABASE_ACCESS_TOKEN not set - Supabase provisioning disabled")
        
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    async def get_organizations(self) -> List[Dict[str, Any]]:
        """
        Get list of Supabase organizations.

        Returns:
            List of organization objects with id, slug, and name

        Raises:
            Exception: If API call fails
        """
        if not self.access_token:
            raise Exception("SUPABASE_ACCESS_TOKEN not configured")

        url = f"{self.base_url}/organizations"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                orgs = response.json()
                
                logger.info(f"Retrieved {len(orgs)} Supabase organizations")
                return orgs
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to get organizations: {e.response.status_code} - {e.response.text}")
                raise Exception(f"Failed to get Supabase organizations: {e.response.text}")
            except Exception as e:
                logger.error(f"Error getting organizations: {str(e)}")
                raise

    async def create_project(
        self,
        org_id: str,
        name: str,
        db_pass: Optional[str] = None,
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Supabase project.

        Args:
            org_id: Organization ID or slug
            name: Project name
            db_pass: Database password (auto-generated if not provided)
            region: AWS region (default from settings if not provided)

        Returns:
            Project info with id, ref, name, region, status

        Raises:
            Exception: If project creation fails
        """
        if not self.access_token:
            raise Exception("SUPABASE_ACCESS_TOKEN not configured")

        # Generate secure password if not provided
        if not db_pass:
            db_pass = self._generate_db_password()

        # Use default region if not specified
        if not region:
            region = settings.SUPABASE_DEFAULT_REGION

        url = f"{self.base_url}/projects"
        payload = {
            "organization_id": org_id,
            "name": name,
            "db_pass": db_pass,
            "region": region,
            "plan": settings.SUPABASE_DEFAULT_PLAN
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                logger.info(f"Creating Supabase project: {name} in region {region}")
                response = await client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                project = response.json()
                
                logger.info(f"Supabase project created: {project.get('id')} - {project.get('name')}")
                return project
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to create project: {e.response.status_code} - {e.response.text}")
                raise Exception(f"Failed to create Supabase project: {e.response.text}")
            except Exception as e:
                logger.error(f"Error creating project: {str(e)}")
                raise

    async def get_api_keys(self, project_id: str) -> Dict[str, str]:
        """
        Get API keys for a Supabase project.

        Args:
            project_id: Project ID or ref

        Returns:
            Dictionary with anon, service_role, and publishable keys

        Raises:
            Exception: If API call fails
        """
        if not self.access_token:
            raise Exception("SUPABASE_ACCESS_TOKEN not configured")

        url = f"{self.base_url}/projects/{project_id}/api-keys"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                keys_list = response.json()
                
                # Parse keys into dictionary
                keys = {}
                for key_obj in keys_list:
                    key_name = key_obj.get("name") or key_obj.get("id")
                    key_type = key_obj.get("type")
                    
                    if key_type == "publishable" or key_name == "default":
                        keys["publishable"] = key_obj.get("api_key")
                    elif key_name == "anon":
                        keys["anon"] = key_obj.get("api_key")
                    elif key_name == "service_role":
                        keys["service_role"] = key_obj.get("api_key")
                
                logger.info(f"Retrieved API keys for project {project_id}")
                return keys
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to get API keys: {e.response.status_code} - {e.response.text}")
                raise Exception(f"Failed to get Supabase API keys: {e.response.text}")
            except Exception as e:
                logger.error(f"Error getting API keys: {str(e)}")
                raise

    async def execute_sql(
        self,
        project_id: str,
        sql_query: str,
        is_migration: bool = True
    ) -> Dict[str, Any]:
        """
        Execute SQL query on Supabase project database.

        Args:
            project_id: Project ID or ref
            sql_query: SQL query to execute
            is_migration: Whether this is a migration (for tracking)

        Returns:
            Execution result with status and message

        Raises:
            Exception: If SQL execution fails
        """
        if not self.access_token:
            raise Exception("SUPABASE_ACCESS_TOKEN not configured")

        url = f"{self.base_url}/projects/{project_id}/database/query"
        
        payload = {
            "query": sql_query
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                logger.info(f"Executing SQL query on project {project_id}")
                
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload
                )
                
                # Handle different response codes
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"SQL query executed successfully")
                    
                    # Track migration if specified
                    if is_migration:
                        migration_record = {
                            "project_id": project_id,
                            "sql": sql_query,
                            "status": "completed",
                            "timestamp": str(__import__('datetime').datetime.utcnow()),
                            "result": result
                        }
                        logger.info(f"Migration tracked: {migration_record}")
                    
                    return {
                        "success": True,
                        "message": "SQL query executed successfully",
                        "result": result,
                        "tracked": is_migration
                    }
                
                elif response.status_code == 400:
                    error_msg = response.text
                    logger.error(f"SQL syntax error: {error_msg}")
                    return {
                        "success": False,
                        "message": f"SQL syntax error: {error_msg}",
                        "status_code": 400
                    }
                
                else:
                    error_msg = response.text
                    logger.error(f"Failed to execute SQL: {response.status_code} - {error_msg}")
                    raise Exception(f"Failed to execute SQL: {error_msg}")
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
                raise Exception(f"Failed to execute SQL: {e.response.text}")
            except Exception as e:
                logger.error(f"Error executing SQL: {str(e)}")
                raise

    @staticmethod
    def _generate_db_password(length: int = 24) -> str:
        """
        Generate a secure database password.

        Args:
            length: Password length (minimum 12)

        Returns:
            Secure random password
        """
        if length < 12:
            length = 12
        
        # Use letters, digits, and safe special characters
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        
        return password


# Global instance
supabase_provisioner = SupabaseProvisioner()
