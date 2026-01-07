"""Unit tests for S3EventRetriever component.

This module contains unit tests for the S3EventRetriever class, testing
S3 operations, JSON retrieval, timestamp filtering, event validation,
and error handling scenarios.
"""

import json
import re
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError
from checkpoint_lambda.models import VisitEvent
from checkpoint_lambda.s3_retriever import S3EventRetriever
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError


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

    @patch("checkpoint_lambda.s3_retriever.boto3.client")
    def test_list_event_files_empty_bucket(self, mock_boto3_client):
        """Test listing files from empty bucket."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {}

        retriever = S3EventRetriever("test-bucket")
        files = retriever.list_event_files()

        assert files == []
        mock_s3.list_objects_v2.assert_called_once_with(Bucket="test-bucket", Prefix="")

    @patch("checkpoint_lambda.s3_retriever.boto3.client")
    def test_list_event_files_with_matching_pattern(self, mock_boto3_client):
        """Test listing files that match the log pattern."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "log-submit-20240115.json"},  # Short format
                {"Key": "log-pass-qc-20240116.json"},  # Short format
                {"Key": "log-not-pass-qc-20240117.json"},  # Short format
                {"Key": "log-delete-20240118.json"},  # Short format
                {
                    "Key": (
                        "log-submit-20240115-100000-42-ingest-form-alpha-110001-01.json"
                    )
                },  # Full format
                {
                    "Key": (
                        "log-pass-qc-20240115-102000-42-ingest-form-alpha-110001-01.json"
                    )
                },  # Full format
                {
                    "Key": (
                        "log-not-pass-qc-20240116-143000-43-ingest-dicom-beta-220002-02.json"
                    )
                },  # Full format
                {"Key": "other-file.json"},  # Should be filtered out
                {"Key": "log-invalid-action-20240119.json"},  # Should be filtered out
            ]
        }

        # Create a pattern that matches both short and full formats for testing
        test_pattern = re.compile(
            r"^.*log-(submit|pass-qc|not-pass-qc|delete)-(\d{8}\.json|\d{8}-\d{6}-\d+-[\w\-]+-[\w]+-[\w]+\.json)$"
        )
        retriever = S3EventRetriever("test-bucket", file_pattern=test_pattern)
        files = retriever.list_event_files()

        expected_files = [
            "log-submit-20240115.json",
            "log-pass-qc-20240116.json",
            "log-not-pass-qc-20240117.json",
            "log-delete-20240118.json",
            "log-submit-20240115-100000-42-ingest-form-alpha-110001-01.json",
            "log-pass-qc-20240115-102000-42-ingest-form-alpha-110001-01.json",
            "log-not-pass-qc-20240116-143000-43-ingest-dicom-beta-220002-02.json",
        ]
        assert files == expected_files

    @patch("checkpoint_lambda.s3_retriever.boto3.client")
    def test_list_event_files_with_prefix(self, mock_boto3_client):
        """Test listing files with S3 prefix."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "logs/log-submit-20240115.json"},  # Short format
                {
                    "Key": (
                        "logs/log-submit-20240115-100000-42-ingest-form-alpha-110001-01.json"
                    )
                },  # Full format
            ]
        }

        # Create a pattern that matches both short and full formats for testing
        test_pattern = re.compile(
            r"^.*log-(submit|pass-qc|not-pass-qc|delete)-(\d{8}\.json|\d{8}-\d{6}-\d+-[\w\-]+-[\w]+-[\w]+\.json)$"
        )
        retriever = S3EventRetriever("test-bucket", "logs/", file_pattern=test_pattern)
        files = retriever.list_event_files()

        assert files == [
            "logs/log-submit-20240115.json",
            "logs/log-submit-20240115-100000-42-ingest-form-alpha-110001-01.json",
        ]
        mock_s3.list_objects_v2.assert_called_once_with(
            Bucket="test-bucket", Prefix="logs/"
        )

    @patch("checkpoint_lambda.s3_retriever.boto3.client")
    def test_list_event_files_default_pattern(self, mock_boto3_client):
        """Test listing files with default pattern (full format only)."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": "log-submit-20240115.json"
                },  # Short format - should be filtered out
                {
                    "Key": (
                        "log-submit-20240115-100000-42-ingest-form-alpha-110001-01.json"
                    )
                },  # Full format - should be included
                {
                    "Key": (
                        "log-pass-qc-20240115-102000-42-ingest-form-alpha-110001-01.json"
                    )
                },  # Full format - should be included
                {"Key": "other-file.json"},  # Should be filtered out
            ]
        }

        # Use default pattern (full format only)
        retriever = S3EventRetriever("test-bucket")
        files = retriever.list_event_files()

        # Only full format files should be returned
        expected_files = [
            "log-submit-20240115-100000-42-ingest-form-alpha-110001-01.json",
            "log-pass-qc-20240115-102000-42-ingest-form-alpha-110001-01.json",
        ]
        assert files == expected_files

    @patch("checkpoint_lambda.s3_retriever.boto3.client")
    def test_list_event_files_s3_error(self, mock_boto3_client):
        """Test handling S3 access errors during file listing."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.list_objects_v2.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "ListObjectsV2",
        )

        retriever = S3EventRetriever("test-bucket")

        with pytest.raises(ClientError):
            retriever.list_event_files()


class TestRetrieveEvent:
    """Test retrieve_event method."""

    @patch("checkpoint_lambda.s3_retriever.boto3.client")
    def test_retrieve_event_valid_json(self, mock_boto3_client):
        """Test retrieving valid JSON event from S3."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

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

        mock_s3.get_object.return_value = {
            "Body": Mock(read=Mock(return_value=json.dumps(event_data).encode()))
        }

        retriever = S3EventRetriever("test-bucket")
        result = retriever.retrieve_event("log-submit-20240115.json")

        # Should return a VisitEvent object, not a dict
        assert isinstance(result, VisitEvent)
        assert result.action == "submit"
        assert result.ptid == "ABC123"
        assert result.pipeline_adcid == 123
        mock_s3.get_object.assert_called_once_with(
            Bucket="test-bucket", Key="log-submit-20240115.json"
        )

    @patch("checkpoint_lambda.s3_retriever.boto3.client")
    def test_retrieve_event_invalid_json(self, mock_boto3_client):
        """Test retrieving invalid JSON from S3."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.get_object.return_value = {
            "Body": Mock(read=Mock(return_value=b"invalid json content"))
        }

        retriever = S3EventRetriever("test-bucket")

        with pytest.raises(json.JSONDecodeError):
            retriever.retrieve_event("invalid-file.json")

    @patch("checkpoint_lambda.s3_retriever.boto3.client")
    def test_retrieve_event_invalid_event_data(self, mock_boto3_client):
        """Test retrieving JSON with invalid event data."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        # Valid JSON but invalid event data
        invalid_event_data = {
            "action": "invalid-action",  # Invalid action
            "pipeline_adcid": "not-a-number",  # Invalid type
            # Missing required fields
        }

        mock_s3.get_object.return_value = {
            "Body": Mock(
                read=Mock(return_value=json.dumps(invalid_event_data).encode())
            )
        }

        retriever = S3EventRetriever("test-bucket")

        with pytest.raises(ValidationError):
            retriever.retrieve_event("invalid-event.json")

    @patch("checkpoint_lambda.s3_retriever.boto3.client")
    def test_retrieve_event_s3_error(self, mock_boto3_client):
        """Test handling S3 errors during event retrieval."""
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Key not found"}}, "GetObject"
        )

        retriever = S3EventRetriever("test-bucket")

        with pytest.raises(ClientError):
            retriever.retrieve_event("nonexistent-file.json")


