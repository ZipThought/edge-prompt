"""
MetricsCollector - Handles collection of performance metrics.

This module provides functionality for collecting and analyzing
performance metrics during EdgePrompt experiments.
"""

import logging
import time
import threading
import os
from typing import Dict, Any, List, Optional

# Make psutil optional
try:
    import psutil
    HAVE_PSUTIL = True
except ImportError:
    HAVE_PSUTIL = False

class MetricsCollector:
    """
    Collects performance metrics during experiments.
    
    This class implements the MetricsCollection algorithm from the EdgePrompt
    methodology, handling:
    - Time-series data collection
    - Resource utilization monitoring (CPU, memory, etc.)
    - Performance statistics calculation
    """
    
    def __init__(self, sampling_interval_ms: int = 100):
        """
        Initialize the MetricsCollector.
        
        Args:
            sampling_interval_ms: How frequently to sample metrics (in ms)
        """
        self.logger = logging.getLogger("edgeprompt.runner.metrics")
        self.sampling_interval_ms = sampling_interval_ms
        self.collection_active = False
        self.collection_thread = None
        self.metrics_data = {
            "timestamps": [],
            "values": {
                "cpu_percent": [],
                "memory_mb": [],
                "elapsed_time_ms": []
            }
        }
        self.start_time = None
        self.logger.info(f"MetricsCollector initialized with sampling interval: {sampling_interval_ms}ms")
    
    def start_collection(self) -> None:
        """
        Start collecting metrics.
        
        Raises:
            RuntimeError: If collection is already active
        """
        if self.collection_active:
            self.logger.warning("Metrics collection already active")
            return
            
        self.logger.info("Starting metrics collection")
        
        # Reset data structures
        self.metrics_data = {
            "timestamps": [],
            "values": {
                "cpu_percent": [],
                "memory_mb": [],
                "elapsed_time_ms": []
            }
        }
        
        # Record start time
        self.start_time = time.time()
        
        # For this scaffold, we'll simulate the start
        self.collection_active = True
        
        # Start the collection thread if psutil is available
        if HAVE_PSUTIL:
            self.collection_thread = threading.Thread(
                target=self._collection_loop,
                daemon=True
            )
            self.collection_thread.start()
        
        self.logger.info("Metrics collection started")
    
    def _collection_loop(self) -> None:
        """Background thread for collecting metrics"""
        if not HAVE_PSUTIL:
            self.logger.warning("psutil not available, skipping detailed metrics collection")
            return
            
        process = psutil.Process(os.getpid())
        
        while self.collection_active:
            try:
                # Get current timestamp
                current_time = time.time()
                elapsed_ms = int((current_time - self.start_time) * 1000)
                
                # Sample metrics
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                
                # Store in time series
                self.metrics_data["timestamps"].append(current_time)
                self.metrics_data["values"]["cpu_percent"].append(cpu_percent)
                self.metrics_data["values"]["memory_mb"].append(memory_mb)
                self.metrics_data["values"]["elapsed_time_ms"].append(elapsed_ms)
                
                # Sleep until next sample
                time.sleep(self.sampling_interval_ms / 1000)
                
            except Exception as e:
                self.logger.error(f"Error collecting metrics: {str(e)}")
                time.sleep(self.sampling_interval_ms / 1000)
    
    def stop_collection(self) -> Dict[str, Any]:
        """
        Stop collecting metrics and return the results.
        
        Returns:
            Dict containing collected metrics
        """
        if not self.collection_active:
            self.logger.warning("No active metrics collection to stop")
            return {}
            
        self.logger.info("Stopping metrics collection")
        
        # Stop the collection thread
        self.collection_active = False
        if HAVE_PSUTIL and self.collection_thread and self.collection_thread.is_alive():
            self.collection_thread.join(timeout=1.0)
        
        # Calculate end time and duration
        end_time = time.time()
        duration_ms = int((end_time - self.start_time) * 1000)
        
        # Calculate summary statistics
        summary = self._calculate_summary()
        summary["execution_time_ms"] = duration_ms
        
        self.logger.info(f"Metrics collection stopped after {duration_ms}ms")
        
        return summary
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """
        Calculate summary statistics from collected metrics.
        
        Returns:
            Dict containing summary statistics
        """
        summary = {}
        
        # If no detailed metrics collected (no psutil), provide basic metrics
        if not HAVE_PSUTIL or not self.metrics_data["timestamps"]:
            summary["avg_cpu_percent"] = 0
            summary["max_cpu_percent"] = 0
            summary["avg_memory_mb"] = 0
            summary["max_memory_mb"] = 0
            summary["memory_usage_mb"] = 0
            summary["sample_count"] = 0
            return summary
            
        # CPU usage
        cpu_values = self.metrics_data["values"]["cpu_percent"]
        if cpu_values:
            summary["avg_cpu_percent"] = sum(cpu_values) / len(cpu_values)
            summary["max_cpu_percent"] = max(cpu_values)
            
        # Memory usage
        memory_values = self.metrics_data["values"]["memory_mb"]
        if memory_values:
            summary["avg_memory_mb"] = sum(memory_values) / len(memory_values)
            summary["max_memory_mb"] = max(memory_values)
            summary["memory_usage_mb"] = memory_values[-1]  # Current memory usage
            
        # Sample count
        summary["sample_count"] = len(self.metrics_data["timestamps"])
        
        return summary
    
    def get_time_series_data(self) -> Dict[str, Any]:
        """
        Get the complete time series data.
        
        Returns:
            Dict containing time series data
        """
        return self.metrics_data
    
    def get_basic_metrics(self) -> Dict[str, Any]:
        """
        Get a simplified set of metrics for quick access.
        
        Returns:
            Dict containing basic metrics
        """
        metrics = {
            "memory_mb": 0,
            "cpu_percent": 0,
            "threads": 0,
            "timestamp": time.time()
        }
        
        if HAVE_PSUTIL:
            try:
                process = psutil.Process(os.getpid())
                metrics = {
                    "memory_mb": process.memory_info().rss / (1024 * 1024),
                    "cpu_percent": process.cpu_percent(),
                    "threads": process.num_threads(),
                    "timestamp": time.time()
                }
            except Exception as e:
                self.logger.error(f"Error getting basic metrics: {str(e)}")
                
        return metrics 