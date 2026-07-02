"""Unit tests for S3EventRetriever component.

This module contains unit tests for the S3EventRetriever class, testing
S3 operations, JSON retrieval, timestamp filtering, event validation,
and error handling scenarios using moto.server for realistic S3 testing.
"""

import json
import os
import re
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError
from checkpoint_lambda.models import VisitEvent
from checkpoint_lambda.s3_retriever import S3EventRetriever
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

# Test data constants to avoid line length issues
SUBMIT_FULL_LOG = "log-submit-20240115-100000-42-ingest-form-alpha-2024-01-15.json"
PASS_QC_FULL_LOG = "log-pass-qc-20240115-102000-42-ingest-form-alpha-2024-01-15.json"
NOT_PASS_QC_FULL_LOG = (
    "log-not-pass-qc-20240116-143000-43-ingest-dicom-beta-2024-01-16.json"
)
INVALID_CONTENT_LOG = "log-submit-20240116-100000-42-ingest-form-alpha-2024-01-16.json"
JSON_ERROR_LOG = "log-submit-20240115-100000-42-ingest-form-alpha-2024-01-15.json"


class TestS3EventRetrieverInit:
    """Test S3EventRetriever initialization."""

    def test_init_with_required_params(self):
        """Test initialization with only required parameters."""
        retriever = S3EventRetriever("test-bucket")

        assert retriever.bucket == "test-bucket"
        assert retriever.prefix == ""
        assert retriever.since_timestamp is None

    def test_init_with_all_params(self):
        """Test initialization with all parameters."""
        timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        retriever = S3EventRetriever("test-bucket", "logs/", timestamp)

        assert retriever.bucket == "test-bucket"
        assert retriever.prefix == "logs/"
        assert retriever.since_timestamp == timestamp


class TestListEventFiles:
    """Test list_event_files method."""

    def test_list_event_files_empty_bucket(self, s3_client, setup_s3_environment):
        """Test listing files from empty bucket."""
        bucket = "test-bucket-empty"

        # Create empty bucket
        s3_client.create_bucket(Bucket=bucket)

        retriever = S3EventRetriever(bucket)
        files = retriever.list_event_files()

        assert files == []

    def test_list_event_files_with_matching_pattern(
        self, s3_client, setup_s3_environment
    ):
        """Test listing files that match the log pattern."""
        bucket = "test-bucket-matching"

        # Create bucket
        s3_client.create_bucket(Bucket=bucket)

        # Upload test files
        test_files = [
            "log-submit-20240115.json",  # Short format
            "log-pass-qc-20240116.json",  # Short format
            "log-not-pass-qc-20240117.json",  # Short format
            "log-delete-20240118.json",  # Short format
            SUBMIT_FULL_LOG,  # Full format
            PASS_QC_FULL_LOG,  # Full format
            NOT_PASS_QC_FULL_LOG,  # Full format
            "other-file.json",  # Should be filtered out
            "log-invalid-action-20240119.json",  # Should be filtered out
        ]

        for file_key in test_files:
            s3_client.put_object(Bucket=bucket, Key=file_key, Body=b"test content")

        # Create a pattern that matches both short and full formats for testing
        test_pattern = re.compile(
            r"^.*log-(submit|pass-qc|not-pass-qc|delete)-(\d{8}\.json|\d{8}-\d{6}-\d+-[\w\-]+-[\w]+-\d{4}-\d{2}-\d{2}\.json)$"
        )
        retriever = S3EventRetriever(bucket, file_pattern=test_pattern)
        files = retriever.list_event_files()

        expected_files = [
            "log-submit-20240115.json",
            "log-pass-qc-20240116.json",
            "log-not-pass-qc-20240117.json",
            "log-delete-20240118.json",
            SUBMIT_FULL_LOG,
            PASS_QC_FULL_LOG,
            NOT_PASS_QC_FULL_LOG,
        ]
        # Sort both lists to avoid order dependency
        assert sorted(files) == sorted(expected_files)

    def test_list_event_files_with_prefix(self, s3_client, setup_s3_environment):
        """Test listing files with S3 prefix."""
        bucket = "test-bucket-prefix"
        prefix = "logs/"

        # Create bucket
        s3_client.create_bucket(Bucket=bucket)

        # Upload test files with prefix
        test_files = [
            "logs/log-submit-20240115.json",  # Short format
            f"logs/{SUBMIT_FULL_LOG}",  # Full format
        ]

        for file_key in test_files:
            s3_client.put_object(Bucket=bucket, Key=file_key, Body=b"test content")

        # Create a pattern that matches both short and full formats for testing
        test_pattern = re.compile(
            r"^.*log-(submit|pass-qc|not-pass-qc|delete)-(\d{8}\.json|\d{8}-\d{6}-\d+-[\w\-]+-[\w]+-\d{4}-\d{2}-\d{2}\.json)$"
        )
        retriever = S3EventRetriever(bucket, prefix, file_pattern=test_pattern)
        files = retriever.list_event_files()

        expected_files = [
            "logs/log-submit-20240115.json",
            f"logs/{SUBMIT_FULL_LOG}",
        ]
        # Sort both lists to avoid order dependency
        assert sorted(files) == sorted(expected_files)

    def test_list_event_files_default_pattern(self, s3_client, setup_s3_environment):
        """Test listing files with default pattern (full format only)."""
        bucket = "test-bucket-default"

        # Create bucket
        s3_client.create_bucket(Bucket=bucket)

        # Upload test files
        test_files = [
            "log-submit-20240115.json",  # Short format - should be filtered out
            SUBMIT_FULL_LOG,  # Full format - should be included
            PASS_QC_FULL_LOG,  # Full format - should be included
            "other-file.json",  # Should be filtered out
        ]

        for file_key in test_files:
            s3_client.put_object(Bucket=bucket, Key=file_key, Body=b"test content")

        # Use default pattern (full format only)
        retriever = S3EventRetriever(bucket)
        files = retriever.list_event_files()

        # Only full format files should be returned
        expected_files = [
            SUBMIT_FULL_LOG,
            PASS_QC_FULL_LOG,
        ]
        # Sort both lists to avoid order dependency
        assert sorted(files) == sorted(expected_files)

    def test_list_event_files_s3_error(self, setup_s3_environment):
        """Test handling S3 access errors during file listing."""
        # Use non-existent bucket to trigger S3 error
        retriever = S3EventRetriever("non-existent-bucket")

        with pytest.raises(ClientError):
            retriever.list_event_files()


