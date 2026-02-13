"""Event grouping functionality for checkpoint processing.

This module provides the EventGrouper class that groups events by study
and datatype combinations for independent checkpoint management.
"""

from typing import Dict, List, Tuple

from checkpoint_lambda.models import VisitEvent

# Type alias for study-datatype grouping key
StudyDatatypeKey = Tuple[str, str]  # (study, datatype)


class EventGrouper:
    """Groups events by study and datatype combinations."""

    @staticmethod
    def group_by_study_datatype(
        events: List[VisitEvent],
    ) -> Dict[StudyDatatypeKey, List[VisitEvent]]:
        """Group events by study and datatype.

        Args:
            events: List of events to group

        Returns:
            Dictionary mapping (study, datatype) to list of events
            Example: {
                ("adrc", "form"): [event1, event2, ...],
                ("adrc", "dicom"): [event3, event4, ...],
                ("dvcid", "form"): [event5, ...]
            }
        """
        grouped: Dict[StudyDatatypeKey, List[VisitEvent]] = {}

        for event in events:
            key = (event.study, event.datatype)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(event)

        return grouped
