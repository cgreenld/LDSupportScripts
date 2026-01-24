"""
Rule Transformer

Transforms DevCycle targeting rules to LaunchDarkly rule format
"""

from typing import Any, Dict, List, Optional, Tuple


class RuleTransformer:
    """Transforms DevCycle targeting rules to LaunchDarkly format."""
    
    # Operator mapping from DevCycle to LaunchDarkly
    OPERATOR_MAP = {
        '=': 'in',
        '!=': 'in',  # with negate: True
        'contain': 'contains',
        'contains': 'contains',
        '!contain': 'contains',  # with negate: True
        'startsWith': 'startsWith',
        '!startsWith': 'startsWith',  # with negate: True
        'endsWith': 'endsWith',
        '!endsWith': 'endsWith',  # with negate: True
        '>': 'greaterThan',
        '<': 'lessThan',
        '>=': 'greaterThanOrEqual',
        '<=': 'lessThanOrEqual',
        'exist': 'exists',
        '!exist': 'exists',  # with negate: True
        'regex': 'matches',
        '!regex': 'matches'  # with negate: True
    }
    
    # Attribute mapping from DevCycle to LaunchDarkly
    ATTRIBUTE_MAP = {
        'user_id': 'key',
        'email': 'email',
        'name': 'name',
        'country': 'country',
        'appVersion': 'appVersion',
        'deviceModel': 'deviceModel',
        'platform': 'platform'
    }
    
    def transform_targets(
        self, 
        targets: List[Dict], 
        variation_key_to_index: Dict[str, int], 
        audience_to_segment_map: Dict[str, str]
    ) -> List[Dict]:
        """Transform DevCycle targets array to LaunchDarkly rules."""
        rules = []
        
        for target in targets:
            rule = self._transform_target(target, variation_key_to_index, audience_to_segment_map)
            if rule:
                rules.append(rule)
        
        return rules
    
    def _transform_target(
        self, 
        target: Dict, 
        variation_key_to_index: Dict[str, int], 
        audience_to_segment_map: Dict[str, str]
    ) -> Optional[Dict]:
        """Transform a single DevCycle target to LaunchDarkly rule."""
        # Build clauses from audience filters
        clauses = self._transform_audience(target.get('audience'), audience_to_segment_map)
        
        # Build rollout from distribution
        rollout = self._transform_distribution(target.get('distribution'), variation_key_to_index)
        
        # Skip targets that have no clauses AND only a single variation
        # (these are effectively default/fallthrough rules)
        # But keep targets with rollout weights (percentage rollouts)
        if not clauses and 'variationId' in rollout:
            return None
        
        result = {'clauses': clauses}
        result.update(rollout)
        
        return result
    
    def _transform_audience(
        self, 
        audience: Optional[Dict], 
        audience_to_segment_map: Dict[str, str]
    ) -> List[Dict]:
        """Transform DevCycle audience to LaunchDarkly clauses."""
        if not audience:
            return []
        
        # Reference to saved audience -> use segment targeting
        if audience.get('type') == 'reference' and audience.get('audienceId'):
            segment_key = audience_to_segment_map.get(audience['audienceId'])
            if segment_key:
                return [{
                    'contextKind': 'user',
                    'attribute': 'segmentMatch',
                    'op': 'segmentMatch',
                    'values': [segment_key],
                    'negate': False
                }]
            return []
        
        # Inline filters - handle both dict and list formats
        filters = audience.get('filters')
        if filters:
            # DevCycle can return filters as: {"operator": "and", "filters": [...]}
            if isinstance(filters, dict) and 'filters' in filters:
                return self._transform_filters(filters['filters'])
            # Or as a direct list of filters
            elif isinstance(filters, list):
                return self._transform_filters(filters)
        
        return []
    
    def _transform_filters(self, filters: List[Dict]) -> List[Dict]:
        """Transform DevCycle filters to LaunchDarkly clauses."""
        clauses = []
        
        for filter_item in filters:
            # Handle nested filter groups
            if filter_item.get('type') == 'group':
                # LaunchDarkly rules use implicit AND between clauses
                # For OR logic, we'd need separate rules (more complex)
                nested_clauses = self._transform_filters(filter_item.get('filters', []))
                clauses.extend(nested_clauses)
                continue
            
            # Skip "all users" filter type
            if filter_item.get('type') == 'all':
                continue
            
            clause = self._transform_filter(filter_item)
            if clause:
                clauses.append(clause)
        
        return clauses
    
    def _transform_filter(self, filter_item: Dict) -> Optional[Dict]:
        """Transform a single DevCycle filter to LaunchDarkly clause."""
        # Determine context kind
        context_kind = self._map_context_kind(filter_item.get('type'))
        
        # Determine attribute
        attribute = self._map_attribute(filter_item.get('subType'), filter_item.get('dataKey'))
        
        # Determine operator
        op, negate = self._map_operator(filter_item.get('comparator'))
        
        # Handle values
        values = filter_item.get('values', [])
        
        # Ensure values is a list
        if not isinstance(values, list):
            values = [values]
        
        return {
            'contextKind': context_kind,
            'attribute': attribute,
            'op': op,
            'values': values,
            'negate': negate
        }
    
    def _map_context_kind(self, type_val: Optional[str]) -> str:
        """Map DevCycle context type to LaunchDarkly context kind."""
        kind_map = {
            'user': 'user',
            'device': 'device',
            'organization': 'organization',
            'application': 'application'
        }
        return kind_map.get(type_val or 'user', 'user')
    
    def _map_attribute(self, sub_type: Optional[str], data_key: Optional[str]) -> str:
        """Map DevCycle attribute to LaunchDarkly attribute."""
        # Custom data uses the dataKey
        if sub_type == 'customData' and data_key:
            return data_key
        
        # Map standard attributes
        return self.ATTRIBUTE_MAP.get(sub_type or '', sub_type or 'key')
    
    def _map_operator(self, comparator: Optional[str]) -> Tuple[str, bool]:
        """Map DevCycle comparator to LaunchDarkly operator."""
        if not comparator:
            return ('in', False)
        
        is_negated = comparator.startswith('!') or comparator.startswith('not')
        
        op = self.OPERATOR_MAP.get(comparator, 'in')
        negate = is_negated or comparator == '!='
        
        return (op, negate)
    
    def _transform_distribution(
        self, 
        distribution: Optional[List[Dict]], 
        variation_key_to_index: Dict[str, int]
    ) -> Dict[str, Any]:
        """Transform DevCycle distribution to LaunchDarkly rollout."""
        if not distribution or len(distribution) == 0:
            return {'variationId': 0}
        
        # Get variation key - DevCycle uses either 'variation' or '_variation'
        def get_variation_key(d: Dict) -> str:
            return d.get('_variation') or d.get('variation') or ''
        
        # Normalize percentage to 0-100 scale
        def get_percentage(d: Dict) -> float:
            pct = d.get('percentage', 0)
            if not isinstance(pct, (int, float)):
                return 0
            # DevCycle uses 0-1 scale where 1 = 100%
            # Convert to 0-100 scale
            if 0 < pct <= 1:
                pct = pct * 100
            return pct
        
        # Single variation at 100%
        first_pct = get_percentage(distribution[0])
        if len(distribution) == 1 and first_pct >= 99:  # Allow for rounding
            variation_key = get_variation_key(distribution[0])
            variation_id = variation_key_to_index.get(variation_key, 0)
            return {'variationId': variation_id}
        
        # Percentage rollout - multiple variations
        rollout_weights = {}
        
        for d in distribution:
            variation_key = get_variation_key(d)
            variation_id = variation_key_to_index.get(variation_key, 0)
            pct = get_percentage(d)
            # LaunchDarkly uses weights in thousandths (0-100000)
            # pct is now 0-100, so multiply by 1000 to get 0-100000
            rollout_weights[variation_id] = round(pct * 1000)
        
        return {'rolloutWeights': rollout_weights}

