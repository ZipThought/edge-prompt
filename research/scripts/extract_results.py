#!/usr/bin/env python3
"""
EdgePrompt Results Extractor

This script extracts A/B testing results directly from the results JSON files
and prepares them for visualization.
"""

import os
import sys
import json
import logging
import argparse
import pandas as pd
import numpy as np
from datetime import datetime

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure logging for the extractor"""
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
    logger = logging.getLogger('edgeprompt.extract')
    return logger

def extract_results(results_file: str, output_dir: str, logger: logging.Logger) -> None:
    """
    Extract A/B testing results from the results JSON file.
    
    Args:
        results_file: Path to the results JSON file
        output_dir: Directory to save extracted data
        logger: Logger instance
    """
    logger.info(f"Extracting results from {results_file}")
    
    # Load results
    try:
        with open(results_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading results file: {str(e)}")
        return
    
    # Extract scenario comparison data
    scenario_comparison = data.get('scenario_comparison', {})
    if not scenario_comparison:
        logger.warning("No scenario comparison data found")
        return
    
    logger.info("Found scenario comparison data")
    
    # Extract raw results data to get hardware profile and model information
    raw_results = data.get('raw_results', [])
    if not raw_results:
        logger.warning("No raw results data found")
        return
    
    # Create model/hardware profile mapping
    model_hw_mapping = []
    for result in raw_results:
        model_hw_mapping.append({
            'hardware_profile': result.get('hardware_profile', 'unknown'),
            'llm_s_model_id': result.get('llm_s_model_id', 'unknown')
        })
    
    # Create safety comparison data
    safety_data = []
    for model_hw in model_hw_mapping:
        safety_data.append({
            'hardware_profile': model_hw['hardware_profile'],
            'llm_s_model_id': model_hw['llm_s_model_id'],
            'safety_violation_A': scenario_comparison.get('safety_violation_rate_A', 0) * 100,  # Convert to percentage
            'safety_violation_B': scenario_comparison.get('safety_violation_rate_B', 0) * 100,
            'safety_improvement': (scenario_comparison.get('safety_violation_rate_B', 0) - 
                                 scenario_comparison.get('safety_violation_rate_A', 0)) * 100
        })
    
    # Create constraint adherence data
    constraint_data = []
    for model_hw in model_hw_mapping:
        constraint_data.append({
            'hardware_profile': model_hw['hardware_profile'],
            'llm_s_model_id': model_hw['llm_s_model_id'],
            'constraint_adherence_A': scenario_comparison.get('constraint_adherence_rate_A', 0) * 100,  # Convert to percentage
            'constraint_adherence_B': scenario_comparison.get('constraint_adherence_rate_B', 0) * 100,
            'constraint_improvement': (scenario_comparison.get('constraint_adherence_rate_A', 0) - 
                                     scenario_comparison.get('constraint_adherence_rate_B', 0)) * 100
        })
    
    # Create token usage data
    token_data = []
    for model_hw in model_hw_mapping:
        token_data.append({
            'hardware_profile': model_hw['hardware_profile'],
            'llm_s_model_id': model_hw['llm_s_model_id'],
            'total_tokens_A': scenario_comparison.get('avg_total_tokens_A', 0),
            'total_tokens_B': scenario_comparison.get('avg_total_tokens_B', 0),
            'token_difference': scenario_comparison.get('avg_total_tokens_A', 0) - 
                              scenario_comparison.get('avg_total_tokens_B', 0),
            'token_ratio': scenario_comparison.get('avg_total_tokens_A', 0) / 
                         max(1, scenario_comparison.get('avg_total_tokens_B', 0))
        })
    
    # Create latency data
    latency_data = []
    for model_hw in model_hw_mapping:
        latency_data.append({
            'hardware_profile': model_hw['hardware_profile'],
            'llm_s_model_id': model_hw['llm_s_model_id'],
            'latency_ms_A': scenario_comparison.get('avg_total_latency_A', 0),
            'latency_ms_B': scenario_comparison.get('avg_total_latency_B', 0),
            'latency_ratio': scenario_comparison.get('avg_total_latency_A', 0) / 
                           max(1, scenario_comparison.get('avg_total_latency_B', 0))
        })
    
    # Save data to CSV files
    os.makedirs(output_dir, exist_ok=True)
    
    # Safety comparison
    safety_df = pd.DataFrame(safety_data)
    safety_file = os.path.join(output_dir, 'safety_comparison.csv')
    safety_df.to_csv(safety_file, index=False)
    logger.info(f"Saved safety comparison to {safety_file}")
    
    # Constraint adherence
    constraint_df = pd.DataFrame(constraint_data)
    constraint_file = os.path.join(output_dir, 'constraint_comparison.csv')
    constraint_df.to_csv(constraint_file, index=False)
    logger.info(f"Saved constraint adherence comparison to {constraint_file}")
    
    # Token usage
    token_df = pd.DataFrame(token_data)
    token_file = os.path.join(output_dir, 'token_comparison.csv')
    token_df.to_csv(token_file, index=False)
    logger.info(f"Saved token usage comparison to {token_file}")
    
    # Latency
    latency_df = pd.DataFrame(latency_data)
    latency_file = os.path.join(output_dir, 'latency_comparison.csv')
    latency_df.to_csv(latency_file, index=False)
    logger.info(f"Saved latency comparison to {latency_file}")
    
    logger.info("Extraction complete")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='EdgePrompt Results Extractor'
    )
    
    parser.add_argument(
        '--results-file',
        type=str,
        required=True,
        help='Path to the results JSON file'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='../data/processed',
        help='Directory for saving extracted data (default: ../data/processed)'
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
    """Main entry point for the extractor"""
    args = parse_args()
    
    # Set up logging
    logger = setup_logging(args.log_level)
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Extract results
    extract_results(args.results_file, args.output_dir, logger)
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 