class TestRetrieveEvent:
    """Test retrieve_event method."""

    def test_retrieve_event_valid_json(self, s3_client, setup_s3_environment):
        """Test retrieving valid JSON event from S3."""
        bucket = "test-bucket-retrieve-valid"
        key = "log-submit-20240115.json"

        # Create bucket
        s3_client.create_bucket(Bucket=bucket)

        event_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "form",
            "module": "UDS",
            "timestamp": "2024-01-15T10:00:00Z",
        }

        # Upload JSON file to S3
        s3_client.put_object(
            Bucket=bucket, Key=key, Body=json.dumps(event_data).encode()
        )

        retriever = S3EventRetriever(bucket)
        result = retriever.retrieve_event(key)

        # Should return a VisitEvent object, not a dict
        assert isinstance(result, VisitEvent)
        assert result.action == "submit"
        assert result.ptid == "ABC123"
        assert result.pipeline_adcid == 123

    def test_retrieve_event_invalid_json(self, s3_client, setup_s3_environment):
        """Test retrieving invalid JSON from S3."""
        bucket = "test-bucket-retrieve-invalid-json"
        key = "invalid-file.json"

        # Create bucket
        s3_client.create_bucket(Bucket=bucket)

        # Upload invalid JSON content
        s3_client.put_object(Bucket=bucket, Key=key, Body=b"invalid json content")

        retriever = S3EventRetriever(bucket)

        with pytest.raises(json.JSONDecodeError):
            retriever.retrieve_event(key)

    def test_retrieve_event_invalid_event_data(self, s3_client, setup_s3_environment):
        """Test retrieving JSON with invalid event data."""
        bucket = "test-bucket-retrieve-invalid-event"
        key = "invalid-event.json"

        # Create bucket
        s3_client.create_bucket(Bucket=bucket)

        # Valid JSON but invalid event data
        invalid_event_data = {
            "action": "invalid-action",  # Invalid action
            "pipeline_adcid": "not-a-number",  # Invalid type
            # Missing required fields
        }

        # Upload invalid event data
        s3_client.put_object(
            Bucket=bucket, Key=key, Body=json.dumps(invalid_event_data).encode()
        )

        retriever = S3EventRetriever(bucket)

        with pytest.raises(ValidationError):
            retriever.retrieve_event(key)

    def test_retrieve_event_s3_error(self, s3_client, setup_s3_environment):
        """Test handling S3 errors during event retrieval."""
        bucket = "test-bucket-retrieve-s3-error"
        key = "nonexistent-file.json"

        # Create bucket but don't upload the file
        s3_client.create_bucket(Bucket=bucket)

        retriever = S3EventRetriever(bucket)

        with pytest.raises(ClientError):
            retriever.retrieve_event(key)


