#!/usr/bin/env python3
"""
EdgePrompt Figure Generator

This script creates publication-ready figures from the processed data,
suitable for inclusion in the EdgePrompt paper.
"""

import os
import sys
import logging
import argparse
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import matplotlib
# Use non-interactive backend (doesn't require display)
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Add parent directory to path to enable imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

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

def render_ab_safety_comparison(data_dir: str, output_dir: str, logger: logging.Logger) -> None:
    """
    Render Figure: Safety Effectiveness Comparison (A/B testing).
    
    Args:
        data_dir: Directory containing processed data
        output_dir: Directory to save figures
        logger: Logger instance
    """
    input_file = os.path.join(data_dir, 'safety_comparison.csv')
    
    if not os.path.exists(input_file):
        logger.warning(f"Safety comparison data not found: {input_file}")
        return
        
    # Load data
    df = pd.read_csv(input_file)
    
    if df.empty:
        logger.warning("No safety comparison data available")
        return
        
    logger.info("Rendering Figure: Safety Effectiveness Comparison (A/B testing)")
    
    # Set up the figure
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Reshape data for grouped bar chart
    melted_df = pd.melt(
        df, 
        id_vars=["hardware_profile", "llm_s_model_id"],
        value_vars=["safety_violation_A", "safety_violation_B"],
        var_name="scenario", 
        value_name="violation_rate"
    )
    
    # Replace scenario names for better labels
    melted_df["scenario"] = melted_df["scenario"].replace({
        "safety_violation_A": "EdgePrompt (A)",
        "safety_violation_B": "Baseline (B)"
    })
    
    # Create grouped bar chart
    sns.barplot(
        x="llm_s_model_id", 
        y="violation_rate",
        hue="scenario", 
        data=melted_df,
        ax=ax
    )
    
    # Add labels and title
    ax.set_xlabel("LLM-S Model")
    ax.set_ylabel("Safety Violation Rate (%)")
    ax.set_title("Safety Effectiveness: EdgePrompt vs. Baseline")
    
    # Add value labels on bars
    for container in ax.containers:
        ax.bar_label(container, fmt='%.1f%%', padding=3)
    
    # Add gridlines
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    
    # Adjust layout and save
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'Figure_Paper_SafetyCompare.png')
    plt.savefig(output_file)
    logger.info(f"Saved safety comparison figure to {output_file}")
    plt.close(fig)

def render_ab_constraint_comparison(data_dir: str, output_dir: str, logger: logging.Logger) -> None:
    """
    Render Figure: Constraint Adherence Comparison (A/B testing).
    
    Args:
        data_dir: Directory containing processed data
        output_dir: Directory to save figures
        logger: Logger instance
    """
    input_file = os.path.join(data_dir, 'constraint_comparison.csv')
    
    if not os.path.exists(input_file):
        logger.warning(f"Constraint comparison data not found: {input_file}")
        return
        
    # Load data
    df = pd.read_csv(input_file)
    
    if df.empty:
        logger.warning("No constraint comparison data available")
        return
        
    logger.info("Rendering Figure: Constraint Adherence Comparison (A/B testing)")
    
    # Set up the figure
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Reshape data for grouped bar chart
    melted_df = pd.melt(
        df, 
        id_vars=["hardware_profile", "llm_s_model_id"],
        value_vars=["constraint_adherence_A", "constraint_adherence_B"],
        var_name="scenario", 
        value_name="adherence_rate"
    )
    
    # Replace scenario names for better labels
    melted_df["scenario"] = melted_df["scenario"].replace({
        "constraint_adherence_A": "EdgePrompt (A)",
        "constraint_adherence_B": "Baseline (B)"
    })
    
    # Create grouped bar chart
    sns.barplot(
        x="llm_s_model_id", 
        y="adherence_rate",
        hue="scenario", 
        data=melted_df,
        ax=ax
    )
    
    # Add labels and title
    ax.set_xlabel("LLM-S Model")
    ax.set_ylabel("Constraint Adherence Rate (%)")
    ax.set_title("Constraint Adherence: EdgePrompt vs. Baseline")
    
    # Add value labels on bars
    for container in ax.containers:
        ax.bar_label(container, fmt='%.1f%%', padding=3)
    
    # Add gridlines
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    
    # Adjust layout and save
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'Figure_Paper_ConstraintCompare.png')
    plt.savefig(output_file)
    logger.info(f"Saved constraint adherence comparison figure to {output_file}")
    plt.close(fig)

