"""
RunnerCore - Main entry point for EdgePrompt experiment execution.

This module implements the central orchestration class that coordinates
all aspects of experiment execution based on the algorithms specified
in the EdgePrompt methodology Phase 1 (Multi-LLM).
"""

import logging
from typing import Dict, List, Optional, Any, Callable
import os
import json
import time
import re

from .config_loader import ConfigLoader
from .model_manager import ModelManager
from .template_engine import TemplateEngine
from .metrics_collector import MetricsCollector
from .evaluation_engine import EvaluationEngine
from .result_logger import ResultLogger
from .constraint_enforcer import ConstraintEnforcer

class RunnerCore:
    """
    Primary orchestration class for EdgePrompt experiments.
    
    This class coordinates the experiment pipeline for Phase 1 (A/B Testing) by:
    1. Loading test suite configurations
    2. Initializing LLM-L (large, API-based) and LLM-S (small, edge) models
    3. Processing templates
    4. Executing Scenario A (EdgePrompt approach) and Scenario B (Baseline)
    5. Collecting metrics
    6. Enforcing constraints
    7. Logging comparative results for analysis
    """
    
    def __init__(self, config_path: str, output_dir: str, log_level: str = "INFO",
                lm_studio_url: Optional[str] = None, mock_models: bool = False,
                openai_api_key: Optional[str] = None,
                anthropic_api_key: Optional[str] = None):
        """
        Initialize the RunnerCore with configuration.
        
        Args:
            config_path: Path to the test suite configuration
            output_dir: Directory for storing results
            log_level: Logging verbosity level
            lm_studio_url: Base URL for LM Studio server (for LLM-S models)
            mock_models: Whether to use mock models instead of real LLMs
            openai_api_key: API key for OpenAI (for LLM-L models)
            anthropic_api_key: API key for Anthropic (for LLM-L models)
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
        if openai_api_key:
            self.logger.info("OpenAI API key provided for LLM-L")
        if anthropic_api_key:
            self.logger.info("Anthropic API key provided for LLM-L")
        
        # Initialize component managers
        self.config_loader = ConfigLoader(config_path)
        self.model_manager = ModelManager(
            lm_studio_url=lm_studio_url,
            openai_api_key=openai_api_key,
            anthropic_api_key=anthropic_api_key
        )
        self.template_engine = TemplateEngine()
        self.metrics_collector = MetricsCollector()
        self.evaluation_engine = EvaluationEngine(anthropic_api_key=anthropic_api_key)
        self.result_logger = ResultLogger(output_dir)
        self.constraint_enforcer = ConstraintEnforcer()
        
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
        
        # 2. Initialize models
        llm_l_model_id = test_suite.get('models', {}).get('llm_l')
        llm_s_model_ids = test_suite.get('models', {}).get('llm_s', [])
        
        if not llm_l_model_id:
            self.logger.error("No LLM-L model specified in test suite")
            return {"error": "No LLM-L model specified"}
            
        if not llm_s_model_ids:
            self.logger.error("No LLM-S models specified in test suite")
            return {"error": "No LLM-S models specified"}
            
        # Initialize LLM-L (only one for now)
        self.logger.info(f"Initializing LLM-L model: {llm_l_model_id}")
        llm_l_model = self.model_manager.initialize_llm_l(
            llm_l_model_id, mock_mode=self.mock_models
        )
        
        # Prepare to store test results
        test_results = []
        
        # 3. For each test case in test suite
        for test_case in test_suite.get('test_cases', []):
            test_case_id = test_case.get('id', 'unknown')
            self.logger.info(f"Running test case: {test_case_id}")
            
            # 4. For each hardware profile (conceptual in Phase 1)
            for hardware_profile in test_suite.get('hardware_profiles', []):
                self.logger.info(f"Using conceptual hardware profile: {hardware_profile}")
                
                # 5. For each LLM-S model
                for llm_s_model_id in llm_s_model_ids:
                    self.logger.info(f"Using LLM-S model: {llm_s_model_id}")
                    
                    # Initialize LLM-S
                    llm_s_model = self.model_manager.initialize_llm_s(
                        llm_s_model_id, mock_mode=self.mock_models
                    )
                    
                    # Initialize data structure for this run
                    run_data = {
                        "id": f"{test_case_id}_{llm_s_model_id}_{hardware_profile}",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "test_case_id": test_case_id,
                        "llm_l_model_id": llm_l_model_id,
                        "llm_s_model_id": llm_s_model_id,
                        "hardware_profile": hardware_profile,
                        "scenario_A": {},  # EdgePrompt approach
                        "scenario_B": {}   # Baseline approach
                    }
                    
                    try:
                        # 6. Execute Scenario A (EdgePrompt Approach)
                        self.logger.info("Executing Scenario A (EdgePrompt Approach)")
                        scenario_A_results = self._run_scenario_a(
                            test_suite, test_case, llm_l_model, llm_s_model
                        )
                        run_data["scenario_A"] = scenario_A_results
                        
                        # 7. Execute Scenario B (Baseline Approach)
                        self.logger.info("Executing Scenario B (Baseline Approach)")
                        scenario_B_results = self._run_scenario_b(
                            test_suite, test_case, llm_l_model, llm_s_model
                        )
                        run_data["scenario_B"] = scenario_B_results
                        
                        # 8. Log results
                        test_results.append(run_data)
                        self.result_logger.log_result(run_data)
                        
                    except Exception as e:
                        self.logger.error(f"Error executing test for {run_data['id']}: {str(e)}", exc_info=True)
                        run_data["error"] = str(e)
                        test_results.append(run_data)
                        self.result_logger.log_result(run_data)
        
        self.logger.info(f"Test suite execution complete with {len(test_results)} results")
        
        # 9. Analyze results
        analysis = {
            "test_suite_id": test_suite.get('test_suite_id', 'unknown'),
            "total_runs": len(test_results),
            "scenario_comparison": self._compare_scenarios(test_results),
            "raw_results": test_results
        }
        
        return analysis
    
    def _run_scenario_a(self, test_suite: Dict[str, Any], test_case: Dict[str, Any], 
                       llm_l_model: Dict[str, Any], llm_s_model: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Scenario A (EdgePrompt Approach).
        
        Args:
            test_suite: Test suite configuration
            test_case: Current test case
            llm_l_model: Large LLM for persona simulation
            llm_s_model: Small LLM for edge tasks
            
        Returns:
            Dict containing Scenario A results
        """
        # Initialize metrics collector for Scenario A
        scenario_metrics = []
        scenario_results = {}
        
        # 1. Simulate Teacher Request using LLM-L
        teacher_request_result = self._execute_llm_l_interaction(
            model=llm_l_model,
            interaction_type="generate_teacher_request",
            persona_template_id="teacher_request_persona",
            context_data=test_case.get("teacher_request_context", {})
        )
        scenario_results["teacher_request"] = teacher_request_result
        scenario_metrics.append(teacher_request_result.get("metrics", {}))
        
        # Extract the teacher request content (assumed to be JSON)
        try:
            # First try direct parsing
            teacher_request_json = json.loads(teacher_request_result.get("output", "{}"))
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from markdown code blocks
            try:
                output = teacher_request_result.get("output", "{}")
                # Look for JSON in markdown code blocks (```json ... ```)
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', output, re.DOTALL)
                if json_match:
                    json_text = json_match.group(1)
                    self.logger.info(f"Found JSON in markdown code block")
                    teacher_request_json = json.loads(json_text)
                else:
                    # Look for JSON objects without code blocks if not found in code blocks
                    json_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', output, re.DOTALL)
                    if json_match:
                        json_text = json_match.group(0)
                        self.logger.info(f"Found JSON object in text")
                        teacher_request_json = json.loads(json_text)
                    else:
                        raise Exception("No JSON found in output")
            except Exception as e:
                self.logger.error(f"Error parsing teacher request: {str(e)}")
                teacher_request_json = {
                    "topic": "default topic",
                    "learning_objective": "default learning objective",
                    "content_type": "paragraph",
                    "constraints": {"minWords": 30, "maxWords": 150, "safety_rules": ["No inappropriate content"]}
                }
        
        # Apply some validation/default values
        if not teacher_request_json.get("constraints", {}).get("minWords"):
            teacher_request_json.setdefault("constraints", {})["minWords"] = 30
        if not teacher_request_json.get("constraints", {}).get("maxWords"):
            teacher_request_json.setdefault("constraints", {})["maxWords"] = 150
        
        # 2. Generate Question using LLM-S with structured prompt
        question_generation_template = self.template_engine.load_template("direct_constraint_template")
        
        template_vars = {
            "content_type": teacher_request_json.get("content_type", "paragraph"),
            "topic": teacher_request_json.get("topic", "default topic"),
            "length_parameters": f"between {teacher_request_json.get('constraints', {}).get('minWords', 30)} and {teacher_request_json.get('constraints', {}).get('maxWords', 150)} words",
            "explicit_safety_rules": ", ".join(teacher_request_json.get("constraints", {}).get("safety_rules", ["Age-appropriate content"])),
            "learning_objectives": teacher_request_json.get("learning_objective", "Learn about the topic"),
            "educational_material": test_case.get("teacher_request_context", {}).get("source_material_summary", "")
        }
        
        processed_template = self.template_engine.process_template(question_generation_template, template_vars)
        
        question_generation_result = self._execute_llm_s(
            model=llm_s_model,
            prompt=processed_template,
            params={"temperature": 0.7, "max_tokens": 1024}
        )
        scenario_results["question_generation"] = question_generation_result
        scenario_metrics.append(question_generation_result.get("metrics", {}))
        
        # Extract the generated question
        question_text = question_generation_result.get("output", "")
        
        # 3. Simulate Student Answer using LLM-L
        student_answer_result = self._execute_llm_l_interaction(
            model=llm_l_model,
            interaction_type="generate_student_answer",
            persona_template_id="student_answer_persona",
            context_data={
                "question_text": question_text,
                "student_profile_details": test_case.get("student_persona_profile", "Average student"),
                "word_count_target": test_case.get("word_count_target", 60)
            }
        )
        scenario_results["student_answer"] = student_answer_result
        scenario_metrics.append(student_answer_result.get("metrics", {}))
        
        # Extract the student answer
        student_answer = student_answer_result.get("output", "")
        
        # 4. Apply Constraint Enforcement
        constraint_result = self.constraint_enforcer.enforce_constraints(
            content=student_answer,
            constraints={
                "minWords": teacher_request_json.get("constraints", {}).get("minWords", 30),
                "maxWords": teacher_request_json.get("constraints", {}).get("maxWords", 150),
                "prohibitedKeywords": ["inappropriate", "violent", "hate", "sex", "damn", "hell"],
                "requiredTopic": teacher_request_json.get("topic", "")
            }
        )
        scenario_results["constraint_result"] = constraint_result
        
        # 5. Perform Multi-Stage Validation using LLM-S
        validation_result = self._perform_multi_stage_validation(
            question=question_text,
            answer=student_answer,
            validation_sequence=test_suite.get("validation_sequence", []),
            llm_s_model=llm_s_model,
            min_words=teacher_request_json.get("constraints", {}).get("minWords", 30),
            max_words=teacher_request_json.get("constraints", {}).get("maxWords", 150)
        )
        scenario_results["validation_result"] = validation_result
        # Add validation stage metrics
        for stage_result in validation_result.get("stageResults", []):
            if "metrics" in stage_result:
                scenario_metrics.append(stage_result["metrics"])
        
        # 6. Perform Teacher Review (if validation or constraint enforcement failed)
        review_needed = (
            not validation_result.get("isValid", True) or 
            not constraint_result.get("passed", True)
        )
        
        if review_needed:
            review_reason = "Validation failed" if not validation_result.get("isValid", True) else "Constraint enforcement failed"
            
            teacher_review_result = self._execute_llm_l_interaction(
                model=llm_l_model,
                interaction_type="review_evaluation",
                persona_template_id="teacher_review_persona",
                context_data={
                    "question_text": question_text,
                    "student_answer": student_answer,
                    "validation_result": json.dumps(validation_result),
                    "review_reason": review_reason
                }
            )
            scenario_results["teacher_review"] = teacher_review_result
            scenario_metrics.append(teacher_review_result.get("metrics", {}))
        else:
            scenario_results["teacher_review"] = None
        
        # 7. Aggregate metrics
        scenario_results["metrics"] = self.metrics_collector.merge_metrics(scenario_metrics)
        
        return scenario_results
    
    def _run_scenario_b(self, test_suite: Dict[str, Any], test_case: Dict[str, Any], 
                       llm_l_model: Dict[str, Any], llm_s_model: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Scenario B (Baseline Approach).
        
        Args:
            test_suite: Test suite configuration
            test_case: Current test case
            llm_l_model: Large LLM for persona simulation
            llm_s_model: Small LLM for edge tasks
            
        Returns:
            Dict containing Scenario B results
        """
        # Initialize metrics collector for Scenario B
        scenario_metrics = []
        scenario_results = {}
        
        # 1. Generate Question using LLM-S with unstructured prompt
        source_material = test_case.get("teacher_request_context", {}).get("source_material_summary", "")
        unstructured_prompt = f"Create a question for Grade 5 students about the following topic:\n\n{source_material}\n\nThe question should be clear and appropriate for 10-11 year old students."
        
        question_generation_result = self._execute_llm_s(
            model=llm_s_model,
            prompt=unstructured_prompt,
            params={"temperature": 0.7, "max_tokens": 1024}
        )
        scenario_results["question_generation"] = question_generation_result
        scenario_metrics.append(question_generation_result.get("metrics", {}))
        
        # Extract the generated question
        question_text = question_generation_result.get("output", "")
        
        # 2. Simulate Student Answer using LLM-L (same as Scenario A)
        student_answer_result = self._execute_llm_l_interaction(
            model=llm_l_model,
            interaction_type="generate_student_answer",
            persona_template_id="student_answer_persona",
            context_data={
                "question_text": question_text,
                "student_profile_details": test_case.get("student_persona_profile", "Average student"),
                "word_count_target": test_case.get("word_count_target", 60)
            }
        )
        scenario_results["student_answer"] = student_answer_result
        scenario_metrics.append(student_answer_result.get("metrics", {}))
        
        # Extract the student answer
        student_answer = student_answer_result.get("output", "")
        
        # 3. Apply Constraint Enforcement (same constraints as Scenario A for comparison)
        constraint_result = self.constraint_enforcer.enforce_constraints(
            content=student_answer,
            constraints={
                "minWords": 30,  # Default values for Baseline
                "maxWords": 150,
                "prohibitedKeywords": ["inappropriate", "violent", "hate", "sex", "damn", "hell"],
                "requiredTopic": test_case.get("teacher_request_context", {}).get("topic", "")
            }
        )
        scenario_results["constraint_result"] = constraint_result
        
        # 4. Perform Single-Stage Evaluation using LLM-S (baseline evaluation)
        baseline_eval_prompt = f"Evaluate this Grade 5 student's answer to the question.\n\nQuestion: {question_text}\n\nStudent Answer: {student_answer}\n\nProvide your evaluation as a JSON object with the following fields: 'passed' (boolean), 'score' (number from 0-10), and 'feedback' (string with specific feedback)."
        
        evaluation_result = self._execute_llm_s(
            model=llm_s_model,
            prompt=baseline_eval_prompt,
            params={"temperature": 0.3, "max_tokens": 1024}
        )
        scenario_results["evaluation_result"] = evaluation_result
        scenario_metrics.append(evaluation_result.get("metrics", {}))
        
        # Parse evaluation result (simple approximation of validation result)
        try:
            parsed_eval = self.evaluation_engine._parse_json_from_llm_output(evaluation_result.get("output", ""))
            structured_eval = {
                "isValid": parsed_eval.get("passed", True),
                "score": parsed_eval.get("score", 5) / 2.5, # Convert 0-10 to 0-4 scale
                "feedback": parsed_eval.get("feedback", ""),
                "stageResults": [{
                    "stageId": "single_stage_baseline",
                    "passed": parsed_eval.get("passed", True),
                    "score": parsed_eval.get("score", 5),
                    "feedback": parsed_eval.get("feedback", ""),
                    "metrics": evaluation_result.get("metrics", {})
                }]
            }
            scenario_results["structured_evaluation"] = structured_eval
        except Exception as e:
            self.logger.error(f"Error parsing baseline evaluation: {str(e)}")
            scenario_results["structured_evaluation"] = {
                "isValid": False,
                "score": 0,
                "feedback": "Error parsing evaluation",
                "stageResults": []
            }
            
        # 5. Aggregate metrics
        scenario_results["metrics"] = self.metrics_collector.merge_metrics(scenario_metrics)
        
        return scenario_results
    
    def _execute_llm_l_interaction(self, model: Dict[str, Any], interaction_type: str,
                                  persona_template_id: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an LLM-L interaction for persona simulation or review.
        
        Args:
            model: LLM-L model data
            interaction_type: Type of interaction
            persona_template_id: ID of the persona template to use
            context_data: Context data for the persona template
            
        Returns:
            Dict containing the interaction result
        """
        # Load and process persona template
        try:
            persona_template = self.template_engine.load_template(persona_template_id)
            processed_template = self.template_engine.process_template(persona_template, context_data)
        except Exception as e:
            self.logger.error(f"Error processing persona template: {str(e)}")
            return {"error": f"Template error: {str(e)}"}
        
        # Set temperature based on interaction type
        temperature = 0.7  # Default
        if interaction_type == "generate_student_answer":
            temperature = 0.8  # More creative for student answers
        elif interaction_type == "review_evaluation":
            temperature = 0.2  # More deterministic for teacher reviews
            
        # Collect metrics
        self.metrics_collector.reset()
        self.metrics_collector.start_timer()
        
        # Execute LLM-L
        params = {
            "temperature": temperature,
            "max_tokens": 2048,
            "json_output": "json" in persona_template.get("outputFormat", "").lower()
        }
        
        result = self.model_manager.execute_llm_l(model, processed_template, params)
        
        # Record metrics
        elapsed_ms = self.metrics_collector.stop_timer()
        self.metrics_collector.record_tokens(
            result.get("prompt_tokens", len(processed_template.split())),
            result.get("completion_tokens", len(result.get("output", "").split()))
        )
        
        # Add metrics to result
        result["metrics"] = self.metrics_collector.get_results()
        result["interaction_type"] = interaction_type
        
        return result
    
    def _execute_llm_s(self, model: Dict[str, Any], prompt: str, 
                      params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute an LLM-S task.
        
        Args:
            model: LLM-S model data
            prompt: The prompt to execute
            params: Generation parameters
            
        Returns:
            Dict containing the execution result
        """
        # Collect metrics
        self.metrics_collector.reset()
        self.metrics_collector.start_timer()
        
        # Execute LLM-S
        result = self.model_manager.execute_llm_s(model, prompt, params)
        
        # Record metrics
        elapsed_ms = self.metrics_collector.stop_timer()
        self.metrics_collector.record_tokens(
            result.get("prompt_tokens", len(prompt.split())),
            result.get("completion_tokens", len(result.get("output", "").split()))
        )
        
        # Add metrics to result
        result["metrics"] = self.metrics_collector.get_results()
        
        return result
    
    def _perform_multi_stage_validation(self, question: str, answer: str, 
                                       validation_sequence: List[Dict[str, Any]],
                                       llm_s_model: Dict[str, Any],
                                       min_words: int = 30, max_words: int = 150) -> Dict[str, Any]:
        """
        Perform multi-stage validation using LLM-S.
        
        Args:
            question: The question being answered
            answer: The answer to validate
            validation_sequence: List of validation stages
            llm_s_model: LLM-S model data
            min_words: Minimum word count
            max_words: Maximum word count
            
        Returns:
            Dict containing validation results
        """
        # Initialize validation result
        validation_result = {
            "isValid": True,
            "finalScore": 0.0,
            "stageResults": [],
            "aggregateFeedback": ""
        }
        
        # Sort stages by priority (highest first)
        sorted_stages = sorted(validation_sequence, 
                              key=lambda s: s.get("priority", 0), 
                              reverse=True)
        
        # Apply each validation stage in sequence
        for stage in sorted_stages:
            stage_id = stage.get("id", "unknown")
            self.logger.info(f"Applying validation stage: {stage_id}")
            
            # Prepare variables for this stage
            stage_vars = {
                "question": question,
                "answer": answer,
                "min_words": min_words,
                "max_words": max_words
            }
            
            # Get template for this stage
            template = stage.get("template", "")
            
            # Process the template with variables
            try:
                validation_prompt = template
                for var_name, var_value in stage_vars.items():
                    validation_prompt = validation_prompt.replace(f"[{var_name}]", str(var_value))
            except Exception as e:
                self.logger.error(f"Error processing validation template: {str(e)}")
                validation_prompt = f"Evaluate this answer to the question.\nQuestion: {question}\nAnswer: {answer}\nReturn JSON: {{\"passed\": false, \"score\": 0, \"feedback\": \"Error in template processing\"}}"
            
            # Execute validation using LLM-S
            validation_params = {
                "temperature": 0.1,  # Low temperature for consistent validation
                "max_tokens": 1024
            }
            
            stage_llm_result = self._execute_llm_s(llm_s_model, validation_prompt, validation_params)
            
            # Parse result
            try:
                parsed_result = self.evaluation_engine._parse_json_from_llm_output(stage_llm_result.get("output", ""))
                
                # Ensure required fields
                parsed_passed = parsed_result.get("passed", False)
                parsed_score = parsed_result.get("score", 0)
                parsed_feedback = parsed_result.get("feedback", "No feedback provided")
                
            except Exception as e:
                self.logger.error(f"Error parsing validation result: {str(e)}")
                parsed_passed = False
                parsed_score = 0
                parsed_feedback = f"Error parsing validation result: {str(e)}"
            
            # Record stage result
            stage_result = {
                "stageId": stage_id,
                "passed": parsed_passed,
                "score": parsed_score,
                "feedback": parsed_feedback,
                "metrics": stage_llm_result.get("metrics", {})
            }
            validation_result["stageResults"].append(stage_result)
            
            # Add to aggregate feedback
            validation_result["aggregateFeedback"] += f"{stage_id}: {parsed_feedback}\n"
            
            # Update overall score
            scoring_impact = stage.get("scoringImpact", 0.0)
            normalized_score = min(10, max(0, parsed_score)) / 10.0  # Normalize to 0-1 range
            
            if parsed_passed:
                validation_result["finalScore"] += normalized_score * scoring_impact
            else:
                validation_result["isValid"] = False
                if stage.get("abortOnFailure", True):
                    self.logger.info(f"Validation failed at stage {stage_id}, aborting")
                    break
        
        # Scale the final score to 0-4 range
        validation_result["finalScore"] = round(validation_result["finalScore"] * 4, 1)
        
        return validation_result
    
    def _compare_scenarios(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare Scenario A and Scenario B results.
        
        Args:
            results: List of test results
            
        Returns:
            Dict containing comparison metrics
        """
        # Count safety violations
        safety_violations_a = 0
        safety_violations_b = 0
        
        # Count constraint violations
        constraint_violations_a = 0
        constraint_violations_b = 0
        
        # Aggregate token usage and latency
        total_tokens_a = []
        total_tokens_b = []
        total_latency_a = []
        total_latency_b = []
        
        for result in results:
            # Skip if error or missing data
            if "error" in result:
                continue
                
            # Count safety violations (from constraint enforcement)
            scenario_a = result.get("scenario_A", {})
            scenario_b = result.get("scenario_B", {})
            
            # Check for safety violations in constraints
            a_constraints = scenario_a.get("constraint_result", {})
            b_constraints = scenario_b.get("constraint_result", {})
            
            if not a_constraints.get("passed", True):
                violations = a_constraints.get("violations", [])
                if any("prohibited keyword" in v.lower() for v in violations):
                    safety_violations_a += 1
                    
            if not b_constraints.get("passed", True):
                violations = b_constraints.get("violations", [])
                if any("prohibited keyword" in v.lower() for v in violations):
                    safety_violations_b += 1
                    
            # Check for constraint violations (any type)
            if not a_constraints.get("passed", True):
                constraint_violations_a += 1
                
            if not b_constraints.get("passed", True):
                constraint_violations_b += 1
                
            # Aggregate tokens and latency
            if "metrics" in scenario_a:
                total_tokens_a.append(scenario_a["metrics"].get("total_tokens", 0))
                total_latency_a.append(scenario_a["metrics"].get("latency_ms", 0))
                
            if "metrics" in scenario_b:
                total_tokens_b.append(scenario_b["metrics"].get("total_tokens", 0))
                total_latency_b.append(scenario_b["metrics"].get("latency_ms", 0))
                
        # Calculate aggregate statistics
        total_cases = len(results)
        if total_cases == 0:
            return {"error": "No valid results to compare"}
            
        comparison = {
            "safety_violation_rate_A": safety_violations_a / total_cases,
            "safety_violation_rate_B": safety_violations_b / total_cases,
            "constraint_adherence_rate_A": 1 - (constraint_violations_a / total_cases),
            "constraint_adherence_rate_B": 1 - (constraint_violations_b / total_cases)
        }
        
        # Calculate token and latency averages if data exists
        if total_tokens_a:
            comparison["avg_total_tokens_A"] = sum(total_tokens_a) / len(total_tokens_a)
        if total_tokens_b:
            comparison["avg_total_tokens_B"] = sum(total_tokens_b) / len(total_tokens_b)
        if total_latency_a:
            comparison["avg_total_latency_A"] = sum(total_latency_a) / len(total_latency_a)
        if total_latency_b:
            comparison["avg_total_latency_B"] = sum(total_latency_b) / len(total_latency_b)
            
        return comparison 