class TestRetrieveAndValidateEvents:
    """Test retrieve_and_validate_events method."""

    def test_retrieve_and_validate_events_success(
        self, s3_client, setup_s3_environment
    ):
        """Test successful retrieval and validation of events."""
        bucket = "test-bucket-validate-success"

        # Create bucket
        s3_client.create_bucket(Bucket=bucket)

        # Create valid event data
        event_data_1 = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "form",
            "module": "UDS",
            "timestamp": "2024-01-15T10:00:00Z",
        }

        event_data_2 = {
            "action": "pass-qc",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-16",
            "datatype": "form",
            "module": "UDS",
            "timestamp": "2024-01-16T10:00:00Z",
        }

        # Upload files to S3
        s3_client.put_object(
            Bucket=bucket,
            Key=("log-submit-20240115-100000-42-ingest-form-alpha-2024-01-15.json"),
            Body=json.dumps(event_data_1).encode(),
        )
        s3_client.put_object(
            Bucket=bucket,
            Key=("log-pass-qc-20240116-100000-42-ingest-form-alpha-2024-01-16.json"),
            Body=json.dumps(event_data_2).encode(),
        )

        retriever = S3EventRetriever(bucket)
        valid_events, validation_errors = retriever.retrieve_and_validate_events()

        assert len(valid_events) == 2
        assert len(validation_errors) == 0
        assert all(isinstance(event, VisitEvent) for event in valid_events)
        # Sort events by action to avoid order dependency
        events_by_action = {event.action: event for event in valid_events}
        assert "submit" in events_by_action
        assert "pass-qc" in events_by_action

    def test_retrieve_and_validate_events_with_validation_errors(
        self, s3_client, setup_s3_environment
    ):
        """Test handling validation errors during event processing."""
        bucket = "test-bucket-validate-errors"

        # Create bucket
        s3_client.create_bucket(Bucket=bucket)

        # Create valid event data
        valid_event_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "form",
            "module": "UDS",
            "timestamp": "2024-01-15T10:00:00Z",
        }

        # Create invalid event data
        invalid_event_data = {
            "action": "invalid-action",  # Invalid action
            "pipeline_adcid": "not-a-number",  # Invalid type
            # Missing required fields
        }

        # Upload files to S3
        s3_client.put_object(
            Bucket=bucket,
            Key=SUBMIT_FULL_LOG,
            Body=json.dumps(valid_event_data).encode(),
        )
        s3_client.put_object(
            Bucket=bucket,
            Key=INVALID_CONTENT_LOG,  # Valid pattern but invalid content
            Body=json.dumps(invalid_event_data).encode(),
        )

        retriever = S3EventRetriever(bucket)
        valid_events, validation_errors = retriever.retrieve_and_validate_events()

        assert len(valid_events) == 1
        assert len(validation_errors) == 1
        assert valid_events[0].action == "submit"
        assert validation_errors[0]["source_key"] == INVALID_CONTENT_LOG
        assert "errors" in validation_errors[0]

    def test_retrieve_and_validate_events_no_timestamp_filtering(
        self, s3_client, setup_s3_environment
    ):
        """Test that all events are returned regardless of timestamp."""
        bucket = "test-bucket-validate-timestamp"

        # Create bucket
        s3_client.create_bucket(Bucket=bucket)

        # Create event data with different timestamps
        event_data_1 = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "form",
            "module": "UDS",
            "timestamp": "2024-01-15T10:00:00Z",  # Earlier timestamp
        }

        event_data_2 = {
            "action": "pass-qc",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-16",
            "datatype": "form",
            "module": "UDS",
            "timestamp": "2024-01-16T10:00:00Z",  # Later timestamp
        }

        # Upload files to S3
        s3_client.put_object(
            Bucket=bucket,
            Key=("log-submit-20240115-100000-42-ingest-form-alpha-2024-01-15.json"),
            Body=json.dumps(event_data_1).encode(),
        )
        s3_client.put_object(
            Bucket=bucket,
            Key=("log-pass-qc-20240116-100000-42-ingest-form-alpha-2024-01-16.json"),
            Body=json.dumps(event_data_2).encode(),
        )

        # Set timestamp filter - events are no longer filtered by timestamp
        filter_timestamp = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        retriever = S3EventRetriever(bucket, since_timestamp=filter_timestamp)
        valid_events, validation_errors = retriever.retrieve_and_validate_events()

        # Both events should be returned (no per-event timestamp filter)
        assert len(valid_events) == 2
        assert len(validation_errors) == 0
        actions = {event.action for event in valid_events}
        assert "submit" in actions
        assert "pass-qc" in actions

    def test_retrieve_and_validate_events_with_retrieval_errors(
        self, s3_client, setup_s3_environment
    ):
        """Test handling S3 retrieval errors during event processing."""
        bucket = "test-bucket-validate-retrieval-errors"

        # Create bucket
        s3_client.create_bucket(Bucket=bucket)

        # Create valid event data
        valid_event_data = {
            "action": "submit",
            "study": "adrc",
            "pipeline_adcid": 123,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "test_gear",
            "ptid": "ABC123",
            "visit_date": "2024-01-15",
            "datatype": "form",
            "module": "UDS",
            "timestamp": "2024-01-15T10:00:00Z",
        }

        # Upload one valid file
        s3_client.put_object(
            Bucket=bucket,
            Key=("log-submit-20240115-100000-42-ingest-form-alpha-2024-01-15.json"),
            Body=json.dumps(valid_event_data).encode(),
        )

        # Create retriever that will try to access a non-existent file
        # We'll simulate this by manually adding a non-existent key to the list
        retriever = S3EventRetriever(bucket)

        # Patch list_event_files to return both existing and non-existing files
        with patch.object(retriever, "list_event_files") as mock_list:
            mock_list.return_value = [
                ("log-submit-20240115-100000-42-ingest-form-alpha-2024-01-15.json"),
                ("inaccessible-20240115-100000-42-ingest-form-alpha-2024-01-15.json"),
            ]

            valid_events, validation_errors = retriever.retrieve_and_validate_events()

        assert len(valid_events) == 1
        assert len(validation_errors) == 1
        assert valid_events[0].action == "submit"
        assert validation_errors[0]["source_key"] == (
            "inaccessible-20240115-100000-42-ingest-form-alpha-2024-01-15.json"
        )
        assert "S3 error" in str(validation_errors[0]["errors"])

    def test_retrieve_and_validate_events_empty_bucket(
        self, s3_client, setup_s3_environment
    ):
        """Test handling empty bucket scenario."""
        bucket = "test-bucket-validate-empty"

        # Create empty bucket
        s3_client.create_bucket(Bucket=bucket)

        retriever = S3EventRetriever(bucket)
        valid_events, validation_errors = retriever.retrieve_and_validate_events()

        assert len(valid_events) == 0
        assert len(validation_errors) == 0

    def test_retrieve_and_validate_events_list_files_error(self, setup_s3_environment):
        """Test handling errors during file listing."""
        # Use non-existent bucket to trigger S3 error
        retriever = S3EventRetriever("non-existent-bucket-validate")

        with pytest.raises(ClientError):
            retriever.retrieve_and_validate_events()


