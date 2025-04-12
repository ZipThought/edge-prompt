"""
RunnerCore - Main entry point for EdgePrompt experiment execution.

This module implements the central orchestration class that coordinates
all aspects of experiment execution based on the algorithms specified
in the EdgePrompt methodology.
"""

import logging
from typing import Dict, List, Optional, Any
import os
import json
import time

from .config_loader import ConfigLoader
from .model_manager import ModelManager
from .template_engine import TemplateEngine
from .environment_manager import EnvironmentManager
from .test_executor import TestExecutor
from .metrics_collector import MetricsCollector
from .evaluation_engine import EvaluationEngine
from .result_logger import ResultLogger

class RunnerCore:
    """
    Primary orchestration class for EdgePrompt experiments.
    
    This class coordinates the entire experiment pipeline:
    1. Loading test suite configurations
    2. Preparing hardware simulation environments
    3. Initializing models
    4. Processing templates
    5. Executing tests
    6. Collecting metrics
    7. Evaluating results
    8. Logging data for analysis
    """
    
    def __init__(self, config_path: str, output_dir: str, log_level: str = "INFO",
                lm_studio_url: Optional[str] = None, mock_models: bool = False,
                anthropic_api_key: Optional[str] = None):
        """
        Initialize the RunnerCore with configuration.
        
        Args:
            config_path: Path to the test suite configuration
            output_dir: Directory for storing results
            log_level: Logging verbosity level
            lm_studio_url: Base URL for LM Studio server (e.g., http://localhost:1234)
            mock_models: Whether to use mock models instead of real LLMs
            anthropic_api_key: API key for Anthropic Claude (for evaluation proxy)
        """
        self.logger = self._setup_logging(log_level)
        self.logger.info(f"Initializing RunnerCore with config: {config_path}")
        
        self.config_path = config_path
        self.output_dir = output_dir
        self.mock_models = mock_models
        
        # Log configuration
        if lm_studio_url:
            self.logger.info(f"Using LM Studio at: {lm_studio_url}")
        if mock_models:
            self.logger.info("Running with mock models (simulation mode)")
        if anthropic_api_key:
            self.logger.info("Anthropic API key provided for evaluation proxy")
        
        # Initialize component managers
        self.config_loader = ConfigLoader(config_path)
        self.model_manager = ModelManager(lm_studio_url=lm_studio_url)
        self.template_engine = TemplateEngine()
        self.environment_manager = EnvironmentManager()
        self.test_executor = TestExecutor(lm_studio_url=lm_studio_url)
        self.metrics_collector = MetricsCollector()
        self.evaluation_engine = EvaluationEngine(anthropic_api_key=anthropic_api_key)
        self.result_logger = ResultLogger(output_dir)
        
        # Create timestamp for this run
        self.timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        
        self.logger.info("RunnerCore initialization complete")
    
    def _setup_logging(self, log_level: str) -> logging.Logger:
        """Configure logging for the runner"""
        logger = logging.getLogger("edgeprompt.runner")
        log_level_dict = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
        }
        logger.setLevel(log_level_dict.get(log_level, logging.INFO))
        
        # Add console handler if not already present
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def run_test_suite(self) -> Dict[str, Any]:
        """
        Execute the complete test suite as defined in configuration.
        
        Returns:
            Dict containing aggregated test results
        """
        self.logger.info("Starting test suite execution")
        
        # 1. Load test suite configuration
        test_suite = self.config_loader.load_test_suite()
        self.logger.info(f"Loaded test suite: {test_suite.get('test_suite_id', 'unknown')}")
        
        # 2. Prepare all resources
        test_results = []
        
        # 3. For each test case in test suite
        for test_case in test_suite.get('test_cases', []):
            self.logger.info(f"Running test case: {test_case.get('id', 'unknown')}")
            
            try:
                # a. Load appropriate template
                template = self.template_engine.load_template(
                    test_suite['templates'][0]  # First template for now
                )
                
                # b. Configure hardware simulation environment
                for hardware_profile in test_suite.get('hardware_profiles', []):
                    self.logger.info(f"Using hardware profile: {hardware_profile}")
                    self.environment_manager.configure_environment(hardware_profile)
                    
                    # c. Initialize models with configuration
                    for model_id in test_suite.get('models', []):
                        self.logger.info(f"Initializing model: {model_id}")
                        model = self.model_manager.initialize_model(model_id)
                        
                        # d. Process template with test case variables
                        processed_template = self.template_engine.process_template(
                            template, test_case.get('variables', {})
                        )
                        
                        # e. Start metrics collection
                        self.metrics_collector.start_collection()
                        
                        # f. Execute edge LLM with processed template
                        generation_result = self.test_executor.execute_test(
                            model, processed_template
                        )
                        
                        # g. If validation test - execute validation
                        if 'validation' in test_suite.get('test_suite_id', ''):
                            # Create a lambda to call the test executor as required by validate_result
                            edge_llm_func = lambda prompt, params: self.test_executor.execute_test(
                                model, prompt, params
                            )
                            
                            validation_result = self.evaluation_engine.validate_result(
                                test_case.get('question', ''),
                                generation_result.get('output', ''),  # Pass just the output text, not the whole result
                                test_suite.get('validation_sequence', []),
                                edge_llm_func  # Pass the lambda function as the callback
                            )
                            self.logger.info(f"Validation result: {validation_result.get('isValid')}")
                        else:
                            validation_result = None
                            
                        # h. Stop metrics collection
                        metrics = self.metrics_collector.stop_collection()
                        
                        # i. Record results
                        result = {
                            "id": f"{test_case.get('id', 'unknown')}_{model_id}_{hardware_profile}",
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "test_case_id": test_case.get('id', 'unknown'),
                            "model_id": model_id,
                            "hardware_profile": hardware_profile,
                            "generation_result": generation_result,
                            "validation_result": validation_result,
                            "metrics": metrics
                        }
                        test_results.append(result)
                        
                        # Log the result
                        self.result_logger.log_result(result)
                        
                        # j. Reset the environment for the next run
                        self.environment_manager.reset_environment()
                        
            except Exception as e:
                self.logger.error(f"Error executing test case {test_case.get('id', 'unknown')}: {str(e)}")
        
        self.logger.info(f"Test suite execution complete with {len(test_results)} results")
        
        # 4. Analyze results
        analysis = {
            "test_suite_id": test_suite.get('test_suite_id', 'unknown'),
            "total_tests": len(test_results),
            "successful_tests": sum(1 for r in test_results if r.get("validation_result", {}).get("isValid", False)),
            "metrics_summary": self._calculate_metrics_summary(test_results),
            "raw_results": test_results
        }
        
        return analysis
    
    def _calculate_metrics_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """Calculate summary statistics from test results"""
        # Simple summary for now
        summary = {}
        if not results:
            return summary
            
        # Average execution time
        try:
            summary["avg_execution_time_ms"] = sum(
                r.get("metrics", {}).get("execution_time_ms", 0) 
                for r in results
            ) / len(results)
            
            # Average memory usage
            summary["avg_memory_usage_mb"] = sum(
                r.get("metrics", {}).get("memory_usage_mb", 0) 
                for r in results
            ) / len(results)
            
            # By model performance
            models = set(r.get("model_id") for r in results)
            summary["by_model"] = {}
            for model in models:
                model_results = [r for r in results if r.get("model_id") == model]
                summary["by_model"][model] = {
                    "count": len(model_results),
                    "avg_execution_time_ms": sum(
                        r.get("metrics", {}).get("execution_time_ms", 0) 
                        for r in model_results
                    ) / len(model_results) if model_results else 0,
                }
        except Exception as e:
            self.logger.error(f"Error calculating metrics summary: {str(e)}")
            
        return summary 