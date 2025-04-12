"""
TestExecutor - Handles execution of individual tests.

This module provides functionality for executing LLM inference
using LM Studio's OpenAI-compatible API in the EdgePrompt research framework.
"""

import logging
import time
import json
from typing import Dict, Any, List, Optional, Callable

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class TestExecutor:
    """
    Executes tests against LLM models through LM Studio's API.
    
    This class handles:
    - Connecting to LM Studio via OpenAI-compatible API
    - Constructing chat completion requests
    - Processing model responses, including token counts
    - Handling errors and timeouts
    """
    
    def __init__(self, lm_studio_url: Optional[str] = None):
        """
        Initialize the TestExecutor.
        
        Args:
            lm_studio_url: Base URL for LM Studio server (optional)
        """
        self.logger = logging.getLogger("edgeprompt.runner.executor")
        self.lm_studio_url = lm_studio_url
        
        if not OPENAI_AVAILABLE:
            self.logger.warning("OpenAI package not available - Install with 'pip install openai>=1.0.0'")
        
        if lm_studio_url:
            self.logger.info(f"TestExecutor initialized with LM Studio URL: {lm_studio_url}")
        else:
            self.logger.info("TestExecutor initialized in mock mode (LM Studio URL not provided)")
    
    def execute_test(self, model_metadata: Dict[str, Any], prompt: str, 
                    generation_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a test against a model via LM Studio's API.
        
        Args:
            model_metadata: Model metadata containing api_identifier
            prompt: The prompt to send to the model
            generation_params: Optional parameters controlling generation
            
        Returns:
            Dict containing the test results including output text and token counts
        """
        # Get the API identifier from model metadata
        api_identifier = model_metadata.get('api_identifier')
        if not api_identifier:
            error_msg = "Missing API identifier in model metadata"
            self.logger.error(error_msg)
            return {"error": error_msg, "output": "ERROR: " + error_msg}
        
        self.logger.info(f"Executing test with model {api_identifier}")
        
        # Default generation parameters
        if generation_params is None:
            generation_params = {
                "max_tokens": 100,
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40
            }
            
        # Log basic info
        self.logger.info(f"Prompt length: {len(prompt)} chars, {len(prompt.split())} words")
        
        # Use the mock if no LM Studio URL is provided or OpenAI is not available
        if not self.lm_studio_url or not OPENAI_AVAILABLE:
            self.logger.warning("Using mock generation (no LM Studio URL or OpenAI package unavailable)")
            return self._execute_mock(api_identifier, prompt, generation_params)
        
        # Start timing
        start_time = time.time()
        
        try:
            # Initialize OpenAI client with LM Studio base URL
            client = OpenAI(
                base_url=self.lm_studio_url,
                api_key="lm-studio"  # LM Studio doesn't validate the key
            )
            
            # Prepare messages for chat completion
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
            
            # Prepare generation parameters
            chat_params = {
                "model": api_identifier,
                "messages": messages,
                "max_tokens": generation_params.get("max_tokens", 100),
                "temperature": generation_params.get("temperature", 0.7),
                "top_p": generation_params.get("top_p", 0.9)
            }
            
            # Add other parameters if present
            if "stop" in generation_params:
                chat_params["stop"] = generation_params["stop"]
                
            if "presence_penalty" in generation_params:
                chat_params["presence_penalty"] = generation_params["presence_penalty"]
                
            if "frequency_penalty" in generation_params:
                chat_params["frequency_penalty"] = generation_params["frequency_penalty"]
            
            # Make the API call
            self.logger.info(f"Calling LM Studio API with model {api_identifier}")
            completion = client.chat.completions.create(**chat_params)
            
            # Extract content from response
            output_text = completion.choices[0].message.content
            
            # Extract token counts
            input_tokens = completion.usage.prompt_tokens
            output_tokens = completion.usage.completion_tokens
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Prepare result
            result = {
                "output": output_text,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "execution_time_ms": execution_time_ms,
                "generation_params": generation_params,
            }
            
            self.logger.info(f"Test execution completed in {execution_time_ms}ms - Input tokens: {input_tokens}, Output tokens: {output_tokens}")
            
            return result
            
        except Exception as e:
            error_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Error executing test: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            # Return error result
            return {
                "error": error_msg,
                "output": f"ERROR: {str(e)}",
                "execution_time_ms": error_time_ms,
                "generation_params": generation_params,
            }
    
    def _execute_mock(self, model_id: str, prompt: str, 
                     generation_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a mock generation when LM Studio is not available.
        
        Args:
            model_id: The model identifier
            prompt: The prompt to send
            generation_params: Generation parameters
            
        Returns:
            Dict with mock results
        """
        start_time = time.time()
        
        # Sleep to simulate processing
        time.sleep(0.5) 
        
        # Generate mock output
        output = f"[Mock output for prompt: {prompt[:30]}...]"
        
        # Calculate mock token counts
        input_tokens = len(prompt.split())
        output_tokens = len(output.split())
        
        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Prepare result
        result = {
            "output": output,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "execution_time_ms": execution_time_ms,
            "generation_params": generation_params,
            "mock": True
        }
        
        self.logger.info(f"Mock test execution completed in {execution_time_ms}ms")
        
        return result
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """
        Parse model output to extract structured data.
        
        Args:
            output: The raw model output
            
        Returns:
            Dict containing parsed output
        """
        # Try to parse as JSON first (for validation outputs)
        try:
            return json.loads(output)
        except (json.JSONDecodeError, TypeError):
            # If not JSON, return as raw output
            return {
                "raw_output": output,
                "parsed": {
                    "success": True,
                    "content": output
                }
            } 