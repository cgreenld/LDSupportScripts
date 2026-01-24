"""
Segment Transformer

Transforms DevCycle audiences to LaunchDarkly segments
"""

import re
from typing import Any, Dict, List, Optional, Tuple


class SegmentTransformer:
    """Transforms DevCycle audiences to LaunchDarkly segments."""
    
    # Operator mapping from DevCycle to LaunchDarkly
    OPERATOR_MAP = {
        '=': 'in',
        '!=': 'in',
        'contain': 'contains',
        'contains': 'contains',
        '!contain': 'contains',
        'startsWith': 'startsWith',
        'endsWith': 'endsWith',
        '>': 'greaterThan',
        '<': 'lessThan',
        '>=': 'greaterThanOrEqual',
        '<=': 'lessThanOrEqual',
        'exist': 'exists',
        '!exist': 'exists'
    }
    
    def transform_audiences(self, audiences: List[Dict]) -> List[Dict]:
        """Transform all DevCycle audiences to LaunchDarkly segments."""
        return [self._transform_audience(audience) for audience in audiences]
    
    def _transform_audience(self, audience: Dict) -> Dict:
        """Transform a single DevCycle audience to LaunchDarkly segment."""
        # Transform filters to segment rules
        rules = self._transform_filters_to_rules(audience.get('filters', []))
        
        return {
            'key': self._sanitize_key(audience.get('key', '')),
            'name': audience.get('name'),
            'description': audience.get('description') or f"Migrated from DevCycle audience: {audience.get('key')}",
            'tags': ['migrated-from-devcycle'],
            
            # Segment targeting rules
            'rules': rules,
            
            # Individual includes/excludes (populated later if needed)
            'included': [],
            'excluded': [],
            
            # Source tracking
            '_source': {
                'platform': 'devcycle',
                'originalId': audience.get('_id'),
                'originalKey': audience.get('key')
            }
        }
    
    def _transform_filters_to_rules(self, filters: List[Dict]) -> List[Dict]:
        """Transform DevCycle filters to LaunchDarkly segment rules."""
        rules = []
        
        # Each filter becomes a clause in the rule
        # DevCycle uses AND logic between filters by default
        clauses = []
        
        for filter_item in filters:
            # Handle nested filter groups
            if filter_item.get('type') == 'group':
                # For OR groups, we need separate rules
                if filter_item.get('operator') == 'or':
                    nested_clauses = self._transform_filters_to_clauses(filter_item.get('filters', []))
                    # Each OR condition becomes a separate rule
                    for clause in nested_clauses:
                        rules.append({'clauses': [clause]})
                else:
                    # AND groups get combined
                    clauses.extend(self._transform_filters_to_clauses(filter_item.get('filters', [])))
                continue
            
            clause = self._transform_filter_to_clause(filter_item)
            if clause:
                clauses.append(clause)
        
        # Add main rule with all AND clauses
        if clauses:
            rules.insert(0, {'clauses': clauses})
        
        return rules
    
    def _transform_filters_to_clauses(self, filters: List[Dict]) -> List[Dict]:
        """Transform filters to clause array."""
        clauses = []
        
        for filter_item in filters:
            if filter_item.get('type') == 'group':
                clauses.extend(self._transform_filters_to_clauses(filter_item.get('filters', [])))
            else:
                clause = self._transform_filter_to_clause(filter_item)
                if clause:
                    clauses.append(clause)
        
        return clauses
    
    def _transform_filter_to_clause(self, filter_item: Dict) -> Optional[Dict]:
        """Transform a single filter to a clause."""
        # Skip "all users" filter
        if filter_item.get('type') == 'all':
            return None
        
        context_kind = self._map_context_kind(filter_item.get('type'))
        attribute = self._map_attribute(filter_item.get('subType'), filter_item.get('dataKey'))
        op, negate = self._map_operator(filter_item.get('comparator'))
        
        values = filter_item.get('values', [])
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
        """Map context type."""
        kind_map = {
            'user': 'user',
            'device': 'device',
            'organization': 'organization'
        }
        return kind_map.get(type_val or 'user', 'user')
    
    def _map_attribute(self, sub_type: Optional[str], data_key: Optional[str]) -> str:
        """Map attribute name."""
        if sub_type == 'customData' and data_key:
            return data_key
        
        attribute_map = {
            'user_id': 'key',
            'email': 'email',
            'name': 'name',
            'country': 'country'
        }
        
        return attribute_map.get(sub_type or '', sub_type or 'key')
    
    def _map_operator(self, comparator: Optional[str]) -> Tuple[str, bool]:
        """Map operator."""
        if not comparator:
            return ('in', False)
        
        is_negated = comparator.startswith('!') or comparator == '!='
        op = self.OPERATOR_MAP.get(comparator, 'in')
        
        return (op, is_negated)
    
    def _sanitize_key(self, key: str) -> str:
        """Sanitize key for LaunchDarkly."""
        # Lowercase
        result = key.lower()
        # Replace invalid characters with hyphens
        result = re.sub(r'[^a-z0-9\-_.]', '-', result)
        # Replace multiple hyphens with single
        result = re.sub(r'--+', '-', result)
        # Remove leading/trailing hyphens
        result = result.strip('-')
        return result

