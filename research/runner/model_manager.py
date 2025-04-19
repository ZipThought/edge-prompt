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
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Tuple, Callable

class MockModel:
    """
    Facilitates development and testing without requiring actual model access.
    
    This approach:
    - Speeds up development by removing dependency on heavyweight models
    - Ensures reproducible tests even in CI/CD environments without model access
    - Provides deterministic responses for reliable test validation
    - Eliminates network latency and API costs during development
    """
    
    def __init__(self, model_id: str, model_type: str = "llm_s"):
        """
        Retains model identity to maintain traceability in mock scenarios.
        
        Args:
            model_id: Identifier for the model
            model_type: Type of model ('llm_l' or 'llm_s')
        """
        self.model_id = model_id
        self.model_type = model_type
        
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Provides predictable outputs to enable reliable testing.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            Dict containing generation results
        """
        import random
        import time
        
        # Simulate processing delay based on prompt length and model type
        delay = min(1.0 if self.model_type == "llm_s" else 3.0, len(prompt) * 0.0005)
        time.sleep(delay)
        
        # Generate different mock responses based on model type
        if self.model_type == "llm_l":
            output = f"MOCK LLM-L RESPONSE from {self.model_id}: This simulates a persona response."
            if "json_output" in kwargs and kwargs["json_output"]:
                output = json.dumps({
                    "role": "teacher" if "teacher" in prompt.lower() else "student",
                    "content": f"Mock {self.model_id} response with simulated JSON structure",
                    "evaluation": {
                        "score": random.randint(6, 9),
                        "feedback": "This is mock feedback from the LLM-L model."
                    }
                })
        else:  # llm_s
            output = f"MOCK LLM-S RESPONSE from {self.model_id}: This simulates an edge model response."
            if "json_output" in kwargs and kwargs["json_output"]:
                output = json.dumps({
                    "passed": random.choice([True, True, False]),  # Bias toward passing
                    "score": random.randint(5, 10),
                    "feedback": "This is mock feedback from the LLM-S model."
                })
                
        # Estimate token counts based on input/output length
        prompt_tokens = len(prompt.split())
        completion_tokens = len(output.split())
        
        return {
            "model_id": self.model_id,
            "model_type": self.model_type,
            "output": output,
            "elapsed_seconds": delay,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
        
class ModelManager:
    """
    Abstracts model access to enable flexibility and consistency across experiments.
    
    This class manages both LLM-L (large API models for persona simulation)
    and LLM-S (small models for edge tasks) using appropriate clients.
    """
    
    def __init__(self, model_cache_dir: Optional[str] = None, 
                lm_studio_url: Optional[str] = None,
                openai_api_key: Optional[str] = None,
                anthropic_api_key: Optional[str] = None):
        """
        Supports flexible configuration to accommodate different environments and use cases.
        
        Args:
            model_cache_dir: Directory for caching models
            lm_studio_url: URL for LM Studio API (for LLM-S)
            openai_api_key: OpenAI API key (for LLM-L)
            anthropic_api_key: Anthropic API key (for LLM-L)
        """
        self.logger = logging.getLogger("edgeprompt.runner.model_manager")
        
        # Configure cache directory to persist across sessions
        self.model_cache_dir = model_cache_dir or os.path.expanduser("~/.edgeprompt/models")
        self._ensure_cache_dir()
        
        # Configure API endpoints and keys
        self.lm_studio_url = lm_studio_url or os.environ.get("LM_STUDIO_URL", "http://localhost:1234")
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.anthropic_api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        # Cache loaded models to prevent redundant initialization
        self.loaded_models = {}
        
        # Load model configs (now with llm_l_models and llm_s_models)
        self.model_configs = self._load_model_configs()
        
        # Initialize API clients (lazily)
        self._openai_client = None
        self._anthropic_client = None
        
        self.logger.info(f"ModelManager initialized with {len(self.model_configs.get('llm_l_models', []))} LLM-L models and {len(self.model_configs.get('llm_s_models', []))} LLM-S models")
            
    def _ensure_cache_dir(self):
        """Ensures the model cache directory exists"""
        try:
            os.makedirs(self.model_cache_dir, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create model cache directory: {str(e)}")
            raise RuntimeError(f"Cannot create model cache directory: {str(e)}")
            
    def _load_model_configs(self) -> Dict[str, Any]:
        """Loads model configurations from configs/model_configs.json"""
        # Get the research root directory
        research_root = Path(__file__).parent.parent  # Go up one level from runner/ to research/
        config_path = research_root / "configs" / "model_configs.json"
        
        if not config_path.exists():
            self.logger.warning(f"Model configuration file not found at {config_path}")
            return {"llm_l_models": [], "llm_s_models": []}
            
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
                
                # New structure has llm_l_models and llm_s_models as keys
                if isinstance(config_data, dict) and "llm_l_models" in config_data and "llm_s_models" in config_data:
                    return config_data
                    
                # Legacy format (list of models) - convert to new format
                self.logger.warning("Legacy model config format detected. Converting to new format.")
                return {
                    "llm_l_models": [],
                    "llm_s_models": config_data if isinstance(config_data, list) else []
                }
                
        except Exception as e:
            self.logger.error(f"Failed to load model configurations: {str(e)}")
            return {"llm_l_models": [], "llm_s_models": []}
            
    def initialize_llm_l(self, model_id: str, mock_mode: bool = False) -> Dict[str, Any]:
        """
        Initialize an LLM-L (large API model) for persona simulation.
        
        Args:
            model_id: ID of the model to initialize
            mock_mode: Whether to use a mock model instead of real API
            
        Returns:
            Dict containing model metadata
            
        Raises:
            ValueError: If model ID is unknown or API key is missing
        """
        model_key = f"llm_l:{model_id}"
        
        # Return cached model if available
        if model_key in self.loaded_models and not mock_mode:
            self.logger.info(f"Using cached LLM-L model: {model_id}")
            return self.loaded_models[model_key]
            
        # Use mock model if requested
        if mock_mode:
            self.logger.info(f"Initializing mock LLM-L: {model_id}")
            mock = MockModel(model_id, model_type="llm_l")
            model_data = self._get_llm_l_details(model_id)
            model_data["mock"] = True
            model_data["instance"] = mock
            self.loaded_models[model_key] = model_data
            return model_data
            
        # Get model details
        model_data = self._get_llm_l_details(model_id)
        provider = model_data.get("provider", "").lower()
        
        # Initialize based on provider
        if provider == "openai":
            if not self.openai_api_key:
                raise ValueError(f"OpenAI API key required for model {model_id}")
                
            self.logger.info(f"Initializing OpenAI LLM-L: {model_id}")
            model_data["initialized"] = True
            model_data["client"] = self._get_openai_client()
                
        elif provider == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError(f"Anthropic API key required for model {model_id}")
                
            self.logger.info(f"Initializing Anthropic LLM-L: {model_id}")
            model_data["initialized"] = True
            model_data["client"] = self._get_anthropic_client()
                
        else:
            raise ValueError(f"Unsupported provider for LLM-L: {provider}")
            
        # Cache and return
        self.loaded_models[model_key] = model_data
        return model_data
        
    def initialize_llm_s(self, model_id: str, mock_mode: bool = False) -> Dict[str, Any]:
        """
        Initialize an LLM-S (small model) for edge tasks.
        
        Args:
            model_id: ID of the model to initialize
            mock_mode: Whether to use a mock model
            
        Returns:
            Dict containing model metadata
        """
        model_key = f"llm_s:{model_id}"
        
        # Return cached model if available
        if model_key in self.loaded_models and not mock_mode:
            self.logger.info(f"Using cached LLM-S model: {model_id}")
            return self.loaded_models[model_key]
            
        # Use mock model if requested
        if mock_mode:
            self.logger.info(f"Initializing mock LLM-S: {model_id}")
            mock = MockModel(model_id, model_type="llm_s")
            model_data = self._get_llm_s_details(model_id)
            model_data["mock"] = True
            model_data["instance"] = mock
            self.loaded_models[model_key] = model_data
            return model_data
            
        # Get model details
        model_data = self._get_llm_s_details(model_id)
        client_type = model_data.get("client_type", "").lower()
        
        # Initialize based on client type
        if client_type == "local_gguf":
            self.logger.info(f"Initializing local GGUF LLM-S via LM Studio: {model_id}")
            
            # Verify model availability
            api_id = model_data.get("api_identifier")
            if not self.check_model_availability(api_id):
                raise ValueError(f"Model {api_id} not available in LM Studio")
                
            model_data["initialized"] = True
                
        elif client_type == "api":
            self.logger.info(f"Initializing API-based LLM-S: {model_id}")
            # API-specific initialization would go here
            model_data["initialized"] = True
                
        else:
            raise ValueError(f"Unsupported client_type for LLM-S: {client_type}")
            
        # Cache and return
        self.loaded_models[model_key] = model_data
        return model_data
        
    def _get_openai_client(self):
        """Get or initialize OpenAI client"""
        if self._openai_client is None:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.openai_api_key)
                self.logger.info("OpenAI client initialized")
            except ImportError:
                self.logger.error("Failed to import OpenAI. Install with 'pip install openai'.")
                raise
                
        return self._openai_client
        
    def _get_anthropic_client(self):
        """Get or initialize Anthropic client"""
        if self._anthropic_client is None:
            try:
                import anthropic
                self._anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
                self.logger.info("Anthropic client initialized")
            except ImportError:
                self.logger.error("Failed to import Anthropic. Install with 'pip install anthropic'.")
                raise
                
        return self._anthropic_client
        
    def check_model_availability(self, api_identifier: str) -> bool:
        """
        Validates model availability in LM Studio.
        
        Args:
            api_identifier: API identifier for the model
            
        Returns:
            Boolean indicating if model is available
        """
        try:
            # Import at runtime to avoid dependency when using mock models
            from openai import OpenAI
            
            client = OpenAI(
                base_url=f"{self.lm_studio_url}/v1",
                api_key="lm-studio"
            )
            
            # Check against available models
            models = client.models.list()
            
            for model in models.data:
                if model.id == api_identifier:
                    self.logger.info(f"Model {api_identifier} is available in LM Studio")
                    return True
                    
            self.logger.warning(f"Model {api_identifier} not found in LM Studio")
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking model availability: {str(e)}")
            return False
            
    def _get_llm_l_details(self, model_id: str) -> Dict[str, Any]:
        """
        Get details for an LLM-L model.
        
        Args:
            model_id: ID of the model
            
        Returns:
            Dict containing model details
            
        Raises:
            ValueError: If model ID is unknown
        """
        llm_l_models = self.model_configs.get("llm_l_models", [])
        for model in llm_l_models:
            if model.get("model_id") == model_id:
                # Create a copy to prevent modifying the shared configuration
                return dict(model)
                
        raise ValueError(f"Unknown LLM-L model ID: {model_id}")
        
    def _get_llm_s_details(self, model_id: str) -> Dict[str, Any]:
        """
        Get details for an LLM-S model.
        
        Args:
            model_id: ID of the model
            
        Returns:
            Dict containing model details
            
        Raises:
            ValueError: If model ID is unknown
        """
        llm_s_models = self.model_configs.get("llm_s_models", [])
        for model in llm_s_models:
            if model.get("model_id") == model_id:
                # Create a copy to prevent modifying the shared configuration
                return dict(model)
                
        raise ValueError(f"Unknown LLM-S model ID: {model_id}")
        
    def unload_model(self, model_id: str, model_type: str = "llm_s"):
        """
        Unload a model to free resources.
        
        Args:
            model_id: ID of the model to unload
            model_type: Type of model ('llm_l' or 'llm_s')
        """
        model_key = f"{model_type}:{model_id}"
        
        if model_key in self.loaded_models:
            self.logger.info(f"Unloading {model_type} model: {model_id}")
            
            # Access model instance for cleanup if available
            model_details = self.loaded_models[model_key]
            model_instance = model_details.get("instance")
            
            # Handle model-specific cleanup
            if model_instance and hasattr(model_instance, "unload"):
                model_instance.unload()
                
            # Remove from cache
            del self.loaded_models[model_key]
            
    def execute_llm_l(self, model_data: Dict[str, Any], prompt: str, 
                     params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute an LLM-L model with the given prompt.
        
        Args:
            model_data: Model data from initialize_llm_l
            prompt: The prompt to send
            params: Generation parameters
            
        Returns:
            Dict containing generation results
        """
        import time
        start_time = time.time()
        
        # Set default parameters
        default_params = {
            "temperature": 0.7,
            "max_tokens": 2048,
            "top_p": 0.95
        }
        
        # Apply specific parameters if provided
        execution_params = default_params.copy()
        if params:
            execution_params.update(params)
            
        self.logger.info(f"Executing LLM-L ({model_data['model_id']}) with prompt length: {len(prompt)}")
        
        # Handle mock model
        if model_data.get("mock", False):
            instance = model_data.get("instance")
            return instance.generate(prompt, **execution_params)
            
        # Execute based on provider
        provider = model_data.get("provider", "").lower()
        api_id = model_data.get("api_identifier")
        
        try:
            if provider == "openai":
                # Get client
                client = model_data.get("client", self._get_openai_client())
                
                # Execute OpenAI API call
                response = client.chat.completions.create(
                    model=api_id,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=execution_params["temperature"],
                    max_tokens=execution_params["max_tokens"],
                    top_p=execution_params["top_p"]
                )
                
                # Extract and return results
                output_text = response.choices[0].message.content
                elapsed_time = time.time() - start_time
                
                return {
                    "model_id": api_id,
                    "model_type": "llm_l",
                    "output": output_text,
                    "elapsed_seconds": elapsed_time,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
                
            elif provider == "anthropic":
                # Get client
                client = model_data.get("client", self._get_anthropic_client())
                
                # Execute Anthropic API call
                response = client.messages.create(
                    model=api_id,
                    max_tokens=execution_params["max_tokens"],
                    temperature=execution_params["temperature"],
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                # Extract and return results
                output_text = response.content[0].text
                elapsed_time = time.time() - start_time
                
                return {
                    "model_id": api_id,
                    "model_type": "llm_l",
                    "output": output_text,
                    "elapsed_seconds": elapsed_time,
                    "prompt_tokens": getattr(response, "usage", {}).get("input_tokens", len(prompt.split())),
                    "completion_tokens": getattr(response, "usage", {}).get("output_tokens", len(output_text.split())),
                    "total_tokens": getattr(response, "usage", {}).get("input_tokens", len(prompt.split())) + 
                                   getattr(response, "usage", {}).get("output_tokens", len(output_text.split()))
                }
                
            else:
                raise ValueError(f"Unsupported provider for LLM-L: {provider}")
                
        except Exception as e:
            self.logger.error(f"Error executing LLM-L: {str(e)}")
            
            # Return error information in consistent format
            return {
                "model_id": api_id,
                "model_type": "llm_l",
                "error": str(e),
                "error_type": type(e).__name__,
                "elapsed_seconds": time.time() - start_time
            }
            
    def execute_llm_s(self, model_data: Dict[str, Any], prompt: str, 
                     params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute an LLM-S model with the given prompt.
        
        Args:
            model_data: Model data from initialize_llm_s
            prompt: The prompt to send
            params: Generation parameters
            
        Returns:
            Dict containing generation results
        """
        import time
        start_time = time.time()
        
        # Set default parameters
        default_params = {
            "temperature": 0.7,
            "max_tokens": 2048,
            "top_p": 0.95
        }
        
        # Apply specific parameters if provided
        execution_params = default_params.copy()
        if params:
            execution_params.update(params)
            
        self.logger.info(f"Executing LLM-S ({model_data['model_id']}) with prompt length: {len(prompt)}")
        
        # Handle mock model
        if model_data.get("mock", False):
            instance = model_data.get("instance")
            return instance.generate(prompt, **execution_params)
            
        # Execute based on client type
        client_type = model_data.get("client_type", "").lower()
        api_id = model_data.get("api_identifier")
        
        try:
            if client_type == "local_gguf":
                # Execute via LM Studio API
                from openai import OpenAI
                
                client = OpenAI(
                    base_url=f"{self.lm_studio_url}/v1",
                    api_key="lm-studio"
                )
                
                # Create message format for the API
                messages = [{"role": "user", "content": prompt}]
                
                # Execute the model request
                completion = client.chat.completions.create(
                    model=api_id,
                    messages=messages,
                    temperature=execution_params["temperature"],
                    max_tokens=execution_params["max_tokens"],
                    top_p=execution_params.get("top_p", 0.95)
                )
                
                # Extract output text from response
                output_text = completion.choices[0].message.content
                
                # Calculate metrics for analysis
                elapsed_time = time.time() - start_time
                
                return {
                    "model_id": api_id,
                    "model_type": "llm_s",
                    "output": output_text,
                    "elapsed_seconds": elapsed_time,
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens
                }
                
            elif client_type == "api":
                # Placeholder for other API implementations
                raise NotImplementedError(f"API client type not yet implemented for LLM-S")
                
            else:
                raise ValueError(f"Unsupported client_type for LLM-S: {client_type}")
                
        except Exception as e:
            self.logger.error(f"Error executing LLM-S: {str(e)}")
            
            # Return error information in consistent format
            return {
                "model_id": api_id,
                "model_type": "llm_s",
                "error": str(e),
                "error_type": type(e).__name__,
                "elapsed_seconds": time.time() - start_time
            }
            
    def get_model_info(self, model_id: str, model_type: str = "llm_s") -> Dict[str, Any]:
        """
        Get information about a model without loading it.
        
        Args:
            model_id: ID of the model
            model_type: Type of model ('llm_l' or 'llm_s')
            
        Returns:
            Dict containing model information
        """
        if model_type == "llm_l":
            return self._get_llm_l_details(model_id)
        else:
            return self._get_llm_s_details(model_id) 