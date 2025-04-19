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
    
    Implements the simplified MetricsCollection algorithm (Phase 1 Focus) from
    PROMPT_ENGINEERING.md, Sec 2.4, handling:
    - Timing of operations (latency_ms)
    - Token usage tracking (input_tokens, output_tokens, total_tokens)
    - Basic performance statistics (tokens_per_second)
    """
    
    def __init__(self):
        """Initialize the MetricsCollector"""
        self.logger = logging.getLogger("edgeprompt.runner.metrics")
        self.start_time: Optional[float] = None
        self.metrics_data: Dict[str, Any] = {}
        self.logger.info("MetricsCollector initialized")
    
    def start_timer(self) -> None:
        """
        Start the latency timer.
        """
        self.start_time = time.time()
        self.metrics_data = {}
        self.logger.debug("Timer started")
    
    def stop_timer(self) -> Optional[int]:
        """
        Stop the timer, calculate latency, and store it.
        
        Returns:
            Elapsed time in milliseconds, or None if timer wasn't started.
        """
        if self.start_time is None:
            self.logger.warning("Timer was not started before stopping.")
            self.metrics_data.pop('latency_ms', None)
            return None
            
        end_time = time.time()
        elapsed_ms = int((end_time - self.start_time) * 1000)
        self.metrics_data['latency_ms'] = elapsed_ms
        self.start_time = None
        self.logger.debug(f"Timer stopped after {elapsed_ms}ms")
        return elapsed_ms
    
    def record_tokens(self, input_tokens: Optional[int], output_tokens: Optional[int]) -> None:
        """
        Record token counts. Handles potential None values from APIs.
        
        Args:
            input_tokens: Number of input tokens (can be None).
            output_tokens: Number of output tokens (can be None).
        """
        in_tokens = input_tokens or 0
        out_tokens = output_tokens or 0

        self.metrics_data['input_tokens'] = in_tokens
        self.metrics_data['output_tokens'] = out_tokens
        self.metrics_data['total_tokens'] = in_tokens + out_tokens

        latency_ms = self.metrics_data.get('latency_ms')
        if latency_ms is not None and latency_ms > 0 and out_tokens > 0:
            try:
                tokens_per_second = out_tokens / (latency_ms / 1000.0)
                self.metrics_data['tokens_per_second'] = round(tokens_per_second, 2)
            except ZeroDivisionError:
                 self.logger.warning("Division by zero calculating tokens_per_second (latency was zero?).")
                 self.metrics_data['tokens_per_second'] = 0.0
        else:
            self.metrics_data['tokens_per_second'] = 0.0

        self.logger.debug(f"Recorded {in_tokens} input tokens, {out_tokens} output tokens")
    
    def get_results(self) -> Dict[str, Any]:
        """
        Get the collected metrics for the last timed operation.
        
        Returns:
            Dict containing collected metrics (latency_ms, tokens, etc.).
            Returns an empty dict if no metrics were recorded (e.g., timer not stopped).
        """
        final_metrics = {
            'latency_ms': self.metrics_data.get('latency_ms'),
            'input_tokens': self.metrics_data.get('input_tokens'),
            'output_tokens': self.metrics_data.get('output_tokens'),
            'total_tokens': self.metrics_data.get('total_tokens'),
            'tokens_per_second': self.metrics_data.get('tokens_per_second')
        }
        return final_metrics
    
    def reset(self) -> None:
        """Reset the metrics collector state (start time and data)."""
        self.start_time = None
        self.metrics_data = {}
        self.logger.debug("Metrics collector reset")
    
    def merge_metrics(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple metrics dictionaries into a single summary.
        Useful for aggregating metrics across multiple steps (e.g., validation stages).
        
        Args:
            metrics_list: List of metrics dictionaries to merge
            
        Returns:
            Dict containing summed metrics (latency, tokens) and recalculated avg tokens/sec.
        """
        if not metrics_list:
            return {}
            
        merged = {
            'latency_ms': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0,
            'tokens_per_second': 0.0
        }

        valid_metrics_count = 0
        for metrics in metrics_list:
            if metrics:
                merged['latency_ms'] += metrics.get('latency_ms', 0) or 0
                merged['input_tokens'] += metrics.get('input_tokens', 0) or 0
                merged['output_tokens'] += metrics.get('output_tokens', 0) or 0
                merged['total_tokens'] += metrics.get('total_tokens', 0) or 0
                valid_metrics_count += 1

        if merged['latency_ms'] > 0 and merged['output_tokens'] > 0:
            try:
                merged['tokens_per_second'] = round(
                    merged['output_tokens'] / (merged['latency_ms'] / 1000.0), 2
                )
            except ZeroDivisionError:
                 self.logger.warning("Division by zero calculating merged tokens_per_second.")
                 merged['tokens_per_second'] = 0.0

        merged['merged_steps'] = valid_metrics_count
        return merged 