class TestS3EventRetrieverErrorHandling:
    """Test error handling scenarios."""

    def test_s3_credentials_error(self, setup_s3_environment):
        """Test handling missing AWS credentials."""
        # Clear AWS credentials to simulate NoCredentialsError
        # This is tricky with moto.server since we need credentials set
        # We'll test this by using an invalid endpoint instead
        original_endpoint = os.environ.get("AWS_ENDPOINT_URL")
        os.environ["AWS_ENDPOINT_URL"] = "http://invalid-endpoint:9999"

        try:
            retriever = S3EventRetriever("test-bucket-credentials-error")
            # This should fail with a connection error when trying to connect
            # to the invalid endpoint
            with pytest.raises((ClientError, ConnectionError, OSError, Exception)):
                retriever.list_event_files()
        finally:
            # Restore original endpoint
            if original_endpoint is not None:
                os.environ["AWS_ENDPOINT_URL"] = original_endpoint
            else:
                os.environ.pop("AWS_ENDPOINT_URL", None)

    def test_json_decode_error_handling(self, s3_client, setup_s3_environment):
        """Test handling JSON decode errors."""
        bucket = "test-bucket-json-decode-error"
        key = JSON_ERROR_LOG  # Valid pattern but invalid JSON

        # Create bucket
        s3_client.create_bucket(Bucket=bucket)

        # Upload malformed JSON file
        s3_client.put_object(Bucket=bucket, Key=key, Body=b"{ invalid json content")

        retriever = S3EventRetriever(bucket)
        valid_events, validation_errors = retriever.retrieve_and_validate_events()

        assert len(valid_events) == 0
        assert len(validation_errors) == 1
        assert validation_errors[0]["source_key"] == key
        assert "JSON decode error" in str(validation_errors[0]["errors"])