def create_ab_token_usage_table(data_dir: str, output_dir: str, logger: logging.Logger) -> None:
    """
    Create Table: Token Usage Comparison (A/B testing).
    
    Args:
        data_dir: Directory containing processed data
        output_dir: Directory to save tables
        logger: Logger instance
    """
    input_file = os.path.join(data_dir, 'token_comparison.csv')
    
    if not os.path.exists(input_file):
        logger.warning(f"Token comparison data not found: {input_file}")
        return
        
    # Load data
    df = pd.read_csv(input_file)
    
    if df.empty:
        logger.warning("No token comparison data available")
        return
        
    logger.info("Creating Table: Token Usage Comparison (A/B testing)")
    
    # Format data for table
    table_df = df.copy()
    
    # Rename columns for clarity
    table_df.columns = [
        'Hardware Profile',
        'LLM-S Model',
        'EdgePrompt Tokens',
        'Baseline Tokens',
        'Token Difference',
        'Token Ratio (A/B)'
    ]
    
    # Format numeric columns
    table_df['EdgePrompt Tokens'] = table_df['EdgePrompt Tokens'].round(0).astype(int)
    table_df['Baseline Tokens'] = table_df['Baseline Tokens'].round(0).astype(int)
    table_df['Token Difference'] = table_df['Token Difference'].round(0).astype(int)
    table_df['Token Ratio (A/B)'] = table_df['Token Ratio (A/B)'].round(2)
    
    # Save as CSV
    output_file = os.path.join(output_dir, 'Table_Paper_TokenCompare.csv')
    table_df.to_csv(output_file, index=False)
    logger.info(f"Saved token usage comparison table to {output_file}")
    
    # Create a visual representation
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Reshape data for grouped bar chart
    melted_df = pd.melt(
        df, 
        id_vars=["hardware_profile", "llm_s_model_id"],
        value_vars=["total_tokens_A", "total_tokens_B"],
        var_name="scenario", 
        value_name="tokens"
    )
    
    # Replace scenario names for better labels
    melted_df["scenario"] = melted_df["scenario"].replace({
        "total_tokens_A": "EdgePrompt (A)",
        "total_tokens_B": "Baseline (B)"
    })
    
    # Create grouped bar chart
    sns.barplot(
        x="llm_s_model_id", 
        y="tokens",
        hue="scenario", 
        data=melted_df,
        ax=ax
    )
    
    # Add labels and title
    ax.set_xlabel("LLM-S Model")
    ax.set_ylabel("Average Token Count")
    ax.set_title("Token Usage: EdgePrompt vs. Baseline")
    
    # Add value labels on bars
    for container in ax.containers:
        ax.bar_label(container, fmt='%d', padding=3)
    
    # Add gridlines
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    
    # Adjust layout and save
    plt.tight_layout()
    vis_output_file = os.path.join(output_dir, 'Figure_TokenUsage.png')
    plt.savefig(vis_output_file)
    logger.info(f"Saved token usage visualization to {vis_output_file}")
    plt.close(fig)

def create_ab_latency_table(data_dir: str, output_dir: str, logger: logging.Logger) -> None:
    """
    Create Table: Latency Comparison (A/B testing).
    
    Args:
        data_dir: Directory containing processed data
        output_dir: Directory to save tables
        logger: Logger instance
    """
    input_file = os.path.join(data_dir, 'latency_comparison.csv')
    
    if not os.path.exists(input_file):
        logger.warning(f"Latency comparison data not found: {input_file}")
        return
        
    # Load data
    df = pd.read_csv(input_file)
    
    if df.empty:
        logger.warning("No latency comparison data available")
        return
        
    logger.info("Creating Table: Latency Comparison (A/B testing)")
    
    # Format data for table
    table_df = df.copy()
    
    # Rename columns for clarity
    table_df.columns = [
        'Hardware Profile',
        'LLM-S Model',
        'EdgePrompt Latency (ms)',
        'Baseline Latency (ms)',
        'Latency Ratio (A/B)'
    ]
    
    # Format numeric columns
    table_df['EdgePrompt Latency (ms)'] = table_df['EdgePrompt Latency (ms)'].round(0).astype(int)
    table_df['Baseline Latency (ms)'] = table_df['Baseline Latency (ms)'].round(0).astype(int)
    table_df['Latency Ratio (A/B)'] = table_df['Latency Ratio (A/B)'].round(2)
    
    # Save as CSV
    output_file = os.path.join(output_dir, 'Table_Paper_LatencyCompare.csv')
    table_df.to_csv(output_file, index=False)
    logger.info(f"Saved latency comparison table to {output_file}")
    
    # Create a visual representation
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Reshape data for grouped bar chart
    melted_df = pd.melt(
        df, 
        id_vars=["hardware_profile", "llm_s_model_id"],
        value_vars=["latency_ms_A", "latency_ms_B"],
        var_name="scenario", 
        value_name="latency_ms"
    )
    
    # Replace scenario names for better labels
    melted_df["scenario"] = melted_df["scenario"].replace({
        "latency_ms_A": "EdgePrompt (A)",
        "latency_ms_B": "Baseline (B)"
    })
    
    # Create grouped bar chart
    sns.barplot(
        x="llm_s_model_id", 
        y="latency_ms",
        hue="scenario", 
        data=melted_df,
        ax=ax
    )
    
    # Add labels and title
    ax.set_xlabel("LLM-S Model")
    ax.set_ylabel("Average Latency (ms)")
    ax.set_title("Latency: EdgePrompt vs. Baseline")
    
    # Add value labels on bars
    for container in ax.containers:
        ax.bar_label(container, fmt='%d', padding=3)
    
    # Add gridlines
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    
    # Adjust layout and save
    plt.tight_layout()
    vis_output_file = os.path.join(output_dir, 'Figure_Latency.png')
    plt.savefig(vis_output_file)
    logger.info(f"Saved latency visualization to {vis_output_file}")
    plt.close(fig)

