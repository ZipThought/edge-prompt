#!/usr/bin/env python3
"""
EdgePrompt Figure Generator

This script creates publication-ready figures from the processed data,
suitable for inclusion in the EdgePrompt paper.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Third-party imports
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Use non-interactive backend (doesn't require display)
matplotlib.use('Agg')

# Add parent directory to path to enable imports (if utils are needed later)
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Set up publication-quality figure settings
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.titlesize'] = 16

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure logging for the figure generator"""
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
    logger = logging.getLogger('edgeprompt.figures')
    return logger

def render_edgeprompt_vs_baseline_safety(data_dir: str, output_dir: str, logger: logging.Logger) -> None:
    """
    Render Figure: Safety Effectiveness Comparison (EdgeLLM EdgePrompt vs EdgeLLM Baseline).
    
    Args:
        data_dir: Directory containing processed data
        output_dir: Directory to save figures
        logger: Logger instance
    """
    input_file = os.path.join(data_dir, 'edgeprompt_vs_baseline_safety.csv')
    
    if not os.path.exists(input_file):
        logger.warning(f"Safety comparison data not found: {input_file}. Skipping figure generation.")
        return
        
    try:
        df = pd.read_csv(input_file)
        if df.empty:
            logger.warning(f"No safety comparison data available in {input_file}. Skipping figure.")
            return
    except Exception as e:
         logger.error(f"Failed to load or process {input_file}: {e}", exc_info=True)
         return
        
    logger.info("Rendering Figure: Safety Effectiveness Comparison (EdgePrompt vs. Edge Baseline)...")
    
    # Check required columns
    id_vars = [col for col in ["hardware_profile", "edge_llm_model_id"] if col in df.columns]
    value_vars = [col for col in ["safety_violation_rate_run4", "safety_violation_rate_run3"] if col in df.columns]
    if not id_vars or len(value_vars) != 2:
        logger.error(f"Missing required columns in {input_file} for safety comparison plot. Need grouping ({id_vars}) and value ({value_vars}) columns.")
        return

    # Set up the figure
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Reshape data for grouped bar chart
    try:
        melted_df = pd.melt(
            df, 
            id_vars=id_vars,
            value_vars=value_vars,
            var_name="scenario", 
            value_name="violation_rate"
        )
    except Exception as e:
         logger.error(f"Error melting dataframe for plotting: {e}", exc_info=True)
         plt.close(fig)
         return

    # Replace scenario names for better labels
    melted_df["scenario"] = melted_df["scenario"].replace({
        "safety_violation_rate_run4": "EdgePrompt (Run 4)",
        "safety_violation_rate_run3": "Edge Baseline (Run 3)"
    })
    
    # Determine grouping variable for x-axis
    x_group = "edge_llm_model_id" if "edge_llm_model_id" in id_vars else id_vars[0]
    
    # Create grouped bar chart
    try:
        sns.barplot(
            x=x_group, 
            y="violation_rate",
            hue="scenario", 
            data=melted_df,
            ax=ax,
            palette="viridis" # Use a visually distinct palette
        )
    except Exception as e:
         logger.error(f"Error creating barplot: {e}", exc_info=True)
         plt.close(fig)
         return
    
    # Add labels and title
    ax.set_xlabel("EdgeLLM Model")
    ax.set_ylabel("Safety Violation Rate (%)")
    ax.set_title("Safety Effectiveness: EdgeLLM EdgePrompt vs. EdgeLLM Baseline")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%')) # Format y-axis as percentage
    
    # Add value labels on bars
    try:
        for container in ax.containers:
            ax.bar_label(container, fmt='%.1f%%', padding=3)
    except Exception as e:
         logger.warning(f"Could not add bar labels: {e}") # Non-critical error
    
    # Add gridlines
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    ax.legend(title='Method')
    plt.xticks(rotation=45, ha="right") # Rotate labels if they overlap
    
    # Adjust layout and save
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'Figure_Paper_EdgePrompt_vs_Baseline_Safety.png')
    try:
        plt.savefig(output_file)
        logger.info(f"Saved safety comparison figure to {output_file}")
    except Exception as e:
         logger.error(f"Failed to save figure {output_file}: {e}")
    finally:
        plt.close(fig) # Ensure figure is closed

