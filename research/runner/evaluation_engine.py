"""
EvaluationEngine - Handles evaluation of model outputs.

This module provides functionality for evaluating model outputs
against expected results and validation criteria, using both
edge LLMs (via multi-stage validation) and external LLMs (Anthropic Claude).
"""

import logging
import json
import time
import re
from typing import Dict, Any, List, Optional, Union, Callable

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

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
    
    def __init__(self, anthropic_api_key: Optional[str] = None):
        """
        Initialize the EvaluationEngine.
        
        Args:
            anthropic_api_key: API key for Anthropic Claude (for evaluation_with_llm_proxy)
        """
        self.logger = logging.getLogger("edgeprompt.runner.evaluation")
        self.anthropic_api_key = anthropic_api_key
        
        if not ANTHROPIC_AVAILABLE:
            self.logger.warning("Anthropic package not available - Install with 'pip install anthropic>=0.20.0'")
        
        self.logger.info("EvaluationEngine initialized")
    
    def validate_result(self, question: str, answer: str, 
                       validation_sequence: List[Dict[str, Any]],
                       edge_llm_engine_func: Callable) -> Dict[str, Any]:
        """
        Apply a validation sequence to a model result using edge LLM.
        
        Args:
            question: The original question
            answer: The model-generated answer to validate
            validation_sequence: List of validation stages to apply
            edge_llm_engine_func: Function to call the edge LLM for validation
            
        Returns:
            Dict containing validation results
        """
        self.logger.info(f"Validating result with {len(validation_sequence)} validation stages")
        
        # Initialize validation result
        validation_result = {
            "isValid": True,
            "score": 0,
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
                "answer": answer
            }
            
            # Get template for this stage
            template = stage.get("template", "")
            
            # Construct validation prompt
            # In a real implementation, this would use TemplateEngine.process_template
            validation_prompt = template.replace("[question]", question).replace("[answer]", answer)
            
            # Execute validation using the provided LLM function
            try:
                # Generate parameters focused on deterministic output
                generation_params = {
                    "temperature": 0.1,  # Low temperature for consistent validation
                    "max_tokens": 500    # Enough for structured output
                }
                
                # Call the edge LLM
                start_time = time.time()
                validation_response = edge_llm_engine_func(
                    validation_prompt, 
                    generation_params
                )
                execution_time_ms = int((time.time() - start_time) * 1000)
                
                # Extract output text
                output = validation_response.get("output", "")
                
                # Parse JSON from the output
                stage_result = self._parse_json_from_llm_output(output)
                
                # Add execution time
                stage_result["executionTime"] = execution_time_ms
                
            except Exception as e:
                self.logger.error(f"Error in validation stage {stage_id}: {str(e)}", exc_info=True)
                stage_result = {
                    "passed": False,
                    "score": 0,
                    "feedback": f"Validation error: {str(e)}",
                    "executionTime": 0
                }
            
            # Record stage result
            validation_result["stageResults"].append({
                "stageId": stage_id,
                "passed": stage_result.get("passed", False),
                "score": stage_result.get("score", 0),
                "feedback": stage_result.get("feedback", ""),
                "executionTime": stage_result.get("executionTime", 0)
            })
            
            # Add to aggregate feedback
            if "feedback" in stage_result and stage_result["feedback"]:
                validation_result["aggregateFeedback"] += f"{stage_id}: {stage_result['feedback']}\n"
            
            # Update overall score
            scoring_impact = stage.get("scoringImpact", 0.0)
            normalized_score = stage_result.get("score", 0) / 10.0  # Normalize to 0-1
            validation_result["score"] += normalized_score * scoring_impact
            
            # If stage failed and abort_on_failure is set, mark as invalid and break
            if not stage_result.get("passed", False) and stage.get("abortOnFailure", True):
                validation_result["isValid"] = False
                self.logger.info(f"Validation failed at stage {stage_id}")
                break
        
        # Scale the final score appropriately (default 0-4)
        validation_result["score"] = round(validation_result["score"] * 4, 1)
        
        self.logger.info(f"Validation completed. Valid: {validation_result['isValid']}, Score: {validation_result['score']}")
        
        return validation_result
    
    def _parse_json_from_llm_output(self, text: str) -> Dict[str, Any]:
        """
        Attempt to extract and parse JSON from LLM output text.
        
        Args:
            text: Raw LLM output text
            
        Returns:
            Parsed JSON as dict or default error dict
        """
        # Default values if parsing fails
        default_result = {
            "passed": False,
            "score": 0,
            "feedback": "Failed to parse validation result"
        }
        
        if not text:
            return default_result
            
        try:
            # First, try direct JSON parsing (if the entire output is JSON)
            return json.loads(text)
        except json.JSONDecodeError:
            # If direct parse fails, try to extract JSON using regex
            try:
                # Look for JSON objects within markdown code blocks
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
                    
                # Look for JSON objects not in code blocks
                json_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
                    
                # If no JSON detected, try simpler patterns
                passed_match = re.search(r'passed["\s:]+\s*(true|false)', text, re.IGNORECASE)
                score_match = re.search(r'score["\s:]+\s*([0-9.]+)', text)
                feedback_match = re.search(r'feedback["\s:]+\s*"([^"]*)"', text)
                
                result = default_result.copy()
                if passed_match:
                    result["passed"] = passed_match.group(1).lower() == 'true'
                if score_match:
                    result["score"] = float(score_match.group(1))
                if feedback_match:
                    result["feedback"] = feedback_match.group(1)
                    
                return result
                
            except Exception as e:
                self.logger.error(f"Error parsing validation result: {str(e)}")
                return default_result
    
    def evaluate_with_llm_proxy(self, content_to_evaluate: str, 
                              reference_criteria: str,
                              evaluation_role: str = "expert teacher",
                              evaluation_llm_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluate content using Anthropic Claude as a proxy for human evaluation.
        
        This implements the StateOfTheArtEvaluation algorithm from the
        EdgePrompt methodology.
        
        Args:
            content_to_evaluate: The content to evaluate (e.g., generated answer)
            reference_criteria: Criteria or rubric for evaluation
            evaluation_role: Role definition for the evaluator (e.g., "Grade 5 teacher")
            evaluation_llm_config: Configuration options including API key
            
        Returns:
            Dict containing structured evaluation results
        """
        self.logger.info("Evaluating with external LLM (Anthropic Claude)")
        
        # Get API key from config or instance
        api_key = None
        if evaluation_llm_config and "anthropic_api_key" in evaluation_llm_config:
            api_key = evaluation_llm_config.get("anthropic_api_key")
        else:
            api_key = self.anthropic_api_key
            
        if not api_key:
            error_msg = "Missing Anthropic API key for evaluation"
            self.logger.error(error_msg)
            return {"error": error_msg}
            
        if not ANTHROPIC_AVAILABLE:
            error_msg = "Anthropic package not available"
            self.logger.error(error_msg)
            return {"error": error_msg}
            
        # Get model from config or use default
        model = "claude-3-5-sonnet-latest"  # Default model
        if evaluation_llm_config and "model" in evaluation_llm_config:
            model = evaluation_llm_config.get("model")
            
        # Start timing
        start_time = time.time()
        
        try:
            # Initialize Anthropic client
            client = anthropic.Anthropic(api_key=api_key)
            
            # Construct system prompt with role
            system_prompt = f"""You are an {evaluation_role} evaluating educational content.
Analyze the content based on the provided criteria.
Provide your assessment as a detailed JSON object with these fields:
- overall_score: numeric score from 0-10 (where 10 is perfect)
- criteria_scores: object mapping individual criteria to scores
- feedback: string with specific, constructive feedback
- strengths: array of content strengths  
- areas_for_improvement: array of suggested improvements
- is_valid: boolean indicating if content meets minimum requirements

YOUR RESPONSE MUST BE VALID JSON WITH NO ADDITIONAL TEXT BEFORE OR AFTER."""
            
            # Construct user prompt with content and criteria
            user_prompt = f"""CONTENT TO EVALUATE:
```
{content_to_evaluate}
```

EVALUATION CRITERIA:
```
{reference_criteria}
```

Please provide your evaluation as a JSON object."""
            
            # Make the API call
            self.logger.info(f"Calling Anthropic API with model {model}")
            response = client.messages.create(
                model=model,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent evaluation
                max_tokens=2000
            )
            
            # Extract response content
            response_text = response.content[0].text
            
            # Parse JSON from the response
            try:
                evaluation = self._parse_json_from_llm_output(response_text)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse Anthropic response as JSON: {str(e)}")
                self.logger.debug(f"Raw response: {response_text}")
                evaluation = {
                    "error": "Failed to parse response",
                    "raw_response": response_text
                }
                
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            evaluation["execution_time_ms"] = execution_time_ms
            
            self.logger.info(f"External evaluation complete in {execution_time_ms}ms")
            
            return evaluation
            
        except Exception as e:
            error_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Error in external evaluation: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return {
                "error": error_msg,
                "execution_time_ms": error_time_ms
            } 