def render_neural_symbolic_effectiveness(data_dir: str, output_dir: str, logger: logging.Logger) -> None:
    """
    Render Figure 1: Neural-Symbolic Effectiveness.
    
    Args:
        data_dir: Directory containing processed data
        output_dir: Directory to save figures
        logger: Logger instance
    """
    input_file = os.path.join(data_dir, 'neural_symbolic_effectiveness.csv')
    
    if not os.path.exists(input_file):
        logger.warning(f"Neural-symbolic effectiveness data not found: {input_file}")
        return
        
    # Load data
    df = pd.read_csv(input_file)
    
    if df.empty:
        logger.warning("No neural-symbolic effectiveness data available")
        return
        
    logger.info("Rendering Figure 1: Neural-Symbolic Effectiveness")
    
    # Set up the figure
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Set up a grouped bar chart
    df_pivoted = df.pivot(index='template_type', columns='model_id', values='safety_compliance_rate')
    df_pivoted.plot(kind='bar', ax=ax)
    
    # Add labels and title
    ax.set_xlabel('Template Type')
    ax.set_ylabel('Safety Compliance Rate (%)')
    ax.set_title('Figure 1: Neural-Symbolic Effectiveness')
    ax.set_ylim(0, 100)
    
    # Add value labels on top of bars
    for container in ax.containers:
        ax.bar_label(container, fmt='%.1f%%', padding=3)
    
    # Adjust layout and save
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'fig1_neural_symbolic_effectiveness.png')
    plt.savefig(output_file)
    logger.info(f"Saved Figure 1 to {output_file}")
    plt.close(fig)

def render_hardware_comparison(data_dir: str, output_dir: str, logger: logging.Logger) -> None:
    """
    Render Figure 2: Hardware Performance Comparison.
    
    Args:
        data_dir: Directory containing processed data
        output_dir: Directory to save figures
        logger: Logger instance
    """
    input_file = os.path.join(data_dir, 'hardware_performance.csv')
    
    if not os.path.exists(input_file):
        logger.warning(f"Hardware performance data not found: {input_file}")
        return
        
    # Load data
    df = pd.read_csv(input_file)
    
    if df.empty:
        logger.warning("No hardware performance data available")
        return
        
    logger.info("Rendering Figure 2: Hardware Performance Comparison")
    
    # Set up the figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
    
    # Prepare data for plotting
    pivot_time = df.pivot(index='hardware_profile', columns='model_id', values='metrics.execution_time_ms_mean')
    pivot_memory = df.pivot(index='hardware_profile', columns='model_id', values='metrics.memory_usage_mb_mean')
    
    # Plot execution time
    pivot_time.plot(kind='bar', ax=ax1, color=['#1f77b4', '#ff7f0e', '#2ca02c'])
    ax1.set_title('Execution Time by Hardware Profile')
    ax1.set_xlabel('Hardware Profile')
    ax1.set_ylabel('Execution Time (ms)')
    
    # Plot memory usage
    pivot_memory.plot(kind='bar', ax=ax2, color=['#1f77b4', '#ff7f0e', '#2ca02c'])
    ax2.set_title('Memory Usage by Hardware Profile')
    ax2.set_xlabel('Hardware Profile')
    ax2.set_ylabel('Memory Usage (MB)')
    
    # Add overall title
    fig.suptitle('Figure 2: Edge Device Performance Comparison', fontsize=16)
    
    # Adjust layout and save
    plt.tight_layout(rect=[0, 0, 1, 0.95])  # Make room for the suptitle
    output_file = os.path.join(output_dir, 'fig2_hardware_comparison.png')
    plt.savefig(output_file)
    logger.info(f"Saved Figure 2 to {output_file}")
    plt.close(fig)

