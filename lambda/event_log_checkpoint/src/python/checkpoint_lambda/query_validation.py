"""Query validation utilities for checkpoint parquet files.

This module provides utility functions for validating that checkpoint
parquet files support the analytical queries required for monthly
reports, specifically filtering by center_label and counting events by
action type.
"""

from typing import Dict, List

import polars as pl
from polars import DataFrame


def filter_by_center_label(df: DataFrame, center_label: str) -> DataFrame:
    """Filter events by center_label.

    Validates requirement 5.1: WHEN querying the checkpoint file by center_label
    THEN the system SHALL return all events for that center efficiently.

    Args:
        df: DataFrame containing checkpoint events
        center_label: Center label to filter by

    Returns:
        DataFrame containing only events for the specified center
    """
    return df.filter(pl.col("center_label") == center_label)


def count_events_by_action(df: DataFrame, action: str) -> int:
    """Count events by specific action type.

    Validates requirement 5.2: WHEN querying for visits with errors
    THEN the system SHALL support counting events where action equals not-pass-qc.

    Args:
        df: DataFrame containing checkpoint events
        action: Action type to count (e.g., "not-pass-qc", "submit",
                "pass-qc", "delete")

    Returns:
        Number of events with the specified action
    """
    return df.filter(pl.col("action") == action).height


def count_not_pass_qc_events(df: DataFrame) -> int:
    """Count events where action equals not-pass-qc.

    Convenience function specifically for requirement 5.2.

    Args:
        df: DataFrame containing checkpoint events

    Returns:
        Number of events with action "not-pass-qc"
    """
    return count_events_by_action(df, "not-pass-qc")


def get_action_counts(df: DataFrame) -> Dict[str, int]:
    """Get counts of all action types in the dataset.

    Args:
        df: DataFrame containing checkpoint events

    Returns:
        Dictionary mapping action types to their counts
    """
    action_counts = df.group_by("action").agg(pl.len().alias("count")).sort("action")

    return dict(
        zip(
            action_counts["action"].to_list(),
            action_counts["count"].to_list(),
            strict=False,
        )
    )


def filter_by_center_and_action(
    df: DataFrame, center_label: str, action: str
) -> DataFrame:
    """Filter events by both center_label and action type.

    Args:
        df: DataFrame containing checkpoint events
        center_label: Center label to filter by
        action: Action type to filter by

    Returns:
        DataFrame containing events matching both criteria
    """
    return df.filter(
        (pl.col("center_label") == center_label) & (pl.col("action") == action)
    )


def count_by_center_and_action(df: DataFrame, center_label: str, action: str) -> int:
    """Count events matching both center_label and action criteria.

    Args:
        df: DataFrame containing checkpoint events
        center_label: Center label to filter by
        action: Action type to filter by

    Returns:
        Number of events matching both criteria
    """
    return filter_by_center_and_action(df, center_label, action).height


def validate_parquet_schema_supports_filtering(df: DataFrame) -> bool:
    """Validate that parquet schema supports efficient filtering operations.

    Checks that key columns have appropriate data types for filtering:
    - center_label: string type for text filtering
    - action: string type for categorical filtering
    - timestamp: datetime type for temporal operations
    - pipeline_adcid: integer type for numeric operations

    Args:
        df: DataFrame to validate

    Returns:
        True if schema supports efficient filtering operations

    Raises:
        ValueError: If schema doesn't support required operations
    """
    schema = df.schema

    # Check required columns exist
    required_columns = ["center_label", "action", "timestamp", "pipeline_adcid"]
    missing_columns = [col for col in required_columns if col not in schema]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Check data types support efficient filtering
    if schema["center_label"] != pl.Utf8:
        raise ValueError(f"center_label must be Utf8, got {schema['center_label']}")

    if schema["action"] != pl.Utf8:
        raise ValueError(f"action must be Utf8, got {schema['action']}")

    # Timestamp should be datetime (polars may convert timezone info)
    if not isinstance(schema["timestamp"], pl.Datetime):
        raise ValueError(f"timestamp must be Datetime, got {schema['timestamp']}")

    # pipeline_adcid should be integer (polars may convert to Int64 in parquet)
    if schema["pipeline_adcid"] not in [pl.Int32, pl.Int64]:
        raise ValueError(
            f"pipeline_adcid must be integer type, got {schema['pipeline_adcid']}"
        )

    return True


def get_centers_list(df: DataFrame) -> List[str]:
    """Get list of unique center labels in the dataset.

    Args:
        df: DataFrame containing checkpoint events

    Returns:
        Sorted list of unique center labels
    """
    return sorted(df["center_label"].unique().to_list())


def get_actions_list(df: DataFrame) -> List[str]:
    """Get list of unique action types in the dataset.

    Args:
        df: DataFrame containing checkpoint events

    Returns:
        Sorted list of unique action types
    """
    return sorted(df["action"].unique().to_list())
