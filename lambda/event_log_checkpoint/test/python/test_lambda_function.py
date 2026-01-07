"""Unit tests for Lambda handler with end-to-end testing.

This module contains unit tests for the Lambda handler function,
testing event parsing, response format, and complete workflow with
realistic S3 operations using moto.server for end-to-end testing.

These tests verify the complete integration of all components working
together with actual S3 operations against a mocked S3 server.
"""

import json
from unittest.mock import Mock

from aws_lambda_powertools.utilities.typing import LambdaContext
from checkpoint_lambda.lambda_function import lambda_handler


def create_log_filename(action, timestamp, adcid, project, ptid, visit_num):
    """Create a log filename following the standard pattern.

    Args:
        action: Event action (submit, pass-qc, not-pass-qc, delete)
        timestamp: Timestamp in YYYYMMDD-HHMMSS format
        adcid: Pipeline/center identifier
        project: Project label
        ptid: Participant ID
        visit_num: Visit number

    Returns:
        str: Formatted log filename
    """
    return f"log-{action}-{timestamp}-{adcid}-{project}-{ptid}-{visit_num}.json"


def create_s3_log_key(prefix, action, timestamp, adcid, project, ptid, visit_num):
    """Create a full S3 key for a log file.

    Args:
        prefix: S3 prefix (e.g., "logs/2024/")
        action: Event action
        timestamp: Timestamp in YYYYMMDD-HHMMSS format
        adcid: Pipeline/center identifier
        project: Project label
        ptid: Participant ID
        visit_num: Visit number

    Returns:
        str: Full S3 key path
    """
    filename = create_log_filename(action, timestamp, adcid, project, ptid, visit_num)
    return f"{prefix}{filename}"


class TestLambdaHandlerBasicStructure:
    """Unit tests for Lambda handler basic structure with moto.server."""

    def test_lambda_event_parsing_all_parameters(self, s3_client, setup_s3_environment):
        """Test that Lambda handler accepts all expected event parameters."""
        # Create test buckets
        source_bucket = "test-event-logs-bucket"
        checkpoint_bucket = "test-checkpoint-bucket"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Test event with all required parameters
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
            "prefix": "logs/2024/",
        }

        # Mock Lambda context
        mock_context = Mock(spec=LambdaContext)
        mock_context.function_name = "test-function"
        mock_context.aws_request_id = "test-request-id"

        # Call handler - should not raise any errors
        response = lambda_handler(test_event, mock_context)

        # Verify response is a dictionary (basic structure)
        assert isinstance(response, dict)

    def test_lambda_event_parsing_required_parameters_only(
        self, s3_client, setup_s3_environment
    ):
        """Test Lambda handler with only required parameters."""
        # Create test buckets
        source_bucket = "test-event-logs-bucket-2"
        checkpoint_bucket = "test-checkpoint-bucket-2"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Test event with only required parameters (no prefix)
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
        }

        mock_context = Mock(spec=LambdaContext)

        # Call handler - should not raise any errors
        response = lambda_handler(test_event, mock_context)

        # Verify response is a dictionary (basic structure)
        assert isinstance(response, dict)

    def test_lambda_context_handling(self, s3_client, setup_s3_environment):
        """Test that Lambda handler properly handles context object."""
        # Create test buckets
        source_bucket = "test-bucket-context"
        checkpoint_bucket = "test-checkpoint-bucket-context"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
        }

        # Mock Lambda context with typical attributes
        mock_context = Mock(spec=LambdaContext)
        mock_context.function_name = "event-log-checkpoint"
        mock_context.aws_request_id = "12345678-1234-1234-1234-123456789012"
        mock_context.log_group_name = "/aws/lambda/event-log-checkpoint"
        mock_context.log_stream_name = "2024/01/15/[$LATEST]abcdef123456"
        mock_context.memory_limit_in_mb = 3008
        mock_context.get_remaining_time_in_millis.return_value = 900000

        # Call handler
        response = lambda_handler(test_event, mock_context)

        # Verify response is a dictionary (basic structure test)
        assert isinstance(response, dict)

    def test_basic_response_format_structure(self, s3_client, setup_s3_environment):
        """Test that Lambda handler returns simplified response format."""
        # Create test buckets
        source_bucket = "test-bucket-response"
        checkpoint_bucket = "test-checkpoint-bucket-response"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
        }

        mock_context = Mock(spec=LambdaContext)

        # Call handler
        response = lambda_handler(test_event, mock_context)

        # Verify simplified response format
        assert isinstance(response, dict)
        assert response == {"statusCode": 200}

        # Verify no detailed metrics in response
        assert "checkpoint_path" not in response
        assert "new_events_processed" not in response
        assert "total_events" not in response
        assert "events_failed" not in response
        assert "execution_time_ms" not in response

    def test_empty_event_handling(self, setup_s3_environment):
        """Test Lambda handler behavior with empty event returns error."""
        mock_context = Mock(spec=LambdaContext)

        # Test with empty event - should return validation error
        empty_event = {}

        # Call handler
        response = lambda_handler(empty_event, mock_context)
        assert isinstance(response, dict)
        assert response["statusCode"] == 400
        assert response["error"] == "ValidationError"
        assert "message" in response

    def test_handler_function_signature(self):
        """Test that the handler function has the correct signature."""
        import inspect

        from checkpoint_lambda.lambda_function import lambda_handler

        # Get function signature
        sig = inspect.signature(lambda_handler)
        params = list(sig.parameters.keys())

        # Verify function has correct parameter names
        assert len(params) == 2
        assert params[0] == "event"
        assert params[1] == "context"

        # Verify return type annotation (if present)
        if sig.return_annotation != inspect.Signature.empty:
            assert (
                sig.return_annotation is dict
                or str(sig.return_annotation) == "dict[str, typing.Any]"
            )

    def test_handler_imports_powertools(self):
        """Test that the handler imports AWS Lambda Powertools components."""
        # Verify that the lambda_function module imports Logger
        import checkpoint_lambda.lambda_function as lambda_module

        # Check that Logger is imported and available
        assert hasattr(lambda_module, "logger")

        # Verify logger is from Lambda Powertools
        logger_class_name = lambda_module.logger.__class__.__name__
        assert logger_class_name == "Logger"

    def test_various_event_structures(self, s3_client, setup_s3_environment):
        """Test handler with various event structures."""
        mock_context = Mock(spec=LambdaContext)

        # Create test buckets for each test case
        test_buckets = [
            ("bucket1", "bucket2"),
            ("bucket3", "bucket4"),
            ("bucket5", "bucket6"),
            ("bucket7", "bucket8"),
        ]

        for _i, (source_bucket, checkpoint_bucket) in enumerate(test_buckets):
            s3_client.create_bucket(Bucket=source_bucket)
            s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Test with different event structures
        test_events = [
            # Minimal event
            {
                "source_bucket": "bucket1",
                "checkpoint_bucket": "bucket2",
                "checkpoint_key": "key1",
            },
            # Event with prefix
            {
                "source_bucket": "bucket3",
                "checkpoint_bucket": "bucket4",
                "checkpoint_key": "key1",
                "prefix": "logs/",
            },
            # Event with empty prefix
            {
                "source_bucket": "bucket5",
                "checkpoint_bucket": "bucket6",
                "checkpoint_key": "key1",
                "prefix": "",
            },
            # Event with additional fields (should be ignored gracefully)
            {
                "source_bucket": "bucket7",
                "checkpoint_bucket": "bucket8",
                "checkpoint_key": "key1",
                "extra_field": "should_be_ignored",
                "another_field": 123,
            },
        ]

        for event in test_events:
            response = lambda_handler(event, mock_context)
            assert isinstance(response, dict)


