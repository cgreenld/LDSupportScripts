"""Entry point for running as a module: python -m src"""
import sys
from pathlib import Path

# Add src directory to path
_src_dir = Path(__file__).parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from main import cli

if __name__ == '__main__':
    cli()

