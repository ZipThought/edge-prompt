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
from typing import Dict, Any, Optional, Union

class MockModel:
    """
    Facilitates development and testing without requiring actual model access.
    
    This approach:
    - Speeds up development by removing dependency on heavyweight models
    - Ensures reproducible tests even in CI/CD environments without model access
    - Provides deterministic responses for reliable test validation
    - Eliminates network latency and API costs during development
    """
    
    def __init__(self, model_id: str):
        """
        Retains model identity to maintain traceability in mock scenarios.
        
        Preserving identity:
        - Ensures mock outputs can be traced to specific model configurations
        - Allows model-specific mock behavior when needed
        - Maintains consistency in logs and output analysis
        """
        self.model_id = model_id
        
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Provides predictable outputs to enable reliable testing.
        
        Deterministic generation:
        - Enables exact test assertions without variability
        - Simplifies debugging by removing model randomness
        - Creates reproducible test scenarios across environments
        """
        return f"MOCK RESPONSE from model {self.model_id}: This is a response to your prompt"
        
class ModelManager:
    """
    Abstracts model access to enable flexibility and consistency across experiments.
    
    This abstraction:
    - Decouples experiment code from specific model implementations
    - Provides a single point for model validation and configuration
    - Enables transparent switching between real and mock models
    - Centralizes error handling and resource management
    """
    
    def __init__(self, model_cache_dir: Optional[str] = None, 
                lm_studio_url: Optional[str] = None):
        """
        Supports flexible configuration to accommodate different environments and use cases.
        
        This flexibility:
        - Enables running in various environments without code changes
        - Allows customization for different storage constraints and network setups
        - Supports both development and production configurations
        - Facilitates testing with environment-specific settings
        """
        self.logger = logging.getLogger("edgeprompt.runner.model_manager")
        
        # Configure cache directory to persist across sessions while remaining user-specific
        self.model_cache_dir = model_cache_dir or os.path.expanduser("~/.edgeprompt/models")
        self._ensure_cache_dir()
        
        # Allow URL configuration to support different deployment scenarios
        self.lm_studio_url = lm_studio_url or os.environ.get("LM_STUDIO_URL", "http://localhost:1234")
        
        # Cache loaded models to prevent redundant initialization and improve performance
        self.loaded_models = {}
        
        # Centralize configuration to ensure consistency across the application
        self.model_configs = self._load_model_configs()
        
    def _ensure_cache_dir(self):
        """
        Prevents runtime errors by validating cache directory access early.
        
        Early validation:
        - Fails fast with clear error messages rather than during model loading
        - Ensures permissions are appropriate before attempting model operations
        - Creates necessary directory structure to avoid scattered mkdir calls
        """
        try:
            os.makedirs(self.model_cache_dir, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create model cache directory: {str(e)}")
            raise RuntimeError(f"Cannot create model cache directory: {str(e)}")
            
    def _load_model_configs(self) -> Dict[str, Any]:
        """
        Centralizes model configuration to reduce duplication and increase consistency.
        
        This centralization:
        - Provides a single source of truth for model parameters
        - Simplifies adding or updating models across the system
        - Reduces the risk of inconsistent configurations
        - Improves maintainability by isolating configuration changes
        """
        # Get the research root directory and look for the config file in configs/
        research_root = Path(__file__).parent.parent  # Go up one level from runner/ to research/
        config_path = research_root / "configs" / "model_configs.json"
        
        if not config_path.exists():
            self.logger.warning(f"Model configuration file not found at {config_path}")
            return {}
            
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
                # Convert list to dict keyed by model_id for easier lookup
                config_dict = {}
                for model in config_data:
                    if "model_id" in model:
                        config_dict[model["model_id"]] = model
                
                return config_dict
        except Exception as e:
            self.logger.error(f"Failed to load model configurations: {str(e)}")
            return {}
            
    def initialize_model(self, model_id: str, 
                         model_config: Optional[Dict[str, Any]] = None,
                         mock_mode: bool = False) -> Union[Dict[str, Any], MockModel]:
        """
        Abstracts model initialization to isolate complexity from experiment code.
        
        This abstraction:
        - Shields experiments from model-specific initialization details
        - Enables switching between real and mock models transparently
        - Centralizes error handling for more robust experiments
        - Provides a consistent interface regardless of model implementation
        """
        # Support mock mode for faster development and testing
        if mock_mode:
            self.logger.info(f"Initializing mock model for {model_id}")
            mock = MockModel(model_id)
            
            # Include mock flag to ensure downstream code knows this is a mock
            model_metadata = self._get_model_details(model_id, model_config)
            model_metadata["mock"] = True
            model_metadata["instance"] = mock
            
            return model_metadata
            
        # Reuse existing model instances to prevent resource duplication
        if model_id in self.loaded_models:
            self.logger.info(f"Using already initialized model: {model_id}")
            return self.loaded_models[model_id]
            
        # Retrieve model configuration with validation
        model_details = self._get_model_details(model_id, model_config)
        
        # Validate model availability before returning to prevent downstream failures
        if "api_identifier" in model_details:
            api_id = model_details["api_identifier"]
            if not self.check_model_availability(api_id):
                raise ValueError(f"Model {api_id} not available in LM Studio")
                
        # Cache for future requests to improve performance
        self.loaded_models[model_id] = model_details
        return model_details
        
    def check_model_availability(self, api_identifier: str) -> bool:
        """
        Validates model availability early to prevent failures during experiments.
        
        Early validation:
        - Fails before experiment execution rather than during critical sections
        - Provides immediate feedback on configuration or connection issues
        - Prevents wasted resources on experiments that would eventually fail
        - Improves error messages by identifying missing models explicitly
        """
        try:
            # Import at runtime to avoid dependency when using mock models
            from openai import OpenAI
            
            client = OpenAI(
                base_url=f"{self.lm_studio_url}/v1",
                api_key="lm-studio"
            )
            
            # Check against available models to confirm accessibility
            models = client.models.list()
            
            for model in models.data:
                if model.id == api_identifier:
                    self.logger.info(f"Model {api_identifier} is available")
                    return True
                    
            self.logger.warning(f"Model {api_identifier} not found in LM Studio")
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking model availability: {str(e)}")
            return False
            
    def _get_model_details(self, model_id: str, 
                          config_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Balances configuration flexibility with consistency across the system.
        
        This approach:
        - Provides sensible defaults while enabling experiment-specific overrides
        - Ensures core configuration remains consistent even with overrides
        - Enables experimentation with different parameters without changing base configs
        - Maintains backward compatibility when adding new configuration options
        """
        if model_id not in self.model_configs:
            raise ValueError(f"Unknown model ID: {model_id}. Add it to model_configs.json first.")
            
        # Create copy to prevent modifying shared configuration
        model_details = dict(self.model_configs[model_id])
        
        # Apply experimental overrides while preserving base configuration
        if config_override:
            model_details.update(config_override)
            
        return model_details
        
    def unload_model(self, model_id: str):
        """
        Manages resource lifecycle to prevent memory leaks and resource exhaustion.
        
        Explicit resource management:
        - Prevents memory leaks in long-running applications
        - Enables loading multiple models in sequence with limited resources
        - Reduces resource contention in multi-user environments
        - Ensures deterministic cleanup instead of relying on garbage collection
        """
        if model_id in self.loaded_models:
            self.logger.info(f"Unloading model: {model_id}")
            
            # Access model instance for cleanup if available
            model_details = self.loaded_models[model_id]
            model_instance = model_details.get("instance")
            
            # Handle model-specific cleanup operations
            if model_instance and hasattr(model_instance, "unload"):
                model_instance.unload()
                
            # Remove from cache to free memory
            del self.loaded_models[model_id]
            
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """
        Separates information access from resource allocation for efficiency.
        
        This separation:
        - Enables lightweight queries without loading models
        - Supports UI components that display model capabilities
        - Allows filtering available models by attributes
        - Facilitates planning before committing resources
        """
        return self._get_model_details(model_id) 