# DevCycle to LaunchDarkly Feature Flag Migration

A Python migration utility for transferring feature flags, targeting rules, and audiences from DevCycle to LaunchDarkly.

## Quick Start

### Prerequisites
- Python 3.10+
- DevCycle Management API credentials (Client ID & Secret)
- LaunchDarkly API token with write access

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd DevCycle2LD

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with your API credentials
```

### Run Migration

```bash
# Preview migration (dry-run mode - default)
python src/main.py migrate

# Execute actual migration
python src/main.py migrate --execute
```

---

## Overview

This tool performs an ETL (Extract-Transform-Load) migration of feature flags between platforms while preserving:
- On/Off state per environment
- Targeting rules and conditions
- Variation definitions
- Audience/Segment configurations

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   EXTRACT       │     │   TRANSFORM     │     │   LOAD          │
│   (DevCycle)    │ ──▶ │   (Mapping)     │ ──▶ │   (LaunchDarkly)│
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
  GET /v2/features        Normalize rules         POST /api/v2/flags
  GET /v2/audiences       Map variations          POST /api/v2/segments
  GET /v2/variables       Handle edge cases       PATCH targeting
```

## Conceptual Mapping

| DevCycle Concept | LaunchDarkly Equivalent | Notes |
|------------------|-------------------------|-------|
| Feature | Feature Flag | Core entity |
| Variation | Variation | Both support multivariate |
| Environment | Environment | Direct mapping |
| Targeting Rules | Targeting Rules | Structure differs significantly |
| User Targeting | Individual Targets | Per-context targeting |
| Audiences | Segments | Reusable targeting groups |
| Variables | Flag Variations + Contexts | LD uses typed variations |

## API References

### DevCycle Management API
- **Documentation**: https://docs.devcycle.com/management-api/#tag/Features-v2
- **Base URL**: `https://api.devcycle.com/v2`
- **Authentication**: Bearer token (client credentials)

#### Key Endpoints
```
GET /v2/projects/{project_id}/features           # List all features
GET /v2/projects/{project_id}/features/{key}     # Get specific feature with rules
GET /v2/projects/{project_id}/audiences          # Get audiences
GET /v2/projects/{project_id}/variables          # Get variable definitions
GET /v2/projects/{project_id}/environments       # Get environments
```

### LaunchDarkly API
- **Documentation**: https://launchdarkly.com/docs/api/feature-flags
- **Base URL**: `https://app.launchdarkly.com/api/v2`
- **Authentication**: API access token (Authorization header)

#### Key Endpoints
```
POST   /api/v2/flags/{projectKey}                      # Create feature flag
PATCH  /api/v2/flags/{projectKey}/{flagKey}            # Update flag/targeting
GET    /api/v2/flags/{projectKey}                      # List flags
POST   /api/v2/segments/{projectKey}/{envKey}          # Create segment
PATCH  /api/v2/segments/{projectKey}/{envKey}/{segKey} # Update segment
```

## Data Structures

### Intermediate Migration Schema

```python
migration_flag_schema = {
    # Core identity
    "key": str,                    # Flag key (must be valid in both systems)
    "name": str,                   # Display name
    "description": str,
    
    # State tracking per environment
    "environments": {
        "<envKey>": {
            "on": bool,            # Is flag serving variations or off?
            "offVariation": int,   # Index of variation when off
            "fallthrough": {       # Default rule when no targeting matches
                "variation": int
            },
            "targets": [],         # Individual user/context targeting
            "rules": []            # Targeting rules (complex logic)
        }
    },
    
    # Variations (the values the flag can return)
    "variations": [
        {"value": any, "name": str, "description": str}
    ],
    
    # Metadata
    "tags": [],
    "temporary": bool,
    
    # Migration tracking
    "_source": {
        "platform": "devcycle",
        "originalId": str,
        "extractedAt": "timestamp",
        "rulesHash": str           # For change detection
    }
}
```

### DevCycle Rule Structure

```json
{
  "targets": [
    {
      "audience": {
        "filters": [
          {
            "type": "user",
            "subType": "user_id",
            "comparator": "=",
            "values": ["user-123"]
          }
        ]
      },
      "distribution": [
        { "variation": "variation-a", "percentage": 100 }
      ]
    }
  ]
}
```

### LaunchDarkly Equivalent Rule Structure

```json
{
  "rules": [
    {
      "clauses": [
        {
          "contextKind": "user",
          "attribute": "key",
          "op": "in",
          "values": ["user-123"]
        }
      ],
      "rollout": {
        "variations": [
          { "variation": 0, "weight": 100000 }
        ]
      }
    }
  ]
}
```

## Operator Mapping

| DevCycle Operator | LaunchDarkly Operator | Notes |
|-------------------|----------------------|-------|
| `=` | `in` | Equality check |
| `!=` | `in` + negate | Use negate flag |
| `contains` | `contains` | Substring match |
| `startsWith` | `startsWith` | Prefix match |
| `endsWith` | `endsWith` | Suffix match |
| `>` | `greaterThan` | Numeric comparison |
| `<` | `lessThan` | Numeric comparison |
| `>=` | `greaterThanOrEqual` | Numeric comparison |
| `<=` | `lessThanOrEqual` | Numeric comparison |
| `exist` | `exists` | Attribute exists |
| `!exist` | `exists` + negate | Attribute missing |

