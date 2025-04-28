#!/usr/bin/env python3
"""
Setup Test Environment

This script creates necessary directories and files for testing.
"""

import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_test_environment():
    """Set up the test environment."""
    logger.info("Setting up test environment")
    
    # Create directories
    directories = [
        "data/visuals",
        "test_results"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")
    
    # Create __init__.py files for test directories if needed
    test_packages = [
        "tests",
        "tests/test_agents",
        "tests/test_integration",
        "tests/test_models",
        "tests/test_services"
    ]
    
    for package in test_packages:
        os.makedirs(package, exist_ok=True)
        init_file = os.path.join(package, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                pass
            logger.info(f"Created file: {init_file}")
    
    logger.info("Test environment setup complete")

if __name__ == "__main__":
    setup_test_environment()