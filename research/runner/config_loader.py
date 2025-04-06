"""
ConfigLoader - Handles loading and validation of test suite configurations.

This module provides functionality to load, validate, and preprocess
configuration files for EdgePrompt experiments.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List

class ConfigLoader:
    """
    Responsible for loading and validating configuration files.
    
    This class handles:
    - Loading test suite configurations
    - Validating against expected schemas
    - Resolving file paths and dependencies
    - Preprocessing configurations for use by other components
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the ConfigLoader.
        
        Args:
            config_path: Path to the main configuration file or directory
        """
        self.logger = logging.getLogger("edgeprompt.runner.config")
        self.config_path = config_path
        self.base_dir = os.path.dirname(os.path.abspath(config_path))
        self.logger.info(f"Initialized ConfigLoader with path: {config_path}")
    
    def load_test_suite(self) -> Dict[str, Any]:
        """
        Load the test suite configuration from the specified path.
        
        Returns:
            Dict containing the test suite configuration
        """
        self.logger.info(f"Loading test suite from: {self.config_path}")
        try:
            with open(self.config_path, 'r') as f:
                test_suite = json.load(f)
                
            # Validate basic structure
            self._validate_test_suite(test_suite)
            
            # Resolve additional resources
            self._resolve_references(test_suite)
            
            return test_suite
            
        except FileNotFoundError:
            self.logger.error(f"Config file not found: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading test suite: {str(e)}")
            raise
    
    def _validate_test_suite(self, test_suite: Dict[str, Any]) -> None:
        """
        Validate the basic structure of a test suite configuration.
        
        Args:
            test_suite: The test suite configuration to validate
            
        Raises:
            ValueError: If the configuration is missing required fields
        """
        required_fields = ['test_suite_id', 'description', 'templates', 'models', 'test_cases']
        missing = [field for field in required_fields if field not in test_suite]
        
        if missing:
            error_msg = f"Test suite configuration missing required fields: {', '.join(missing)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _resolve_references(self, test_suite: Dict[str, Any]) -> None:
        """
        Resolve template and resource references in the test suite.
        
        This loads additional files referenced by the test suite, such as:
        - Template definitions
        - Hardware profiles
        - Model configurations
        - Validation sequences
        
        Args:
            test_suite: The test suite configuration to enhance with resolved references
        """
        # Resolve templates
        if isinstance(test_suite.get('templates', []), list):
            for i, template_name in enumerate(test_suite['templates']):
                template_path = os.path.join(
                    self.base_dir, 
                    '..', 'templates', 
                    f"{template_name}.json"
                )
                try:
                    if os.path.exists(template_path):
                        with open(template_path, 'r') as f:
                            self.logger.info(f"Loading template: {template_path}")
                            test_suite[f'template_data_{i}'] = json.load(f)
                except Exception as e:
                    self.logger.warning(f"Could not load template {template_name}: {str(e)}")
        
        # Resolve hardware profiles if not already loaded
        if isinstance(test_suite.get('hardware_profiles', []), list) and not test_suite.get('hardware_profile_data'):
            hardware_path = os.path.join(
                self.base_dir, 
                '..', 'hardware_profiles.json'
            )
            try:
                if os.path.exists(hardware_path):
                    with open(hardware_path, 'r') as f:
                        self.logger.info(f"Loading hardware profiles: {hardware_path}")
                        all_profiles = json.load(f)
                        # Filter to just the ones we need
                        test_suite['hardware_profile_data'] = [
                            profile for profile in all_profiles 
                            if profile.get('profile_id') in test_suite['hardware_profiles']
                        ]
            except Exception as e:
                self.logger.warning(f"Could not load hardware profiles: {str(e)}")
                
        # Resolve model configs
        if isinstance(test_suite.get('models', []), list) and not test_suite.get('model_data'):
            model_path = os.path.join(
                self.base_dir, 
                '..', 'model_configs.json'
            )
            try:
                if os.path.exists(model_path):
                    with open(model_path, 'r') as f:
                        self.logger.info(f"Loading model configs: {model_path}")
                        all_models = json.load(f)
                        # Filter to just the ones we need
                        test_suite['model_data'] = [
                            model for model in all_models 
                            if model.get('model_id') in test_suite['models']
                        ]
            except Exception as e:
                self.logger.warning(f"Could not load model configs: {str(e)}")
    
    def load_hardware_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific hardware profile configuration.
        
        Args:
            profile_id: Identifier for the hardware profile
            
        Returns:
            Dict containing the hardware profile or None if not found
        """
        hardware_path = os.path.join(
            self.base_dir, 
            '..', 'hardware_profiles.json'
        )
        
        try:
            with open(hardware_path, 'r') as f:
                profiles = json.load(f)
                
            for profile in profiles:
                if profile.get('profile_id') == profile_id:
                    return profile
                    
            self.logger.warning(f"Hardware profile not found: {profile_id}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading hardware profile {profile_id}: {str(e)}")
            return None
    
    def load_model_config(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific model configuration.
        
        Args:
            model_id: Identifier for the model
            
        Returns:
            Dict containing the model configuration or None if not found
        """
        model_path = os.path.join(
            self.base_dir, 
            '..', 'model_configs.json'
        )
        
        try:
            with open(model_path, 'r') as f:
                models = json.load(f)
                
            for model in models:
                if model.get('model_id') == model_id:
                    return model
                    
            self.logger.warning(f"Model configuration not found: {model_id}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading model configuration {model_id}: {str(e)}")
            return None
    
    def load_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific template configuration.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Dict containing the template or None if not found
        """
        template_path = os.path.join(
            self.base_dir, 
            '..', 'templates', 
            f"{template_name}.json"
        )
        
        try:
            with open(template_path, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.error(f"Error loading template {template_name}: {str(e)}")
            return None 