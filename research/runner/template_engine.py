"""
TemplateEngine - Handles template processing and variable substitution.

This module is responsible for loading templates and processing them
with variables according to the EdgePrompt specifications.
"""

import logging
import re
import os
import json
from typing import Dict, Any, Optional, List, Tuple

# Local application imports
from .config_loader import ConfigLoader # Assuming ConfigLoader is in the same directory

class TemplateEngine:
    """
    Processes templates with variable substitution and constraint encoding.
    
    This class implements the TemplateProcessing algorithm as specified in the
    EdgePrompt methodology, handling:
    - Template validation against schemas
    - Variable substitution
    - Constraint encoding
    - Token efficiency optimization
    """
    
    # Regex updated slightly to include numbers, matching spec example
    VAR_PATTERN = re.compile(r'\[([a-zA-Z0-9_]+)\]')

    def __init__(self, config_loader: ConfigLoader):
        """
        Initialize the TemplateEngine.
        
        Args:
            config_loader: Instance of ConfigLoader used to load templates.
        """
        self.logger = logging.getLogger("edgeprompt.runner.template")
        self.config_loader = config_loader # Store ConfigLoader instance
        self.logger.info("TemplateEngine initialized")
    
    def process_template(self, template_name: str, variables: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Loads and processes a template according to the TemplateProcessing algorithm.

        Args:
            template_name: The name of the template to load (without .json extension).
            variables: Dictionary of values to substitute into the template pattern.

        Returns:
            A tuple containing:
            - processed_prompt (str | None): The fully processed prompt ready for LLM, or None on error.
            - metadata (Dict[str, Any]): Information about the processing (e.g., template_id, variables used).
        """
        metadata = {"template_name": template_name, "variables_provided": list(variables.keys()), "processing_success": False}
        self.logger.debug(f"Processing template: {template_name} with variables: {list(variables.keys())}")

        # Load template using ConfigLoader
        template = self.config_loader.load_template(template_name)
        if not template:
            self.logger.error(f"Failed to load template: {template_name}")
            metadata["error"] = f"Template '{template_name}' not loaded."
            return None, metadata

        template_id = template.get('id', template_name)
        metadata["template_id"] = template_id

        # === TemplateProcessing Algorithm Steps ===

        # 1. Validate template_instance against template_schema (Basic validation)
        # TODO: Add full schema validation once ConfigLoader supports loading schemas.
        if not all(k in template for k in ['id', 'pattern', 'type']):
            error_msg = f"Template {template_id} missing required keys (id, pattern, type)."
            self.logger.error(error_msg)
            metadata["error"] = error_msg
            return None, metadata

        pattern = template["pattern"]
        template_type = template["type"]
        processed_prompt = pattern

        # 2-4. Variable Extraction & Substitution
        template_vars = template.get("variables", {}) # Get template-defined variables and defaults
        provided_vars = set(variables.keys())
        found_vars_in_pattern = set(self.VAR_PATTERN.findall(pattern))
        metadata["variables_in_pattern"] = list(found_vars_in_pattern)
        
        # Track missing variables for debugging
        missing_vars = []
        
        # First, use provided values where available
        substitution_vars = {}  # The variables we'll actually use
        
        # For each variable found in the pattern...
        for var_name in found_vars_in_pattern:
            if var_name in provided_vars:
                # Use the provided value
                substitution_vars[var_name] = variables[var_name]
            elif var_name in template_vars:
                # Use the default value from template
                default_value = template_vars.get(var_name, "")
                # Handle if the default is a dict (for backward compatibility)
                if isinstance(default_value, dict):
                    default_value = ""
                substitution_vars[var_name] = default_value
                self.logger.debug(f"Variable '{var_name}' not provided, using default from template.")
            else:
                # No default available, use empty string and log warning
                self.logger.warning(f"Variable '{var_name}' found in template '{template_id}' pattern but not provided. Substituting empty string.")
                substitution_vars[var_name] = ""
                missing_vars.append(var_name)
        
        # Add missing vars to metadata for debugging
        if missing_vars:
            metadata["missing_variables"] = missing_vars
            
        # Replace the original variables with our processed ones that include defaults
        variables = substitution_vars

        # Perform substitution
        try:
            for var_name in found_vars_in_pattern:
                value_str = str(variables.get(var_name, "")) # Default to empty string if somehow still missing
                placeholder = f"[{var_name}]"
                processed_prompt = processed_prompt.replace(placeholder, value_str)
        except Exception as e:
            error_msg = f"Error during variable substitution for template {template_id}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            metadata["error"] = error_msg
            return None, metadata

        # 5. Apply explicit constraint encoding
        #    (Using data from `constraints` or `answerSpace` fields in the template)
        constraints_list = template.get("constraints", [])
        answer_space = template.get("answerSpace", {})
        # Combine high-level constraints with specific answerSpace details
        constraint_data = {
            "explicit_list": constraints_list,
            **answer_space # Merge answerSpace dict into constraint data
        }
        formatted_constraint_text = self._format_constraints(constraint_data, template_type)
        processed_prompt = self._apply_constraints(processed_prompt, formatted_constraint_text, template_type)

        # 6. Perform basic token efficiency optimization
        processed_prompt = self._optimize_tokens(processed_prompt)

        # 7. Record metadata (already partially done)
        metadata["processing_success"] = True
        metadata["final_prompt_length_chars"] = len(processed_prompt)
        self.logger.debug(f"Template {template_id} processed successfully.")

        # 8. Return processed prompt and metadata
        return processed_prompt, metadata
    
    def _format_constraints(self, constraint_data: Dict[str, Any], template_type: str) -> str:
        """
        Format constraints based on data from `constraints` list and `answerSpace` object.

        Args:
            constraint_data: Dictionary containing 'explicit_list' and answerSpace key-values.
            template_type: The type of template (affects formatting).

        Returns:
            A formatted string representing the constraints for the prompt.
        """
        lines = []
        # Add explicit constraints first
        explicit_list = constraint_data.get("explicit_list", [])
        if explicit_list:
             lines.extend(explicit_list)

        # Add specific constraints from answerSpace
        if constraint_data.get("minWords") is not None and constraint_data.get("maxWords") is not None:
             lines.append(f"Content length must be between {constraint_data['minWords']} and {constraint_data['maxWords']} words.")
        elif constraint_data.get("maxWords") is not None:
             lines.append(f"Content length must be maximum {constraint_data['maxWords']} words.")

        if constraint_data.get("vocabulary"):
             lines.append(f"Vocabulary must be suitable for: {constraint_data['vocabulary']}.")
        if constraint_data.get("structure"):
             lines.append(f"Use structure: {constraint_data['structure']}.")
        if constraint_data.get("prohibitedContent"):
             prohibited_str = ", ".join(constraint_data["prohibitedContent"])
             lines.append(f"Avoid prohibited content types/topics: {prohibited_str}.")

        # Add any other key-value pairs from answerSpace.other or top-level
        other_constraints = constraint_data.get("other", {})
        for key, value in other_constraints.items():
             lines.append(f"{key.replace('_', ' ').capitalize()}: {value}")

        if not lines:
            return ""

        # Add prefix based on type
        prefix = "CONSTRAINTS:"
        if template_type == "validation":
            prefix = "VALIDATION CRITERIA:"

        # Combine lines with bullet points
        formatted_lines = "\n- ".join(lines)
        return f"{prefix}\n- {formatted_lines}"
    
    def _apply_constraints(self, processed: str, constraint_text: str, template_type: str) -> str:
        """
        Applies the formatted constraint text to the processed prompt.
        Currently appends to the end, following spec example structure.

        Args:
            processed: The prompt processed so far.
            constraint_text: The formatted string of constraints.
            template_type: The type of template being processed.

        Returns:
            The prompt with constraints appended.
        """
        if not constraint_text:
            return processed

        # Append constraints at the end, ensuring separation
        # (Could be made more sophisticated based on template markers if needed)
        return f"{processed.strip()}\n\n{constraint_text}\n" # Ensure newline at end
    
    def _optimize_tokens(self, text: str) -> str:
        """
        Perform basic token optimization (whitespace reduction).
        """
        # 1. Eliminate redundant whitespace (multiple spaces/newlines)
        optimized = re.sub(r'[ \t]+', ' ', text) # Replace multiple spaces/tabs with single space
        optimized = re.sub(r'\n\s*\n', '\n\n', optimized) # Replace multiple newlines with double newline
        optimized = optimized.strip() # Remove leading/trailing whitespace
        return optimized
        
    def preprocess_template_variables(self, template_name: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocesses template variables, adding defaults and checking requirements.
        
        Args:
            template_name: The name of the template to load
            variables: The provided variables
            
        Returns:
            Dict with preprocessed variables including default values
        """
        # Load the template
        template = self.config_loader.load_template(template_name)
        if not template:
            self.logger.error(f"Failed to load template: {template_name} for preprocessing")
            return variables
        
        template_id = template.get('id', template_name)
        processed_vars = variables.copy()
        
        # Check which variables are needed in the pattern
        pattern = template.get("pattern", "")
        needed_vars = set(self.VAR_PATTERN.findall(pattern))
        
        # Get default values
        default_values = template.get("defaultValues", {})
        
        # Get variable definitions
        var_definitions = template.get("variables", {})
        
        # Add default values for missing variables
        for var_name in needed_vars:
            if var_name not in processed_vars and var_name in default_values:
                processed_vars[var_name] = default_values[var_name]
                self.logger.debug(f"Added default value for '{var_name}' in template {template_id}")
                
        # Check for required variables that are still missing
        missing_required = []
        for var_name, var_info in var_definitions.items():
            is_required = isinstance(var_info, dict) and var_info.get('required', False)
            if is_required and var_name in needed_vars and var_name not in processed_vars:
                missing_required.append(var_name)
                # Add placeholder text to indicate missing required variable
                processed_vars[var_name] = f"[MISSING REQUIRED: {var_name}]"
                
        # Log warnings for missing required variables
        if missing_required:
            self.logger.warning(f"Template {template_id} missing required variables: {missing_required}")
            
        return processed_vars
    
    def extract_template_variables(self, template_name: str) -> List[str]:
        """
        Loads a template and extracts all variable placeholders (e.g., [variable_name]).

        Args:
            template_name: The name of the template to load.

        Returns:
            List of variable names found in the template's pattern, or empty list on error.
        """
        template = self.config_loader.load_template(template_name)
        if not template or 'pattern' not in template:
             self.logger.error(f"Cannot extract variables: Failed to load or invalid pattern for template {template_name}")
             return []

        pattern = template.get('pattern', '')
        return self.VAR_PATTERN.findall(pattern)

    def get_template_schema(self, template_type: str) -> Dict[str, Any]:
        """
        Get the JSON schema for a template type.
        
        Args:
            template_type: Type of template
            
        Returns:
            JSON schema dict for validation
        """
        schema_paths = {
            "question_generation": "schemas/teacher_input_template_schema.json",
            "validation": "schemas/validation_sequence_schema.json",
            "rubric": "schemas/rubric_schema.json"
        }
        
        if template_type not in schema_paths:
            self.logger.warning(f"No schema defined for template type: {template_type}")
            return {}
            
        schema_path = schema_paths[template_type]
        if not os.path.isfile(schema_path):
            self.logger.warning(f"Schema file not found: {schema_path}")
            return {}
            
        try:
            with open(schema_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading schema: {str(e)}")
            return {} 