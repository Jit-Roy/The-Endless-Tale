"""
Helper utilities for parsing LLM responses.
"""

import ast
import json
import re
from typing import Dict, Any


def _extract_json_block(text: str) -> str:
    """Extract the first JSON object or array block from the text."""
    brace_start = text.find("{")
    bracket_start = text.find("[")
    if brace_start == -1 and bracket_start == -1:
        return text

    if brace_start == -1:
        start = bracket_start
        end_char = "]"
    elif bracket_start == -1:
        start = brace_start
        end_char = "}"
    else:
        if brace_start < bracket_start:
            start = brace_start
            end_char = "}"
        else:
            start = bracket_start
            end_char = "]"

    end = text.rfind(end_char)
    if end == -1 or end <= start:
        return text
    return text[start:end + 1]


def _repair_json_text(text: str) -> str:
    """Repair common JSON formatting issues produced by LLM output."""
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()
    text = _extract_json_block(text)

    text = re.sub(r",\s*([}\]])", r"\1", text)
    text = re.sub(r'"\s*\n\s*"', r'",\n"', text)
    text = re.sub(r'([0-9truefalsnull])\s*\n\s*"', r"\1,\n\"", text, flags=re.IGNORECASE)
    text = re.sub(r'([}\]"\w])\s*\n\s*"', r"\1,\n\"", text)

    return text


def parse_json_response(response_text: str) -> Dict[str, Any]:
    """
    Parse JSON response from LLM, handling markdown code blocks and minor formatting issues.
    
    Args:
        response_text: Raw response text from the model
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        ValueError: If no parseable JSON-like content is found.
    """
    if response_text is None:
        raise ValueError("Model returned no text to parse.")

    response_text = response_text.strip()
    if not response_text:
        raise ValueError("Model returned an empty response.")

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        repaired = _repair_json_text(response_text)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(repaired)
            except Exception as exc:
                raise ValueError(f"Unable to parse JSON response: {exc}\nOriginal response: {response_text}")
