#!/usr/bin/env python3
"""
Seed Test Flags for DevCycle

Creates sample flags with various targeting rules to test the migration tool.
Run from the project root: python scripts/seed_test_flags.py
"""

import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from dotenv import load_dotenv
import requests

load_dotenv()

# DevCycle Management API
class DevCycleSeeder:
    def __init__(self):
        self.client_id = os.getenv('DEVCYCLE_CLIENT_ID')
        self.client_secret = os.getenv('DEVCYCLE_CLIENT_SECRET')
        self.project_id = os.getenv('DEVCYCLE_PROJECT_ID')
        self.base_url = 'https://api.devcycle.com'
        self.access_token = None
        
    def authenticate(self):
        """Get access token."""
        print("Authenticating with DevCycle...")
        response = requests.post(
            'https://auth.devcycle.com/oauth/token',
            json={
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'audience': 'https://api.devcycle.com/'
            }
        )
        response.raise_for_status()
        self.access_token = response.json()['access_token']
        print("✅ Authenticated successfully")
        
    def request(self, method, path, data=None):
        """Make API request."""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        url = f"{self.base_url}{path}"
        response = requests.request(method, url, headers=headers, json=data)
        
        if response.status_code >= 400:
            print(f"  Error: {response.status_code} - {response.text}")
        response.raise_for_status()
        return response.json() if response.content else None
    
    def get_environments(self):
        """Get all environments."""
        return self.request('GET', f'/v1/projects/{self.project_id}/environments')
    
    def create_feature(self, feature_data):
        """Create a feature."""
        return self.request('POST', f'/v1/projects/{self.project_id}/features', feature_data)
    
    def update_feature_config(self, feature_key, env_key, config_data):
        """Update feature configuration for an environment."""
        # Try the environment-specific endpoint
        return self.request(
            'PATCH', 
            f'/v1/projects/{self.project_id}/features/{feature_key}/configurations?environment={env_key}',
            config_data
        )
    
    def create_audience(self, audience_data):
        """Create an audience."""
        return self.request('POST', f'/v1/projects/{self.project_id}/audiences', audience_data)
    
    def feature_exists(self, feature_key):
        """Check if feature exists."""
        try:
            self.request('GET', f'/v1/projects/{self.project_id}/features/{feature_key}')
            return True
        except:
            return False
    
    def delete_feature(self, feature_key):
        """Delete a feature."""
        try:
            self.request('DELETE', f'/v1/projects/{self.project_id}/features/{feature_key}')
            return True
        except:
            return False


