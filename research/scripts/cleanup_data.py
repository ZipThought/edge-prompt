#!/usr/bin/env python3
"""
EdgePrompt Data Cleanup Script

This script organizes the data directory by:
1. Creating backups of all important files 
2. Properly processing JSONL files (the primary experimental data format)
3. Removing only clearly identified duplicates and temporary files
4. Consolidating metrics in a simple, deterministic way
"""

import os
import sys
import json
import shutil
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Set, Tuple
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

def collect_test_suites(data_dir: str, logger: logging.Logger) -> Dict[str, Dict[str, List[str]]]:
    """
    Collect all test suites and their result files, categorizing them by type.
    
    Args:
        data_dir: Base data directory
        logger: Logger instance
        
    Returns:
        Dictionary mapping test suite names to dictionaries of file types and paths
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
            # Find all result files by type
            json_files = glob.glob(os.path.join(suite_dir, '*.json'))
            jsonl_files = glob.glob(os.path.join(suite_dir, '*.jsonl'))
            summary_files = [f for f in json_files if os.path.basename(f).startswith('results_')]
            individual_json_files = [f for f in json_files if not os.path.basename(f).startswith('results_')]
            
            test_suites[item] = {
                'jsonl': jsonl_files,
                'summary': summary_files,
                'individual': individual_json_files
            }
            
            logger.info(f"Found test suite '{item}' with {len(jsonl_files)} JSONL files, "
                       f"{len(summary_files)} summary files, and {len(individual_json_files)} individual result files")
            
    return test_suites

def backup_all_data(test_suites: Dict[str, Dict[str, List[str]]], data_dir: str, logger: logging.Logger) -> None:
    """
    Create backups of all data files before processing.
    
    Args:
        test_suites: Dictionary mapping test suite names to dictionaries of file types and paths
        data_dir: Base data directory
        logger: Logger instance
    """
    backup_dir = os.path.join(data_dir, 'backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    
    # Create backup directory
    os.makedirs(backup_dir, exist_ok=True)
    logger.info(f"Created backup directory: {backup_dir}")
    
    # Backup each test suite
    for suite_name, files in test_suites.items():
        suite_backup = os.path.join(backup_dir, suite_name)
        os.makedirs(suite_backup, exist_ok=True)
        
        # Backup all files
        all_files = files['jsonl'] + files['summary'] + files['individual']
        for file_path in all_files:
            dest_file = os.path.join(suite_backup, os.path.basename(file_path))
            try:
                shutil.copy2(file_path, dest_file)
                logger.debug(f"Backed up: {file_path} -> {dest_file}")
            except Exception as e:
                logger.error(f"Error backing up {file_path}: {str(e)}")
    
    logger.info(f"All data backed up to: {backup_dir}")
    return backup_dir

def extract_jsonl_data(jsonl_files: List[str], logger: logging.Logger) -> List[Dict[str, Any]]:
    """
    Extract data from JSONL files with simple deterministic logic.
    
    Args:
        jsonl_files: List of JSONL file paths
        logger: Logger instance
        
    Returns:
        List of extracted records
    """
    all_records = []
    
    # Process each JSONL file
    for file_path in jsonl_files:
        record_count = 0
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        record['_source_file'] = file_path  # Add source tracking
                        all_records.append(record)
                        record_count += 1
                    except json.JSONDecodeError as e:
                        logger.warning(f"Skipping invalid JSON line in {file_path}: {e}")
                        continue
            
            logger.info(f"Extracted {record_count} records from JSONL file: {file_path}")
        except Exception as e:
            logger.error(f"Error processing JSONL file {file_path}: {str(e)}")
    
    return all_records

def archive_old_runs(test_suites: Dict[str, Dict[str, List[str]]], data_dir: str, logger: logging.Logger) -> None:
    """
    Archive old runs by copying them to an 'archive' directory.
    
    Args:
        test_suites: Dictionary mapping test suite names to dictionaries of file types and paths
        data_dir: Base data directory
        logger: Logger instance
    """
    archive_dir = os.path.join(data_dir, 'archive')
    
    # Create archive directory if it doesn't exist
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)
        logger.info(f"Created archive directory: {archive_dir}")
    
    # Process each test suite
    for suite_name, files in test_suites.items():
        logger.info(f"Archiving old runs for test suite: {suite_name}")
        
        # Create archive directory for this suite if it doesn't exist
        suite_archive = os.path.join(archive_dir, suite_name)
        os.makedirs(suite_archive, exist_ok=True)
        
        # Archive summary files except the most recent one (by timestamp)
        if len(files['summary']) > 1:
            # Sort by modification time (newest first)
            sorted_summaries = sorted(files['summary'], key=os.path.getmtime, reverse=True)
            
            # Keep the most recent, archive the rest
            most_recent = sorted_summaries[0]
            to_archive = sorted_summaries[1:]
            
            logger.info(f"Keeping most recent summary: {os.path.basename(most_recent)}")
            
            # Archive older summaries
            for file_path in to_archive:
                filename = os.path.basename(file_path)
                timestamp = filename.replace('results_', '').replace('.json', '')
                
                # Create timestamp directory
                timestamp_dir = os.path.join(suite_archive, timestamp)
                os.makedirs(timestamp_dir, exist_ok=True)
                
                # Copy to archive
                dest_file = os.path.join(timestamp_dir, filename)
                try:
                    shutil.copy2(file_path, dest_file)
                    logger.info(f"Archived summary: {filename}")
                except Exception as e:
                    logger.error(f"Error archiving {file_path}: {str(e)}")

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

def consolidate_results(test_suites: Dict[str, Dict[str, List[str]]], data_dir: str, logger: logging.Logger) -> None:
    """
    Consolidate results into processed metrics files, using a deterministic approach.
    
    Args:
        test_suites: Dictionary mapping test suite names to dictionaries of file types and paths
        data_dir: Base data directory
        logger: Logger instance
    """
    processed_dir = os.path.join(data_dir, 'processed')
    
    # Ensure processed directory exists
    os.makedirs(processed_dir, exist_ok=True)
    
    # Process each test suite
    for suite_name, files in test_suites.items():
        logger.info(f"Consolidating results for test suite: {suite_name}")
        
        # Process JSONL files (primary source of truth)
        if files['jsonl']:
            # Extract all records from JSONL files
            all_records = extract_jsonl_data(files['jsonl'], logger)
            
            if all_records:
                # Group by model for consolidated metrics
                results_by_model = {}
                
                for record in all_records:
                    model_id = record.get('model_id', 'unknown')
                    
                    if model_id not in results_by_model:
                        results_by_model[model_id] = []
                    
                    # Extract basic metrics
                    test_case_id = record.get('test_case_id', 'unknown') 
                    metrics = {
                        'test_case_id': test_case_id,
                        'hardware_profile': record.get('hardware_profile', 'unknown'),
                        'execution_time_ms': record.get('metrics', {}).get('execution_time_ms', 0),
                        'memory_usage_mb': record.get('metrics', {}).get('memory_usage_mb', 0),
                        'is_valid': record.get('validation_result', {}).get('isValid', False),
                        'validation_score': record.get('validation_result', {}).get('score', 0),
                        'has_error': 'error' in record,
                        'timestamp': record.get('timestamp', ''),
                        'source': 'jsonl'
                    }
                    
                    results_by_model[model_id].append(metrics)
                
                # Save metrics by model
                for model_id, metrics in results_by_model.items():
                    output_file = os.path.join(processed_dir, f'{suite_name}_{model_id}_metrics.json')
                    with open(output_file, 'w') as f:
                        json.dump(metrics, f, indent=2)
                    logger.info(f"Saved {len(metrics)} metrics for {model_id} to: {output_file}")
        
        # If no JSONL, try using summary file as fallback
        elif files['summary'] and not files['jsonl']:
            # Take the most recent summary
            latest_summary = sorted(files['summary'], key=os.path.getmtime, reverse=True)[0]
            logger.info(f"No JSONL files for {suite_name}, using summary: {os.path.basename(latest_summary)}")
            
            try:
                with open(latest_summary, 'r') as f:
                    summary_data = json.load(f)
                
                # Extract and group by model
                results_by_model = {}
                
                for result in summary_data.get('raw_results', []):
                    model_id = result.get('model_id', 'unknown')
                    
                    if model_id not in results_by_model:
                        results_by_model[model_id] = []
                    
                    # Extract basic metrics
                    metrics = {
                        'test_case_id': result.get('test_case_id', 'unknown'),
                        'hardware_profile': result.get('hardware_profile', 'unknown'),
                        'execution_time_ms': result.get('metrics', {}).get('execution_time_ms', 0),
                        'memory_usage_mb': result.get('metrics', {}).get('memory_usage_mb', 0),
                        'is_valid': result.get('validation_result', {}).get('isValid', False),
                        'validation_score': result.get('validation_result', {}).get('score', 0),
                        'timestamp': result.get('timestamp', ''),
                        'source': 'summary'
                    }
                    
                    results_by_model[model_id].append(metrics)
                
                # Save metrics by model
                for model_id, metrics in results_by_model.items():
                    output_file = os.path.join(processed_dir, f'{suite_name}_{model_id}_metrics.json')
                    with open(output_file, 'w') as f:
                        json.dump(metrics, f, indent=2)
                    logger.info(f"Saved {len(metrics)} metrics for {model_id} to: {output_file}")
            
            except Exception as e:
                logger.error(f"Error processing summary file {latest_summary}: {str(e)}")
        else:
            logger.warning(f"No JSONL or summary files found for suite: {suite_name}")

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
        '--skip-backup',
        action='store_true',
        help='Skip creating backup (use with caution)'
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
    
    # Create backup before any modifications
    if not args.skip_backup:
        logger.info("Creating backup of all data...")
        backup_dir = backup_all_data(test_suites, args.data_dir, logger)
        logger.info(f"Backup created at: {backup_dir}")
    
    # Archive old runs
    if not args.skip_archive:
        logger.info("Archiving old runs...")
        archive_old_runs(test_suites, args.data_dir, logger)
    
    # Remove temporary files
    logger.info("Removing temporary files...")
    remove_temp_files(args.data_dir, logger)
    
    # Consolidate results
    logger.info("Consolidating results...")
    consolidate_results(test_suites, args.data_dir, logger)
    
    logger.info("Data cleanup completed successfully")
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 