def render_edgeprompt_vs_baseline_constraint(data_dir: str, output_dir: str, logger: logging.Logger) -> None:
    """
    Render Figure: Constraint Adherence Comparison (EdgeLLM EdgePrompt vs EdgeLLM Baseline).
    
    Args:
        data_dir: Directory containing processed data
        output_dir: Directory to save figures
        logger: Logger instance
    """
    input_file = os.path.join(data_dir, 'edgeprompt_vs_baseline_constraint.csv')
    
    if not os.path.exists(input_file):
        logger.warning(f"Constraint comparison data not found: {input_file}. Skipping figure generation.")
        return
        
    try:
        df = pd.read_csv(input_file)
        if df.empty:
            logger.warning(f"No constraint comparison data available in {input_file}. Skipping figure.")
            return
    except Exception as e:
         logger.error(f"Failed to load or process {input_file}: {e}", exc_info=True)
         return
        
    logger.info("Rendering Figure: Constraint Adherence Comparison (EdgePrompt vs. Edge Baseline)...")
    
    # Check required columns
    id_vars = [col for col in ["hardware_profile", "edge_llm_model_id"] if col in df.columns]
    value_vars = [col for col in ["constraint_pass_rate_run4", "constraint_pass_rate_run3"] if col in df.columns]
    if not id_vars or len(value_vars) != 2:
        logger.error(f"Missing required columns in {input_file} for constraint comparison plot. Need grouping ({id_vars}) and value ({value_vars}) columns.")
        return

    # Set up the figure
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Reshape data for grouped bar chart
    try:
        melted_df = pd.melt(
            df, 
            id_vars=id_vars,
            value_vars=value_vars,
            var_name="scenario", 
            value_name="adherence_rate"
        )
    except Exception as e:
         logger.error(f"Error melting dataframe for plotting: {e}", exc_info=True)
         plt.close(fig)
         return

    # Replace scenario names for better labels
    melted_df["scenario"] = melted_df["scenario"].replace({
        "constraint_pass_rate_run4": "EdgePrompt (Run 4)",
        "constraint_pass_rate_run3": "Edge Baseline (Run 3)"
    })
    
    # Determine grouping variable for x-axis
    x_group = "edge_llm_model_id" if "edge_llm_model_id" in id_vars else id_vars[0]

    # Create grouped bar chart
    try:
        sns.barplot(
            x=x_group, 
            y="adherence_rate",
            hue="scenario", 
            data=melted_df,
            ax=ax,
            palette="viridis"
        )
    except Exception as e:
         logger.error(f"Error creating barplot: {e}", exc_info=True)
         plt.close(fig)
         return

    # Add labels and title
    ax.set_xlabel("EdgeLLM Model")
    ax.set_ylabel("Constraint Adherence Rate (%)")
    ax.set_title("Constraint Adherence: EdgeLLM EdgePrompt vs. EdgeLLM Baseline")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%')) # Format y-axis as percentage

    # Add value labels on bars
    try:
        for container in ax.containers:
            ax.bar_label(container, fmt='%.1f%%', padding=3)
    except Exception as e:
         logger.warning(f"Could not add bar labels: {e}")

    # Add gridlines
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    ax.legend(title='Method')
    plt.xticks(rotation=45, ha="right")

    # Adjust layout and save
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'Figure_Paper_EdgePrompt_vs_Baseline_Constraints.png')
    try:
        plt.savefig(output_file)
        logger.info(f"Saved constraint adherence comparison figure to {output_file}")
    except Exception as e:
         logger.error(f"Failed to save figure {output_file}: {e}")
    finally:
        plt.close(fig)

