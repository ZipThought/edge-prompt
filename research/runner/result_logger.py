"""
ResultLogger - Handles logging of experiment results.

This module provides functionality for logging, storing, and organizing
results from EdgePrompt experiments.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

class ResultLogger:
    """
    Logs and stores experiment results.
    
    This class handles:
    - Writing results to files
    - Organizing results by test suite/case
    - Aggregating results for analysis
    """
    
    def __init__(self, output_dir: str):
        """
        Initialize the ResultLogger.
        
        Args:
            output_dir: Directory for storing results
        """
        self.logger = logging.getLogger("edgeprompt.runner.results")
        self.output_dir = output_dir
        self._ensure_output_dir()
        self.logger.info(f"ResultLogger initialized with output dir: {output_dir}")
    
    def _ensure_output_dir(self) -> None:
        """Create the output directory if it doesn't exist"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
            self.logger.info(f"Created output directory: {self.output_dir}")
    
    def log_result(self, result: Dict[str, Any]) -> str:
        """
        Log a test result.
        
        Args:
            result: The test result to log
            
        Returns:
            Path to the logged result file
        """
        self.logger.info(f"Logging result for test: {result.get('id', 'unknown')}")
        
        # Create a filename based on the test ID and timestamp
        test_id = result.get('id', 'unknown')
        timestamp = result.get('timestamp', datetime.now().isoformat())
        filename = f"{test_id}_{timestamp.replace(':', '-')}.json"
        
        # Ensure safe filename
        filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        
        # Construct the full path
        file_path = os.path.join(self.output_dir, filename)
        
        # Write the result to the file
        with open(file_path, 'w') as f:
            json.dump(result, f, indent=2)
            
        self.logger.info(f"Result logged to: {file_path}")
        
        # Also append to a JSONL file for easier batch processing
        jsonl_path = os.path.join(self.output_dir, "all_results.jsonl")
        with open(jsonl_path, 'a') as f:
            f.write(json.dumps(result) + "\n")
            
        return file_path
    
    def log_aggregate_results(self, results: List[Dict[str, Any]], name: str) -> str:
        """
        Log aggregate results from multiple tests.
        
        Args:
            results: List of test results
            name: Name for the aggregate results
            
        Returns:
            Path to the logged aggregate results file
        """
        self.logger.info(f"Logging aggregate results: {name} ({len(results)} results)")
        
        # Create a filename based on the name and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.json"
        
        # Ensure safe filename
        filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        
        # Construct the full path
        file_path = os.path.join(self.output_dir, filename)
        
        # Write the results to the file
        with open(file_path, 'w') as f:
            json.dump(results, f, indent=2)
            
        self.logger.info(f"Aggregate results logged to: {file_path}")
        
        return file_path
    
    def get_all_results(self) -> List[Dict[str, Any]]:
        """
        Get all logged results.
        
        Returns:
            List of all test results
        """
        results = []
        
        # Check if the JSONL file exists
        jsonl_path = os.path.join(self.output_dir, "all_results.jsonl")
        if os.path.exists(jsonl_path):
            with open(jsonl_path, 'r') as f:
                for line in f:
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Error decoding result: {str(e)}")
                        
            self.logger.info(f"Loaded {len(results)} results from {jsonl_path}")
            return results
        
        # If JSONL file doesn't exist, try loading individual files
        for filename in os.listdir(self.output_dir):
            if filename.endswith(".json") and filename != "all_results.json":
                file_path = os.path.join(self.output_dir, filename)
                try:
                    with open(file_path, 'r') as f:
                        results.append(json.load(f))
                except json.JSONDecodeError as e:
                    self.logger.error(f"Error decoding result file {filename}: {str(e)}")
                    
        self.logger.info(f"Loaded {len(results)} results from individual files")
        
        return results