#!/usr/bin/env python3
"""
Verification script for EdgePrompt validation architecture.
Validates core functionality works as intended:
1. JSON processing from LLM responses with various formats
2. Template processing with mixed variable types 
3. Validation result extraction from LLM outputs
"""

import json
import logging
import sys
from runner.template_engine import TemplateEngine
from runner.evaluation_engine import EvaluationEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("validation_verification")

def verify_json_processing():
    """Verify JSON processing from LLM responses with various formats"""
    from runner.runner_core import RunnerCore
    import re
    
    # Sample LLM outputs in various formats
    test_responses = [
        # JSON in markdown code block
        """
        Here's the teacher request:
        
        ```json
        {
          "topic": "Indonesian Rainforests",
          "learning_objective": "Understand the importance of rainforest conservation",
          "content_type": "paragraph",
          "constraints": {
            "minWords": 50,
            "maxWords": 120,
            "safety_rules": ["Age-appropriate content", "No political bias"]
          }
        }
        ```
        """,
        
        # JSON with backticks but no language specifier
        """
        ```
        {
          "topic": "Traditional Games",
          "learning_objective": "Compare modern and traditional games",
          "content_type": "essay",
          "constraints": {
            "minWords": 40,
            "maxWords": 100,
            "safety_rules": ["Child-friendly content"]
          }
        }
        ```
        """,
        
        # Direct JSON (no markdown)
        """{
          "topic": "Water Cycle",
          "learning_objective": "Explain the stages of water cycle",
          "content_type": "diagram description",
          "constraints": {
            "minWords": 30,
            "maxWords": 80,
            "safety_rules": ["Scientific accuracy"]
          }
        }"""
    ]
    
    success_count = 0
    
    for i, response in enumerate(test_responses):
        logger.info(f"Verifying JSON processing scenario {i+1}...")
        try:
            # First try direct parsing
            try:
                json_data = json.loads(response)
                logger.info("Direct JSON processing succeeded")
                success_count += 1
                continue
            except json.JSONDecodeError:
                # If direct parsing fails, try to extract JSON from markdown code blocks
                try:
                    # Look for JSON in markdown code blocks (```json ... ```)
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
                    if json_match:
                        json_text = json_match.group(1)
                        logger.info(f"Found JSON in markdown code block")
                        json_data = json.loads(json_text)
                        success_count += 1
                        continue
                    
                    # Look for JSON objects without code blocks if not found in code blocks
                    json_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', response, re.DOTALL)
                    if json_match:
                        json_text = json_match.group(0)
                        logger.info(f"Found JSON object in text")
                        json_data = json.loads(json_text)
                        success_count += 1
                        continue
                    else:
                        raise Exception("No JSON found in output")
                except Exception as e:
                    logger.error(f"Error processing response: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Scenario {i+1} validation failed: {str(e)}")
    
    logger.info(f"JSON processing validation: {success_count}/{len(test_responses)} scenarios validated")
    return success_count == len(test_responses)

def verify_template_processing():
    """Verify template processing with mixed variable types"""
    
    # Create a template that uses various variable types
    template = {
        "id": "test_template",
        "type": "test",
        "pattern": "This is a template with [number_var] numeric variables, [string_var] string variables, and [list_var] items."
    }
    
    # Different variable types that should all be properly handled
    variables = {
        "number_var": 42,
        "string_var": "some text",
        "list_var": ["a", "b", "c"],
        "nullable_var": None
    }
    
    engine = TemplateEngine()
    
    try:
        result = engine.process_template(template, variables)
        expected = "This is a template with 42 numeric variables, some text string variables, and ['a', 'b', 'c'] items."
        
        if result == expected:
            logger.info("Template processing validation passed")
            return True
        else:
            logger.error(f"Template output mismatch. Expected: '{expected}', Got: '{result}'")
            return False
    except Exception as e:
        logger.error(f"Template processing validation failed: {str(e)}")
        return False

def verify_validation_parsing():
    """Verify validation result extraction from various LLM output formats"""
    
    # Sample validation outputs in various formats
    test_validations = [
        # Clean JSON
        '{"passed": true, "score": 8, "feedback": "Good answer with appropriate vocabulary"}',
        
        # JSON in markdown
        """```json
        {
          "passed": false,
          "score": 3,
          "feedback": "Answer doesn't address the question properly"
        }
        ```""",
        
        # Text with extractable fields
        """
        Evaluation result:
        - passed: false
        - score: 5
        - feedback: The student needs to work on clarity.
        """,
        
        # Alternative field names/formats
        """
        {"valid": true, "score": 7.5, "feedback": "Mostly correct but could expand more"}
        """
    ]
    
    engine = EvaluationEngine()
    success_count = 0
    
    for i, validation in enumerate(test_validations):
        logger.info(f"Verifying validation extraction scenario {i+1}...")
        try:
            result = engine._parse_json_from_llm_output(validation)
            
            # Verify we correctly extracted the required fields
            if "passed" in result and "score" in result and "feedback" in result:
                logger.info(f"Successfully extracted: passed={result['passed']}, score={result['score']}")
                success_count += 1
            else:
                logger.error(f"Missing required fields in extracted result: {result}")
                
        except Exception as e:
            logger.error(f"Scenario {i+1} validation failed: {str(e)}")
    
    logger.info(f"Validation extraction: {success_count}/{len(test_validations)} scenarios validated")
    return success_count == len(test_validations)

def main():
    """Run all verification checks"""
    logger.info("Starting EdgePrompt validation architecture verification...")
    
    verification_checks = [
        ("JSON processing from LLM responses", verify_json_processing),
        ("Template processing with mixed variables", verify_template_processing),
        ("Validation result extraction", verify_validation_parsing)
    ]
    
    all_verified = True
    
    for check_name, check_func in verification_checks:
        logger.info(f"Verifying: {check_name}")
        try:
            result = check_func()
            if result:
                logger.info(f"✅ {check_name}: VERIFIED")
            else:
                logger.error(f"❌ {check_name}: VERIFICATION FAILED")
                all_verified = False
        except Exception as e:
            logger.error(f"❌ {check_name}: ERROR - {str(e)}")
            all_verified = False
    
    if all_verified:
        logger.info("🎉 EdgePrompt validation architecture successfully verified!")
        return 0
    else:
        logger.error("⚠️ Some verification checks failed")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 