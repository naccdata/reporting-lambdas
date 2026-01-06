"""Checkpoint class for managing event data collections.

This module provides the Checkpoint class that encapsulates checkpoint
data and provides operations for working with event collections.
"""

from datetime import datetime
from typing import List, Optional

from polars import DataFrame, Datetime, Int32, Utf8, col, concat

from checkpoint_lambda.models import VisitEvent


def create_checkpoint_dataframe() -> DataFrame:
    """Create an empty dataframe for Checkpoint data."""
    return DataFrame(
        schema={
            "action": Utf8,
            "study": Utf8,
            "pipeline_adcid": Int32,
            "project_label": Utf8,
            "center_label": Utf8,
            "gear_name": Utf8,
            "ptid": Utf8,
            "visit_date": Utf8,
            "visit_number": Utf8,
            "datatype": Utf8,
            "module": Utf8,
            "packet": Utf8,
            "timestamp": Datetime("us", time_zone="UTC"),
        }
    )


def events_to_dataframe(events: List[VisitEvent]) -> DataFrame:
    """Convert a list of VisitEvent objects to a DataFrame.

    Args:
        events: List of validated VisitEvent objects

    Returns:
        DataFrame containing the event data
    """
    if not events:
        return create_checkpoint_dataframe()

    # Convert VisitEvent objects to DataFrame using model_dump()
    data = [event.model_dump() for event in events]
    return DataFrame(data)


class Checkpoint:
    """Encapsulates checkpoint data and provides operations for working with
    event collections."""

    def __init__(self, events_df: Optional[DataFrame] = None):
        """Initialize checkpoint with event data.

        Args:
            events_df: DataFrame containing event data, None for empty checkpoint
        """

        self._events_df = (
            create_checkpoint_dataframe() if events_df is None else events_df
        )

    @classmethod
    def from_events(cls, events: List[VisitEvent]) -> "Checkpoint":
        """Create checkpoint from list of VisitEvent objects.

        Args:
            events: List of validated events

        Returns:
            Checkpoint instance with events converted to DataFrame
        """
        df = events_to_dataframe(events)
        return cls(df)

    @classmethod
    def empty(cls) -> "Checkpoint":
        """Create an empty checkpoint.

        Returns:
            Empty checkpoint instance
        """
        return cls()

    def get_last_processed_timestamp(self) -> Optional[datetime]:
        """Get the latest timestamp from checkpoint events.

        Returns:
            Latest timestamp, or None if checkpoint is empty
        """
        if self.is_empty():
            return None

        # Get maximum timestamp, handling nulls
        max_timestamp = self._events_df.select(col("timestamp").max()).item()
        return max_timestamp

    def add_events(self, new_events: List[VisitEvent]) -> "Checkpoint":
        """Create new checkpoint with additional events merged in.

        This method handles the merging logic internally:
        - Converts new events to DataFrame
        - Merges with existing events
        - Sorts by timestamp
        - Returns new Checkpoint instance

        Args:
            new_events: List of new validated events to add

        Returns:
            New checkpoint instance with merged events, sorted by timestamp
        """
        if not new_events:
            # No new events, return copy of current checkpoint
            return Checkpoint(self._events_df.clone())

        # Convert new events to DataFrame
        new_events_df = events_to_dataframe(new_events)

        # Merge with existing events
        merged_df = (
            new_events_df
            if self.is_empty()
            else concat([self._events_df, new_events_df])
        )

        # Sort by timestamp
        merged_df = merged_df.sort("timestamp")

        return Checkpoint(merged_df)

    def get_event_count(self) -> int:
        """Get total number of events in checkpoint.

        Returns:
            Number of events
        """
        return len(self._events_df)

    def is_empty(self) -> bool:
        """Check if checkpoint contains any events.

        Returns:
            True if checkpoint is empty
        """
        return len(self._events_df) == 0

    @property
    def dataframe(self) -> DataFrame:
        """Get underlying DataFrame for operations that absolutely need direct
        access.

        Note: This should be used sparingly. Prefer adding methods to Checkpoint
        for common operations rather than exposing the implementation.

        Returns:
            Polars DataFrame containing event data
        """
        return self._events_df
