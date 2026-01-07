"""Query validation utilities for checkpoint parquet files.

This module provides utility functions for validating that checkpoint
parquet files support the analytical queries required for monthly
reports, specifically filtering by center_label and counting events by
action type, as well as advanced filtering by packet type and date
ranges.
"""

from datetime import datetime
from typing import Dict, List, Optional

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


def filter_by_packet_type(df: DataFrame, packet: str) -> DataFrame:
    """Filter events by packet type.

    Validates requirement 5.5: WHEN querying by packet type THEN the system
    SHALL support filtering and grouping events by the packet field.

    Args:
        df: DataFrame containing checkpoint events
        packet: Packet type to filter by

    Returns:
        DataFrame containing only events for the specified packet type
    """
    return df.filter(pl.col("packet") == packet)


def group_by_packet_type(df: DataFrame) -> DataFrame:
    """Group events by packet type and count them.

    Validates requirement 5.5: WHEN querying by packet type THEN the system
    SHALL support filtering and grouping events by the packet field.

    Args:
        df: DataFrame containing checkpoint events

    Returns:
        DataFrame with packet types and their counts, sorted by packet
    """
    return df.group_by("packet").agg(pl.len().alias("count")).sort("packet")


def filter_by_date_range(
    df: DataFrame,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    date_field: str = "visit_date",
) -> DataFrame:
    """Filter events by date range on visit_date or timestamp field.

    Validates requirement 5.6: WHEN querying by date range THEN the system
    SHALL support filtering events where visit_date or timestamp falls
    within specified bounds.

    Args:
        df: DataFrame containing checkpoint events
        start_date: Start date in YYYY-MM-DD format (inclusive), None for no lower bound
        end_date: End date in YYYY-MM-DD format (inclusive), None for no upper bound
        date_field: Field to filter on ("visit_date" or "timestamp")

    Returns:
        DataFrame containing events within the specified date range
    """
    filtered_df = df

    if date_field == "visit_date":
        if start_date is not None:
            filtered_df = filtered_df.filter(pl.col("visit_date") >= start_date)
        if end_date is not None:
            filtered_df = filtered_df.filter(pl.col("visit_date") <= end_date)
    elif date_field == "timestamp":
        if start_date is not None:
            # Convert string date to datetime for timestamp comparison
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            filtered_df = filtered_df.filter(pl.col("timestamp") >= start_datetime)
        if end_date is not None:
            # Convert string date to datetime for timestamp comparison (end of day)
            end_datetime = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            filtered_df = filtered_df.filter(pl.col("timestamp") <= end_datetime)
    else:
        raise ValueError(
            f"Invalid date_field: {date_field}. Must be 'visit_date' or 'timestamp'"
        )

    return filtered_df


def filter_by_timestamp_range(
    df: DataFrame,
    start_timestamp: Optional[datetime] = None,
    end_timestamp: Optional[datetime] = None,
) -> DataFrame:
    """Filter events by timestamp range.

    Validates requirement 5.6: WHEN querying by date range THEN the system
    SHALL support filtering events where visit_date or timestamp falls
    within specified bounds.

    Args:
        df: DataFrame containing checkpoint events
        start_timestamp: Start timestamp (inclusive), None for no lower bound
        end_timestamp: End timestamp (inclusive), None for no upper bound

    Returns:
        DataFrame containing events within the specified timestamp range
    """
    filtered_df = df

    if start_timestamp is not None:
        filtered_df = filtered_df.filter(pl.col("timestamp") >= start_timestamp)
    if end_timestamp is not None:
        filtered_df = filtered_df.filter(pl.col("timestamp") <= end_timestamp)

    return filtered_df


def calculate_submission_timing_metrics(df: DataFrame) -> DataFrame:
    """Calculate time differences between visit_date and submit event
    timestamps.

    Validates requirement 5.3: WHEN calculating submission timing metrics THEN
    the system SHALL support computing time differences between visit_date and
    submit event timestamps.

    Args:
        df: DataFrame containing checkpoint events

    Returns:
        DataFrame with submit events and additional columns:
        - days_from_visit_to_submit: Number of days between visit_date and timestamp
    """
    submit_events = df.filter(pl.col("action") == "submit")

    # Convert visit_date string to date for calculation
    return submit_events.with_columns(
        [
            (pl.col("timestamp").dt.date() - pl.col("visit_date").str.to_date())
            .dt.total_days()
            .alias("days_from_visit_to_submit")
        ]
    )


def calculate_qc_timing_metrics(df: DataFrame) -> DataFrame:
    """Calculate time differences between visit_date and pass-qc event
    timestamps.

    Validates requirement 5.4: WHEN calculating QC timing metrics THEN the
    system SHALL support computing time differences between visit_date and
    pass-qc event timestamps.

    Args:
        df: DataFrame containing checkpoint events

    Returns:
        DataFrame with pass-qc events and additional columns:
        - days_from_visit_to_qc: Number of days between visit_date and timestamp
    """
    qc_events = df.filter(pl.col("action") == "pass-qc")

    # Convert visit_date string to date for calculation
    return qc_events.with_columns(
        [
            (pl.col("timestamp").dt.date() - pl.col("visit_date").str.to_date())
            .dt.total_days()
            .alias("days_from_visit_to_qc")
        ]
    )


def group_and_count_by_multiple_fields(
    df: DataFrame, group_fields: List[str]
) -> DataFrame:
    """Group events by multiple fields and count them.

    Validates requirement 5.7: WHEN counting visit volumes THEN the system
    SHALL support grouping and counting events by module, packet, and action type.

    Args:
        df: DataFrame containing checkpoint events
        group_fields: List of field names to group by
                     (e.g., ["module", "packet", "action"])

    Returns:
        DataFrame with grouped fields and their counts, sorted by group fields
    """
    return df.group_by(group_fields).agg(pl.len().alias("count")).sort(group_fields)


def get_packet_types_list(df: DataFrame) -> List[str]:
    """Get list of unique packet types in the dataset.

    Args:
        df: DataFrame containing checkpoint events

    Returns:
        Sorted list of unique packet types (excluding null values)
    """
    return sorted([p for p in df["packet"].unique().to_list() if p is not None])