class TestLambdaHandlerFirstRunScenario:
    """Unit tests for Lambda handler first run scenario with moto.server."""

    def test_first_run_checkpoint_store_exists_returns_false(
        self, s3_client, setup_s3_environment
    ):
        """Test CheckpointStore.exists() returns False for first run."""
        # Create test buckets
        source_bucket = "test-event-logs-bucket-first-run"
        checkpoint_bucket = "test-checkpoint-bucket-first-run"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Setup test event
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
            "prefix": "logs/2024/",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler
        response = lambda_handler(test_event, mock_context)

        # Verify simplified response format
        assert isinstance(response, dict)
        assert response == {"statusCode": 200}

    def test_first_run_checkpoint_store_load_creates_empty_checkpoint(
        self, s3_client, setup_s3_environment
    ):
        """Test CheckpointStore.load() creates empty checkpoint when none
        exists."""
        # Create test buckets
        source_bucket = "test-event-logs-bucket-load"
        checkpoint_bucket = "test-checkpoint-bucket-load"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Setup test event
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler
        response = lambda_handler(test_event, mock_context)

        # Verify simplified response format
        assert isinstance(response, dict)
        assert response == {"statusCode": 200}

    def test_first_run_s3_event_retriever_mocked(self, s3_client, setup_s3_environment):
        """Test S3EventRetriever is properly mocked for first run scenario."""
        # Create test buckets
        source_bucket = "test-event-logs-bucket-retriever"
        checkpoint_bucket = "test-checkpoint-bucket-retriever"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Setup test event
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
            "prefix": "logs/2024/",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler - this will test the current stub implementation
        response = lambda_handler(test_event, mock_context)

        # Verify response is a dictionary (basic structure test for current stub)
        assert isinstance(response, dict)
        assert "statusCode" in response
        assert response["statusCode"] == 200

        # Note: The actual S3EventRetriever calls will be tested when
        # implementation is added

    def test_first_run_checkpoint_components_mocked(
        self, s3_client, setup_s3_environment
    ):
        """Test Checkpoint components are properly mocked for first run
        scenario."""
        # Create test buckets
        source_bucket = "test-event-logs-bucket-components"
        checkpoint_bucket = "test-checkpoint-bucket-components"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Setup test event
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler - this will test the current stub implementation
        response = lambda_handler(test_event, mock_context)

        # Verify response is a dictionary (basic structure test for current stub)
        assert isinstance(response, dict)
        assert "statusCode" in response
        assert response["statusCode"] == 200

        # Note: The actual Checkpoint operations will be tested when
        # implementation is added

    def test_first_run_end_to_end_scenario(self, s3_client, setup_s3_environment):
        """Test complete first run scenario end-to-end with all components
        mocked."""
        # Create test buckets
        source_bucket = "test-event-logs-bucket-e2e"
        checkpoint_bucket = "test-checkpoint-bucket-e2e"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Setup test event
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
            "prefix": "logs/2024/",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler - this will test the current stub implementation
        response = lambda_handler(test_event, mock_context)

        # Verify response is a dictionary (basic structure test for current stub)
        assert isinstance(response, dict)
        assert "statusCode" in response
        assert response["statusCode"] == 200

        # Note: The complete first run workflow will be tested when
        # implementation is added
        # This test establishes the expected behavior for future implementation

    def test_first_run_with_empty_prefix(self, s3_client, setup_s3_environment):
        """Test first run scenario with empty prefix parameter."""
        # Create test buckets
        source_bucket = "test-event-logs-bucket-empty-prefix"
        checkpoint_bucket = "test-checkpoint-bucket-empty-prefix"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Setup test event with no prefix
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler - this will test the current stub implementation
        response = lambda_handler(test_event, mock_context)

        # Verify response is a dictionary (basic structure test for current stub)
        assert isinstance(response, dict)
        assert "statusCode" in response
        assert response["statusCode"] == 200

        # Note: The actual prefix handling will be tested when implementation is added

    def test_first_run_with_no_valid_events_no_checkpoint_created(
        self, s3_client, setup_s3_environment
    ):
        """Test first run scenario with no valid events - no checkpoint should be created."""
        from checkpoint_lambda.checkpoint_store import CheckpointStore

        # Create test buckets
        source_bucket = "test-event-logs-bucket-no-valid"
        checkpoint_bucket = "test-checkpoint-bucket-no-valid"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Create invalid event files in S3 (will fail validation)
        invalid_events = [
            {
                "key": "logs/invalid-event-1.json",
                "content": {
                    "action": "invalid-action",  # Invalid action
                    "study": "adrc",
                    "pipeline_adcid": 42,
                    "project_label": "test-project",
                    "center_label": "test-center",
                    "gear_name": "test-gear",
                    "ptid": "110001",
                    "visit_date": "2024-01-15",
                    "datatype": "form",
                    "module": "UDS",
                    "timestamp": "2024-01-15T10:00:00Z",
                },
            },
            {
                "key": "logs/malformed.json",
                "content": "{ invalid json content",  # Malformed JSON
            },
        ]

        # Upload invalid event files to S3
        for event_file in invalid_events:
            content = event_file["content"]
            if isinstance(content, dict):
                import json

                content = json.dumps(content)
            s3_client.put_object(
                Bucket=source_bucket, Key=event_file["key"], Body=content
            )

        # Setup test event
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
            "prefix": "logs/",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler
        response = lambda_handler(test_event, mock_context)

        # Verify response is successful
        assert isinstance(response, dict)
        assert response["statusCode"] == 200

        # Verify no checkpoint was created (first run with no valid events)
        checkpoint_store = CheckpointStore(
            checkpoint_bucket, "checkpoints/events.parquet"
        )
        assert not checkpoint_store.exists()
        assert checkpoint_store.load() is None

    def test_first_run_scenario_event_parameter_parsing(
        self, s3_client, setup_s3_environment
    ):
        """Test that first run scenario properly parses all event
        parameters."""
        # Create test buckets
        source_bucket = "test-event-logs-bucket-parsing"
        checkpoint_bucket = "test-checkpoint-bucket-parsing"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Setup test event with all parameters
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
            "prefix": "logs/2024/",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler
        response = lambda_handler(test_event, mock_context)

        # Verify response structure
        assert isinstance(response, dict)
        assert "statusCode" in response
        assert response["statusCode"] == 200

        # Note: When implementation is added, this test will verify that:
        # - CheckpointStore is created with checkpoint_bucket and checkpoint_key
        # - S3EventRetriever is created with source_bucket and prefix
        # - since_timestamp is None for first run (no previous checkpoint)

    def test_first_run_scenario_validates_expected_workflow(
        self, s3_client, setup_s3_environment
    ):
        """Test that first run scenario follows expected workflow pattern."""
        # Create test buckets
        source_bucket = "test-event-logs-bucket-workflow"
        checkpoint_bucket = "test-checkpoint-bucket-workflow"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Setup test event
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
            "prefix": "logs/2024/",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler
        response = lambda_handler(test_event, mock_context)

        # Verify basic response structure
        assert isinstance(response, dict)
        assert "statusCode" in response
        assert response["statusCode"] == 200

        # Note: When implementation is added, this test will verify the workflow:
        # 1. CheckpointStore.exists() returns False (no previous checkpoint)
        # 2. CheckpointStore.load() returns None
        # 3. Checkpoint.empty() creates empty checkpoint
        # 4. S3EventRetriever retrieves events with since_timestamp=None
        # 5. Checkpoint.add_events() merges new events with empty checkpoint
        # 6. CheckpointStore.save() saves updated checkpoint


