"""
ModelManager - Abstracts model access to decouple experiment logic from model implementation.

This module separates model access concerns from experiment logic to:
- Enable different model backends without changing experiment code
- Support testing without requiring actual model dependencies
- Provide a consistent interface for experiments regardless of underlying model technology
- Allow for mock models to speed up development and testing cycles
"""

import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Third-party imports (assuming installed, add try-except blocks for graceful failure)
try:
    import anthropic
except ImportError:
    anthropic = None
try:
    import openai
except ImportError:
    openai = None
try:
    import requests
except ImportError:
    requests = None

# Local application imports
from .config_loader import ConfigLoader
from .metrics_collector import MetricsCollector

class MockModel:
    """
    Facilitates development and testing without requiring actual model access.
    
    This approach:
    - Speeds up development by removing dependency on heavyweight models
    - Ensures reproducible tests even in CI/CD environments without model access
    - Provides deterministic responses for reliable test validation
    - Eliminates network latency and API costs during development
    """
    
    def __init__(self, model_id: str, model_type: str = "edge_llm"):
        """
        Retains model identity to maintain traceability in mock scenarios.
        
        Args:
            model_id: Identifier for the model
            model_type: Type of model ('cloud_llm' or 'edge_llm')
        """
        self.model_id = model_id
        self.model_type = model_type
        self.logger = logging.getLogger(f"edgeprompt.runner.mock_model.{model_id}")
        
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Provides predictable outputs to enable reliable testing. Mimics algorithm output.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional generation parameters (e.g., max_tokens, temperature, json_output)
            
        Returns:
            Dict containing generation results mimicking algorithm structure.
        """
        self.logger.debug(f"Generating mock response for prompt (first 50 chars): {prompt[:50]}... Args: {kwargs}")
        
        # Simulate processing delay based on prompt length and model type
        delay = min(0.5 if self.model_type == "edge_llm" else 1.5, len(prompt) * 0.0002)
        time.sleep(delay)
        
        # Generate different mock responses based on model type and structure
        # Determine if JSON output is expected based on common keys
        expect_json = kwargs.get("json_output", False) or \
                      kwargs.get("response_format", {}).get("type") == "json_object" or \
                      "json" in prompt.lower() # Simple heuristic
        
        if self.model_type == "cloud_llm":
            generated_text = f"MOCK CloudLLM RESPONSE from {self.model_id}: This simulates a persona response."
            if expect_json:
                # Mimic CloudLLM_Interaction output structure (nested under llm_output)
                mock_obj = {
                    "role": "teacher" if "teacher" in prompt.lower() else "student",
                    "content": f"Mock {self.model_id} response with simulated JSON structure",
                    "evaluation": {
                        "score": random.randint(6, 9),
                        "feedback": "This is mock feedback from the CloudLLM model.",
                        "passed": True
                    }
                }
                generated_text = json.dumps(mock_obj)
            output_key = "llm_output" # Key defined in CloudLLM_Interaction spec
        else:  # edge_llm
            generated_text = f"MOCK EdgeLLM RESPONSE from {self.model_id}: This simulates an edge model response."
            if expect_json:
                 # Mimic EdgeLLMExecution output structure (nested under generated_text)
                 # Often used for validation stages
                mock_obj = {
                    "passed": random.choice([True, True, False]),  # Bias toward passing
                    "score": random.uniform(0.5, 1.0),
                    "feedback": "This is mock feedback from the EdgeLLM validation model.",
                    "word_count": random.randint(40, 120) # Example extra data
                }
                generated_text = json.dumps(mock_obj)
            output_key = "generated_text" # Key defined in EdgeLLMExecution spec
        
        # Estimate token counts based on input/output length
        # (Very rough estimate, real APIs provide this)
        prompt_tokens = len(prompt.split())
        completion_tokens = len(generated_text.split())
        
        # Mimic the structure returned by _execute_model_call helper
        result = {
            output_key: generated_text,
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "metrics": {
                 "latency_ms": delay * 1000,
                 "input_tokens": prompt_tokens,
                 "output_tokens": completion_tokens,
                 "tokens_per_second": completion_tokens / delay if delay > 0 else 0
            }
        }
        self.logger.debug(f"Mock generation complete. Result keys: {result.keys()}")
        return result
        
class ModelManager:
    """
    Abstracts model access for CloudLLM (API) and EdgeLLM (local/API) models.

    Uses ConfigLoader to get model details and MetricsCollector for performance tracking.
    Aligns with `CloudLLM_Interaction` and `EdgeLLMExecution` algorithms.
    """
    
    def __init__(self, config_loader: ConfigLoader, metrics_collector: MetricsCollector,
                 lm_studio_url: Optional[str] = None,
                 openai_api_key: Optional[str] = None,
                 anthropic_api_key: Optional[str] = None):
        """
        Initialize ModelManager.

        Args:
            config_loader: Instance of ConfigLoader to fetch model configs.
            metrics_collector: Instance of MetricsCollector for timing/token counts.
            lm_studio_url: URL for LM Studio API (for some EdgeLLM).
            openai_api_key: OpenAI API key (for CloudLLM).
            anthropic_api_key: Anthropic API key (for CloudLLM).
        """
        self.logger = logging.getLogger("edgeprompt.runner.model_manager")
        self.config_loader = config_loader
        self.metrics_collector = metrics_collector # Store the collector
        
        # Configure API endpoints and keys from args or environment
        self.lm_studio_url = lm_studio_url or os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1") # Ensure /v1 for completions endpoint
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.anthropic_api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        # Cache loaded model instances/clients
        self.loaded_models: Dict[str, Dict[str, Any]] = {} # Cache stores {model_key: model_data_with_instance/client}
        
        # Lazy initialization for API clients
        self._openai_client = None
        self._anthropic_client = None
        
        self.logger.info("ModelManager initialized.")
        if not self.openai_api_key: self.logger.warning("OpenAI API key not provided.")
        if not self.anthropic_api_key: self.logger.warning("Anthropic API key not provided.")
        if not requests: self.logger.warning("`requests` library not installed, LM Studio interaction might fail.")
        
    def _get_openai_client(self):
        """Lazily initializes and returns the OpenAI client."""
        if not openai:
             self.logger.error("OpenAI library not installed. Cannot create client.")
             raise ImportError("OpenAI library is required.")
        if not self._openai_client:
            if not self.openai_api_key:
                raise ValueError("OpenAI API key is required but not provided.")
            self._openai_client = openai.OpenAI(api_key=self.openai_api_key)
        return self._openai_client
    
    def _get_anthropic_client(self):
        """Lazily initializes and returns the Anthropic client."""
        if not anthropic:
            self.logger.error("Anthropic library not installed. Cannot create client.")
            raise ImportError("Anthropic library is required.")
        if not self._anthropic_client:
            if not self.anthropic_api_key:
                 raise ValueError("Anthropic API key is required but not provided.")
            self._anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        return self._anthropic_client
    
    def _initialize_model(self, model_id: str, model_type: str, mock_mode: bool) -> Dict[str, Any]:
        """
        Helper to initialize or retrieve a model (CloudLLM or EdgeLLM).

        Handles caching, mock mode, and provider-specific setup.
        """
        model_key = f"{model_type}:{model_id}"
        if model_key in self.loaded_models and not mock_mode: # Don't return cached mock model if mock_mode is now False
             if not self.loaded_models[model_key].get("mock", False): # Ensure cached real model isn't returned in mock_mode
                 self.logger.info(f"Using cached {model_type.upper()} model: {model_id}")
                 return self.loaded_models[model_key]
             else:
                 # If mock_mode=False but cached model is mock, re-initialize
                 self.logger.info(f"Re-initializing {model_type.upper()} model {model_id} (was previously mocked).")
                 del self.loaded_models[model_key]
        elif mock_mode and model_key in self.loaded_models and self.loaded_models[model_key].get("mock", False):
             self.logger.info(f"Using cached mock {model_type.upper()} model: {model_id}")
             return self.loaded_models[model_key]

        # Load model configuration details using ConfigLoader
        model_config = self.config_loader.load_model_config(model_id)
        if not model_config:
            raise ValueError(f"Configuration for {model_type.upper()} model ID '{model_id}' not found.")

        # Create mock model if requested
        if mock_mode:
            self.logger.info(f"Initializing mock {model_type.upper()}: {model_id}")
            mock_instance = MockModel(model_id, model_type=model_type)
            model_config["mock"] = True
            model_config["instance"] = mock_instance
            self.loaded_models[model_key] = model_config
            return model_config

        # Initialize real model based on type and config
        provider = model_config.get("provider", "").lower()
        client_type = model_config.get("client_type", "").lower()

        if model_type == "cloud_llm":
            if provider == "openai":
                model_config["client"] = self._get_openai_client()
            elif provider == "anthropic":
                 model_config["client"] = self._get_anthropic_client()
            else:
                raise ValueError(f"Unsupported provider for CloudLLM model {model_id}: {provider}")
            self.logger.info(f"Initialized CloudLLM ({provider}): {model_id}")

        elif model_type == "edge_llm":
            # Currently primarily supports LM Studio compatible endpoints
            if client_type == "lm_studio" or "local" in client_type: # Assume local means LM Studio for now
                 # No specific client needed, will use requests in execute_edge_llm
                 model_config["client_type"] = "lm_studio" # Standardize
                 self.logger.info(f"Prepared EdgeLLM (LM Studio target): {model_id} at {self.lm_studio_url}")
                 if not requests:
                     self.logger.warning("`requests` library needed for LM Studio interaction.")
            else:
                 raise ValueError(f"Unsupported client_type for EdgeLLM model {model_id}: {client_type}")

        else:
            raise ValueError(f"Unknown model type: {model_type}")

        model_config["initialized"] = True
        model_config["mock"] = False
        self.loaded_models[model_key] = model_config
        return model_config

    def initialize_cloud_llm(self, model_id: str, mock_mode: bool = False) -> Dict[str, Any]:
        """Initializes a CloudLLM model using the helper method."""
        return self._initialize_model(model_id, "cloud_llm", mock_mode)

    def initialize_edge_llm(self, model_id: str, mock_mode: bool = False) -> Dict[str, Any]:
        """Initializes an EdgeLLM model using the helper method."""
        return self._initialize_model(model_id, "edge_llm", mock_mode)

    def _execute_model_call(self, model_data: Dict[str, Any], prompt: str,
                           api_call_func: Callable[..., Tuple[str, int, int]], # Func returning (output_text, in_tokens, out_tokens)
                           result_key: str # Key for the main output ('generated_text' or 'llm_output')
                          ) -> Dict[str, Any]:
        """
        Helper function to wrap model execution, handle timing, metrics, and errors.
        """
        model_id = model_data.get("model_id", "unknown")
        self.logger.debug(f"Executing {model_id} with prompt (first 50 chars): {prompt[:50]}...")

        try:
            # Start metrics collection before the call
            self.metrics_collector.start_timer()
            output_text, input_tokens, output_tokens = api_call_func() # Execute the specific API call
            self.metrics_collector.stop_timer()

            # Record tokens after the call completes
            self.metrics_collector.record_tokens(input_tokens, output_tokens)
            performance_metrics = self.metrics_collector.get_results()

            result = {
                result_key: output_text,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "metrics": performance_metrics
            }
            self.logger.debug(f"Execution successful for {model_id}. Output size: {len(output_text)} chars.")
            return result
            
        except Exception as e:
            # Ensure timer is stopped even if call fails
            if self.metrics_collector.start_time:
                self.metrics_collector.stop_timer()
            self.logger.error(f"Error executing model {model_id}: {str(e)}", exc_info=True)
            # Return error structure consistent with success structure
            return {
                result_key: None,
                "error": str(e),
                "input_tokens": len(prompt.split()), # Estimate
                "output_tokens": 0,
                "metrics": self.metrics_collector.get_results() # Get latency if timer stopped
            }

    def execute_cloud_llm(self, model_data: Dict[str, Any], prompt: str,
                     params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute CloudLLM (API model) interaction. Aligns with CloudLLM_Interaction algorithm.

        Args:
            model_data: Model configuration dictionary (from initialize_cloud_llm).
            prompt: The prompt string.
            params: Dictionary of generation parameters (e.g., temperature, max_tokens, response_format).

        Returns:
            Dictionary containing 'llm_output', token counts, and 'metrics'. Includes 'error' on failure.
        """
        params = params or {}
        model_id = model_data.get("model_id", "unknown")

        # Handle mock execution first
        if model_data.get("mock"):
            mock_instance: MockModel = model_data.get("instance")
            return mock_instance.generate(prompt, **params)

        provider = model_data.get("provider", "").lower()
        client = model_data.get("client")
        if not client:
             return {"error": f"CloudLLM client for {model_id} not initialized.", "llm_output": None, "metrics": {}}

        def api_call() -> Tuple[str, int, int]:
            if provider == "openai":
                if not openai: raise ImportError("OpenAI library not installed.")
                response_format = params.get("response_format")
                openai_params = {
                    "model": model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": params.get("temperature", 0.5),
                    "max_tokens": params.get("max_tokens", 512),
                }
                # Correctly handle JSON mode for OpenAI
                if isinstance(response_format, dict) and response_format.get("type") == "json_object":
                     openai_params["response_format"] = {"type": "json_object"}

                response = client.chat.completions.create(**openai_params)
                output_text = response.choices[0].message.content
                in_tokens = response.usage.prompt_tokens
                out_tokens = response.usage.completion_tokens
                return output_text, in_tokens, out_tokens

            elif provider == "anthropic":
                if not anthropic: raise ImportError("Anthropic library not installed.")
                # Anthropic uses 'max_tokens' directly, not 'max_tokens_to_sample' in latest versions
                response = client.messages.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=params.get("temperature", 0.5),
                    max_tokens=params.get("max_tokens", 512),
                )
                output_text = response.content[0].text
                in_tokens = response.usage.input_tokens
                out_tokens = response.usage.output_tokens
                return output_text, in_tokens, out_tokens
            else:
                raise ValueError(f"Unsupported CloudLLM provider for execution: {provider}")

        return self._execute_model_call(model_data, prompt, api_call, "llm_output")

    def execute_edge_llm(self, model_data: Dict[str, Any], prompt: str,
                     params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute EdgeLLM (edge model) task. Aligns with EdgeLLMExecution algorithm.
        Currently assumes LM Studio compatible API endpoint.

        Args:
            model_data: Model configuration dictionary (from initialize_edge_llm).
            prompt: The prompt string.
            params: Dictionary of generation parameters (e.g., temperature, max_tokens).

        Returns:
            Dictionary containing 'generated_text', token counts, and 'metrics'. Includes 'error' on failure.
        """
        params = params or {}
        model_id = model_data.get("model_id", "unknown")
        client_type = model_data.get("client_type", "").lower()

        # Handle mock execution first
        if model_data.get("mock"):
            mock_instance: MockModel = model_data.get("instance")
            return mock_instance.generate(prompt, **params)

        # --- LM Studio Execution Logic ---
        if client_type == "lm_studio":
            if not requests:
                 return {"error": "`requests` library not installed, cannot call LM Studio.", "generated_text": None, "metrics": {}}

            # --- Ensure correct API endpoint construction ---
            base_url = self.lm_studio_url
            # Add /v1 if it seems missing (basic check)
            if not base_url.endswith('/v1') and '/v1/' not in base_url:
                 # Avoid double slashes if base_url already ends with /
                 if base_url.endswith('/'):
                      base_url += 'v1'
                 else:
                      base_url += '/v1' 
            # Construct the final endpoint URL
            api_url = f"{base_url}/chat/completions"
            self.logger.debug(f"Constructed LM Studio API URL: {api_url}")
            # --- End endpoint construction ---

            # Prepare payload (OpenAI compatible)
            payload = {
                # Use model_id from config for LM Studio, assuming it matches loaded model ID
                "model": model_id, 
                "messages": [{"role": "user", "content": prompt}],
                "temperature": params.get("temperature", 0.7),
                "max_tokens": params.get("max_tokens", 256), # Typically smaller for edge
                "stream": False # Expect single response
            }
            # Handle JSON format requestsj
            json_format_requested = params.get("json_output", False) or (
                isinstance(params.get("response_format"), dict) and 
                params.get("response_format", {}).get("type") == "json_object"
            )
            
            # Since LM Studio doesn't support response_format parameter,
            # we'll modify the prompt to emphasize JSON output when requested
            if json_format_requested and not "json" in prompt.lower():
                # Add explicit JSON formatting instructions
                prompt_addition = "\n\nIMPORTANT: Your response must be a valid JSON object only. Do not include any text outside the JSON object."
                payload["messages"][0]["content"] = prompt + prompt_addition
                self.logger.debug("Added JSON formatting instructions to prompt.")

            headers = {"Content-Type": "application/json"}

            def api_call() -> Tuple[str, int, int]:
                response = requests.post(api_url, headers=headers, json=payload)
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                data = response.json()
                
                # --- Added error handling and logging ---
                try:
                    # Extract response text
                    output_text = data['choices'][0]['message']['content']
                    
                    # Extract token counts if available
                    input_tokens = data.get('usage', {}).get('prompt_tokens', 0)
                    output_tokens = data.get('usage', {}).get('completion_tokens', 0)
                    
                    return output_text, input_tokens, output_tokens
                except KeyError as e:
                    self.logger.error(f"LM Studio response missing expected key: {e}")
                    self.logger.error(f"Full response data from LM Studio: {data}")
                    raise # Re-raise the error after logging
                # --- End added error handling ---

            result = self._execute_model_call(
                model_data=model_data,  # Pass the full model data dict
                prompt=prompt, 
                api_call_func=api_call,
                result_key="generated_text" # Specify the correct output key for EdgeLLM
            )
            
            # Check if JSON repair is needed
            if json_format_requested and not result.get("error"):
                generated_text = result.get("generated_text", "")
                try:
                    # Test if it's valid JSON
                    json.loads(generated_text)
                    # It's valid, no need to repair
                except json.JSONDecodeError:
                    # It's not valid JSON, attempt repair (limit to one attempt)
                    self.logger.warning("EdgeLLM returned invalid JSON, attempting repair...")
                    fixed_text = self.repair_json_output(generated_text, model_data, max_attempts=1)
                    if fixed_text != generated_text:
                        self.logger.info("JSON repaired successfully")
                        result["generated_text"] = fixed_text
                        result["json_repaired"] = True
            
            return result

        else:
            # Placeholder for other EdgeLLM clients (e.g., direct Transformers/llama.cpp)
            self.logger.error(f"EdgeLLM client type '{client_type}' not implemented for execution.")
            return {
                "error": f"EdgeLLM client type '{client_type}' execution not implemented.",
                "generated_text": None,
                "metrics": {}
            }

    def unload_model(self, model_id: str, model_type: str = "edge_llm"):
        """Removes a model from the cache (conceptual unload)."""
        model_key = f"{model_type}:{model_id}"
        if model_key in self.loaded_models:
            del self.loaded_models[model_key]
            self.logger.info(f"Unloaded model {model_key} from cache.")
        else:
            self.logger.warning(f"Model {model_key} not found in cache for unloading.")

    def repair_json_with_llm(self, text: str, model_data: Dict[str, Any], max_attempts: int = 1) -> str:
        """
        Attempts to repair malformed JSON output by making a follow-up model call.
        Uses the new centralized json_utils.repair_json_with_llm function.
        
        Args:
            text: The potentially malformed JSON text
            model_data: The model configuration used to make the repair call
            max_attempts: Maximum number of repair attempts to prevent infinite loops
            
        Returns:
            Fixed JSON string or the original string if repair fails/isn't needed
        """
        from .json_utils import repair_json_with_llm, extract_json_from_text
        
        # Define the LLM repair function that will be called by the utility
        def llm_repair_func(prompt: str, model_data: Dict[str, Any]) -> str:
            # Execute the model with the repair prompt
            params = {
                "temperature": 0.1,
                "max_tokens": 512,
                "json_output": True
            }
            
            result = self.execute_edge_llm(model_data, prompt, params)
            
            if result.get("error"):
                self.logger.warning(f"JSON repair LLM call failed: {result.get('error')}")
                return text  # Return original on failure
                
            return result.get("generated_text", "")
        
        # First check if it's already valid JSON or if we can extract it from markdown
        parsed_json, method = extract_json_from_text(text)
        if parsed_json is not None:
            self.logger.info(f"Already valid JSON or successfully extracted (method: {method})")
            # Convert back to string
            return json.dumps(parsed_json)
        
        # If extraction failed, try repair
        required_keys = ["passed", "score", "feedback"]
        default_values = {
            "passed": False,
            "score": 0.5,
            "feedback": "Failed to parse validation result."
        }
        
        # Call the centralized repair function
        repair_result = repair_json_with_llm(
            text=text,
            llm_repair_func=llm_repair_func,
            model_data=model_data,
            required_keys=required_keys,
            default_values=default_values,
            max_attempts=max_attempts
        )
        
        # Return the result as JSON string
        return json.dumps(repair_result)
        
    # For backwards compatibility
    def repair_json_output(self, text: str, model_data: Dict[str, Any], max_attempts: int = 1) -> str:
        """
        Legacy method for backwards compatibility.
        Uses the new repair_json_with_llm method.
        """
        return self.repair_json_with_llm(text, model_data, max_attempts)
                
    def get_model_info(self, model_id: str, model_type: str = "edge_llm") -> Optional[Dict[str, Any]]:
        """Retrieves configuration details for a given model ID."""
        try:
             config = self.config_loader.load_model_config(model_id)
             if config:
                 # Ensure the type matches (check provider for CloudLLM, client_type for EdgeLLM)
                 is_cloud_llm = model_type == "cloud_llm" and config.get("provider") in ["openai", "anthropic"]
                 is_edge_llm = model_type == "edge_llm" and "local" in config.get("client_type", "").lower()

                 if (is_cloud_llm and model_type == "cloud_llm") or (is_edge_llm and model_type == "edge_llm"):
                      return config
                 else:
                     self.logger.warning(f"Model ID {model_id} found, but type mismatch (expected {model_type}).")
                     return None
             else:
                 return None
        except Exception as e:
            self.logger.error(f"Error retrieving info for model {model_id}: {str(e)}")
            return None