"""
DevCycle API Client

Handles authentication and API calls to DevCycle Management API
Documentation: https://docs.devcycle.com/management-api/
"""

import time
from typing import Any, Dict, List, Optional

import requests


class DevCycleClient:
    """Client for interacting with the DevCycle Management API."""
    
    def __init__(self, config: Dict[str, str]):
        """
        Initialize DevCycle client.
        
        Args:
            config: Dictionary with clientId, clientSecret, and optional baseUrl
        """
        self.client_id = config.get('clientId')
        self.client_secret = config.get('clientSecret')
        self.base_url = config.get('baseUrl', 'https://api.devcycle.com')
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[float] = None
    
    def authenticate(self) -> str:
        """
        Authenticate with DevCycle using client credentials.
        
        Returns:
            Access token string
        
        Raises:
            Exception: If authentication fails
        """
        try:
            response = requests.post(
                'https://auth.devcycle.com/oauth/token',
                json={
                    'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'audience': 'https://api.devcycle.com/'
                },
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data['access_token']
            # Set expiry with buffer (5 minutes before actual expiry)
            self.token_expiry = time.time() + (data['expires_in'] - 300)
            
            return self.access_token
        
        except requests.exceptions.RequestException as e:
            error_desc = ''
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_desc = e.response.json().get('error_description', str(e))
                except Exception:
                    error_desc = str(e)
            else:
                error_desc = str(e)
            raise Exception(f"DevCycle authentication failed: {error_desc}")
    
    def _ensure_authenticated(self):
        """Ensure we have a valid access token."""
        if not self.access_token or time.time() >= (self.token_expiry or 0):
            self.authenticate()
    
    def request(self, method: str, path: str, data: Optional[Dict] = None) -> Any:
        """
        Make an authenticated API request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            data: Optional request body data
        
        Returns:
            Response JSON data
        
        Raises:
            Exception: If API request fails
        """
        self._ensure_authenticated()
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}{path}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data if data else None
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_msg = e.response.json().get('message', str(e))
                except Exception:
                    error_msg = str(e)
            raise Exception(f"DevCycle API error ({method} {path}): {error_msg}")
    
    def get(self, path: str) -> Any:
        """GET request helper."""
        return self.request('GET', path)
    
    def _unwrap_list_response(self, response: Any) -> List[Dict]:
        """
        Unwrap API response to get list of items.
        
        DevCycle API may return lists directly or wrapped in an object
        like {"items": [...]} or {"data": [...]}.
        """
        if isinstance(response, list):
            return response
        if isinstance(response, dict):
            # Try common wrapper keys used by DevCycle API
            for key in ['items', 'data', 'features', 'environments', 'audiences', 'variables', 'projects']:
                if key in response and isinstance(response[key], list):
                    return response[key]
            # If it's a dict but no list key found, return empty
            return []
        return []
    
    def list_projects(self) -> List[Dict]:
        """List all projects."""
        response = self.get('/v1/projects')
        return self._unwrap_list_response(response)
    
    def list_features(self, project_id: str) -> List[Dict]:
        """Get all features for a project."""
        response = self.get(f'/v1/projects/{project_id}/features')
        return self._unwrap_list_response(response)
    
    def get_feature(self, project_id: str, feature_key: str) -> Dict:
        """Get a specific feature with full details."""
        return self.get(f'/v1/projects/{project_id}/features/{feature_key}')
    
    def list_environments(self, project_id: str) -> List[Dict]:
        """Get all environments for a project."""
        response = self.get(f'/v1/projects/{project_id}/environments')
        return self._unwrap_list_response(response)
    
    def list_audiences(self, project_id: str) -> List[Dict]:
        """Get all audiences for a project."""
        response = self.get(f'/v1/projects/{project_id}/audiences')
        return self._unwrap_list_response(response)
    
    def list_variables(self, project_id: str) -> List[Dict]:
        """Get all variables for a project."""
        response = self.get(f'/v1/projects/{project_id}/variables')
        return self._unwrap_list_response(response)
    
    def get_feature_config(self, project_id: str, feature_key: str, environment_key: str) -> Dict:
        """Get feature configuration for specific environment."""
        return self.get(
            f'/v1/projects/{project_id}/features/{feature_key}/configurations?environment={environment_key}'
        )

