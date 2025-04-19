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

def analyze_scenario_comparison(df: pd.DataFrame, output_dir: str, logger: logging.Logger) -> None:
    """
    Analyze Phase 1 Scenario comparison results (e.g., A/B testing).

    Loads detailed run data, extracts metrics for Scenario A and B,
    calculates aggregate statistics (rates, averages), and saves
    both detailed and aggregated comparison data to CSV files suitable
    for the render_figures.py script.
    
    Args:
        df: DataFrame containing raw results (expecting nested scenario data).
        output_dir: Directory to save processed CSV results.
        logger: Logger instance.
    """
    logger.info("Starting A/B Comparison Analysis (Phase 1)...")

    # Ensure output directory exists
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create output directory {output_dir}: {e}")
        return # Cannot proceed without output directory

    # Filter DataFrame for relevant rows (containing both scenarios)
    # Check if scenario data is nested or already flattened
    if 'scenario_A.status' in df.columns and 'scenario_B.status' in df.columns:
        # Data seems already normalized/flattened
        ab_df = df.copy()
        logger.debug(f"Found {len(ab_df)} rows with flattened scenario data.")
    elif 'scenario_A' in df.columns and 'scenario_B' in df.columns:
         # Data needs normalization from nested dicts
         try:
             # Check if columns contain dicts or potentially JSON strings
             if isinstance(df['scenario_A'].iloc[0], str):
                  df['scenario_A'] = df['scenario_A'].apply(lambda x: json.loads(x) if isinstance(x, str) else x)
             if isinstance(df['scenario_B'].iloc[0], str):
                  df['scenario_B'] = df['scenario_B'].apply(lambda x: json.loads(x) if isinstance(x, str) else x)

             # Normalize nested data
             ab_df = pd.json_normalize(df.to_dict('records'), sep='.')
             logger.debug(f"Normalized nested scenario data. Resulting columns: {ab_df.columns.tolist()}")
         except Exception as e:
             logger.error(f"Error normalizing nested scenario data: {e}", exc_info=True)
             return
    else:
         logger.warning("Could not find 'scenario_A' and 'scenario_B' columns/data for A/B analysis. Skipping.")
         return

    if ab_df.empty:
        logger.warning("No A/B comparison results found after filtering/normalization. Skipping.")
        return
        
    logger.info(f"Processing {len(ab_df)} A/B comparison results entries.")

    # Check for variant_id column or add default if missing
    if 'variant_id' not in ab_df.columns:
        logger.info("No 'variant_id' column found. Adding default 'standard' variant ID.")
        ab_df['variant_id'] = 'standard'
    
    # Get unique variants
    variants = ab_df['variant_id'].unique()
    logger.info(f"Found {len(variants)} Scenario A variants: {variants}")

    # --- Extract Key Metrics Per Run --- 
    # Initialize list to store extracted data for each run
    detailed_comparison_records = []

    for _, row in ab_df.iterrows():
        record = {
            # Identifiers
            'run_id': row.get('id', 'unknown'),
            'test_case_id': row.get('test_case_id', 'unknown'),
            'llm_l_model_id': row.get('llm_l_model_id', 'unknown'),
            'llm_s_model_id': row.get('llm_s_model_id', 'unknown'),
            'hardware_profile': row.get('hardware_profile', 'unknown'),
            'variant_id': row.get('variant_id', 'standard')
        }

        # --- Scenario A Metrics --- 
        # Safety (derived from constraints)
        a_constraint_violations = row.get('scenario_A.steps.constraint_enforcement.violations', [])
        # Ensure violations is a list before processing
        if not isinstance(a_constraint_violations, list):
             a_constraint_violations = [] 
        record['safety_violation_A'] = int(any("prohibited keyword" in str(v).lower() for v in a_constraint_violations))
        # Constraint Adherence
        record['constraint_passed_A'] = int(row.get('scenario_A.steps.constraint_enforcement.passed', False))
        # Validation
        record['validation_passed_A'] = int(row.get('scenario_A.final_decision.passed_validation', False))
        record['validation_score_A'] = pd.to_numeric(row.get('scenario_A.final_decision.final_score'), errors='coerce')
        # Performance
        record['total_tokens_A'] = pd.to_numeric(row.get('scenario_A.total_metrics.total_tokens'), errors='coerce')
        record['latency_ms_A'] = pd.to_numeric(row.get('scenario_A.total_metrics.latency_ms'), errors='coerce')

        # --- Scenario B Metrics ---
        # Safety (derived from constraints)
        b_constraint_violations = row.get('scenario_B.steps.constraint_enforcement.violations', [])
        if not isinstance(b_constraint_violations, list):
             b_constraint_violations = []
        record['safety_violation_B'] = int(any("prohibited keyword" in str(v).lower() for v in b_constraint_violations))
        # Constraint Adherence
        record['constraint_passed_B'] = int(row.get('scenario_B.steps.constraint_enforcement.passed', False))
        # Baseline Evaluation (use this for B's pass/score)
        record['evaluation_passed_B'] = int(row.get('scenario_B.final_decision.passed_evaluation', False))
        record['evaluation_score_B'] = pd.to_numeric(row.get('scenario_B.final_decision.final_score'), errors='coerce')
        # Performance
        record['total_tokens_B'] = pd.to_numeric(row.get('scenario_B.total_metrics.total_tokens'), errors='coerce')
        record['latency_ms_B'] = pd.to_numeric(row.get('scenario_B.total_metrics.latency_ms'), errors='coerce')

        detailed_comparison_records.append(record)

    if not detailed_comparison_records:
        logger.warning("No detailed comparison records generated. Cannot proceed with aggregation.")
        return
    
    # --- Create Detailed DataFrame --- 
    detailed_df = pd.DataFrame(detailed_comparison_records)
    # Handle potential NaN values resulting from coerce errors or missing data
    numeric_cols = ['safety_violation_A', 'constraint_passed_A', 'validation_passed_A', 'validation_score_A', 'total_tokens_A', 'latency_ms_A',
                    'safety_violation_B', 'constraint_passed_B', 'evaluation_passed_B', 'evaluation_score_B', 'total_tokens_B', 'latency_ms_B']
    for col in numeric_cols:
        if col in detailed_df.columns:
            detailed_df[col] = detailed_df[col].fillna(0)

    # Save detailed results
    detailed_file = os.path.join(output_dir, 'ab_comparison_detailed.csv')
    detailed_df.to_csv(detailed_file, index=False)
    logger.info(f"Saved detailed A/B comparison results to {detailed_file}")

    # --- Aggregate Results for Visualization --- 
    # Group by relevant factors (e.g., llm_s_model, hardware_profile, variant_id)
    grouping_factors = ['llm_s_model_id', 'hardware_profile', 'variant_id']
    # Check if factors exist
    valid_grouping_factors = [f for f in grouping_factors if f in detailed_df.columns]
    if not valid_grouping_factors:
        logger.warning("Cannot group results: Missing grouping columns. Aggregating overall.")
        # Aggregate overall if grouping factors are missing
        agg_df = detailed_df[numeric_cols].agg(['mean', 'sum', 'count']).T # Added sum for counts
        # Need to restructure agg_df slightly if aggregated overall
        agg_df_mean = detailed_df[numeric_cols].mean().to_frame('mean')
        agg_df_sum = detailed_df[numeric_cols].sum().to_frame('sum')
        agg_df_count = pd.Series({'count': len(detailed_df)})
        agg_df = pd.concat([agg_df_mean, agg_df_sum], axis=1).T
        agg_df['overall_group'] = 'Overall' # Add a dummy grouping column
        agg_df = agg_df.reset_index().rename(columns={'index': 'metric'}) 
        # This overall aggregation might need adjustment depending on how specific metrics are calculated below
        # For simplicity, we'll focus on the grouped aggregation first. Need to rethink the overall case.
        logger.error("Overall aggregation case not fully implemented for specific comparison CSVs. Please ensure grouping factors exist.")
        return # Exit if grouping factors are missing, as the logic below depends on them.
        
    else:
        logger.info(f"Aggregating results by: {valid_grouping_factors}")
        # Calculate both mean and sum for rate calculations, count comes along
        agg_funcs = {col: ['mean', 'sum'] for col in numeric_cols}
        agg_df = detailed_df.groupby(valid_grouping_factors).agg(agg_funcs)
        agg_df.columns = ['_'.join(col).strip() for col in agg_df.columns.values] # Flatten MultiIndex
        agg_df['count'] = detailed_df.groupby(valid_grouping_factors).size() # Add count separately
        agg_df = agg_df.reset_index()


    if agg_df.empty:
        logger.warning("Aggregation resulted in an empty DataFrame. Skipping aggregated CSV output.")
        return
        
    # --- Calculate Comparative Metrics and Save Specific CSVs ---
    
    # Make sure count is present for rate calculations
    if 'count' not in agg_df.columns:
         logger.error("Aggregation failed to produce a 'count' column. Cannot calculate rates.")
         return

    # Safety Comparison (Violation Rate)
    try:
        safety_df = agg_df[valid_grouping_factors].copy()
        # Calculate rates using sum / count
        safety_df['safety_violation_rate_A'] = (agg_df['safety_violation_A_sum'] / agg_df['count']) * 100
        safety_df['safety_violation_rate_B'] = (agg_df['safety_violation_B_sum'] / agg_df['count']) * 100
        safety_df['safety_rate_difference'] = safety_df['safety_violation_rate_A'] - safety_df['safety_violation_rate_B']
        safety_file = os.path.join(output_dir, 'safety_comparison.csv')
        safety_df.to_csv(safety_file, index=False, float_format='%.2f')
        logger.info(f"Saved safety comparison results to {safety_file}")
    except KeyError as e:
        logger.warning(f"Could not generate safety_comparison.csv. Missing column: {e}")
    except Exception as e:
        logger.error(f"Error generating safety_comparison.csv: {e}", exc_info=True)


    # Constraint Adherence Comparison (Pass Rate)
    try:
        constraint_df = agg_df[valid_grouping_factors].copy()
         # Calculate rates using sum / count
        constraint_df['constraint_pass_rate_A'] = (agg_df['constraint_passed_A_sum'] / agg_df['count']) * 100
        # Note: Scenario B uses 'evaluation_passed_B' as its primary pass metric per extraction logic
        constraint_df['constraint_pass_rate_B'] = (agg_df['evaluation_passed_B_sum'] / agg_df['count']) * 100 
        constraint_df['constraint_rate_difference'] = constraint_df['constraint_pass_rate_A'] - constraint_df['constraint_pass_rate_B']
        constraint_file = os.path.join(output_dir, 'constraint_comparison.csv')
        constraint_df.to_csv(constraint_file, index=False, float_format='%.2f')
        logger.info(f"Saved constraint comparison results to {constraint_file}")
    except KeyError as e:
        logger.warning(f"Could not generate constraint_comparison.csv. Missing column: {e}")
    except Exception as e:
        logger.error(f"Error generating constraint_comparison.csv: {e}", exc_info=True)

    # Token Usage Comparison (Relative Efficiency)
    try:
        token_df = agg_df[valid_grouping_factors].copy()
        token_df['avg_tokens_A'] = agg_df['total_tokens_A_mean']
        token_df['avg_tokens_B'] = agg_df['total_tokens_B_mean']
        token_df['token_usage_ratio'] = token_df['avg_tokens_A'] / token_df['avg_tokens_B']
        token_df['token_difference'] = token_df['avg_tokens_A'] - token_df['avg_tokens_B']
        token_file = os.path.join(output_dir, 'token_usage_comparison.csv')
        token_df.to_csv(token_file, index=False, float_format='%.2f')
        logger.info(f"Saved token usage comparison results to {token_file}")
    except KeyError as e:
        logger.warning(f"Could not generate token_usage_comparison.csv. Missing column: {e}")
    except Exception as e:
        logger.error(f"Error generating token_usage_comparison.csv: {e}", exc_info=True)

    # Latency Comparison 
    try:
        latency_df = agg_df[valid_grouping_factors].copy()
        latency_df['avg_latency_A'] = agg_df['latency_ms_A_mean']
        latency_df['avg_latency_B'] = agg_df['latency_ms_B_mean']
        latency_df['latency_ratio'] = latency_df['avg_latency_A'] / latency_df['avg_latency_B']
        latency_df['latency_difference'] = latency_df['avg_latency_A'] - latency_df['avg_latency_B']
        latency_file = os.path.join(output_dir, 'latency_comparison.csv')
        latency_df.to_csv(latency_file, index=False, float_format='%.2f')
        logger.info(f"Saved latency comparison results to {latency_file}")
    except KeyError as e:
        logger.warning(f"Could not generate latency_comparison.csv. Missing column: {e}")
    except Exception as e:
        logger.error(f"Error generating latency_comparison.csv: {e}", exc_info=True)
        
    # Save aggregated results (all metrics) 
    aggregated_file = os.path.join(output_dir, 'ab_comparison_aggregated.csv')
    agg_df.to_csv(aggregated_file, index=False)
    logger.info(f"Saved aggregated A/B comparison results to {aggregated_file}")
    
    # Generate variant comparison summary
    try:
        variant_df = agg_df.groupby(['variant_id']).agg({
            'safety_violation_A_mean': 'mean',
            'safety_violation_B_mean': 'mean',
            'constraint_passed_A_mean': 'mean',
            'constraint_passed_B_mean': 'mean',
            'validation_passed_A_mean': 'mean',
            'evaluation_passed_B_mean': 'mean',
            'validation_score_A_mean': 'mean',
            'evaluation_score_B_mean': 'mean',
            'total_tokens_A_mean': 'mean',
            'total_tokens_B_mean': 'mean',
            'latency_ms_A_mean': 'mean',
            'latency_ms_B_mean': 'mean',
            'count': 'sum'
        }).reset_index()
        
        variant_df['token_usage_ratio'] = variant_df['total_tokens_A_mean'] / variant_df['total_tokens_B_mean']
        variant_df['latency_ratio'] = variant_df['latency_ms_A_mean'] / variant_df['latency_ms_B_mean']
        variant_df['validation_score_diff'] = variant_df['validation_score_A_mean'] - variant_df['evaluation_score_B_mean']
        
        variant_file = os.path.join(output_dir, 'variant_comparison.csv')
        variant_df.to_csv(variant_file, index=False, float_format='%.4f')
        logger.info(f"Saved variant comparison summary to {variant_file}")
    except Exception as e:
        logger.error(f"Error generating variant_comparison.csv: {e}", exc_info=True)

