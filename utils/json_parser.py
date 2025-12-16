"""Shared JSON parsing utilities for agents."""

import json
import re
from typing import Dict, Any, Optional


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences from text."""
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            return text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end > start:
            return text[start:end].strip()
    return text


def clean_json_string(json_str: str) -> str:
    """Clean common JSON formatting issues."""
    # Remove trailing commas
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)
    return json_str


def extract_json_from_text(text: str) -> Optional[str]:
    """Extract JSON object from text using regex."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return clean_json_string(match.group(0))
    return None


def parse_json_safe(text: str, fallback_to_extraction: bool = True) -> Dict[str, Any]:
    """
    Safely parse JSON from text, handling common issues.
    
    Args:
        text: Text containing JSON
        fallback_to_extraction: If True, try to extract JSON using regex if direct parsing fails
        
    Returns:
        Parsed JSON as dictionary
        
    Raises:
        ValueError: If JSON cannot be parsed
    """
    if not text or not text.strip():
        raise ValueError("Empty text provided for JSON parsing")
    
    # Strip code fences
    cleaned_text = strip_code_fences(text)
    
    # Try direct JSON parsing
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        if not fallback_to_extraction:
            raise ValueError(f"Could not parse JSON: {cleaned_text[:500]}")
        
        # Try to extract JSON using regex
        extracted = extract_json_from_text(cleaned_text)
        if extracted:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                pass
        
        raise ValueError(f"Could not parse JSON from text: {cleaned_text[:500]}")

