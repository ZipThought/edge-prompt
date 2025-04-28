"""
EdgeLLM Runners - Abstract interface and implementations for local LLM execution.

This module provides an abstraction layer for executing local LLMs through
different backends (LM Studio, Ollama) with a consistent interface.
"""

import abc
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple

# Third-party imports with graceful failure
try:
    import requests
except ImportError:
    requests = None
try:
    import openai
except ImportError:
    openai = None

# Local application imports
from .metrics_collector import MetricsCollector


class EdgeLLMRunner(abc.ABC):
    """
    Abstract base class defining the interface for EdgeLLM execution backends.
    
    All EdgeLLM runner implementations must implement the execute method
    with a consistent return structure.
    """
    
    @abc.abstractmethod
    def execute(self, prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a prompt against the EdgeLLM model.
        
        Args:
            prompt: The prompt string to send to the model
            params: Dictionary of generation parameters (e.g., temperature, max_tokens, json_output)
        
        Returns:
            Dictionary containing the following keys:
            - 'generated_text' (str|None): The generated content or None on error
            - 'input_tokens' (int): Count of input tokens processed
            - 'output_tokens' (int): Count of output tokens generated
            - 'metrics' (dict): Performance metrics including at least 'latency_ms'
            - 'error' (str|None): Error message if any, or None on success
        """
        pass


class LMStudioRunner(EdgeLLMRunner):
    """
    Runner implementation for LM Studio's OpenAI-compatible API.
    
    Uses LM Studio's OpenAI-compatible endpoints to execute local models.
    """
    
    def __init__(self, lm_studio_url: str, model_data: Dict[str, Any], metrics_collector: MetricsCollector):
        """
        Initialize the LM Studio runner.
        
        Args:
            lm_studio_url: Base URL for the LM Studio API
            model_data: Model configuration dictionary
            metrics_collector: Instance for tracking performance metrics
        """
        self.logger = logging.getLogger("edgeprompt.runner.edge_lm_studio")
        self.lm_studio_url = lm_studio_url
        self.model_data = model_data
        self.metrics_collector = metrics_collector
        self.model_id = model_data.get("model_id", "unknown")
        
        # Ensure correct API endpoint construction
        if not self.lm_studio_url.endswith('/v1') and '/v1/' not in self.lm_studio_url:
            # Avoid double slashes if base_url already ends with /
            if self.lm_studio_url.endswith('/'):
                self.lm_studio_url += 'v1'
            else:
                self.lm_studio_url += '/v1'
        
        self.logger.info(f"Initialized LMStudioRunner for model {self.model_id}")

    def execute(self, prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a prompt through LM Studio's OpenAI-compatible API.
        
        Args:
            prompt: The prompt string to send to the model
            params: Dictionary of generation parameters
        
        Returns:
            Dictionary with standard EdgeLLMRunner return structure
        """
        if not requests:
            return {
                "generated_text": None,
                "error": "`requests` library not installed, cannot call LM Studio.",
                "input_tokens": len(prompt.split()),  # Estimate
                "output_tokens": 0,
                "metrics": {}
            }
        
        # Construct API URL for chat completions
        api_url = f"{self.lm_studio_url}/chat/completions"
        self.logger.debug(f"Using LM Studio API URL: {api_url}")
        
        # Prepare payload (OpenAI compatible)
        payload = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": params.get("temperature", 0.7),
            "max_tokens": params.get("max_tokens", 256),
            "stream": False
        }
        
        # Handle JSON format requests
        json_format_requested = params.get("json_output", False) or (
            isinstance(params.get("response_format"), dict) and 
            params.get("response_format", {}).get("type") == "json_object"
        )
        
        # Since LM Studio doesn't support response_format parameter,
        # we'll modify the prompt to emphasize JSON output when requested
        if json_format_requested and "json" not in prompt.lower():
            # Add explicit JSON formatting instructions
            prompt_addition = "\n\nIMPORTANT: Your response must be a valid JSON object only. Do not include any text outside the JSON object."
            payload["messages"][0]["content"] = prompt + prompt_addition
            self.logger.debug("Added JSON formatting instructions to prompt.")
        
        headers = {"Content-Type": "application/json"}
        
        try:
            # Start metrics collection
            self.metrics_collector.start_timer()
            
            # Make the API call
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()  # Raise HTTPError for bad responses
            data = response.json()
            
            # Extract response text
            output_text = data['choices'][0]['message']['content']
            
            # Extract token counts if available
            input_tokens = data.get('usage', {}).get('prompt_tokens', 0)
            output_tokens = data.get('usage', {}).get('completion_tokens', 0)
            
            # Stop metrics collection and record tokens
            self.metrics_collector.stop_timer()
            self.metrics_collector.record_tokens(input_tokens, output_tokens)
            performance_metrics = self.metrics_collector.get_results()
            
            result = {
                "generated_text": output_text,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "metrics": performance_metrics,
                "error": None
            }
            
            return result
            
        except Exception as e:
            # Ensure timer is stopped even if call fails
            if self.metrics_collector.start_time:
                self.metrics_collector.stop_timer()
            
            self.logger.error(f"Error executing model {self.model_id} with LM Studio: {str(e)}", exc_info=True)
            
            # Return error structure consistent with success structure
            return {
                "generated_text": None,
                "error": str(e),
                "input_tokens": len(prompt.split()),  # Estimate
                "output_tokens": 0,
                "metrics": self.metrics_collector.get_results()  # Get latency if timer stopped
            }


