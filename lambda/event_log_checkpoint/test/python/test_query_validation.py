"""Unit tests for query validation basic functionality.

This module contains unit tests to verify that parquet checkpoint files
support basic analytical queries for monthly reports, specifically
filtering by center_label and counting events by action type.
"""

from datetime import datetime

import polars as pl
from checkpoint_lambda.query_validation import (
    calculate_qc_timing_metrics,
    calculate_submission_timing_metrics,
    count_by_center_and_action,
    count_events_by_action,
    count_not_pass_qc_events,
    filter_by_center_and_action,
    filter_by_center_label,
    filter_by_date_range,
    filter_by_packet_type,
    filter_by_timestamp_range,
    get_action_counts,
    get_actions_list,
    get_centers_list,
    group_and_count_by_multiple_fields,
    group_by_packet_type,
    validate_parquet_schema_supports_filtering,
)
from polars import DataFrame

# Test data constants to prevent E501 line length errors
CENTER_ALPHA = "alpha"
CENTER_BETA = "beta"
CENTER_GAMMA = "gamma"

ACTION_SUBMIT = "submit"
ACTION_PASS_QC = "pass-qc"
ACTION_NOT_PASS_QC = "not-pass-qc"
ACTION_DELETE = "delete"

PTID_ABC123 = "ABC123"
PTID_XYZ789 = "XYZ789"
PTID_DEF456 = "DEF456"
PTID_GHI789 = "GHI789"

VISIT_DATE_JAN15 = "2024-01-15"
VISIT_DATE_JAN16 = "2024-01-16"
VISIT_DATE_JAN17 = "2024-01-17"

TIMESTAMP_JAN15_10AM = datetime(2024, 1, 15, 10, 0, 0)
TIMESTAMP_JAN15_11AM = datetime(2024, 1, 15, 11, 0, 0)
TIMESTAMP_JAN16_10AM = datetime(2024, 1, 16, 10, 0, 0)
TIMESTAMP_JAN16_11AM = datetime(2024, 1, 16, 11, 0, 0)
TIMESTAMP_JAN17_10AM = datetime(2024, 1, 17, 10, 0, 0)