def render_quality_vs_reference(data_dir: str, output_dir: str, logger: logging.Logger) -> None:
    """
    Render Figure: Quality Comparison vs Reference (CloudLLM).
    
    Args:
        data_dir: Directory containing processed data
        output_dir: Directory to save figures
        logger: Logger instance
    """
    input_file = os.path.join(data_dir, 'quality_vs_reference.csv')
    
    if not os.path.exists(input_file):
        logger.warning(f"Quality comparison data not found: {input_file}. Skipping figure generation.")
        return
        
    try:
        df = pd.read_csv(input_file)
        if df.empty:
            logger.warning(f"No quality comparison data available in {input_file}. Skipping figure.")
            return
    except Exception as e:
         logger.error(f"Failed to load or process {input_file}: {e}", exc_info=True)
         return
        
    logger.info("Rendering Figure: Quality vs Reference Comparison...")
    
    # Check required columns
    id_vars = [col for col in ["hardware_profile", "edge_llm_model_id"] if col in df.columns]
    value_vars = [col for col in ["agreement_score_run3_vs_ref", "agreement_score_run4_vs_ref"] if col in df.columns]
    if not id_vars or len(value_vars) != 2:
        logger.error(f"Missing required columns in {input_file} for quality comparison plot. Need grouping ({id_vars}) and value ({value_vars}) columns.")
        return

    # Set up the figure
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Reshape data for grouped bar chart
    try:
        melted_df = pd.melt(
            df, 
            id_vars=id_vars,
            value_vars=value_vars,
            var_name="method", 
            value_name="agreement_score"
        )
    except Exception as e:
         logger.error(f"Error melting dataframe for plotting: {e}", exc_info=True)
         plt.close(fig)
         return

    # Replace scenario names for better labels
    melted_df["method"] = melted_df["method"].replace({
        "agreement_score_run4_vs_ref": "EdgePrompt (Run 4)",
        "agreement_score_run3_vs_ref": "Edge Baseline (Run 3)"
    })
    
    # Determine grouping variable for x-axis
    x_group = "edge_llm_model_id" if "edge_llm_model_id" in id_vars else id_vars[0]

    # Create grouped bar chart
    try:
        sns.barplot(
            x=x_group, 
            y="agreement_score",
            hue="method", 
            data=melted_df,
            ax=ax,
            palette="viridis"
        )
    except Exception as e:
         logger.error(f"Error creating barplot: {e}", exc_info=True)
         plt.close(fig)
         return

    # Add labels and title
    ax.set_xlabel("EdgeLLM Model")
    ax.set_ylabel("Agreement Score with CloudLLM Reference")
    ax.set_title("Quality vs Reference: EdgeLLM Methods Compared to CloudLLM")

    # Add value labels on bars
    try:
        for container in ax.containers:
            ax.bar_label(container, fmt='%.3f', padding=3)
    except Exception as e:
         logger.warning(f"Could not add bar labels: {e}")

    # Add gridlines
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    ax.legend(title='Method')
    plt.xticks(rotation=45, ha="right")

    # Adjust layout and save
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'Figure_Paper_Quality_vs_Reference.png')
    try:
        plt.savefig(output_file)
        logger.info(f"Saved quality comparison figure to {output_file}")
    except Exception as e:
         logger.error(f"Failed to save figure {output_file}: {e}")
    finally:
        plt.close(fig)

def create_edgeprompt_vs_baseline_token_table(data_dir: str, output_dir: str, logger: logging.Logger) -> None:
    """
    Create Table: Token Usage Comparison (EdgeLLM EdgePrompt vs EdgeLLM Baseline).
    
    Args:
        data_dir: Directory containing processed data
        output_dir: Directory to save tables
        logger: Logger instance
    """
    input_file = os.path.join(data_dir, 'edgeprompt_vs_baseline_token_usage.csv')
    
    if not os.path.exists(input_file):
        logger.warning(f"Token comparison data not found: {input_file}. Skipping table generation.")
        return
        
    try:
        df = pd.read_csv(input_file)
        if df.empty:
            logger.warning(f"No token comparison data available in {input_file}. Skipping table.")
            return
    except Exception as e:
         logger.error(f"Failed to load or process {input_file}: {e}", exc_info=True)
         return
        
    logger.info("Creating Table: Token Usage Comparison (EdgePrompt vs. Edge Baseline)...")
    
    # Select and rename columns for the table
    table_cols = {
        'edge_llm_model_id': 'EdgeLLM Model',
        'hardware_profile': 'Hardware Profile',
        'avg_tokens_run4': 'EdgePrompt Tokens (Avg)',
        'avg_tokens_run3': 'Edge Baseline Tokens (Avg)',
        'token_difference_run4_vs_run3': 'Token Difference (R4-R3)',
        'token_ratio_run4_vs_run3': 'Token Ratio (R4/R3)',
        'avg_tokens_run1': 'CloudLLM Ref Tokens (Avg)',
        'token_ratio_run4_vs_run1': 'EdgePrompt vs Ref Ratio (R4/R1)'
    }
    # Ensure columns exist before selecting/renaming
    cols_to_select = [col for col in table_cols.keys() if col in df.columns]
    if len(cols_to_select) < 4: # At least need model, run3, run4 tokens
         logger.error(f"Missing essential columns in {input_file} for token table. Found: {df.columns.tolist()}")
         return

    table_df = df[cols_to_select].rename(columns=table_cols)
    
    # Format numeric columns
    token_cols = ['EdgePrompt Tokens (Avg)', 'Edge Baseline Tokens (Avg)', 'Token Difference (R4-R3)', 'CloudLLM Ref Tokens (Avg)']
    for col in token_cols:
         if col in table_df.columns:
              table_df[col] = table_df[col].round(0).astype(int)
    
    ratio_cols = ['Token Ratio (R4/R3)', 'EdgePrompt vs Ref Ratio (R4/R1)']
    for col in ratio_cols:
         if col in table_df.columns:
             table_df[col] = table_df[col].round(2)
    
    # Save as CSV
    output_file = os.path.join(output_dir, 'Table_Paper_EdgePrompt_vs_Baseline_TokenCompare.csv')
    try:
        table_df.to_csv(output_file, index=False)
        logger.info(f"Saved token usage comparison table to {output_file}")
    except Exception as e:
         logger.error(f"Failed to save table {output_file}: {e}")

