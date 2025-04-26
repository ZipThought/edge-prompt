"""
EvaluationEngine - Handles evaluation of model outputs.

This module provides functionality for evaluating model outputs
against expected results and validation criteria, using both
edge LLMs (via multi-stage validation) and external LLMs (Anthropic Claude).
"""

import logging
import json
import time
from typing import Dict, Any, List, Optional, Union, Callable

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Local application imports
from .template_engine import TemplateEngine
from .metrics_collector import MetricsCollector
from .json_utils import parse_llm_json_output, repair_json_with_llm

class EvaluationEngine:
    """
    Evaluates model outputs against validation criteria.
    
    This class implements the MultiStageValidation algorithm from the EdgePrompt
    methodology, handling:
    - Multi-stage validation sequences using edge LLMs
    - Proxy evaluation using Anthropic Claude
    - Result scoring and feedback collection
    - Structured output parsing
    """
    
    def __init__(self, template_engine: TemplateEngine, metrics_collector: MetricsCollector,
                 anthropic_api_key: Optional[str] = None):
        """
        Initialize the EvaluationEngine.
        
        Args:
            template_engine: Instance of TemplateEngine for processing validation prompts.
            metrics_collector: Instance of MetricsCollector for proxy evaluation timing.
            anthropic_api_key: API key for Anthropic Claude (for evaluation_with_llm_proxy)
        """
        self.logger = logging.getLogger("edgeprompt.runner.evaluation")
        self.template_engine = template_engine
        self.metrics_collector = metrics_collector
        self.anthropic_api_key = anthropic_api_key
        self._anthropic_client = None # Lazy initialization
        
        if not ANTHROPIC_AVAILABLE:
            self.logger.warning("Anthropic package not available - LLM Proxy evaluation disabled. Install with 'pip install anthropic>=0.20.0'")
        elif not self.anthropic_api_key:
             self.logger.warning("Anthropic API key not provided - LLM Proxy evaluation disabled.")
        
        self.logger.info("EvaluationEngine initialized")
    
    def _get_anthropic_client(self):
        """Lazily initializes and returns the Anthropic client."""
        if not ANTHROPIC_AVAILABLE: return None
        if self._anthropic_client is None:
            if not self.anthropic_api_key:
                 self.logger.warning("Cannot initialize Anthropic client: API key missing.")
                 return None
            try:
                self._anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
            except Exception as e:
                self.logger.error(f"Failed to initialize Anthropic client: {e}")
                return None
        return self._anthropic_client

    def validate_result(self, question: str, answer: str, 
                       validation_sequence: List[Dict[str, Any]],
                       edge_llm_execute_func: Callable[[Dict[str, Any], str, Optional[Dict[str, Any]]], Dict[str, Any]],
                       llm_s_model_data: Dict[str, Any] # Pass the initialized model data
                       ) -> Dict[str, Any]:
        """
        Apply a validation sequence using an Edge LLM (LLM-S).
        Implements PROMPT_ENGINEERING.md, Sec 2.3: MultiStageValidation Algorithm.
        
        Args:
            question: The original question prompt content.
            answer: The model-generated answer content to validate.
            validation_sequence: List of validation stage objects from the config.
            edge_llm_execute_func: Callable that executes the LLM-S model 
                                     (e.g., ModelManager.execute_llm_s).
            llm_s_model_data: The initialized model data dictionary for the LLM-S model.
            
        Returns:
            Dict containing validation results: {isValid, finalScore, stageResults, aggregateFeedback, metrics}.
        """
        if not validation_sequence:
             self.logger.warning("Empty validation sequence provided.")
             return {"isValid": True, "finalScore": 0.0, "stageResults": [], "aggregateFeedback": "", "metrics": {}}

        self.logger.info(f"Starting multi-stage validation with {len(validation_sequence)} stages.")

        # Initialize overall result structure
        validation_result = {
            "isValid": True,
            "finalScore": 0.0,
            "stageResults": [],
            "aggregateFeedback": "",
            "total_validation_metrics": {} # To store aggregated metrics
        }
        all_stage_metrics = []

        # Sort stages by priority (descending, higher first)
        # Default priority to 0 if missing
        sorted_stages = sorted(validation_sequence, key=lambda s: s.get("priority", 0), reverse=True)

        # 3. For each stage in sorted sequence
        for stage in sorted_stages:
            stage_id = stage.get("id", "unknown_stage")
            self.logger.debug(f"Running validation stage: {stage_id}")

            # 3a. Prepare stage variables
            stage_vars = {'question': question, 'answer': answer}
            # Add any other vars needed by specific stage templates if defined in stage config (e.g. min_words)
            # stage_vars.update(stage.get("template_variables", {}))

            # 3b. Process the stage template
            template_name = stage.get("template")
            if not template_name:
                 self.logger.error(f"Validation stage {stage_id} is missing 'template' key.")
                 # CRASH on critical validation errors instead of continuing
                 raise ValueError(f"VALIDATION ERROR: Stage {stage_id} is missing 'template' key. Aborting validation.")

            validation_prompt, _ = self.template_engine.process_template(template_name, stage_vars)
            if validation_prompt is None:
                 self.logger.error(f"Failed to process template '{template_name}' for stage {stage_id}.")
                 # CRASH on template processing failure
                 raise ValueError(f"VALIDATION ERROR: Failed to process template '{template_name}' for stage {stage_id}. Aborting validation.")

            # 3c. Execute LLM-S validation step
            # Parameters for validation: low temp, ensure JSON output if template requests it
            generation_params = {
                "temperature": 0.1,
                "max_tokens": 512, # Allow enough tokens for JSON + feedback
                "response_format": {"type": "json_object"} # Request JSON output
            }

            try:
                # Call the passed execution function
                llm_s_result = edge_llm_execute_func(llm_s_model_data, validation_prompt, generation_params)

                # 3d. Robustly parse the result
                if llm_s_result.get("error"):
                     raise RuntimeError(f"LLM-S execution error: {llm_s_result['error']}")

                generated_text = llm_s_result.get("generated_text", "")
                parsed_stage_data = self._parse_json_from_llm_output(generated_text)

                # Get metrics from the LLM result
                stage_metrics = llm_s_result.get("metrics", {})
                all_stage_metrics.append(stage_metrics)

            except Exception as e:
                self.logger.error(f"Error executing or parsing validation stage {stage_id}: {e}", exc_info=True)
                # CRASH on execution error
                raise RuntimeError(f"VALIDATION ERROR: Failed to execute validation stage {stage_id}: {e}")

            # 3f. Record stage result (aligning with spec structure)
            stage_output = {
                "stageId": stage_id,
                "passed": parsed_stage_data.get("passed", False),
                "score": parsed_stage_data.get("score", 0.0), # Expecting 0-1 score
                "feedback": parsed_stage_data.get("feedback", ""),
                "metrics": stage_metrics
                # Add raw output for debugging?
                # "raw_output": generated_text
            }
            validation_result["stageResults"].append(stage_output)

            # 3g. Append feedback
            if stage_output["feedback"]:
                validation_result["aggregateFeedback"] += f"[{stage_id}] {stage_output['feedback']}\n"

            current_stage_passed = stage_output["passed"]
            current_stage_score = stage_output["score"]
            scoring_impact = stage.get("scoringImpact", 0.0)

            # 3h, 3i. Update overall validity and score
            if not current_stage_passed:
                validation_result["isValid"] = False
                # Apply scoring impact even on failure (e.g., could be negative impact)
                # Assuming score is 0 if passed is false
                validation_result["finalScore"] += (0.0 * scoring_impact) # Or adjust based on failure severity if needed

                abort_on_failure = stage.get("abortOnFailure", True) # Default to aborting
                if abort_on_failure:
                    self.logger.warning(f"Validation failed at stage {stage_id} and abortOnFailure=True. Stopping sequence.")
                    break # Exit loop
            else:
                 # Passed: Add weighted score (assuming score is 0-1)
                 validation_result["finalScore"] += (current_stage_score * scoring_impact)

        # Normalize final score? The spec is unclear. Let's assume the sum of scoringImpacts defines the max score.
        # For now, we just sum weighted scores. Clamping to a range might be needed.
        # max_possible_score = sum(s.get("scoringImpact", 0.0) for s in validation_sequence if s.get("scoringImpact", 0.0) > 0)
        # Clamp score between 0 and max_possible_score (or 1 if normalized later)
        # validation_result["finalScore"] = max(0.0, min(validation_result["finalScore"], max_possible_score)) 

        # Aggregate metrics from all stages run
        validation_result["total_validation_metrics"] = self.metrics_collector.merge_metrics(all_stage_metrics)

        self.logger.info(f"Multi-stage validation complete. Overall Valid: {validation_result['isValid']}, Final Score: {validation_result['finalScore']:.2f}")
        return validation_result
    
    def _parse_json_from_llm_output(self, text: str) -> Dict[str, Any]:
        """
        Robustly extracts and parses JSON from LLM output text.
        Searches for JSON in markdown blocks or direct text.
        Validates presence of expected keys: passed (bool), score (float/int), feedback (str).
        
        Args:
            text: Raw LLM output text.
            
        Returns:
            Parsed JSON as dict, or raises ValueError if parsing fails.
        """
        # Use our centralized JSON parsing utility
        required_keys = ["passed", "score", "feedback"]
        default_values = {
            "passed": False,
            "score": 0.5,
            "feedback": "Failed to parse validation result."
        }
        
        # If input is empty or not a string, we can't parse it
        if not text or not isinstance(text, str) or text.strip() == "":
            self.logger.warning("Received empty or non-string output for JSON parsing.")
            raise ValueError("VALIDATION ERROR: Received empty output for JSON parsing.")
        
        self.logger.debug(f"Parsing JSON from output (first 100 chars): {text[:100]}...")
        
        # Use the centralized parsing function
        result = parse_llm_json_output(text, required_keys, default_values)
        
        # We'll maintain the previous behavior of crashing on parse failure to maintain
        # compatibility with existing error handling in _step_multistage_validation_edge
        if not result or not all(k in result for k in required_keys):
            self.logger.warning(f"Could not parse valid JSON with required keys from output: {text[:100]}...")
            raise ValueError(f"VALIDATION ERROR: Could not extract valid JSON with required keys from output: {text[:100]}...")
            
        return result
    
    def evaluate_with_llm_proxy(self, content_to_evaluate: str, 
                              reference_criteria: str,
                              evaluation_role: str = "expert teacher",
                              model_id: str = "claude-3-haiku-20240307") -> Dict[str, Any]:
        """
        Use Anthropic Claude as a proxy for evaluation (e.g., Teacher Review step).
        
        Args:
            content_to_evaluate: The text content to be evaluated.
            reference_criteria: The criteria or rubric for evaluation.
            evaluation_role: The persona the LLM should adopt (e.g., 'expert teacher').
            model_id: The Anthropic model ID to use.
            
        Returns:
            Dictionary containing the evaluation result (e.g., score, feedback, passed) and metrics.
        """
        self.logger.info(f"Performing LLM proxy evaluation using {model_id}")
        client = self._get_anthropic_client()
        if not client:
            return {"error": "Anthropic client not available or not initialized.", "metrics": {}}

        # Construct prompt for evaluation
        prompt = f"""
You are an {evaluation_role}. Evaluate the following content based on the provided criteria.

CRITERIA:
{reference_criteria}

CONTENT TO EVALUATE:
{content_to_evaluate}

Provide your evaluation in JSON format with the following keys:
- "passed": boolean (true if content meets core criteria, false otherwise)
- "score": float (a score from 0.0 to 1.0 representing overall quality based on criteria)
- "feedback": string (detailed feedback explaining the score and decision)
"""

        # Execute API call using MetricsCollector
        result = {"error": "Evaluation failed before API call.", "metrics": {}}
        try:
            self.metrics_collector.start_timer()
            response = client.messages.create(
                model=model_id,
                max_tokens=1024,
                temperature=0.2, # Low temp for objective evaluation
                messages=[{"role": "user", "content": prompt}]
            )
            self.metrics_collector.stop_timer()

            output_text = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            self.metrics_collector.record_tokens(input_tokens, output_tokens)

            # Parse the JSON response
            parsed_evaluation = self._parse_json_from_llm_output(output_text)
            result = {
                **parsed_evaluation, # Includes passed, score, feedback
                 "metrics": self.metrics_collector.get_results(),
                 "raw_output": output_text # Include raw for debugging
            }

        except Exception as e:
            self.logger.error(f"Error during LLM proxy evaluation: {e}", exc_info=True)
            if self.metrics_collector.start_time:
                 self.metrics_collector.stop_timer() # Ensure timer stops on error
            result = {
                "error": str(e),
                 "passed": False,
                 "score": 0.0,
                 "feedback": f"LLM proxy evaluation failed: {e}",
                 "metrics": self.metrics_collector.get_results()
            }

        self.logger.info(f"LLM proxy evaluation complete. Passed: {result.get('passed')}, Score: {result.get('score')}")
        return result 

    def validate_with_sequence(self, question: str, answer: str, 
                            context: Optional[Dict[str, Any]],
                            validation_sequence_id: str,
                            llm_executor: Callable[[str, Optional[Dict[str, Any]]], Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply a validation sequence using an Edge LLM (LLM-S) by loading the sequence from its ID.
        This is a wrapper around validate_result that first loads the validation sequence.
        
        Args:
            question: The original question prompt content.
            answer: The model-generated answer content to validate.
            context: The context data (e.g., teacher request containing constraints/rubric).
            validation_sequence_id: ID of the validation sequence to load.
            llm_executor: Callable that executes the LLM model with a prompt and params.
            
        Returns:
            Dict containing validation results: {isValid, finalScore, stageResults, aggregateFeedback, metrics}.
        """
        self.logger.info(f"Loading validation sequence: {validation_sequence_id}")
        
        # Load the validation sequence configuration
        validation_sequence_config = self.template_engine.config_loader.load_validation_sequence(validation_sequence_id)
        
        if not validation_sequence_config:
            error_msg = f"Could not load validation sequence: {validation_sequence_id}"
            self.logger.error(error_msg)
            return {"error": error_msg, "isValid": False, "finalScore": 0.0, "stageResults": [], "aggregateFeedback": error_msg}
        
        # Extract the stages from the configuration
        validation_stages = validation_sequence_config.get("stages", [])
        
        if not validation_stages:
            error_msg = f"Validation sequence '{validation_sequence_id}' has no stages"
            self.logger.error(error_msg)
            return {"error": error_msg, "isValid": False, "finalScore": 0.0, "stageResults": [], "aggregateFeedback": error_msg}
        
        self.logger.info(f"Loaded validation sequence '{validation_sequence_id}' with {len(validation_stages)} stages")
        
        # Collect metrics from all validation stages
        all_metrics = []
        
        # Sort stages by priority (descending, higher first)
        # Default priority to 0 if missing
        sorted_stages = sorted(validation_stages, key=lambda s: s.get("priority", 0), reverse=True)
        
        # Initialize overall result structure
        validation_result = {
            "isValid": True,
            "finalScore": 0.0,
            "stageResults": [],
            "aggregateFeedback": "",
            "metrics": {}  # To store aggregated metrics
        }
        
        # Process each validation stage
        for stage in sorted_stages:
            stage_id = stage.get("id", "unknown_stage")
            self.logger.debug(f"Running validation stage: {stage_id}")
            
            # Prepare stage variables
            stage_vars = {
                'question': question, 
                'answer': answer
            }
            
            # Add context variables if available
            if context:
                stage_vars.update(context)
            
            # Get the template ID for this stage
            template_id = stage.get("template_id")
            if not template_id:
                error_msg = f"Validation stage {stage_id} is missing 'template_id'"
                self.logger.error(error_msg)
                continue  # Skip this stage
            
            # Process the template
            try:
                # Fix: Process_template returns a tuple of (prompt, metadata)
                prompt_tuple = self.template_engine.process_template(template_id, stage_vars)
                
                # Extract just the prompt from the tuple
                if prompt_tuple is None or prompt_tuple[0] is None:
                    # Handle case where template processing failed
                    error_msg = f"Failed to process template '{template_id}' for stage {stage_id}: {prompt_tuple[1].get('error', 'Unknown error')}"
                    self.logger.error(error_msg)
                    validation_result["stageResults"].append({
                        "stageId": stage_id,
                        "passed": False,
                        "error": error_msg,
                        "feedback": f"Technical error: {error_msg}"
                    })
                    validation_result["aggregateFeedback"] += f"[{stage_id}] Technical error: {error_msg}\n"
                    validation_result["isValid"] = False
                    continue  # Skip this stage
                
                validation_prompt = prompt_tuple[0]
                self.logger.debug(f"Processed template for stage {stage_id}, prompt length: {len(validation_prompt)}")
            except Exception as e:
                self.logger.error(f"Failed to process template '{template_id}' for stage {stage_id}: {e}")
                validation_result["stageResults"].append({
                    "stageId": stage_id,
                    "passed": False,
                    "error": str(e),
                    "feedback": f"Technical error: {str(e)}"
                })
                validation_result["aggregateFeedback"] += f"[{stage_id}] Technical error: {str(e)}\n"
                validation_result["isValid"] = False
                continue  # Skip this stage
            
            # Execute LLM for validation
            # Parameters for validation: low temp, ensure JSON output
            params = {
                "temperature": 0.1,
                "max_tokens": 512,  # Allow enough tokens for JSON + feedback
                "response_format": {"type": "json_object"}  # Request JSON output
            }
            
            try:
                # Call the executor function
                llm_result = llm_executor(validation_prompt, params)
                
                # Extract metrics
                stage_metrics = llm_result.get("metrics", {})
                all_metrics.append(stage_metrics)
                
                # Parse the result
                generated_text = llm_result.get("generated_text", "")
                parsed_result = self._parse_json_from_llm_output(generated_text)
                
                # Check if parsing succeeded
                if not parsed_result:
                    error_msg = f"Failed to parse JSON result from stage {stage_id}"
                    self.logger.error(error_msg)
                    validation_result["stageResults"].append({
                        "stageId": stage_id,
                        "passed": False,
                        "error": error_msg,
                        "feedback": f"Technical error: {error_msg}"
                    })
                    validation_result["aggregateFeedback"] += f"[{stage_id}] Technical error: {error_msg}\n"
                    validation_result["isValid"] = False
                    continue  # Skip this stage
                
                # Record stage result
                stage_result = {
                    "stageId": stage_id,
                    "passed": parsed_result.get("passed", False),
                    "score": parsed_result.get("score", 0.0),
                    "feedback": parsed_result.get("feedback", ""),
                    "metrics": stage_metrics
                }
                
                validation_result["stageResults"].append(stage_result)
                
                # Add feedback to aggregate feedback
                if stage_result["feedback"]:
                    validation_result["aggregateFeedback"] += f"[{stage_id}] {stage_result['feedback']}\n"
                
                # Update overall validity and score
                stage_weight = stage.get("weight", 1.0)
                if not stage_result["passed"]:
                    validation_result["isValid"] = False
                    # Apply weight to score (0 for failed stages)
                    validation_result["finalScore"] += 0.0
                    
                    # Check if we should abort on failure
                    if validation_sequence_config.get("abortOnFailure", True):
                        self.logger.warning(f"Validation failed at stage {stage_id} and abortOnFailure=True. Stopping sequence.")
                        break
                else:
                    # Add weighted score
                    validation_result["finalScore"] += (stage_result["score"] * stage_weight)
            
            except Exception as e:
                self.logger.error(f"Error in validation stage {stage_id}: {e}", exc_info=True)
                validation_result["isValid"] = False
                validation_result["stageResults"].append({
                    "stageId": stage_id,
                    "passed": False,
                    "error": str(e),
                    "feedback": f"Technical error: {str(e)}"
                })
                
                # Update aggregate feedback
                validation_result["aggregateFeedback"] += f"[{stage_id}] Technical error: {str(e)}\n"
                
                # Check if we should abort on failure
                if validation_sequence_config.get("abortOnFailure", True):
                    break
        
        # Normalize the final score if needed
        # Get total weight of all stages
        total_weight = sum(stage.get("weight", 1.0) for stage in sorted_stages)
        if total_weight > 0:
            validation_result["finalScore"] = validation_result["finalScore"] / total_weight
        
        # Check if the score meets the passing threshold
        passing_threshold = validation_sequence_config.get("passing_threshold", 0.6)
        if validation_result["finalScore"] < passing_threshold:
            validation_result["isValid"] = False
        
        # Merge all metrics
        validation_result["metrics"] = self.metrics_collector.merge_metrics([m for m in all_metrics if m])
        
        return validation_result 