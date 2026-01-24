"""
DevCycle Feature Extractor

Extracts all features, audiences, and configurations from DevCycle
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .client import DevCycleClient


class DevCycleExtractor:
    """Extracts all data needed for migration from DevCycle."""
    
    def __init__(self, config: Dict[str, str]):
        """
        Initialize extractor.
        
        Args:
            config: Dictionary with clientId, clientSecret, and projectId
        """
        self.client = DevCycleClient({
            'clientId': config.get('clientId'),
            'clientSecret': config.get('clientSecret')
        })
        self.project_id = config.get('projectId')
    
    def extract_all(self) -> Dict[str, Any]:
        """
        Extract all data needed for migration.
        
        Returns:
            Dictionary containing all extracted data
        """
        print(f"Extracting data from DevCycle project: {self.project_id}")
        
        # Get environments first (needed for feature configs)
        environments = self.extract_environments()
        print(f"  Found {len(environments)} environments")
        
        # Get all features
        features = self.extract_features(environments)
        print(f"  Found {len(features)} features")
        
        # Get all audiences
        audiences = self.extract_audiences()
        print(f"  Found {len(audiences)} audiences")
        
        # Get all variables
        variables = self.extract_variables()
        print(f"  Found {len(variables)} variables")
        
        return {
            'extractedAt': datetime.utcnow().isoformat() + 'Z',
            'projectId': self.project_id,
            'environments': environments,
            'features': features,
            'audiences': audiences,
            'variables': variables
        }
    
    def extract_environments(self) -> List[Dict[str, Any]]:
        """Extract all environments."""
        environments = self.client.list_environments(self.project_id)
        
        result = []
        for env in environments:
            if isinstance(env, dict):
                result.append({
                    'key': env.get('key'),
                    'name': env.get('name'),
                    'type': env.get('type'),
                    '_id': env.get('_id')
                })
            elif isinstance(env, str):
                # Handle case where env is just a key string
                result.append({
                    'key': env,
                    'name': env,
                    'type': None,
                    '_id': None
                })
        return result
    
    def extract_features(self, environments: List[Dict]) -> List[Dict[str, Any]]:
        """Extract all features with their configurations per environment."""
        features_list = self.client.list_features(self.project_id)
        features = []
        
        for feature in features_list:
            # Handle case where feature might be a string
            if isinstance(feature, str):
                feature_key = feature
                feature = {'key': feature_key}
            elif isinstance(feature, dict):
                feature_key = feature.get('key')
            else:
                print(f"    Skipping unknown feature type: {type(feature)}")
                continue
            
            print(f"    Extracting feature: {feature_key}")
            
            # Get full feature details
            full_feature = self.client.get_feature(self.project_id, feature_key)
            
            # Ensure full_feature is a dict
            if not isinstance(full_feature, dict):
                print(f"    Warning: Feature {feature_key} returned unexpected type: {type(full_feature)}")
                full_feature = {}
            
            # Build variation ID to key mapping from the feature's variations
            variation_id_to_key = {}
            for v in full_feature.get('variations', []):
                if isinstance(v, dict) and v.get('_id') and v.get('key'):
                    variation_id_to_key[v['_id']] = v['key']
            
            # Build environment configurations
            environment_configs = {}
            
            for env in environments:
                env_key = env.get('key') if isinstance(env, dict) else env
                
                # First try to extract from the feature response
                env_config = self._extract_environment_config(full_feature, env_key, variation_id_to_key)
                
                # If not found, try fetching configurations separately
                if not env_config:
                    try:
                        config_response = self.client.get_feature_config(
                            self.project_id, feature_key, env_key
                        )
                        if config_response and isinstance(config_response, (dict, list)):
                            # If it's a list, get the first item
                            if isinstance(config_response, list) and len(config_response) > 0:
                                config_response = config_response[0]
                            if isinstance(config_response, dict):
                                env_config = self._extract_config_from_response(config_response, variation_id_to_key)
                    except Exception as e:
                        # Config might not exist for this environment, that's OK
                        pass
                
                if env_config:
                    environment_configs[env_key] = env_config
            
            # Get tags safely
            tags = feature.get('tags', [])
            if not isinstance(tags, list):
                tags = []
            
            features.append({
                'key': feature.get('key'),
                'name': feature.get('name'),
                'description': feature.get('description', ''),
                'type': feature.get('type'),
                'tags': tags,
                'createdAt': feature.get('createdAt'),
                'updatedAt': feature.get('updatedAt'),
                
                # Variations
                'variations': self._extract_variations(full_feature),
                
                # Environment-specific configurations
                'environments': environment_configs,
                
                # Store original for reference
                '_original': full_feature
            })
        
        return features
    
    def _extract_environment_config(
        self, 
        feature: Dict, 
        environment_key: str,
        variation_id_to_key: Dict[str, str] = None
    ) -> Optional[Dict]:
        """Extract environment-specific configuration for a feature."""
        # DevCycle stores configurations per environment
        configurations = feature.get('configurations', [])
        if not isinstance(configurations, list):
            configurations = []
        
        config = None
        
        for c in configurations:
            if not isinstance(c, dict):
                continue
            env = c.get('environment')
            if env == environment_key or (isinstance(env, dict) and env.get('key') == environment_key):
                config = c
                break
        
        if not config:
            return None
        
        return self._extract_config_from_response(config, variation_id_to_key)
    
    def _extract_config_from_response(
        self, 
        config: Dict, 
        variation_id_to_key: Dict[str, str] = None
    ) -> Optional[Dict]:
        """Extract configuration from a config response dict."""
        if not isinstance(config, dict):
            return None
        
        variation_id_to_key = variation_id_to_key or {}
        
        # Safely get defaultServe
        default_serve = config.get('defaultServe')
        if not isinstance(default_serve, dict):
            default_serve = {}
        
        # Map default serve variation ID to key
        default_variation_id = default_serve.get('_variation') or default_serve.get('variation')
        default_variation = variation_id_to_key.get(default_variation_id, default_variation_id)
        
        return {
            # On/Off state
            'status': config.get('status'),  # 'active' or 'inactive'
            'on': config.get('status') == 'active',
            
            # Targeting rules
            'targets': self._extract_targets(config.get('targets', []), variation_id_to_key),
            
            # Default serve (fallthrough)
            'defaultServe': {
                'variation': default_variation,
                'percentage': default_serve.get('percentage')
            },
            
            # Users/contexts scheduled for specific variations
            'forcedUsers': config.get('forcedUsers', [])
        }
    
    def _extract_targets(self, targets: List[Dict], variation_id_to_key: Dict[str, str] = None) -> List[Dict]:
        """Extract targeting rules from DevCycle format."""
        if not isinstance(targets, list):
            return []
        
        variation_id_to_key = variation_id_to_key or {}
        
        result = []
        for target in targets:
            if not isinstance(target, dict):
                continue
            
            # Extract distribution safely
            distribution = target.get('distribution', [])
            if not isinstance(distribution, list):
                distribution = []
            
            extracted_distribution = []
            for d in distribution:
                if isinstance(d, dict):
                    # DevCycle uses _variation (ID) in config responses
                    variation_id = d.get('_variation') or d.get('variation')
                    # Map ID to key if we have the mapping
                    variation_key = variation_id_to_key.get(variation_id, variation_id) if variation_id else None
                    
                    extracted_distribution.append({
                        'variation': variation_key,
                        '_variationId': variation_id,  # Keep original ID for reference
                        'percentage': d.get('percentage')
                    })
            
            result.append({
                'name': target.get('name'),
                
                # Audience definition (inline or reference)
                'audience': self._extract_audience(target.get('audience')),
                
                # Distribution (which variations at what percentages)
                'distribution': extracted_distribution,
                
                # Rollout settings
                'rollout': target.get('rollout')
            })
        
        return result
    
    def _extract_audience(self, audience: Optional[Dict]) -> Optional[Dict]:
        """Extract audience/filter definition."""
        if not audience:
            return None
        
        # Check if it's a reference to a saved audience
        if audience.get('_audience'):
            return {
                'type': 'reference',
                'audienceId': audience['_audience']
            }
        
        # Get filters - can be a dict {"operator": "and", "filters": [...]} or a list
        raw_filters = audience.get('filters', [])
        
        if isinstance(raw_filters, dict):
            # DevCycle returns filters as {"operator": "and/or", "filters": [...]}
            filter_list = raw_filters.get('filters', [])
            operator = raw_filters.get('operator', 'and')
        else:
            filter_list = raw_filters
            operator = 'and'
        
        # Inline audience definition
        return {
            'type': 'inline',
            'operator': operator,
            'filters': self._extract_filters(filter_list)
        }
    
    def _extract_filters(self, filters: List[Dict]) -> List[Dict]:
        """Extract filter conditions."""
        if not isinstance(filters, list):
            return []
        
        result = []
        
        for filter_item in filters:
            if not isinstance(filter_item, dict):
                continue
            
            # Handle nested filter groups (AND/OR)
            if filter_item.get('filters'):
                result.append({
                    'type': 'group',
                    'operator': filter_item.get('operator', 'and'),
                    'filters': self._extract_filters(filter_item['filters'])
                })
            else:
                # Individual filter
                result.append({
                    'type': filter_item.get('type'),           # 'user', 'all', etc.
                    'subType': filter_item.get('subType'),     # 'user_id', 'email', 'customData', etc.
                    'comparator': filter_item.get('comparator'),  # '=', '!=', 'contains', etc.
                    'values': filter_item.get('values', []),
                    
                    # For custom data filters
                    'dataKey': filter_item.get('dataKey'),
                    'dataKeyType': filter_item.get('dataKeyType')
                })
        
        return result
    
    def _extract_variations(self, feature: Dict) -> List[Dict]:
        """Extract variations from feature."""
        variations = feature.get('variations', [])
        
        result = []
        for v in variations:
            # Handle case where variation might be a string (just the key)
            if isinstance(v, str):
                result.append({
                    'key': v,
                    'name': v,
                    'variables': []
                })
                continue
            
            # Handle case where variation is a dict
            if isinstance(v, dict):
                variables_data = v.get('variables', [])
                extracted_variables = []
                
                # DevCycle returns variables as a DICT like {"var-key": value}
                # not as a list of {key, value} objects
                if isinstance(variables_data, dict):
                    for var_key, var_value in variables_data.items():
                        extracted_variables.append({
                            'key': var_key,
                            'value': var_value
                        })
                elif isinstance(variables_data, list):
                    # Handle list format (legacy or alternative format)
                    for var in variables_data:
                        if isinstance(var, dict):
                            extracted_variables.append({
                                'key': var.get('key') or var.get('_variable'),
                                'value': var.get('value')
                            })
                        elif isinstance(var, str):
                            extracted_variables.append({
                                'key': var,
                                'value': None
                            })
                
                result.append({
                    'key': v.get('key'),
                    'name': v.get('name'),
                    'variables': extracted_variables
                })
        
        return result
    
    def extract_audiences(self) -> List[Dict[str, Any]]:
        """Extract all audiences (reusable segments)."""
        audiences = self.client.list_audiences(self.project_id)
        
        result = []
        for audience in audiences:
            if isinstance(audience, dict):
                result.append({
                    '_id': audience.get('_id'),
                    'key': audience.get('key'),
                    'name': audience.get('name'),
                    'description': audience.get('description', ''),
                    'filters': self._extract_filters(audience.get('filters', []))
                })
            elif isinstance(audience, str):
                result.append({
                    '_id': None,
                    'key': audience,
                    'name': audience,
                    'description': '',
                    'filters': []
                })
        return result
    
    def extract_variables(self) -> List[Dict[str, Any]]:
        """Extract all variables."""
        variables = self.client.list_variables(self.project_id)
        
        result = []
        for variable in variables:
            if isinstance(variable, dict):
                result.append({
                    '_id': variable.get('_id'),
                    'key': variable.get('key'),
                    'name': variable.get('name'),
                    'type': variable.get('type'),  # 'Boolean', 'String', 'Number', 'JSON'
                    'defaultValue': variable.get('defaultValue')
                })
            elif isinstance(variable, str):
                result.append({
                    '_id': None,
                    'key': variable,
                    'name': variable,
                    'type': None,
                    'defaultValue': None
                })
        return result