class TestQueryValidationBasic:
    """Unit tests for basic query validation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.bucket = "test-query-bucket"
        self.key = "checkpoints/test-query-checkpoint.parquet"

    def create_sample_checkpoint_data(self) -> DataFrame:
        """Create sample checkpoint data for testing queries.

        Returns:
            DataFrame with diverse event data for testing filtering and counting
        """
        sample_data = {
            "action": [
                ACTION_SUBMIT,
                ACTION_PASS_QC,
                ACTION_NOT_PASS_QC,
                ACTION_SUBMIT,
                ACTION_DELETE,
                ACTION_PASS_QC,
            ],
            "study": ["adrc", "adrc", "adrc", "adrc", "adrc", "adrc"],
            "pipeline_adcid": [42, 42, 42, 43, 43, 43],
            "project_label": [
                "ingest",
                "ingest",
                "ingest",
                "ingest",
                "ingest",
                "ingest",
            ],
            "center_label": [
                CENTER_ALPHA,
                CENTER_ALPHA,
                CENTER_ALPHA,
                CENTER_BETA,
                CENTER_BETA,
                CENTER_GAMMA,
            ],
            "gear_name": [
                "form-gear",
                "form-gear",
                "form-gear",
                "form-gear",
                "form-gear",
                "form-gear",
            ],
            "ptid": [
                PTID_ABC123,
                PTID_ABC123,
                PTID_XYZ789,
                PTID_DEF456,
                PTID_DEF456,
                PTID_GHI789,
            ],
            "visit_date": [
                VISIT_DATE_JAN15,
                VISIT_DATE_JAN15,
                VISIT_DATE_JAN16,
                VISIT_DATE_JAN16,
                VISIT_DATE_JAN16,
                VISIT_DATE_JAN17,
            ],
            "visit_number": ["01", "01", "02", "01", "01", "03"],
            "datatype": ["form", "form", "form", "form", "form", "form"],
            "module": ["UDS", "UDS", "UDS", "FTLD", "FTLD", "LBD"],
            "packet": ["I", "I", "A", "I", "I", "B"],
            "timestamp": [
                TIMESTAMP_JAN15_10AM,
                TIMESTAMP_JAN15_11AM,
                TIMESTAMP_JAN16_10AM,
                TIMESTAMP_JAN16_11AM,
                TIMESTAMP_JAN16_11AM,
                TIMESTAMP_JAN17_10AM,
            ],
        }
        return DataFrame(sample_data)

    def test_filter_by_center_label_single_center(
        self, s3_client, setup_s3_environment
    ):
        """Test filtering parquet file by center_label returns correct events.

        Validates requirement 5.1: WHEN querying the checkpoint file by
        center_label THEN the system SHALL return all events for that
        center efficiently.
        """
        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_sample_checkpoint_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Query for center_label = "alpha"
        result_df = pl.read_parquet(s3_uri).filter(
            pl.col("center_label") == CENTER_ALPHA
        )

        # Verify results
        assert len(result_df) == 3  # Should have 3 events for center alpha
        assert result_df["center_label"].to_list() == [CENTER_ALPHA] * 3

        # Verify we got the correct events (all alpha events)
        expected_ptids = [PTID_ABC123, PTID_ABC123, PTID_XYZ789]
        assert result_df["ptid"].to_list() == expected_ptids

        expected_actions = [ACTION_SUBMIT, ACTION_PASS_QC, ACTION_NOT_PASS_QC]
        assert result_df["action"].to_list() == expected_actions

    def test_filter_by_center_label_multiple_centers(
        self, s3_client, setup_s3_environment
    ):
        """Test filtering parquet file by different center_labels returns
        correct events."""
        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_sample_checkpoint_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Query for center_label = "beta"
        beta_result = pl.read_parquet(s3_uri).filter(
            pl.col("center_label") == CENTER_BETA
        )
        assert len(beta_result) == 2  # Should have 2 events for center beta
        assert beta_result["center_label"].to_list() == [CENTER_BETA] * 2

        # Query for center_label = "gamma"
        gamma_result = pl.read_parquet(s3_uri).filter(
            pl.col("center_label") == CENTER_GAMMA
        )
        assert len(gamma_result) == 1  # Should have 1 event for center gamma
        assert gamma_result["center_label"].to_list() == [CENTER_GAMMA]

    def test_filter_by_center_label_no_matches(self, s3_client, setup_s3_environment):
        """Test filtering by non-existent center_label returns empty result."""
        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_sample_checkpoint_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Query for non-existent center
        result_df = pl.read_parquet(s3_uri).filter(
            pl.col("center_label") == "nonexistent"
        )

        # Verify empty result
        assert len(result_df) == 0

    def test_count_events_by_action_not_pass_qc(self, s3_client, setup_s3_environment):
        """Test counting events where action equals not-pass-qc.

        Validates requirement 5.2: WHEN querying for visits with errors
        THEN the system SHALL support counting events where action
        equals not-pass-qc.
        """
        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_sample_checkpoint_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Count events where action = "not-pass-qc"
        not_pass_qc_count = (
            pl.read_parquet(s3_uri)
            .filter(pl.col("action") == ACTION_NOT_PASS_QC)
            .height
        )

        # Verify count - should be 1 based on our sample data
        assert not_pass_qc_count == 1

    def test_count_events_by_all_action_types(self, s3_client, setup_s3_environment):
        """Test counting events by all action types to verify data
        integrity."""
        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_sample_checkpoint_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Count events by action type
        action_counts = (
            pl.read_parquet(s3_uri)
            .group_by("action")
            .agg(pl.len().alias("count"))
            .sort("action")
        )

        # Convert to dictionary for easier verification
        counts_dict = dict(
            zip(
                action_counts["action"].to_list(),
                action_counts["count"].to_list(),
                strict=False,
            )
        )

        # Verify counts based on our sample data
        expected_counts = {
            ACTION_DELETE: 1,
            ACTION_NOT_PASS_QC: 1,
            ACTION_PASS_QC: 2,
            ACTION_SUBMIT: 2,
        }

        assert counts_dict == expected_counts

    def test_count_events_by_action_with_center_filter(
        self, s3_client, setup_s3_environment
    ):
        """Test counting events by action type with center_label filtering."""
        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_sample_checkpoint_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Count not-pass-qc events for center alpha only
        alpha_not_pass_qc_count = (
            pl.read_parquet(s3_uri)
            .filter(
                (pl.col("center_label") == CENTER_ALPHA)
                & (pl.col("action") == ACTION_NOT_PASS_QC)
            )
            .height
        )

        # Verify count - should be 1 (only XYZ789 in alpha has not-pass-qc)
        assert alpha_not_pass_qc_count == 1

        # Count not-pass-qc events for center beta (should be 0)
        beta_not_pass_qc_count = (
            pl.read_parquet(s3_uri)
            .filter(
                (pl.col("center_label") == CENTER_BETA)
                & (pl.col("action") == ACTION_NOT_PASS_QC)
            )
            .height
        )

        assert beta_not_pass_qc_count == 0

    def test_empty_parquet_file_queries(self, s3_client, setup_s3_environment):
        """Test queries on empty parquet file return appropriate results."""
        # Import here to avoid import issues during test discovery
        from checkpoint_lambda.checkpoint import Checkpoint

        # Create bucket and empty checkpoint
        s3_client.create_bucket(Bucket=self.bucket)
        empty_checkpoint = Checkpoint.empty()

        # Write empty checkpoint to S3
        s3_uri = f"s3://{self.bucket}/{self.key}"
        empty_checkpoint.dataframe.write_parquet(s3_uri)

        # Test filtering empty file
        result_df = pl.read_parquet(s3_uri).filter(
            pl.col("center_label") == CENTER_ALPHA
        )
        assert len(result_df) == 0

        # Test counting on empty file
        not_pass_qc_count = (
            pl.read_parquet(s3_uri)
            .filter(pl.col("action") == ACTION_NOT_PASS_QC)
            .height
        )
        assert not_pass_qc_count == 0

    def test_parquet_schema_supports_filtering(self, s3_client, setup_s3_environment):
        """Test that parquet schema preserves data types for efficient
        filtering."""
        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_sample_checkpoint_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and verify schema
        read_df = pl.read_parquet(s3_uri)

        # Verify key columns have correct types for efficient filtering
        assert read_df.schema["center_label"] == pl.Utf8
        assert read_df.schema["action"] == pl.Utf8
        assert read_df.schema["timestamp"] == pl.Datetime(
            "us"
        )  # Parquet doesn't preserve timezone
        assert (
            read_df.schema["pipeline_adcid"] == pl.Int64
        )  # Polars converts to Int64 in parquet

        # Verify filtering operations work efficiently (no type conversion needed)
        filtered_result = read_df.filter(pl.col("center_label") == CENTER_ALPHA)
        assert len(filtered_result) > 0

        # Verify all filtered results have the expected center_label
        assert filtered_result["center_label"].to_list() == [CENTER_ALPHA] * len(
            filtered_result
        )


class TestQueryValidationUtilities:
    """Unit tests for query validation utility functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.bucket = "test-query-bucket"
        self.key = "checkpoints/test-query-checkpoint.parquet"

    def create_sample_checkpoint_data(self) -> DataFrame:
        """Create sample checkpoint data for testing queries.

        Returns:
            DataFrame with diverse event data for testing filtering and counting
        """
        sample_data = {
            "action": [
                ACTION_SUBMIT,
                ACTION_PASS_QC,
                ACTION_NOT_PASS_QC,
                ACTION_SUBMIT,
                ACTION_DELETE,
                ACTION_PASS_QC,
            ],
            "study": ["adrc", "adrc", "adrc", "adrc", "adrc", "adrc"],
            "pipeline_adcid": [42, 42, 42, 43, 43, 43],
            "project_label": [
                "ingest",
                "ingest",
                "ingest",
                "ingest",
                "ingest",
                "ingest",
            ],
            "center_label": [
                CENTER_ALPHA,
                CENTER_ALPHA,
                CENTER_ALPHA,
                CENTER_BETA,
                CENTER_BETA,
                CENTER_GAMMA,
            ],
            "gear_name": [
                "form-gear",
                "form-gear",
                "form-gear",
                "form-gear",
                "form-gear",
                "form-gear",
            ],
            "ptid": [
                PTID_ABC123,
                PTID_ABC123,
                PTID_XYZ789,
                PTID_DEF456,
                PTID_DEF456,
                PTID_GHI789,
            ],
            "visit_date": [
                VISIT_DATE_JAN15,
                VISIT_DATE_JAN15,
                VISIT_DATE_JAN16,
                VISIT_DATE_JAN16,
                VISIT_DATE_JAN16,
                VISIT_DATE_JAN17,
            ],
            "visit_number": ["01", "01", "02", "01", "01", "03"],
            "datatype": ["form", "form", "form", "form", "form", "form"],
            "module": ["UDS", "UDS", "UDS", "FTLD", "FTLD", "LBD"],
            "packet": ["I", "I", "A", "I", "I", "B"],
            "timestamp": [
                TIMESTAMP_JAN15_10AM,
                TIMESTAMP_JAN15_11AM,
                TIMESTAMP_JAN16_10AM,
                TIMESTAMP_JAN16_11AM,
                TIMESTAMP_JAN16_11AM,
                TIMESTAMP_JAN17_10AM,
            ],
        }
        return DataFrame(sample_data)

    def test_filter_by_center_label_utility(self):
        """Test filter_by_center_label utility function."""
        sample_df = self.create_sample_checkpoint_data()

        # Test filtering by center alpha
        alpha_result = filter_by_center_label(sample_df, CENTER_ALPHA)
        assert len(alpha_result) == 3
        assert alpha_result["center_label"].to_list() == [CENTER_ALPHA] * 3

        # Test filtering by center beta
        beta_result = filter_by_center_label(sample_df, CENTER_BETA)
        assert len(beta_result) == 2
        assert beta_result["center_label"].to_list() == [CENTER_BETA] * 2

        # Test filtering by non-existent center
        empty_result = filter_by_center_label(sample_df, "nonexistent")
        assert len(empty_result) == 0

    def test_count_events_by_action_utility(self):
        """Test count_events_by_action utility function."""
        sample_df = self.create_sample_checkpoint_data()

        # Test counting different action types
        assert count_events_by_action(sample_df, ACTION_SUBMIT) == 2
        assert count_events_by_action(sample_df, ACTION_PASS_QC) == 2
        assert count_events_by_action(sample_df, ACTION_NOT_PASS_QC) == 1
        assert count_events_by_action(sample_df, ACTION_DELETE) == 1

        # Test counting non-existent action
        assert count_events_by_action(sample_df, "nonexistent") == 0

    def test_count_not_pass_qc_events_utility(self):
        """Test count_not_pass_qc_events convenience function."""
        sample_df = self.create_sample_checkpoint_data()

        # Test the convenience function
        assert count_not_pass_qc_events(sample_df) == 1

    def test_get_action_counts_utility(self):
        """Test get_action_counts utility function."""
        sample_df = self.create_sample_checkpoint_data()

        action_counts = get_action_counts(sample_df)

        expected_counts = {
            ACTION_DELETE: 1,
            ACTION_NOT_PASS_QC: 1,
            ACTION_PASS_QC: 2,
            ACTION_SUBMIT: 2,
        }

        assert action_counts == expected_counts

    def test_filter_by_center_and_action_utility(self):
        """Test filter_by_center_and_action utility function."""
        sample_df = self.create_sample_checkpoint_data()

        # Test filtering by center alpha and not-pass-qc action
        alpha_not_pass_qc = filter_by_center_and_action(
            sample_df, CENTER_ALPHA, ACTION_NOT_PASS_QC
        )
        assert len(alpha_not_pass_qc) == 1
        assert alpha_not_pass_qc["center_label"].to_list() == [CENTER_ALPHA]
        assert alpha_not_pass_qc["action"].to_list() == [ACTION_NOT_PASS_QC]

        # Test filtering by center beta and not-pass-qc action (should be empty)
        beta_not_pass_qc = filter_by_center_and_action(
            sample_df, CENTER_BETA, ACTION_NOT_PASS_QC
        )
        assert len(beta_not_pass_qc) == 0

    def test_count_by_center_and_action_utility(self):
        """Test count_by_center_and_action utility function."""
        sample_df = self.create_sample_checkpoint_data()

        # Test counting by center and action
        assert (
            count_by_center_and_action(sample_df, CENTER_ALPHA, ACTION_NOT_PASS_QC) == 1
        )
        assert (
            count_by_center_and_action(sample_df, CENTER_BETA, ACTION_NOT_PASS_QC) == 0
        )
        assert count_by_center_and_action(sample_df, CENTER_ALPHA, ACTION_SUBMIT) == 1

    def test_validate_parquet_schema_supports_filtering(self):
        """Test validate_parquet_schema_supports_filtering utility function."""
        sample_df = self.create_sample_checkpoint_data()

        # Test that our sample data has a valid schema
        assert validate_parquet_schema_supports_filtering(sample_df) is True

    def test_get_centers_list_utility(self):
        """Test get_centers_list utility function."""
        sample_df = self.create_sample_checkpoint_data()

        centers = get_centers_list(sample_df)
        expected_centers = [CENTER_ALPHA, CENTER_BETA, CENTER_GAMMA]

        assert centers == expected_centers

    def test_get_actions_list_utility(self):
        """Test get_actions_list utility function."""
        sample_df = self.create_sample_checkpoint_data()

        actions = get_actions_list(sample_df)
        expected_actions = [
            ACTION_DELETE,
            ACTION_NOT_PASS_QC,
            ACTION_PASS_QC,
            ACTION_SUBMIT,
        ]

        assert actions == expected_actions

    def test_utility_functions_with_empty_dataframe(self):
        """Test utility functions with empty DataFrame."""
        # Import here to avoid import issues during test discovery
        from checkpoint_lambda.checkpoint import Checkpoint

        empty_df = Checkpoint.empty().dataframe

        # Test filtering functions return empty results
        assert len(filter_by_center_label(empty_df, CENTER_ALPHA)) == 0
        assert count_events_by_action(empty_df, ACTION_SUBMIT) == 0
        assert count_not_pass_qc_events(empty_df) == 0

        # Test aggregation functions return empty results
        assert get_action_counts(empty_df) == {}
        assert get_centers_list(empty_df) == []
        assert get_actions_list(empty_df) == []

        # Test schema validation (empty DataFrame should still have correct schema)
        assert validate_parquet_schema_supports_filtering(empty_df) is True


