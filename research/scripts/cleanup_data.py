#!/usr/bin/env python3
"""
EdgePrompt Data Cleanup Script

This script cleans up and organizes the data directory by:
1. Removing duplicate test results
2. Archiving old test runs
3. Consolidating results into a clean format
4. Removing any temporary files
"""

import os
import sys
import json
import shutil
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Set
import glob

# Add parent directory to path to enable imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure logging for the script"""
    log_level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR
    }
    
    # Configure root logger
    logging.basicConfig(
        level=log_level_map.get(log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create logger
    logger = logging.getLogger('edgeprompt.cleanup')
    return logger

def collect_test_suites(data_dir: str, logger: logging.Logger) -> Dict[str, List[str]]:
    """
    Collect all test suites and their result files.
    
    Args:
        data_dir: Base data directory
        logger: Logger instance
        
    Returns:
        Dictionary mapping test suite names to lists of result file paths
    """
    raw_dir = os.path.join(data_dir, 'raw')
    if not os.path.exists(raw_dir):
        logger.warning(f"Raw data directory not found: {raw_dir}")
        return {}
        
    # Get all subdirectories in raw (each is a test suite)
    test_suites = {}
    for item in os.listdir(raw_dir):
        suite_dir = os.path.join(raw_dir, item)
        if os.path.isdir(suite_dir):
            # Find all JSON files in this test suite
            result_files = glob.glob(os.path.join(suite_dir, '*.json'))
            test_suites[item] = result_files
            logger.info(f"Found test suite '{item}' with {len(result_files)} result files")
            
    return test_suites

def find_duplicates(result_files: List[str], logger: logging.Logger) -> Dict[str, List[str]]:
    """
    Find duplicate test case results based on test_case_id, model_id, and timestamp.
    Group them by test_case_id+model_id.
    
    Args:
        result_files: List of result file paths
        logger: Logger instance
        
    Returns:
        Dictionary mapping test identifiers to lists of duplicate file paths
    """
    # Group results by test case ID and model ID
    grouped_results = {}
    
    for file_path in result_files:
        try:
            # Skip results summary files (they start with 'results_')
            if os.path.basename(file_path).startswith('results_'):
                continue
                
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Extract identifiers
            test_case_id = data.get('test_case_id', '')
            model_id = data.get('model_id', '')
            
            if not test_case_id or not model_id:
                logger.warning(f"Missing test_case_id or model_id in file: {file_path}")
                continue
                
            # Create a group key
            group_key = f"{test_case_id}_{model_id}"
            
            if group_key not in grouped_results:
                grouped_results[group_key] = []
                
            grouped_results[group_key].append(file_path)
                
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error processing file {file_path}: {str(e)}")
            continue
    
    # Filter to only groups with duplicates
    duplicates = {k: v for k, v in grouped_results.items() if len(v) > 1}
    
    for group, files in duplicates.items():
        logger.info(f"Found {len(files)} duplicate results for {group}")
        
    return duplicates

def get_most_recent_files(duplicates: Dict[str, List[str]], logger: logging.Logger) -> Dict[str, str]:
    """
    For each group of duplicates, determine the most recent file to keep.
    
    Args:
        duplicates: Dictionary mapping test identifiers to lists of duplicate file paths
        logger: Logger instance
        
    Returns:
        Dictionary mapping test identifiers to the path of the file to keep
    """
    files_to_keep = {}
    
    for group, file_paths in duplicates.items():
        # Sort by file modification time (most recent first)
        sorted_files = sorted(file_paths, key=os.path.getmtime, reverse=True)
        
        # Keep the most recent file
        files_to_keep[group] = sorted_files[0]
        logger.info(f"Keeping most recent file for {group}: {os.path.basename(sorted_files[0])}")
        
    return files_to_keep

def archive_old_runs(data_dir: str, logger: logging.Logger) -> None:
    """
    Archive old runs by moving them to an 'archive' directory.
    
    Args:
        data_dir: Base data directory
        logger: Logger instance
    """
    raw_dir = os.path.join(data_dir, 'raw')
    archive_dir = os.path.join(data_dir, 'archive')
    
    # Create archive directory if it doesn't exist
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)
        logger.info(f"Created archive directory: {archive_dir}")
    
    # Get list of all result directories
    for item in os.listdir(raw_dir):
        suite_dir = os.path.join(raw_dir, item)
        if not os.path.isdir(suite_dir):
            continue
            
        # Check summary files to find old runs
        summary_files = glob.glob(os.path.join(suite_dir, 'results_*.json'))
        
        # If more than one summary file, archive all but the most recent
        if len(summary_files) <= 1:
            continue
            
        # Sort by file modification time (oldest first)
        sorted_files = sorted(summary_files, key=os.path.getmtime)
        
        # Keep the most recent, archive the rest
        files_to_archive = sorted_files[:-1]
        
        for file_path in files_to_archive:
            # Extract timestamp from filename
            filename = os.path.basename(file_path)
            timestamp = filename.replace('results_', '').replace('.json', '')
            
            # Create archive directory for this timestamp if it doesn't exist
            timestamp_archive = os.path.join(archive_dir, item, timestamp)
            os.makedirs(timestamp_archive, exist_ok=True)
            
            # Find all files from this run (based on timestamp)
            run_files = glob.glob(os.path.join(suite_dir, f'*{timestamp}*'))
            
            # Move files to archive
            for run_file in run_files:
                dest_file = os.path.join(timestamp_archive, os.path.basename(run_file))
                try:
                    shutil.move(run_file, dest_file)
                    logger.info(f"Archived: {run_file} -> {dest_file}")
                except Exception as e:
                    logger.error(f"Error archiving {run_file}: {str(e)}")

def remove_temp_files(data_dir: str, logger: logging.Logger) -> None:
    """
    Remove temporary files from the data directory.
    
    Args:
        data_dir: Base data directory
        logger: Logger instance
    """
    # Common temporary files to remove
    temp_patterns = [
        '*.tmp',
        '*.temp',
        '*~',
        '*.bak',
        '.DS_Store',
        'Thumbs.db'
    ]
    
    # Find and remove temporary files
    for pattern in temp_patterns:
        temp_files = glob.glob(os.path.join(data_dir, '**', pattern), recursive=True)
        for file_path in temp_files:
            try:
                os.remove(file_path)
                logger.info(f"Removed temporary file: {file_path}")
            except Exception as e:
                logger.error(f"Error removing {file_path}: {str(e)}")

def consolidate_results(data_dir: str, logger: logging.Logger) -> None:
    """
    Consolidate and standardize result files.
    
    Args:
        data_dir: Base data directory
        logger: Logger instance
    """
    raw_dir = os.path.join(data_dir, 'raw')
    processed_dir = os.path.join(data_dir, 'processed')
    
    # Ensure processed directory exists
    os.makedirs(processed_dir, exist_ok=True)
    
    # Process each test suite
    for item in os.listdir(raw_dir):
        suite_dir = os.path.join(raw_dir, item)
        if not os.path.isdir(suite_dir):
            continue
            
        # Find the most recent summary file
        summary_files = glob.glob(os.path.join(suite_dir, 'results_*.json'))
        if not summary_files:
            logger.warning(f"No summary files found for test suite: {item}")
            continue
            
        # Sort by file modification time (most recent first)
        latest_summary = sorted(summary_files, key=os.path.getmtime, reverse=True)[0]
        
        try:
            # Load the summary file
            with open(latest_summary, 'r') as f:
                summary_data = json.load(f)
                
            # Extract and standardize metrics
            results_by_model = {}
            for result in summary_data.get('raw_results', []):
                model_id = result.get('model_id', 'unknown')
                test_case_id = result.get('test_case_id', 'unknown')
                
                if model_id not in results_by_model:
                    results_by_model[model_id] = []
                    
                # Extract key metrics
                metrics = {
                    'test_case_id': test_case_id,
                    'hardware_profile': result.get('hardware_profile', 'unknown'),
                    'execution_time_ms': result.get('metrics', {}).get('execution_time_ms', 0),
                    'memory_usage_mb': result.get('metrics', {}).get('memory_usage_mb', 0),
                    'is_valid': result.get('validation_result', {}).get('isValid', False),
                    'validation_score': result.get('validation_result', {}).get('score', 0)
                }
                
                results_by_model[model_id].append(metrics)
            
            # Save standardized results for each model
            for model_id, results in results_by_model.items():
                output_file = os.path.join(processed_dir, f'{item}_{model_id}_metrics.json')
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)
                logger.info(f"Consolidated metrics saved to: {output_file}")
                
        except Exception as e:
            logger.error(f"Error processing summary file {latest_summary}: {str(e)}")