class TestS3EventRetrieverPropertyTests:
    """Property-based tests for S3EventRetriever."""

    # Feature: event-log-scraper, Property 1: File pattern matching correctness
    @given(
        bucket_name=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=3, max_size=20
        ).filter(lambda x: x[0].isalnum() and x[-1].isalnum() and "--" not in x),
        prefix=st.one_of(
            st.just(""),  # No prefix
            st.text(
                alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",
                min_size=1,
                max_size=10,
            ).map(lambda x: x + "/"),  # Simple prefix with trailing slash
        ),
        s3_keys=st.lists(
            st.one_of(
                # Valid log files - visit_date pattern
                st.builds(
                    lambda action: (
                        f"log-{action}-20240115-100000-42-test-ABC123-2024-01-15.json"
                    ),
                    action=st.sampled_from(
                        ["submit", "pass-qc", "not-pass-qc", "delete"]
                    ),
                ),
                # Invalid files - simple non-matching patterns
                st.just("other-file.json"),  # Wrong extension
                st.just("data-file.json"),  # Wrong prefix
            ),
            min_size=0,
            max_size=3,  # Reduced for speed
        ),
    )
    @settings(
        max_examples=3,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )  # Reduced examples for speed
    def test_file_pattern_matching_correctness(
        self, bucket_name, prefix, s3_keys, s3_client, setup_s3_environment
    ):
        """Property test: File pattern matching should only return files
        matching the configured pattern.

        This test validates Requirements 1.1: the list_event_files
        function should return only files matching the configured
        pattern.
        """
        # Create a pattern that matches both short and full formats for testing
        test_pattern = re.compile(
            r"^.*log-(submit|pass-qc|not-pass-qc|delete)"
            r"-(\d{8}\.json|\d{8}-\d{6}-\d+-[\w\-]+"
            r"-[\w]+-\d{4}-\d{2}-\d{2}\.json)$"
        )

        # Create retriever with test pattern
        retriever = S3EventRetriever(bucket_name, prefix, file_pattern=test_pattern)

        # Skip test if method not implemented yet
        try:
            # Try to call the method to see if it's implemented
            retriever.list_event_files()
        except NotImplementedError:
            pytest.skip("list_event_files not implemented yet")
        except Exception:
            # If it's implemented but fails for other reasons, we can continue
            # with the test
            pass

        # Create bucket and upload files
        s3_client.create_bucket(Bucket=bucket_name)

        # Add prefix to keys if specified
        prefixed_keys = [f"{prefix}{key}" if prefix else key for key in s3_keys]

        # Upload all files to S3
        for key in prefixed_keys:
            s3_client.put_object(Bucket=bucket_name, Key=key, Body=b"test content")

        # Get filtered files
        result_files = retriever.list_event_files()

        # Use the same test pattern for validation
        # Verify all returned files match the test pattern
        for file_key in result_files:
            assert test_pattern.match(file_key), (
                f"File {file_key} does not match expected pattern"
            )

        # Verify no valid files were excluded
        expected_files = [key for key in prefixed_keys if test_pattern.match(key)]
        assert set(result_files) == set(expected_files), (
            f"Expected files {expected_files} but got {result_files}"
        )

    # Feature: event-log-scraper, Property 2: JSON retrieval completeness
    @given(
        bucket_name=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=3, max_size=20
        ).filter(lambda x: x[0].isalnum() and x[-1].isalnum() and "--" not in x),
        s3_key=st.just("test-file.json"),  # Simplified for speed
        event_data=st.just(
            {  # Simplified for speed
                "action": "submit",
                "study": "adrc",
                "pipeline_adcid": 123,
                "project_label": "test_project",
                "center_label": "test_center",
                "gear_name": "test_gear",
                "ptid": "ABC123",
                "visit_date": "2024-01-15",
                "datatype": "form",
                "module": "UDS",
                "timestamp": "2024-01-15T10:00:00Z",
            }
        ),
    )
    @settings(
        max_examples=3,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )  # Reduced examples for speed
    def test_json_retrieval_completeness(
        self, bucket_name, s3_key, event_data, s3_client, setup_s3_environment
    ):
        """Property test: For any valid VisitEvent JSON file in S3, the
        retrieve_event function should successfully parse and return a valid
        VisitEvent object.

        This test validates Requirements 1.2: WHEN the Lambda retrieves
        a file from S3 THEN the Lambda SHALL read the complete file
        content as JSON and validate it as a VisitEvent.
        """
        # Create retriever
        retriever = S3EventRetriever(bucket_name)

        # Create bucket and upload file
        s3_client.create_bucket(Bucket=bucket_name)

        # Convert event data to bytes as S3 would return it
        json_bytes = json.dumps(event_data, separators=(",", ":")).encode("utf-8")
        s3_client.put_object(Bucket=bucket_name, Key=s3_key, Body=json_bytes)

        # Retrieve event and verify it's a VisitEvent object
        result = retriever.retrieve_event(s3_key)

        # Verify the result is a VisitEvent object
        assert isinstance(result, VisitEvent), (
            f"Expected VisitEvent object, got {type(result)}"
        )

        # Verify the data matches the original
        assert result.action == event_data["action"]
        assert result.pipeline_adcid == event_data["pipeline_adcid"]
        assert result.ptid == event_data["ptid"]

    # Feature: event-log-scraper, Property 4: Error resilience in retrieval
    @given(
        bucket_name=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=3, max_size=20
        ).filter(lambda x: x[0].isalnum() and x[-1].isalnum() and "--" not in x),
        file_scenarios=st.lists(
            st.one_of(
                # Successful file scenario (simplified)
                st.just(
                    {
                        "type": "success",
                        "key": "log-submit-20240115.json",
                        "event_data": {
                            "action": "submit",
                            "study": "adrc",
                            "pipeline_adcid": 123,
                            "project_label": "test_project",
                            "center_label": "test_center",
                            "gear_name": "test_gear",
                            "ptid": "ABC123",
                            "visit_date": "2024-01-15",
                            "datatype": "form",
                            "module": "UDS",
                            "timestamp": "2024-01-15T10:00:00Z",
                        },
                    }
                ),
                # S3 access error scenario (simplified)
                st.just(
                    {
                        "type": "s3_error",
                        "key": "log-pass-qc-20240116.json",
                        "error_code": "NoSuchKey",
                    }
                ),
                # JSON decode error scenario (simplified)
                st.just(
                    {
                        "type": "json_error",
                        "key": "log-delete-20240117.json",
                        "invalid_content": "invalid json content",
                    }
                ),
            ),
            min_size=1,
            max_size=3,  # Reduced for speed
        ),
    )
    @settings(max_examples=3, deadline=None)  # Reduced examples for speed
    def test_error_resilience_in_retrieval(self, bucket_name, file_scenarios):
        """Property test: For any collection of S3 files where some fail to
        retrieve, the system should continue processing remaining files and
        return all successfully retrieved events.

        This test validates Requirements 1.3 and 1.4:
        - 1.3: WHEN the Lambda encounters an S3 access error THEN the Lambda
               SHALL log the error with the file path and continue processing
               remaining files
        - 1.4: WHEN the Lambda completes file retrieval THEN the Lambda SHALL
               return a collection of all successfully retrieved event objects
        """
        # Create retriever
        retriever = S3EventRetriever(bucket_name)

        # Skip test if method not implemented yet
        try:
            # Try to call the method to see if it's implemented
            retriever.retrieve_and_validate_events()
        except NotImplementedError:
            pytest.skip("retrieve_and_validate_events not implemented yet")
        except Exception:
            # If it's implemented but fails for other reasons, we can continue
            # with the test
            pass

        # Count expected successful events
        expected_successful_events = [
            scenario for scenario in file_scenarios if scenario["type"] == "success"
        ]
        expected_error_count = len(file_scenarios) - len(expected_successful_events)

        # If we get here, the method is implemented, so we can run the full test
        with (
            patch(
                "checkpoint_lambda.s3_retriever.S3EventRetriever.list_event_files"
            ) as mock_list,
            patch(
                "checkpoint_lambda.s3_retriever.S3EventRetriever.retrieve_event"
            ) as mock_retrieve,
        ):
            # Setup file list
            file_keys = [scenario["key"] for scenario in file_scenarios]
            mock_list.return_value = file_keys

            # Setup retrieve_event to simulate different scenarios
            def retrieve_side_effect(key):
                # Find the scenario for this key
                scenario = next(s for s in file_scenarios if s["key"] == key)

                if scenario["type"] == "success":
                    # Return a VisitEvent object instead of raw dict
                    return VisitEvent.model_validate(scenario["event_data"])
                elif scenario["type"] == "s3_error":
                    raise ClientError(
                        {
                            "Error": {
                                "Code": scenario["error_code"],
                                "Message": f"S3 error for {key}",
                            }
                        },
                        "GetObject",
                    )
                elif scenario["type"] == "json_error":
                    raise json.JSONDecodeError("Invalid JSON", "doc", 0)
                else:
                    raise ValueError(f"Unknown scenario type: {scenario['type']}")

            mock_retrieve.side_effect = retrieve_side_effect

            # Execute the method under test
            valid_events, validation_errors = retriever.retrieve_and_validate_events()

            # Verify error resilience: system should continue processing
            # despite errors and return all successfully retrieved events

            # 1. Verify all successful events were processed and returned
            assert len(valid_events) == len(expected_successful_events), (
                f"Expected {len(expected_successful_events)} valid events, "
                f"but got {len(valid_events)}"
            )

            # 2. Verify all failed events were recorded as errors
            assert len(validation_errors) == expected_error_count, (
                f"Expected {expected_error_count} validation errors, "
                f"but got {len(validation_errors)}"
            )

            # 3. Verify that each error contains the expected information
            error_keys = {error["source_key"] for error in validation_errors}
            expected_error_keys = {
                scenario["key"]
                for scenario in file_scenarios
                if scenario["type"] != "success"
            }
            assert error_keys == expected_error_keys, (
                f"Expected error keys {expected_error_keys}, but got {error_keys}"
            )

            # 4. Verify that each error has the required structure
            for error in validation_errors:
                assert "source_key" in error, "Validation error missing 'source_key'"
                assert "errors" in error, "Validation error missing 'errors'"
                assert error["source_key"] in file_keys, (
                    f"Error source_key {error['source_key']} not in original file list"
                )

            # 5. Verify all valid events are VisitEvent objects
            for event in valid_events:
                assert isinstance(event, VisitEvent), (
                    f"Expected VisitEvent object, got {type(event)}"
                )

            # 6. Verify that the method was called with all files
            mock_list.assert_called_once()
            assert mock_retrieve.call_count == len(file_scenarios), (
                f"Expected {len(file_scenarios)} retrieve calls, "
                f"but got {mock_retrieve.call_count}"
            )


