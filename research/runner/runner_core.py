"""
RunnerCore - Main entry point for EdgePrompt experiment execution.

Implements the central orchestration class coordinating Phase 1 (Multi-LLM testing)
based on the TestOrchestrationPhase1MultiLLM_Revised algorithm specified in
PROMPT_ENGINEERING.md (Sec 2.7).
"""

import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

# Local application imports
from .config_loader import ConfigLoader
from .constraint_enforcer import ConstraintEnforcer
from .evaluation_engine import EvaluationEngine
from .metrics_collector import MetricsCollector
from .model_manager import ModelManager
from .result_logger import ResultLogger
from .template_engine import TemplateEngine


class RunnerCore:
    """
    Orchestrates EdgePrompt Phase 1 experiments with the four-run structure.

    Implements the TestOrchestrationPhase1MultiLLM_Revised algorithm (PROMPT_ENGINEERING.md, Sec 2.7).
    Coordinates component interactions (Config, Models, Templates, Metrics, Evaluation, Constraints, Logging).
    Follows SOLID principles where each component has a clear responsibility.
    """
    
    def __init__(self, config_path: str, output_dir: str, log_level: str = "INFO",
                lm_studio_url: Optional[str] = None, ollama_url: Optional[str] = None, 
                mock_models: bool = False, openai_api_key: Optional[str] = None,
                anthropic_api_key: Optional[str] = None):
        """
        Initialize the RunnerCore and all its components.

        Injects dependencies into components based on refactored signatures.
        
        Args:
            config_path: Path to the main test suite configuration file.
            output_dir: Directory for storing results and logs.
            log_level: Logging verbosity level (DEBUG, INFO, WARNING, ERROR).
            lm_studio_url: Base URL for LM Studio server (if used for EdgeLLM).
            ollama_url: Base URL for Ollama server (if used for EdgeLLM).
            mock_models: If True, use mock models instead of real LLMs.
            openai_api_key: API key for OpenAI (CloudLLM).
            anthropic_api_key: API key for Anthropic (CloudLLM and Proxy Evaluation).
        """
        self.logger = self._setup_logging(log_level)
        self.logger.info(f"Initializing RunnerCore with config: {config_path}")
        
        # Store config parameters
        self.config_path = config_path
        self.output_dir = output_dir
        self.mock_models = mock_models
        
        # Log key settings
        self.logger.info(f"Output directory: {output_dir}")
        self.logger.info(f"Log level: {log_level}")
        if lm_studio_url: self.logger.info(f"Using LM Studio URL: {lm_studio_url}")
        if ollama_url: self.logger.info(f"Using Ollama URL: {ollama_url}")
        self.logger.info(f"Mock models enabled: {mock_models}")
        if openai_api_key: self.logger.debug("OpenAI API key provided.")
        if anthropic_api_key: self.logger.debug("Anthropic API key provided.")

        # Initialize components with dependencies (DI)
        try:
            # Foundational components first
            self.config_loader = ConfigLoader(config_path)
            self.metrics_collector = MetricsCollector()
            # TemplateEngine needs ConfigLoader
            self.template_engine = TemplateEngine(self.config_loader)

            # Components requiring others
            # ModelManager needs ConfigLoader and MetricsCollector
            self.model_manager = ModelManager(
                config_loader=self.config_loader,
                metrics_collector=self.metrics_collector, # Pass collector instance
                lm_studio_url=lm_studio_url,
                ollama_url=ollama_url,
                openai_api_key=openai_api_key,
                anthropic_api_key=anthropic_api_key
            )
            # EvaluationEngine needs TemplateEngine and MetricsCollector
            self.evaluation_engine = EvaluationEngine(
                template_engine=self.template_engine, # Pass template engine
                metrics_collector=self.metrics_collector, # Pass collector instance
                anthropic_api_key=anthropic_api_key
            )
            # ConstraintEnforcer and ResultLogger have simple init
            self.constraint_enforcer = ConstraintEnforcer()
            self.result_logger = ResultLogger(output_dir)
        
        except Exception as e:
            self.logger.critical(f"Failed to initialize core components: {e}", exc_info=True)
            # Propagate error to prevent running with faulty setup
            raise RuntimeError(f"Core component initialization failed: {e}") from e

        self.logger.info("RunnerCore initialization complete.")
    
    def _setup_logging(self, log_level: str) -> logging.Logger:
        """Configure logging for the runner and its components."""
        root_logger = logging.getLogger("edgeprompt") # Get root logger for the app
        log_level_enum = getattr(logging, log_level.upper(), logging.INFO)
        root_logger.setLevel(log_level_enum)

        # Prevent duplicate handlers if called multiple times (e.g., in notebooks)
        if not root_logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            root_logger.addHandler(handler)

        # Return the specific logger for this class
        return logging.getLogger("edgeprompt.runner.core")
            
    
    def run_test_suite(self) -> Dict[str, Any]:
        """
        Executes the full test suite specified in the config file.
        Follows TestOrchestrationPhase1MultiLLM_Revised algorithm (PROMPT_ENGINEERING.md, Sec 2.7).
        
        Returns:
            Dict containing analysis summary. Raw results are saved to files.
        """
        self.logger.info("=== Starting Test Suite Execution ===")
        
        # --- Algorithm Step 1: Load Test Suite ---
        try:
            test_suite = self.config_loader.load_test_suite()
            suite_id = test_suite.get('test_suite_id', 'unknown_suite')
            self.logger.info(f"Loaded test suite: {suite_id}")
        except Exception as e:
            return self._log_and_return_error(f"Failed to load test suite from {self.config_path}", e)

        # --- Algorithm Step 2: Initialize Models ---
        # Get model IDs from the updated configuration structure
        cloud_llm_model_id = test_suite.get('models', {}).get('cloud_llm')
        edge_llm_model_ids = test_suite.get('models', {}).get('edge_llm', [])

        if not cloud_llm_model_id:
             return self._log_and_return_error("No CloudLLM model specified in test suite.")
        if not edge_llm_model_ids:
             return self._log_and_return_error("No EdgeLLM models specified in test suite.")

        # Initialize CloudLLM
        try:
             self.logger.info(f"Initializing CloudLLM model: {cloud_llm_model_id}")
             cloud_llm_model_data = self.model_manager.initialize_cloud_llm(
                 cloud_llm_model_id, mock_mode=self.mock_models
             )
        except Exception as e:
            return self._log_and_return_error(f"Failed to initialize CloudLLM model {cloud_llm_model_id}", e)

        # --- Algorithm Steps 3-14: Execute the four-run test structure ---
        test_suite_results = []
        run_counter = 0

        # Get run parameters from the updated configuration
        run_parameters = test_suite.get('run_parameters', {})
        if not run_parameters:
            return self._log_and_return_error("No run parameters defined in test suite.")
        
        self.logger.info(f"Executing four-run test structure")

        for test_case in test_suite.get('test_cases', []):
            test_case_id = test_case.get('id', f'unknown_case_{run_counter}')
            self.logger.info(f"--- Running Test Case: {test_case_id} ---")
            
            # Generate teacher request for all runs ONCE per test case
            # This ensures all runs use the same topic and constraints
            self.logger.info(f"Generating shared teacher request for test case: {test_case_id}")
            teacher_request_result = self._step_teacher_request(test_case, cloud_llm_model_data)
            if teacher_request_result.get("error"):
                self.logger.error(f"Failed to generate teacher request for test case {test_case_id}: {teacher_request_result.get('error')}")
                continue
                
            teacher_request_content = teacher_request_result.get("parsed_content")
            # Store the teacher request in the test case to be used by all runs
            test_case["shared_teacher_request"] = teacher_request_content
            
            # Log the topic for verification 
            self.logger.info(f"Topic from original test case: {test_case.get('variables', {}).get('topic')}")
            self.logger.info(f"Topic from shared teacher request: {teacher_request_content.get('topic')}")

            # Hardware profiles are conceptual labels in Phase 1
            for hardware_profile in test_suite.get('hardware_profiles', ["sim_unconstrained"]):
                 self.logger.debug(f"Using conceptual hardware profile: {hardware_profile}")

                 for edge_llm_model_id in edge_llm_model_ids:
                     self.logger.info(f"--- Using EdgeLLM model: {edge_llm_model_id} ---")
                     
                     run_counter += 1
                     # Create unique run ID including suite, case, model, profile, counter
                     run_id = f"{suite_id}_{test_case_id}_{edge_llm_model_id}_{hardware_profile}_{run_counter}"
                     run_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', run_id) # Sanitize ID

                     # Initialize EdgeLLM for this specific run configuration
                     try:
                         edge_llm_model_data = self.model_manager.initialize_edge_llm(
                             edge_llm_model_id, mock_mode=self.mock_models
                         )
                     except Exception as e:
                         self.logger.error(f"Failed to initialize EdgeLLM model {edge_llm_model_id} for run {run_id}", exc_info=True)
                         run_data = self._create_run_data_struct(run_id, test_case_id, cloud_llm_model_id, edge_llm_model_id, hardware_profile)
                         run_data["error"] = f"EdgeLLM Initialization Failed: {e}"
                         test_suite_results.append(run_data)
                         self.result_logger.log_result(run_data)
                         continue # Skip to next EdgeLLM model

                     # Prepare run data structure
                     run_data = self._create_run_data_struct(run_id, test_case_id, cloud_llm_model_id, edge_llm_model_id, hardware_profile)

                     try:
                         # --- Step 7: Generate Input Stimulus ---
                         # For simplicity, we're using the test case directly as our input stimulus
                         # In a more complex scenario, we could generate synthetic data using cloud_llm
                         input_stimulus = test_case
                         run_data["input_stimulus"] = input_stimulus

                         # --- Step 8: Initialize Results Structure ---
                         # This is already handled in _create_run_data_struct

                         # --- Step 9: Execute Run 1 (CloudLLM, SingleTurn_Direct) ---
                         self.logger.info(f"[Run {run_id}] Run 1: Executing CloudLLM with SingleTurn_Direct...")
                         run_data["run_1"] = self._run_cloud_baseline(
                             test_case, cloud_llm_model_data
                         )

                         # --- Step 10: Execute Run 2 (CloudLLM, MultiTurn_EdgePrompt) ---
                         validation_sequence_id = run_parameters.get('run_2', {}).get('validation_sequence', 'basic_validation_sequence')
                         self.logger.info(f"[Run {run_id}] Run 2: Executing CloudLLM with MultiTurn_EdgePrompt...")
                         run_data["run_2"] = self._run_cloud_edgeprompt(
                             test_case, cloud_llm_model_data, validation_sequence_id
                         )

                         # --- Step 11: Execute Run 3 (EdgeLLM, SingleTurn_Direct) ---
                         self.logger.info(f"[Run {run_id}] Run 3: Executing EdgeLLM with SingleTurn_Direct...")
                         run_data["run_3"] = self._run_edge_baseline(
                             test_case, edge_llm_model_data
                         )

                         # --- Step 12: Execute Run 4 (EdgeLLM, MultiTurn_EdgePrompt) ---
                         validation_sequence_id = run_parameters.get('run_4', {}).get('validation_sequence', 'basic_validation_sequence')
                         self.logger.info(f"[Run {run_id}] Run 4: Executing EdgeLLM with MultiTurn_EdgePrompt...")
                         run_data["run_4"] = self._run_edge_edgeprompt(
                             test_case, edge_llm_model_data, validation_sequence_id
                         )

                         # Log topic consistency verification for this run
                         self._verify_topic_consistency(run_data, test_case)

                     except Exception as e:
                         self.logger.error(f"Critical error during run execution for run {run_id}", exc_info=True)
                         run_data["error"] = f"Run Execution Failed: {e}"
                     finally:
                          # --- Step 13: Log Result ---
                          test_suite_results.append(run_data)
                          self.result_logger.log_result(run_data)
                          self.logger.info(f"[Run {run_id}] Completed and logged.")

        # --- Cleanup: Unload models (optional) ---
        self.model_manager.unload_model(cloud_llm_model_id, model_type="cloud_llm")
        for edge_llm_id in edge_llm_model_ids:
            self.model_manager.unload_model(edge_llm_id, model_type="edge_llm")

        self.logger.info(f"=== Test Suite Execution Complete. Total runs logged: {len(test_suite_results)} ===")

        # --- Step 14: Analyze Results (Basic Summary) ---
        # Detailed analysis is performed by the analyze_results.py script.
        # This provides a quick summary log.
        analysis_summary = self._create_analysis_summary(suite_id, run_counter, test_suite_results)
        self.result_logger.log_aggregate_results(test_suite_results, f"{suite_id}_raw_results")
        self.result_logger.log_aggregate_results(analysis_summary, f"{suite_id}_analysis_summary")

        return analysis_summary # Return summary, raw results are in files

    # --- Four Run Structure Methods ---

    def _run_cloud_baseline(self, test_case: Dict[str, Any], cloud_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Run 1 (Cloud Baseline):
        CloudLLM executor with SingleTurn_Direct method.
        Similar to the previous Scenario B but using CloudLLM.
        """
        run_results = {"status": "started", "steps": {}}
        all_metrics = [] # Collect metrics dict from each step

        try:
            # Step 1: Generate Simple, Unstructured Question (CloudLLM)
            question_result = self._step_generate_simple_question(test_case, cloud_llm_model_data)
            run_results["steps"]["generated_question"] = question_result
            all_metrics.append(question_result.get("metrics"))
            if question_result.get("error"): raise RuntimeError(f"Baseline Question Generation failed: {question_result['error']}")
            question_text = question_result.get("llm_output")
            if not question_text: raise ValueError("Baseline question text is empty.")

            # Create context for student answer (null teacher_request for baseline)
            context = None

            # Step 2: Simulate Student Answer (CloudLLM)
            student_answer_result = self._step_simulate_student_answer(question_text, context, test_case, cloud_llm_model_data)
            run_results["steps"]["student_answer"] = student_answer_result
            all_metrics.append(student_answer_result.get("metrics"))
            if student_answer_result.get("error"): raise RuntimeError(f"Baseline Student Answer failed: {student_answer_result['error']}")
            
            student_answer_text = student_answer_result.get("llm_output")
            if not student_answer_text: raise ValueError("Baseline student answer text is empty.")

            # Step 3: Simple Baseline Evaluation
            baseline_evaluation_result = self._step_baseline_evaluation(
                question_text, student_answer_text, test_case, cloud_llm_model_data
            )
            run_results["steps"]["baseline_evaluation"] = baseline_evaluation_result
            all_metrics.append(baseline_evaluation_result.get("metrics"))

            # Step 4: Constraint Enforcement
            constraint_result = self._step_constraint_enforcement(student_answer_text, test_case)
            run_results["steps"]["constraint_enforcement"] = constraint_result
            
            # Store output and final decision
            run_results["output"] = student_answer_text
            run_results["final_decision"] = {
                "passed_evaluation": baseline_evaluation_result.get("parsed_evaluation", {}).get("passed", False),
                "passed_constraints": constraint_result.get("passed", False),
                "final_score": baseline_evaluation_result.get("parsed_evaluation", {}).get("score", 0.0)
            }
            
            run_results["status"] = "completed"
            
        except Exception as e:
            self.logger.error(f"Error in Run 1 (Cloud Baseline) execution: {e}", exc_info=True)
            run_results["status"] = "failed"
            run_results["error"] = f"Run 1 Failed: {e}"
            
        # Aggregate metrics for entire run
        run_results["total_metrics"] = self.metrics_collector.merge_metrics([m for m in all_metrics if m])
        return run_results

    def _run_cloud_edgeprompt(self, test_case: Dict[str, Any], cloud_llm_model_data: Dict[str, Any], validation_sequence_id: str) -> Dict[str, Any]:
        """
        Execute Run 2 (Cloud EdgePrompt):
        CloudLLM executor with MultiTurn_EdgePrompt method.
        Similar to the previous Scenario A but using CloudLLM.
        """
        run_results = {"status": "started", "steps": {}}
        all_metrics = [] # Collect metrics dict from each step

        try:
            # Step 1: Use the shared Teacher Request generated earlier
            # This ensures topic consistency across all runs
            teacher_request_content = test_case.get("shared_teacher_request")
            
            # Fall back to generating a new request only if the shared one is not available
            if not teacher_request_content:
                self.logger.warning("Shared teacher request not found in test case. Generating new request.")
                teacher_request_result = self._step_teacher_request(test_case, cloud_llm_model_data)
                run_results["steps"]["teacher_request"] = teacher_request_result
                all_metrics.append(teacher_request_result.get("metrics"))
                if teacher_request_result.get("error"): raise RuntimeError(f"Teacher Request failed: {teacher_request_result['error']}")
                teacher_request_content = teacher_request_result["parsed_content"]
            else:
                # Log using shared request
                run_results["steps"]["teacher_request"] = {
                    "status": "from_shared_request",
                    "parsed_content": teacher_request_content,
                    "metrics": {
                        "latency_ms": 0,  # No latency since we're reusing
                        "input_tokens": 0,
                        "output_tokens": 0
                    }
                }

            # Step 2: Generate Question (CloudLLM)
            question_result = self._step_generate_structured_question(teacher_request_content, test_case, cloud_llm_model_data)
            run_results["steps"]["generated_question"] = question_result
            all_metrics.append(question_result.get("metrics"))
            if question_result.get("error"): raise RuntimeError(f"Generate Question failed: {question_result['error']}")
            question_text = question_result.get("llm_output")
            if not question_text: raise ValueError("Generated question text is empty.")

            # Step 3: Simulate Student Answer (CloudLLM)
            student_answer_result = self._step_simulate_student_answer(question_text, teacher_request_content, test_case, cloud_llm_model_data)
            run_results["steps"]["student_answer"] = student_answer_result
            all_metrics.append(student_answer_result.get("metrics"))
            if student_answer_result.get("error"): raise RuntimeError(f"Student Answer failed: {student_answer_result['error']}")
            
            answer_text = student_answer_result.get("llm_output")
            if not answer_text: raise ValueError("Generated answer text is empty.")

            # Step 4: Perform Multi-Stage Validation
            multi_stage_validation_result = self._step_multistage_validation(
                question_text, answer_text, teacher_request_content, cloud_llm_model_data, validation_sequence_id
            )
            
            run_results["steps"]["multi_stage_validation"] = multi_stage_validation_result
            all_metrics.append(multi_stage_validation_result.get("metrics"))
            if multi_stage_validation_result.get("error"): 
                raise RuntimeError(f"Multi-stage Validation failed: {multi_stage_validation_result['error']}")
            
            # Step 5: Constraint Enforcement
            constraint_result = self._step_constraint_enforcement(answer_text, teacher_request_content)
            run_results["steps"]["constraint_enforcement"] = constraint_result

            # Step 6: Teacher Review (if validation/constraint issues)
            if (not multi_stage_validation_result.get("isValid", True) or 
                not constraint_result.get("passed", True)):
                teacher_review_result = self._step_teacher_review(
                    multi_stage_validation_result, constraint_result, 
                    question_text, answer_text, cloud_llm_model_data
                )
                run_results["steps"]["teacher_review"] = teacher_review_result
                all_metrics.append(teacher_review_result.get("metrics"))
            else:
                run_results["steps"]["teacher_review"] = {"executed": False, "reason": "Validation and constraints passed"}
            
            # Store output and final decision
            run_results["output"] = answer_text
            run_results["final_decision"] = {
                "passed_validation": multi_stage_validation_result.get("isValid", False),
                "passed_constraints": constraint_result.get("passed", False),
                "final_score": multi_stage_validation_result.get("finalScore", 0.0),
                "feedback": multi_stage_validation_result.get("aggregateFeedback", "")
            }
            
            run_results["status"] = "completed"
            
        except Exception as e:
            self.logger.error(f"Error in Run 2 (Cloud EdgePrompt) execution: {e}", exc_info=True)
            run_results["status"] = "failed"
            run_results["error"] = f"Run 2 Failed: {e}"
            
        # Aggregate metrics for entire run
        run_results["total_metrics"] = self.metrics_collector.merge_metrics([m for m in all_metrics if m])
        
        # Add quality metrics compared to reference (Run 1)
        # Note: Detailed quality analysis is typically done by the analysis script
        # This is just a placeholder for future expansion
        run_results["quality_vs_ref"] = {
            "pending_analysis": True,
            "note": "Quality metrics vs. Run 1 reference are calculated in the analysis phase."
        }
        
        return run_results

    def _run_edge_baseline(self, test_case: Dict[str, Any], edge_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Run 3 (Edge Baseline):
        EdgeLLM executor with SingleTurn_Direct method.
        Similar to the previous Scenario B but using EdgeLLM.
        """
        run_results = {"status": "started", "steps": {}}
        all_metrics = [] # Collect metrics dict from each step

        try:
            # Step 1: Generate Simple, Unstructured Question (EdgeLLM)
            question_result = self._step_generate_simple_question_edge(test_case, edge_llm_model_data)
            run_results["steps"]["generated_question"] = question_result
            all_metrics.append(question_result.get("metrics"))
            if question_result.get("error"): raise RuntimeError(f"Baseline Question Generation failed: {question_result['error']}")
            question_text = question_result.get("generated_text")
            if not question_text: raise ValueError("Baseline question text is empty.")

            # Create context for student answer (null teacher_request for baseline)
            context = None

            # Step 2: Simulate Student Answer (EdgeLLM)
            student_answer_result = self._step_simulate_student_answer_edge(question_text, context, test_case, edge_llm_model_data)
            run_results["steps"]["student_answer"] = student_answer_result
            all_metrics.append(student_answer_result.get("metrics"))
            if student_answer_result.get("error"): raise RuntimeError(f"Baseline Student Answer failed: {student_answer_result['error']}")
            
            student_answer_text = student_answer_result.get("generated_text")
            if not student_answer_text: raise ValueError("Baseline student answer text is empty.")

            # Step 3: Simple Baseline Evaluation (EdgeLLM)
            baseline_evaluation_result = self._step_baseline_evaluation_edge(
                question_text, student_answer_text, test_case, edge_llm_model_data
            )
            run_results["steps"]["baseline_evaluation"] = baseline_evaluation_result
            all_metrics.append(baseline_evaluation_result.get("metrics"))

            # Step 4: Constraint Enforcement
            constraint_result = self._step_constraint_enforcement(student_answer_text, test_case)
            run_results["steps"]["constraint_enforcement"] = constraint_result

            # Store output and final decision
            run_results["output"] = student_answer_text
            run_results["final_decision"] = {
                "passed_evaluation": baseline_evaluation_result.get("parsed_evaluation", {}).get("passed", False),
                "passed_constraints": constraint_result.get("passed", False),
                "final_score": baseline_evaluation_result.get("parsed_evaluation", {}).get("score", 0.0)
            }
            
            run_results["status"] = "completed"
            
        except Exception as e:
            self.logger.error(f"Error in Run 3 (Edge Baseline) execution: {e}", exc_info=True)
            run_results["status"] = "failed"
            run_results["error"] = f"Run 3 Failed: {e}"
            
        # Aggregate metrics for entire run
        run_results["total_metrics"] = self.metrics_collector.merge_metrics([m for m in all_metrics if m])
        
        # Add quality metrics compared to reference (Run 1)
        # Note: Detailed quality analysis is typically done by the analysis script
        run_results["quality_vs_ref"] = {
            "pending_analysis": True,
            "note": "Quality metrics vs. Run 1 reference are calculated in the analysis phase."
        }
        
        return run_results

    def _run_edge_edgeprompt(self, test_case: Dict[str, Any], edge_llm_model_data: Dict[str, Any], validation_sequence_id: str) -> Dict[str, Any]:
        """
        Execute Run 4 (Edge EdgePrompt):
        EdgeLLM executor with MultiTurn_EdgePrompt method.
        Similar to the previous Scenario A but using EdgeLLM.
        """
        run_results = {"status": "started", "steps": {}}
        all_metrics = [] # Collect metrics dict from each step

        try:
            # Step 1: Use the shared Teacher Request generated earlier
            # This ensures topic consistency across all runs
            teacher_request_content = test_case.get("shared_teacher_request")
            
            # Fall back to previous approach if shared request is not available
            if not teacher_request_content:
                teacher_request_content = test_case.get("teacher_request_context", {})
                if not teacher_request_content:
                    teacher_request_content = {
                        "topic": test_case.get("variables", {}).get("topic", "general knowledge"),
                        "constraints": test_case.get("constraints", {}),
                        "evaluation_criteria": test_case.get("evaluation_criteria", {})
                    }
                self.logger.warning("Shared teacher request not found. Using fallback approach.")
                
            run_results["steps"]["teacher_request"] = {
                "status": "from_shared_request" if test_case.get("shared_teacher_request") else "from_test_case",
                "parsed_content": teacher_request_content
            }

            # Step 2: Generate Question (EdgeLLM)
            question_result = self._step_generate_structured_question_edge(teacher_request_content, test_case, edge_llm_model_data)
            run_results["steps"]["generated_question"] = question_result
            all_metrics.append(question_result.get("metrics"))
            if question_result.get("error"): raise RuntimeError(f"Generate Question failed: {question_result['error']}")
            question_text = question_result.get("generated_text")
            if not question_text: raise ValueError("Generated question text is empty.")

            # Step 3: Simulate Student Answer (EdgeLLM)
            student_answer_result = self._step_simulate_student_answer_edge(question_text, teacher_request_content, test_case, edge_llm_model_data)
            run_results["steps"]["student_answer"] = student_answer_result
            all_metrics.append(student_answer_result.get("metrics"))
            if student_answer_result.get("error"): raise RuntimeError(f"Student Answer failed: {student_answer_result['error']}")
            
            answer_text = student_answer_result.get("generated_text")
            if not answer_text: raise ValueError("Generated answer text is empty.")

            # Step 4: Perform Multi-Stage Validation with EdgeLLM
            multi_stage_validation_result = self._step_multistage_validation_edge(
                question_text, answer_text, teacher_request_content, edge_llm_model_data, validation_sequence_id
            )
            
            run_results["steps"]["multi_stage_validation"] = multi_stage_validation_result
            all_metrics.append(multi_stage_validation_result.get("metrics"))
            if multi_stage_validation_result.get("error"): 
                raise RuntimeError(f"Multi-stage Validation failed: {multi_stage_validation_result['error']}")
            
            # Step 5: Constraint Enforcement
            constraint_result = self._step_constraint_enforcement(answer_text, teacher_request_content)
            run_results["steps"]["constraint_enforcement"] = constraint_result

            # Store output and final decision
            run_results["output"] = answer_text
            run_results["final_decision"] = {
                "passed_validation": multi_stage_validation_result.get("isValid", False),
                "passed_constraints": constraint_result.get("passed", False),
                "final_score": multi_stage_validation_result.get("finalScore", 0.0),
                "feedback": multi_stage_validation_result.get("aggregateFeedback", "")
            }
            
            run_results["status"] = "completed"
            
        except Exception as e:
            self.logger.error(f"Error in Run 4 (Edge EdgePrompt) execution: {e}", exc_info=True)
            run_results["status"] = "failed"
            run_results["error"] = f"Run 4 Failed: {e}"
            
        # Aggregate metrics for entire run
        run_results["total_metrics"] = self.metrics_collector.merge_metrics([m for m in all_metrics if m])
        
        # Add quality metrics compared to reference (Run 1)
        # Note: Detailed quality analysis is typically done by the analysis script
        run_results["quality_vs_ref"] = {
            "pending_analysis": True,
            "note": "Quality metrics vs. Run 1 reference are calculated in the analysis phase."
        }
        
        return run_results


    # --- CloudLLM Step Helpers ---

    def _step_teacher_request(self, test_case: Dict[str, Any], cloud_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Simulate Teacher Request (CloudLLM)."""
        self.logger.debug("Simulating Teacher Request...")
        
        # For mock mode, we can directly use the teacher_request_context
        # This works better with the templates in our test environment
        if cloud_llm_model_data.get("mock", False):
            # Use the test case data directly as the teacher request
            teacher_req_data = test_case.get("teacher_request_context", {})
            
            # If empty, construct from test case data
            if not teacher_req_data:
                teacher_req_data = {
                    "topic": test_case.get("variables", {}).get("topic", "general knowledge"),
                    "learning_objective": f"Understanding {test_case.get('variables', {}).get('topic', 'general knowledge')}",
                    "content_type": "question",
                    "constraints": test_case.get("constraints", {})
                }
            
            self.logger.debug(f"Using mock teacher request data: {teacher_req_data}")
            return {
                "status": "completed", 
                "llm_output": json.dumps(teacher_req_data),
                "parsed_content": teacher_req_data,
                "metrics": {
                    "latency_ms": 50,
                    "input_tokens": 0,
                    "output_tokens": len(json.dumps(teacher_req_data).split())
                }
            }
        
        # Process for real mode
        teacher_req_ctx = test_case.get("teacher_request_context", {})
        
        # For real mode, we need to populate some required context fields in the template
        if "source_material_summary" not in teacher_req_ctx:
            teacher_req_ctx["source_material_summary"] = test_case.get("variables", {}).get("context", "No context provided")
            
        if "previous_common_errors" not in teacher_req_ctx:
            teacher_req_ctx["previous_common_errors"] = "No previous errors recorded"
        
        # Assume template name defined in test suite or default
        teacher_req_template = test_case.get("teacher_request_template", "teacher_request_persona")

        result = self._execute_cloud_llm_interaction(
            model_data=cloud_llm_model_data,
            interaction_type="generate_teacher_request",
            persona_template_id=teacher_req_template,
            context_data=teacher_req_ctx,
            expected_output_format="json" # Expect JSON for request structure
        )

        # Robustly parse the teacher request JSON
        parsed_content = None
        if not result.get("error"):
             parsed_content = self._parse_json_from_llm_output(result.get("llm_output"))
             if not parsed_content or not isinstance(parsed_content, dict) or "topic" not in parsed_content: # Basic check for dict structure
                 self.logger.warning(f"Failed to parse valid teacher request JSON from CloudLLM output for template {teacher_req_template}. Output: {result.get('llm_output')}")
                 result["error"] = result.get("error", "") + " Failed to parse valid teacher request JSON."
                 parsed_content = None # Ensure it's None on failure
             else:
                 self.logger.debug("Parsed teacher request successfully.")

        result["parsed_content"] = parsed_content # Add parsed content (or None)
        return result

    def _step_generate_structured_question(self, teacher_request: Optional[Dict[str, Any]], test_case: Dict[str, Any], cloud_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Generate Structured Question (CloudLLM)."""
        self.logger.debug("Generating Question using CloudLLM...")
        if not teacher_request: # Handle case where previous step failed
            return {"error": "Cannot generate question: Teacher request data is missing.", "metrics": {}}

        # Determine template: from teacher request or default
        question_gen_template = teacher_request.get("question_template_id", "direct_constraint_template")
        # Use teacher request content directly as variables for the template
        # Merge test case context too, in case template needs it
        question_gen_vars = {**teacher_request, **test_case.get("teacher_request_context", {})}

        prompt, metadata = self.template_engine.process_template(question_gen_template, question_gen_vars)
        if prompt is None:
            error_msg = f"Failed to process question generation template '{question_gen_template}': {metadata.get('error', 'Unknown')}"
            self.logger.error(error_msg)
            return {"error": error_msg, "metrics": {}}

        # Execute CloudLLM call
        result = self._execute_cloud_llm_interaction(
            model_data=cloud_llm_model_data,
            interaction_type="generate_structured_question",
            prompt=prompt,
            expected_output_format="text" # Simple text output expected here
        )
        
        return result

    def _step_generate_simple_question(self, test_case: Dict[str, Any], cloud_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Generate Simple Unstructured Question (CloudLLM)."""
        self.logger.debug("Generating Simple Question using CloudLLM...")
        
        # For simple baseline, we use a basic template with fewer constraints
        simple_prompt_template = test_case.get("baseline_template_id", "teacher_request_persona")
        simple_prompt_vars = {
            "topic": test_case.get("variables", {}).get("topic", "general knowledge"),
            "complexity": test_case.get("variables", {}).get("complexity", "moderate"),
            "audience": test_case.get("variables", {}).get("audience", "high school student"),
            "learning_objective": f"Understanding {test_case.get('variables', {}).get('topic', 'general knowledge')}"
        }
        
        prompt, metadata = self.template_engine.process_template(simple_prompt_template, simple_prompt_vars)
        if prompt is None:
            error_msg = f"Failed to process simple question template '{simple_prompt_template}': {metadata.get('error', 'Unknown')}"
            self.logger.error(error_msg)
            return {"error": error_msg, "metrics": {}}

        # Execute CloudLLM call
        result = self._execute_cloud_llm_interaction(
            model_data=cloud_llm_model_data,
            interaction_type="generate_simple_question",
            prompt=prompt,
            expected_output_format="text" # Simple text output expected here
        )
        
        return result

    def _step_simulate_student_answer(self, question: str, context: Optional[Dict[str, Any]], test_case: Dict[str, Any], cloud_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Simulate Student Answer (CloudLLM)."""
        self.logger.debug("Simulating Student Answer using CloudLLM...")
        
        # Determine student persona template
        student_template = test_case.get("student_template_id", "student_answer_persona")
        
        # Prepare variables for the template
        student_vars = {
            "question": question,
            "student_level": test_case.get("variables", {}).get("student_level", "average"),
            "topic": test_case.get("variables", {}).get("topic", "general knowledge"),
        }
        
        # If we have context from teacher request, add constraint awareness
        if context and isinstance(context, dict):
            student_vars["aware_of_constraints"] = True
            student_vars["constraints"] = context.get("constraints", {})
            student_vars["min_words"] = context.get("constraints", {}).get("min_words", 100)
            student_vars["max_words"] = context.get("constraints", {}).get("max_words", 500)
        else:
            student_vars["aware_of_constraints"] = False
        
        # Process the student template
        prompt, metadata = self.template_engine.process_template(student_template, student_vars)
        if prompt is None:
            error_msg = f"Failed to process student answer template '{student_template}': {metadata.get('error', 'Unknown')}"
            self.logger.error(error_msg)
            return {"error": error_msg, "metrics": {}}

        # Execute CloudLLM call
        result = self._execute_cloud_llm_interaction(
            model_data=cloud_llm_model_data,
            interaction_type="simulate_student",
            prompt=prompt,
            expected_output_format="text" # Simple text output expected here
        )
        
        return result

    def _step_baseline_evaluation(self, question: str, answer: str, test_case: Dict[str, Any], cloud_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Baseline Evaluation (CloudLLM)."""
        self.logger.debug("Performing Baseline Evaluation using CloudLLM...")
        
        # Determine evaluation template
        eval_template = test_case.get("baseline_eval_template_id", "teacher_review_persona")
        
        # Prepare variables for template
        eval_vars = {
            "question": question,
            "student_answer": answer,
            "topic": test_case.get("variables", {}).get("topic", "general knowledge"),
            "evaluation_criteria": test_case.get("evaluation_criteria", {})
        }
        
        # Process evaluation template
        prompt, metadata = self.template_engine.process_template(eval_template, eval_vars)
        if prompt is None:
            error_msg = f"Failed to process baseline evaluation template '{eval_template}': {metadata.get('error', 'Unknown')}"
            self.logger.error(error_msg)
            return {"error": error_msg, "metrics": {}}

        # Execute CloudLLM call
        result = self._execute_cloud_llm_interaction(
            model_data=cloud_llm_model_data,
            interaction_type="evaluate_answer",
            prompt=prompt,
            expected_output_format="json" # Expect structured evaluation result
        )
        
        # Parse evaluation result
        if not result.get("error"):
             parsed_eval = self._parse_json_from_llm_output(result.get("llm_output"))
             if not parsed_eval:
                 self.logger.warning(f"Failed to parse valid evaluation JSON from CloudLLM output. Output: {result.get('llm_output')}")
                 result["error"] = result.get("error", "") + " Failed to parse valid evaluation JSON."
             else:
                 # Apply normalization to ensure consistent keys
                 if "valid" in parsed_eval and "passed" not in parsed_eval:
                     parsed_eval["passed"] = parsed_eval["valid"]
                 
                 if "feedback" not in parsed_eval and "comments" in parsed_eval:
                     parsed_eval["feedback"] = parsed_eval["comments"]
                     
                 if "score" not in parsed_eval and any(k in parsed_eval for k in ["rating", "evaluation", "grade"]):
                     for key in ["rating", "evaluation", "grade"]:
                         if key in parsed_eval:
                             value = parsed_eval[key]
                             if isinstance(value, (int, float)):
                                 parsed_eval["score"] = float(value) / 10.0 if value > 10 else float(value)
                             break
                 
                 # Ensure score is within 0-1 range
                 if "score" in parsed_eval:
                     try:
                         score = float(parsed_eval["score"])
                         if score > 1.0 and score <= 10.0:
                             parsed_eval["score"] = score / 10.0
                         elif score > 10.0 and score <= 100.0:
                             parsed_eval["score"] = score / 100.0
                     except (ValueError, TypeError):
                         parsed_eval["score"] = 0.5 # Default if cannot parse
                         
             result["parsed_evaluation"] = parsed_eval
                 
        return result

    def _step_multistage_validation(self, question: str, answer: str, teacher_request: Dict[str, Any], cloud_llm_model_data: Dict[str, Any], validation_sequence_id: str) -> Dict[str, Any]:
        """Step: Multi-Stage Validation using the EvaluationEngine (CloudLLM)."""
        self.logger.debug(f"Performing Multi-Stage Validation (CloudLLM) using sequence: {validation_sequence_id}")
        
        # Delegate to the evaluation engine
        result = self.evaluation_engine.evaluate_using_cloud_llm(
            validation_sequence_id=validation_sequence_id,
            cloud_llm_model_data=cloud_llm_model_data,
            question=question,
            answer=answer,
            teacher_request=teacher_request
        )
        
        return result

    def _step_teacher_review(self, validation_result: Dict[str, Any], constraint_result: Dict[str, Any], 
                            question: str, answer: str, cloud_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Teacher Review (CloudLLM) for failed validations."""
        self.logger.debug("Performing Teacher Review using CloudLLM...")
        
        # Prepare the validation results for the teacher review
        validation_summary = "Validation checks failed.\n"
        
        # Add multistage validation feedback
        if "stages" in validation_result:
            validation_summary += "Validation stages:\n"
            for i, stage in enumerate(validation_result.get("stages", [])):
                status = "✅" if stage.get("passed", False) else "❌"
                feedback = stage.get("feedback", "No feedback provided")
                validation_summary += f"{i+1}. {status} {stage.get('name', f'Stage {i+1}')}: {feedback}\n"
        
        # Add constraint violation details
        if not constraint_result.get("passed", True):
            validation_summary += "\nConstraint violations:\n"
            for violation in constraint_result.get("violations", []):
                validation_summary += f"- {violation}\n"
        
        # Prepare variables for teacher review
        review_vars = {
            "question": question,
            "student_answer": answer,
            "validation_summary": validation_summary,
            "aggregated_feedback": validation_result.get("aggregateFeedback", "No aggregated feedback available")
        }
        
        # Process teacher review template
        review_template = "teacher_review_persona" # Default template
        prompt, metadata = self.template_engine.process_template(review_template, review_vars)
        if prompt is None:
            error_msg = f"Failed to process teacher review template '{review_template}': {metadata.get('error', 'Unknown')}"
            self.logger.error(error_msg)
            return {"error": error_msg, "metrics": {}}

        # Execute CloudLLM call
        result = self._execute_cloud_llm_interaction(
            model_data=cloud_llm_model_data,
            interaction_type="teacher_review",
            prompt=prompt,
            expected_output_format="json" # Expect structured review result
        )
        
        # Parse review result
        if not result.get("error"):
             parsed_review = self._parse_json_from_llm_output(result.get("llm_output"))
             if not parsed_review:
                 self.logger.warning(f"Failed to parse valid review JSON from CloudLLM output. Output: {result.get('llm_output')}")
                 result["error"] = result.get("error", "") + " Failed to parse valid review JSON."
             else:
                 result["parsed_review"] = parsed_review
                 
        return result

    def _step_constraint_enforcement(self, text: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Step: Constraint Enforcement."""
        # Check if we have constraint data
        constraints = {}
        if isinstance(context, dict) and "constraints" in context:
            constraints = context.get("constraints", {})
        elif isinstance(context, dict):
            constraints = context  # Some contexts might have constraints at top level
        
        # If no constraints defined, check test case
        if not constraints and hasattr(self, "_current_test_case"):
            constraints = getattr(self, "_current_test_case", {}).get("constraints", {})
        
        # Default constraints if none specified
        if not constraints:
            constraints = {
                "min_words": 50,
                "max_words": 500,
                "prohibited_topics": [],
                "required_topics": []
            }
            
        # Delegate to the constraint enforcer
        result = self.constraint_enforcer.validate(text, constraints)
        return result

    def _execute_cloud_llm_interaction(self, model_data: Dict[str, Any], interaction_type: str, 
                                      prompt: Optional[str] = None, persona_template_id: Optional[str] = None,
                                      context_data: Optional[Dict[str, Any]] = None,
                                      expected_output_format: str = "text") -> Dict[str, Any]:
        """
        Execute CloudLLM interaction. Centralized method for CloudLLM calls.
        
        Args:
            model_data: CloudLLM model configuration from ModelManager.
            interaction_type: Type of interaction for logging.
            prompt: The prompt to send (if already prepared).
            persona_template_id: Template ID to process (if not using direct prompt).
            context_data: Variables for template processing.
            expected_output_format: What kind of output to request ("text" or "json").
            
        Returns:
            Dictionary with 'llm_output', 'metrics', and optional 'error'.
        """
        # If using template instead of direct prompt, process it
        if prompt is None and persona_template_id:
            if context_data is None:
                context_data = {}
            prompt, metadata = self.template_engine.process_template(persona_template_id, context_data)
            if prompt is None:
                error_msg = f"Failed to process template '{persona_template_id}': {metadata.get('error', 'Unknown')}"
                self.logger.error(error_msg)
                return {"error": error_msg, "metrics": {}}
        
        # Prepare parameters based on expected output format
        params = {
            "temperature": 0.7,  # Default temperature, adjust as needed
            "max_tokens": 1024   # Default max tokens, adjust as needed
        }
        
        # Configure for JSON output if requested
        if expected_output_format.lower() == "json":
            params["response_format"] = {"type": "json_object"}
        
        # Execute CloudLLM call
        result = self.model_manager.execute_cloud_llm(model_data, prompt, params)
        
        # Log metrics by type for analysis
        metrics = result.get("metrics", {})
        if metrics:
            metrics["interaction_type"] = interaction_type
            
        # Return consistent result structure
        return {
            "llm_output": result.get("llm_output"),
            "error": result.get("error"),
            "metrics": metrics
        }

    # --- EdgeLLM Step Helpers ---

    def _step_generate_simple_question_edge(self, test_case: Dict[str, Any], edge_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Generate Simple Unstructured Question (EdgeLLM)."""
        self.logger.debug("Generating Simple Question using EdgeLLM...")
        
        # For simple baseline, we use a basic template with fewer constraints
        simple_prompt_template = test_case.get("baseline_template_id", "teacher_request_persona")
        simple_prompt_vars = {
            "topic": test_case.get("variables", {}).get("topic", "general knowledge"),
            "complexity": test_case.get("variables", {}).get("complexity", "moderate"),
            "audience": test_case.get("variables", {}).get("audience", "high school student"),
            "learning_objective": f"Understanding {test_case.get('variables', {}).get('topic', 'general knowledge')}"
        }
        
        prompt, metadata = self.template_engine.process_template(simple_prompt_template, simple_prompt_vars)
        if prompt is None:
            error_msg = f"Failed to process simple question template '{simple_prompt_template}': {metadata.get('error', 'Unknown')}"
            self.logger.error(error_msg)
            return {"error": error_msg, "metrics": {}}

        # Execute EdgeLLM call
        result = self.model_manager.execute_edge_llm(
            model_data=edge_llm_model_data,
            prompt=prompt,
            params={
                "temperature": 0.7,
                "max_tokens": 512
            }
        )
        
        # Log metrics by type for analysis
        metrics = result.get("metrics", {})
        if metrics:
            metrics["interaction_type"] = "generate_simple_question_edge"
            
        # Return consistent result structure
        return {
            "generated_text": result.get("generated_text"),
            "error": result.get("error"),
            "metrics": metrics
        }

    def _step_generate_structured_question_edge(self, teacher_request: Dict[str, Any], test_case: Dict[str, Any], edge_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Generate Structured Question (EdgeLLM)."""
        self.logger.debug("Generating Question using EdgeLLM...")
        
        # Determine template: from teacher request or default
        question_gen_template = teacher_request.get("question_template_id", "direct_constraint_template")
        # Use teacher request content directly as variables for the template
        # Merge test case context too, in case template needs it
        question_gen_vars = {**teacher_request, **test_case.get("teacher_request_context", {})}

        prompt, metadata = self.template_engine.process_template(question_gen_template, question_gen_vars)
        if prompt is None:
            error_msg = f"Failed to process question generation template '{question_gen_template}': {metadata.get('error', 'Unknown')}"
            self.logger.error(error_msg)
            return {"error": error_msg, "metrics": {}}

        # Execute EdgeLLM call
        result = self.model_manager.execute_edge_llm(
            model_data=edge_llm_model_data,
            prompt=prompt,
            params={
                "temperature": 0.7,
                "max_tokens": 512
            }
        )
        
        # Log metrics by type for analysis
        metrics = result.get("metrics", {})
        if metrics:
            metrics["interaction_type"] = "generate_structured_question_edge"
            
        # Return consistent result structure
        return {
            "generated_text": result.get("generated_text"),
            "error": result.get("error"),
            "metrics": metrics
        }

    def _step_simulate_student_answer_edge(self, question: str, context: Optional[Dict[str, Any]], test_case: Dict[str, Any], edge_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Simulate Student Answer (EdgeLLM)."""
        self.logger.debug("Simulating Student Answer using EdgeLLM...")
        
        # Determine student persona template
        student_template = test_case.get("student_template_id", "student_answer_persona")
        
        # Prepare variables for the template
        student_vars = {
            "question": question,
            "student_level": test_case.get("variables", {}).get("student_level", "average"),
            "topic": test_case.get("variables", {}).get("topic", "general knowledge"),
        }
        
        # If we have context from teacher request, add constraint awareness
        if context and isinstance(context, dict):
            student_vars["aware_of_constraints"] = True
            student_vars["constraints"] = context.get("constraints", {})
            student_vars["min_words"] = context.get("constraints", {}).get("min_words", 100)
            student_vars["max_words"] = context.get("constraints", {}).get("max_words", 500)
        else:
            student_vars["aware_of_constraints"] = False
        
        # Process the student template
        prompt, metadata = self.template_engine.process_template(student_template, student_vars)
        if prompt is None:
            error_msg = f"Failed to process student answer template '{student_template}': {metadata.get('error', 'Unknown')}"
            self.logger.error(error_msg)
            return {"error": error_msg, "metrics": {}}

        # Execute EdgeLLM call
        result = self.model_manager.execute_edge_llm(
            model_data=edge_llm_model_data,
            prompt=prompt,
            params={
                "temperature": 0.7,
                "max_tokens": 1024
            }
        )
        
        # Log metrics by type for analysis
        metrics = result.get("metrics", {})
        if metrics:
            metrics["interaction_type"] = "simulate_student_edge"
            
        # Return consistent result structure
        return {
            "generated_text": result.get("generated_text"),
            "error": result.get("error"),
            "metrics": metrics
        }

    def _step_baseline_evaluation_edge(self, question: str, answer: str, test_case: Dict[str, Any], edge_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Baseline Evaluation (EdgeLLM)."""
        self.logger.debug("Performing Baseline Evaluation using EdgeLLM...")
        
        # Determine evaluation template
        eval_template = test_case.get("baseline_eval_template_id", "teacher_review_persona")
        
        # Prepare variables for template
        eval_vars = {
            "question": question,
            "student_answer": answer,
            "topic": test_case.get("variables", {}).get("topic", "general knowledge"),
            "evaluation_criteria": test_case.get("evaluation_criteria", {})
        }
        
        # Process evaluation template
        prompt, metadata = self.template_engine.process_template(eval_template, eval_vars)
        if prompt is None:
            error_msg = f"Failed to process baseline evaluation template '{eval_template}': {metadata.get('error', 'Unknown')}"
            self.logger.error(error_msg)
            return {"error": error_msg, "metrics": {}}

        # Execute EdgeLLM call
        result = self.model_manager.execute_edge_llm(
            model_data=edge_llm_model_data,
            prompt=prompt,
            params={
                "temperature": 0.3,
                "max_tokens": 512,
                "json_output": True
            }
        )
        
        # Log metrics by type for analysis
        metrics = result.get("metrics", {})
        if metrics:
            metrics["interaction_type"] = "evaluate_answer_edge"
        
        # Parse evaluation result
        if not result.get("error"):
             parsed_eval = self._parse_json_from_llm_output(result.get("generated_text"))
             if not parsed_eval:
                 self.logger.warning(f"Failed to parse valid evaluation JSON from EdgeLLM output. Output: {result.get('generated_text')}")
                 result["error"] = result.get("error", "") + " Failed to parse valid evaluation JSON."
             else:
                 # Apply normalization to ensure consistent keys
                 if "valid" in parsed_eval and "passed" not in parsed_eval:
                     parsed_eval["passed"] = parsed_eval["valid"]
                 
                 if "feedback" not in parsed_eval and "comments" in parsed_eval:
                     parsed_eval["feedback"] = parsed_eval["comments"]
                     
                 if "score" not in parsed_eval and any(k in parsed_eval for k in ["rating", "evaluation", "grade"]):
                     for key in ["rating", "evaluation", "grade"]:
                         if key in parsed_eval:
                             value = parsed_eval[key]
                             if isinstance(value, (int, float)):
                                 parsed_eval["score"] = float(value) / 10.0 if value > 10 else float(value)
                             break
                 
                 # Ensure score is within 0-1 range
                 if "score" in parsed_eval:
                     try:
                         score = float(parsed_eval["score"])
                         if score > 1.0 and score <= 10.0:
                             parsed_eval["score"] = score / 10.0
                         elif score > 10.0 and score <= 100.0:
                             parsed_eval["score"] = score / 100.0
                     except (ValueError, TypeError):
                         parsed_eval["score"] = 0.5 # Default if cannot parse
                         
             result["parsed_evaluation"] = parsed_eval
                 
        # Return consistent result structure
        return {
            "generated_text": result.get("generated_text"),
            "error": result.get("error"),
            "metrics": metrics,
            "parsed_evaluation": result.get("parsed_evaluation", {})
        }

    def _step_multistage_validation_edge(self, question: str, answer: str, teacher_request: Dict[str, Any], edge_llm_model_data: Dict[str, Any], validation_sequence_id: str) -> Dict[str, Any]:
        """Step: Multi-Stage Validation using the EvaluationEngine (EdgeLLM)."""
        self.logger.debug(f"Performing Multi-Stage Validation (EdgeLLM) using sequence: {validation_sequence_id}")
        
        # Delegate to the evaluation engine
        result = self.evaluation_engine.evaluate_using_edge_llm(
            validation_sequence_id=validation_sequence_id,
            edge_llm_model_data=edge_llm_model_data,
            question=question,
            answer=answer,
            teacher_request=teacher_request
        )
        
        return result

    # --- Helper Methods ---

    def _parse_json_from_llm_output(self, text: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Parse JSON from LLM output text using a robust approach.
        
        Delegate to the evaluation engine's helper for consistency.
        """
        if not text:
            return None
            
        return self.evaluation_engine.parse_json_from_llm_output(text)

    def _create_run_data_struct(self, run_id: str, test_case_id: str, cloud_llm_model_id: str, edge_llm_model_id: str, hardware_profile: str) -> Dict[str, Any]:
        """Create the basic data structure for a run result."""
        timestamp = datetime.now().isoformat()
        
        return {
            "run_id": run_id,
            "timestamp": timestamp,
            "test_case_id": test_case_id,
            "cloud_llm_model": cloud_llm_model_id,
            "edge_llm_model": edge_llm_model_id,
            "hardware_profile": hardware_profile,
            "status": "initialized",
            "mock_mode": self.mock_models
        }
        
    def _verify_topic_consistency(self, run_data: Dict[str, Any], test_case: Dict[str, Any]) -> bool:
        """Check if all runs use the same topic for valid comparison."""
        teacher_request = test_case.get("shared_teacher_request", {})
        original_topic = test_case.get("variables", {}).get("topic", "")
        shared_topic = teacher_request.get("topic", "")
        
        # Get topics from each run output if they exist
        run_1_topic = run_data.get("run_1", {}).get("output", "").split("\n")[0] if run_data.get("run_1") else ""
        run_2_topic = run_data.get("run_2", {}).get("output", "").split("\n")[0] if run_data.get("run_2") else ""
        run_3_topic = run_data.get("run_3", {}).get("output", "").split("\n")[0] if run_data.get("run_3") else ""
        run_4_topic = run_data.get("run_4", {}).get("output", "").split("\n")[0] if run_data.get("run_4") else ""
        
        self.logger.debug(f"[Run {run_data.get('run_id')}] Topic consistency check:")
        self.logger.debug(f"  - Original: {original_topic}")
        self.logger.debug(f"  - Shared: {shared_topic}")
        self.logger.debug(f"  - Run 1: {run_1_topic[:50]}...")
        self.logger.debug(f"  - Run 2: {run_2_topic[:50]}...")
        self.logger.debug(f"  - Run 3: {run_3_topic[:50]}...")
        self.logger.debug(f"  - Run 4: {run_4_topic[:50]}...")
        
        # For now just log, could implement stricter checking
        return True
        
    def _create_analysis_summary(self, suite_id: str, run_counter: int, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a basic analysis summary of the test suite results."""
        error_count = sum(1 for r in results if "error" in r and r["error"])
        successful_runs = sum(1 for r in results if r.get("status") == "completed")
        
        # Get some basic aggregate metrics 
        total_metrics_runs = []
        for run in results:
            # Check for error-free runs
            if run.get("status") == "completed":
                # Collect metrics for comparisons
                for run_type in ["run_1", "run_2", "run_3", "run_4"]:
                    if run_type in run and "total_metrics" in run[run_type]:
                        metrics = run[run_type]["total_metrics"]
                        metrics["run_type"] = run_type
                        metrics["edge_llm_model"] = run.get("edge_llm_model")
                        total_metrics_runs.append(metrics)
        
        # Very simple metrics calculation for now
        avg_latency = {}
        avg_tokens = {}
        for run_type in ["run_1", "run_2", "run_3", "run_4"]:
            type_metrics = [m for m in total_metrics_runs if m.get("run_type") == run_type]
            if type_metrics:
                latencies = [m.get("latency_ms", 0) for m in type_metrics]
                avg_latency[run_type] = sum(latencies) / len(latencies) if latencies else 0
                
                tokens = [m.get("output_tokens", 0) for m in type_metrics]
                avg_tokens[run_type] = sum(tokens) / len(tokens) if tokens else 0
        
        return {
            "suite_id": suite_id,
            "timestamp": datetime.now().isoformat(),
            "total_runs": run_counter,
            "successful_runs": successful_runs,
            "error_count": error_count,
            "summary_metrics": {
                "avg_latency_ms": avg_latency,
                "avg_output_tokens": avg_tokens
            }
        }
                
    def _log_and_return_error(self, message: str, exception: Exception = None) -> Dict[str, Any]:
        """Log an error and return a standardized error result."""
        error_message = message
        if exception:
            error_message += f" Error: {str(exception)}"
            self.logger.error(error_message, exc_info=True)
        else:
            self.logger.error(error_message)
            
        return {
            "status": "failed",
            "error": error_message,
            "error_count": 1
        }