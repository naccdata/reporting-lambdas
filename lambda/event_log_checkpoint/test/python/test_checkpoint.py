"""Unit tests for Checkpoint class.

This module contains unit tests for the Checkpoint class, testing
checkpoint creation, event merging, timestamp handling, and utility
methods.
"""

from datetime import datetime, timezone

from checkpoint_lambda.checkpoint import Checkpoint
from checkpoint_lambda.models import VisitEvent
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.strategies import composite


class TestCheckpoint:
    """Unit tests for Checkpoint class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create sample VisitEvent objects for testing
        self.sample_events = [
            VisitEvent(
                action="submit",
                study="adrc",
                pipeline_adcid=123,
                project_label="test_project",
                center_label="test_center",
                gear_name="test_gear",
                ptid="ABC123",
                visit_date="2024-01-15",
                visit_number="01",
                datatype="form",
                module="UDS",
                packet="I",
                timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            ),
            VisitEvent(
                action="pass-qc",
                study="adrc",
                pipeline_adcid=123,
                project_label="test_project",
                center_label="test_center",
                gear_name="test_gear",
                ptid="ABC123",
                visit_date="2024-01-15",
                visit_number="01",
                datatype="form",
                module="UDS",
                packet="I",
                timestamp=datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
            ),
            VisitEvent(
                action="submit",
                study="adrc",
                pipeline_adcid=456,
                project_label="test_project",
                center_label="test_center",
                gear_name="test_gear",
                ptid="XYZ789",
                visit_date="2024-01-16",
                visit_number="02",
                datatype="dicom",
                timestamp=datetime(2024, 1, 16, 9, 0, 0, tzinfo=timezone.utc),
            ),
        ]

    def test_from_events_creates_checkpoint_with_events(self):
        """Test from_events class method creates checkpoint with provided
        events."""
        checkpoint = Checkpoint.from_events(self.sample_events)

        assert not checkpoint.is_empty()
        assert checkpoint.get_event_count() == 3

        # Verify events are stored correctly
        df = checkpoint.dataframe
        assert len(df) == 3
        assert df["action"].to_list() == ["submit", "pass-qc", "submit"]
        assert df["ptid"].to_list() == ["ABC123", "ABC123", "XYZ789"]

    def test_from_events_with_empty_list_creates_empty_checkpoint(self):
        """Test from_events with empty list creates empty checkpoint."""
        checkpoint = Checkpoint.from_events([])

        assert checkpoint.is_empty()
        assert checkpoint.get_event_count() == 0

    def test_empty_class_method_creates_empty_checkpoint(self):
        """Test empty class method creates empty checkpoint."""
        checkpoint = Checkpoint.empty()

        assert checkpoint.is_empty()
        assert checkpoint.get_event_count() == 0
        assert checkpoint.get_last_processed_timestamp() is None

    def test_get_last_processed_timestamp_with_events(self):
        """Test get_last_processed_timestamp returns latest timestamp."""
        checkpoint = Checkpoint.from_events(self.sample_events)

        last_timestamp = checkpoint.get_last_processed_timestamp()

        # Should return the latest timestamp (2024-01-16 09:00:00)
        expected_timestamp = datetime(2024, 1, 16, 9, 0, 0, tzinfo=timezone.utc)
        assert last_timestamp == expected_timestamp

    def test_get_last_processed_timestamp_with_empty_checkpoint(self):
        """Test get_last_processed_timestamp returns None for empty
        checkpoint."""
        checkpoint = Checkpoint.empty()

        last_timestamp = checkpoint.get_last_processed_timestamp()

        assert last_timestamp is None

    def test_get_last_processed_timestamp_with_single_event(self):
        """Test get_last_processed_timestamp with single event."""
        single_event = [self.sample_events[0]]
        checkpoint = Checkpoint.from_events(single_event)

        last_timestamp = checkpoint.get_last_processed_timestamp()

        expected_timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        assert last_timestamp == expected_timestamp

    def test_add_events_to_empty_checkpoint(self):
        """Test add_events method with empty checkpoint."""
        empty_checkpoint = Checkpoint.empty()
        new_events = self.sample_events[:2]  # First two events

        updated_checkpoint = empty_checkpoint.add_events(new_events)

        # Original checkpoint should remain unchanged
        assert empty_checkpoint.is_empty()
        assert empty_checkpoint.get_event_count() == 0

        # New checkpoint should contain the events
        assert not updated_checkpoint.is_empty()
        assert updated_checkpoint.get_event_count() == 2

        # Verify events are sorted by timestamp
        df = updated_checkpoint.dataframe
        timestamps = df["timestamp"].to_list()
        assert timestamps == sorted(timestamps)

    def test_add_events_to_existing_checkpoint(self):
        """Test add_events method merging with existing checkpoint."""
        # Create checkpoint with first event
        existing_checkpoint = Checkpoint.from_events([self.sample_events[0]])

        # Add remaining events
        new_events = self.sample_events[1:]

        updated_checkpoint = existing_checkpoint.add_events(new_events)

        # Original checkpoint should remain unchanged
        assert existing_checkpoint.get_event_count() == 1

        # Updated checkpoint should contain all events
        assert updated_checkpoint.get_event_count() == 3

        # Verify events are sorted by timestamp
        df = updated_checkpoint.dataframe
        timestamps = df["timestamp"].to_list()
        assert timestamps == sorted(timestamps)

        # Verify all events are present
        ptids = df["ptid"].to_list()
        assert "ABC123" in ptids
        assert "XYZ789" in ptids

    def test_add_events_with_empty_list(self):
        """Test add_events with empty list returns copy of current
        checkpoint."""
        checkpoint = Checkpoint.from_events(self.sample_events)
        original_count = checkpoint.get_event_count()

        updated_checkpoint = checkpoint.add_events([])

        # Should return a copy with same data
        assert updated_checkpoint.get_event_count() == original_count
        assert checkpoint.get_event_count() == original_count

        # Should be different objects
        assert updated_checkpoint is not checkpoint

    def test_add_events_preserves_event_evolution(self):
        """Test add_events preserves multiple events for same visit (event
        evolution)."""
        # Create events for same visit with different timestamps
        visit_events = [
            VisitEvent(
                action="submit",
                study="adrc",
                pipeline_adcid=123,
                project_label="test_project",
                center_label="test_center",
                gear_name="test_gear",
                ptid="ABC123",
                visit_date="2024-01-15",
                visit_number="01",
                datatype="form",
                module="UDS",
                packet="I",
                timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            ),
            VisitEvent(
                action="submit",
                study="adrc",
                pipeline_adcid=123,
                project_label="test_project",
                center_label="test_center",
                gear_name="test_gear",
                ptid="ABC123",
                visit_date="2024-01-15",
                visit_number="01",
                datatype="form",
                module="UDS",
                packet="I",
                timestamp=datetime(
                    2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
                ),  # Later timestamp
            ),
        ]

        checkpoint = Checkpoint.from_events(visit_events)

        # Both events should be preserved
        assert checkpoint.get_event_count() == 2

        # Events should be sorted by timestamp
        df = checkpoint.dataframe
        timestamps = df["timestamp"].to_list()
        assert timestamps[0] < timestamps[1]

    def test_add_events_maintains_timestamp_ordering(self):
        """Test add_events maintains timestamp ordering after merge."""
        # Create checkpoint with later event (with all fields to avoid schema issues)
        later_event = VisitEvent(
            action="submit",
            study="adrc",
            pipeline_adcid=789,
            project_label="test_project",
            center_label="test_center",
            gear_name="test_gear",
            ptid="DEF456",
            visit_date="2024-01-20",
            visit_number="03",  # Add visit_number to match schema
            datatype="form",  # Use form datatype to allow module
            module="UDS",  # Add module to match schema
            packet="F",  # Add packet to match schema
            timestamp=datetime(2024, 1, 20, 15, 0, 0, tzinfo=timezone.utc),
        )
        checkpoint = Checkpoint.from_events([later_event])

        # Add earlier events
        earlier_events = self.sample_events

        updated_checkpoint = checkpoint.add_events(earlier_events)

        # Verify all events are present and sorted
        df = updated_checkpoint.dataframe
        timestamps = df["timestamp"].to_list()
        assert len(timestamps) == 4
        assert timestamps == sorted(timestamps)

        # Verify the earliest and latest timestamps
        assert timestamps[0] == datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        assert timestamps[-1] == datetime(2024, 1, 20, 15, 0, 0, tzinfo=timezone.utc)

    def test_get_event_count_with_various_sizes(self):
        """Test get_event_count with various checkpoint sizes."""
        # Empty checkpoint
        empty_checkpoint = Checkpoint.empty()
        assert empty_checkpoint.get_event_count() == 0

        # Single event
        single_checkpoint = Checkpoint.from_events([self.sample_events[0]])
        assert single_checkpoint.get_event_count() == 1

        # Multiple events
        multi_checkpoint = Checkpoint.from_events(self.sample_events)
        assert multi_checkpoint.get_event_count() == 3

    def test_is_empty_with_various_states(self):
        """Test is_empty method with various checkpoint states."""
        # Empty checkpoint
        empty_checkpoint = Checkpoint.empty()
        assert empty_checkpoint.is_empty() is True

        # Checkpoint with events
        non_empty_checkpoint = Checkpoint.from_events(self.sample_events)
        assert non_empty_checkpoint.is_empty() is False

        # Checkpoint created from empty list
        empty_list_checkpoint = Checkpoint.from_events([])
        assert empty_list_checkpoint.is_empty() is True

    def test_dataframe_property_returns_polars_dataframe(self):
        """Test dataframe property returns underlying Polars DataFrame."""
        checkpoint = Checkpoint.from_events(self.sample_events)

        df = checkpoint.dataframe

        # Should be a Polars DataFrame
        import polars as pl

        assert isinstance(df, pl.DataFrame)

        # Should contain the expected columns
        expected_columns = [
            "action",
            "study",
            "pipeline_adcid",
            "project_label",
            "center_label",
            "gear_name",
            "ptid",
            "visit_date",
            "visit_number",
            "datatype",
            "module",
            "packet",
            "timestamp",
        ]
        assert list(df.columns) == expected_columns

        # Should contain the expected number of rows
        assert len(df) == 3

    def test_dataframe_property_with_empty_checkpoint(self):
        """Test dataframe property with empty checkpoint."""
        empty_checkpoint = Checkpoint.empty()

        df = empty_checkpoint.dataframe

        # Should be a Polars DataFrame with correct schema but no rows
        import polars as pl

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0

        # Should have the expected columns even when empty
        expected_columns = [
            "action",
            "study",
            "pipeline_adcid",
            "project_label",
            "center_label",
            "gear_name",
            "ptid",
            "visit_date",
            "visit_number",
            "datatype",
            "module",
            "packet",
            "timestamp",
        ]
        assert list(df.columns) == expected_columns

    def test_checkpoint_immutability(self):
        """Test that checkpoint operations don't modify original checkpoint."""
        original_checkpoint = Checkpoint.from_events(self.sample_events)
        original_count = original_checkpoint.get_event_count()

        # Adding events should not modify original
        new_event = VisitEvent(
            action="delete",
            study="adrc",
            pipeline_adcid=999,
            project_label="test_project",
            center_label="test_center",
            gear_name="test_gear",
            ptid="TEST999",
            visit_date="2024-01-25",
            visit_number="04",  # Add visit_number to match schema
            datatype="form",  # Use form datatype to allow module
            module="MDS",  # Add module to match schema
            packet="M",  # Add packet to match schema
            timestamp=datetime(2024, 1, 25, 12, 0, 0, tzinfo=timezone.utc),
        )

        updated_checkpoint = original_checkpoint.add_events([new_event])

        # Original should be unchanged
        assert original_checkpoint.get_event_count() == original_count
        assert updated_checkpoint.get_event_count() == original_count + 1

    def test_checkpoint_with_null_optional_fields(self):
        """Test checkpoint handles events with null optional fields
        correctly."""
        event_with_nulls = VisitEvent(
            action="submit",
            study="adrc",
            pipeline_adcid=123,
            project_label="test_project",
            center_label="test_center",
            gear_name="test_gear",
            ptid="NULL123",
            visit_date="2024-01-15",
            visit_number=None,  # Null optional field
            datatype="dicom",
            module=None,  # Null optional field
            packet=None,  # Null optional field
            timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )

        checkpoint = Checkpoint.from_events([event_with_nulls])

        assert not checkpoint.is_empty()
        assert checkpoint.get_event_count() == 1

        # Verify null values are preserved in DataFrame
        df = checkpoint.dataframe
        row = df.row(0, named=True)
        assert row["visit_number"] is None
        assert row["module"] is None
        assert row["packet"] is None


