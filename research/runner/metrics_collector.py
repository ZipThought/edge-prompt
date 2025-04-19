"""
MetricsCollector - Handles collection of performance metrics.

This module provides a simplified metrics collection for Phase 1 of EdgePrompt,
focusing on latency and token usage rather than detailed hardware monitoring.
"""

import logging
import time
from typing import Dict, Any, List, Optional

class MetricsCollector:
    """
    Collects latency and token metrics during experiments.
    
    This class implements the simplified MetricsCollection algorithm from
    the EdgePrompt Phase 1 methodology, handling:
    - Timing of operations
    - Token usage tracking
    - Basic performance statistics
    """
    
    def __init__(self):
        """Initialize the MetricsCollector"""
        self.logger = logging.getLogger("edgeprompt.runner.metrics")
        self.start_time = None
        self.metrics_data = {}
        self.logger.info("MetricsCollector initialized")
    
    def start_timer(self) -> None:
        """
        Start the latency timer.
        """
        self.start_time = time.time()
        self.logger.debug("Timer started")
    
    def stop_timer(self) -> int:
        """
        Stop the timer and return elapsed milliseconds.
        
        Returns:
            Elapsed time in milliseconds
        """
        if self.start_time is None:
            self.logger.warning("Timer was not started")
            return 0
            
        end_time = time.time()
        elapsed_ms = int((end_time - self.start_time) * 1000)
        self.metrics_data['latency_ms'] = elapsed_ms
        self.logger.debug(f"Timer stopped after {elapsed_ms}ms")
        return elapsed_ms
    
    def record_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """
        Record token counts for the operation.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        self.metrics_data['input_tokens'] = input_tokens
        self.metrics_data['output_tokens'] = output_tokens
        self.metrics_data['total_tokens'] = input_tokens + output_tokens
        
        # Calculate tokens per second if we have latency data
        if 'latency_ms' in self.metrics_data and output_tokens > 0:
            tokens_per_second = output_tokens / (self.metrics_data['latency_ms'] / 1000.0)
            self.metrics_data['tokens_per_second'] = round(tokens_per_second, 2)
            
        self.logger.debug(f"Recorded {input_tokens} input tokens, {output_tokens} output tokens")
    
    def get_results(self) -> Dict[str, Any]:
        """
        Get the collected metrics.
        
        Returns:
            Dict containing collected metrics
        """
        return self.metrics_data.copy()
    
    def reset(self) -> None:
        """Reset the metrics collector for a new operation"""
        self.start_time = None
        self.metrics_data = {}
        self.logger.debug("Metrics collector reset")
    
    def merge_metrics(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple metrics dictionaries into a single summary.
        
        Args:
            metrics_list: List of metrics dictionaries to merge
            
        Returns:
            Dict containing merged metrics
        """
        if not metrics_list:
            return {}
            
        merged = {
            'latency_ms': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0
        }
        
        for metrics in metrics_list:
            merged['latency_ms'] += metrics.get('latency_ms', 0)
            merged['input_tokens'] += metrics.get('input_tokens', 0)
            merged['output_tokens'] += metrics.get('output_tokens', 0)
            merged['total_tokens'] += metrics.get('total_tokens', 0)
            
        # Calculate overall tokens per second
        if merged['latency_ms'] > 0 and merged['output_tokens'] > 0:
            merged['tokens_per_second'] = round(
                merged['output_tokens'] / (merged['latency_ms'] / 1000.0), 2
            )
            
        return merged 