"""Date and time utility functions."""

import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Union


def parse_iso_datetime(iso_string: str) -> datetime:
    """Parse ISO format datetime string.

    Args:
        iso_string: ISO format datetime string

    Returns:
        Parsed datetime object

    Raises:
        ValueError: If string cannot be parsed
    """
    try:
        # Handle various ISO formats
        if iso_string.endswith("Z"):
            iso_string = iso_string[:-1] + "+00:00"

        return datetime.fromisoformat(iso_string)
    except ValueError as e:
        raise ValueError(f"Invalid ISO datetime format: {iso_string}") from e


def to_iso_string(dt: datetime) -> str:
    """Convert datetime to ISO format string.

    Args:
        dt: Datetime object to convert

    Returns:
        ISO format datetime string
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.isoformat()


def get_utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def get_date_range(
    start_date: Union[str, date], end_date: Union[str, date]
) -> list[date]:
    """Generate list of dates between start and end dates (inclusive).

    Args:
        start_date: Start date (string in YYYY-MM-DD format or date object)
        end_date: End date (string in YYYY-MM-DD format or date object)

    Returns:
        List of date objects
    """
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)

    if start_date > end_date:
        raise ValueError("start_date must be before or equal to end_date")

    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)

    return dates


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "2h 30m 15s")
    """
    if seconds < 0:
        return "0s"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def parse_date_from_filename(
    filename: str, pattern: Optional[str] = None
) -> Optional[date]:
    """Extract date from filename using regex pattern.

    Args:
        filename: Filename to parse
        pattern: Optional regex pattern (default looks for YYYYMMDD or YYYY-MM-DD)

    Returns:
        Parsed date or None if not found
    """
    if pattern is None:
        # Default patterns for common date formats
        patterns = [
            r"(\d{4}-\d{2}-\d{2})",  # YYYY-MM-DD
            r"(\d{8})",  # YYYYMMDD
            r"(\d{4}_\d{2}_\d{2})",  # YYYY_MM_DD
        ]
    else:
        patterns = [pattern]

    for pat in patterns:
        match = re.search(pat, filename)
        if match:
            date_str = match.group(1)
            try:
                if "-" in date_str:
                    return date.fromisoformat(date_str)
                elif "_" in date_str:
                    return datetime.strptime(date_str, "%Y_%m_%d").date()
                elif len(date_str) == 8:
                    return datetime.strptime(date_str, "%Y%m%d").date()
            except ValueError:
                continue

    return None


def get_business_days_between(start_date: date, end_date: date) -> int:
    """Calculate number of business days between two dates.

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        Number of business days (Monday-Friday)
    """
    if start_date > end_date:
        return 0

    business_days = 0
    current_date = start_date

    while current_date <= end_date:
        # Monday = 0, Sunday = 6
        if current_date.weekday() < 5:  # Monday to Friday
            business_days += 1
        current_date += timedelta(days=1)

    return business_days