class TestShouldProcessEvent:
    """Test should_process_event method."""

    def test_should_process_event_no_timestamp_filter(self):
        """Test processing when no timestamp filter is set."""
        retriever = S3EventRetriever("test-bucket")

        event = VisitEvent(
            action="submit",
            study="adrc",
            pipeline_adcid=123,
            project_label="test_project",
            center_label="test_center",
            gear_name="test_gear",
            ptid="ABC123",
            visit_date="2024-01-15",
            datatype="form",
            module="UDS",
            timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )

        assert retriever.should_process_event(event) is True

    def test_should_process_event_newer_than_filter(self):
        """Test processing event newer than filter timestamp."""
        filter_timestamp = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
        retriever = S3EventRetriever("test-bucket", since_timestamp=filter_timestamp)

        event = VisitEvent(
            action="submit",
            study="adrc",
            pipeline_adcid=123,
            project_label="test_project",
            center_label="test_center",
            gear_name="test_gear",
            ptid="ABC123",
            visit_date="2024-01-15",
            datatype="form",
            module="UDS",
            timestamp=datetime(
                2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc
            ),  # 1 hour later
        )

        assert retriever.should_process_event(event) is True

    def test_should_process_event_older_than_filter(self):
        """Test skipping event older than filter timestamp."""
        filter_timestamp = datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc)
        retriever = S3EventRetriever("test-bucket", since_timestamp=filter_timestamp)

        event = VisitEvent(
            action="submit",
            study="adrc",
            pipeline_adcid=123,
            project_label="test_project",
            center_label="test_center",
            gear_name="test_gear",
            ptid="ABC123",
            visit_date="2024-01-15",
            datatype="form",
            module="UDS",
            timestamp=datetime(
                2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc
            ),  # 1 hour earlier
        )

        assert retriever.should_process_event(event) is False

    def test_should_process_event_equal_to_filter(self):
        """Test skipping event equal to filter timestamp."""
        filter_timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        retriever = S3EventRetriever("test-bucket", since_timestamp=filter_timestamp)

        event = VisitEvent(
            action="submit",
            study="adrc",
            pipeline_adcid=123,
            project_label="test_project",
            center_label="test_center",
            gear_name="test_gear",
            ptid="ABC123",
            visit_date="2024-01-15",
            datatype="form",
            module="UDS",
            timestamp=datetime(
                2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc
            ),  # Exactly equal
        )

        assert retriever.should_process_event(event) is False