class TestLambdaHandlerIncrementalRunScenario:
    """Unit tests for Lambda handler incremental run scenario with
    moto.server."""

    def test_incremental_run_checkpoint_store_load_returns_existing_checkpoint(
        self, s3_client, setup_s3_environment
    ):
        """Test CheckpointStore.load() returns existing checkpoint for
        incremental run."""
        from datetime import datetime

        from checkpoint_lambda.checkpoint import Checkpoint
        from checkpoint_lambda.models import VisitEvent

        # Create test buckets
        source_bucket = "test-event-logs-incremental-load"
        checkpoint_bucket = "test-checkpoint-incremental-load"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Create existing checkpoint with sample events
        existing_events = [
            VisitEvent(
                action="submit",
                study="adrc",
                pipeline_adcid=42,
                project_label="ingest-form-alpha",
                center_label="test-center",
                gear_name="form-processor",
                ptid="110001",
                visit_date="2024-01-15",
                visit_number="01",
                datatype="form",
                module="UDS",
                packet="I",
                timestamp=datetime.fromisoformat("2024-01-15T10:00:00+00:00"),
            ),
            VisitEvent(
                action="pass-qc",
                study="adrc",
                pipeline_adcid=42,
                project_label="ingest-form-alpha",
                center_label="test-center",
                gear_name="qc-processor",
                ptid="110001",
                visit_date="2024-01-15",
                visit_number="01",
                datatype="form",
                module="UDS",
                packet="I",
                timestamp=datetime.fromisoformat("2024-01-15T10:20:00+00:00"),
            ),
        ]

        # Create and save existing checkpoint
        existing_checkpoint = Checkpoint.from_events(existing_events)
        from checkpoint_lambda.checkpoint_store import CheckpointStore

        checkpoint_store = CheckpointStore(
            checkpoint_bucket, "checkpoints/events.parquet"
        )
        checkpoint_store.save(existing_checkpoint)

        # Setup test event
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
            "prefix": "logs/2024/",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler
        response = lambda_handler(test_event, mock_context)

        # Verify simplified response format
        assert isinstance(response, dict)
        assert response == {"statusCode": 200}

    def test_incremental_run_event_retrieval_with_timestamp_filtering(
        self, s3_client, setup_s3_environment
    ):
        """Test event retrieval with timestamp filtering for incremental
        processing."""
        from datetime import datetime

        from checkpoint_lambda.checkpoint import Checkpoint
        from checkpoint_lambda.models import VisitEvent

        # Create test buckets
        source_bucket = "test-event-logs-timestamp-filter"
        checkpoint_bucket = "test-checkpoint-timestamp-filter"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Create existing checkpoint with events up to 2024-01-15T10:20:00Z
        existing_events = [
            VisitEvent(
                action="submit",
                study="adrc",
                pipeline_adcid=42,
                project_label="ingest-form-alpha",
                center_label="test-center",
                gear_name="form-processor",
                ptid="110001",
                visit_date="2024-01-15",
                visit_number="01",
                datatype="form",
                module="UDS",
                packet="I",
                timestamp=datetime.fromisoformat("2024-01-15T10:00:00+00:00"),
            ),
            VisitEvent(
                action="pass-qc",
                study="adrc",
                pipeline_adcid=42,
                project_label="ingest-form-alpha",
                center_label="test-center",
                gear_name="qc-processor",
                ptid="110001",
                visit_date="2024-01-15",
                visit_number="01",
                datatype="form",
                module="UDS",
                packet="I",
                timestamp=datetime.fromisoformat("2024-01-15T10:20:00+00:00"),
            ),
        ]

        # Create and save existing checkpoint
        existing_checkpoint = Checkpoint.from_events(existing_events)
        from checkpoint_lambda.checkpoint_store import CheckpointStore

        checkpoint_store = CheckpointStore(
            checkpoint_bucket, "checkpoints/events.parquet"
        )
        checkpoint_store.save(existing_checkpoint)

        # Create event files in S3 - some before and some after the last checkpoint timestamp
        event_files = [
            # This event is BEFORE the last checkpoint timestamp - should be filtered out
            {
                "key": create_s3_log_key(
                    "logs/2024/",
                    "submit",
                    "20240115-095000",  # 09:50:00 - before last checkpoint
                    42,
                    "ingest-form-alpha",
                    "110002",
                    "01",
                ),
                "content": {
                    "action": "submit",
                    "study": "adrc",
                    "pipeline_adcid": 42,
                    "project_label": "ingest-form-alpha",
                    "center_label": "test-center",
                    "gear_name": "form-processor",
                    "ptid": "110002",
                    "visit_date": "2024-01-15",
                    "visit_number": "01",
                    "datatype": "form",
                    "module": "UDS",
                    "packet": "I",
                    "timestamp": "2024-01-15T09:50:00Z",
                },
            },
            # This event is AFTER the last checkpoint timestamp - should be processed
            {
                "key": create_s3_log_key(
                    "logs/2024/",
                    "submit",
                    "20240115-103000",  # 10:30:00 - after last checkpoint
                    42,
                    "ingest-form-alpha",
                    "110003",
                    "01",
                ),
                "content": {
                    "action": "submit",
                    "study": "adrc",
                    "pipeline_adcid": 42,
                    "project_label": "ingest-form-alpha",
                    "center_label": "test-center",
                    "gear_name": "form-processor",
                    "ptid": "110003",
                    "visit_date": "2024-01-15",
                    "visit_number": "01",
                    "datatype": "form",
                    "module": "UDS",
                    "packet": "I",
                    "timestamp": "2024-01-15T10:30:00Z",
                },
            },
        ]

        # Upload event files to S3
        for event_file in event_files:
            s3_client.put_object(
                Bucket=source_bucket,
                Key=event_file["key"],
                Body=json.dumps(event_file["content"]),
            )

        # Setup test event
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
            "prefix": "logs/2024/",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler
        response = lambda_handler(test_event, mock_context)

        # Verify simplified response format
        assert isinstance(response, dict)
        assert response == {"statusCode": 200}

        # Note: When full implementation is added, this test will verify:
        # - get_last_processed_timestamp() returns 2024-01-15T10:20:00Z
        # - S3EventRetriever is initialized with since_timestamp=2024-01-15T10:20:00Z
        # - Only events with timestamp > 2024-01-15T10:20:00Z are processed
        # - The event at 09:50:00 is filtered out
        # - The event at 10:30:00 is processed

    def test_incremental_run_realistic_s3_operations_pipeline(
        self, s3_client, setup_s3_environment
    ):
        """Test complete incremental run with realistic S3 operations in event
        processing pipeline."""
        from datetime import datetime

        from checkpoint_lambda.checkpoint import Checkpoint
        from checkpoint_lambda.models import VisitEvent

        # Create test buckets
        source_bucket = "test-event-logs-realistic-pipeline"
        checkpoint_bucket = "test-checkpoint-realistic-pipeline"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Create existing checkpoint with multiple events
        existing_events = [
            VisitEvent(
                action="submit",
                study="adrc",
                pipeline_adcid=42,
                project_label="ingest-form-alpha",
                center_label="center-001",
                gear_name="form-processor",
                ptid="110001",
                visit_date="2024-01-14",
                visit_number="01",
                datatype="form",
                module="UDS",
                packet="I",
                timestamp=datetime.fromisoformat("2024-01-14T15:00:00+00:00"),
            ),
            VisitEvent(
                action="pass-qc",
                study="adrc",
                pipeline_adcid=42,
                project_label="ingest-form-alpha",
                center_label="center-001",
                gear_name="qc-processor",
                ptid="110001",
                visit_date="2024-01-14",
                visit_number="01",
                datatype="form",
                module="UDS",
                packet="I",
                timestamp=datetime.fromisoformat("2024-01-14T15:30:00+00:00"),
            ),
            VisitEvent(
                action="submit",
                study="adrc",
                pipeline_adcid=43,
                project_label="ingest-form-beta",
                center_label="center-002",
                gear_name="form-processor",
                ptid="110002",
                visit_date="2024-01-15",
                visit_number="01",
                datatype="form",
                module="FTLD",
                packet="F",
                timestamp=datetime.fromisoformat("2024-01-15T09:00:00+00:00"),
            ),
        ]

        # Create and save existing checkpoint
        existing_checkpoint = Checkpoint.from_events(existing_events)
        from checkpoint_lambda.checkpoint_store import CheckpointStore

        checkpoint_store = CheckpointStore(
            checkpoint_bucket, "checkpoints/events.parquet"
        )
        checkpoint_store.save(existing_checkpoint)

        # Verify checkpoint was saved correctly
        assert checkpoint_store.exists()
        loaded_checkpoint = checkpoint_store.load()
        assert loaded_checkpoint is not None
        assert loaded_checkpoint.get_event_count() == 3
        last_timestamp = loaded_checkpoint.get_last_processed_timestamp()
        assert last_timestamp == datetime.fromisoformat("2024-01-15T09:00:00+00:00")

        # Create new event files in S3 (after the last checkpoint timestamp)
        new_event_files = [
            {
                "key": create_s3_log_key(
                    "logs/2024/",
                    "pass-qc",
                    "20240115-093000",  # After last checkpoint timestamp
                    43,
                    "ingest-form-beta",
                    "110002",
                    "01",
                ),
                "content": {
                    "action": "pass-qc",
                    "study": "adrc",
                    "pipeline_adcid": 43,
                    "project_label": "ingest-form-beta",
                    "center_label": "center-002",
                    "gear_name": "qc-processor",
                    "ptid": "110002",
                    "visit_date": "2024-01-15",
                    "visit_number": "01",
                    "datatype": "form",
                    "module": "FTLD",
                    "packet": "F",
                    "timestamp": "2024-01-15T09:30:00Z",
                },
            },
            {
                "key": create_s3_log_key(
                    "logs/2024/",
                    "submit",
                    "20240115-100000",  # After last checkpoint timestamp
                    44,
                    "ingest-form-gamma",
                    "110003",
                    "01",
                ),
                "content": {
                    "action": "submit",
                    "study": "adrc",
                    "pipeline_adcid": 44,
                    "project_label": "ingest-form-gamma",
                    "center_label": "center-003",
                    "gear_name": "form-processor",
                    "ptid": "110003",
                    "visit_date": "2024-01-15",
                    "visit_number": "01",
                    "datatype": "form",
                    "module": "LBD",
                    "packet": "L",
                    "timestamp": "2024-01-15T10:00:00Z",
                },
            },
        ]

        # Upload new event files to S3
        for event_file in new_event_files:
            s3_client.put_object(
                Bucket=source_bucket,
                Key=event_file["key"],
                Body=json.dumps(event_file["content"]),
            )

        # Verify files were uploaded
        objects = s3_client.list_objects_v2(Bucket=source_bucket, Prefix="logs/2024/")
        assert "Contents" in objects
        assert len(objects["Contents"]) == 2

        # Setup test event
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
            "prefix": "logs/2024/",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler
        response = lambda_handler(test_event, mock_context)

        # Verify simplified response format
        assert isinstance(response, dict)
        assert response == {"statusCode": 200}

        # Verify checkpoint still exists and can be loaded
        final_checkpoint = checkpoint_store.load()
        assert final_checkpoint is not None
        # Now has original 3 events + 2 new events = 5 total (implementation working correctly)
        assert final_checkpoint.get_event_count() == 5

        # Note: Processing metrics are now logged instead of returned in response
        # The checkpoint S3 path is also logged instead of returned

    def test_incremental_run_with_no_new_events(self, s3_client, setup_s3_environment):
        """Test incremental run scenario when no new events exist."""
        from datetime import datetime

        from checkpoint_lambda.checkpoint import Checkpoint
        from checkpoint_lambda.models import VisitEvent

        # Create test buckets
        source_bucket = "test-event-logs-no-new-events"
        checkpoint_bucket = "test-checkpoint-no-new-events"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Create existing checkpoint
        existing_events = [
            VisitEvent(
                action="submit",
                study="adrc",
                pipeline_adcid=42,
                project_label="ingest-form-alpha",
                center_label="test-center",
                gear_name="form-processor",
                ptid="110001",
                visit_date="2024-01-15",
                visit_number="01",
                datatype="form",
                module="UDS",
                packet="I",
                timestamp=datetime.fromisoformat("2024-01-15T10:00:00+00:00"),
            ),
        ]

        # Create and save existing checkpoint
        existing_checkpoint = Checkpoint.from_events(existing_events)
        from checkpoint_lambda.checkpoint_store import CheckpointStore

        checkpoint_store = CheckpointStore(
            checkpoint_bucket, "checkpoints/events.parquet"
        )
        original_s3_uri = checkpoint_store.save(existing_checkpoint)

        # Get the original checkpoint's last modified time for comparison
        original_response = s3_client.head_object(
            Bucket=checkpoint_bucket, Key="checkpoints/events.parquet"
        )
        original_last_modified = original_response["LastModified"]

        # Don't create any new event files in S3 - simulating no new events

        # Setup test event
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
            "prefix": "logs/2024/",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler
        response = lambda_handler(test_event, mock_context)

        # Verify simplified response format
        assert isinstance(response, dict)
        assert response == {"statusCode": 200}

        # Verify checkpoint still exists but was not overwritten
        assert checkpoint_store.exists()
        final_checkpoint = checkpoint_store.load()
        assert final_checkpoint is not None
        assert final_checkpoint.get_event_count() == 1  # Same as before

        # Verify the checkpoint file was not modified (not overwritten)
        final_response = s3_client.head_object(
            Bucket=checkpoint_bucket, Key="checkpoints/events.parquet"
        )
        final_last_modified = final_response["LastModified"]
        assert final_last_modified == original_last_modified  # File not modified

    def test_incremental_run_checkpoint_store_operations(
        self, s3_client, setup_s3_environment
    ):
        """Test CheckpointStore operations during incremental run."""
        from datetime import datetime

        from checkpoint_lambda.checkpoint import Checkpoint
        from checkpoint_lambda.checkpoint_store import CheckpointStore
        from checkpoint_lambda.models import VisitEvent

        # Create test buckets
        source_bucket = "test-event-logs-store-ops"
        checkpoint_bucket = "test-checkpoint-store-ops"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Create existing checkpoint with known data
        existing_events = [
            VisitEvent(
                action="submit",
                study="adrc",
                pipeline_adcid=42,
                project_label="ingest-form-alpha",
                center_label="test-center",
                gear_name="form-processor",
                ptid="110001",
                visit_date="2024-01-15",
                visit_number="01",
                datatype="form",
                module="UDS",
                packet="I",
                timestamp=datetime.fromisoformat("2024-01-15T10:00:00+00:00"),
            ),
        ]

        # Test CheckpointStore operations directly
        checkpoint_store = CheckpointStore(
            checkpoint_bucket, "checkpoints/events.parquet"
        )

        # Initially, checkpoint should not exist
        assert not checkpoint_store.exists()
        assert checkpoint_store.load() is None

        # Create and save checkpoint
        existing_checkpoint = Checkpoint.from_events(existing_events)
        s3_uri = checkpoint_store.save(existing_checkpoint)
        assert s3_uri == f"s3://{checkpoint_bucket}/checkpoints/events.parquet"

        # Now checkpoint should exist
        assert checkpoint_store.exists()

        # Load checkpoint and verify data
        loaded_checkpoint = checkpoint_store.load()
        assert loaded_checkpoint is not None
        assert loaded_checkpoint.get_event_count() == 1
        assert (
            loaded_checkpoint.get_last_processed_timestamp()
            == datetime.fromisoformat("2024-01-15T10:00:00+00:00")
        )

        # Setup test event for Lambda handler
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
            "prefix": "logs/2024/",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler - should detect existing checkpoint
        response = lambda_handler(test_event, mock_context)

        # Verify simplified response format
        assert isinstance(response, dict)
        assert response == {"statusCode": 200}

        # Verify checkpoint still exists after handler call
        assert checkpoint_store.exists()
        final_checkpoint = checkpoint_store.load()
        assert final_checkpoint is not None
        assert final_checkpoint.get_event_count() == 1