def cleanup_duplicates(test_suites: Dict[str, List[str]], logger: logging.Logger) -> None:
    """
    Clean up duplicate test case results by keeping only the most recent version.
    
    Args:
        test_suites: Dictionary mapping test suite names to lists of result file paths
        logger: Logger instance
    """
    for suite_name, result_files in test_suites.items():
        logger.info(f"Checking for duplicates in test suite: {suite_name}")
        
        # Find duplicate result files
        duplicates = find_duplicates(result_files, logger)
        
        if not duplicates:
            logger.info(f"No duplicates found in test suite: {suite_name}")
            continue
            
        # Determine which files to keep
        files_to_keep = get_most_recent_files(duplicates, logger)
        
        # Delete older duplicates
        for group, duplicate_files in duplicates.items():
            keep_file = files_to_keep[group]
            for file_path in duplicate_files:
                if file_path != keep_file:
                    try:
                        os.remove(file_path)
                        logger.info(f"Removed duplicate: {file_path}")
                    except Exception as e:
                        logger.error(f"Error removing {file_path}: {str(e)}")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='EdgePrompt Data Cleanup Script'
    )
    
    parser.add_argument(
        '--data-dir',
        type=str,
        default='../data',
        help='Base data directory (default: ../data)'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--skip-archive',
        action='store_true',
        help='Skip archiving old runs'
    )
    
    parser.add_argument(
        '--skip-duplicates',
        action='store_true',
        help='Skip removing duplicate files'
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the data cleanup script"""
    args = parse_args()
    
    # Set up logging
    logger = setup_logging(args.log_level)
    
    logger.info(f"Starting data cleanup in directory: {args.data_dir}")
    
    # Collect test suites
    test_suites = collect_test_suites(args.data_dir, logger)
    
    if not test_suites:
        logger.error("No test suites found. Nothing to clean up.")
        return 1
    
    # Clean up duplicate files
    if not args.skip_duplicates:
        logger.info("Cleaning up duplicate files...")
        cleanup_duplicates(test_suites, logger)
    
    # Archive old runs
    if not args.skip_archive:
        logger.info("Archiving old runs...")
        archive_old_runs(args.data_dir, logger)
    
    # Remove temporary files
    logger.info("Removing temporary files...")
    remove_temp_files(args.data_dir, logger)
    
    # Consolidate results
    logger.info("Consolidating results...")
    consolidate_results(args.data_dir, logger)
    
    logger.info("Data cleanup completed successfully")
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 