#!/usr/bin/env python3
"""
EdgePrompt Results Analyzer

This script processes the raw JSONL data from experiments and
generates processed datasets for visualization.
"""

import os
import sys
import json
import logging
import argparse
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime

# Add parent directory to path to enable imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure logging for the analyzer"""
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
    logger = logging.getLogger('edgeprompt.analyze')
    return logger

def load_results(data_dir: str, logger: logging.Logger) -> pd.DataFrame:
    """
    Load all results from JSONL files into a pandas DataFrame.
    
    Args:
        data_dir: Directory containing raw data files
        logger: Logger instance
    
    Returns:
        DataFrame with all results
    """
    results = []
    
    # Check for JSONL file first (most efficient)
    jsonl_path = os.path.join(data_dir, "all_results.jsonl")
    if os.path.exists(jsonl_path):
        logger.info(f"Loading results from {jsonl_path}")
        with open(jsonl_path, 'r') as f:
            for line in f:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"Skipping invalid JSON line in {jsonl_path}")
                    
    # If no JSONL or no results, try individual JSON files (both in data_dir and subdirectories)
    if not results:
        logger.info(f"No JSONL file found, checking individual JSON files in {data_dir} and subdirectories")
        
        # Function to process JSON files in a directory
        def process_json_files(directory):
            nonlocal results
            if not os.path.exists(directory):
                return
                
            for item in os.listdir(directory):
                full_path = os.path.join(directory, item)
                if os.path.isdir(full_path):
                    # Process subdirectories for test suite results
                    process_json_files(full_path)
                elif item.endswith('.json'):
                    try:
                        with open(full_path, 'r') as f:
                            data = json.load(f)
                            # Only add result files that have the expected structure
                            if isinstance(data, dict) and any(key in data for key in ['id', 'test_case_id', 'model_id']):
                                # Add test_suite_id if missing by inferring from path
                                if 'test_suite_id' not in data:
                                    path_parts = full_path.split(os.sep)
                                    # Try to find known test suite names in the path
                                    for part in path_parts:
                                        if part in ['multi_stage_validation', 'neural_symbolic_validation', 'resource_optimization']:
                                            data['test_suite_id'] = part
                                            break
                                results.append(data)
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping invalid JSON file: {full_path}")
        
        # Process the data directory and its subdirectories
        process_json_files(data_dir)
    
    logger.info(f"Loaded {len(results)} results")
    
    if not results:
        logger.warning("No results found!")
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.json_normalize(results)
    return df

def analyze_multi_stage_validation(df: pd.DataFrame, output_dir: str, logger: logging.Logger) -> None:
    """
    Analyze multi-stage validation results.
    
    Args:
        df: DataFrame with results
        output_dir: Directory to save processed results
        logger: Logger instance
    """
    # Check if test_suite_id column exists
    if 'test_suite_id' not in df.columns:
        # Try to infer from the file path or result content
        logger.info("No test_suite_id column found, attempting to infer from data")
        
        # Check for paths or filenames containing 'multi_stage_validation'
        if any(df.get('id', '').str.contains('multi_stage_validation').fillna(False)):
            df['test_suite_id'] = 'multi_stage_validation'
        else:
            # Assume all results are from the most recently run test suite
            df['test_suite_id'] = 'multi_stage_validation'
            logger.warning("Assuming all results are from multi_stage_validation test suite")
    
    # Filter for multi-stage validation test suite
    validation_df = df[df['test_suite_id'] == 'multi_stage_validation'].copy()
    
    if validation_df.empty:
        logger.warning("No multi-stage validation results found")
        return
        
    logger.info(f"Analyzing {len(validation_df)} multi-stage validation results")
    
    # Create stage effectiveness data
    stage_data = []
    
    # Extract stage results
    for _, row in validation_df.iterrows():
        if not isinstance(row.get('validation_result', {}).get('stageResults'), list):
            continue
            
        for stage in row['validation_result']['stageResults']:
            stage_data.append({
                'test_case_id': row.get('test_case_id', 'unknown'),
                'model_id': row.get('model_id', 'unknown'),
                'hardware_profile': row.get('hardware_profile', 'unknown'),
                'stage_id': stage.get('stageId', 'unknown'),
                'passed': stage.get('passed', False),
                'score': stage.get('score', 0),
                'execution_time_ms': stage.get('executionTime', 0)
            })
    
    # Convert to DataFrame
    stage_df = pd.DataFrame(stage_data)
    
    if stage_df.empty:
        logger.warning("No stage data found")
        return
        
    # Calculate stage effectiveness
    stage_effectiveness = stage_df.groupby('stage_id').agg({
        'passed': 'mean',  # Pass rate
        'score': 'mean',   # Average score
        'execution_time_ms': 'mean',  # Average execution time
    }).reset_index()
    
    stage_effectiveness['passed'] = stage_effectiveness['passed'] * 100  # Convert to percentage
    
    # Save to CSV
    output_file = os.path.join(output_dir, 'validation_stage_effectiveness.csv')
    stage_effectiveness.to_csv(output_file, index=False)
    logger.info(f"Saved validation stage effectiveness to {output_file}")
    
    # Calculate validation sequence efficiency
    # First, check if the required columns exist
    required_cols = ['model_id', 'hardware_profile', 'metrics.execution_time_ms', 'metrics.memory_usage_mb', 'validation_result.isValid']
    missing_cols = [col for col in required_cols if col not in validation_df.columns]
    
    if missing_cols:
        logger.warning(f"Missing required columns for sequence efficiency analysis: {missing_cols}")
        return
    
    sequence_efficiency = validation_df.groupby(['model_id', 'hardware_profile']).agg({
        'metrics.execution_time_ms': 'mean',
        'metrics.memory_usage_mb': 'mean',
        'validation_result.isValid': 'mean'  # Validation success rate
    }).reset_index()
    
    sequence_efficiency.rename(columns={
        'metrics.execution_time_ms': 'execution_time_ms',
        'metrics.memory_usage_mb': 'memory_usage_mb',
        'validation_result.isValid': 'validation_success_rate'
    }, inplace=True)
    
    sequence_efficiency['validation_success_rate'] = sequence_efficiency['validation_success_rate'] * 100  # Convert to percentage
    
    # Save to CSV
    output_file = os.path.join(output_dir, 'validation_sequence_efficiency.csv')
    sequence_efficiency.to_csv(output_file, index=False)
    logger.info(f"Saved validation sequence efficiency to {output_file}")

