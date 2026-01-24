"""
Logger Utility

Simple logging with level support
"""

from datetime import datetime


class Logger:
    """Logger class with configurable log levels."""
    
    LEVELS = {
        'debug': 0,
        'info': 1,
        'warn': 2,
        'error': 3
    }
    
    def __init__(self, level: str = 'info'):
        """Initialize logger with specified level."""
        self.current_level = self.LEVELS.get(level.lower(), 1)
    
    def _timestamp(self) -> str:
        """Format current timestamp."""
        return datetime.utcnow().isoformat() + 'Z'
    
    def debug(self, *args):
        """Debug level log."""
        if self.current_level <= self.LEVELS['debug']:
            print(f"[{self._timestamp()}] [DEBUG]", *args)
    
    def info(self, *args):
        """Info level log."""
        if self.current_level <= self.LEVELS['info']:
            print(f"[{self._timestamp()}] [INFO]", *args)
    
    def warn(self, *args):
        """Warning level log."""
        if self.current_level <= self.LEVELS['warn']:
            print(f"[{self._timestamp()}] [WARN]", *args)
    
    def error(self, *args):
        """Error level log."""
        if self.current_level <= self.LEVELS['error']:
            print(f"[{self._timestamp()}] [ERROR]", *args)

