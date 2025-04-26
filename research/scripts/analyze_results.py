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
                                        if part in ['multi_stage_validation', 'neural_symbolic_validation', 'resource_optimization', 'four_run_comparison']:
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

def analyze_four_run_comparison(df: pd.DataFrame, output_dir: str, logger: logging.Logger) -> None:
    """
    Analyze Four-Run Comparison results (CloudLLM vs EdgeLLM with SingleTurn_Direct vs MultiTurn_EdgePrompt).

    Loads detailed run data, extracts metrics for all four runs,
    calculates aggregate statistics (rates, averages), and saves
    both detailed and aggregated comparison data to CSV files suitable
    for the render_figures.py script.
    
    Args:
        df: DataFrame containing raw results (expecting nested run data).
        output_dir: Directory to save processed CSV results.
        logger: Logger instance.
    """
    logger.info("Starting Four-Run Comparison Analysis...")

    # Ensure output directory exists
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create output directory {output_dir}: {e}")
        return # Cannot proceed without output directory

    # Filter DataFrame for relevant rows (containing all runs)
    # Check if run data is nested or already flattened
    if 'run_1.status' in df.columns and 'run_3.status' in df.columns and 'run_4.status' in df.columns:
        # Data seems already normalized/flattened
        four_run_df = df.copy()
        logger.debug(f"Found {len(four_run_df)} rows with flattened run data.")
    elif 'run_1' in df.columns and 'run_3' in df.columns and 'run_4' in df.columns:
         # Data needs normalization from nested dicts
         try:
             # Check if columns contain dicts or potentially JSON strings
             if isinstance(df['run_1'].iloc[0], str):
                  df['run_1'] = df['run_1'].apply(lambda x: json.loads(x) if isinstance(x, str) else x)
             if isinstance(df['run_3'].iloc[0], str):
                  df['run_3'] = df['run_3'].apply(lambda x: json.loads(x) if isinstance(x, str) else x)
             if isinstance(df['run_4'].iloc[0], str):
                  df['run_4'] = df['run_4'].apply(lambda x: json.loads(x) if isinstance(x, str) else x)

             # Normalize nested data
             four_run_df = pd.json_normalize(df.to_dict('records'), sep='.')
             logger.debug(f"Normalized nested run data. Resulting columns: {four_run_df.columns.tolist()}")
         except Exception as e:
             logger.error(f"Error normalizing nested run data: {e}", exc_info=True)
             return
    else:
         logger.warning("Could not find 'run_1', 'run_3' and 'run_4' columns/data for analysis. Skipping.")
         return

    if four_run_df.empty:
        logger.warning("No four-run comparison results found after filtering/normalization. Skipping.")
        return
        
    logger.info(f"Processing {len(four_run_df)} four-run comparison results entries.")
    
    # --- Extract Key Metrics Per Run --- 
    # Initialize list to store extracted data for each run
    detailed_comparison_records = []

    for _, row in four_run_df.iterrows():
        record = {
            # Identifiers
            'run_id': row.get('id', 'unknown'),
            'test_case_id': row.get('test_case_id', 'unknown'),
            'cloud_llm_model_id': row.get('cloud_llm_model_id', 'unknown'),
            'edge_llm_model_id': row.get('edge_llm_model_id', 'unknown'),
            'hardware_profile': row.get('hardware_profile', 'unknown')
        }

        # --- Run 4 Metrics (EdgePrompt) --- 
        # Safety (derived from constraints)
        run4_constraint_violations = row.get('run_4.steps.constraint_enforcement.violations', [])
        # Ensure violations is a list before processing
        if not isinstance(run4_constraint_violations, list):
             run4_constraint_violations = [] 
        record['safety_violation_run4'] = int(any("prohibited keyword" in str(v).lower() for v in run4_constraint_violations))
        # Constraint Adherence
        record['constraint_passed_run4'] = int(row.get('run_4.steps.constraint_enforcement.passed', False))
        # Validation
        record['validation_passed_run4'] = int(row.get('run_4.final_decision.passed_validation', False))
        record['validation_score_run4'] = pd.to_numeric(row.get('run_4.final_decision.final_score'), errors='coerce')
        # Performance
        record['total_tokens_run4'] = pd.to_numeric(row.get('run_4.total_metrics.total_tokens'), errors='coerce')
        record['latency_ms_run4'] = pd.to_numeric(row.get('run_4.total_metrics.latency_ms'), errors='coerce')
        # Output for quality comparison
        record['output_run4'] = row.get('run_4.output', '')

        # --- Run 3 Metrics (Edge Baseline) ---
        # Safety (derived from constraints)
        run3_constraint_violations = row.get('run_3.steps.constraint_enforcement.violations', [])
        if not isinstance(run3_constraint_violations, list):
             run3_constraint_violations = []
        record['safety_violation_run3'] = int(any("prohibited keyword" in str(v).lower() for v in run3_constraint_violations))
        # Constraint Adherence
        record['constraint_passed_run3'] = int(row.get('run_3.steps.constraint_enforcement.passed', False))
        # Baseline Evaluation (use this for Run 3's pass/score)
        record['evaluation_passed_run3'] = int(row.get('run_3.final_decision.passed_evaluation', False))
        record['evaluation_score_run3'] = pd.to_numeric(row.get('run_3.final_decision.final_score'), errors='coerce')
        # Performance
        record['total_tokens_run3'] = pd.to_numeric(row.get('run_3.total_metrics.total_tokens'), errors='coerce')
        record['latency_ms_run3'] = pd.to_numeric(row.get('run_3.total_metrics.latency_ms'), errors='coerce')
        # Output for quality comparison
        record['output_run3'] = row.get('run_3.output', '')
        
        # --- Run 1 Metrics (Cloud Reference) ---
        # Reference Data
        record['total_tokens_run1'] = pd.to_numeric(row.get('run_1.total_metrics.total_tokens'), errors='coerce')
        record['latency_ms_run1'] = pd.to_numeric(row.get('run_1.total_metrics.latency_ms'), errors='coerce')
        record['output_run1'] = row.get('run_1.output', '')
        
        # --- Run 2 Metrics (Cloud EdgePrompt) ---
        # Just include basic metrics for potential future use
        record['total_tokens_run2'] = pd.to_numeric(row.get('run_2.total_metrics.total_tokens'), errors='coerce')
        record['latency_ms_run2'] = pd.to_numeric(row.get('run_2.total_metrics.latency_ms'), errors='coerce')
        record['output_run2'] = row.get('run_2.output', '')

        detailed_comparison_records.append(record)

    if not detailed_comparison_records:
        logger.warning("No detailed comparison records generated. Cannot proceed with aggregation.")
        return
    
    # --- Create Detailed DataFrame --- 
    detailed_df = pd.DataFrame(detailed_comparison_records)
    
    # Handle potential NaN values resulting from coerce errors or missing data
    numeric_cols = [
        'safety_violation_run4', 'constraint_passed_run4', 'validation_passed_run4', 'validation_score_run4', 'total_tokens_run4', 'latency_ms_run4',
        'safety_violation_run3', 'constraint_passed_run3', 'evaluation_passed_run3', 'evaluation_score_run3', 'total_tokens_run3', 'latency_ms_run3',
        'total_tokens_run1', 'latency_ms_run1', 'total_tokens_run2', 'latency_ms_run2'
    ]
    for col in numeric_cols:
        if col in detailed_df.columns:
            detailed_df[col] = detailed_df[col].fillna(0)

    # Save detailed results
    detailed_file = os.path.join(output_dir, 'four_run_comparison_detailed.csv')
    detailed_df.to_csv(detailed_file, index=False)
    logger.info(f"Saved detailed four-run comparison results to {detailed_file}")

    # --- Aggregate Results for Visualization --- 
    # Group by relevant factors (cloud_llm_model_id, edge_llm_model_id, hardware_profile)
    grouping_factors = ['cloud_llm_model_id', 'edge_llm_model_id', 'hardware_profile']
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

    # Safety Comparison (Violation Rate - Run 4 vs Run 3)
    try:
        safety_df = agg_df[valid_grouping_factors].copy()
        # Calculate rates using sum / count
        safety_df['safety_violation_rate_run4'] = (agg_df['safety_violation_run4_sum'] / agg_df['count']) * 100
        safety_df['safety_violation_rate_run3'] = (agg_df['safety_violation_run3_sum'] / agg_df['count']) * 100
        safety_df['safety_rate_difference_run4_vs_run3'] = safety_df['safety_violation_rate_run4'] - safety_df['safety_violation_rate_run3']
        safety_file = os.path.join(output_dir, 'edgeprompt_vs_baseline_safety.csv')
        safety_df.to_csv(safety_file, index=False, float_format='%.2f')
        logger.info(f"Saved safety comparison results to {safety_file}")
    except KeyError as e:
        logger.warning(f"Could not generate edgeprompt_vs_baseline_safety.csv. Missing column: {e}")
    except Exception as e:
        logger.error(f"Error generating edgeprompt_vs_baseline_safety.csv: {e}", exc_info=True)


    # Constraint Adherence Comparison (Pass Rate - Run 4 vs Run 3)
    try:
        constraint_df = agg_df[valid_grouping_factors].copy()
         # Calculate rates using sum / count
        constraint_df['constraint_pass_rate_run4'] = (agg_df['constraint_passed_run4_sum'] / agg_df['count']) * 100
        # Note: Run 3 uses 'evaluation_passed_run3' as its primary pass metric per extraction logic
        constraint_df['constraint_pass_rate_run3'] = (agg_df['evaluation_passed_run3_sum'] / agg_df['count']) * 100 
        constraint_df['constraint_rate_difference_run4_vs_run3'] = constraint_df['constraint_pass_rate_run4'] - constraint_df['constraint_pass_rate_run3']
        constraint_file = os.path.join(output_dir, 'edgeprompt_vs_baseline_constraint.csv')
        constraint_df.to_csv(constraint_file, index=False, float_format='%.2f')
        logger.info(f"Saved constraint comparison results to {constraint_file}")
    except KeyError as e:
        logger.warning(f"Could not generate edgeprompt_vs_baseline_constraint.csv. Missing column: {e}")
    except Exception as e:
        logger.error(f"Error generating edgeprompt_vs_baseline_constraint.csv: {e}", exc_info=True)

    # Token Usage Comparison (Efficiency - Run 4 vs Run 3)
    try:
        token_df = agg_df[valid_grouping_factors].copy()
        token_df['avg_tokens_run4'] = agg_df['total_tokens_run4_mean']
        token_df['avg_tokens_run3'] = agg_df['total_tokens_run3_mean']
        token_df['token_ratio_run4_vs_run3'] = token_df['avg_tokens_run4'] / token_df['avg_tokens_run3']
        token_df['token_difference_run4_vs_run3'] = token_df['avg_tokens_run4'] - token_df['avg_tokens_run3']
        
        # Add reference data (Run 1)
        token_df['avg_tokens_run1'] = agg_df['total_tokens_run1_mean']
        token_df['token_ratio_run3_vs_run1'] = token_df['avg_tokens_run3'] / token_df['avg_tokens_run1']
        token_df['token_ratio_run4_vs_run1'] = token_df['avg_tokens_run4'] / token_df['avg_tokens_run1']
        
        token_file = os.path.join(output_dir, 'edgeprompt_vs_baseline_token_usage.csv')
        token_df.to_csv(token_file, index=False, float_format='%.2f')
        logger.info(f"Saved token usage comparison results to {token_file}")
    except KeyError as e:
        logger.warning(f"Could not generate edgeprompt_vs_baseline_token_usage.csv. Missing column: {e}")
    except Exception as e:
        logger.error(f"Error generating edgeprompt_vs_baseline_token_usage.csv: {e}", exc_info=True)

    # Latency Comparison (Run 4 vs Run 3)
    try:
        latency_df = agg_df[valid_grouping_factors].copy()
        latency_df['avg_latency_run4'] = agg_df['latency_ms_run4_mean']
        latency_df['avg_latency_run3'] = agg_df['latency_ms_run3_mean']
        latency_df['latency_ratio_run4_vs_run3'] = latency_df['avg_latency_run4'] / latency_df['avg_latency_run3']
        latency_df['latency_difference_run4_vs_run3'] = latency_df['avg_latency_run4'] - latency_df['avg_latency_run3']
        
        # Add reference data (Run 1)
        latency_df['avg_latency_run1'] = agg_df['latency_ms_run1_mean']
        latency_df['latency_ratio_run3_vs_run1'] = latency_df['avg_latency_run3'] / latency_df['avg_latency_run1']
        latency_df['latency_ratio_run4_vs_run1'] = latency_df['avg_latency_run4'] / latency_df['avg_latency_run1']
        
        latency_file = os.path.join(output_dir, 'edgeprompt_vs_baseline_latency.csv')
        latency_df.to_csv(latency_file, index=False, float_format='%.2f')
        logger.info(f"Saved latency comparison results to {latency_file}")
    except KeyError as e:
        logger.warning(f"Could not generate edgeprompt_vs_baseline_latency.csv. Missing column: {e}")
    except Exception as e:
        logger.error(f"Error generating edgeprompt_vs_baseline_latency.csv: {e}", exc_info=True)
    
    # Quality Comparison (Placeholder for agreement score)
    # This would be implemented with a proper agreement score calculation
    try:
        quality_df = agg_df[valid_grouping_factors].copy()
        # Extract outputs for potential quality metrics calculation
        # Currently just placing the output columns for external processing
        
        # Implement a basic text similarity measure for demonstration
        # In a real implementation, this would use a proper NLP-based similarity metric like Kappa, BLEU, etc.
        def basic_similarity(a, b):
            if not a or not b:
                return 0
            words_a = set(str(a).lower().split())
            words_b = set(str(b).lower().split())
            if not words_a or not words_b:
                return 0
            intersection = words_a.intersection(words_b)
            union = words_a.union(words_b)
            return len(intersection) / len(union) if union else 0
        
        # Calculate similarity scores between outputs
        output_run1 = detailed_df['output_run1'].tolist()
        output_run3 = detailed_df['output_run3'].tolist()
        output_run4 = detailed_df['output_run4'].tolist()
        
        # Calculate average similarity for each group
        # This is just a placeholder - actual implementation would be more sophisticated
        quality_by_group = {}
        for idx, group in enumerate(detailed_df.groupby(valid_grouping_factors).groups):
            group_indices = detailed_df.groupby(valid_grouping_factors).groups[group]
            run3_vs_run1_scores = []
            run4_vs_run1_scores = []
            
            for i in group_indices:
                run3_vs_run1 = basic_similarity(output_run3[i], output_run1[i])
                run4_vs_run1 = basic_similarity(output_run4[i], output_run1[i])
                run3_vs_run1_scores.append(run3_vs_run1)
                run4_vs_run1_scores.append(run4_vs_run1)
            
            quality_by_group[group] = {
                'agreement_score_run3_vs_ref': sum(run3_vs_run1_scores) / len(run3_vs_run1_scores) if run3_vs_run1_scores else 0,
                'agreement_score_run4_vs_ref': sum(run4_vs_run1_scores) / len(run4_vs_run1_scores) if run4_vs_run1_scores else 0
            }
        
        # Create dataframe from quality scores
        quality_data = []
        for group, scores in quality_by_group.items():
            if isinstance(group, tuple):
                row = dict(zip(valid_grouping_factors, group))
            else:
                row = {valid_grouping_factors[0]: group}
            row.update(scores)
            row['agreement_diff_run4_vs_run3'] = row['agreement_score_run4_vs_ref'] - row['agreement_score_run3_vs_ref']
            quality_data.append(row)
        
        quality_df = pd.DataFrame(quality_data)
        
        quality_file = os.path.join(output_dir, 'quality_vs_reference.csv')
        quality_df.to_csv(quality_file, index=False, float_format='%.4f')
        logger.info(f"Saved quality comparison results to {quality_file}")
    except Exception as e:
        logger.error(f"Error generating quality_vs_reference.csv: {e}", exc_info=True)
    
    # Save aggregated results (all metrics) 
    aggregated_file = os.path.join(output_dir, 'four_run_comparison_aggregated.csv')
    agg_df.to_csv(aggregated_file, index=False)
    logger.info(f"Saved aggregated four-run comparison results to {aggregated_file}")

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
        choices=['all', 'four_run_comparison', 'multi_stage', 'resource'],
        default='four_run_comparison',
        help='Type of analysis to perform (default: four_run_comparison for Phase 1)'
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
    if args.analysis_type == 'all' or args.analysis_type == 'four_run_comparison':
        analyze_four_run_comparison(df, args.output_dir, logger)
        
    if args.analysis_type == 'all' or args.analysis_type == 'multi_stage':
        analyze_multi_stage_validation(df, args.output_dir, logger)
        
    if args.analysis_type == 'all' or args.analysis_type == 'resource':
        analyze_resource_optimization(df, args.output_dir, logger)

    logger.info("Analysis finished.")

if __name__ == '__main__':
    main()