@composite
def valid_visit_event_for_checkpoint(draw):
    """Generate valid VisitEvent data for checkpoint property testing."""
    datatype = draw(
        st.sampled_from(
            [
                "apoe",
                "biomarker",
                "dicom",
                "enrollment",
                "form",
                "genetic-availability",
                "gwas",
                "imputation",
                "scan-analysis",
            ]
        )
    )

    # Generate base data
    data = {
        "action": draw(st.sampled_from(["submit", "delete", "not-pass-qc", "pass-qc"])),
        "study": draw(
            st.text(
                min_size=1,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            )
        ),
        "pipeline_adcid": draw(st.integers(min_value=1, max_value=9999)),
        "project_label": draw(
            st.text(
                min_size=1,
                max_size=50,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc")),
            )
        ),
        "center_label": draw(
            st.text(
                min_size=1,
                max_size=50,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc")),
            )
        ),
        "gear_name": draw(
            st.text(
                min_size=1,
                max_size=50,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc")),
            )
        ),
        "ptid": draw(
            st.text(
                min_size=1,
                max_size=10,
                alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=",
            )
        ),
        "visit_date": draw(
            st.dates(
                min_value=datetime(2020, 1, 1).date(),
                max_value=datetime(2030, 12, 31).date(),
            )
        ).strftime("%Y-%m-%d"),
        "visit_number": draw(
            st.one_of(
                st.none(),
                st.text(
                    min_size=1,
                    max_size=10,
                    alphabet=st.characters(whitelist_categories=("Nd", "Lu", "Ll")),
                ),
            )
        ),
        "datatype": datatype,
        "packet": draw(
            st.one_of(
                st.none(),
                st.text(
                    min_size=1,
                    max_size=10,
                    alphabet=st.characters(whitelist_categories=("Lu", "Ll")),
                ),
            )
        ),
        "timestamp": draw(
            st.datetimes(
                min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31)
            )
        ).replace(tzinfo=timezone.utc),
    }

    # Handle module field based on datatype
    if datatype == "form":
        data["module"] = draw(st.sampled_from(["UDS", "FTLD", "LBD", "MDS"]))
    else:
        data["module"] = None

    return VisitEvent(**data)