## Environment Variables

```bash
# DevCycle credentials
DEVCYCLE_CLIENT_ID=your_client_id
DEVCYCLE_CLIENT_SECRET=your_client_secret
DEVCYCLE_PROJECT_ID=your_project_id

# LaunchDarkly credentials
LD_API_TOKEN=your_api_token
LD_PROJECT_KEY=your_project_key

# Migration settings
DRY_RUN=true                    # Set to false to execute writes
LOG_LEVEL=info                  # debug, info, warn, error
ENVIRONMENT_MAP=dev:test,prod:production  # Optional env name mapping
```

## Migration Phases

### Phase 1: Pre-Migration Preparation
- [ ] Inventory all DevCycle features
- [ ] Identify features with complex rules
- [ ] Map environments between platforms
- [ ] Create LaunchDarkly project structure
- [ ] Set up API credentials

### Phase 2: Extraction (DevCycle)
- [ ] Authenticate with DevCycle API
- [ ] Export all features with current state
- [ ] Export all audiences
- [ ] Export environment-specific targeting
- [ ] Capture on/off state per environment
- [ ] Save extraction snapshot to JSON

### Phase 3: Transformation
- [ ] Validate variation type compatibility
- [ ] Sanitize flag keys for LD compatibility
- [ ] Map targeting rule operators
- [ ] Convert audiences to segment format
- [ ] Handle percentage rollouts
- [ ] Generate transformation report

### Phase 4: Loading (LaunchDarkly)
- [ ] Create segments first (audiences → segments)
- [ ] Create flags with default variations
- [ ] Apply targeting rules per environment
- [ ] Set on/off state per environment
- [ ] Apply individual user targets

### Phase 5: Verification
- [ ] Compare flag evaluations in both systems
- [ ] Verify targeting rule behavior
- [ ] Check segment membership
- [ ] Validate percentage rollout distributions
- [ ] Generate verification report

## Usage

```bash
# Run full migration (dry-run mode - preview only)
python src/main.py migrate

# Run full migration (execute writes to LaunchDarkly)
python src/main.py migrate --execute

# Run extraction only (read-only, saves to snapshots/)
python src/main.py extract

# Run extraction with custom output path
python src/main.py extract --output ./my-extraction.json
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `extract` | Extract features, audiences, and environments from DevCycle |
| `migrate` | Run full ETL migration from DevCycle to LaunchDarkly |

### Command Options

**extract**
- `-o, --output` - Output file path (default: `./snapshots/extracted.json`)

**migrate**
- `--execute` - Execute actual writes (default is dry-run/preview mode)

### Testing with Sample Flags

A seed script is included to create test flags in DevCycle with various targeting rules:

```bash
python scripts/seed_test_flags.py
```

This creates flags with:
- Simple boolean toggles
- Email-based targeting
- User ID targeting
- Custom attribute targeting
- Percentage rollouts (70/30, 50/50)

## Project Structure

```
DevCycle2LD/
├── readme.md              # This file
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
├── .gitignore             # Git ignore rules
├── src/
│   ├── __init__.py
│   ├── __main__.py        # Package entry point
│   ├── main.py            # CLI entry point
│   ├── devcycle/
│   │   ├── __init__.py
│   │   ├── client.py      # DevCycle API client
│   │   └── extractor.py   # Feature extraction logic
│   ├── launchdarkly/
│   │   ├── __init__.py
│   │   ├── client.py      # LaunchDarkly API client
│   │   └── loader.py      # Flag creation logic
│   ├── transform/
│   │   ├── __init__.py
│   │   ├── flags.py       # Flag transformation
│   │   ├── rules.py       # Rule/targeting transformation
│   │   └── segments.py    # Audience→Segment transformation
│   └── utils/
│       ├── __init__.py
│       ├── logger.py      # Logging utility
│       └── report.py      # Migration reporting
├── scripts/
│   └── seed_test_flags.py # Create test flags in DevCycle
├── snapshots/             # Extraction snapshots (gitignored)
└── reports/               # Migration reports (gitignored)
```

## Known Limitations

1. **Percentage Rollouts**: Automatically converted (DevCycle 0-1 → LaunchDarkly 0-100000)
2. **Context Types**: DevCycle "user" maps to LaunchDarkly "user" context kind
3. **Complex Audiences**: Nested AND/OR logic uses AND at the rule level (OR requires separate rules)
4. **Scheduling**: Scheduled flag changes are not migrated automatically
5. **Webhooks/Integrations**: Platform-specific integrations must be reconfigured manually
6. **Multi-project**: Currently supports single project migration; run separately for each project

## Error Handling

The migration script implements:
- **Idempotent operations**: Skip if flag/segment already exists
- **Dry-run mode**: Preview changes without executing
- **Detailed logging**: Track every API call and transformation
- **Rollback support**: Extraction snapshots enable re-running

## Support

For issues with:
- **DevCycle API**: https://docs.devcycle.com/
- **LaunchDarkly API**: https://launchdarkly.com/docs/api
- **This migration tool**: Open an issue in this repository

---

*Generated for financial services feature flag migration project*