class OllamaRunner(EdgeLLMRunner):
    """
    Runner implementation for Ollama's native API.
    
    Uses Ollama's /api/chat endpoint to execute local models.
    """
    
    def __init__(self, ollama_url: str, model_data: Dict[str, Any], metrics_collector: MetricsCollector):
        """
        Initialize the Ollama runner.
        
        Args:
            ollama_url: Base URL for the Ollama API
            model_data: Model configuration dictionary
            metrics_collector: Instance for tracking performance metrics
        """
        self.logger = logging.getLogger("edgeprompt.runner.edge_ollama")
        
        # Ensure URL doesn't have a trailing slash
        self.ollama_url = ollama_url.rstrip('/')
        self.model_data = model_data
        self.metrics_collector = metrics_collector
        self.model_id = model_data.get("model_id", "unknown")
        
        # Get the Ollama tag from model_data (required for Ollama interaction)
        self.ollama_tag = model_data.get("ollama_tag")
        if not self.ollama_tag:
            self.logger.warning(f"No ollama_tag specified for model {self.model_id}. Will use model_id as fallback.")
            self.ollama_tag = self.model_id
        
        self.logger.info(f"Initialized OllamaRunner for model {self.model_id} (Ollama tag: {self.ollama_tag})")

    def execute(self, prompt: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a prompt through Ollama's native API.
        
        Args:
            prompt: The prompt string to send to the model
            params: Dictionary of generation parameters
        
        Returns:
            Dictionary with standard EdgeLLMRunner return structure
        """
        if not requests:
            return {
                "generated_text": None,
                "error": "`requests` library not installed, cannot call Ollama.",
                "input_tokens": len(prompt.split()),  # Estimate
                "output_tokens": 0,
                "metrics": {}
            }
        
        # Construct API URL for Ollama chat endpoint
        api_url = f"{self.ollama_url}/api/chat"
        self.logger.debug(f"Using Ollama API URL: {api_url}")
        
        # Prepare request options from params
        options = {
            "temperature": params.get("temperature", 0.7),
            "num_predict": params.get("max_tokens", 256),
        }
        
        # Handle JSON format requests
        json_format_requested = params.get("json_output", False) or (
            isinstance(params.get("response_format"), dict) and 
            params.get("response_format", {}).get("type") == "json_object"
        )
        
        # If JSON output is requested, set the format parameter and potentially modify the prompt
        if json_format_requested:
            options["format"] = "json"
            if "json" not in prompt.lower():
                # Add explicit JSON formatting instructions
                prompt += "\n\nIMPORTANT: Your response must be a valid JSON object only. Do not include any text outside the JSON object."
                self.logger.debug("Added JSON formatting instructions to prompt.")
        
        # Prepare the payload
        payload = {
            "model": self.ollama_tag,
            "messages": [{"role": "user", "content": prompt}],
            "options": options,
            "stream": False
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            # Start metrics collection
            self.metrics_collector.start_timer()
            
            # Make the API call
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()  # Raise HTTPError for bad responses
            data = response.json()
            
            # Extract response text - Ollama returns the content in 'message.content'
            output_text = data.get('message', {}).get('content', '')
            
            # Extract token counts and metrics - Ollama has different metrics structure
            # prompt_eval_count = tokens processed for the input
            # eval_count = tokens generated for the output
            # eval_duration = time spent generating tokens in nanoseconds
            input_tokens = data.get('prompt_eval_count', 0)
            output_tokens = data.get('eval_count', 0)
            
            # Convert eval_duration from nanoseconds to milliseconds for our metrics
            eval_duration_ns = data.get('eval_duration', 0)
            latency_ms = eval_duration_ns / 1_000_000  # Convert ns to ms
            
            # Stop metrics collection and record tokens
            self.metrics_collector.stop_timer()
            self.metrics_collector.record_tokens(input_tokens, output_tokens)
            performance_metrics = self.metrics_collector.get_results()
            
            # If Ollama provided a latency, override the calculated one
            if eval_duration_ns > 0:
                performance_metrics['latency_ms'] = latency_ms
                
                # Recalculate tokens_per_second
                if output_tokens > 0 and latency_ms > 0:
                    tokens_per_second = (output_tokens / latency_ms) * 1000
                    performance_metrics['tokens_per_second'] = tokens_per_second
            
            result = {
                "generated_text": output_text,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "metrics": performance_metrics,
                "error": None
            }
            
            return result
            
        except Exception as e:
            # Ensure timer is stopped even if call fails
            if self.metrics_collector.start_time:
                self.metrics_collector.stop_timer()
            
            self.logger.error(f"Error executing model {self.model_id} with Ollama: {str(e)}", exc_info=True)
            
            # Return error structure consistent with success structure
            return {
                "generated_text": None,
                "error": str(e),
                "input_tokens": len(prompt.split()),  # Estimate
                "output_tokens": 0,
                "metrics": self.metrics_collector.get_results()  # Get latency if timer stopped
            }