class TestCheckpointPropertyBased:
    """Property-based tests for Checkpoint class."""

    @given(
        st.lists(valid_visit_event_for_checkpoint(), min_size=0, max_size=10),
        st.lists(valid_visit_event_for_checkpoint(), min_size=0, max_size=10),
    )
    def test_property_incremental_checkpoint_correctness(
        self, previous_events, new_events
    ):
        """Property 0: Incremental checkpoint correctness.

        For any previous checkpoint and set of new events, the merged checkpoint
        should contain all events from the previous checkpoint plus all new events,
        with no duplicates removed and no data loss.

        Feature: event-log-scraper, Property 0: Incremental checkpoint correctness
        Validates: Requirements 4.1, 7.1
        """
        # Create previous checkpoint from previous events
        previous_checkpoint = Checkpoint.from_events(previous_events)

        # Get initial counts
        previous_count = previous_checkpoint.get_event_count()
        new_count = len(new_events)

        # Add new events to create merged checkpoint
        merged_checkpoint = previous_checkpoint.add_events(new_events)

        # Verify correctness properties

        # 1. Total count should be sum of previous + new events
        assert merged_checkpoint.get_event_count() == previous_count + new_count

        # 2. Original checkpoint should remain unchanged (immutability)
        assert previous_checkpoint.get_event_count() == previous_count

        # 3. All previous events should be present in merged checkpoint
        if previous_count > 0:
            previous_df = previous_checkpoint.dataframe
            merged_df = merged_checkpoint.dataframe

            # Check that all previous events are in the merged checkpoint
            # We'll verify by checking that for each previous event,
            # there's a matching event in merged
            for i in range(previous_count):
                prev_row = previous_df.row(i, named=True)
                # Find matching row in merged checkpoint
                matching_rows = merged_df.filter(
                    (merged_df["ptid"] == prev_row["ptid"])
                    & (merged_df["visit_date"] == prev_row["visit_date"])
                    & (merged_df["timestamp"] == prev_row["timestamp"])
                    & (merged_df["action"] == prev_row["action"])
                )
                assert len(matching_rows) >= 1, (
                    f"Previous event not found in merged checkpoint: {prev_row}"
                )

        # 4. All new events should be present in merged checkpoint
        if new_count > 0:
            merged_df = merged_checkpoint.dataframe

            for new_event in new_events:
                # Find matching row in merged checkpoint
                matching_rows = merged_df.filter(
                    (merged_df["ptid"] == new_event.ptid)
                    & (merged_df["visit_date"] == new_event.visit_date)
                    & (merged_df["timestamp"] == new_event.timestamp)
                    & (merged_df["action"] == new_event.action)
                )
                assert len(matching_rows) >= 1, (
                    f"New event not found in merged checkpoint: {new_event}"
                )

        # 5. Events should be sorted by timestamp
        if merged_checkpoint.get_event_count() > 1:
            merged_df = merged_checkpoint.dataframe
            timestamps = merged_df["timestamp"].to_list()
            # Check that timestamps are in non-decreasing order
            # (allowing for equal timestamps)
            for i in range(len(timestamps) - 1):
                assert timestamps[i] <= timestamps[i + 1], (
                    "Events not sorted by timestamp: "
                    f"{timestamps[i]} > {timestamps[i + 1]}"
                )

        # 6. No data loss - verify all fields are preserved
        if merged_checkpoint.get_event_count() > 0:
            merged_df = merged_checkpoint.dataframe

            # Verify schema is preserved
            expected_columns = [
                "action",
                "study",
                "pipeline_adcid",
                "project_label",
                "center_label",
                "gear_name",
                "ptid",
                "visit_date",
                "visit_number",
                "datatype",
                "module",
                "packet",
                "timestamp",
            ]
            assert list(merged_df.columns) == expected_columns

            # Verify no null corruption in required fields
            for row_idx in range(len(merged_df)):
                row = merged_df.row(row_idx, named=True)
                assert row["action"] is not None
                assert row["study"] is not None
                assert row["pipeline_adcid"] is not None
                assert row["project_label"] is not None
                assert row["center_label"] is not None
                assert row["gear_name"] is not None
                assert row["ptid"] is not None
                assert row["visit_date"] is not None
                assert row["datatype"] is not None
                assert row["timestamp"] is not None
                # Optional fields (visit_number, module, packet) can be None