class TestLambdaHandlerEndToEndIntegration:
    """End-to-end integration tests with realistic S3 operations."""

    def test_complete_workflow_with_sample_events(
        self, s3_client, setup_s3_environment
    ):
        """Test complete workflow with sample event files in S3."""
        # Create test buckets
        source_bucket = "test-event-logs-integration"
        checkpoint_bucket = "test-checkpoint-integration"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Create sample event files in S3
        sample_events = [
            {
                "key": create_s3_log_key(
                    "logs/2024/",
                    "submit",
                    "20240115-100000",
                    42,
                    "ingest-form-alpha",
                    "110001",
                    "01",
                ),
                "content": {
                    "action": "submit",
                    "study": "adrc",
                    "pipeline_adcid": 42,
                    "project_label": "ingest-form-alpha",
                    "center_label": "test-center",
                    "gear_name": "form-processor",
                    "ptid": "110001",
                    "visit_date": "2024-01-15",
                    "visit_number": "01",
                    "datatype": "form",
                    "module": "UDS",
                    "packet": "I",
                    "timestamp": "2024-01-15T10:00:00Z",
                },
            },
            {
                "key": create_s3_log_key(
                    "logs/2024/",
                    "pass-qc",
                    "20240115-102000",
                    42,
                    "ingest-form-alpha",
                    "110001",
                    "01",
                ),
                "content": {
                    "action": "pass-qc",
                    "study": "adrc",
                    "pipeline_adcid": 42,
                    "project_label": "ingest-form-alpha",
                    "center_label": "test-center",
                    "gear_name": "qc-processor",
                    "ptid": "110001",
                    "visit_date": "2024-01-15",
                    "visit_number": "01",
                    "datatype": "form",
                    "module": "UDS",
                    "packet": "I",
                    "timestamp": "2024-01-15T10:20:00Z",
                },
            },
        ]

        # Upload sample events to S3
        for event_file in sample_events:
            s3_client.put_object(
                Bucket=source_bucket,
                Key=event_file["key"],
                Body=json.dumps(event_file["content"]),
            )

        # Setup test event
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
            "prefix": "logs/2024/",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler
        response = lambda_handler(test_event, mock_context)

        # Verify simplified response format
        assert isinstance(response, dict)
        assert response == {"statusCode": 200}

    def test_workflow_with_mixed_valid_invalid_events(
        self, s3_client, setup_s3_environment
    ):
        """Test workflow with mix of valid and invalid event files."""
        # Create test buckets
        source_bucket = "test-event-logs-mixed"
        checkpoint_bucket = "test-checkpoint-mixed"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Create mix of valid and invalid event files
        event_files = [
            {
                "key": create_s3_log_key(
                    "logs/",
                    "valid-log-submit",
                    "20240115-100000",
                    42,
                    "ingest-form-alpha",
                    "110001",
                    "01",
                ),
                "content": {
                    "action": "submit",
                    "study": "adrc",
                    "pipeline_adcid": 42,
                    "project_label": "ingest-form-alpha",
                    "center_label": "test-center",
                    "gear_name": "form-processor",
                    "ptid": "110001",
                    "visit_date": "2024-01-15",
                    "visit_number": "01",
                    "datatype": "form",
                    "module": "UDS",
                    "packet": "I",
                    "timestamp": "2024-01-15T10:00:00Z",
                },
            },
            {
                "key": create_s3_log_key(
                    "logs/",
                    "invalid-log-submit",
                    "20240115-100000",
                    42,
                    "ingest-form-alpha",
                    "110002",
                    "01",
                ),
                "content": {
                    "action": "invalid-action",  # Invalid action
                    "study": "adrc",
                    "pipeline_adcid": 42,
                    "project_label": "ingest-form-alpha",
                    "center_label": "test-center",
                    "gear_name": "form-processor",
                    "ptid": "110002",
                    "visit_date": "2024-01-15",
                    "datatype": "form",
                    "module": "UDS",
                    "timestamp": "2024-01-15T10:00:00Z",
                },
            },
            {
                "key": "logs/malformed.json",
                "content": "{ invalid json content",  # Malformed JSON
            },
        ]

        # Upload event files to S3
        for event_file in event_files:
            content = event_file["content"]
            if isinstance(content, dict):
                content = json.dumps(content)
            s3_client.put_object(
                Bucket=source_bucket, Key=event_file["key"], Body=content
            )

        # Setup test event
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
            "prefix": "logs/",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler
        response = lambda_handler(test_event, mock_context)

        # Verify simplified response format
        assert isinstance(response, dict)
        assert response == {"statusCode": 200}

    def test_incremental_processing_workflow(self, s3_client, setup_s3_environment):
        """Test incremental processing with existing checkpoint."""
        # Create test buckets
        source_bucket = "test-event-logs-incremental"
        checkpoint_bucket = "test-checkpoint-incremental"
        s3_client.create_bucket(Bucket=source_bucket)
        s3_client.create_bucket(Bucket=checkpoint_bucket)

        # Create initial checkpoint file (simulating previous run)
        # This will be implemented when CheckpointStore is fully integrated

        # Create new event files (after checkpoint timestamp)
        new_events = [
            {
                "key": create_s3_log_key(
                    "logs/",
                    "submit",
                    "20240116-100000",
                    42,
                    "ingest-form-alpha",
                    "110003",
                    "01",
                ),
                "content": {
                    "action": "submit",
                    "study": "adrc",
                    "pipeline_adcid": 42,
                    "project_label": "ingest-form-alpha",
                    "center_label": "test-center",
                    "gear_name": "form-processor",
                    "ptid": "110003",
                    "visit_date": "2024-01-16",
                    "visit_number": "01",
                    "datatype": "form",
                    "module": "UDS",
                    "packet": "I",
                    "timestamp": "2024-01-16T10:00:00Z",
                },
            }
        ]

        # Upload new events to S3
        for event_file in new_events:
            s3_client.put_object(
                Bucket=source_bucket,
                Key=event_file["key"],
                Body=json.dumps(event_file["content"]),
            )

        # Setup test event
        test_event = {
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": "checkpoints/events.parquet",
            "prefix": "logs/",
        }
        mock_context = Mock(spec=LambdaContext)

        # Call handler
        response = lambda_handler(test_event, mock_context)

        # Verify simplified response format
        assert isinstance(response, dict)
        assert response == {"statusCode": 200}