def create_edgeprompt_vs_baseline_latency_table(data_dir: str, output_dir: str, logger: logging.Logger) -> None:
    """
    Create Table: Latency Comparison (EdgeLLM EdgePrompt vs EdgeLLM Baseline).
    
    Args:
        data_dir: Directory containing processed data
        output_dir: Directory to save tables
        logger: Logger instance
    """
    input_file = os.path.join(data_dir, 'edgeprompt_vs_baseline_latency.csv')
    
    if not os.path.exists(input_file):
        logger.warning(f"Latency comparison data not found: {input_file}. Skipping table generation.")
        return
        
    try:
        df = pd.read_csv(input_file)
        if df.empty:
            logger.warning(f"No latency comparison data available in {input_file}. Skipping table.")
            return
    except Exception as e:
         logger.error(f"Failed to load or process {input_file}: {e}", exc_info=True)
         return
        
    logger.info("Creating Table: Latency Comparison (EdgePrompt vs. Edge Baseline)...")
    
    # Select and rename columns for the table
    table_cols = {
        'edge_llm_model_id': 'EdgeLLM Model',
        'hardware_profile': 'Hardware Profile',
        'avg_latency_run4': 'EdgePrompt Latency (ms)',
        'avg_latency_run3': 'Edge Baseline Latency (ms)',
        'latency_difference_run4_vs_run3': 'Latency Difference (ms R4-R3)',
        'latency_ratio_run4_vs_run3': 'Latency Ratio (R4/R3)',
        'avg_latency_run1': 'CloudLLM Ref Latency (ms)',
        'latency_ratio_run4_vs_run1': 'EdgePrompt vs Ref Ratio (R4/R1)'
    }
    cols_to_select = [col for col in table_cols.keys() if col in df.columns]
    if len(cols_to_select) < 4: # At least need model, run3, run4 latency
         logger.error(f"Missing essential columns in {input_file} for latency table. Found: {df.columns.tolist()}")
         return

    table_df = df[cols_to_select].rename(columns=table_cols)

    # Format numeric columns
    latency_cols = ['EdgePrompt Latency (ms)', 'Edge Baseline Latency (ms)', 'Latency Difference (ms R4-R3)', 'CloudLLM Ref Latency (ms)']
    for col in latency_cols:
        if col in table_df.columns:
            table_df[col] = table_df[col].round(1)
    
    ratio_cols = ['Latency Ratio (R4/R3)', 'EdgePrompt vs Ref Ratio (R4/R1)']
    for col in ratio_cols:
        if col in table_df.columns:
            table_df[col] = table_df[col].round(2)
    
    # Save as CSV
    output_file = os.path.join(output_dir, 'Table_Paper_EdgePrompt_vs_Baseline_LatencyCompare.csv')
    try:
        table_df.to_csv(output_file, index=False)
        logger.info(f"Saved latency comparison table to {output_file}")
    except Exception as e:
         logger.error(f"Failed to save table {output_file}: {e}")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='EdgePrompt Figure Generator - Phase 1 Four-Run Comparisons'
    )
    
    parser.add_argument(
        '--data-dir',
        type=str,
        default='../data/processed',
        help='Directory containing processed data (CSV files from analyze_results.py)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='../figures',
        help='Directory for saving generated figures and tables'
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
    """Main entry point for the figure generator"""
    args = parse_args()
    
    # Set up logging
    logger = setup_logging(args.log_level)
    
    # Ensure output directory exists
    try:
        os.makedirs(args.output_dir, exist_ok=True)
    except OSError as e:
         logger.critical(f"Failed to create output directory {args.output_dir}: {e}")
         sys.exit(1)
         
    logger.info(f"Generating Phase 1 figures from data in: {args.data_dir}")
    logger.info(f"Saving figures/tables to: {args.output_dir}")
    
    # Call rendering functions for Phase 1 four-run comparisons
    render_edgeprompt_vs_baseline_safety(args.data_dir, args.output_dir, logger)
    render_edgeprompt_vs_baseline_constraint(args.data_dir, args.output_dir, logger)
    render_quality_vs_reference(args.data_dir, args.output_dir, logger)
    create_edgeprompt_vs_baseline_token_table(args.data_dir, args.output_dir, logger)
    create_edgeprompt_vs_baseline_latency_table(args.data_dir, args.output_dir, logger)
    
    logger.info("Figure generation complete.")

if __name__ == '__main__':
    main()