def analyze_hardware_performance(df: pd.DataFrame, output_dir: str, logger: logging.Logger) -> None:
    """
    Analyze hardware performance across different profiles.
    
    Args:
        df: DataFrame with results
        output_dir: Directory to save processed results
        logger: Logger instance
    """
    # Check if required columns exist
    required_cols = ['hardware_profile', 'model_id', 'metrics.execution_time_ms', 'metrics.memory_usage_mb']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        logger.warning(f"Missing required columns for hardware performance analysis: {missing_cols}")
        return
        
    # Group by hardware profile and model
    hardware_df = df.groupby(['hardware_profile', 'model_id']).agg({
        'metrics.execution_time_ms': ['mean', 'std'],
        'metrics.memory_usage_mb': ['mean', 'max']
    }).reset_index()
    
    # Flatten the column names
    hardware_df.columns = [
        '_'.join(col).strip('_') for col in hardware_df.columns.values
    ]
    
    # Calculate tokens per second (if available)
    if 'output_length' in df.columns and 'metrics.execution_time_ms' in df.columns:
        # Group again to get tokens_per_second
        tokens_df = df.copy()
        tokens_df['tokens_per_second'] = tokens_df['output_length'] / (tokens_df['metrics.execution_time_ms'] / 1000)
        
        tokens_summary = tokens_df.groupby(['hardware_profile', 'model_id']).agg({
            'tokens_per_second': ['mean', 'std']
        }).reset_index()
        
        tokens_summary.columns = [
            '_'.join(col).strip('_') for col in tokens_summary.columns.values
        ]
        
        # Merge with hardware_df
        hardware_df = pd.merge(
            hardware_df, 
            tokens_summary, 
            on=['hardware_profile', 'model_id'],
            how='left'
        )
    
    # Save to CSV
    output_file = os.path.join(output_dir, 'hardware_performance.csv')
    hardware_df.to_csv(output_file, index=False)
    logger.info(f"Saved hardware performance data to {output_file}")

def analyze_neural_symbolic_effectiveness(df: pd.DataFrame, output_dir: str, logger: logging.Logger) -> None:
    """
    Analyze the effectiveness of neural-symbolic validation.
    
    Args:
        df: DataFrame with results
        output_dir: Directory to save processed results
        logger: Logger instance
    """
    # Filter for neural symbolic validation test suite
    neural_df = df[df['test_suite_id'] == 'neural_symbolic_validation'].copy()
    
    if neural_df.empty:
        logger.warning("No neural-symbolic validation results found")
        return
        
    logger.info(f"Analyzing {len(neural_df)} neural-symbolic validation results")
    
    # Extract template information
    neural_df['template_type'] = neural_df['template_id'].fillna('unknown')
    
    # Create effectiveness metrics
    effectiveness_df = neural_df.groupby(['template_type', 'model_id']).agg({
        'validation_result.isValid': 'mean',  # Safety compliance rate
        'validation_result.score': 'mean',    # Educational quality
        'metrics.execution_time_ms': 'mean'   # Performance
    }).reset_index()
    
    effectiveness_df.rename(columns={
        'validation_result.isValid': 'safety_compliance_rate',
        'validation_result.score': 'educational_quality',
        'metrics.execution_time_ms': 'execution_time_ms'
    }, inplace=True)
    
    effectiveness_df['safety_compliance_rate'] = effectiveness_df['safety_compliance_rate'] * 100  # Convert to percentage
    
    # Save to CSV
    output_file = os.path.join(output_dir, 'neural_symbolic_effectiveness.csv')
    effectiveness_df.to_csv(output_file, index=False)
    logger.info(f"Saved neural-symbolic effectiveness data to {output_file}")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='EdgePrompt Results Analyzer'
    )
    
    parser.add_argument(
        '--data-dir',
        type=str,
        default='../data/raw',
        help='Directory containing raw results (default: ../data/raw)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='../data/processed',
        help='Directory for saving processed results (default: ../data/processed)'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the analyzer"""
    args = parse_args()
    
    # Set up logging
    logger = setup_logging(args.log_level)
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    logger.info(f"Starting analysis of results from {args.data_dir}")
    
    # Load results
    results_df = load_results(args.data_dir, logger)
    
    if results_df.empty:
        logger.error("No results to analyze")
        return 1
        
    # Perform analyses
    analyze_multi_stage_validation(results_df, args.output_dir, logger)
    analyze_hardware_performance(results_df, args.output_dir, logger)
    analyze_neural_symbolic_effectiveness(results_df, args.output_dir, logger)
    
    logger.info(f"Analysis complete. Processed data saved to {args.output_dir}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 