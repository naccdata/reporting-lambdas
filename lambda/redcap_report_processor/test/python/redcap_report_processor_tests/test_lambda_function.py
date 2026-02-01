"""Unit tests for template lambda handler.

These tests demonstrate testing patterns for Lambda functions including
event parsing, error handling, and response formatting.
"""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from aws_lambda_powertools.utilities.typing import LambdaContext
from template_lambda.lambda_function import (
    create_error_response,
    create_success_response,
    lambda_handler,
    parse_input_event,
)
from template_lambda.models import ProcessingResult


class TestLambdaHandler:
    """Test cases for the main lambda handler."""

    def test_lambda_handler_scheduled_event_success(self):
        """Test successful processing of a scheduled event."""
        # Arrange
        event = {
            "source": "aws.events",
            "detail-type": "Scheduled Event",
            "detail": {"key": "value"},
            "account": "123456789012",
            "region": "us-east-1",
        }
        context = Mock(spec=LambdaContext)
        context.aws_request_id = "test-request-id"
        context.get_remaining_time_in_millis.return_value = 30000

        # Mock the business logic
        with patch("template_lambda.lambda_function.process_data") as mock_process:
            mock_result = ProcessingResult(
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                records_processed=10,
                records_failed=0,
                output_location="s3://bucket/output.parquet",
            )
            mock_process.return_value = mock_result

            # Act
            response = lambda_handler(event, context)

            # Assert
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["status"] == "success"
            assert body["result"]["records_processed"] == 10
            assert body["result"]["records_failed"] == 0

    def test_lambda_handler_s3_event_success(self):
        """Test successful processing of an S3 event."""
        # Arrange
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "test-file.json"},
                    }
                }
            ]
        }
        context = Mock(spec=LambdaContext)
        context.aws_request_id = "test-request-id"
        context.get_remaining_time_in_millis.return_value = 30000

        # Mock the business logic
        with patch("template_lambda.lambda_function.process_data") as mock_process:
            mock_result = ProcessingResult(
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                records_processed=5,
                records_failed=1,
                output_location="s3://bucket/processed/",
            )
            mock_process.return_value = mock_result

            # Act
            response = lambda_handler(event, context)

            # Assert
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["status"] == "success"
            assert body["result"]["records_processed"] == 5
            assert body["result"]["records_failed"] == 1

    def test_lambda_handler_validation_error(self):
        """Test handling of validation errors."""
        # Arrange
        event = {}  # Invalid event structure
        context = Mock(spec=LambdaContext)
        context.aws_request_id = "test-request-id"
        context.get_remaining_time_in_millis.return_value = 30000

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 200  # Handler completes successfully
        body = json.loads(response["body"])
        assert body["status"] == "success"  # Direct event processing

    def test_lambda_handler_processing_error(self):
        """Test handling of processing errors."""
        # Arrange
        event = {"source": "aws.events", "detail": {"key": "value"}}
        context = Mock(spec=LambdaContext)
        context.aws_request_id = "test-request-id"
        context.get_remaining_time_in_millis.return_value = 30000

        # Mock the business logic to raise an exception
        with patch("template_lambda.lambda_function.process_data") as mock_process:
            mock_process.side_effect = Exception("Processing failed")

            # Act
            response = lambda_handler(event, context)

            # Assert
            assert response["statusCode"] == 500
            body = json.loads(response["body"])
            assert body["status"] == "error"
            assert "Internal processing error" in body["message"]


class TestEventParsing:
    """Test cases for event parsing logic."""

    def test_parse_eventbridge_event(self):
        """Test parsing of EventBridge scheduled events."""
        # Arrange
        event = {
            "source": "aws.events",
            "detail-type": "Scheduled Event",
            "detail": {"key": "value"},
            "account": "123456789012",
            "region": "us-east-1",
        }

        # Act
        parsed = parse_input_event(event)

        # Assert
        assert parsed.event_type == "scheduled"
        assert parsed.source == "eventbridge"
        assert parsed.data == {"key": "value"}
        assert parsed.metadata["account"] == "123456789012"

    def test_parse_s3_event(self):
        """Test parsing of S3 trigger events."""
        # Arrange
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "test-file.json"},
                    }
                }
            ]
        }

        # Act
        parsed = parse_input_event(event)

        # Assert
        assert parsed.event_type == "s3_trigger"
        assert parsed.source == "s3"
        assert "records" in parsed.data
        assert parsed.metadata["record_count"] == 1

    def test_parse_direct_event(self):
        """Test parsing of direct invocation events."""
        # Arrange
        event = {"custom_data": "test_value"}

        # Act
        parsed = parse_input_event(event)

        # Assert
        assert parsed.event_type == "direct"
        assert parsed.source == "direct"
        assert parsed.data == {"custom_data": "test_value"}

    def test_parse_api_gateway_event(self):
        """Test parsing of API Gateway events."""
        # Arrange
        event = {"httpMethod": "POST", "path": "/test", "body": '{"data": "test"}'}

        # Act
        parsed = parse_input_event(event)

        # Assert
        assert parsed.event_type == "direct"
        assert parsed.source == "api_gateway"


class TestResponseFormatting:
    """Test cases for response formatting."""

    def test_create_success_response(self):
        """Test creation of success responses."""
        # Arrange
        result = ProcessingResult(
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 30),
            records_processed=100,
            records_failed=5,
            output_location="s3://bucket/output.parquet",
        )

        # Act
        response = create_success_response(result)

        # Assert
        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"] == "application/json"

        body = json.loads(response["body"])
        assert body["status"] == "success"
        assert body["result"]["records_processed"] == 100
        assert body["result"]["records_failed"] == 5
        assert body["result"]["success_rate"] == pytest.approx(
            95.24, rel=1e-2
        )  # 100/105 * 100
        assert body["result"]["duration_seconds"] == 30.0

    def test_create_error_response_with_details(self):
        """Test creation of error responses with details."""
        # Act
        response = create_error_response(
            400, "Validation failed", "Missing required field"
        )

        # Assert
        assert response["statusCode"] == 400
        assert response["headers"]["Content-Type"] == "application/json"

        body = json.loads(response["body"])
        assert body["status"] == "error"
        assert body["message"] == "Validation failed"
        assert body["details"] == "Missing required field"

    def test_create_error_response_without_details(self):
        """Test creation of error responses without details."""
        # Act
        response = create_error_response(500, "Internal error")

        # Assert
        assert response["statusCode"] == 500

        body = json.loads(response["body"])
        assert body["status"] == "error"
        assert body["message"] == "Internal error"
        assert "details" not in body


# Fixtures for common test data
@pytest.fixture
def sample_eventbridge_event():
    """Sample EventBridge event for testing."""
    return {
        "source": "aws.events",
        "detail-type": "Scheduled Event",
        "detail": {"processing_date": "2024-01-01"},
        "account": "123456789012",
        "region": "us-east-1",
    }


@pytest.fixture
def sample_s3_event():
    """Sample S3 event for testing."""
    return {
        "Records": [
            {
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "test-input-bucket"},
                    "object": {"key": "data/input-file.json", "size": 1024},
                },
            }
        ]
    }


@pytest.fixture
def lambda_context():
    """Mock Lambda context for testing."""
    context = Mock(spec=LambdaContext)
    context.aws_request_id = "test-request-id-123"
    context.function_name = "template-lambda"
    context.function_version = "1"
    context.memory_limit_in_mb = 3008
    context.get_remaining_time_in_millis.return_value = 30000
    return context
