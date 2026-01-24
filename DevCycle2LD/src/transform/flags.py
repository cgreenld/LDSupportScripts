"""
Flag Transformer

Transforms DevCycle features to LaunchDarkly flag format
"""

import re
from datetime import datetime
from typing import Any, Dict, List

from .rules import RuleTransformer
from .segments import SegmentTransformer


class FlagTransformer:
    """Transforms DevCycle features to LaunchDarkly flags."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize transformer.
        
        Args:
            config: Optional configuration with environmentMap
        """
        config = config or {}
        self.environment_map = config.get('environmentMap', {})
        self.rule_transformer = RuleTransformer()
        self.segment_transformer = SegmentTransformer()
    
    def transform_all(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform all extracted data to LaunchDarkly format.
        
        Args:
            extracted_data: Data extracted from DevCycle
        
        Returns:
            Transformed data ready for LaunchDarkly
        """
        print('Transforming extracted data...')
        
        # Transform audiences to segments first
        audiences = extracted_data.get('audiences', [])
        segments = self.segment_transformer.transform_audiences(audiences)
        print(f"  Transformed {len(segments)} audiences to segments")
        
        # Build audience ID to segment key mapping
        audience_to_segment_map = {}
        for i, audience in enumerate(audiences):
            if i < len(segments):
                audience_to_segment_map[audience.get('_id')] = segments[i].get('key')
        
        # Transform features to flags
        features = extracted_data.get('features', [])
        environments = extracted_data.get('environments', [])
        flags = [
            self._transform_feature(feature, environments, audience_to_segment_map)
            for feature in features
        ]
        print(f"  Transformed {len(flags)} features to flags")
        
        return {
            'transformedAt': datetime.utcnow().isoformat() + 'Z',
            'sourceProjectId': extracted_data.get('projectId'),
            'segments': segments,
            'flags': flags
        }
    
    def _transform_feature(
        self, 
        feature: Dict, 
        environments: List[Dict], 
        audience_to_segment_map: Dict[str, str]
    ) -> Dict[str, Any]:
        """Transform a single DevCycle feature to LaunchDarkly flag."""
        # Transform variations
        variations = self._transform_variations(feature)
        
        # Build variation key to index mapping
        variation_key_to_index = {}
        for i, v in enumerate(feature.get('variations', [])):
            variation_key_to_index[v.get('key')] = i
        
        # Transform environment configs
        environment_configs = {}
        for env in environments:
            dc_env_key = env.get('key')
            ld_env_key = self._map_environment_key(dc_env_key)
            config = feature.get('environments', {}).get(dc_env_key)
            
            if config:
                environment_configs[ld_env_key] = self._transform_environment_config(
                    config,
                    variation_key_to_index,
                    audience_to_segment_map
                )
        
        return {
            # Core identity
            'key': self._sanitize_key(feature.get('key', '')),
            'name': feature.get('name'),
            'description': feature.get('description') or f"Migrated from DevCycle: {feature.get('key')}",
            
            # Tags for tracking
            'tags': ['migrated-from-devcycle'] + (feature.get('tags') or []),
            
            # Variations
            'variations': variations,
            
            # Defaults (used when creating flag)
            'defaults': {
                'onVariation': 0,
                'offVariation': len(variations) - 1 if variations else 0
            },
            
            # Temporary flag indicator
            'temporary': False,
            
            # Environment-specific configurations
            'environmentConfigs': environment_configs,
            
            # Source tracking
            '_source': {
                'platform': 'devcycle',
                'originalKey': feature.get('key'),
                'originalType': feature.get('type'),
                'transformedAt': datetime.utcnow().isoformat() + 'Z'
            }
        }
    
    def _transform_variations(self, feature: Dict) -> List[Dict]:
        """Transform variations from DevCycle to LaunchDarkly format."""
        variations = feature.get('variations', [])
        
        result = []
        for v in variations:
            # Determine the value - DevCycle has variables per variation
            variables = v.get('variables', [])
            
            if variables:
                # If single variable, use its value directly
                if len(variables) == 1:
                    value = variables[0].get('value')
                else:
                    # Multiple variables - create JSON object
                    value = {}
                    for variable in variables:
                        value[variable.get('key', '')] = variable.get('value')
            else:
                # Fallback to variation key as value
                value = v.get('key')
            
            result.append({
                'value': value,
                'name': v.get('name') or v.get('key'),
                'description': f"Migrated from DevCycle variation: {v.get('key')}"
            })
        
        return result
    
    def _transform_environment_config(
        self, 
        config: Dict, 
        variation_key_to_index: Dict[str, int], 
        audience_to_segment_map: Dict[str, str]
    ) -> Dict[str, Any]:
        """Transform environment-specific configuration."""
        # Transform targeting rules
        rules = self.rule_transformer.transform_targets(
            config.get('targets', []),
            variation_key_to_index,
            audience_to_segment_map
        )
        
        # Determine fallthrough variation
        fallthrough_variation = 0
        default_serve = config.get('defaultServe', {})
        if default_serve and default_serve.get('variation'):
            fallthrough_variation = variation_key_to_index.get(default_serve['variation'], 0)
        
        # Transform individual targets (forced users)
        targets = self._transform_forced_users(config.get('forcedUsers', []), variation_key_to_index)
        
        return {
            'on': config.get('on', False),
            'fallthrough': {
                'variation': fallthrough_variation
            },
            'rules': rules,
            'targets': targets
        }
    
    def _transform_forced_users(
        self, 
        forced_users: List[Dict], 
        variation_key_to_index: Dict[str, int]
    ) -> List[Dict]:
        """Transform forced users to LaunchDarkly individual targets."""
        targets_by_variation: Dict[int, List[str]] = {}
        
        for forced in forced_users:
            variation_index = variation_key_to_index.get(forced.get('variation'), 0)
            
            if variation_index not in targets_by_variation:
                targets_by_variation[variation_index] = []
            
            targets_by_variation[variation_index].append(forced.get('userId'))
        
        return [
            {
                'contextKind': 'user',
                'variationId': int(variation_id),
                'values': values
            }
            for variation_id, values in targets_by_variation.items()
        ]
    
    def _map_environment_key(self, dc_env_key: str) -> str:
        """Map DevCycle environment key to LaunchDarkly environment key."""
        return self.environment_map.get(dc_env_key, dc_env_key)
    
    def _sanitize_key(self, key: str) -> str:
        """
        Sanitize a key for LaunchDarkly.
        LD keys: lowercase, alphanumeric, hyphens, underscores, periods
        """
        # Lowercase
        result = key.lower()
        # Replace invalid characters with hyphens
        result = re.sub(r'[^a-z0-9\-_.]', '-', result)
        # Replace multiple hyphens with single
        result = re.sub(r'--+', '-', result)
        # Remove leading/trailing hyphens
        result = result.strip('-')
        return result