class TestRetrieveAndValidateEvents:
    """Test retrieve_and_validate_events method."""

    @patch("checkpoint_lambda.s3_retriever.S3EventRetriever.list_event_files")
    @patch("checkpoint_lambda.s3_retriever.S3EventRetriever.retrieve_event")
    @patch("checkpoint_lambda.s3_retriever.S3EventRetriever.should_process_event")
    def test_retrieve_and_validate_events_success(
        self, mock_should_process, mock_retrieve, mock_list
    ):
        """Test successful retrieval and validation of events."""
        # Setup mocks
        mock_list.return_value = [
            "log-submit-20240115.json",
            "log-pass-qc-20240116.json",
        ]

        # Create VisitEvent objects for mocking
        event_1 = VisitEvent(
            action="submit",
            study="adrc",
            pipeline_adcid=123,
            project_label="test_project",
            center_label="test_center",
            gear_name="test_gear",
            ptid="ABC123",
            visit_date="2024-01-15",
            datatype="form",
            module="UDS",
            timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )

        event_2 = VisitEvent(
            action="pass-qc",
            study="adrc",
            pipeline_adcid=123,
            project_label="test_project",
            center_label="test_center",
            gear_name="test_gear",
            ptid="ABC123",
            visit_date="2024-01-16",
            datatype="form",
            module="UDS",
            timestamp=datetime(2024, 1, 16, 10, 0, 0, tzinfo=timezone.utc),
        )

        mock_retrieve.side_effect = [event_1, event_2]
        mock_should_process.return_value = True

        retriever = S3EventRetriever("test-bucket")
        valid_events, validation_errors = retriever.retrieve_and_validate_events()

        assert len(valid_events) == 2
        assert len(validation_errors) == 0
        assert all(isinstance(event, VisitEvent) for event in valid_events)
        assert valid_events[0].action == "submit"
        assert valid_events[1].action == "pass-qc"

    @patch("checkpoint_lambda.s3_retriever.S3EventRetriever.list_event_files")
    @patch("checkpoint_lambda.s3_retriever.S3EventRetriever.retrieve_event")
    @patch("checkpoint_lambda.s3_retriever.S3EventRetriever.should_process_event")
    def test_retrieve_and_validate_events_with_validation_errors(
        self, mock_should_process, mock_retrieve, mock_list
    ):
        """Test handling validation errors during event processing."""
        mock_list.return_value = ["log-submit-20240115.json", "invalid-event.json"]

        # Create valid VisitEvent object for first file
        valid_event = VisitEvent(
            action="submit",
            study="adrc",
            pipeline_adcid=123,
            project_label="test_project",
            center_label="test_center",
            gear_name="test_gear",
            ptid="ABC123",
            visit_date="2024-01-15",
            datatype="form",
            module="UDS",
            timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )

        # Mock retrieve_event to return valid event for first file,
        # raise ValidationError for second
        validation_error = None
        try:
            # Create a ValidationError by trying to validate invalid data
            VisitEvent.model_validate(
                {"action": "invalid-action", "pipeline_adcid": "not-a-number"}
            )
        except ValidationError as e:
            validation_error = e

        mock_retrieve.side_effect = [valid_event, validation_error]
        mock_should_process.return_value = True

        retriever = S3EventRetriever("test-bucket")
        valid_events, validation_errors = retriever.retrieve_and_validate_events()

        assert len(valid_events) == 1
        assert len(validation_errors) == 1
        assert valid_events[0].action == "submit"
        assert validation_errors[0]["source_key"] == "invalid-event.json"
        assert "errors" in validation_errors[0]

    @patch("checkpoint_lambda.s3_retriever.S3EventRetriever.list_event_files")
    @patch("checkpoint_lambda.s3_retriever.S3EventRetriever.retrieve_event")
    @patch("checkpoint_lambda.s3_retriever.S3EventRetriever.should_process_event")
    def test_retrieve_and_validate_events_with_timestamp_filtering(
        self, mock_should_process, mock_retrieve, mock_list
    ):
        """Test timestamp filtering during event processing."""
        mock_list.return_value = [
            "log-submit-20240115.json",
            "log-pass-qc-20240116.json",
        ]

        # Create VisitEvent objects for mocking
        event_1 = VisitEvent(
            action="submit",
            study="adrc",
            pipeline_adcid=123,
            project_label="test_project",
            center_label="test_center",
            gear_name="test_gear",
            ptid="ABC123",
            visit_date="2024-01-15",
            datatype="form",
            module="UDS",
            timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )

        event_2 = VisitEvent(
            action="pass-qc",
            study="adrc",
            pipeline_adcid=123,
            project_label="test_project",
            center_label="test_center",
            gear_name="test_gear",
            ptid="ABC123",
            visit_date="2024-01-16",
            datatype="form",
            module="UDS",
            timestamp=datetime(2024, 1, 16, 10, 0, 0, tzinfo=timezone.utc),
        )

        mock_retrieve.side_effect = [event_1, event_2]
        # Only the second event should be processed
        mock_should_process.side_effect = [False, True]

        retriever = S3EventRetriever("test-bucket")
        valid_events, validation_errors = retriever.retrieve_and_validate_events()

        assert len(valid_events) == 1
        assert len(validation_errors) == 0
        assert valid_events[0].action == "pass-qc"

    @patch("checkpoint_lambda.s3_retriever.S3EventRetriever.list_event_files")
    @patch("checkpoint_lambda.s3_retriever.S3EventRetriever.retrieve_event")
    def test_retrieve_and_validate_events_with_retrieval_errors(
        self, mock_retrieve, mock_list
    ):
        """Test handling S3 retrieval errors during event processing."""
        mock_list.return_value = ["log-submit-20240115.json", "inaccessible-file.json"]

        # Create valid VisitEvent object for first file
        valid_event = VisitEvent(
            action="submit",
            study="adrc",
            pipeline_adcid=123,
            project_label="test_project",
            center_label="test_center",
            gear_name="test_gear",
            ptid="ABC123",
            visit_date="2024-01-15",
            datatype="form",
            module="UDS",
            timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )

        mock_retrieve.side_effect = [
            valid_event,
            ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "Key not found"}},
                "GetObject",
            ),
        ]

        retriever = S3EventRetriever("test-bucket")
        valid_events, validation_errors = retriever.retrieve_and_validate_events()

        assert len(valid_events) == 1
        assert len(validation_errors) == 1
        assert valid_events[0].action == "submit"
        assert validation_errors[0]["source_key"] == "inaccessible-file.json"
        assert "S3 error" in str(validation_errors[0]["errors"])

    @patch("checkpoint_lambda.s3_retriever.S3EventRetriever.list_event_files")
    def test_retrieve_and_validate_events_empty_bucket(self, mock_list):
        """Test handling empty bucket scenario."""
        mock_list.return_value = []

        retriever = S3EventRetriever("test-bucket")
        valid_events, validation_errors = retriever.retrieve_and_validate_events()

        assert len(valid_events) == 0
        assert len(validation_errors) == 0

    @patch("checkpoint_lambda.s3_retriever.S3EventRetriever.list_event_files")
    def test_retrieve_and_validate_events_list_files_error(self, mock_list):
        """Test handling errors during file listing."""
        mock_list.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "ListObjectsV2",
        )

        retriever = S3EventRetriever("test-bucket")

        with pytest.raises(ClientError):
            retriever.retrieve_and_validate_events()


