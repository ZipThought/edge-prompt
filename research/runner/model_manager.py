"""
ModelManager - Handles loading and initialization of LLM models.

This module provides functionality for loading, initializing, and
managing LLM models for use in EdgePrompt experiments.
"""

import os
import logging
import requests
from typing import Dict, Any, Optional, Union, List

class MockModel:
    """Mock model class for simulation"""
    def __init__(self, name, quantization=None, context_window=2048):
        self.name = name
        self.quantization = quantization
        self.context_window = context_window
        
    def generate(self, prompt, max_tokens=2048, temperature=0.7, **kwargs):
        """Mock generation method"""
        output = f"[Mock output for prompt: {prompt[:30]}...]"
        return {
            'output': output,
            'input_tokens': len(prompt.split()),
            'output_tokens': 10
        }

class ModelManager:
    """
    Manages LLM model configurations and metadata.
    
    This class handles:
    - Managing model metadata for LM Studio integration
    - Verifying model availability via LM Studio API
    - Support for mock models during testing
    """
    
    def __init__(self, model_cache_dir: Optional[str] = None, lm_studio_url: Optional[str] = None):
        """
        Initialize the ModelManager.
        
        Args:
            model_cache_dir: Directory for caching model weights (optional)
            lm_studio_url: Base URL for LM Studio server (optional)
        """
        self.logger = logging.getLogger("edgeprompt.runner.model")
        self.model_cache_dir = model_cache_dir or os.path.join(os.path.expanduser("~"), ".cache", "edgeprompt", "models")
        self.lm_studio_url = lm_studio_url
        self._ensure_cache_dir()
        self.loaded_models = {}
        self.logger.info(f"ModelManager initialized with cache dir: {self.model_cache_dir}")
        if self.lm_studio_url:
            self.logger.info(f"LM Studio URL: {self.lm_studio_url}")
    
    def _ensure_cache_dir(self) -> None:
        """Create the model cache directory if it doesn't exist"""
        if not os.path.exists(self.model_cache_dir):
            os.makedirs(self.model_cache_dir, exist_ok=True)
            self.logger.info(f"Created model cache directory: {self.model_cache_dir}")
    
    def initialize_model(self, model_id: str, model_config: Optional[Dict[str, Any]] = None, mock_mode: bool = False) -> Any:
        """
        Initialize a model for inference.
        
        For LM Studio integration, this primarily verifies that the model
        is available and returns metadata needed by TestExecutor.
        
        Args:
            model_id: Identifier for the model
            model_config: Optional configuration overrides
            mock_mode: Whether to use a mock model instead of real model
            
        Returns:
            Model metadata dictionary or MockModel instance
            
        Raises:
            ValueError: If model cannot be found or initialized
        """
        self.logger.info(f"Initializing model: {model_id} (mock_mode={mock_mode})")
        
        # Use mock model if requested
        if mock_mode:
            self.logger.info(f"Using mock model for {model_id}")
            mock_model = MockModel(
                name=model_id,
                quantization=model_config.get('quantization', 'int8') if model_config else 'int8',
                context_window=model_config.get('context_window', 2048) if model_config else 2048
            )
            self.loaded_models[model_id] = mock_model
            return mock_model
        
        # Check if already loaded
        if model_id in self.loaded_models:
            self.logger.info(f"Using already loaded model: {model_id}")
            return self.loaded_models[model_id]
        
        # Get model details
        model_details = self._get_model_details(model_id, model_config)
        
        # Verify the model has an API identifier for LM Studio
        if 'api_identifier' not in model_details:
            error_msg = f"Model {model_id} lacks required 'api_identifier' for LM Studio integration"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Verify model availability in LM Studio (if URL is provided)
        if self.lm_studio_url:
            if not self.check_model_availability(model_details['api_identifier']):
                error_msg = f"Model {model_details['api_identifier']} not available in LM Studio"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
        
        # For LM Studio, we just need to return the API identifier and basic metadata
        model_metadata = {
            'api_identifier': model_details['api_identifier'],
            'model_id': model_id
        }
        
        # Cache the model metadata
        self.loaded_models[model_id] = model_metadata
        
        self.logger.info(f"Model {model_id} initialized successfully with api_identifier: {model_details['api_identifier']}")
        return model_metadata
    
    def check_model_availability(self, api_identifier: str) -> bool:
        """
        Check if a model is available in LM Studio.
        
        Args:
            api_identifier: Model identifier in LM Studio
            
        Returns:
            True if model is available, False otherwise
        """
        if not self.lm_studio_url:
            self.logger.warning("Cannot check model availability: LM Studio URL not provided")
            return True  # Assume available if no URL
        
        try:
            # Query the LM Studio API for available models
            url = f"{self.lm_studio_url}/v1/models"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                self.logger.error(f"Failed to query LM Studio models: {response.status_code}")
                return False
            
            # Parse the response
            data = response.json()
            available_models = [model['id'] for model in data.get('data', [])]
            
            # Check if the requested model is available
            is_available = api_identifier in available_models
            if is_available:
                self.logger.info(f"Model {api_identifier} is available in LM Studio")
            else:
                self.logger.warning(f"Model {api_identifier} not found in LM Studio. Available models: {available_models}")
            
            return is_available
            
        except Exception as e:
            self.logger.error(f"Error checking model availability: {str(e)}")
            return False
    
    def _get_model_details(self, model_id: str, config_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get model details by ID, with optional configuration overrides.
        
        Args:
            model_id: Identifier for the model
            config_override: Optional configuration overrides
            
        Returns:
            Dict containing model details
            
        Raises:
            ValueError: If model ID is unknown
        """
        # In a real implementation, this would load from a configuration source
        # For this scaffold, we'll use hardcoded examples
        model_configs = {
            "gemma-3-12b-it": {
                "base_model": "gemma-3-12b",
                "quantization": "GGUF",
                "context_window": 128000,
                "download_url": "https://model.lmstudio.ai/download/lmstudio-community/gemma-3-12b-it-GGUF",
                "local_path": os.path.join(self.model_cache_dir, "gemma-3-12b"),
                "api_identifier": "gemma-3-12b-it",
                "optimization": {
                    "kv_cache": True,
                    "flash_attention": True,
                    "tensor_parallelism": False,
                    "execution_provider": "CUDA"
                }
            },
            "gemma-3-4b-it": {
                "base_model": "gemma-3-4b",
                "quantization": "GGUF",
                "context_window": 128000,
                "download_url": "https://model.lmstudio.ai/download/lmstudio-community/gemma-3-4b-it-GGUF",
                "local_path": os.path.join(self.model_cache_dir, "gemma-3-4b"),
                "api_identifier": "gemma-3-4b-it",
                "optimization": {
                    "kv_cache": True,
                    "flash_attention": True,
                    "tensor_parallelism": False,
                    "execution_provider": "CUDA"
                }
            },
            "llama-3.2-3b-instruct": {
                "base_model": "llama-3.2-3b",
                "quantization": "Q8_0",
                "context_window": 128000,
                "download_url": "https://model.lmstudio.ai/download/hugging-quants/Llama-3.2-3B-Instruct-Q8_0-GGUF",
                "local_path": os.path.join(self.model_cache_dir, "llama-3.2-3b"),
                "api_identifier": "llama-3.2-3b-instruct",
                "optimization": {
                    "kv_cache": True,
                    "flash_attention": True,
                    "tensor_parallelism": False,
                    "execution_provider": "CUDA"
                }
            }
        }
        
        if model_id not in model_configs:
            self.logger.error(f"Unknown model ID: {model_id}")
            raise ValueError(f"Unknown model ID: {model_id}")
        
        model_details = model_configs[model_id].copy()
        
        # Apply any configuration overrides
        if config_override:
            # Recursively update nested dictionaries
            for key, value in config_override.items():
                if isinstance(value, dict) and key in model_details and isinstance(model_details[key], dict):
                    model_details[key].update(value)
                else:
                    model_details[key] = value
        
        return model_details
        
    def unload_model(self, model_id: str) -> None:
        """
        Unload a model from memory.
        
        For LM Studio integration, this simply removes the cached metadata.
        
        Args:
            model_id: Identifier for the model to unload
        """
        if model_id in self.loaded_models:
            self.logger.info(f"Unloading model: {model_id}")
            del self.loaded_models[model_id]
        else:
            self.logger.warning(f"Model not loaded: {model_id}")
            
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """
        Get information about a model.
        
        Args:
            model_id: Identifier for the model
            
        Returns:
            Dict containing model information
            
        Raises:
            ValueError: If model ID is unknown
        """
        model_details = self._get_model_details(model_id)
        
        # Remove sensitive or unnecessary information
        if 'download_url' in model_details:
            del model_details['download_url']
            
        if 'local_path' in model_details:
            del model_details['local_path']
            
        return model_details 