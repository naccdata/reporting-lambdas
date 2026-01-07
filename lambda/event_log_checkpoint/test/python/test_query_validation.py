"""Unit tests for query validation basic functionality.

This module contains unit tests to verify that parquet checkpoint files
support basic analytical queries for monthly reports, specifically
filtering by center_label and counting events by action type.
"""

from datetime import datetime

import polars as pl
from checkpoint_lambda.query_validation import (
    count_by_center_and_action,
    count_events_by_action,
    count_not_pass_qc_events,
    filter_by_center_and_action,
    filter_by_center_label,
    get_action_counts,
    get_actions_list,
    get_centers_list,
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
