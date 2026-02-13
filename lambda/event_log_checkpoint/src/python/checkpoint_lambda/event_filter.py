"""Event filtering module for checkpoint processing.

This module provides filtering functionality to exclude sandbox project
events from checkpoint processing. Sandbox projects are identified by
project labels matching the pattern "sandbox-*".
"""

from typing import List, Tuple

from checkpoint_lambda.models import VisitEvent


class EventFilter:
    """Filters events based on project label patterns."""

    @staticmethod
    def is_sandbox_project(project_label: str) -> bool:
        """Check if project label matches sandbox pattern.

        Args:
            project_label: Project label from event

        Returns:
            True if project label starts with "sandbox-"
        """
        return project_label.startswith("sandbox-")

    @staticmethod
    def filter_sandbox_events(
        events: List[VisitEvent],
    ) -> Tuple[List[VisitEvent], int]:
        """Filter out sandbox project events.

        Args:
            events: List of events to filter

        Returns:
            Tuple of (filtered_events, filtered_count)
            - filtered_events: Events not matching sandbox pattern
            - filtered_count: Number of events filtered out
        """
        filtered_events = [
            event
            for event in events
            if not EventFilter.is_sandbox_project(event.project_label)
        ]
        filtered_count = len(events) - len(filtered_events)
        return filtered_events, filtered_count
