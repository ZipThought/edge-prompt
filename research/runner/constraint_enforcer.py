"""
ConstraintEnforcer - Handles enforcement of logical constraints on generated content.

This module provides functionality for enforcing constraints like word count limits,
prohibited keywords, and topic relevance for the EdgePrompt framework.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Union

class ConstraintEnforcer:
    """
    Enforces logical constraints on generated content.
    
    This class implements the ConstraintEnforcement algorithm from the
    EdgePrompt methodology, checking content against defined constraints such as:
    - Word count limits
    - Prohibited keywords/content
    - Required topics/content
    - Format requirements
    """
    
    def __init__(self):
        """Initialize the ConstraintEnforcer"""
        self.logger = logging.getLogger("edgeprompt.runner.constraints")
        self.logger.info("ConstraintEnforcer initialized")
    
    def enforce_constraints(self, content: str, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enforce constraints on content.
        
        Args:
            content: String content to check
            constraints: Dictionary of constraints to enforce
            
        Returns:
            Dict with enforcement results: {passed: bool, violations: list}
        """
        self.logger.info(f"Enforcing constraints on content (length: {len(content)})")
        
        # Initialize result
        enforcement_result = {
            "passed": True,
            "violations": []
        }
        
        # Word count constraints
        if "minWords" in constraints or "maxWords" in constraints:
            word_count = self._count_words(content)
            min_words = constraints.get("minWords", 0)
            max_words = constraints.get("maxWords", float('inf'))
            
            if word_count < min_words:
                enforcement_result["passed"] = False
                enforcement_result["violations"].append(
                    f"Word count {word_count} below minimum {min_words}"
                )
                self.logger.info(f"Constraint violation: word count {word_count} below minimum {min_words}")
                
            if word_count > max_words:
                enforcement_result["passed"] = False
                enforcement_result["violations"].append(
                    f"Word count {word_count} exceeds maximum {max_words}"
                )
                self.logger.info(f"Constraint violation: word count {word_count} exceeds maximum {max_words}")
        
        # Prohibited keywords check
        if "prohibitedKeywords" in constraints:
            prohibited_keywords = constraints["prohibitedKeywords"]
            for keyword in prohibited_keywords:
                if self._contains_keyword(content, keyword):
                    enforcement_result["passed"] = False
                    enforcement_result["violations"].append(
                        f"Prohibited keyword '{keyword}' found"
                    )
                    self.logger.info(f"Constraint violation: prohibited keyword '{keyword}' found")
                    # Don't break - collect all violations
        
        # Required topic check (basic implementation)
        if "requiredTopic" in constraints:
            topic = constraints["requiredTopic"]
            if not self._topic_is_present(content, topic):
                enforcement_result["passed"] = False
                enforcement_result["violations"].append(
                    f"Content does not appear to address required topic '{topic}'"
                )
                self.logger.info(f"Constraint violation: required topic '{topic}' not addressed")
        
        # Format check (if specified)
        if "format" in constraints:
            required_format = constraints["format"]
            if required_format.lower() == "json":
                # Basic JSON validation
                if not (content.strip().startswith('{') and content.strip().endswith('}')):
                    enforcement_result["passed"] = False
                    enforcement_result["violations"].append(
                        f"Content does not appear to be in required JSON format"
                    )
                    self.logger.info("Constraint violation: JSON format required but not provided")
        
        # Log summary
        if enforcement_result["passed"]:
            self.logger.info("All constraints passed")
        else:
            self.logger.info(f"Constraint enforcement failed with {len(enforcement_result['violations'])} violations")
            
        return enforcement_result
    
    def _count_words(self, text: str) -> int:
        """Count words in text"""
        return len(re.findall(r'\b\w+\b', text))
    
    def _contains_keyword(self, text: str, keyword: str) -> bool:
        """Check if text contains keyword (case-insensitive)"""
        return re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE) is not None
    
    def _topic_is_present(self, text: str, topic: str) -> bool:
        """
        Basic check if topic is addressed in text.
        
        Note: This is a simple implementation. In a production system,
        this might use embeddings or more sophisticated NLP techniques.
        """
        # Split topic into keywords
        keywords = re.findall(r'\b\w+\b', topic.lower())
        
        # Count how many topic keywords appear in the text
        text_lower = text.lower()
        matched_keywords = sum(1 for keyword in keywords if keyword in text_lower)
        
        # Consider topic present if at least half of keywords are found
        # (minimum 1 keyword for very short topics)
        threshold = max(1, len(keywords) // 2)
        return matched_keywords >= threshold 