def render_validation_performance_table(data_dir: str, output_dir: str, logger: logging.Logger) -> None:
    """
    Create Table 1: Multi-Stage Validation Performance.
    
    Args:
        data_dir: Directory containing processed data
        output_dir: Directory to save tables
        logger: Logger instance
    """
    input_file = os.path.join(data_dir, 'validation_stage_effectiveness.csv')
    
    if not os.path.exists(input_file):
        logger.warning(f"Validation stage effectiveness data not found: {input_file}")
        return
        
    # Load data
    df = pd.read_csv(input_file)
    
    if df.empty:
        logger.warning("No validation stage effectiveness data available")
        return
        
    logger.info("Creating Table 1: Multi-Stage Validation Performance")
    
    # Format the table
    table_df = df.copy()
    
    # Rename columns for clarity
    table_df.columns = [
        'Validation Stage', 
        'Pass Rate (%)', 
        'Average Score', 
        'Execution Time (ms)'
    ]
    
    # Round numeric columns
    table_df['Pass Rate (%)'] = table_df['Pass Rate (%)'].round(1)
    table_df['Average Score'] = table_df['Average Score'].round(2)
    table_df['Execution Time (ms)'] = table_df['Execution Time (ms)'].round(1)
    
    # Sort by pass rate descending
    table_df = table_df.sort_values('Pass Rate (%)', ascending=False)
    
    # Save as CSV
    output_file = os.path.join(output_dir, 'table1_validation_performance.csv')
    table_df.to_csv(output_file, index=False)
    logger.info(f"Saved Table 1 to {output_file}")
    
    # Also save as pretty HTML for easy viewing
    html_file = os.path.join(output_dir, 'table1_validation_performance.html')
    table_df.to_html(html_file, index=False, border=1, classes='dataframe')
    logger.info(f"Saved HTML version of Table 1 to {html_file}")

def render_resource_performance_tradeoff(data_dir: str, output_dir: str, logger: logging.Logger) -> None:
    """
    Render Figure 3: Resource-Performance Tradeoffs.
    
    Args:
        data_dir: Directory containing processed data
        output_dir: Directory to save figures
        logger: Logger instance
    """
    input_file = os.path.join(data_dir, 'validation_sequence_efficiency.csv')
    
    if not os.path.exists(input_file):
        logger.warning(f"Validation sequence efficiency data not found: {input_file}")
        return
        
    # Load data
    df = pd.read_csv(input_file)
    
    if df.empty:
        logger.warning("No validation sequence efficiency data available")
        return
        
    logger.info("Rendering Figure 3: Resource-Performance Tradeoffs")
    
    # Set up the figure
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Create a scatter plot
    models = df['model_id'].unique()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    for i, model in enumerate(models):
        model_data = df[df['model_id'] == model]
        ax.scatter(
            model_data['execution_time_ms'], 
            model_data['validation_success_rate'],
            s=model_data['memory_usage_mb'] / 10,  # Size proportional to memory usage
            alpha=0.7,
            color=colors[i % len(colors)],
            label=model
        )
    
    # Add labels and title
    ax.set_xlabel('Execution Time (ms)')
    ax.set_ylabel('Validation Success Rate (%)')
    ax.set_title('Figure 3: Resource-Performance Tradeoffs')
    
    # Add a legend
    ax.legend(title='Model')
    
    # Add text for each point
    for i, row in df.iterrows():
        ax.annotate(
            row['hardware_profile'],
            (row['execution_time_ms'], row['validation_success_rate']),
            xytext=(5, 5),
            textcoords='offset points',
            fontsize=8
        )
    
    # Add gridlines
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Adjust layout and save
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'fig3_resource_performance_tradeoffs.png')
    plt.savefig(output_file)
    logger.info(f"Saved Figure 3 to {output_file}")
    plt.close(fig)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='EdgePrompt Figure Generator'
    )
    
    parser.add_argument(
        '--data-dir',
        type=str,
        default='../data/processed',
        help='Directory containing processed data (default: ../data/processed)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='../figures',
        help='Directory for saving figures (default: ../figures)'
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
    os.makedirs(args.output_dir, exist_ok=True)
    
    logger.info(f"Starting figure generation from {args.data_dir}")
    
    # Generate A/B comparison figures and tables (Phase 1)
    render_ab_safety_comparison(args.data_dir, args.output_dir, logger)
    render_ab_constraint_comparison(args.data_dir, args.output_dir, logger)
    create_ab_token_usage_table(args.data_dir, args.output_dir, logger)
    create_ab_latency_table(args.data_dir, args.output_dir, logger)
    
    # Generate previous experiment figures (for backward compatibility)
    render_neural_symbolic_effectiveness(args.data_dir, args.output_dir, logger)
    render_hardware_comparison(args.data_dir, args.output_dir, logger)
    render_validation_performance_table(args.data_dir, args.output_dir, logger)
    render_resource_performance_tradeoff(args.data_dir, args.output_dir, logger)
    
    logger.info(f"Figure generation complete. Figures saved to {args.output_dir}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 