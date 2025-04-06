"""
EdgePrompt Runner CLI - Command-line interface for running experiments

This module provides a command-line entry point for executing
EdgePrompt experiments using the RunnerCore class.
"""

import argparse
import os
import sys
import logging
import json
from datetime import datetime

# Add parent directory to path to enable imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from runner.runner_core import RunnerCore

def setup_logging(log_level_str, log_file=None):
    """Configure logging for the CLI"""
    log_level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    log_level = log_level_map.get(log_level_str.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Return configured logger
    return root_logger

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='EdgePrompt Research Runner CLI'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        required=True,
        help='Path to the test suite configuration JSON file'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='./output',
        help='Directory for storing results (default: ./output)'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        help='Log file path (optional)'
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the runner CLI"""
    args = parse_args()
    
    # Set up logging
    log_file = args.log_file or os.path.join(args.output, 'runner.log')
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logger = setup_logging(args.log_level, log_file)
    
    # Log execution start
    logger.info(f"EdgePrompt Runner starting with config: {args.config}")
    start_time = datetime.now()
    
    try:
        # Ensure output directory exists
        os.makedirs(args.output, exist_ok=True)
        
        # Initialize runner
        runner = RunnerCore(
            config_path=args.config,
            output_dir=args.output,
            log_level=args.log_level
        )
        
        # Run test suite
        results = runner.run_test_suite()
        
        # Save results to output file
        output_file = os.path.join(
            args.output, 
            f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to: {output_file}")
        
        # Log execution completion
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Test suite execution completed in {duration:.2f} seconds")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error executing test suite: {str(e)}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main()) 