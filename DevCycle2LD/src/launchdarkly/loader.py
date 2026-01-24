"""
LaunchDarkly Loader

Loads transformed feature flags and segments into LaunchDarkly
"""

from typing import Any, Dict, List

from .client import LaunchDarklyClient


class LaunchDarklyLoader:
    """Loads transformed data into LaunchDarkly."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize loader.
        
        Args:
            config: Dictionary with apiToken, projectKey, and dryRun flag
        """
        self.client = LaunchDarklyClient({
            'apiToken': config.get('apiToken'),
            'dryRun': config.get('dryRun', True)
        })
        self.project_key = config.get('projectKey')
        self.dry_run = config.get('dryRun', True)
        
        self.results = {
            'environments': {'created': [], 'skipped': [], 'failed': []},
            'segments': {'created': [], 'skipped': [], 'failed': []},
            'flags': {'created': [], 'skipped': [], 'failed': []},
            'targeting': {'applied': [], 'failed': []}
        }
    
    def load_all(self, transformed_data: Dict[str, Any], source_environments: List[Dict] = None) -> Dict[str, Any]:
        """
        Load all transformed data into LaunchDarkly.
        
        Args:
            transformed_data: Dictionary with flags and segments to load
            source_environments: Optional list of source environments to create in LD
        
        Returns:
            Results dictionary with created/skipped/failed items
        """
        print(f"Loading into LaunchDarkly project: {self.project_key}")
        print(f"Dry run: {self.dry_run}")
        
        # Get existing environments from LaunchDarkly
        print("\n--- LaunchDarkly Environments (Before) ---")
        existing_environments = self.client.list_environments(self.project_key)
        existing_env_keys = set()
        
        if existing_environments:
            for env in existing_environments:
                if isinstance(env, dict):
                    env_key = env.get('key', 'unknown')
                    env_name = env.get('name', env_key)
                    env_color = env.get('color', '')
                    existing_env_keys.add(env_key)
                    print(f"  • {env_key:<20} ({env_name}){f' [{env_color}]' if env_color else ''}")
                else:
                    existing_env_keys.add(str(env))
                    print(f"  • {env}")
        else:
            print("  No environments found!")
        
        print(f"\n  Total: {len(existing_env_keys)} environment(s)")
        
        # Step 0: Create environments from source if provided
        if source_environments:
            print('\n--- Creating Environments ---')
            self.load_environments(source_environments, existing_env_keys)
            # Refresh environment list after creating
            existing_environments = self.client.list_environments(self.project_key)
            existing_env_keys = set()
            for env in existing_environments:
                if isinstance(env, dict):
                    existing_env_keys.add(env.get('key', 'unknown'))
        
        env_keys = list(existing_env_keys)
        
        # Step 1: Create segments first (they may be referenced by flags)
        print('\n--- Creating Segments ---')
        self.load_segments(transformed_data.get('segments', []), env_keys[0] if env_keys else 'production')
        
        # Step 2: Create flags
        print('\n--- Creating Flags ---')
        self.load_flags(transformed_data.get('flags', []))
        
        # Step 3: Apply targeting rules per environment
        print('\n--- Applying Targeting Rules ---')
        self.apply_targeting(transformed_data.get('flags', []), env_keys)
        
        return self.results
    
    def load_environments(self, source_environments: List[Dict], existing_env_keys: set):
        """Create environments in LaunchDarkly from source environments."""
        # Color palette for environments (LaunchDarkly requires hex colors)
        env_colors = {
            'development': 'A34FDE',  # Purple
            'dev': 'A34FDE',
            'staging': 'FF9E0F',       # Orange
            'stage': 'FF9E0F',
            'test': '3DD6F5',          # Cyan
            'qa': '3DD6F5',
            'production': '417505',    # Green
            'prod': '417505',
        }
        default_color = '939393'  # Gray
        
        for env in source_environments:
            if isinstance(env, dict):
                env_key = env.get('key')
                env_name = env.get('name', env_key)
            else:
                env_key = str(env)
                env_name = env_key
            
            if not env_key:
                continue
            
            # Skip if already exists
            if env_key in existing_env_keys:
                print(f"  ⏭️  Environment exists, skipping: {env_key}")
                self.results['environments']['skipped'].append(env_key)
                continue
            
            try:
                # Determine color based on environment type/key
                color = env_colors.get(env_key.lower(), 
                        env_colors.get(env.get('type', '').lower() if isinstance(env, dict) else '', 
                        default_color))
                
                self.client.create_environment(self.project_key, {
                    'key': env_key,
                    'name': env_name,
                    'color': color,
                    'tags': ['migrated-from-devcycle']
                })
                
                print(f"  ✅ Created environment: {env_key} ({env_name})")
                self.results['environments']['created'].append(env_key)
                
            except Exception as e:
                print(f"  ❌ Failed to create environment {env_key}: {str(e)}")
                self.results['environments']['failed'].append({
                    'key': env_key,
                    'error': str(e)
                })
    
    def load_segments(self, segments: List[Dict], environment_key: str):
        """Load segments into LaunchDarkly."""
        for segment in segments:
            try:
                # Check if segment already exists
                exists = self.client.segment_exists(
                    self.project_key,
                    environment_key,
                    segment['key']
                )
                
                if exists:
                    print(f"  ⏭️  Segment exists, skipping: {segment['key']}")
                    self.results['segments']['skipped'].append(segment['key'])
                    continue
                
                # Create the segment
                self.client.create_segment(self.project_key, environment_key, {
                    'key': segment['key'],
                    'name': segment.get('name'),
                    'description': segment.get('description'),
                    'tags': segment.get('tags', ['migrated-from-devcycle']),
                    'unbounded': False,
                    'rules': segment.get('rules', []),
                    'included': segment.get('included', []),
                    'excluded': segment.get('excluded', [])
                })
                
                print(f"  ✅ Created segment: {segment['key']}")
                self.results['segments']['created'].append(segment['key'])
            
            except Exception as e:
                print(f"  ❌ Failed to create segment {segment['key']}: {str(e)}")
                self.results['segments']['failed'].append({
                    'key': segment['key'],
                    'error': str(e)
                })
    
    def load_flags(self, flags: List[Dict]):
        """Load feature flags into LaunchDarkly."""
        for flag in flags:
            try:
                # Check if flag already exists
                exists = self.client.flag_exists(self.project_key, flag['key'])
                
                if exists:
                    print(f"  ⏭️  Flag exists, skipping: {flag['key']}")
                    self.results['flags']['skipped'].append(flag['key'])
                    continue
                
                # Create the flag
                flag_data = {
                    'key': flag['key'],
                    'name': flag.get('name'),
                    'description': flag.get('description'),
                    'tags': flag.get('tags', ['migrated-from-devcycle']),
                    'variations': flag.get('variations', []),
                    'temporary': flag.get('temporary', False),
                    'defaults': flag.get('defaults')
                }
                
                self.client.create_flag(self.project_key, flag_data)
                
                print(f"  ✅ Created flag: {flag['key']}")
                self.results['flags']['created'].append(flag['key'])
            
            except Exception as e:
                print(f"  ❌ Failed to create flag {flag['key']}: {str(e)}")
                self.results['flags']['failed'].append({
                    'key': flag['key'],
                    'error': str(e)
                })
    
    def apply_targeting(self, flags: List[Dict], environment_keys: List[str]):
        """Apply targeting rules for each flag in each environment."""
        for flag in flags:
            for env_key in environment_keys:
                env_config = flag.get('environmentConfigs', {}).get(env_key)
                
                if not env_config:
                    continue
                
                try:
                    print(f"  Applying targeting for {flag['key']} in {env_key}...")
                    
                    self.client.update_flag_targeting(
                        self.project_key,
                        flag['key'],
                        env_key,
                        {
                            'on': env_config.get('on'),
                            'fallthrough': env_config.get('fallthrough'),
                            'rules': env_config.get('rules'),
                            'targets': env_config.get('targets')
                        }
                    )
                    
                    print(f"    ✅ Applied targeting: {flag['key']} ({env_key})")
                    self.results['targeting']['applied'].append({
                        'flag': flag['key'],
                        'environment': env_key
                    })
                
                except Exception as e:
                    print(f"    ❌ Failed targeting {flag['key']} ({env_key}): {str(e)}")
                    self.results['targeting']['failed'].append({
                        'flag': flag['key'],
                        'environment': env_key,
                        'error': str(e)
                    })

