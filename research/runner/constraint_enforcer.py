"""
ConstraintEnforcer - Handles enforcement of logical constraints on generated content.

This module provides functionality for enforcing constraints like word count limits,
prohibited keywords, and topic relevance for the EdgePrompt framework.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Union

class ConstraintEnforcer:
    """
    Enforces simple, logical constraints on generated content.

    Implements the *lightweight* ConstraintEnforcement algorithm (Phase 1 Focus)
    from PROMPT_ENGINEERING.md, Sec 2.1. Checks are designed to be fast and
    deterministic, suitable for orchestration layers.
    - Word count limits
    - Prohibited keywords (case-insensitive, whole word)
    - Required topics (basic keyword overlap heuristic)
    - Basic format checks (e.g., JSON start/end markers)
    """
    
    def __init__(self):
        """Initialize the ConstraintEnforcer"""
        self.logger = logging.getLogger("edgeprompt.runner.constraints")
        self.logger.info("ConstraintEnforcer initialized")
    
    def enforce_constraints(self, content: str, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applies the configured lightweight constraints to the given content.

        Args:
            content: The text content to check.
            constraints: Dictionary defining the constraints to enforce, based on
                         Phase 1 spec (e.g., {minWords: 50, maxWords: 100,
                         prohibitedKeywords: ["badword"], requiredTopic: "roots"}).

        Returns:
            Dict containing results: {'passed': bool, 'violations': list[str]}
        """
        if not isinstance(content, str):
            self.logger.warning("ConstraintEnforcer received non-string content, cannot enforce.")
            return {"passed": False, "violations": ["Input content was not a string."]}
        
        self.logger.debug(f"Enforcing constraints on content (length: {len(content)}). Constraints: {constraints.keys()}")
        
        # Initialize result
        enforcement_result = {
            "passed": True,
            "violations": []
        }
        
        # Word count constraints
        if "minWords" in constraints or "maxWords" in constraints:
            word_count = self._count_words(content)
            min_words = constraints.get("minWords") # Can be None
            max_words = constraints.get("maxWords") # Can be None
            
            if min_words is not None and word_count < min_words:
                enforcement_result["passed"] = False
                violation_msg = f"Word count {word_count} below minimum {min_words}"
                enforcement_result["violations"].append(violation_msg)
                self.logger.debug(f"Constraint violation: {violation_msg}")
                
            if max_words is not None and word_count > max_words:
                enforcement_result["passed"] = False
                violation_msg = f"Word count {word_count} exceeds maximum {max_words}"
                enforcement_result["violations"].append(violation_msg)
                self.logger.debug(f"Constraint violation: {violation_msg}")
        
        # Prohibited keywords check
        prohibited_keywords = constraints.get("prohibitedKeywords")
        if isinstance(prohibited_keywords, list):
            for keyword in prohibited_keywords:
                if isinstance(keyword, str) and self._contains_keyword(content, keyword):
                    enforcement_result["passed"] = False
                    violation_msg = f"Prohibited keyword '{keyword}' found"
                    enforcement_result["violations"].append(violation_msg)
                    self.logger.debug(f"Constraint violation: {violation_msg}")
                    # Keep checking for other keywords
        
        # Required topic check (basic implementation)
        required_topic = constraints.get("requiredTopic")
        if isinstance(required_topic, str):
            if not self._topic_is_present(content, required_topic):
                enforcement_result["passed"] = False
                violation_msg = f"Content does not appear to address required topic '{required_topic}' (basic check)"
                enforcement_result["violations"].append(violation_msg)
                self.logger.debug(f"Constraint violation: {violation_msg}")
        
        # Format check (if specified)
        required_format = constraints.get("format")
        if isinstance(required_format, str):
            if required_format.lower() == "json":
                # Basic JSON validation check
                stripped_content = content.strip()
                if not (stripped_content.startswith('{') and stripped_content.endswith('}')) and \
                   not (stripped_content.startswith('[') and stripped_content.endswith(']')): # Allow JSON arrays too
                    enforcement_result["passed"] = False
                    violation_msg = f"Content does not appear to be in required JSON format (basic check)"
                    enforcement_result["violations"].append(violation_msg)
                    self.logger.debug(f"Constraint violation: {violation_msg}")

        # Log summary
        if enforcement_result["passed"]:
            self.logger.debug("All constraints passed")
        else:
            self.logger.info(f"Constraint enforcement failed with {len(enforcement_result['violations'])} violations: {enforcement_result['violations']}")
            
        return enforcement_result
    
    def _count_words(self, text: str) -> int:
        """Counts words using regex for word boundaries."""
        if not isinstance(text, str): return 0
        return len(re.findall(r'\b\w+\b', text))
    
    def _contains_keyword(self, text: str, keyword: str) -> bool:
        """Checks if text contains keyword (case-insensitive, whole word only)."""
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