#!/usr/bin/env python3
"""
DevCycle to LaunchDarkly Migration Tool

Main entry point for the migration CLI
"""

import json
import os
import sys
import time
from pathlib import Path

# Add src directory to path for direct script execution
_src_dir = Path(__file__).parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

import click
from dotenv import load_dotenv

from devcycle.extractor import DevCycleExtractor
from launchdarkly.loader import LaunchDarklyLoader
from transform.flags import FlagTransformer
from utils.logger import Logger
from utils.report import ReportGenerator

# Load environment variables
load_dotenv()

# Initialize logger
logger = Logger(os.getenv('LOG_LEVEL', 'info'))


def parse_environment_map(map_string: str) -> dict:
    """Parse environment mapping from string."""
    if not map_string:
        return {}
    
    result = {}
    for pair in map_string.split(','):
        parts = pair.split(':')
        if len(parts) == 2:
            result[parts[0].strip()] = parts[1].strip()
    
    return result


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """Migrate feature flags from DevCycle to LaunchDarkly."""
    pass


@cli.command()
@click.option('-o', '--output', default='./snapshots/extraction.json', help='Output file path')
def extract(output: str):
    """Extract features and audiences from DevCycle."""
    logger.info('Starting DevCycle extraction...')
    
    extractor = DevCycleExtractor({
        'clientId': os.getenv('DEVCYCLE_CLIENT_ID'),
        'clientSecret': os.getenv('DEVCYCLE_CLIENT_SECRET'),
        'projectId': os.getenv('DEVCYCLE_PROJECT_ID')
    })
    
    try:
        data = extractor.extract_all()
        
        # Ensure output directory exists
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write extraction snapshot
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Extraction complete. {len(data['features'])} features extracted.")
        logger.info(f"Output saved to: {output}")
    
    except Exception as e:
        import traceback
        logger.error(f'Extraction failed: {str(e)}')
        if os.getenv('LOG_LEVEL', '').lower() == 'debug':
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option('-i', '--input', 'input_file', default='./snapshots/extraction.json', help='Input extraction file')
@click.option('-o', '--output', default='./snapshots/transformed.json', help='Output transformed file')
@click.option('--preview', is_flag=True, help='Preview transformation without saving')
def transform(input_file: str, output: str, preview: bool):
    """Transform DevCycle data to LaunchDarkly format."""
    logger.info('Starting transformation...')
    
    try:
        with open(input_file, 'r') as f:
            extracted_data = json.load(f)
        
        transformer = FlagTransformer({
            'environmentMap': parse_environment_map(os.getenv('ENVIRONMENT_MAP', ''))
        })
        
        transformed = transformer.transform_all(extracted_data)
        
        if preview:
            logger.info('Transformation preview:')
            print(json.dumps(transformed, indent=2))
        else:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(transformed, f, indent=2)
            logger.info(f"Transformation complete. Output saved to: {output}")
        
        # Summary
        logger.info(f"Flags: {len(transformed['flags'])}")
        logger.info(f"Segments: {len(transformed['segments'])}")
    
    except Exception as e:
        logger.error(f'Transformation failed: {str(e)}')
        sys.exit(1)


@cli.command()
@click.option('--skip-extract', is_flag=True, help='Skip extraction, use existing snapshot')
@click.option('-i', '--input', 'input_file', default='./snapshots/extraction.json', help='Input extraction file (if skipping extract)')
def migrate(skip_extract: bool, input_file: str):
    """Run full migration from DevCycle to LaunchDarkly."""
    dry_run = os.getenv('DRY_RUN', 'true').lower() != 'false'
    logger.info(f'Starting migration (dry-run: {dry_run})...')
    
    report = ReportGenerator()
    
    try:
        extracted_data = None
        
        # Phase 1: Extract
        if not skip_extract:
            logger.info('Phase 1: Extracting from DevCycle...')
            extractor = DevCycleExtractor({
                'clientId': os.getenv('DEVCYCLE_CLIENT_ID'),
                'clientSecret': os.getenv('DEVCYCLE_CLIENT_SECRET'),
                'projectId': os.getenv('DEVCYCLE_PROJECT_ID')
            })
            extracted_data = extractor.extract_all()
            report.add_phase('extraction', {
                'features': len(extracted_data['features']),
                'audiences': len(extracted_data['audiences'])
            })
        else:
            logger.info('Phase 1: Loading existing extraction...')
            with open(input_file, 'r') as f:
                extracted_data = json.load(f)
        
        # Phase 2: Transform
        logger.info('Phase 2: Transforming data...')
        transformer = FlagTransformer({
            'environmentMap': parse_environment_map(os.getenv('ENVIRONMENT_MAP', ''))
        })
        transformed = transformer.transform_all(extracted_data)
        report.add_phase('transformation', {
            'flags': len(transformed['flags']),
            'segments': len(transformed['segments'])
        })
        
        # Phase 3: Load
        logger.info('Phase 3: Loading into LaunchDarkly...')
        loader = LaunchDarklyLoader({
            'apiToken': os.getenv('LD_API_TOKEN'),
            'projectKey': os.getenv('LD_PROJECT_KEY'),
            'dryRun': dry_run
        })
        
        # Pass source environments to create them in LD if they don't exist
        source_environments = extracted_data.get('environments', [])
        load_results = loader.load_all(transformed, source_environments=source_environments)
        report.add_phase('loading', load_results)
        
        # Generate final report
        final_report = report.generate()
        
        # Save report
        reports_dir = Path('./reports')
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"migration-{int(time.time() * 1000)}.json"
        
        with open(report_path, 'w') as f:
            json.dump(final_report, f, indent=2)
        
        logger.info('Migration complete!')
        logger.info(f'Report saved to: {report_path}')
        print('\n--- Migration Summary ---')
        print(json.dumps(final_report['summary'], indent=2))
    
    except Exception as e:
        logger.error(f'Migration failed: {str(e)}')
        sys.exit(1)


@cli.command()
@click.option('--flag', help='Verify specific flag key')
def verify(flag: str):
    """Verify migration by comparing flags between platforms."""
    logger.info('Starting verification...')
    logger.warn('Verification not yet implemented')
    # TODO: Implement verification logic


if __name__ == '__main__':
    cli()