# Placeholder for other analysis functions (Phase 2 or specific tests)
def analyze_multi_stage_validation(df: pd.DataFrame, output_dir: str, logger: logging.Logger) -> None:
    logger.info("Multi-stage validation analysis not implemented for Phase 1 focus.")
    pass

def analyze_resource_optimization(df: pd.DataFrame, output_dir: str, logger: logging.Logger) -> None:
    logger.info("Resource optimization analysis not implemented for Phase 1 focus.")
    pass

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='EdgePrompt Results Analyzer'
    )
    
    parser.add_argument(
        '--data-dir',
        type=str,
        default='../data/raw',
        help='Directory containing raw results data (JSONL or JSON files)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='../data/processed',
        help='Directory for saving processed data (CSV files)'
    )
    
    parser.add_argument(
        '--analysis-type',
        type=str,
        choices=['all', 'ab_comparison', 'multi_stage', 'resource'],
        default='ab_comparison',
        help='Type of analysis to perform (default: ab_comparison for Phase 1)'
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
    
    # Load results
    df = load_results(args.data_dir, logger)
    
    if df.empty:
        logger.error("No results data loaded. Exiting analysis.")
        sys.exit(1)
    
    # Perform requested analysis
    if args.analysis_type == 'all' or args.analysis_type == 'ab_comparison':
        analyze_scenario_comparison(df, args.output_dir, logger)
        
    if args.analysis_type == 'all' or args.analysis_type == 'multi_stage':
        analyze_multi_stage_validation(df, args.output_dir, logger)
        
    if args.analysis_type == 'all' or args.analysis_type == 'resource':
        analyze_resource_optimization(df, args.output_dir, logger)

    logger.info("Analysis finished.")

if __name__ == '__main__':
    main() 