class TestFilterRemoval:
    """Tests verifying timestamp filter removal from S3EventRetriever.

    Validates Requirements:
    - 4.1: S3_Event_Retriever returns all valid Visit_Events without
            filtering by event timestamp
    - 4.2: Events with timestamps older than since_timestamp are
            still included
    - 4.3: S3_Event_Retriever removes should_process_event method
    - 5.1: S3 objects with LastModified < since_timestamp are skipped
    - 5.2: S3 LastModified used only as performance optimization
    - 5.3: S3 objects with LastModified >= since_timestamp are
            downloaded regardless of event timestamps
    - 5.4: When since_timestamp is None, all objects are downloaded
    """

    # Constants for test event keys (avoid E501 line length)
    SUBMIT_KEY = "log-submit-20240115-100000-42-ingest-form-alpha-2024-01-15.json"
    PASSQC_KEY = "log-pass-qc-20240120-100000-42-ingest-form-alpha-2024-01-20.json"
    OLD_EVENT_KEY = "log-submit-20240101-100000-42-ingest-form-alpha-2024-01-01.json"

    def _make_event_data(
        self,
        action: str = "submit",
        timestamp: str = "2024-01-15T10:00:00Z",
        ptid: str = "ABC123",
        visit_date: str = "2024-01-15",
    ) -> dict:
        """Create valid event data for testing."""
        return {
            "action": action,
            "study": "adrc",
            "pipeline_adcid": 42,
            "project_label": "test_project",
            "center_label": "test_center",
            "gear_name": "ingest",
            "ptid": ptid,
            "visit_date": visit_date,
            "datatype": "form",
            "module": "UDS",
            "timestamp": timestamp,
        }

    def test_should_process_event_method_removed(self):
        """Verify should_process_event no longer exists.

        Validates Requirement 4.3.
        """
        retriever = S3EventRetriever("any-bucket")
        assert not hasattr(retriever, "should_process_event")

    def test_fetch_and_validate_returns_visit_event_directly(
        self, s3_client, setup_s3_environment
    ):
        """Verify _fetch_and_validate returns VisitEvent directly.

        There is no "skipped" result path; valid events are always
        returned as VisitEvent objects.

        Validates Requirements 4.1, 4.2.
        """
        bucket = "test-bucket-fetch-validate-direct"
        s3_client.create_bucket(Bucket=bucket)

        event_data = self._make_event_data(timestamp="2024-01-10T10:00:00Z")
        s3_client.put_object(
            Bucket=bucket,
            Key=self.SUBMIT_KEY,
            Body=json.dumps(event_data).encode(),
        )

        # Use a since_timestamp AFTER the event timestamp
        since = datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
        retriever = S3EventRetriever(bucket, since_timestamp=since)

        result = retriever._fetch_and_validate(self.SUBMIT_KEY)  # noqa: SLF001

        # Must be VisitEvent, never a "skipped" dict
        assert isinstance(result, VisitEvent)
        assert result.action == "submit"
        assert result.ptid == "ABC123"

    def test_s3_lastmodified_prefilter_skips_old_files(
        self, s3_client, setup_s3_environment
    ):
        """Verify list_event_files skips files with LastModified earlier than
        since_timestamp.

        Validates Requirement 5.1.
        """
        bucket = "test-bucket-prefilter-old"
        s3_client.create_bucket(Bucket=bucket)

        # Upload a file (LastModified will be "now" from moto)
        s3_client.put_object(
            Bucket=bucket,
            Key=self.SUBMIT_KEY,
            Body=b"content",
        )

        # Set since_timestamp far in the future so file is "old"
        future_ts = datetime(2099, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        retriever = S3EventRetriever(bucket, since_timestamp=future_ts)
        files = retriever.list_event_files()

        assert files == []

    def test_s3_lastmodified_prefilter_includes_recent_files(
        self, s3_client, setup_s3_environment
    ):
        """Verify list_event_files includes files with LastModified at or after
        since_timestamp.

        Validates Requirements 5.2, 5.3.
        """
        bucket = "test-bucket-prefilter-recent"
        s3_client.create_bucket(Bucket=bucket)

        # Upload file (LastModified = now from moto, which is recent)
        s3_client.put_object(
            Bucket=bucket,
            Key=self.SUBMIT_KEY,
            Body=b"content",
        )

        # Set since_timestamp in the past so file is "recent"
        past_ts = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        retriever = S3EventRetriever(bucket, since_timestamp=past_ts)
        files = retriever.list_event_files()

        assert self.SUBMIT_KEY in files

    def test_s3_lastmodified_prefilter_disabled_when_no_timestamp(
        self, s3_client, setup_s3_environment
    ):
        """Verify all files are listed when since_timestamp is None.

        Validates Requirement 5.4.
        """
        bucket = "test-bucket-prefilter-none"
        s3_client.create_bucket(Bucket=bucket)

        # Upload multiple files
        s3_client.put_object(
            Bucket=bucket,
            Key=self.SUBMIT_KEY,
            Body=b"content",
        )
        s3_client.put_object(
            Bucket=bucket,
            Key=self.PASSQC_KEY,
            Body=b"content",
        )

        # No since_timestamp - all files should be returned
        retriever = S3EventRetriever(bucket, since_timestamp=None)
        files = retriever.list_event_files()

        assert len(files) == 2
        assert self.SUBMIT_KEY in files
        assert self.PASSQC_KEY in files

    def test_events_returned_regardless_of_event_timestamp(
        self, s3_client, setup_s3_environment
    ):
        """Verify events with old timestamps are still returned.

        The event timestamp inside the file does NOT affect whether
        the event is returned. Only S3 LastModified is used as a
        pre-filter on file listing, not on event content.

        Validates Requirements 4.1, 4.2, 5.2.
        """
        bucket = "test-bucket-event-ts-irrelevant"
        s3_client.create_bucket(Bucket=bucket)

        # Event with a very old timestamp inside it
        old_event = self._make_event_data(
            timestamp="2020-06-01T10:00:00Z",
            visit_date="2020-06-01",
        )
        # Event with a recent timestamp
        new_event = self._make_event_data(
            action="pass-qc",
            timestamp="2024-01-20T10:00:00Z",
            visit_date="2024-01-20",
        )

        s3_client.put_object(
            Bucket=bucket,
            Key=self.SUBMIT_KEY,
            Body=json.dumps(old_event).encode(),
        )
        s3_client.put_object(
            Bucket=bucket,
            Key=self.PASSQC_KEY,
            Body=json.dumps(new_event).encode(),
        )

        # since_timestamp is between the two event timestamps
        # but both files have recent LastModified (just uploaded)
        since = datetime(2024, 1, 10, 0, 0, 0, tzinfo=timezone.utc)
        retriever = S3EventRetriever(bucket, since_timestamp=since)
        events, errors = retriever.retrieve_and_validate_events()

        # Both events returned regardless of event timestamp
        assert len(events) == 2
        assert len(errors) == 0
        actions = {e.action for e in events}
        assert "submit" in actions
        assert "pass-qc" in actions
