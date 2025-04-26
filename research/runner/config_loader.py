"""
ConfigLoader - Handles loading and validation of test suite configurations.

This module provides functionality to load, validate, and preprocess
configuration files for EdgePrompt experiments.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List

# TODO: Implement full JSON schema validation against PROMPT_ENGINEERING.md schemas
#       using a library like jsonschema for enhanced robustness.

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
        
        # --- Corrected Path Definitions ---
        # Determine paths relative to the location of this file (config_loader.py)
        loader_dir = os.path.dirname(os.path.abspath(__file__))
        # research_dir should be the parent of loader_dir (runner/)
        research_dir = os.path.abspath(os.path.join(loader_dir, '..')) 
        self._configs_dir = os.path.join(research_dir, 'configs')
        self._templates_dir = os.path.join(self._configs_dir, 'templates')
        self._hardware_profiles_file = os.path.join(self._configs_dir, 'hardware_profiles.json')
        self._model_configs_file = os.path.join(self._configs_dir, 'model_configs.json')
        # --- End Correction ---

        # Keep the path to the specific test suite config file provided
        self.config_path = config_path 
        # self.base_dir might still be useful if test cases reference relative paths
        self.base_dir = os.path.dirname(os.path.abspath(config_path))
        
        self.logger.info(f"Initialized ConfigLoader. Test Suite: {config_path}. Base dir for suite: {self.base_dir}")
        self.logger.debug(f"Templates dir: {self._templates_dir}")
        self.logger.debug(f"Configs dir: {self._configs_dir}")
    
    def load_test_suite(self) -> Dict[str, Any]:
        """
        Load the main test suite configuration file.

        Does NOT resolve nested references (templates, models etc.).
        Use specific load methods for those.

        Returns:
            Dict containing the raw test suite configuration.

        Raises:
            FileNotFoundError: If the config file doesn't exist.
            json.JSONDecodeError: If the file is not valid JSON.
            ValueError: If the config is missing required top-level fields.
        """
        self.logger.info(f"Loading test suite from: {self.config_path}")
        try:
            with open(self.config_path, 'r') as f:
                test_suite = json.load(f)
                
            # Validate basic structure
            self._validate_test_suite(test_suite)
            
            # Note: References like templates, models, hardware are NOT resolved here.
            # Other components should use specific load methods as needed.
            self.logger.info(f"Successfully loaded test suite: {test_suite.get('test_suite_id', 'N/A')}")
            return test_suite
            
        except FileNotFoundError:
            self.logger.error(f"Config file not found: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {str(e)}")
            raise
        except ValueError as e: # Catch validation error
            self.logger.error(f"Test suite validation failed: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error loading test suite: {str(e)}", exc_info=True)
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
    
    def _load_config_list_and_find_item(self, file_path: str, item_id: str, id_field: str) -> Optional[Dict[str, Any]]:
        """
        Helper to load a JSON file containing a list of configs and find one by ID.

        Args:
            file_path: Path to the JSON file.
            item_id: The ID of the item to find.
            id_field: The key in each dictionary representing the ID (e.g., 'profile_id').

        Returns:
            The dictionary matching the item_id, or None if not found or error occurs.
        """
        try:
            with open(file_path, 'r') as f:
                config_list = json.load(f)
                if not isinstance(config_list, list):
                    self.logger.error(f"Expected a list in config file {file_path}, found {type(config_list)}")
                    return None

            for item in config_list:
                if isinstance(item, dict) and item.get(id_field) == item_id:
                    return item

            self.logger.warning(f"Item with {id_field} '{item_id}' not found in {file_path}")
            return None

        except FileNotFoundError:
            self.logger.error(f"Config file not found: {file_path}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file {file_path}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading/processing {file_path} for {id_field} {item_id}: {str(e)}", exc_info=True)
            return None
    
    def load_hardware_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific hardware profile configuration.
        
        Args:
            profile_id: Identifier for the hardware profile
            
        Returns:
            Dict containing the hardware profile or None if not found
        """
        self.logger.debug(f"Attempting to load hardware profile: {profile_id}")
        return self._load_config_list_and_find_item(
            self._hardware_profiles_file, profile_id, 'profile_id'
        )
    
    def load_model_config(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific model configuration from model_configs.json.
        Searches within both 'cloud_llm_models' and 'edge_llm_models' lists.
        
        Args:
            model_id: Identifier for the model
            
        Returns:
            Dict containing the model configuration or None if not found
        """
        self.logger.debug(f"Attempting to load model config: {model_id} from {self._model_configs_file}")
        
        try:
            with open(self._model_configs_file, 'r') as f:
                model_data = json.load(f)

            if not isinstance(model_data, dict):
                self.logger.error(f"Expected a dictionary in {self._model_configs_file}, found {type(model_data)}")
                return None

            # Search in cloud_llm_models (previously llm_l_models)
            cloud_llm_list = model_data.get('cloud_llm_models', [])
            if isinstance(cloud_llm_list, list):
                 for model in cloud_llm_list:
                      if isinstance(model, dict) and model.get('model_id') == model_id:
                           self.logger.debug(f"Found model '{model_id}' in cloud_llm_models.")
                           return model
            else:
                self.logger.warning(f"'cloud_llm_models' key in {self._model_configs_file} is not a list.")

            # Search in edge_llm_models (previously llm_s_models) if not found in cloud_llm_models
            edge_llm_list = model_data.get('edge_llm_models', [])
            if isinstance(edge_llm_list, list):
                 for model in edge_llm_list:
                      if isinstance(model, dict) and model.get('model_id') == model_id:
                           self.logger.debug(f"Found model '{model_id}' in edge_llm_models.")
                           return model
            else:
                 self.logger.warning(f"'edge_llm_models' key in {self._model_configs_file} is not a list.")

            # If not found in either list
            self.logger.warning(f"Model config with id '{model_id}' not found in {self._model_configs_file}")
            return None

        except FileNotFoundError:
            self.logger.error(f"Model config file not found: {self._model_configs_file}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in model config file {self._model_configs_file}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading/processing model config for {model_id}: {str(e)}", exc_info=True)
            return None
    
    def load_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific template configuration.
        
        Args:
            template_name: Name of the template (without .json extension)
            
        Returns:
            Dict containing the template or None if not found
        """
        template_path = os.path.join(self._templates_dir, f"{template_name}.json")
        self.logger.debug(f"Attempting to load template: {template_path}")

        try:
            with open(template_path, 'r') as f:
                template_data = json.load(f)
                # Basic validation: Check for 'id' and 'pattern' which are essential
                if not isinstance(template_data, dict) or \
                   'id' not in template_data or \
                   'pattern' not in template_data:
                    self.logger.error(f"Invalid template structure or missing 'id'/'pattern' key in {template_path}")
                    return None
                return template_data
        except FileNotFoundError:
            self.logger.error(f"Template file not found: {template_path}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in template file {template_path}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading template {template_name} from {template_path}: {str(e)}", exc_info=True)
            return None
    
    def load_validation_sequence(self, sequence_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a validation sequence configuration.
        
        Validation sequences define multi-stage validation workflows and have
        different requirements than prompt templates.
        
        Args:
            sequence_name: Name of the validation sequence (without .json extension)
            
        Returns:
            Dict containing the validation sequence or None if not found/invalid
        """
        sequence_path = os.path.join(self._templates_dir, f"{sequence_name}.json")
        self.logger.debug(f"Attempting to load validation sequence: {sequence_path}")

        try:
            with open(sequence_path, 'r') as f:
                sequence_data = json.load(f)
                
                # Validation sequence-specific validation
                if not isinstance(sequence_data, dict):
                    self.logger.error(f"Invalid validation sequence: not a dictionary in {sequence_path}")
                    return None
                
                # Check essential fields for a validation sequence
                if 'id' not in sequence_data:
                    self.logger.error(f"Invalid validation sequence: missing 'id' in {sequence_path}")
                    return None
                
                if 'stages' not in sequence_data or not isinstance(sequence_data['stages'], list):
                    self.logger.error(f"Invalid validation sequence: missing or invalid 'stages' array in {sequence_path}")
                    return None
                
                # Check that each stage has required fields
                for i, stage in enumerate(sequence_data['stages']):
                    if not isinstance(stage, dict):
                        self.logger.error(f"Invalid validation stage at index {i}: not a dictionary")
                        return None
                    if 'id' not in stage:
                        self.logger.error(f"Invalid validation stage at index {i}: missing 'id'")
                        return None
                    if 'template_id' not in stage:
                        self.logger.error(f"Invalid validation stage at index {i}: missing 'template_id'")
                        return None
                
                self.logger.debug(f"Successfully loaded validation sequence '{sequence_data['id']}' with {len(sequence_data['stages'])} stages")
                return sequence_data
                
        except FileNotFoundError:
            self.logger.error(f"Validation sequence file not found: {sequence_path}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in validation sequence file {sequence_path}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading validation sequence {sequence_name} from {sequence_path}: {str(e)}", exc_info=True)
            return None