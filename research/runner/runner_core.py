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
                lm_studio_url: Optional[str] = None, mock_models: bool = False,
                 openai_api_key: Optional[str] = None,
                anthropic_api_key: Optional[str] = None):
        """
        Initialize the RunnerCore and all its components.

        Injects dependencies into components based on refactored signatures.
        
        Args:
            config_path: Path to the main test suite configuration file.
            output_dir: Directory for storing results and logs.
            log_level: Logging verbosity level (DEBUG, INFO, WARNING, ERROR).
            lm_studio_url: Base URL for LM Studio server (if used for EdgeLLM).
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
            params={"temperature": 0.7}  # Allow some creativity
        )
        self.logger.debug(f"Generated question text (first 50): {result.get('llm_output', '')[:50]}...")
        return result

    def _step_generate_simple_question(self, test_case: Dict[str, Any], cloud_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Generate Simple, Unstructured Question (CloudLLM) with topic control."""
        self.logger.debug("Generating Simple Question using CloudLLM with topic control...")
        
        # Get the shared teacher request if available
        teacher_request = test_case.get("shared_teacher_request")
        if teacher_request and isinstance(teacher_request, dict):
            # Use the shared teacher request for consistency
            topic = teacher_request.get("topic", "a relevant topic")
            objective = teacher_request.get("learning_objective", f"Understanding {topic}")
            # Try to get grade level from constraints
            grade_level = "Grade 5" # Default
            if isinstance(teacher_request.get("constraints"), dict):
                if "safety_rules" in teacher_request["constraints"]:
                    safety_rules = teacher_request["constraints"]["safety_rules"]
                    if isinstance(safety_rules, list) and safety_rules:
                        grade_level = safety_rules[0]  # Use first safety rule as grade level
        else:
            # Fall back to previous behavior if shared request not available
            teacher_req_ctx = test_case.get("teacher_request_context", {})
            topic = teacher_req_ctx.get("topic", "a relevant topic")
            objective = teacher_req_ctx.get("learning_objective", "explain something simply")
            # Infer grade level or use default if not specified
            grade_level = "Grade 5" # Default
            if isinstance(teacher_req_ctx.get("desired_constraints"), dict):
                grade_level = teacher_req_ctx["desired_constraints"].get("safety", grade_level)

        # Create a more focused prompt with explicit topic control
        unstructured_prompt = f"""
Generate a single, clear question about '{topic}' suitable for {grade_level}.
The question should relate to the objective: {objective}.

Your question should be direct, focused on {topic}, and appropriate for the grade level.
Do not provide additional context or explanations - just the question itself.
"""

        result = self._execute_cloud_llm_interaction(
            model_data=cloud_llm_model_data,
            interaction_type="generate_simple_question",
            prompt=unstructured_prompt,
            params={"temperature": 0.7}
        )
        self.logger.debug(f"Generated topic-controlled question (first 50): {result.get('llm_output', '')[:50]}...")
        return result

    def _step_simulate_student_answer(self, question_text: Optional[str], teacher_request: Optional[Dict[str, Any]], test_case: Dict[str, Any], cloud_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Simulate Student Answer (CloudLLM)."""
        self.logger.debug("Simulating Student Answer using CloudLLM...")
        if not question_text:
            return {"error": "Cannot simulate answer: Generated question text is missing.", "metrics": {}}
        if not teacher_request: teacher_request = {} # Handle missing teacher request gracefully for constraints

        student_answer_template = test_case.get("student_answer_template", "student_answer_persona")
        # Provide context for the student persona template
        student_context = {
             "question_text": question_text,
             "student_profile_details": test_case.get("student_persona_profile", "Average student."),
             # Try to get word count target from teacher request constraints
             "word_count_target": teacher_request.get("constraints", {}).get("maxWords", 100) // 2
        }
        result = self._execute_cloud_llm_interaction(
            model_data=cloud_llm_model_data,
            interaction_type="generate_student_answer",
            persona_template_id=student_answer_template,
            context_data=student_context
        )
        self.logger.debug(f"Simulated student answer (first 50): {result.get('llm_output', '')[:50]}...")
        return result

    def _step_baseline_evaluation(self, question: Optional[str], answer: Optional[str], test_case: Dict[str, Any], cloud_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Simple Baseline Evaluation (CloudLLM)."""
        self.logger.debug("Performing Baseline Evaluation using CloudLLM...")
        step_result = {"status": "skipped", "passed": False, "score": 0.0, "feedback": ""}

        if not question or not answer:
            step_result["error"] = "Missing question or answer for evaluation."
            return step_result

        # Get evaluation criteria from the test case
        eval_criteria = test_case.get("evaluation_criteria", {})
        criteria_str = json.dumps(eval_criteria, indent=2)

        context_data = {
            "question_text": question,
            "student_answer": answer,
            "evaluation_criteria": criteria_str
        }

        # Execute evaluation, requesting JSON output
        result = self._execute_cloud_llm_interaction(
            model_data=cloud_llm_model_data,
            interaction_type="baseline_evaluation",
            prompt=f"""Evaluate this student answer:
Question: {question}
Answer: {answer}
Criteria: {criteria_str}

Provide a JSON response with these fields:
{{
  "passed": true/false,
  "score": (0.0-1.0),
  "feedback": "Detailed feedback on the answer"
}}""",
            params={"temperature": 0.1, "response_format": {"type": "json_object"}}
        )

        # Parse the result (assuming similar format to validation stages for comparison)
        parsed_eval = None
        if not result.get("error"):
             parsed_eval = self._parse_json_from_llm_output(result.get("llm_output"))
             if parsed_eval is None:
                 self.logger.warning(f"Baseline evaluation result was not parseable JSON.")
                 # Add error info to the main result dict if parsing failed
                 result["error"] = result.get("error", "") + " Failed to parse baseline evaluation JSON."
                 parsed_eval = {"passed": False, "score": 0.0, "feedback": "Parsing failed"} # Default on parse fail
             else:
                 self.logger.debug(f"Parsed baseline evaluation: {parsed_eval}")
        else:
             self.logger.warning(f"Baseline evaluation LLM call failed: {result.get('error')}")
             parsed_eval = {"passed": False, "score": 0.0, "feedback": "Evaluation step failed"} # Default on execution fail

        result["parsed_evaluation"] = parsed_eval # Store parsed data (or default)
        return result

    def _step_multistage_validation(self, question: Optional[str], answer: Optional[str], 
                                  teacher_request: Optional[Dict[str, Any]], 
                                  cloud_llm_model_data: Dict[str, Any],
                                  validation_sequence_id: str = "basic_validation_sequence") -> Dict[str, Any]:
        """
        Performs multi-stage validation using CloudLLM.
        Uses the EvaluationEngine for the actual validation.
        """
        if not question or not answer:
            return {"error": "Missing question or answer for validation", "isValid": False}
        
        try:
            self.logger.debug(f"Starting multi-stage validation with sequence '{validation_sequence_id}'")
            
            # Use the EvaluationEngine to handle the validation
            def cloud_llm_executor_wrapper(prompt: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
                # This inner function calls the actual ModelManager method
                return self._execute_cloud_llm_interaction(
                    cloud_llm_model_data, 
                    "validation", 
                    prompt=prompt, 
                    params=params
                )
            
            # Execute the validation through the evaluation engine
            validation_result = self.evaluation_engine.validate_with_sequence(
                question=question,
                answer=answer,
                context=teacher_request,  # Contains constraints and rubric
                validation_sequence_id=validation_sequence_id,
                llm_executor=cloud_llm_executor_wrapper
            )
            
            return validation_result
        
        except Exception as e:
            self.logger.error(f"Multi-stage validation error: {e}", exc_info=True)
            return {"error": f"Validation failed: {str(e)}", "isValid": False}

    def _step_constraint_enforcement(self, student_answer: Optional[str], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Step: Constraint Enforcement."""
        self.logger.debug("Performing Constraint Enforcement...")
        if not student_answer:
            return {"passed": False, "violations": ["Cannot enforce constraints: Student answer missing."]}
        if not context: context = {} # Handle missing context gracefully

        # Get constraints from context
        constraints_to_enforce = context.get("constraints", {})
        if not isinstance(constraints_to_enforce, dict):
            self.logger.warning(f"Constraints from context were not a dictionary: {constraints_to_enforce}. Using empty constraints.")
            constraints_to_enforce = {}

        result = self.constraint_enforcer.enforce_constraints(
            content=student_answer,
            constraints=constraints_to_enforce
        )
        self.logger.debug(f"Constraint enforcement complete. Passed: {result.get('passed')}")
        return result

    def _step_teacher_review(self, validation_result: Dict[str, Any], constraint_result: Dict[str, Any], question: Optional[str], answer: Optional[str], cloud_llm_model_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Step: Simulate Teacher Review (CloudLLM, Optional)."""
        # Trigger review if validation OR constraints failed
        review_needed = not validation_result.get("isValid", True) or not constraint_result.get("passed", True)
        if not review_needed:
            self.logger.debug("Skipping Teacher Review (validation/constraints passed).")
            return {"status": "skipped (passed validation/constraints)"}
        if not question or not answer:
             self.logger.warning("Skipping Teacher Review: Missing question or answer.")
             return {"status": "skipped (missing question/answer)"}


        self.logger.info("Validation/Constraints failed, simulating Teacher Review...")
        # Prepare context for the review template
        review_context = {
             "question": question,
             "student_answer": answer,
             "validation_feedback": validation_result.get("aggregateFeedback", "N/A"),
             "constraint_violations": constraint_result.get("violations", [])
        }
        # Assume a standard review template exists
        review_template = "teacher_review_persona" # Needs to be defined in configs/templates

        result = self._execute_cloud_llm_interaction(
             model_data=cloud_llm_model_data,
             interaction_type="review_evaluation",
             persona_template_id=review_template,
             context_data=review_context,
             expected_output_format="json" # Expect structured review output
        )

        # Optionally parse the review JSON
        if not result.get("error"):
             parsed_review = self._parse_json_from_llm_output(result.get("llm_output"))
             result["parsed_review"] = parsed_review # Add parsed review (or None)

        self.logger.debug(f"Teacher review complete. Error: {result.get('error')}")
        return result

    # --- EdgeLLM Step Helpers ---

    def _step_generate_simple_question_edge(self, test_case: Dict[str, Any], edge_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Generate Simple, Unstructured Question (EdgeLLM) with topic control."""
        self.logger.debug("Generating Simple Question using EdgeLLM with topic control...")
        
        # Get the shared teacher request if available
        teacher_request = test_case.get("shared_teacher_request")
        if teacher_request and isinstance(teacher_request, dict):
            # Use the shared teacher request for consistency
            topic = teacher_request.get("topic", "a relevant topic")
            objective = teacher_request.get("learning_objective", f"Understanding {topic}")
            # Try to get grade level from constraints
            grade_level = "Grade 5" # Default
            if isinstance(teacher_request.get("constraints"), dict):
                if "safety_rules" in teacher_request["constraints"]:
                    safety_rules = teacher_request["constraints"]["safety_rules"]
                    if isinstance(safety_rules, list) and safety_rules:
                        grade_level = safety_rules[0]  # Use first safety rule as grade level
        else:
            # Fall back to previous behavior if shared request not available
            teacher_req_ctx = test_case.get("teacher_request_context", {})
            topic = teacher_req_ctx.get("topic", "a relevant topic")
            objective = teacher_req_ctx.get("learning_objective", "explain something simply")
            # Infer grade level or use default if not specified
            grade_level = "Grade 5" # Default
            if isinstance(teacher_req_ctx.get("desired_constraints"), dict):
                grade_level = teacher_req_ctx["desired_constraints"].get("safety", grade_level)

        # Create a more focused prompt with explicit topic control
        unstructured_prompt = f"""
Generate a single, clear question about '{topic}' suitable for {grade_level}.
The question should relate to the objective: {objective}.

Your question should be direct, focused on {topic}, and appropriate for the grade level.
Do not provide additional context or explanations - just the question itself.
"""

        result = self._execute_edge_llm(
             edge_llm_model_data, unstructured_prompt, params={"temperature": 0.7}
        )
        self.logger.debug(f"Generated topic-controlled question (first 50): {result.get('generated_text', '')[:50]}...")
        return result

    def _step_generate_structured_question_edge(self, teacher_request: Optional[Dict[str, Any]], test_case: Dict[str, Any], edge_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Generate Structured Question (EdgeLLM)."""
        self.logger.debug("Generating Question using EdgeLLM...")
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

        # Execute EdgeLLM call
        result = self._execute_edge_llm(
             edge_llm_model_data, prompt, params={"temperature": 0.7} # Allow some creativity
        )
        self.logger.debug(f"Generated question text (first 50): {result.get('generated_text', '')[:50]}...")
        return result

    def _step_simulate_student_answer_edge(self, question_text: Optional[str], context: Optional[Dict[str, Any]], test_case: Dict[str, Any], edge_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Simulate Student Answer (EdgeLLM)."""
        self.logger.debug("Simulating Student Answer using EdgeLLM...")
        if not question_text:
            return {"error": "Cannot simulate answer: Generated question text is missing.", "metrics": {}}
        if not context: context = {} # Handle missing context gracefully for constraints

        # Create simple prompt for student answer
        word_count_target = context.get("constraints", {}).get("maxWords", 100) // 2
        
        student_prompt = f"""Answer the following question as if you were a student. 
Write approximately {word_count_target} words.

Student profile: {test_case.get("student_persona_profile", "Average student.")}

Question: {question_text}

Your answer:"""

        result = self._execute_edge_llm(
            edge_llm_model_data, student_prompt, params={"temperature": 0.7}
        )
        self.logger.debug(f"Simulated student answer (first 50): {result.get('generated_text', '')[:50]}...")
        return result

    def _step_baseline_evaluation_edge(self, question: Optional[str], answer: Optional[str], test_case: Dict[str, Any], edge_llm_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Step: Simple Baseline Evaluation (EdgeLLM)."""
        self.logger.debug("Performing Baseline Evaluation using EdgeLLM...")
        step_result = {"status": "skipped", "passed": False, "score": 0.0, "feedback": ""}

        if not question or not answer:
            step_result["error"] = "Missing question or answer for evaluation."
            return step_result

        # Get evaluation criteria from the test case
        eval_criteria = test_case.get("evaluation_criteria", {})
        criteria_str = json.dumps(eval_criteria, indent=2)

        eval_prompt = f"""Evaluate this student answer:
Question: {question}
Answer: {answer}
Criteria: {criteria_str}

Provide a JSON response with these fields:
{{
  "passed": true/false,
  "score": (0.0-1.0),
  "feedback": "Detailed feedback on the answer"
}}"""

        # Execute evaluation
        result = self._execute_edge_llm(
             edge_llm_model_data, eval_prompt, params={"temperature": 0.1, "json_output": True}
        )

        # Parse the result
        parsed_eval = None
        if not result.get("error"):
             parsed_eval = self._parse_json_from_llm_output(result.get("generated_text"))
             if parsed_eval is None:
                 self.logger.warning(f"Baseline evaluation result was not parseable JSON.")
                 # Add error info to the main result dict if parsing failed
                 result["error"] = result.get("error", "") + " Failed to parse baseline evaluation JSON."
                 parsed_eval = {"passed": False, "score": 0.0, "feedback": "Parsing failed"} # Default on parse fail
             else:
                 self.logger.debug(f"Parsed baseline evaluation: {parsed_eval}")
        else:
             self.logger.warning(f"Baseline evaluation LLM call failed: {result.get('error')}")
             parsed_eval = {"passed": False, "score": 0.0, "feedback": "Evaluation step failed"} # Default on execution fail

        result["parsed_evaluation"] = parsed_eval # Store parsed data (or default)
        return result

    def _step_multistage_validation_edge(self, question: Optional[str], answer: Optional[str], 
                                      teacher_request: Optional[Dict[str, Any]], 
                                      edge_llm_model_data: Dict[str, Any],
                                      validation_sequence_id: str = "basic_validation_sequence") -> Dict[str, Any]:
        """
        Performs multi-stage validation using EdgeLLM.
        Uses the EvaluationEngine for the actual validation.
        """
        if not question or not answer:
            return {"error": "Missing question or answer for validation", "isValid": False}
        
        try:
            self.logger.debug(f"Starting multi-stage validation with sequence '{validation_sequence_id}'")
            
            # Use the EvaluationEngine to handle the validation
            def edge_llm_executor_wrapper(prompt: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
                # This inner function calls the actual ModelManager method
                return self._execute_edge_llm(edge_llm_model_data, prompt, params)
            
            # Execute the validation through the evaluation engine
            try:
                validation_result = self.evaluation_engine.validate_with_sequence(
                    question=question,
                    answer=answer,
                    context=teacher_request,  # Contains constraints and rubric
                    validation_sequence_id=validation_sequence_id,
                    llm_executor=edge_llm_executor_wrapper
                )
                return validation_result
            except ValueError as ve:
                # Catch JSON parsing errors specifically
                if "VALIDATION ERROR" in str(ve) and any(msg in str(ve) for msg in ["JSON", "parse"]):
                    self.logger.warning(f"JSON parsing error detected: {ve}")
                    
                    # Import our new JSON utilities
                    from .json_utils import parse_llm_json_output
                    
                    # First try the simplified validation sequence
                    simple_validation_id = "simplified_validation_sequence"
                    
                    # Only try simplified sequence if we're not already using it
                    if validation_sequence_id != simple_validation_id:
                        self.logger.info("Attempting validation with simplified sequence for better JSON output...")
                        try:
                            # Try with the simplified sequence
                            validation_result = self.evaluation_engine.validate_with_sequence(
                                question=question,
                                answer=answer,
                                context=teacher_request,
                                validation_sequence_id=simple_validation_id,
                                llm_executor=edge_llm_executor_wrapper
                            )
                            return validation_result
                        except Exception as e2:
                            self.logger.error(f"Simplified validation also failed: {e2}")
                            # Proceed to direct JSON generation
                    
                    # If we get here, both regular and simplified validation failed
                    # Use a direct JSON generation approach
                    self.logger.info("Generating direct validation JSON...")
                    
                    # Construct a simple validation prompt that focuses just on generating valid JSON
                    json_focus_prompt = f"""Evaluate this student answer to a question. Return ONLY valid JSON without markdown.

QUESTION: {question}

STUDENT ANSWER: {answer}

Evaluate if the answer is relevant to the question and the information is accurate.
Output MUST be valid JSON with this exact structure: {{"passed": true/false, "score": 0.7, "feedback": "Your feedback here"}}

The "passed" field must be true or false.
The "score" field must be a number between 0 and 1.
The "feedback" field must be a string with your evaluation.

IMPORTANT: Return ONLY the JSON object - NO markdown formatting, code blocks, or explanations."""

                    # Execute with parameters forcing JSON output and low temperature
                    json_params = {
                        "temperature": 0.1,
                        "max_tokens": 256,
                        "json_output": True
                    }
                    
                    result = edge_llm_executor_wrapper(json_focus_prompt, json_params)
                    
                    if result.get("error"):
                        self.logger.error(f"Direct JSON generation failed: {result.get('error')}")
                        
                        # Last resort - try JSON repair if we have a response from a previous attempt
                        # This typically happens when there's a partial JSON in a prior validation attempt
                        original_error_text = str(ve)
                        if "extract valid JSON from output:" in original_error_text:
                            # Try to extract the failed output from the error message
                            error_parts = original_error_text.split("output:")
                            if len(error_parts) > 1:
                                failed_output = error_parts[1].strip()
                                if failed_output:
                                    self.logger.info("Attempting JSON repair on previous failed output...")
                                    repaired_json_str = self.model_manager.repair_json_with_llm(
                                        failed_output, 
                                        edge_llm_model_data,
                                        max_attempts=1
                                    )
                                    try:
                                        # Try to parse the repaired JSON
                                        parsed_json = json.loads(repaired_json_str)
                                        return {
                                            "isValid": parsed_json.get("passed", False),
                                            "finalScore": float(parsed_json.get("score", 0.0)),
                                            "stageResults": [{
                                                "stageId": "json_repaired_validation",
                                                "passed": parsed_json.get("passed", False),
                                                "score": float(parsed_json.get("score", 0.0)),
                                                "feedback": parsed_json.get("feedback", "Repaired validation result.")
                                            }],
                                            "aggregateFeedback": parsed_json.get("feedback", "Repaired validation result."),
                                            "metrics": {"json_repaired": True}
                                        }
                                    except json.JSONDecodeError:
                                        # Give up and raise the original exception
                                        raise ve
                        
                        # If we get here, all approaches failed
                        raise ve
                        
                    # Try to parse the direct JSON result using our utility
                    generated_text = result.get("generated_text", "")
                    parsed_json = parse_llm_json_output(
                        generated_text,
                        required_keys=["passed", "score", "feedback"],
                        default_values={
                            "passed": False,
                            "score": 0.5,
                            "feedback": "Validation could not be completed properly."
                        }
                    )
                    
                    # Return in the expected format for validation results
                    return {
                        "isValid": parsed_json.get("passed", False),
                        "finalScore": float(parsed_json.get("score", 0.0)),
                        "stageResults": [{
                            "stageId": "direct_json_validation",
                            "passed": parsed_json.get("passed", False),
                            "score": float(parsed_json.get("score", 0.0)),
                            "feedback": parsed_json.get("feedback", "Direct JSON validation result.")
                        }],
                        "aggregateFeedback": parsed_json.get("feedback", "Direct JSON validation result."),
                        "metrics": result.get("metrics", {})
                    }
                else:
                    # Not a JSON parsing error, re-raise
                    raise
            
        except Exception as e:
            self.logger.error(f"Multi-stage validation error: {e}", exc_info=True)
            return {"error": f"Validation failed: {str(e)}", "isValid": False}


    # --- Core LLM Execution Helpers ---

    def _execute_cloud_llm_interaction(self, model_data: Dict[str, Any], interaction_type: str,
                                     persona_template_id: Optional[str] = None, context_data: Optional[Dict[str, Any]] = None,
                                     prompt: Optional[str] = None,
                                     params: Optional[Dict[str, Any]] = None,
                                     expected_output_format: Optional[str] = None) -> Dict[str, Any]:
        """
        Helper to execute an interaction with CloudLLM.
        Handles template processing and calls ModelManager.
        Returns full result dict.
        """
        self.logger.debug(f"Executing CloudLLM Interaction: {interaction_type}")

        # Process template if provided
        if persona_template_id and context_data:
            # Process Persona Prompt Template
            processed_prompt, metadata = self.template_engine.process_template(persona_template_id, context_data)
            if processed_prompt is None:
                error_msg = f"Failed to process persona template '{persona_template_id}': {metadata.get('error', 'Unknown')}"
                self.logger.error(error_msg)
                # Return structure consistent with ModelManager failure
                return {"error": error_msg, "llm_output": None, "metrics": {}}
            prompt = processed_prompt

        if not prompt:
            error_msg = "No prompt provided and template processing failed"
            self.logger.error(error_msg)
            return {"error": error_msg, "llm_output": None, "metrics": {}}

        # Set up parameters
        execution_params = params or {"temperature": 0.7} # Default temp
        if interaction_type == "review_evaluation": execution_params["temperature"] = 0.2 # More objective review
        if expected_output_format == "json":
            execution_params["response_format"] = {"type": "json_object"}

        result = self.model_manager.execute_cloud_llm(model_data, prompt, execution_params)
        # Result structure: {llm_output, input_tokens, output_tokens, metrics, error?}
        result["interaction_type"] = interaction_type # Add interaction type for context
        self.logger.debug(f"CloudLLM Interaction '{interaction_type}' complete. Error: {result.get('error')}")
        return result

    def _execute_edge_llm(self, model_data: Dict[str, Any], prompt: str,
                       params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Helper to execute a task with EdgeLLM via ModelManager.
        Returns full result dict.
        """
        self.logger.debug(f"Executing EdgeLLM task (prompt len {len(prompt)})... Params: {params}")
        if not prompt:
             self.logger.error("EdgeLLM execution requested with empty prompt.")
             return {"error": "Empty prompt provided to EdgeLLM.", "generated_text": None, "metrics": {}}
        result = self.model_manager.execute_edge_llm(model_data, prompt, params)
        # Result structure: {generated_text, input_tokens, output_tokens, metrics, error?}
        self.logger.debug(f"EdgeLLM task complete. Error: {result.get('error')}")
        return result


    # --- Other Helper Methods ---

    def _parse_json_from_llm_output(self, text: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Robustly attempts to parse JSON from LLM text output using various patterns.
        Returns dictionary on success, None on failure. Logs warnings on failure.
        """
        if not text or not isinstance(text, str):
            self.logger.warning("Attempted to parse JSON from empty or non-string input.")
            return None

        # Clean potential wrapping quotes if the whole string is quoted JSON
        if text.startswith('"') and text.endswith('"'):
             text = text[1:-1].replace('\\"', '"').replace('\\\\', '\\')

        # Strip leading/trailing whitespace
        text = text.strip()

        self.logger.debug(f"Attempting to parse JSON from output (first 150): {text[:150]}...")

        # 1. Try direct parsing (most common case for compliant models)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            self.logger.debug("Direct JSON parsing failed. Trying extraction patterns.")
            pass # Continue to extraction patterns

        # 2. Try extracting from markdown code blocks (```json ... ``` or ``` ... ```)
        patterns = [
            r'```(?:json)?\s*(\{.*?\})\s*```', # ```json { ... } ``` or ``` { ... } ``` (non-greedy)
            r'```\s*(\[.*?\])\s*```'          # ``` [ ... ] ``` (for arrays)
        ]
        for pattern in patterns:
             match = re.search(pattern, text, re.DOTALL)
             if match:
                 json_text = match.group(1)
                 try:
                     self.logger.debug(f"Found JSON in markdown block: {json_text[:100]}...")
                     return json.loads(json_text)
                 except json.JSONDecodeError:
                     self.logger.warning(f"Extracted text from markdown looked like JSON but failed to parse: {json_text[:100]}...")
                     # Continue searching, maybe there's another block or direct JSON later

        # 3. Permissive: Find first top-level JSON object or array starting at the beginning
        #    Handles cases where the LLM just outputs JSON without markdown
        json_match_obj = re.match(r'^\s*(\{.*?\})\s*$', text, re.DOTALL)
        json_match_arr = re.match(r'^\s*(\[.*?\])\s*$', text, re.DOTALL)
        if json_match_obj:
            json_text = json_match_obj.group(1)
        elif json_match_arr:
            json_text = json_match_arr.group(1)
        else:
             json_text = None

        if json_text:
            try:
                 self.logger.debug(f"Found JSON object/array via start/end match: {json_text[:100]}...")
                 # Final check: ensure it's a dict or list after parsing
                 parsed_data = json.loads(json_text)
                 if isinstance(parsed_data, (dict, list)):
                     return parsed_data
                 else:
                      self.logger.warning(f"Permissive search found JSON-like text but result was not dict/list: {type(parsed_data)}")
            except json.JSONDecodeError:
                 self.logger.warning(f"Permissive search found JSON-like text but failed parse: {json_text[:100]}...")

        self.logger.warning(f"Failed to find/parse valid JSON in text: {text[:150]}...")
        return None # Failed to parse

    def _create_run_data_struct(self, run_id: str, test_case_id: str, cloud_llm_id: str, edge_llm_id: str, hw_profile: str) -> Dict[str, Any]:
        """Creates the initial dictionary structure for a single test run results."""
        return {
            "id": run_id,
            "timestamp": datetime.now().isoformat(),
            "test_case_id": test_case_id,
            "cloud_llm_model_id": cloud_llm_id,
            "edge_llm_model_id": edge_llm_id,
            "hardware_profile": hw_profile,
            "run_1": {"status": "pending"},
            "run_2": {"status": "pending"},
            "run_3": {"status": "pending"},
            "run_4": {"status": "pending"}
        }

    def _create_analysis_summary(self, suite_id: str, run_count: int, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Creates a basic analysis summary dictionary (more detailed analysis in scripts)."""
        summary = {
            "test_suite_id": suite_id,
            "total_runs_attempted": run_count,
            "total_runs_logged": len(results),
            "runs_with_errors": 0,
            "runs_by_status": {
                "run_1": {"completed": 0, "failed": 0, "pending": 0},
                "run_2": {"completed": 0, "failed": 0, "pending": 0},
                "run_3": {"completed": 0, "failed": 0, "pending": 0},
                "run_4": {"completed": 0, "failed": 0, "pending": 0}
            }
        }
        
        errors = 0
        for res in results:
            # Count top-level errors
            if res.get("error"):
                errors += 1
            
            # Count run-specific statuses
            for run_key in ["run_1", "run_2", "run_3", "run_4"]:
                run_data = res.get(run_key, {})
                status = run_data.get("status", "pending")
                
                if status == "completed":
                    summary["runs_by_status"][run_key]["completed"] += 1
                elif status == "failed" or run_data.get("error"):
                    summary["runs_by_status"][run_key]["failed"] += 1
                    errors += 1
                else:
                    summary["runs_by_status"][run_key]["pending"] += 1
        
        summary["runs_with_errors"] = errors
        self.logger.info(f"Analysis Summary: Attempted={run_count}, Logged={len(results)}, Errors={errors}")
        
        return summary 

    def _verify_topic_consistency(self, run_data: Dict[str, Any], test_case: Dict[str, Any]) -> None:
        """
        Verify topic consistency across all runs and log the results.
        This helps identify when runs are not following the same topic.
        """
        self.logger.info("-- Topic Consistency Verification --")
        
        # Get the expected topic
        expected_topic = test_case.get("shared_teacher_request", {}).get("topic", 
                           test_case.get("variables", {}).get("topic", "unknown"))
        
        self.logger.info(f"Expected topic: {expected_topic}")
        
        # Extract the first 100 chars of generated questions for inspection
        for run_num in range(1, 5):
            run_key = f"run_{run_num}"
            if run_key in run_data:
                question_data = run_data[run_key].get("steps", {}).get("generated_question", {})
                question_text = question_data.get("llm_output", question_data.get("generated_text", ""))
                if question_text:
                    preview = question_text[:100].replace("\n", " ")
                    self.logger.info(f"{run_key} question preview: \"{preview}...\"")
        
        self.logger.info("-- End Verification --")

    def _log_and_return_error(self, message: str, exception: Optional[Exception] = None) -> Dict[str, str]:
        """Logs a critical error and returns an error dictionary for run_test_suite exit."""
        if exception:
             # Log full traceback for exceptions
             self.logger.critical(f"{message}: {exception}", exc_info=True)
             return {"error": f"{message}: {exception}"}
        else:
             self.logger.critical(message)
             return {"error": message}