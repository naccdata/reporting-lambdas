"""String manipulation and formatting utilities."""

import json
import re
from typing import Any, Dict, List, Optional


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """Sanitize filename by replacing invalid characters.

    Args:
        filename: Original filename
        replacement: Character to replace invalid characters with

    Returns:
        Sanitized filename safe for filesystem use
    """
    # Remove or replace characters that are invalid in filenames
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(invalid_chars, replacement, filename)

    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip(". ")

    # Ensure filename is not empty
    if not sanitized:
        sanitized = "unnamed_file"

    return sanitized


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to maximum length with optional suffix.

    Args:
        text: String to truncate
        max_length: Maximum allowed length
        suffix: Suffix to add when truncating

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text

    if len(suffix) >= max_length:
        return text[:max_length]

    return text[: max_length - len(suffix)] + suffix


def camel_to_snake(camel_str: str) -> str:
    """Convert camelCase string to snake_case.

    Args:
        camel_str: String in camelCase format

    Returns:
        String in snake_case format
    """
    # Insert underscore before uppercase letters (except at start)
    snake_str = re.sub("([a-z0-9])([A-Z])", r"\1_\2", camel_str)
    return snake_str.lower()


def snake_to_camel(snake_str: str) -> str:
    """Convert snake_case string to camelCase.

    Args:
        snake_str: String in snake_case format

    Returns:
        String in camelCase format
    """
    components = snake_str.split("_")
    return components[0] + "".join(word.capitalize() for word in components[1:])


def extract_numbers(text: str) -> List[float]:
    """Extract all numbers from a string.

    Args:
        text: String to extract numbers from

    Returns:
        List of numbers found in the string
    """
    # Pattern to match integers and floats (including negative)
    pattern = r"-?\d+\.?\d*"
    matches = re.findall(pattern, text)

    numbers = []
    for match in matches:
        try:
            if "." in match:
                numbers.append(float(match))
            else:
                numbers.append(float(int(match)))
        except ValueError:
            continue

    return numbers


def mask_sensitive_data(text: str, patterns: Optional[Dict[str, str]] = None) -> str:
    """Mask sensitive data in strings using regex patterns.

    Args:
        text: Text to mask
        patterns: Dictionary of pattern names to regex patterns

    Returns:
        Text with sensitive data masked
    """
    if patterns is None:
        patterns = {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
            "ssn": r"\b\d{3}-?\d{2}-?\d{4}\b",
            "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        }

    masked_text = text
    for pattern_name, pattern in patterns.items():
        masked_text = re.sub(pattern, f"[MASKED_{pattern_name.upper()}]", masked_text)

    return masked_text


def format_bytes(bytes_count: int) -> str:
    """Format byte count to human-readable string.

    Args:
        bytes_count: Number of bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    if bytes_count == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    size = float(bytes_count)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Safely parse JSON string with fallback default.

    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails

    Returns:
        Parsed JSON data or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text by collapsing multiple spaces and trimming.

    Args:
        text: Text to normalize

    Returns:
        Text with normalized whitespace
    """
    # Replace multiple whitespace characters with single space
    normalized = re.sub(r"\s+", " ", text)
    # Trim leading and trailing whitespace
    return normalized.strip()
