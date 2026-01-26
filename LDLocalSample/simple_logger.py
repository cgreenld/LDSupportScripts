import logging
import os
from datetime import datetime


class SimpleLogger:
    """A simple logging helper for Flask apps."""
    
    def __init__(self, app_name="LDApp", log_file="app.log"):
        self.app_name = app_name
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # File handler
        file_handler = logging.FileHandler(f"logs/{log_file}")
        file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_format = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
    
    def info(self, message):
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message):
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message):
        """Log error message."""
        self.logger.error(message)
    
    def debug(self, message):
        """Log debug message."""
        self.logger.debug(message)
    
    def log_request(self, method, path, status_code=None):
        """Log HTTP request."""
        if status_code:
            self.info(f"{method} {path} - Status: {status_code}")
        else:
            self.info(f"{method} {path}")
    
    def log_feature_flag(self, flag_name, result):
        """Log feature flag evaluation."""
        self.info(f"Feature flag '{flag_name}' = {result}")