def main():
    seeder = DevCycleSeeder()
    seeder.authenticate()
    
    # Get environments
    print("\n📋 Getting environments...")
    environments = seeder.get_environments()
    env_keys = [e['key'] for e in environments]
    print(f"  Found: {', '.join(env_keys)}")
    
    # Generate unique suffix to avoid variable conflicts
    import random
    import string
    suffix = ''.join(random.choices(string.ascii_lowercase, k=4))
    print(f"  Using suffix: {suffix}")
    
    # Define test features
    test_features = [
        # 1. Simple boolean flag
        {
            'key': f'test-boolean-{suffix}',
            'name': 'Test Simple Boolean',
            'description': 'A simple on/off boolean flag',
            'type': 'release',
            'variables': [
                {'key': f'enabled-{suffix}', 'type': 'Boolean'}
            ],
            'variations': [
                {'key': 'on', 'name': 'On', 'variables': {f'enabled-{suffix}': True}},
                {'key': 'off', 'name': 'Off', 'variables': {f'enabled-{suffix}': False}}
            ]
        },
        
        # 2. String flag with multiple variations
        {
            'key': f'test-string-{suffix}',
            'name': 'Test String Variations',
            'description': 'String flag with multiple variations for testing',
            'type': 'release',
            'variables': [
                {'key': f'theme-{suffix}', 'type': 'String'}
            ],
            'variations': [
                {'key': 'light', 'name': 'Light Theme', 'variables': {f'theme-{suffix}': 'light'}},
                {'key': 'dark', 'name': 'Dark Theme', 'variables': {f'theme-{suffix}': 'dark'}},
                {'key': 'system', 'name': 'System Default', 'variables': {f'theme-{suffix}': 'system'}}
            ]
        },
        
        # 3. Number flag for percentage rollout testing
        {
            'key': f'test-rollout-{suffix}',
            'name': 'Test Percentage Rollout',
            'description': 'Flag to test percentage-based rollouts',
            'type': 'release',
            'variables': [
                {'key': f'version-{suffix}', 'type': 'Number'}
            ],
            'variations': [
                {'key': 'v1', 'name': 'Version 1', 'variables': {f'version-{suffix}': 1}},
                {'key': 'v2', 'name': 'Version 2', 'variables': {f'version-{suffix}': 2}}
            ]
        },
        
        # 4. JSON flag for complex config
        {
            'key': f'test-json-{suffix}',
            'name': 'Test JSON Config',
            'description': 'JSON flag with complex configuration',
            'type': 'release',
            'variables': [
                {'key': f'config-{suffix}', 'type': 'JSON'}
            ],
            'variations': [
                {
                    'key': 'default', 
                    'name': 'Default Config', 
                    'variables': {f'config-{suffix}': {'maxItems': 10, 'showBanner': False}}
                },
                {
                    'key': 'premium', 
                    'name': 'Premium Config', 
                    'variables': {f'config-{suffix}': {'maxItems': 100, 'showBanner': True, 'features': ['export', 'import']}}
                }
            ]
        },
        
        # 5. Flag for user targeting
        {
            'key': f'test-users-{suffix}',
            'name': 'Test User Targeting',
            'description': 'Flag with specific user targeting rules',
            'type': 'release',
            'variables': [
                {'key': f'access-{suffix}', 'type': 'Boolean'}
            ],
            'variations': [
                {'key': 'granted', 'name': 'Access Granted', 'variables': {f'access-{suffix}': True}},
                {'key': 'denied', 'name': 'Access Denied', 'variables': {f'access-{suffix}': False}}
            ]
        },
        
        # 6. Flag for email targeting
        {
            'key': f'test-email-{suffix}',
            'name': 'Test Email Targeting',
            'description': 'Flag with email-based targeting',
            'type': 'release',
            'variables': [
                {'key': f'beta-{suffix}', 'type': 'Boolean'}
            ],
            'variations': [
                {'key': 'enabled', 'name': 'Beta Enabled', 'variables': {f'beta-{suffix}': True}},
                {'key': 'disabled', 'name': 'Beta Disabled', 'variables': {f'beta-{suffix}': False}}
            ]
        },
        
        # 7. Flag for custom data targeting
        {
            'key': f'test-customdata-{suffix}',
            'name': 'Test Custom Data Targeting',
            'description': 'Flag targeting based on custom user data',
            'type': 'release',
            'variables': [
                {'key': f'tier-{suffix}', 'type': 'String'}
            ],
            'variations': [
                {'key': 'free', 'name': 'Free Tier', 'variables': {f'tier-{suffix}': 'free'}},
                {'key': 'pro', 'name': 'Pro Tier', 'variables': {f'tier-{suffix}': 'pro'}},
                {'key': 'enterprise', 'name': 'Enterprise Tier', 'variables': {f'tier-{suffix}': 'enterprise'}}
            ]
        }
    ]
    
    # Create features
    print("\n🚀 Creating test features...")
    created_features = []
    
    for feature in test_features:
        feature_key = feature['key']
        
        # Check if exists and delete
        if seeder.feature_exists(feature_key):
            print(f"  🗑️  Deleting existing feature: {feature_key}")
            seeder.delete_feature(feature_key)
            time.sleep(0.5)  # Rate limiting
        
        print(f"  Creating: {feature_key}")
        try:
            result = seeder.create_feature(feature)
            created_features.append(feature_key)
            print(f"    ✅ Created: {feature['name']}")
        except Exception as e:
            print(f"    ❌ Failed: {str(e)}")
        
        time.sleep(0.5)  # Rate limiting
    
    # Apply targeting rules to features
    print("\n🎯 Configuring targeting rules...")
    
    dev_env = 'development' if 'development' in env_keys else env_keys[0]
    prod_env = 'production' if 'production' in env_keys else env_keys[-1]
    
    targeting_configs = [
        # 1. Simple boolean - different states per environment
        {
            'feature': f'test-boolean-{suffix}',
            'env': dev_env,
            'config': {
                'status': 'active',
                'targets': [
                    {
                        'name': 'All Users',
                        'audience': {'filters': {'operator': 'and', 'filters': [{'type': 'all'}]}},
                        'distribution': [{'_variation': 'on', 'percentage': 1}]
                    }
                ]
            }
        },
        {
            'feature': f'test-boolean-{suffix}',
            'env': prod_env,
            'config': {
                'status': 'active',
                'targets': [
                    {
                        'name': 'All Users',
                        'audience': {'filters': {'operator': 'and', 'filters': [{'type': 'all'}]}},
                        'distribution': [{'_variation': 'off', 'percentage': 1}]
                    }
                ]
            }
        },
        
        # 2. Percentage rollout - 70/30 split
        {
            'feature': f'test-rollout-{suffix}',
            'env': dev_env,
            'config': {
                'status': 'active',
                'targets': [
                    {
                        'name': '70/30 Rollout',
                        'audience': {'filters': {'operator': 'and', 'filters': [{'type': 'all'}]}},
                        'distribution': [
                            {'_variation': 'v1', 'percentage': 0.7},
                            {'_variation': 'v2', 'percentage': 0.3}
                        ]
                    }
                ]
            }
        },
        
        # 3. User ID targeting
        {
            'feature': f'test-users-{suffix}',
            'env': dev_env,
            'config': {
                'status': 'active',
                'targets': [
                    {
                        'name': 'Specific Users',
                        'audience': {
                            'filters': {
                                'operator': 'and',
                                'filters': [
                                    {
                                        'type': 'user',
                                        'subType': 'user_id',
                                        'comparator': '=',
                                        'values': ['user-123', 'user-456', 'admin-user']
                                    }
                                ]
                            }
                        },
                        'distribution': [{'_variation': 'granted', 'percentage': 1}]
                    },
                    {
                        'name': 'Default',
                        'audience': {'filters': {'operator': 'and', 'filters': [{'type': 'all'}]}},
                        'distribution': [{'_variation': 'denied', 'percentage': 1}]
                    }
                ]
            }
        },
        
        # 4. Email targeting with contains
        {
            'feature': f'test-email-{suffix}',
            'env': dev_env,
            'config': {
                'status': 'active',
                'targets': [
                    {
                        'name': 'Internal Users',
                        'audience': {
                            'filters': {
                                'operator': 'and',
                                'filters': [
                                    {
                                        'type': 'user',
                                        'subType': 'email',
                                        'comparator': 'contain',
                                        'values': ['@acme.com', '@internal.test']
                                    }
                                ]
                            }
                        },
                        'distribution': [{'_variation': 'enabled', 'percentage': 1}]
                    },
                    {
                        'name': 'Default',
                        'audience': {'filters': {'operator': 'and', 'filters': [{'type': 'all'}]}},
                        'distribution': [{'_variation': 'disabled', 'percentage': 1}]
                    }
                ]
            }
        },
        
        # 5. Custom data targeting
        {
            'feature': f'test-customdata-{suffix}',
            'env': dev_env,
            'config': {
                'status': 'active',
                'targets': [
                    {
                        'name': 'Enterprise Users',
                        'audience': {
                            'filters': {
                                'operator': 'and',
                                'filters': [
                                    {
                                        'type': 'user',
                                        'subType': 'customData',
                                        'dataKey': 'plan',
                                        'dataKeyType': 'String',
                                        'comparator': '=',
                                        'values': ['enterprise']
                                    }
                                ]
                            }
                        },
                        'distribution': [{'_variation': 'enterprise', 'percentage': 1}]
                    },
                    {
                        'name': 'Pro Users',
                        'audience': {
                            'filters': {
                                'operator': 'and',
                                'filters': [
                                    {
                                        'type': 'user',
                                        'subType': 'customData',
                                        'dataKey': 'plan',
                                        'dataKeyType': 'String',
                                        'comparator': '=',
                                        'values': ['pro']
                                    }
                                ]
                            }
                        },
                        'distribution': [{'_variation': 'pro', 'percentage': 1}]
                    },
                    {
                        'name': 'Default',
                        'audience': {'filters': {'operator': 'and', 'filters': [{'type': 'all'}]}},
                        'distribution': [{'_variation': 'free', 'percentage': 1}]
                    }
                ]
            }
        },
        
        # 6. String variations with 50/50 split
        {
            'feature': f'test-string-{suffix}',
            'env': dev_env,
            'config': {
                'status': 'active',
                'targets': [
                    {
                        'name': 'Theme Test',
                        'audience': {'filters': {'operator': 'and', 'filters': [{'type': 'all'}]}},
                        'distribution': [
                            {'_variation': 'light', 'percentage': 0.5},
                            {'_variation': 'dark', 'percentage': 0.5}
                        ]
                    }
                ]
            }
        },
        
        # 7. JSON config - different configs per environment
        {
            'feature': f'test-json-{suffix}',
            'env': dev_env,
            'config': {
                'status': 'active',
                'targets': [
                    {
                        'name': 'All Users',
                        'audience': {'filters': {'operator': 'and', 'filters': [{'type': 'all'}]}},
                        'distribution': [{'_variation': 'premium', 'percentage': 1}]
                    }
                ]
            }
        },
        {
            'feature': f'test-json-{suffix}',
            'env': prod_env,
            'config': {
                'status': 'active',
                'targets': [
                    {
                        'name': 'All Users',
                        'audience': {'filters': {'operator': 'and', 'filters': [{'type': 'all'}]}},
                        'distribution': [{'_variation': 'default', 'percentage': 1}]
                    }
                ]
            }
        }
    ]
    
    for tc in targeting_configs:
        if tc['feature'] not in created_features:
            continue
            
        print(f"  Configuring {tc['feature']} in {tc['env']}...")
        try:
            seeder.update_feature_config(tc['feature'], tc['env'], tc['config'])
            print(f"    ✅ Configured targeting rules")
        except Exception as e:
            print(f"    ❌ Failed: {str(e)}")
        
        time.sleep(0.3)
    
    # Create a test audience
    print("\n👥 Creating test audience...")
    try:
        # DevCycle audience filters use nested structure with operator
        audience = seeder.create_audience({
            'key': 'beta-testers',
            'name': 'Beta Testers',
            'description': 'Users who have opted into beta testing',
            'filters': {
                'operator': 'and',
                'filters': [
                    {
                        'type': 'user',
                        'subType': 'customData',
                        'dataKey': 'beta_tester',
                        'dataKeyType': 'Boolean',
                        'comparator': '=',
                        'values': [True]
                    }
                ]
            }
        })
        print("  ✅ Created audience: beta-testers")
    except Exception as e:
        if '409' in str(e) or 'already exists' in str(e).lower():
            print("  ⏭️  Audience already exists: beta-testers")
        else:
            print(f"  ❌ Failed: {str(e)}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SEED COMPLETE")
    print("=" * 50)
    print(f"Created {len(created_features)} features:")
    for f in created_features:
        print(f"  • {f}")
    print("\nTargeting rules configured for:")
    print(f"  • User ID matching")
    print(f"  • Email contains")
    print(f"  • Custom data (plan attribute)")
    print(f"  • Percentage rollouts (70/30, 50/50)")
    print(f"  • Different variations per environment")
    print("\nAudience created:")
    print(f"  • beta-testers")
    print("\n✨ Ready to test migration!")
    print("Run: python src/main.py migrate")


if __name__ == '__main__':
    main()