class TestQueryValidationAdvancedFiltering:
    """Unit tests for advanced query validation filtering functionality.

    Tests for requirements 5.3, 5.5, and 5.6:
    - Filtering by packet type
    - Date range filtering
    - Grouping and counting by multiple fields
    """

    def setup_method(self):
        """Set up test fixtures."""
        self.bucket = "test-advanced-query-bucket"
        self.key = "checkpoints/test-advanced-query-checkpoint.parquet"

    def create_advanced_sample_data(self) -> DataFrame:
        """Create sample checkpoint data with diverse packet types and dates
        for testing.

        Returns:
            DataFrame with diverse event data for testing advanced filtering
        """
        sample_data = {
            "action": [
                ACTION_SUBMIT,
                ACTION_PASS_QC,
                ACTION_NOT_PASS_QC,
                ACTION_SUBMIT,
                ACTION_DELETE,
                ACTION_PASS_QC,
                ACTION_SUBMIT,
                ACTION_PASS_QC,
            ],
            "study": ["adrc", "adrc", "adrc", "adrc", "adrc", "adrc", "adrc", "adrc"],
            "pipeline_adcid": [42, 42, 42, 43, 43, 43, 44, 44],
            "project_label": [
                "ingest",
                "ingest",
                "ingest",
                "ingest",
                "ingest",
                "ingest",
                "ingest",
                "ingest",
            ],
            "center_label": [
                CENTER_ALPHA,
                CENTER_ALPHA,
                CENTER_ALPHA,
                CENTER_BETA,
                CENTER_BETA,
                CENTER_GAMMA,
                CENTER_ALPHA,
                CENTER_BETA,
            ],
            "gear_name": [
                "form-gear",
                "form-gear",
                "form-gear",
                "form-gear",
                "form-gear",
                "form-gear",
                "form-gear",
                "form-gear",
            ],
            "ptid": [
                PTID_ABC123,
                PTID_ABC123,
                PTID_XYZ789,
                PTID_DEF456,
                PTID_DEF456,
                PTID_GHI789,
                "JKL012",
                "MNO345",
            ],
            "visit_date": [
                VISIT_DATE_JAN15,  # 2024-01-15
                VISIT_DATE_JAN15,  # 2024-01-15
                VISIT_DATE_JAN16,  # 2024-01-16
                VISIT_DATE_JAN16,  # 2024-01-16
                VISIT_DATE_JAN16,  # 2024-01-16
                VISIT_DATE_JAN17,  # 2024-01-17
                "2024-01-18",  # Additional date for range testing
                "2024-01-19",  # Additional date for range testing
            ],
            "visit_number": ["01", "01", "02", "01", "01", "03", "01", "02"],
            "datatype": [
                "form",
                "form",
                "form",
                "form",
                "form",
                "form",
                "form",
                "form",
            ],
            "module": ["UDS", "UDS", "UDS", "FTLD", "FTLD", "LBD", "UDS", "FTLD"],
            "packet": ["I", "I", "A", "I", "I", "B", "C", "A"],  # Diverse packet types
            "timestamp": [
                TIMESTAMP_JAN15_10AM,  # 2024-01-15 10:00:00
                TIMESTAMP_JAN15_11AM,  # 2024-01-15 11:00:00
                TIMESTAMP_JAN16_10AM,  # 2024-01-16 10:00:00
                TIMESTAMP_JAN16_11AM,  # 2024-01-16 11:00:00
                TIMESTAMP_JAN16_11AM,  # 2024-01-16 11:00:00
                TIMESTAMP_JAN17_10AM,  # 2024-01-17 10:00:00
                datetime(2024, 1, 18, 14, 30, 0),  # 2024-01-18 14:30:00
                datetime(2024, 1, 19, 9, 15, 0),  # 2024-01-19 09:15:00
            ],
        }
        return DataFrame(sample_data)

    def test_filter_by_packet_type_single_packet(self, s3_client, setup_s3_environment):
        """Test filtering parquet file by packet type returns correct events.

        Validates requirement 5.5: WHEN querying by packet type THEN the
        system SHALL support filtering and grouping events by the packet
        field.
        """
        # Import here to avoid import issues during test discovery

        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_advanced_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and filter by packet type "I"
        read_df = pl.read_parquet(s3_uri)
        packet_i_result = filter_by_packet_type(read_df, "I")

        # Verify results - should have 4 events with packet "I"
        assert len(packet_i_result) == 4
        assert packet_i_result["packet"].to_list() == ["I"] * 4

        # Verify we got the correct events
        expected_ptids = [PTID_ABC123, PTID_ABC123, PTID_DEF456, PTID_DEF456]
        assert packet_i_result["ptid"].to_list() == expected_ptids

    def test_filter_by_packet_type_multiple_packets(
        self, s3_client, setup_s3_environment
    ):
        """Test filtering by different packet types returns correct events."""
        # Import here to avoid import issues during test discovery

        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_advanced_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and test different packet types
        read_df = pl.read_parquet(s3_uri)

        # Test packet "A"
        packet_a_result = filter_by_packet_type(read_df, "A")
        assert len(packet_a_result) == 2  # Should have 2 events with packet "A"
        assert packet_a_result["packet"].to_list() == ["A"] * 2

        # Test packet "B"
        packet_b_result = filter_by_packet_type(read_df, "B")
        assert len(packet_b_result) == 1  # Should have 1 event with packet "B"
        assert packet_b_result["packet"].to_list() == ["B"]

        # Test packet "C"
        packet_c_result = filter_by_packet_type(read_df, "C")
        assert len(packet_c_result) == 1  # Should have 1 event with packet "C"
        assert packet_c_result["packet"].to_list() == ["C"]

    def test_group_by_packet_type(self, s3_client, setup_s3_environment):
        """Test grouping events by packet type and counting them.

        Validates requirement 5.5: WHEN querying by packet type THEN the
        system SHALL support filtering and grouping events by the packet
        field.
        """
        # Import here to avoid import issues during test discovery

        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_advanced_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and group by packet type
        read_df = pl.read_parquet(s3_uri)
        packet_counts = group_by_packet_type(read_df)

        # Convert to dictionary for easier verification
        counts_dict = dict(
            zip(
                packet_counts["packet"].to_list(),
                packet_counts["count"].to_list(),
                strict=False,
            )
        )

        # Verify counts based on our sample data
        expected_counts = {
            "A": 2,  # XYZ789 and MNO345
            "B": 1,  # GHI789
            "C": 1,  # JKL012
            "I": 4,  # ABC123 (2), DEF456 (2)
        }

        assert counts_dict == expected_counts

    def test_filter_by_date_range_visit_date(self, s3_client, setup_s3_environment):
        """Test filtering events by visit_date range.

        Validates requirement 5.6: WHEN querying by date range THEN the
        system SHALL support filtering events where visit_date or
        timestamp falls within specified bounds.
        """
        # Import here to avoid import issues during test discovery

        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_advanced_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and test date range filtering
        read_df = pl.read_parquet(s3_uri)

        # Test filtering by visit_date range (2024-01-16 to 2024-01-17)
        date_range_result = filter_by_date_range(
            read_df,
            start_date="2024-01-16",
            end_date="2024-01-17",
            date_field="visit_date",
        )

        # Should have 4 events (3 on 2024-01-16, 1 on 2024-01-17)
        assert len(date_range_result) == 4

        # Verify all dates are within range
        visit_dates = date_range_result["visit_date"].to_list()
        assert all(
            date >= "2024-01-16" and date <= "2024-01-17" for date in visit_dates
        )

    def test_filter_by_date_range_start_only(self, s3_client, setup_s3_environment):
        """Test filtering events with only start date specified."""
        # Import here to avoid import issues during test discovery

        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_advanced_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and test start date only
        read_df = pl.read_parquet(s3_uri)

        # Test filtering with start_date only (>= 2024-01-17)
        start_only_result = filter_by_date_range(
            read_df, start_date="2024-01-17", date_field="visit_date"
        )

        # Should have 3 events (1 on 2024-01-17, 1 on 2024-01-18, 1 on 2024-01-19)
        assert len(start_only_result) == 3

        # Verify all dates are >= start date
        visit_dates = start_only_result["visit_date"].to_list()
        assert all(date >= "2024-01-17" for date in visit_dates)

    def test_filter_by_date_range_end_only(self, s3_client, setup_s3_environment):
        """Test filtering events with only end date specified."""
        # Import here to avoid import issues during test discovery

        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_advanced_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and test end date only
        read_df = pl.read_parquet(s3_uri)

        # Test filtering with end_date only (<= 2024-01-16)
        end_only_result = filter_by_date_range(
            read_df, end_date="2024-01-16", date_field="visit_date"
        )

        # Should have 5 events (2 on 2024-01-15, 3 on 2024-01-16)
        assert len(end_only_result) == 5

        # Verify all dates are <= end date
        visit_dates = end_only_result["visit_date"].to_list()
        assert all(date <= "2024-01-16" for date in visit_dates)

    def test_filter_by_timestamp_range(self, s3_client, setup_s3_environment):
        """Test filtering events by timestamp range.

        Validates requirement 5.6: WHEN querying by date range THEN the
        system SHALL support filtering events where visit_date or
        timestamp falls within specified bounds.
        """
        # Import here to avoid import issues during test discovery

        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_advanced_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and test timestamp range filtering
        read_df = pl.read_parquet(s3_uri)

        # Test filtering by timestamp range (2024-01-16 10:00:00 to 2024-01-17 10:00:00)
        start_ts = datetime(2024, 1, 16, 10, 0, 0)
        end_ts = datetime(2024, 1, 17, 10, 0, 0)

        timestamp_range_result = filter_by_timestamp_range(
            read_df, start_timestamp=start_ts, end_timestamp=end_ts
        )

        # Should have 4 events within this timestamp range
        assert len(timestamp_range_result) == 4

        # Verify all timestamps are within range
        timestamps = timestamp_range_result["timestamp"].to_list()
        assert all(start_ts <= ts <= end_ts for ts in timestamps)

    def test_group_and_count_by_multiple_fields(self, s3_client, setup_s3_environment):
        """Test grouping and counting events by multiple fields.

        Validates requirement 5.7: WHEN counting visit volumes THEN the
        system SHALL support grouping and counting events by module,
        packet, and action type.
        """
        # Import here to avoid import issues during test discovery

        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_advanced_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and test multi-field grouping
        read_df = pl.read_parquet(s3_uri)

        # Test grouping by module, packet, and action
        multi_group_result = group_and_count_by_multiple_fields(
            read_df, ["module", "packet", "action"]
        )

        # Verify we have the expected number of unique combinations
        assert len(multi_group_result) > 0

        # Verify the result has the expected columns
        expected_columns = {"module", "packet", "action", "count"}
        assert set(multi_group_result.columns) == expected_columns

        # Test grouping by just module and action
        module_action_result = group_and_count_by_multiple_fields(
            read_df, ["module", "action"]
        )

        # Verify we have the expected columns
        expected_columns = {"module", "action", "count"}
        assert set(module_action_result.columns) == expected_columns

        # Verify counts sum to total events
        total_count = module_action_result["count"].sum()
        assert total_count == len(read_df)

    def test_calculate_submission_timing_metrics(self, s3_client, setup_s3_environment):
        """Test calculating time differences between visit_date and submit
        timestamps.

        Validates requirement 5.3: WHEN calculating submission timing
        metrics THEN the system SHALL support computing time differences
        between visit_date and submit event timestamps.
        """
        # Import here to avoid import issues during test discovery

        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_advanced_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and calculate submission timing metrics
        read_df = pl.read_parquet(s3_uri)
        timing_result = calculate_submission_timing_metrics(read_df)

        # Should have 3 submit events in our sample data
        assert len(timing_result) == 3

        # Verify we have the timing calculation column
        assert "days_from_visit_to_submit" in timing_result.columns

        # Verify all results are submit actions
        assert timing_result["action"].to_list() == [ACTION_SUBMIT] * 3

        # Verify timing calculations are reasonable
        # (should be 0 for same-day submissions)
        timing_values = timing_result["days_from_visit_to_submit"].to_list()
        assert all(isinstance(val, (int, float)) for val in timing_values)

    def test_advanced_filtering_with_empty_results(
        self, s3_client, setup_s3_environment
    ):
        """Test advanced filtering functions with queries that return empty
        results."""
        # Import here to avoid import issues during test discovery

        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_advanced_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and test empty results
        read_df = pl.read_parquet(s3_uri)

        # Test filtering by non-existent packet type
        empty_packet_result = filter_by_packet_type(read_df, "NONEXISTENT")
        assert len(empty_packet_result) == 0

        # Test filtering by date range with no matches
        empty_date_result = filter_by_date_range(
            read_df,
            start_date="2025-01-01",
            end_date="2025-01-31",
            date_field="visit_date",
        )
        assert len(empty_date_result) == 0

        # Test filtering by timestamp range with no matches
        future_start = datetime(2025, 1, 1, 0, 0, 0)
        future_end = datetime(2025, 1, 31, 23, 59, 59)
        empty_timestamp_result = filter_by_timestamp_range(
            read_df, start_timestamp=future_start, end_timestamp=future_end
        )
        assert len(empty_timestamp_result) == 0


