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

    @given(
        st.lists(
            st.tuples(
                # Base visit info (ptid, visit_date, visit_number)
                st.text(
                    min_size=1,
                    max_size=10,
                    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
                ),
                st.dates(
                    min_value=datetime(2020, 1, 1).date(),
                    max_value=datetime(2030, 12, 31).date(),
                ).map(lambda d: d.strftime("%Y-%m-%d")),
                st.one_of(
                    st.none(),
                    st.text(
                        min_size=1,
                        max_size=5,
                        alphabet=st.characters(whitelist_categories=["Nd"]),
                    ),
                ),
                # Number of evolving events for this visit (1-5)
                st.integers(min_value=1, max_value=5),
            ),
            min_size=1,
            max_size=3,
        ).map(
            # Ensure unique visits by deduplicating on (ptid, visit_date, visit_number)
            lambda visits: list(
                {
                    (ptid, visit_date, visit_number): (
                        ptid,
                        visit_date,
                        visit_number,
                        num_events,
                    )
                    for ptid, visit_date, visit_number, num_events in visits
                }.values()
            )
        )
    )
    def test_property_event_evolution_preservation(self, visit_specs):  # noqa: C901
        """Property 15: Event evolution preservation.

        For any collection of events including multiple events for the same visit
        with different levels of data completeness, all events should be included
        in the checkpoint file with their respective timestamps preserved,
        allowing analysis of data evolution over time.

        Feature: event-log-scraper, Property 15: Event evolution preservation
        Validates: Requirements 7.1, 7.3, 7.4
        """
        all_events = []
        expected_event_count = 0

        # Generate evolving events for each visit
        for ptid, visit_date, visit_number, num_events in visit_specs:
            expected_event_count += num_events

            # Create base timestamp for this visit
            base_timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

            # Generate evolving events for this visit
            for i in range(num_events):
                # Each event has a slightly later timestamp
                event_timestamp = base_timestamp.replace(
                    minute=base_timestamp.minute + (i * 10)
                )

                # Create events with increasing completeness
                # Early events may have None for optional fields
                # Later events have more complete data
                if i == 0:
                    # First event - minimal data
                    module = None
                    packet = None
                    datatype = "dicom"  # Non-form datatype so module must be None
                elif i == 1:
                    # Second event - some data filled in
                    module = None
                    packet = "I" if i % 2 == 0 else "F"
                    datatype = "dicom"
                else:
                    # Later events - more complete data
                    module = "UDS" if i % 2 == 0 else "MDS"
                    packet = "I" if i % 2 == 0 else "F"
                    datatype = "form"  # Form datatype allows module

                # Sometimes create identical events (same content, different timestamp)
                # to test requirement 7.3
                action = "submit" if i < 2 else ("pass-qc" if i % 2 == 0 else "submit")

                event = VisitEvent(
                    action=action,
                    study="adrc",
                    pipeline_adcid=123 + i,  # Vary slightly to show evolution
                    project_label="test_project",
                    center_label="test_center",
                    gear_name="test_gear",
                    ptid=ptid,
                    visit_date=visit_date,
                    visit_number=visit_number,
                    datatype=datatype,
                    module=module,
                    packet=packet,
                    timestamp=event_timestamp,
                )
                all_events.append(event)

        # Create checkpoint with all evolving events
        checkpoint = Checkpoint.from_events(all_events)

        # Verify Property 15: Event evolution preservation

        # 1. All events should be preserved (Requirements 7.1, 7.3, 7.4)
        assert checkpoint.get_event_count() == expected_event_count, (
            f"Expected {expected_event_count} events, "
            f"got {checkpoint.get_event_count()}"
        )

        # 2. All events should be present with their timestamps preserved
        df = checkpoint.dataframe
        assert len(df) == expected_event_count

        # 3. Verify that multiple events for same visit are all preserved (Req 7.1)
        for ptid, visit_date, visit_number, num_events in visit_specs:
            # Find all events for this visit (including visit_number in filter)
            if visit_number is None:
                visit_events = df.filter(
                    (df["ptid"] == ptid)
                    & (df["visit_date"] == visit_date)
                    & (df["visit_number"].is_null())
                )
            else:
                visit_events = df.filter(
                    (df["ptid"] == ptid)
                    & (df["visit_date"] == visit_date)
                    & (df["visit_number"] == visit_number)
                )

            # Should have all events for this visit
            assert len(visit_events) == num_events, (
                f"Expected {num_events} events for visit "
                f"{ptid}/{visit_date}/{visit_number}, got {len(visit_events)}"
            )

            # 4. Verify timestamps are preserved and allow tracking evolution (Req 7.4)
            if num_events > 1:
                timestamps = visit_events["timestamp"].to_list()
                # Should be sorted (checkpoint sorts by timestamp)
                assert timestamps == sorted(timestamps), (
                    f"Timestamps not sorted for visit "
                    f"{ptid}/{visit_date}/{visit_number}: {timestamps}"
                )

                # 5. Verify data evolution can be tracked
                # Later events should have same or more complete data
                for i in range(len(visit_events) - 1):
                    current_row = visit_events.row(i, named=True)
                    next_row = visit_events.row(i + 1, named=True)

                    # Timestamps should increase
                    assert current_row["timestamp"] <= next_row["timestamp"]

                    # Core fields should remain consistent or evolve
                    assert current_row["ptid"] == next_row["ptid"]
                    assert current_row["visit_date"] == next_row["visit_date"]

        # 6. Verify identical events are preserved (Req 7.3)
        # Check if there are any events with same ptid, visit_date,
        # action but different timestamps
        for ptid, visit_date, visit_number, num_events in visit_specs:
            if visit_number is None:
                visit_events = df.filter(
                    (df["ptid"] == ptid)
                    & (df["visit_date"] == visit_date)
                    & (df["visit_number"].is_null())
                )
            else:
                visit_events = df.filter(
                    (df["ptid"] == ptid)
                    & (df["visit_date"] == visit_date)
                    & (df["visit_number"] == visit_number)
                )

            if num_events >= 2:
                # Check for events with same action but different timestamps
                actions = visit_events["action"].to_list()
                timestamps = visit_events["timestamp"].to_list()

                # If we have duplicate actions, they should have different timestamps
                # (this tests that identical content events are preserved with
                # timestamps)
                action_timestamp_pairs = list(zip(actions, timestamps, strict=False))
                unique_pairs = set(action_timestamp_pairs)

                # All pairs should be unique
                # (same action can appear with different timestamps)
                assert len(action_timestamp_pairs) == len(unique_pairs) or len(
                    set(actions)
                ) < len(actions), (
                    "Identical events should be preserved with different timestamps"
                )

        # 7. Verify schema preservation during evolution
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

        # 8. Verify that analysis of data evolution is supported
        # Test that we can identify the most recent event per visit
        for ptid, visit_date, visit_number, num_events in visit_specs:
            if num_events > 1:
                # Get most recent event for this visit
                if visit_number is None:
                    visit_events = df.filter(
                        (df["ptid"] == ptid)
                        & (df["visit_date"] == visit_date)
                        & (df["visit_number"].is_null())
                    ).sort("timestamp", descending=True)
                else:
                    visit_events = df.filter(
                        (df["ptid"] == ptid)
                        & (df["visit_date"] == visit_date)
                        & (df["visit_number"] == visit_number)
                    ).sort("timestamp", descending=True)

                most_recent = visit_events.row(0, named=True)

                # Should be able to identify this as the most complete/recent
                assert most_recent["timestamp"] is not None
                assert most_recent["ptid"] == ptid
                assert most_recent["visit_date"] == visit_date

                # Most recent event should have timestamp >= all others for this visit
                all_visit_timestamps = visit_events["timestamp"].to_list()
                assert most_recent["timestamp"] == max(all_visit_timestamps)

    @given(st.lists(valid_visit_event_for_checkpoint(), min_size=1, max_size=20))
    def test_property_timestamp_ordering(self, events):  # noqa: C901
        """Property 16: Timestamp ordering.

        For any collection of events, the checkpoint file should preserve or support
        ordering by timestamp to enable identification of the most recent event
        per visit.

        Feature: event-log-scraper, Property 16: Timestamp ordering
        Validates: Requirements 7.2, 7.4
        """
        # Create checkpoint from events
        checkpoint = Checkpoint.from_events(events)

        if checkpoint.is_empty():
            return  # Nothing to test with empty checkpoint

        df = checkpoint.dataframe

        # Property 1: Events should be ordered by timestamp (Requirement 7.2)
        timestamps = df["timestamp"].to_list()

        # Verify timestamps are in non-decreasing order
        for i in range(len(timestamps) - 1):
            assert timestamps[i] <= timestamps[i + 1], (
                f"Events not properly ordered by timestamp: "
                f"{timestamps[i]} > {timestamps[i + 1]} at positions {i}, {i + 1}"
            )

        # Property 2: Should support identifying most recent event per visit
        # (Req 7.2, 7.4)
        # Group events by visit (ptid, visit_date, visit_number combination)
        visit_groups = {}

        for i in range(len(df)):
            row = df.row(i, named=True)
            visit_key = (row["ptid"], row["visit_date"], row["visit_number"])

            if visit_key not in visit_groups:
                visit_groups[visit_key] = []
            visit_groups[visit_key].append(row)

        # For each visit group, verify we can identify the most recent event
        for visit_key, visit_events in visit_groups.items():
            if len(visit_events) > 1:
                # Sort by timestamp to find the most recent
                sorted_events = sorted(visit_events, key=lambda x: x["timestamp"])
                most_recent_expected = sorted_events[-1]

                # Verify that the checkpoint supports finding this most recent event
                # by filtering and sorting
                ptid, visit_date, visit_number = visit_key

                if visit_number is None:
                    filtered_events = df.filter(
                        (df["ptid"] == ptid)
                        & (df["visit_date"] == visit_date)
                        & (df["visit_number"].is_null())
                    )
                else:
                    filtered_events = df.filter(
                        (df["ptid"] == ptid)
                        & (df["visit_date"] == visit_date)
                        & (df["visit_number"] == visit_number)
                    )

                # Sort by timestamp descending to get most recent first
                sorted_filtered = filtered_events.sort("timestamp", descending=True)

                if len(sorted_filtered) > 0:
                    most_recent_actual = sorted_filtered.row(0, named=True)

                    # The most recent event should match our expectation
                    assert (
                        most_recent_actual["timestamp"]
                        == most_recent_expected["timestamp"]
                    ), (
                        f"Most recent event timestamp mismatch for visit {visit_key}: "
                        f"expected {most_recent_expected['timestamp']}, "
                        f"got {most_recent_actual['timestamp']}"
                    )

                    # Verify it's actually the latest timestamp for this visit
                    visit_timestamps = filtered_events["timestamp"].to_list()
                    max_timestamp = max(visit_timestamps)
                    assert most_recent_actual["timestamp"] == max_timestamp, (
                        "Most recent event is not actually the latest for "
                        f"visit {visit_key}"
                    )

        # Property 3: Ordering should be stable and consistent (Requirement 7.2)
        # If we create the same checkpoint multiple times, ordering should be identical
        checkpoint2 = Checkpoint.from_events(events)
        df2 = checkpoint2.dataframe

        timestamps2 = df2["timestamp"].to_list()
        assert timestamps == timestamps2, (
            "Timestamp ordering is not consistent across checkpoint creations"
        )

        # Property 4: Preserve all versions for data evolution analysis
        # (Requirement 7.4)
        # Verify that events with same visit but different timestamps are all preserved
        for visit_key, visit_events in visit_groups.items():
            if len(visit_events) > 1:
                # All events for this visit should be preserved
                ptid, visit_date, visit_number = visit_key

                if visit_number is None:
                    visit_df = df.filter(
                        (df["ptid"] == ptid)
                        & (df["visit_date"] == visit_date)
                        & (df["visit_number"].is_null())
                    )
                else:
                    visit_df = df.filter(
                        (df["ptid"] == ptid)
                        & (df["visit_date"] == visit_date)
                        & (df["visit_number"] == visit_number)
                    )

                # Should have all events for this visit
                assert len(visit_df) == len(visit_events), (
                    f"Not all events preserved for visit {visit_key}: "
                    f"expected {len(visit_events)}, got {len(visit_df)}"
                )

                # Events should be ordered by timestamp within the visit
                visit_timestamps = visit_df["timestamp"].to_list()
                sorted_visit_timestamps = sorted(visit_timestamps)
                assert visit_timestamps == sorted_visit_timestamps, (
                    f"Events for visit {visit_key} not ordered by timestamp: "
                    f"{visit_timestamps} != {sorted_visit_timestamps}"
                )

        # Property 5: Support temporal analysis across all events (Requirement 7.2)
        # Verify that global timestamp ordering enables temporal analysis
        if len(df) > 1:
            # Should be able to find earliest and latest events across all data
            earliest_timestamp = min(timestamps)
            latest_timestamp = max(timestamps)

            # Find events with these timestamps
            earliest_events = df.filter(df["timestamp"] == earliest_timestamp)
            latest_events = df.filter(df["timestamp"] == latest_timestamp)

            assert len(earliest_events) >= 1, "Could not find earliest event"
            assert len(latest_events) >= 1, "Could not find latest event"

            # Verify these are actually at the expected positions in sorted order
            assert timestamps[0] == earliest_timestamp, (
                "Earliest timestamp not at beginning of sorted list"
            )
            assert timestamps[-1] == latest_timestamp, (
                "Latest timestamp not at end of sorted list"
            )

    @given(
        st.lists(
            st.tuples(
                # Base visit info (ptid, visit_date, visit_number)
                st.text(
                    min_size=1,
                    max_size=10,
                    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
                ),
                st.dates(
                    min_value=datetime(2020, 1, 1).date(),
                    max_value=datetime(2030, 12, 31).date(),
                ).map(lambda d: d.strftime("%Y-%m-%d")),
                st.one_of(
                    st.none(),
                    st.text(
                        min_size=1,
                        max_size=5,
                        alphabet=st.characters(whitelist_categories=["Nd"]),
                    ),
                ),
                # Number of events for this visit (2-5 to ensure multiple events)
                st.integers(min_value=2, max_value=5),
            ),
            min_size=1,
            max_size=3,
        ).map(
            # Ensure unique visits by deduplicating on (ptid, visit_date, visit_number)
            lambda visits: list(
                {
                    (ptid, visit_date, visit_number): (
                        ptid,
                        visit_date,
                        visit_number,
                        num_events,
                    )
                    for ptid, visit_date, visit_number, num_events in visits
                }.values()
            )
        )
    )
    def test_property_event_completeness_analysis(self, visit_specs):  # noqa: C901
        """Property 17: Event completeness analysis.

        For any visit with multiple events, querying the checkpoint file should support
        identifying the most recent event (by timestamp) to get the most complete data
        available for that visit.

        Feature: event-log-scraper, Property 17: Event completeness analysis
        Validates: Requirements 7.5, 7.6
        """
        all_events = []

        # Generate events with increasing completeness for each visit
        for ptid, visit_date, visit_number, num_events in visit_specs:
            # Create base timestamp for this visit
            base_timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

            # Generate events with increasing data completeness over time
            for i in range(num_events):
                # Each event has a later timestamp
                # (using hours to avoid minute overflow)
                event_timestamp = base_timestamp.replace(
                    hour=base_timestamp.hour + i,
                    minute=0,  # Reset minutes to avoid overflow
                )

                # Create events with increasing completeness
                # Early events have less complete data, later events more complete
                if i == 0:
                    # First event - minimal required data only
                    module = None
                    packet = None
                    datatype = "dicom"  # Non-form datatype so module must be None
                    action = "submit"
                elif i == 1:
                    # Second event - some optional fields filled
                    module = None
                    packet = "I"
                    datatype = "dicom"
                    action = "submit"  # Same action, more complete data
                else:
                    # Later events - most complete data
                    module = "UDS" if i % 2 == 0 else "MDS"
                    packet = "I" if i % 2 == 0 else "F"
                    datatype = "form"  # Form datatype allows module
                    action = "pass-qc" if i >= 2 else "submit"

                event = VisitEvent(
                    action=action,
                    study="adrc",
                    pipeline_adcid=123,
                    project_label="test_project",
                    center_label="test_center",
                    gear_name="test_gear",
                    ptid=ptid,
                    visit_date=visit_date,
                    visit_number=visit_number,
                    datatype=datatype,
                    module=module,
                    packet=packet,
                    timestamp=event_timestamp,
                )
                all_events.append(event)

        # Create checkpoint with all events
        checkpoint = Checkpoint.from_events(all_events)
        df = checkpoint.dataframe

        # Test Property 17: Event completeness analysis

        # For each visit, verify we can identify the most recent event
        # which should have the most complete data (Requirements 7.5, 7.6)
        for ptid, visit_date, visit_number, num_events in visit_specs:
            # Query for all events for this visit
            if visit_number is None:
                visit_events = df.filter(
                    (df["ptid"] == ptid)
                    & (df["visit_date"] == visit_date)
                    & (df["visit_number"].is_null())
                )
            else:
                visit_events = df.filter(
                    (df["ptid"] == ptid)
                    & (df["visit_date"] == visit_date)
                    & (df["visit_number"] == visit_number)
                )

            # Should have all events for this visit
            assert len(visit_events) == num_events, (
                f"Expected {num_events} events for visit "
                f"{ptid}/{visit_date}/{visit_number}, got {len(visit_events)}"
            )

            # Test Requirement 7.5: Support identifying the most recent event per visit
            # Sort by timestamp descending to get most recent first
            recent_events = visit_events.sort("timestamp", descending=True)
            most_recent_event = recent_events.row(0, named=True)

            # Verify this is actually the most recent by timestamp
            all_timestamps = visit_events["timestamp"].to_list()
            max_timestamp = max(all_timestamps)
            assert most_recent_event["timestamp"] == max_timestamp, (
                f"Most recent event does not have the latest timestamp for visit "
                f"{ptid}/{visit_date}/{visit_number}"
            )

            # Test Requirement 7.6: Support tracking how event data becomes more
            # complete
            # Verify that we can analyze data evolution by comparing events over time
            if num_events > 1:
                # Sort events by timestamp ascending to see evolution
                chronological_events = visit_events.sort("timestamp", descending=False)

                # Track data completeness progression
                completeness_scores = []
                for i in range(len(chronological_events)):
                    row = chronological_events.row(i, named=True)

                    # Calculate completeness score (number of non-null optional fields)
                    score = 0
                    if row["visit_number"] is not None:
                        score += 1
                    if row["module"] is not None:
                        score += 1
                    if row["packet"] is not None:
                        score += 1

                    completeness_scores.append(score)

                # Verify that completeness generally increases or stays the same
                # over time
                # (data should not become less complete in later events)
                for i in range(len(completeness_scores) - 1):
                    current_score = completeness_scores[i]
                    next_score = completeness_scores[i + 1]

                    # Later events should have >= completeness
                    # (allowing for same completeness)
                    assert next_score >= current_score, (
                        f"Data completeness decreased over time for visit "
                        f"{ptid}/{visit_date}/{visit_number}: "
                        f"score {current_score} -> {next_score} "
                        f"at positions {i} -> {i + 1}"
                    )

                # Verify that the most recent event has the highest or equal
                # completeness
                max_completeness = max(completeness_scores)
                most_recent_completeness = completeness_scores[-1]
                assert most_recent_completeness == max_completeness, (
                    f"Most recent event does not have maximum completeness for visit "
                    f"{ptid}/{visit_date}/{visit_number}: "
                    f"recent={most_recent_completeness}, max={max_completeness}"
                )

            # Test that querying supports analytical use cases
            # Verify we can efficiently find the latest status for reporting
            latest_action = most_recent_event["action"]
            latest_timestamp = most_recent_event["timestamp"]

            # Should be able to query for visits with specific latest status
            assert latest_action in ["submit", "pass-qc", "not-pass-qc", "delete"], (
                f"Invalid action in most recent event: {latest_action}"
            )

            # Should be able to use this for monthly reporting queries
            # (e.g., count visits by latest status)
            assert latest_timestamp is not None, (
                "Most recent event should have valid timestamp for temporal analysis"
            )

        # Test cross-visit analysis capabilities
        # Verify that we can identify the most recent event across all visits
        if len(visit_specs) > 1:
            # Find the globally most recent event
            global_recent = df.sort("timestamp", descending=True).row(0, named=True)

            # Should be able to identify this event's visit
            assert global_recent["ptid"] is not None
            assert global_recent["visit_date"] is not None
            assert global_recent["timestamp"] is not None

            # Should be the latest timestamp across all events
            all_timestamps = df["timestamp"].to_list()
            global_max_timestamp = max(all_timestamps)
            assert global_recent["timestamp"] == global_max_timestamp, (
                "Global most recent event does not have the latest timestamp"
            )

        # Test that the checkpoint supports efficient querying for completeness analysis
        # Verify schema supports all required fields for analysis
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
        assert list(df.columns) == expected_columns, (
            "Checkpoint schema does not support required fields for "
            "completeness analysis"
        )
