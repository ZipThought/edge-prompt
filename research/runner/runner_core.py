"""
RunnerCore - Main entry point for EdgePrompt experiment execution.

Implements the central orchestration class coordinating Phase 1 (Multi-LLM A/B testing)
based on the TestOrchestrationPhase1MultiLLM algorithm specified in
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
    Orchestrates EdgePrompt Phase 1 experiments (A/B Testing).

    Implements the TestOrchestrationPhase1MultiLLM algorithm (PROMPT_ENGINEERING.md, Sec 2.7).
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
            lm_studio_url: Base URL for LM Studio server (if used for LLM-S).
            mock_models: If True, use mock models instead of real LLMs.
            openai_api_key: API key for OpenAI (LLM-L).
            anthropic_api_key: API key for Anthropic (LLM-L and Proxy Evaluation).
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
        Follows TestOrchestrationPhase1MultiLLM algorithm (PROMPT_ENGINEERING.md, Sec 2.7).
        
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

        # --- Algorithm Step 2: Initialize LLM-L ---
        llm_l_model_id = test_suite.get('models', {}).get('llm_l')
        llm_s_model_ids = test_suite.get('models', {}).get('llm_s', [])

        if not llm_l_model_id:
             return self._log_and_return_error("No LLM-L model specified in test suite.")
        if not llm_s_model_ids:
             return self._log_and_return_error("No LLM-S models specified in test suite.")

        try:
             self.logger.info(f"Initializing LLM-L model: {llm_l_model_id}")
             llm_l_model_data = self.model_manager.initialize_llm_l(
                 llm_l_model_id, mock_mode=self.mock_models
             )
        except Exception as e:
            return self._log_and_return_error(f"Failed to initialize LLM-L model {llm_l_model_id}", e)

        # --- Algorithm Steps 3-10: Loop through Cases/Profiles/Models ---
        test_suite_results = []
        run_counter = 0

        for test_case in test_suite.get('test_cases', []):
            test_case_id = test_case.get('id', f'unknown_case_{run_counter}')
            self.logger.info(f"--- Running Test Case: {test_case_id} ---")

            # Hardware profiles are conceptual labels in Phase 1
            for hardware_profile in test_suite.get('hardware_profiles', ["sim_unconstrained"]):
                 self.logger.debug(f"Using conceptual hardware profile: {hardware_profile}")

                 for llm_s_model_id in llm_s_model_ids:
                     self.logger.info(f"--- Using LLM-S model: {llm_s_model_id} ---")
                     run_counter += 1
                     # Create unique run ID including suite, case, model, profile, counter
                     run_id = f"{suite_id}_{test_case_id}_{llm_s_model_id}_{hardware_profile}_{run_counter}"
                     run_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', run_id) # Sanitize ID

                     # Initialize LLM-S for this specific run configuration
                     try:
                         llm_s_model_data = self.model_manager.initialize_llm_s(
                             llm_s_model_id, mock_mode=self.mock_models
                         )
                     except Exception as e:
                         self.logger.error(f"Failed to initialize LLM-S model {llm_s_model_id} for run {run_id}", exc_info=True)
                         run_data = self._create_run_data_struct(run_id, test_case_id, llm_l_model_id, llm_s_model_id, hardware_profile)
                         run_data["error"] = f"LLM-S Initialization Failed: {e}"
                         test_suite_results.append(run_data)
                         self.result_logger.log_result(run_data)
                         continue # Skip to next LLM-S model

                     # Prepare run data structure
                     run_data = self._create_run_data_struct(run_id, test_case_id, llm_l_model_id, llm_s_model_id, hardware_profile)

                     try:
                         # --- Steps 6-8: Execute Scenario A (EdgePrompt) ---
                         self.logger.info(f"[Run {run_id}] Executing Scenario A...")
                         run_data["scenario_A"] = self._run_scenario_a(
                             test_suite, test_case, llm_l_model_data, llm_s_model_data
                         )

                         # --- Step 9: Execute Scenario B (Baseline) ---
                         self.logger.info(f"[Run {run_id}] Executing Scenario B...")
                         run_data["scenario_B"] = self._run_scenario_b(
                             test_suite, test_case, llm_l_model_data, llm_s_model_data
                         )

                     except Exception as e:
                         self.logger.error(f"Critical error during scenario execution for run {run_id}", exc_info=True)
                         run_data["error"] = f"Scenario Execution Failed: {e}"
                     finally:
                          # --- Step 10: Log Result ---
                          test_suite_results.append(run_data)
                          self.result_logger.log_result(run_data)
                          self.logger.info(f"[Run {run_id}] Completed and logged.")

        # --- Cleanup: Unload models (optional) ---
        self.model_manager.unload_model(llm_l_model_id, model_type="llm_l")
        for llm_s_id in llm_s_model_ids:
            self.model_manager.unload_model(llm_s_id, model_type="llm_s")

        self.logger.info(f"=== Test Suite Execution Complete. Total runs logged: {len(test_suite_results)} ===")

        # --- Step 11: Analyze Results (Basic Summary) ---
        # Detailed analysis is performed by the analyze_results.py script.
        # This provides a quick summary log.
        analysis_summary = self._create_analysis_summary(suite_id, run_counter, test_suite_results)
        self.result_logger.log_aggregate_results(test_suite_results, f"{suite_id}_raw_results")
        self.result_logger.log_aggregate_results(analysis_summary, f"{suite_id}_analysis_summary")

        return analysis_summary # Return summary, raw results are in files

    # --- Scenario Execution Methods ---

    def _run_scenario_a(self, test_suite: Dict[str, Any], test_case: Dict[str, Any],
                       llm_l_model_data: Dict[str, Any], llm_s_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes Scenario A (EdgePrompt) steps based on TestOrchestrationPhase1MultiLLM (Sec 2.7).
        Uses helper methods for clarity. Returns results including aggregated metrics.
        """
        scenario_A_results = {"status": "started", "steps": {}}
        all_metrics = [] # Collect metrics dict from each step

        try:
            # Step 8a: Simulate Teacher Request (LLM-L)
            teacher_request_result = self._step_a_teacher_request(test_case, llm_l_model_data)
            scenario_A_results["steps"]["teacher_request"] = teacher_request_result
            all_metrics.append(teacher_request_result.get("metrics"))
            if teacher_request_result.get("error"): raise RuntimeError(f"Teacher Request failed: {teacher_request_result['error']}")
            teacher_request_content = teacher_request_result["parsed_content"] # Assume helper includes parsing

            # Step 8b: Generate Question (LLM-S)
            question_result = self._step_a_generate_question(teacher_request_content, test_case, llm_s_model_data)
            scenario_A_results["steps"]["generated_question"] = question_result
            all_metrics.append(question_result.get("metrics"))
            if question_result.get("error"): raise RuntimeError(f"Generate Question failed: {question_result['error']}")
            question_text = question_result.get("generated_text")
            if not question_text: raise ValueError("Generated question text is empty.")


            # Step 8c: Simulate Student Answer (LLM-L)
            student_answer_result = self._step_a_student_answer(question_text, teacher_request_content, test_case, llm_l_model_data)
            scenario_A_results["steps"]["student_answer"] = student_answer_result
            all_metrics.append(student_answer_result.get("metrics"))
            if student_answer_result.get("error"): raise RuntimeError(f"Student Answer failed: {student_answer_result['error']}")
            student_answer_text = student_answer_result.get("llm_output")
            if not student_answer_text: raise ValueError("Simulated student answer text is empty.")


            # Step 8d: Multi-Stage Validation (LLM-S)
            multi_stage_validation_result = self._step_a_multistage_validation(question_text, student_answer_text, teacher_request_content, llm_s_model_data)
            scenario_A_results["steps"]["multi_stage_validation"] = multi_stage_validation_result
            # Metrics are aggregated *within* multi_stage_validation_result["total_validation_metrics"]
            all_metrics.append(multi_stage_validation_result.get("total_validation_metrics"))
            if multi_stage_validation_result.get("error"): raise RuntimeError(f"Multi-Stage Validation failed: {multi_stage_validation_result['error']}")


            # Step 8e: Constraint Enforcement (Orchestrator)
            constraint_result = self._step_a_constraint_enforcement(student_answer_text, teacher_request_content)
            scenario_A_results["steps"]["constraint_enforcement"] = constraint_result

            # Step 8f: Simulate Teacher Review (LLM-L, Optional)
            teacher_review_result = self._step_a_teacher_review(
                multi_stage_validation_result, constraint_result,
                question_text, student_answer_text, llm_l_model_data
            )
            scenario_A_results["steps"]["teacher_review"] = teacher_review_result
            if teacher_review_result and teacher_review_result.get("metrics"): # Review is optional
                 all_metrics.append(teacher_review_result.get("metrics"))
            # Handle potential error from review step if it occurred
            if teacher_review_result and teacher_review_result.get("error"):
                self.logger.warning(f"Teacher Review step encountered an error: {teacher_review_result['error']}")
                # Decide if this should halt scenario A? For now, just log.


            # Step 8g: Store Final Results
            scenario_A_results["final_decision"] = {
                "passed_validation": multi_stage_validation_result.get("isValid"),
                "passed_constraints": constraint_result.get("passed"),
                "final_score": multi_stage_validation_result.get("finalScore")
            }
            scenario_A_results["status"] = "completed"

        except Exception as e:
             self.logger.error(f"Error executing Scenario A steps: {e}", exc_info=True)
             scenario_A_results["status"] = "failed"
             scenario_A_results["error"] = f"Scenario A Failed: {e}"

        # Aggregate all metrics collected during Scenario A
        # Filter out None values in case a step failed before producing metrics
        scenario_A_results["total_metrics"] = self.metrics_collector.merge_metrics([m for m in all_metrics if m])
        return scenario_A_results

    def _run_scenario_b(self, test_suite: Dict[str, Any], test_case: Dict[str, Any],
                       llm_l_model_data: Dict[str, Any], llm_s_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes Scenario B (Baseline) steps based on TestOrchestrationPhase1MultiLLM (Sec 2.7).
        Uses helper methods for clarity. Returns results including aggregated metrics.
        """
        scenario_B_results = {"status": "started", "steps": {}}
        all_metrics = [] # Collect metrics dict from each step

        try:
            # Step 9a: Generate Question (LLM-S, Unstructured)
            question_result = self._step_b_generate_question(test_case, llm_s_model_data)
            scenario_B_results["steps"]["generated_question"] = question_result
            all_metrics.append(question_result.get("metrics"))
            if question_result.get("error"): raise RuntimeError(f"Baseline Question Generation failed: {question_result['error']}")
            question_text = question_result.get("generated_text")
            if not question_text: raise ValueError("Generated baseline question text is empty.")


            # Step 9b: Simulate Student Answer (LLM-L)
            student_answer_result = self._step_b_student_answer(question_text, test_case, llm_l_model_data)
            scenario_B_results["steps"]["student_answer"] = student_answer_result
            all_metrics.append(student_answer_result.get("metrics"))
            if student_answer_result.get("error"): raise RuntimeError(f"Baseline Student Answer failed: {student_answer_result['error']}")
            student_answer_text = student_answer_result.get("llm_output")
            if not student_answer_text: raise ValueError("Simulated baseline student answer text is empty.")


            # Step 9c: Perform Baseline Evaluation (LLM-S, Single Stage)
            baseline_eval_result = self._step_b_baseline_evaluation(question_text, student_answer_text, test_suite, llm_s_model_data)
            scenario_B_results["steps"]["baseline_evaluation"] = baseline_eval_result
            all_metrics.append(baseline_eval_result.get("metrics"))
            # Extract parsed data, handle potential errors during eval/parsing
            parsed_eval = baseline_eval_result.get("parsed_evaluation", {"passed": False, "score": 0.0}) # Default if parsing failed
            if baseline_eval_result.get("error"):
                 self.logger.warning(f"Baseline evaluation step failed: {baseline_eval_result['error']}")
                 # Overwrite parsed eval if the step itself failed
                 parsed_eval = {"passed": False, "score": 0.0, "feedback": "Evaluation step failed"}


            # Step 9d: Constraint Enforcement (Orchestrator)
            constraint_result = self._step_b_constraint_enforcement(student_answer_text, test_case)
            scenario_B_results["steps"]["constraint_enforcement"] = constraint_result

            # Step 9e: Store Final Results
            scenario_B_results["final_decision"] = {
                # Use parsed evaluation result for baseline pass/fail
                "passed_evaluation": parsed_eval.get("passed"),
                "passed_constraints": constraint_result.get("passed"),
                "final_score": parsed_eval.get("score") # Use baseline eval score
            }
            scenario_B_results["status"] = "completed"

        except Exception as e:
             self.logger.error(f"Error executing Scenario B steps: {e}", exc_info=True)
             scenario_B_results["status"] = "failed"
             scenario_B_results["error"] = f"Scenario B Failed: {e}"

        # Aggregate all metrics collected during Scenario B
        scenario_B_results["total_metrics"] = self.metrics_collector.merge_metrics([m for m in all_metrics if m])
        return scenario_B_results


    # --- Scenario A Helper Methods ---

    def _step_a_teacher_request(self, test_case: Dict[str, Any], llm_l_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Scenario A, Step 8a: Simulate Teacher Request (LLM-L)."""
        self.logger.debug("[A:8a] Simulating Teacher Request...")
        teacher_req_ctx = test_case.get("teacher_request_context", {})
        # Assume template name defined in test suite or default
        # Ensure template exists. Use a known default.
        teacher_req_template = test_case.get("teacher_request_template", "teacher_request_persona")

        result = self._execute_llm_l_interaction(
            model_data=llm_l_model_data,
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
                 self.logger.warning(f"Failed to parse valid teacher request JSON from LLM-L output for template {teacher_req_template}. Output: {result.get('llm_output')}")
                 result["error"] = result.get("error", "") + " Failed to parse valid teacher request JSON."
                 parsed_content = None # Ensure it's None on failure
             else:
                 self.logger.debug("Parsed teacher request successfully.")

        result["parsed_content"] = parsed_content # Add parsed content (or None)
        return result

    def _step_a_generate_question(self, teacher_request: Optional[Dict[str, Any]], test_case: Dict[str, Any], llm_s_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Scenario A, Step 8b: Generate Question (LLM-S)."""
        self.logger.debug("[A:8b] Generating Question using LLM-S...")
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

        # Execute LLM-S call
        result = self._execute_llm_s(
             llm_s_model_data, prompt, params={"temperature": 0.7} # Allow some creativity
        )
        self.logger.debug(f"Generated question text (first 50): {result.get('generated_text', '')[:50]}...")
        return result

    def _step_a_student_answer(self, question_text: Optional[str], teacher_request: Optional[Dict[str, Any]], test_case: Dict[str, Any], llm_l_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Scenario A, Step 8c: Simulate Student Answer (LLM-L)."""
        self.logger.debug("[A:8c] Simulating Student Answer...")
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
        result = self._execute_llm_l_interaction(
            model_data=llm_l_model_data,
            interaction_type="generate_student_answer",
            persona_template_id=student_answer_template,
            context_data=student_context
        )
        self.logger.debug(f"Simulated student answer (first 50): {result.get('llm_output', '')[:50]}...")
        return result

    def _step_a_multistage_validation(self, question: Optional[str], answer: Optional[str], teacher_request: Optional[Dict[str, Any]], llm_s_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Scenario A, Step 8d: Perform Multi-Stage Validation (LLM-S)."""
        self.logger.debug("[A:8d] Performing Multi-Stage Validation...")
        default_error_result = {"error": "Missing input", "isValid": False, "finalScore": 0.0, "stageResults": [], "aggregateFeedback": "", "total_validation_metrics": {}}
        if not question or not answer: return {**default_error_result, "error": "Missing question or answer text."}
        if not teacher_request: teacher_request = {} # Handle missing teacher request gracefully

        # Determine validation sequence: from teacher request or default
        validation_sequence_name = teacher_request.get("validation_sequence_id", "basic_validation_sequence")

        # Load the sequence definition using the dedicated load_validation_sequence method
        validation_sequence_config = self.config_loader.load_validation_sequence(validation_sequence_name)
        if not validation_sequence_config or "stages" not in validation_sequence_config:
             error_msg = f"Failed to load or invalid validation sequence: {validation_sequence_name}"
             self.logger.error(error_msg)
             return {**default_error_result, "error": error_msg, "aggregateFeedback": error_msg}

        validation_stages = validation_sequence_config.get("stages", [])

        # Delegate to EvaluationEngine using a wrapper for the LLM-S execution function
        def llm_s_executor_wrapper(prompt: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
            # This inner function calls the actual ModelManager method
            return self.model_manager.execute_llm_s(llm_s_model_data, prompt, params)

        result = self.evaluation_engine.validate_result(
             question=question,
             answer=answer,
             validation_sequence=validation_stages,
             edge_llm_execute_func=llm_s_executor_wrapper,
             llm_s_model_data=llm_s_model_data # Pass model context
        )
        self.logger.debug(f"Multi-stage validation complete. Valid: {result.get('isValid')}, Score: {result.get('finalScore')}")
        return result

    def _step_a_constraint_enforcement(self, student_answer: Optional[str], teacher_request: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Scenario A, Step 8e: Constraint Enforcement (Orchestrator)."""
        self.logger.debug("[A:8e] Performing Constraint Enforcement...")
        if not student_answer:
            return {"passed": False, "violations": ["Cannot enforce constraints: Student answer missing."]}
        if not teacher_request: teacher_request = {} # Handle missing teacher request gracefully

        # Get constraints primarily from the parsed teacher request
        constraints_to_enforce = teacher_request.get("constraints", {})
        if not isinstance(constraints_to_enforce, dict):
            self.logger.warning(f"Constraints from teacher request were not a dictionary: {constraints_to_enforce}. Using empty constraints.")
            constraints_to_enforce = {}

        # OPTIONAL: Also consider adding constraints from the original template's answerSpace if needed
        # question_gen_template_name = teacher_request.get("question_template_id", "direct_constraint_template")
        # template_def = self.config_loader.load_template(question_gen_template_name)
        # if template_def and 'answerSpace' in template_def and isinstance(template_def['answerSpace'], dict):
        #     # Be careful how you merge - teacher constraints might override template defaults
        #     merged_constraints = {**template_def['answerSpace'], **constraints_to_enforce}
        #     constraints_to_enforce = merged_constraints

        result = self.constraint_enforcer.enforce_constraints(
            content=student_answer,
            constraints=constraints_to_enforce
        )
        self.logger.debug(f"Constraint enforcement complete. Passed: {result.get('passed')}")
        return result

    def _step_a_teacher_review(self, validation_result: Dict[str, Any], constraint_result: Dict[str, Any], question: Optional[str], answer: Optional[str], llm_l_model_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Scenario A, Step 8f: Simulate Teacher Review (LLM-L, Optional)."""
        # Trigger review if validation OR constraints failed
        review_needed = not validation_result.get("isValid", True) or not constraint_result.get("passed", True)
        if not review_needed:
            self.logger.debug("[A:8f] Skipping Teacher Review (validation/constraints passed).")
            return {"status": "skipped (passed validation/constraints)"}
        if not question or not answer:
             self.logger.warning("[A:8f] Skipping Teacher Review: Missing question or answer.")
             return {"status": "skipped (missing question/answer)"}


        self.logger.info("[A:8f] Validation/Constraints failed, simulating Teacher Review...")
        # Prepare context for the review template
        review_context = {
             "question": question,
             "student_answer": answer,
             "validation_feedback": validation_result.get("aggregateFeedback", "N/A"),
             "constraint_violations": constraint_result.get("violations", [])
        }
        # Assume a standard review template exists
        review_template = "teacher_review_persona" # Needs to be defined in configs/templates

        result = self._execute_llm_l_interaction(
             model_data=llm_l_model_data,
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

    # --- Scenario B Helper Methods ---

    def _step_b_generate_question(self, test_case: Dict[str, Any], llm_s_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Scenario B, Step 9a: Generate Question (LLM-S, Unstructured)."""
        self.logger.debug("[B:9a] Generating Question (Unstructured)...")
        # Create a simple, unstructured prompt. Heuristic based on teacher context.
        teacher_req_ctx = test_case.get("teacher_request_context", {})
        topic = teacher_req_ctx.get("topic", "a relevant topic")
        objective = teacher_req_ctx.get("learning_objective", "explain something simply")
        # Infer grade level or use default if not specified
        grade_level = "Grade 5" # Default
        if isinstance(teacher_req_ctx.get("desired_constraints"), dict):
             grade_level = teacher_req_ctx["desired_constraints"].get("safety", grade_level)

        unstructured_prompt = f"Generate a single, clear question about '{topic}' suitable for {grade_level}. The question should relate to the objective: {objective}."

        result = self._execute_llm_s(
             llm_s_model_data, unstructured_prompt, params={"temperature": 0.7}
        )
        self.logger.debug(f"Generated baseline question (first 50): {result.get('generated_text', '')[:50]}...")
        return result

    def _step_b_student_answer(self, question_text: Optional[str], test_case: Dict[str, Any], llm_l_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Scenario B, Step 9b: Simulate Student Answer (LLM-L). (Identical logic to A)."""
        self.logger.debug("[B:9b] Simulating Student Answer...")
        if not question_text:
            return {"error": "Cannot simulate baseline answer: Generated question text is missing.", "metrics": {}}

        student_answer_template = test_case.get("student_answer_template", "student_answer_persona")
        student_context = {
             "question_text": question_text,
             "student_profile_details": test_case.get("student_persona_profile", "Average student."),
             # No specific word count target easily available for baseline
        }
        result = self._execute_llm_l_interaction(
            model_data=llm_l_model_data,
            interaction_type="generate_student_answer",
            persona_template_id=student_answer_template,
            context_data=student_context
        )
        self.logger.debug(f"Simulated baseline student answer (first 50): {result.get('llm_output', '')[:50]}...")
        return result

    def _step_b_baseline_evaluation(self, question: Optional[str], answer: Optional[str],
                                   test_suite: Dict[str, Any], llm_s_model_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform baseline evaluation using a simple LLM-S prompt.
        Corresponds to Step 9c in TestOrchestrationPhase1MultiLLM.
        """
        self.logger.debug("[B:9c] Performing Baseline Evaluation...")
        step_result = {"status": "skipped", "passed": False, "score": 0.0, "feedback": ""}

        if not question or not answer:
            step_result["error"] = "Missing question or answer for evaluation."
            return step_result

        # --- Corrected Template Name Usage ---
        # Directly use the expected template name, checking if it was listed in the suite
        baseline_eval_template_name = "baseline_eval_persona"
        if baseline_eval_template_name not in test_suite.get("templates", []):
             self.logger.error(f"Required template '{baseline_eval_template_name}' not listed in test suite templates.")
             step_result["error"] = f"Template '{baseline_eval_template_name}' missing from suite config."
             return step_result
        # --- End Correction ---

        # Get evaluation criteria from the test case
        eval_criteria = test_suite.get("test_cases", [{}])[0].get("evaluation_criteria", {})
        criteria_str = json.dumps(eval_criteria, indent=2)

        context_data = {
            "question_text": question,
            "student_answer": answer,
            "evaluation_criteria": criteria_str
        }

        # Execute evaluation, requesting JSON output
        result = self._execute_llm_s(
             llm_s_model_data,
             criteria_str,
             params={"temperature": 0.1, "response_format": {"type": "json_object"}}
        )

        # Parse the result (assuming similar format to validation stages for comparison)
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

    def _step_b_constraint_enforcement(self, student_answer: Optional[str], test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Scenario B, Step 9d: Constraint Enforcement (Orchestrator)."""
        self.logger.debug("[B:9d] Performing Constraint Enforcement (using A's constraints for comparison)...")
        if not student_answer:
             return {"passed": False, "violations": ["Cannot enforce constraints: Baseline answer missing."]}

        # Attempt to apply the *same* constraints defined for Scenario A for fair comparison.
        # These likely originate from the teacher_request_context in the test case config.
        constraints_to_enforce = test_case.get("teacher_request_context", {}).get("desired_constraints", {})
        if not constraints_to_enforce or not isinstance(constraints_to_enforce, dict):
             # Fallback if desired_constraints not found or invalid in test case config
             self.logger.warning("Could not determine Scenario A constraints for Scenario B enforcement comparison. Using defaults.")
             constraints_to_enforce = { "minWords": 30, "maxWords": 200, "prohibitedKeywords": ["inappropriate", "violent"]} # Example fallback

        result = self.constraint_enforcer.enforce_constraints(
            content=student_answer,
            constraints=constraints_to_enforce
        )
        self.logger.debug(f"Baseline constraint enforcement complete. Passed: {result.get('passed')}")
        return result


    # --- Core LLM Execution Helpers ---

    def _execute_llm_l_interaction(self, model_data: Dict[str, Any], interaction_type: str,
                                  persona_template_id: str, context_data: Dict[str, Any],
                                  expected_output_format: Optional[str] = None) -> Dict[str, Any]:
        """
        Helper to execute an interaction with LLM-L using a persona template.
        Handles template processing and calls ModelManager.
        Aligns with LLM_L_Interaction Algorithm (Sec 2.6). Returns full result dict.
        """
        self.logger.debug(f"Executing LLM-L Interaction: {interaction_type} using template {persona_template_id}")

        # 1 & 2: Process Persona Prompt Template
        prompt, metadata = self.template_engine.process_template(persona_template_id, context_data)
        if prompt is None:
            error_msg = f"Failed to process persona template '{persona_template_id}': {metadata.get('error', 'Unknown')}"
            self.logger.error(error_msg)
            # Return structure consistent with ModelManager failure
            return {"error": error_msg, "llm_output": None, "metrics": {}}

        # 3 & 4: Execute LLM-L Inference via ModelManager
        params = {"temperature": 0.7} # Default temp
        if interaction_type == "review_evaluation": params["temperature"] = 0.2 # More objective review
        if expected_output_format == "json":
            params["response_format"] = {"type": "json_object"}

        result = self.model_manager.execute_llm_l(model_data, prompt, params)
        # Result structure: {llm_output, input_tokens, output_tokens, metrics, error?}
        result["interaction_type"] = interaction_type # Add interaction type for context
        self.logger.debug(f"LLM-L Interaction '{interaction_type}' complete. Error: {result.get('error')}")
        return result

    def _execute_llm_s(self, model_data: Dict[str, Any], prompt: str,
                      params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Helper to execute a task with LLM-S via ModelManager.
        Aligns with EdgeLLMExecution Algorithm (Sec 2.5). Returns full result dict.
        """
        self.logger.debug(f"Executing LLM-S task (prompt len {len(prompt)})... Params: {params}")
        if not prompt:
             self.logger.error("LLM-S execution requested with empty prompt.")
             return {"error": "Empty prompt provided to LLM-S.", "generated_text": None, "metrics": {}}
        result = self.model_manager.execute_llm_s(model_data, prompt, params)
        # Result structure: {generated_text, input_tokens, output_tokens, metrics, error?}
        self.logger.debug(f"LLM-S task complete. Error: {result.get('error')}")
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

    def _create_run_data_struct(self, run_id: str, test_case_id: str, llm_l_id: str, llm_s_id: str, hw_profile: str) -> Dict[str, Any]:
        """Creates the initial dictionary structure for a single test run results."""
        return {
            "id": run_id,
            "timestamp": datetime.now().isoformat(),
            "test_case_id": test_case_id,
            "llm_l_model_id": llm_l_id,
            "llm_s_model_id": llm_s_id,
            "hardware_profile": hw_profile,
            "scenario_A": {"status": "pending"},
            "scenario_B": {"status": "pending"}
        }

    def _create_analysis_summary(self, suite_id: str, run_count: int, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Creates a basic analysis summary dictionary (more detailed analysis in scripts)."""
        summary = {
            "test_suite_id": suite_id,
            "total_runs_attempted": run_count,
            "total_runs_logged": len(results),
            "runs_with_errors": 0,
            # Add more summary stats if needed here
        }
        errors = 0
        for res in results:
            # Count top-level errors or errors within scenarios
            if res.get("error") or res.get("scenario_A", {}).get("error") or res.get("scenario_B", {}).get("error"):
                errors += 1
        summary["runs_with_errors"] = errors
        self.logger.info(f"Analysis Summary: Attempted={run_count}, Logged={len(results)}, Errors={errors}")
        # Note: Detailed comparison logic moved to analyze_results.py
        return summary 

    def _log_and_return_error(self, message: str, exception: Optional[Exception] = None) -> Dict[str, str]:
        """Logs a critical error and returns an error dictionary for run_test_suite exit."""
        if exception:
             # Log full traceback for exceptions
             self.logger.critical(f"{message}: {exception}", exc_info=True)
             return {"error": f"{message}: {exception}"}
        else:
             self.logger.critical(message)
             return {"error": message}

# Note: Removed the internal _compare_scenarios method.
# Complex comparison logic is delegated to the dedicated analysis script (`analyze_results.py`)
# to keep RunnerCore focused on orchestration.