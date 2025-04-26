"""
JSON Utilities - Centralized JSON parsing and repairing utilities.

This module provides robust JSON parsing functions for handling model outputs,
including extracting JSON from markdown blocks and repairing malformed JSON.
"""

import json
import logging
import re
from typing import Dict, Any, Optional, Tuple, List, Callable, Union

# Set up module-level logger
logger = logging.getLogger("edgeprompt.runner.json_utils")

def extract_json_from_text(text: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Robustly extract and parse JSON from text that may contain markdown, code blocks, or other formatting.
    
    Args:
        text: The text that potentially contains JSON
        
    Returns:
        Tuple of (parsed_json, extraction_method) where:
        - parsed_json is the extracted and parsed JSON object or None if extraction failed
        - extraction_method is a string describing how the JSON was extracted (for debugging)
    """
    if not text or not isinstance(text, str) or text.strip() == "":
        logger.warning("Received empty or non-string input for JSON extraction")
        return None, "empty_input"
    
    # First try direct parsing (most common case)
    try:
        parsed_json = json.loads(text)
        logger.debug("Direct JSON parsing successful")
        return parsed_json, "direct_parse"
    except json.JSONDecodeError:
        logger.debug("Direct JSON parsing failed, attempting extraction...")
    
    # Try various extraction patterns
    extraction_patterns = [
        # Code blocks with or without language specifier
        (r'```(?:json)?\s*([\s\S]*?)```', "markdown_code_block"),
        (r'```\s*([\s\S]*?)```', "markdown_code_block"),
        
        # Single backtick code (inline code)
        (r'`([\s\S]*?)`', "inline_code"),
        
        # Just a JSON object in the text
        (r'(\{[\s\S]*?\})', "json_object"),
        
        # Key-value pairs (output of some models)
        (r'(?:[\r\n]|^)((?:(?:"?[a-zA-Z_][a-zA-Z0-9_]*"?\s*:\s*(?:"[^"]*"|\'[^\']*\'|true|false|null|-?\d+(?:\.\d+)?|undefined)[\s,]*)+))', "key_value_pairs")
    ]
    
    # Try each extraction pattern
    for pattern, method in extraction_patterns:
        try:
            matches = re.findall(pattern, text, re.DOTALL)
            
            # Try each match (if multiple)
            for match in matches:
                # Skip empty matches
                if not match or not match.strip():
                    continue
                    
                # Clean up the extracted text
                extracted_text = match.strip()
                
                # If it doesn't look like JSON (doesn't start with { for objects or [ for arrays), skip
                if not (extracted_text.startswith("{") or extracted_text.startswith("[")):
                    # Some special case handling for key-value pairs
                    if method == "key_value_pairs":
                        # If it looks like key-value pairs, try to convert to JSON
                        extracted_text = "{" + extracted_text + "}"
                    else:
                        continue
                
                try:
                    # Try to parse the extracted text
                    parsed_json = json.loads(extracted_text)
                    logger.debug(f"Extracted JSON using method: {method}")
                    return parsed_json, method
                except json.JSONDecodeError:
                    # This match didn't work, try to clean it up
                    try:
                        # Replace single quotes with double quotes around keys and string values
                        fixed_text = re.sub(r'\'([^\']*?)\'', r'"\1"', extracted_text)
                        # Add quotes to unquoted keys
                        fixed_text = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', fixed_text)
                        # Fix True/False to true/false
                        fixed_text = fixed_text.replace("True", "true").replace("False", "false")
                        # Remove trailing commas
                        fixed_text = re.sub(r',\s*([}\]])', r'\1', fixed_text)
                        
                        parsed_json = json.loads(fixed_text)
                        logger.debug(f"Extracted and fixed JSON using method: {method}_fixed")
                        return parsed_json, f"{method}_fixed"
                    except json.JSONDecodeError:
                        # Still failed, continue to next match
                        continue
                    
        except Exception as e:
            logger.debug(f"Pattern matching error with method {method}: {e}")
            continue
    
    # If we got here, all extraction methods failed
    logger.warning(f"Failed to extract JSON from text. First 100 chars: {text[:100]}...")
    return None, "extraction_failed"


def validate_and_fix_json_structure(parsed_json: Dict[str, Any], 
                                   required_keys: List[str],
                                   default_values: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate parsed JSON against required keys and fix any issues.
    
    Args:
        parsed_json: The parsed JSON object to validate
        required_keys: List of keys that must be present
        default_values: Dictionary of default values for missing keys
        
    Returns:
        The validated and fixed JSON object
    """
    if not isinstance(parsed_json, dict):
        logger.warning(f"Parsed JSON is not a dictionary: {type(parsed_json)}")
        # Create a new dictionary with default values
        return {k: default_values.get(k) for k in required_keys}
    
    # Check for required keys
    missing_keys = set(required_keys) - set(parsed_json.keys())
    if missing_keys:
        logger.warning(f"Parsed JSON missing required keys: {missing_keys}")
        # Add missing keys with default values
        for key in missing_keys:
            if key in default_values:
                parsed_json[key] = default_values[key]
    
    # Type conversion for standard validation keys
    if "passed" in parsed_json and not isinstance(parsed_json["passed"], bool):
        # Convert to boolean
        if isinstance(parsed_json["passed"], str):
            parsed_json["passed"] = parsed_json["passed"].lower() in ('true', 'yes', 'y', '1', 't')
        else:
            parsed_json["passed"] = bool(parsed_json["passed"])
    
    if "score" in parsed_json and not isinstance(parsed_json["score"], (int, float)):
        # Convert to float
        try:
            if isinstance(parsed_json["score"], str):
                # Check for fraction format (e.g., "7/10")
                if '/' in parsed_json["score"]:
                    num, denom = parsed_json["score"].split('/')
                    parsed_json["score"] = float(num.strip()) / float(denom.strip())
                else:
                    parsed_json["score"] = float(parsed_json["score"])
            else:
                parsed_json["score"] = float(default_values.get("score", 0.5))
        except (ValueError, TypeError):
            parsed_json["score"] = float(default_values.get("score", 0.5))
            
        # Normalize score to 0-1 range if it appears to be on a different scale
        if parsed_json["score"] > 1.0 and parsed_json["score"] <= 10.0:
            parsed_json["score"] = parsed_json["score"] / 10.0
        elif parsed_json["score"] < 0.0 or parsed_json["score"] > 1.0:
            parsed_json["score"] = max(0.0, min(1.0, parsed_json["score"]))
    
    if "feedback" in parsed_json and not isinstance(parsed_json["feedback"], str):
        # Convert to string
        parsed_json["feedback"] = str(parsed_json["feedback"])
    
    return parsed_json


def parse_llm_json_output(text: str, 
                        required_keys: List[str] = None, 
                        default_values: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    High-level function to parse JSON from LLM output text, with validation and fixing.
    
    Args:
        text: The LLM output text to parse
        required_keys: List of keys that must be present in the JSON
        default_values: Dictionary of default values for missing keys
        
    Returns:
        The parsed, validated, and fixed JSON object or empty dict if parsing failed
    """
    # Set defaults if not provided
    if required_keys is None:
        required_keys = ["passed", "score", "feedback"]
    
    if default_values is None:
        default_values = {
            "passed": False,
            "score": 0.5,
            "feedback": "Failed to parse validation result."
        }
    
    # First try to extract JSON
    parsed_json, method = extract_json_from_text(text)
    
    if parsed_json is None:
        logger.warning("Failed to extract JSON from LLM output")
        # Return default values
        return {k: default_values.get(k) for k in required_keys}
    
    # Validate and fix JSON structure
    return validate_and_fix_json_structure(parsed_json, required_keys, default_values)


def repair_json_with_llm(text: str, 
                         llm_repair_func: Callable[[str, Dict[str, Any]], str], 
                         model_data: Dict[str, Any],
                         required_keys: List[str] = None,
                         default_values: Dict[str, Any] = None,
                         max_attempts: int = 1) -> Dict[str, Any]:
    """
    Use an LLM to repair malformed JSON in text.
    
    Args:
        text: The text containing malformed JSON
        llm_repair_func: Function that sends a repair prompt to an LLM and returns the response
        model_data: Model data to pass to the repair function
        required_keys: List of keys that must be present in the JSON
        default_values: Dictionary of default values for missing keys
        max_attempts: Maximum number of repair attempts to prevent infinite loops
        
    Returns:
        The parsed, repaired JSON object or defaults if repair failed
    """
    # Set defaults if not provided
    if required_keys is None:
        required_keys = ["passed", "score", "feedback"]
    
    if default_values is None:
        default_values = {
            "passed": False,
            "score": 0.5,
            "feedback": "Failed to parse validation result."
        }
    
    # First try standard parsing
    parsed_json, method = extract_json_from_text(text)
    
    if parsed_json is not None:
        # Successfully parsed, just validate and fix structure
        return validate_and_fix_json_structure(parsed_json, required_keys, default_values)
    
    # Need to repair
    logger.info("Standard JSON parsing failed, attempting repair with LLM...")
    
    # Keep track of attempts
    attempt = 0
    current_text = text
    
    while attempt < max_attempts:
        attempt += 1
        logger.debug(f"Repair attempt {attempt}/{max_attempts}")
        
        # Generate the repair prompt
        repair_prompt = f"""Fix the following text into valid JSON. Return ONLY the fixed JSON, nothing else.

TEXT TO FIX:
```
{current_text}
```

Your response should be ONLY a valid JSON object with these exact keys:
{", ".join([f'"{k}"' for k in required_keys])}

Do NOT include markdown formatting, code blocks, or any text outside the JSON object.
"""
        
        # Send to LLM repair function
        repaired_text = llm_repair_func(repair_prompt, model_data)
        
        # If repaired text is the same as input, no point continuing
        if repaired_text == current_text:
            logger.warning("Repair produced identical output - stopping repair attempts")
            break
            
        # Try to parse the repaired text
        parsed_json, method = extract_json_from_text(repaired_text)
        
        if parsed_json is not None:
            # Successfully repaired and parsed
            logger.info(f"Successfully repaired JSON (method: {method})")
            return validate_and_fix_json_structure(parsed_json, required_keys, default_values)
        
        # Update for next attempt
        current_text = repaired_text
    
    # If we got here, repair failed
    logger.warning(f"JSON repair failed after {attempt} attempts")
    return {k: default_values.get(k) for k in required_keys}