class TestQueryValidationTemporalCalculations:
    """Unit tests for temporal calculation functionality.

    Tests for requirements 5.4, 5.7, and 5.8:
    - QC timing metrics (visit_date to pass-qc timestamp differences)
    - Visit volume counting by multiple fields
    - QC pass rate analysis
    """

    def setup_method(self):
        """Set up test fixtures."""
        self.bucket = "test-temporal-query-bucket"
        self.key = "checkpoints/test-temporal-query-checkpoint.parquet"

    def create_temporal_sample_data(self) -> DataFrame:
        """Create sample checkpoint data with temporal patterns for testing.

        Returns:
            DataFrame with diverse temporal event data for testing calculations
        """
        sample_data = {
            "action": [
                ACTION_SUBMIT,
                ACTION_PASS_QC,
                ACTION_SUBMIT,
                ACTION_PASS_QC,
                ACTION_NOT_PASS_QC,
                ACTION_SUBMIT,
                ACTION_PASS_QC,
                ACTION_NOT_PASS_QC,
                ACTION_SUBMIT,
                ACTION_PASS_QC,
            ],
            "study": ["adrc"] * 10,
            "pipeline_adcid": [42, 42, 43, 43, 43, 44, 44, 44, 45, 45],
            "project_label": ["ingest"] * 10,
            "center_label": [
                CENTER_ALPHA,
                CENTER_ALPHA,
                CENTER_BETA,
                CENTER_BETA,
                CENTER_BETA,
                CENTER_GAMMA,
                CENTER_GAMMA,
                CENTER_GAMMA,
                CENTER_ALPHA,
                CENTER_ALPHA,
            ],
            "gear_name": ["form-gear"] * 10,
            "ptid": [
                PTID_ABC123,
                PTID_ABC123,
                PTID_XYZ789,
                PTID_XYZ789,
                PTID_XYZ789,
                PTID_DEF456,
                PTID_DEF456,
                PTID_DEF456,
                PTID_GHI789,
                PTID_GHI789,
            ],
            "visit_date": [
                VISIT_DATE_JAN15,  # 2024-01-15
                VISIT_DATE_JAN15,  # 2024-01-15
                VISIT_DATE_JAN16,  # 2024-01-16
                VISIT_DATE_JAN16,  # 2024-01-16
                VISIT_DATE_JAN16,  # 2024-01-16
                VISIT_DATE_JAN17,  # 2024-01-17
                VISIT_DATE_JAN17,  # 2024-01-17
                VISIT_DATE_JAN17,  # 2024-01-17
                "2024-01-18",  # Different date for timing calculations
                "2024-01-18",  # Different date for timing calculations
            ],
            "visit_number": [
                "01",
                "01",
                "02",
                "02",
                "02",
                "01",
                "01",
                "01",
                "03",
                "03",
            ],
            "datatype": ["form"] * 10,
            "module": [
                "UDS",
                "UDS",
                "FTLD",
                "FTLD",
                "FTLD",
                "LBD",
                "LBD",
                "LBD",
                "UDS",
                "UDS",
            ],
            "packet": ["I", "I", "A", "A", "A", "B", "B", "B", "C", "C"],
            "timestamp": [
                # Same day submissions and QC
                TIMESTAMP_JAN15_10AM,  # submit on same day as visit
                datetime(2024, 1, 15, 16, 0, 0),  # pass-qc 6 hours later same day
                TIMESTAMP_JAN16_10AM,  # submit on same day as visit
                datetime(2024, 1, 16, 18, 0, 0),  # pass-qc 8 hours later same day
                datetime(2024, 1, 16, 19, 0, 0),  # not-pass-qc 9 hours later same day
                TIMESTAMP_JAN17_10AM,  # submit on same day as visit
                datetime(2024, 1, 18, 14, 0, 0),  # pass-qc next day (1 day later)
                datetime(2024, 1, 18, 15, 0, 0),  # not-pass-qc next day (1 day later)
                # Multi-day delays
                datetime(2024, 1, 18, 9, 0, 0),  # submit on same day as visit
                datetime(2024, 1, 21, 11, 0, 0),  # pass-qc 3 days later
            ],
        }
        return DataFrame(sample_data)

    def test_calculate_qc_timing_metrics_same_day(
        self, s3_client, setup_s3_environment
    ):
        """Test calculating QC timing metrics for same-day QC events.

        Validates requirement 5.4: WHEN calculating QC timing metrics
        THEN the system SHALL support computing time differences between
        visit_date and pass-qc event timestamps.
        """
        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_temporal_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and calculate QC timing metrics
        read_df = pl.read_parquet(s3_uri)
        qc_timing_result = calculate_qc_timing_metrics(read_df)

        # Should have 4 pass-qc events in our sample data
        assert len(qc_timing_result) == 4

        # Verify we have the timing calculation column
        assert "days_from_visit_to_qc" in qc_timing_result.columns

        # Verify all results are pass-qc actions
        assert qc_timing_result["action"].to_list() == [ACTION_PASS_QC] * 4

        # Verify timing calculations
        timing_values = qc_timing_result["days_from_visit_to_qc"].to_list()

        # Check that we have reasonable timing values
        assert all(isinstance(val, (int, float)) for val in timing_values)

        # Check specific timing expectations based on our test data
        # Two same-day QC events should have 0 days difference
        same_day_count = sum(1 for val in timing_values if val == 0)
        assert same_day_count >= 2  # At least 2 same-day QC events

        # One next-day QC event should have 1 day difference
        next_day_count = sum(1 for val in timing_values if val == 1)
        assert next_day_count >= 1  # At least 1 next-day QC event

        # One multi-day QC event should have 3 days difference
        multi_day_count = sum(1 for val in timing_values if val == 3)
        assert multi_day_count >= 1  # At least 1 multi-day QC event

    def test_calculate_qc_timing_metrics_with_filtering(
        self, s3_client, setup_s3_environment
    ):
        """Test QC timing metrics combined with center filtering."""
        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_temporal_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and filter by center before calculating timing
        read_df = pl.read_parquet(s3_uri)
        alpha_events = filter_by_center_label(read_df, CENTER_ALPHA)
        alpha_qc_timing = calculate_qc_timing_metrics(alpha_events)

        # Should have 2 pass-qc events for center alpha
        assert len(alpha_qc_timing) == 2

        # Verify all are from center alpha
        assert alpha_qc_timing["center_label"].to_list() == [CENTER_ALPHA] * 2

        # Verify timing calculations exist
        timing_values = alpha_qc_timing["days_from_visit_to_qc"].to_list()
        assert all(isinstance(val, (int, float)) for val in timing_values)

    def test_calculate_submission_timing_metrics_comprehensive(
        self, s3_client, setup_s3_environment
    ):
        """Test comprehensive submission timing metrics calculation.

        Validates requirement 5.3: WHEN calculating submission timing
        metrics THEN the system SHALL support computing time differences
        between visit_date and submit event timestamps.
        """
        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_temporal_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and calculate submission timing metrics
        read_df = pl.read_parquet(s3_uri)
        submit_timing_result = calculate_submission_timing_metrics(read_df)

        # Should have 4 submit events in our sample data
        assert len(submit_timing_result) == 4

        # Verify we have the timing calculation column
        assert "days_from_visit_to_submit" in submit_timing_result.columns

        # Verify all results are submit actions
        assert submit_timing_result["action"].to_list() == [ACTION_SUBMIT] * 4

        # Verify timing calculations - all should be 0 (same day submissions)
        timing_values = submit_timing_result["days_from_visit_to_submit"].to_list()
        assert all(val == 0 for val in timing_values)  # All same-day submissions

    def test_group_and_count_by_multiple_fields_comprehensive(
        self, s3_client, setup_s3_environment
    ):
        """Test comprehensive grouping and counting by multiple fields.

        Validates requirement 5.7: WHEN counting visit volumes THEN the
        system SHALL support grouping and counting events by module,
        packet, and action type.
        """
        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_temporal_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and test comprehensive multi-field grouping
        read_df = pl.read_parquet(s3_uri)

        # Test grouping by module, packet, and action (requirement 5.7)
        module_packet_action_result = group_and_count_by_multiple_fields(
            read_df, ["module", "packet", "action"]
        )

        # Verify we have the expected columns
        expected_columns = {"module", "packet", "action", "count"}
        assert set(module_packet_action_result.columns) == expected_columns

        # Verify counts sum to total events
        total_count = module_packet_action_result["count"].sum()
        assert total_count == len(read_df)

        # Test grouping by center, module, and action for visit volume analysis
        center_module_action_result = group_and_count_by_multiple_fields(
            read_df, ["center_label", "module", "action"]
        )

        # Verify we have the expected columns
        expected_columns = {"center_label", "module", "action", "count"}
        assert set(center_module_action_result.columns) == expected_columns

        # Verify counts sum to total events
        total_count = center_module_action_result["count"].sum()
        assert total_count == len(read_df)

        # Test that we can identify specific combinations
        # Should have UDS/I/submit combination
        uds_i_submit = center_module_action_result.filter(
            (pl.col("module") == "UDS") & (pl.col("action") == ACTION_SUBMIT)
        )
        assert len(uds_i_submit) > 0

    def test_qc_pass_rate_analysis(self, s3_client, setup_s3_environment):
        """Test QC pass rate analysis by comparing pass-qc vs not-pass-qc
        counts.

        Validates requirement 5.8: WHEN analyzing QC pass rates THEN the
        system SHALL support comparing counts of pass-qc versus not-
        pass-qc events.
        """
        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_temporal_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and analyze QC pass rates
        read_df = pl.read_parquet(s3_uri)

        # Count pass-qc vs not-pass-qc events
        pass_qc_count = count_events_by_action(read_df, ACTION_PASS_QC)
        not_pass_qc_count = count_events_by_action(read_df, ACTION_NOT_PASS_QC)

        # Verify we have both types of events
        assert pass_qc_count > 0
        assert not_pass_qc_count > 0

        # Calculate pass rate
        total_qc_events = pass_qc_count + not_pass_qc_count
        pass_rate = pass_qc_count / total_qc_events

        # Verify pass rate is reasonable (between 0 and 1)
        assert 0 <= pass_rate <= 1

        # Test QC pass rates by center
        centers = get_centers_list(read_df)
        center_pass_rates = {}

        for center in centers:
            center_pass_count = count_by_center_and_action(
                read_df, center, ACTION_PASS_QC
            )
            center_not_pass_count = count_by_center_and_action(
                read_df, center, ACTION_NOT_PASS_QC
            )

            center_total_qc = center_pass_count + center_not_pass_count
            if center_total_qc > 0:
                center_pass_rates[center] = center_pass_count / center_total_qc

        # Verify we calculated pass rates for centers with QC events
        assert len(center_pass_rates) > 0

        # Verify all pass rates are valid
        for _center, rate in center_pass_rates.items():
            assert 0 <= rate <= 1

    def test_qc_pass_rate_analysis_by_module(self, s3_client, setup_s3_environment):
        """Test QC pass rate analysis grouped by module."""
        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_temporal_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and analyze QC pass rates by module
        read_df = pl.read_parquet(s3_uri)

        # Group QC events by module and action
        qc_events = read_df.filter(
            pl.col("action").is_in([ACTION_PASS_QC, ACTION_NOT_PASS_QC])
        )

        module_qc_counts = group_and_count_by_multiple_fields(
            qc_events, ["module", "action"]
        )

        # Verify we have QC events for different modules
        assert len(module_qc_counts) > 0

        # Verify we have both pass and not-pass events
        actions_in_result = set(module_qc_counts["action"].to_list())
        assert ACTION_PASS_QC in actions_in_result
        assert ACTION_NOT_PASS_QC in actions_in_result

        # Calculate pass rates by module
        modules = set(module_qc_counts["module"].to_list())
        module_pass_rates = {}

        for module in modules:
            module_events = module_qc_counts.filter(pl.col("module") == module)

            pass_count = 0
            not_pass_count = 0

            for row in module_events.iter_rows(named=True):
                if row["action"] == ACTION_PASS_QC:
                    pass_count = row["count"]
                elif row["action"] == ACTION_NOT_PASS_QC:
                    not_pass_count = row["count"]

            total_count = pass_count + not_pass_count
            if total_count > 0:
                module_pass_rates[module] = pass_count / total_count

        # Verify we calculated pass rates for modules with QC events
        assert len(module_pass_rates) > 0

        # Verify all pass rates are valid
        for _module, rate in module_pass_rates.items():
            assert 0 <= rate <= 1

    def test_complex_temporal_query_patterns(self, s3_client, setup_s3_environment):
        """Test complex temporal query patterns combining multiple operations.

        Tests combining temporal calculations with filtering and
        grouping for comprehensive analytical queries.
        """
        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_temporal_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and perform complex temporal analysis
        read_df = pl.read_parquet(s3_uri)

        # Complex pattern 1: QC timing metrics for specific center and date range
        alpha_events = filter_by_center_label(read_df, CENTER_ALPHA)
        alpha_jan_events = filter_by_date_range(
            alpha_events,
            start_date="2024-01-15",
            end_date="2024-01-18",
            date_field="visit_date",
        )
        alpha_qc_timing = calculate_qc_timing_metrics(alpha_jan_events)

        # Should have QC events for center alpha in the date range
        if len(alpha_qc_timing) > 0:
            assert all(
                center == CENTER_ALPHA
                for center in alpha_qc_timing["center_label"].to_list()
            )
            assert "days_from_visit_to_qc" in alpha_qc_timing.columns

        # Complex pattern 2: Submission timing by packet type
        packet_i_events = filter_by_packet_type(read_df, "I")
        packet_i_submit_timing = calculate_submission_timing_metrics(packet_i_events)

        if len(packet_i_submit_timing) > 0:
            assert all(
                packet == "I" for packet in packet_i_submit_timing["packet"].to_list()
            )
            assert "days_from_visit_to_submit" in packet_i_submit_timing.columns

        # Complex pattern 3: QC pass rates by center and module combination
        center_module_qc = read_df.filter(
            pl.col("action").is_in([ACTION_PASS_QC, ACTION_NOT_PASS_QC])
        )

        center_module_counts = group_and_count_by_multiple_fields(
            center_module_qc, ["center_label", "module", "action"]
        )

        # Verify we can analyze pass rates by center-module combinations
        assert len(center_module_counts) > 0

        # Verify we have the expected structure for pass rate analysis
        expected_columns = {"center_label", "module", "action", "count"}
        assert set(center_module_counts.columns) == expected_columns

    def test_temporal_calculations_with_empty_results(
        self, s3_client, setup_s3_environment
    ):
        """Test temporal calculation functions with empty datasets."""
        # Create bucket and sample data
        s3_client.create_bucket(Bucket=self.bucket)
        sample_df = self.create_temporal_sample_data()

        # Write sample data to S3 as parquet
        s3_uri = f"s3://{self.bucket}/{self.key}"
        sample_df.write_parquet(s3_uri)

        # Read back and test with filters that return empty results
        read_df = pl.read_parquet(s3_uri)

        # Filter to get empty dataset
        empty_events = filter_by_center_label(read_df, "nonexistent_center")

        # Test temporal calculations on empty datasets
        empty_qc_timing = calculate_qc_timing_metrics(empty_events)
        assert len(empty_qc_timing) == 0

        empty_submit_timing = calculate_submission_timing_metrics(empty_events)
        assert len(empty_submit_timing) == 0

        empty_grouping = group_and_count_by_multiple_fields(
            empty_events, ["module", "action"]
        )
        assert len(empty_grouping) == 0