class TestS3EventRetrieverErrorHandling:
    """Test error handling scenarios."""

    @patch("checkpoint_lambda.s3_retriever.boto3.client")
    def test_s3_credentials_error(self, mock_boto3_client):
        """Test handling missing AWS credentials."""
        mock_boto3_client.side_effect = NoCredentialsError()

        retriever = S3EventRetriever("test-bucket")

        with pytest.raises(NoCredentialsError):
            retriever.list_event_files()

    @patch("checkpoint_lambda.s3_retriever.S3EventRetriever.retrieve_event")
    @patch("checkpoint_lambda.s3_retriever.S3EventRetriever.list_event_files")
    def test_json_decode_error_handling(self, mock_list, mock_retrieve):
        """Test handling JSON decode errors."""
        mock_list.return_value = ["malformed-file.json"]
        mock_retrieve.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)

        retriever = S3EventRetriever("test-bucket")
        valid_events, validation_errors = retriever.retrieve_and_validate_events()

        assert len(valid_events) == 0
        assert len(validation_errors) == 1
        assert validation_errors[0]["source_key"] == "malformed-file.json"
        assert "JSON decode error" in str(validation_errors[0]["errors"])


class TestS3EventRetrieverPropertyTests:
    """Property-based tests for S3EventRetriever."""

    # Feature: event-log-scraper, Property 1: File pattern matching correctness
    @given(
        bucket_name=st.from_regex(r"[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]"),
        prefix=st.one_of(
            st.just(""),  # No prefix
            st.from_regex(
                r"[a-zA-Z0-9_\-]{1,20}/"
            ),  # Simple prefix with trailing slash
        ),
        s3_keys=st.lists(
            st.one_of(
                # Valid log files - modern pattern
                st.builds(
                    lambda action,
                    year,
                    month,
                    day,
                    hour,
                    minute,
                    second,
                    adcid,
                    project,
                    ptid,
                    visitnum: (
                        f"log-{action}-{year:04d}{month:02d}{day:02d}-"
                        f"{hour:02d}{minute:02d}{second:02d}-{adcid}-"
                        f"{project}-{ptid}-{visitnum}.json"
                    ),
                    action=st.sampled_from(
                        ["submit", "pass-qc", "not-pass-qc", "delete"]
                    ),
                    year=st.integers(min_value=2020, max_value=2030),
                    month=st.integers(min_value=1, max_value=12),
                    day=st.integers(min_value=1, max_value=28),
                    hour=st.integers(min_value=0, max_value=23),
                    minute=st.integers(min_value=0, max_value=59),
                    second=st.integers(min_value=0, max_value=59),
                    adcid=st.integers(min_value=1, max_value=999),
                    project=st.from_regex(r"[a-zA-Z0-9_\-]{1,15}"),
                    ptid=st.from_regex(r"[a-zA-Z0-9]{1,10}"),
                    visitnum=st.from_regex(r"[0-9]{1,3}"),
                ),
                # Valid log files - legacy pattern
                st.builds(
                    lambda action,
                    year,
                    month,
                    day: f"log-{action}-{year:04d}{month:02d}{day:02d}.json",
                    action=st.sampled_from(
                        ["submit", "pass-qc", "not-pass-qc", "delete"]
                    ),
                    year=st.integers(min_value=2020, max_value=2030),
                    month=st.integers(min_value=1, max_value=12),
                    day=st.integers(min_value=1, max_value=28),
                ),
                # Invalid files - simple non-matching patterns
                st.from_regex(
                    r"[a-zA-Z0-9_\-]{1,30}\.(txt|csv|xml)"
                ),  # Wrong extension
                st.from_regex(r"data-[a-zA-Z0-9_\-]{1,20}\.json"),  # Wrong prefix
                st.builds(
                    lambda action, date: f"log-{action}-{date}.json",
                    action=st.from_regex(r"[a-z]{3,10}"),  # Invalid action
                    date=st.from_regex(r"[0-9]{6,10}"),  # Invalid date format
                ),
            ),
            min_size=0,
            max_size=5,  # Reduced for performance
        ),
    )
    @settings(max_examples=10, deadline=None)  # Disable deadline for performance
    def test_file_pattern_matching_correctness(self, bucket_name, prefix, s3_keys):
        """Property test: File pattern matching should only return files
        matching the configured pattern.

        This test validates Requirements 1.1: the list_event_files
        function should return only files matching the configured
        pattern.
        """
        # Create a pattern that matches both short and full formats for testing
        test_pattern = re.compile(
            r"^.*log-(submit|pass-qc|not-pass-qc|delete)-(\d{8}\.json|\d{8}-\d{6}-\d+-[\w\-]+-[\w]+-[\w]+\.json)$"
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

        # If we get here, the method is implemented, so we can run the full test
        with patch("checkpoint_lambda.s3_retriever.boto3.client") as mock_boto3_client:
            # Setup mock S3 client
            mock_s3 = Mock()
            mock_boto3_client.return_value = mock_s3

            # Add prefix to keys if specified
            prefixed_keys = [f"{prefix}{key}" if prefix else key for key in s3_keys]

            mock_s3.list_objects_v2.return_value = {
                "Contents": [{"Key": key} for key in prefixed_keys]
            }

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

            # Verify S3 was called with correct parameters
            mock_s3.list_objects_v2.assert_called_once_with(
                Bucket=bucket_name, Prefix=prefix
            )

    # Feature: event-log-scraper, Property 2: JSON retrieval completeness
    @given(
        bucket_name=st.from_regex(r"[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]"),
        s3_key=st.builds(
            lambda name: f"{name}.json", name=st.from_regex(r"[a-zA-Z0-9_\-]{1,20}")
        ),
        # Generate valid VisitEvent data instead of arbitrary JSON
        event_data=st.builds(
            lambda action, adcid: {
                "action": action,
                "study": "adrc",
                "pipeline_adcid": adcid,
                "project_label": "test_project",
                "center_label": "test_center",
                "gear_name": "test_gear",
                "ptid": "ABC123",  # Use fixed valid PTID
                "visit_date": "2024-01-15",
                "datatype": "form",
                "module": "UDS",
                "timestamp": "2024-01-15T10:00:00Z",
            },
            action=st.sampled_from(["submit", "pass-qc", "not-pass-qc", "delete"]),
            adcid=st.integers(min_value=1, max_value=999),
        ),
    )
    @settings(max_examples=10, deadline=None)  # Disable deadline for performance
    def test_json_retrieval_completeness(self, bucket_name, s3_key, event_data):
        """Property test: For any valid VisitEvent JSON file in S3, the
        retrieve_event function should successfully parse and return a valid
        VisitEvent object.

        This test validates Requirements 1.2: WHEN the Lambda retrieves
        a file from S3 THEN the Lambda SHALL read the complete file
        content as JSON and validate it as a VisitEvent.
        """
        # Create retriever
        retriever = S3EventRetriever(bucket_name)

        with patch("checkpoint_lambda.s3_retriever.boto3.client") as mock_boto3_client:
            # Setup mock S3 client
            mock_s3 = Mock()
            mock_boto3_client.return_value = mock_s3

            # Convert event data to bytes as S3 would return it
            json_bytes = json.dumps(event_data, separators=(",", ":")).encode("utf-8")
            mock_s3.get_object.return_value = {
                "Body": Mock(read=Mock(return_value=json_bytes))
            }

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

            # Verify S3 was called with correct parameters
            mock_s3.get_object.assert_called_once_with(Bucket=bucket_name, Key=s3_key)

    # Feature: event-log-scraper, Property 3: Timestamp filtering correctness
    @given(
        bucket_name=st.from_regex(r"[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]"),
        cutoff_timestamp=st.datetimes(
            min_value=datetime(2020, 1, 1),  # Naive datetime
            max_value=datetime(2030, 12, 31),  # Naive datetime
        ).map(
            lambda dt: dt.replace(tzinfo=timezone.utc)
        ),  # Add timezone after generation
        # Generate VisitEvent objects instead of raw dictionaries
        events=st.lists(
            st.builds(
                lambda action, offset_hours: VisitEvent(
                    action=action,
                    study="adrc",
                    pipeline_adcid=123,
                    project_label="test_project",
                    center_label="test_center",
                    gear_name="test_gear",
                    ptid="ABC123",
                    visit_date="2024-01-15",
                    datatype="form",
                    module="UDS",
                    timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
                    + timedelta(hours=offset_hours),
                ),
                action=st.sampled_from(["submit", "pass-qc", "not-pass-qc", "delete"]),
                offset_hours=st.integers(min_value=-24, max_value=24),
            ),
            min_size=0,
            max_size=5,  # Reduced for performance
        ),
    )
    @settings(max_examples=15, deadline=None)  # Disable deadline for performance
    def test_timestamp_filtering_correctness(
        self, bucket_name, cutoff_timestamp, events
    ):
        """Property test: For any cutoff timestamp and collection of events,
        the retrieval system should process only events with timestamp strictly
        greater than the cutoff timestamp.

        This test validates Requirements 1.1 and 7.4: the system should
        filter events by timestamp to support incremental processing and
        preserve event ordering based on timestamp values.
        """
        # Create retriever with timestamp filter
        retriever = S3EventRetriever(bucket_name, since_timestamp=cutoff_timestamp)

        # Test each event individually
        for event in events:
            # Determine expected result
            should_process_expected = event.timestamp > cutoff_timestamp

            # Test the actual method
            should_process_actual = retriever.should_process_event(event)

            # Verify the filtering is correct
            assert should_process_actual == should_process_expected, (
                f"Event with timestamp {event.timestamp} should be "
                f"{'processed' if should_process_expected else 'filtered out'} "
                f"when cutoff is {cutoff_timestamp}, "
                f"but got {should_process_actual}"
            )

        # Test the case with no timestamp filter (should process all events)
        retriever_no_filter = S3EventRetriever(bucket_name, since_timestamp=None)

        for event in events:
            should_process_no_filter = retriever_no_filter.should_process_event(event)
            # When no filter is set, all events should be processed
            assert should_process_no_filter is True, (
                f"Event should be processed when no timestamp filter is set, "
                f"but got {should_process_no_filter}"
            )

    # Feature: event-log-scraper, Property 4: Error resilience in retrieval
    @given(
        bucket_name=st.from_regex(r"[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]"),
        file_scenarios=st.lists(
            st.one_of(
                # Successful file scenario
                st.builds(
                    lambda key, event_data: {
                        "type": "success",
                        "key": key,
                        "event_data": event_data,
                    },
                    key=st.builds(
                        lambda action, date: f"log-{action}-{date}.json",
                        action=st.sampled_from(
                            ["submit", "pass-qc", "not-pass-qc", "delete"]
                        ),
                        date=st.from_regex(r"20[2-3][0-9][01][0-9][0-3][0-9]"),
                    ),
                    event_data=st.builds(
                        lambda action: {
                            "action": action,
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
                        action=st.sampled_from(
                            ["submit", "pass-qc", "not-pass-qc", "delete"]
                        ),
                    ),
                ),
                # S3 access error scenario
                st.builds(
                    lambda key, error_code: {
                        "type": "s3_error",
                        "key": key,
                        "error_code": error_code,
                    },
                    key=st.builds(
                        lambda action, date: f"log-{action}-{date}.json",
                        action=st.sampled_from(
                            ["submit", "pass-qc", "not-pass-qc", "delete"]
                        ),
                        date=st.from_regex(r"20[2-3][0-9][01][0-9][0-3][0-9]"),
                    ),
                    error_code=st.sampled_from(
                        ["NoSuchKey", "AccessDenied", "InternalError"]
                    ),
                ),
                # JSON decode error scenario
                st.builds(
                    lambda key: {
                        "type": "json_error",
                        "key": key,
                        "invalid_content": "invalid json content",
                    },
                    key=st.builds(
                        lambda action, date: f"log-{action}-{date}.json",
                        action=st.sampled_from(
                            ["submit", "pass-qc", "not-pass-qc", "delete"]
                        ),
                        date=st.from_regex(r"20[2-3][0-9][01][0-9][0-3][0-9]"),
                    ),
                ),
            ),
            min_size=1,
            max_size=5,  # Reduced for performance
        ),
    )
    @settings(max_examples=10, deadline=None)  # Disable deadline for performance
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
            patch(
                "checkpoint_lambda.s3_retriever.S3EventRetriever.should_process_event"
            ) as mock_should_process,
        ):
            # Setup file list
            file_keys = [scenario["key"] for scenario in file_scenarios]
            mock_list.return_value = file_keys

            # Setup should_process_event to always return True for simplicity
            mock_should_process.return_value = True

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

            # Verify error resilience: system should continue processing despite errors
            # and return all successfully retrieved events

            # 1. Verify all successful events were processed and returned
            assert len(valid_events) == len(expected_successful_events), (
                f"Expected {len(expected_successful_events)} valid events, "
                f"but got {len(valid_events)}"
            )

            # 2. Verify all failed events were recorded as validation errors
            assert len(validation_errors) == expected_error_count, (
                f"Expected {expected_error_count} validation errors, "
                f"but got {len(validation_errors)}"
            )

            # 3. Verify that each validation error contains the expected information
            error_keys = {error["source_key"] for error in validation_errors}
            expected_error_keys = {
                scenario["key"]
                for scenario in file_scenarios
                if scenario["type"] != "success"
            }
            assert error_keys == expected_error_keys, (
                f"Expected error keys {expected_error_keys}, but got {error_keys}"
            )

            # 4. Verify that each validation error has the required structure
            for error in validation_errors:
                assert "source_key" in error, "Validation error missing 'source_key'"
                assert "errors" in error, "Validation error missing 'errors'"
                assert error["source_key"] in file_keys, (
                    f"Error source_key {error['source_key']} not in original file list"
                )

            # 5. Verify that all valid events are properly validated VisitEvent objects
            for event in valid_events:
                assert isinstance(event, VisitEvent), (
                    f"Expected VisitEvent object, got {type(event)}"
                )

            # 6. Verify that the method was called with all files (no early termination)
            mock_list.assert_called_once()
            assert mock_retrieve.call_count == len(file_scenarios), (
                f"Expected {len(file_scenarios)} retrieve calls, "
                f"but got {mock_retrieve.call_count}"
            )

            # 7. Verify that should_process_event was called for each
            # successfully retrieved event
            # (Note: should_process_event is only called for events that were
            # successfully retrieved)
            expected_should_process_calls = len(expected_successful_events)
            assert mock_should_process.call_count == expected_should_process_calls, (
                f"Expected {expected_should_process_calls} should_process_event calls, "
                f"but got {mock_should_process.call_count}"
            )
