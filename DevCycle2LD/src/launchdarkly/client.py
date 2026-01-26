"""
LaunchDarkly API Client

Handles API calls to LaunchDarkly REST API
Documentation: https://launchdarkly.com/docs/api
"""

import json
import time
from typing import Any, Dict, List, Optional

import requests


class LaunchDarklyClient:
    """Client for interacting with the LaunchDarkly API."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LaunchDarkly client.
        
        Args:
            config: Dictionary with apiToken, optional baseUrl, and dryRun flag
        """
        self.api_token = config.get('apiToken')
        self.base_url = config.get('baseUrl', 'https://app.launchdarkly.com/api/v2')
        self.dry_run = config.get('dryRun', True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': self.api_token,
            'Content-Type': 'application/json'
        })
    
    def request(
        self, 
        method: str, 
        path: str, 
        data: Optional[Dict] = None, 
        content_type: str = 'application/json',
        max_retries: int = 5,
        base_delay: float = 1.0
    ) -> Any:
        """
        Make an API request with rate limit handling.
        
        Args:
            method: HTTP method
            path: API endpoint path
            data: Optional request body data
            content_type: Content-Type header value
            max_retries: Maximum number of retries on rate limit (429)
            base_delay: Base delay in seconds for exponential backoff
        
        Returns:
            Response JSON data
        
        Raises:
            Exception: If API request fails after all retries
        """
        url = f"{self.base_url}{path}"
        headers = {'Content-Type': content_type}
        
        for attempt in range(max_retries + 1):
            try:
                # When using custom content type (like semantic patch), 
                # we must use data= instead of json= to prevent requests
                # from overriding our Content-Type header
                if content_type != 'application/json' and data:
                    response = self.session.request(
                        method=method,
                        url=url,
                        headers=headers,
                        data=json.dumps(data)
                    )
                else:
                    response = self.session.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=data if data else None
                    )
                response.raise_for_status()
                
                if response.content:
                    return response.json()
                return None
            
            except requests.exceptions.RequestException as e:
                status_code = None
                if hasattr(e, 'response') and e.response is not None:
                    status_code = e.response.status_code
                
                # Handle rate limiting (429)
                if status_code == 429:
                    if attempt >= max_retries:
                        raise Exception(f"LaunchDarkly API rate limit exceeded after {max_retries} retries ({method} {path})")
                    
                    # Get retry delay from Retry-After header or use exponential backoff
                    retry_after = None
                    if hasattr(e, 'response') and e.response is not None:
                        retry_after = e.response.headers.get('Retry-After')
                    
                    if retry_after:
                        delay = float(retry_after)
                    else:
                        delay = base_delay * (2 ** attempt)
                    
                    print(f"  ⏳ [LaunchDarkly] Rate limited, waiting {delay:.1f}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(delay)
                    continue
                
                # Other errors - don't retry
                error_msg = str(e)
                status_code_str = str(status_code) if status_code else ''
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        response_json = e.response.json()
                        error_msg = response_json.get('message', str(e))
                        if 'errors' in response_json:
                            error_msg += f" - Details: {response_json['errors']}"
                    except Exception:
                        error_msg = str(e)
                
                raise Exception(f"LaunchDarkly API error ({status_code_str} {method} {path}): {error_msg}")
        
        # Should not reach here, but just in case
        raise Exception(f"LaunchDarkly API request failed after {max_retries} retries ({method} {path})")
    
    # ==================== Flag Operations ====================
    
    def list_flags(self, project_key: str) -> Dict:
        """List all feature flags in a project."""
        return self.request('GET', f'/flags/{project_key}')
    
    def get_flag(self, project_key: str, flag_key: str) -> Dict:
        """Get a specific feature flag."""
        return self.request('GET', f'/flags/{project_key}/{flag_key}')
    
    def flag_exists(self, project_key: str, flag_key: str) -> bool:
        """Check if a flag exists."""
        try:
            self.get_flag(project_key, flag_key)
            return True
        except Exception as e:
            if '404' in str(e):
                return False
            raise
    
    def create_flag(self, project_key: str, flag_data: Dict) -> Dict:
        """Create a new feature flag."""
        if self.dry_run:
            print(f"[DRY-RUN] Would create flag: {flag_data.get('key')}")
            return {'key': flag_data.get('key'), '_dryRun': True}
        
        return self.request('POST', f'/flags/{project_key}', flag_data)
    
    def update_flag(
        self, 
        project_key: str, 
        flag_key: str, 
        patch_operations: List[Dict]
    ) -> Dict:
        """Update a feature flag using JSON Patch."""
        if self.dry_run:
            print(f"[DRY-RUN] Would update flag: {flag_key}")
            print(f"[DRY-RUN] Operations: {json.dumps(patch_operations, indent=2)}")
            return {'key': flag_key, '_dryRun': True}
        
        return self.request(
            'PATCH',
            f'/flags/{project_key}/{flag_key}',
            patch_operations,
            'application/json-patch+json'
        )
    
    def update_flag_targeting(
        self, 
        project_key: str, 
        flag_key: str, 
        environment_key: str, 
        targeting: Dict
    ) -> Optional[Dict]:
        """Update flag targeting for a specific environment using JSON Patch."""
        operations = []
        env_path = f'/environments/{environment_key}'
        
        # Turn flag on/off
        if targeting.get('on') is not None:
            operations.append({
                'op': 'replace',
                'path': f'{env_path}/on',
                'value': targeting['on']
            })
        
        # Set fallthrough variation (by index)
        fallthrough = targeting.get('fallthrough', {})
        if fallthrough.get('variation') is not None:
            operations.append({
                'op': 'replace',
                'path': f'{env_path}/fallthrough/variation',
                'value': fallthrough['variation']
            })
        
        # Add targeting rules
        rules = targeting.get('rules', [])
        for rule in rules:
            clauses = rule.get('clauses', [])
            if not clauses:
                continue
            
            # Build rule object for LaunchDarkly
            ld_rule = {
                'clauses': clauses
            }
            
            # Either variation OR rollout
            if rule.get('rolloutWeights'):
                rollout_weights = rule['rolloutWeights']
                weighted_variations = [
                    {'variation': int(var_id), 'weight': weight}
                    for var_id, weight in rollout_weights.items()
                ]
                ld_rule['rollout'] = {
                    'variations': weighted_variations
                }
            elif rule.get('variationId') is not None:
                ld_rule['variation'] = rule['variationId']
            else:
                ld_rule['variation'] = 0
            
            operations.append({
                'op': 'add',
                'path': f'{env_path}/rules/-',
                'value': ld_rule
            })
        
        # Add individual targets
        targets = targeting.get('targets', [])
        for target in targets:
            values = target.get('values', [])
            if not values:
                continue
            
            variation_idx = target['variationId']
            for value in values:
                operations.append({
                    'op': 'add',
                    'path': f'{env_path}/targets/{variation_idx}/values/-',
                    'value': value
                })
        
        if not operations:
            return None
        
        return self.update_flag(project_key, flag_key, operations)
    
    # ==================== Segment Operations ====================
    
    def list_segments(self, project_key: str, environment_key: str) -> Dict:
        """List all segments in a project/environment."""
        return self.request('GET', f'/segments/{project_key}/{environment_key}')
    
    def get_segment(self, project_key: str, environment_key: str, segment_key: str) -> Dict:
        """Get a specific segment."""
        return self.request('GET', f'/segments/{project_key}/{environment_key}/{segment_key}')
    
    def segment_exists(self, project_key: str, environment_key: str, segment_key: str) -> bool:
        """Check if a segment exists."""
        try:
            self.get_segment(project_key, environment_key, segment_key)
            return True
        except Exception as e:
            if '404' in str(e):
                return False
            raise
    
    def create_segment(self, project_key: str, environment_key: str, segment_data: Dict) -> Dict:
        """Create a new segment."""
        if self.dry_run:
            print(f"[DRY-RUN] Would create segment: {segment_data.get('key')}")
            return {'key': segment_data.get('key'), '_dryRun': True}
        
        return self.request('POST', f'/segments/{project_key}/{environment_key}', segment_data)
    
    def update_segment(
        self, 
        project_key: str, 
        environment_key: str, 
        segment_key: str, 
        patch_operations: Dict
    ) -> Dict:
        """Update a segment."""
        if self.dry_run:
            print(f"[DRY-RUN] Would update segment: {segment_key}")
            return {'key': segment_key, '_dryRun': True}
        
        return self.request(
            'PATCH',
            f'/segments/{project_key}/{environment_key}/{segment_key}',
            patch_operations,
            'application/json; domain-model=launchdarkly.semanticpatch'
        )
    
    # ==================== Environment Operations ====================
    
    def list_environments(self, project_key: str) -> List[Dict]:
        """List all environments in a project."""
        # Use the dedicated environments endpoint
        response = self.request('GET', f'/projects/{project_key}/environments')
        
        # Handle case where response might not be a dict
        if not isinstance(response, dict):
            if isinstance(response, list):
                return response
            print(f"  [DEBUG] Unexpected environments response type: {type(response)}")
            return []
        
        # LaunchDarkly returns environments in an "items" array
        environments = response.get('items', [])
        
        # Fallback: check if environments is directly in response
        if not environments and 'environments' in response:
            environments = response.get('environments', [])
        
        if not environments:
            # Debug: print available keys to understand the structure
            print(f"  [DEBUG] Environments response keys: {list(response.keys())}")
        
        return environments if isinstance(environments, list) else []
    
    def environment_exists(self, project_key: str, environment_key: str) -> bool:
        """Check if an environment exists."""
        try:
            self.request('GET', f'/projects/{project_key}/environments/{environment_key}')
            return True
        except Exception as e:
            if '404' in str(e):
                return False
            raise
    
    def create_environment(self, project_key: str, environment_data: Dict) -> Dict:
        """
        Create a new environment in a project.
        
        Args:
            project_key: The project key
            environment_data: Dict with key, name, color, and optional fields
        
        Returns:
            Created environment data
        """
        if self.dry_run:
            print(f"[DRY-RUN] Would create environment: {environment_data.get('key')}")
            return {'key': environment_data.get('key'), '_dryRun': True}
        
        return self.request('POST', f'/projects/{project_key}/environments', environment_data)
    
    # ==================== Project Operations ====================
    
    def get_project(self, project_key: str) -> Dict:
        """Get project details."""
        return self.request('GET', f'/projects/{project_key}')

