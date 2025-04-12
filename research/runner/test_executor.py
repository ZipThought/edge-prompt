"""
TestExecutor - Centralizes model API interactions to simplify experiment workflows.

This module abstracts LLM API interactions to:
- Reduce code duplication across different experiment types
- Provide consistent error handling and logging for API calls
- Enable mock executions for testing without model dependencies
- Centralize response parsing and standardization
"""

import json
import logging
import random
import string
import time
from typing import Dict, Any, Optional, List, Union

class TestExecutor:
    """
    Centralizes API interactions to reduce code duplication and improve maintainability.
    
    This centralization:
    - Reduces duplication of API-related code across experiments
    - Creates a single point for logging and error handling
    - Simplifies mocking for testing without model dependencies
    - Standardizes output format for consistent downstream processing
    """
    
    def __init__(self, lm_studio_url: Optional[str] = None):
        """
        Supports configurable API endpoint to accommodate different environments.
        
        This flexibility:
        - Enables development across different environments
        - Simplifies testing with environment-specific settings
        - Facilitates deployment in different network configurations
        """
        self.logger = logging.getLogger("edgeprompt.runner.test_executor")
        
        # Allow configuration for different environments
        self.lm_studio_url = lm_studio_url or "http://localhost:1234"
    
    def execute_test(self, model_metadata: Dict[str, Any], prompt: str, 
                    generation_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Centralizes model interaction to provide consistent handling and logging.
        
        This centralization:
        - Ensures consistent error handling across all model interactions
        - Standardizes logging for reproducibility and debugging
        - Enables mock execution for testing without model dependencies
        - Creates consistent output structure for downstream processing
        """
        # Log prompt length for debugging performance and token usage
        self.logger.info(f"Executing test with prompt length: {len(prompt)}")
        
        # Support mock execution for testing without requiring actual model access
        if model_metadata.get("mock", False):
            self.logger.info("Using mock execution mode")
            return self._execute_mock(model_metadata.get("model_id", "unknown"), prompt, generation_params)
        
        # Use API identifier from metadata to maintain consistent model references
        api_id = model_metadata.get("api_identifier")
        if not api_id:
            raise ValueError("Model metadata missing api_identifier")
            
        # Start with default parameters for safety and predictability
        params = {
            "temperature": 0.7,
            "max_tokens": 2048,
            "top_p": 0.95,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "stop": None
        }
        
        # Apply specific parameters if provided to support experiment needs
        if generation_params:
            params.update(generation_params)
            
        # Measure execution time for performance analysis
        start_time = time.time()
        
        try:
            # Import at runtime to avoid dependency when using mock execution
            from openai import OpenAI
            
            # Initialize client with appropriate URL and API key
            client = OpenAI(
                base_url=f"{self.lm_studio_url}/v1",
                api_key="lm-studio"  # LM Studio doesn't use real keys
            )
            
            # Create message format for the API
            messages = [{"role": "user", "content": prompt}]
            
            # Execute the model request
            completion = client.chat.completions.create(
                model=api_id,
                messages=messages,
                temperature=params["temperature"],
                max_tokens=params["max_tokens"],
                top_p=params["top_p"],
                frequency_penalty=params["frequency_penalty"],
                presence_penalty=params["presence_penalty"],
                stop=params["stop"]
            )
            
            # Extract output text from response
            output_text = completion.choices[0].message.content
            
            # Calculate metrics for analysis
            elapsed_time = time.time() - start_time
            
            # Construct standardized result
            result = {
                "model_id": api_id,
                "output": output_text,
                "elapsed_seconds": elapsed_time,
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "total_tokens": completion.usage.total_tokens
            }
            
            self.logger.info(f"Completed execution in {elapsed_time:.2f}s, total tokens: {result['total_tokens']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing test: {str(e)}")
            
            # Return error information in consistent format for downstream handling
            return {
                "model_id": api_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "elapsed_seconds": time.time() - start_time
            }
    
    def _execute_mock(self, model_id: str, prompt: str, 
                     generation_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Provides mock execution to enable testing without model dependencies.
        
        Mock execution:
        - Simplifies testing by removing external dependencies
        - Ensures reproducible results for test validation
        - Speeds up development by avoiding actual API calls
        - Allows testing of error handling and edge cases
        """
        # Simulate processing delay to mimic real execution time
        delay = min(2.0, len(prompt) * 0.001)  # Realistic delay based on prompt length
        time.sleep(delay)
        
        # Generate mock token counts for testing token-based logic
        prompt_tokens = len(prompt.split())
        completion_tokens = random.randint(50, 200)  # Reasonable mock range
        
        # Create mock output with identifiable prefix
        output = f"MOCK OUTPUT from model {model_id}: Response to prompt of length {len(prompt)}"
        
        # Return consistent format matching real execution
        return {
            "model_id": model_id,
            "output": output,
            "elapsed_seconds": delay,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
        
    def parse_output(self, output: str) -> Dict[str, Any]:
        """
        Standardizes output parsing to ensure consistent downstream processing.
        
        Centralized parsing:
        - Ensures consistent interpretation of model outputs
        - Reduces duplication of parsing logic across experiments
        - Creates predictable output structure for analysis
        - Shields downstream code from model-specific output formats
        """
        # Start with basic output structure
        result = {"raw_output": output}
        
        try:
            # Attempt to parse JSON if output appears to be JSON format
            if output.strip().startswith('{') and output.strip().endswith('}'):
                parsed = json.loads(output)
                result["parsed_json"] = parsed
            else:
                # Basic text extraction for non-JSON outputs
                # Extract the first line as a summary
                lines = output.strip().split('\n')
                result["first_line"] = lines[0] if lines else ""
                
                # Try to extract any numbers found in the output for metrics
                import re
                numbers = re.findall(r'\d+\.\d+|\d+', output)
                if numbers:
                    result["extracted_numbers"] = [float(n) if '.' in n else int(n) for n in numbers]
        
        except Exception as e:
            # Record parsing errors without failing
            result["parsing_error"] = str(e)
            
        return result 