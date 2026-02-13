"""Unit tests for REDCap Report Processing lambda handler."""

import json
from datetime import datetime
from unittest.mock import Mock, patch

from aws_lambda_powertools.utilities.typing import LambdaContext
from redcap_report_processor_lambda.lambda_function import lambda_handler
from redcap_report_processor_lambda.models import REDCapProcessingResult


class TestLambdaHandler:
    """Test cases for the main lambda handler."""

    def test_lambda_handler_event_success(self, valid_event):
        """Test successful processing a report."""
        context = Mock(spec=LambdaContext)
        context.aws_request_id = "test-request-id"
        context.get_remaining_time_in_millis.return_value = 30000

        # Mock the business logic
        with patch(
            "redcap_report_processor_lambda.lambda_function.process_data"
        ) as mock_process:
            output_location = "s3://dummy-bucket/redcap/sandbox/testing/file.parquet"
            mock_result = REDCapProcessingResult(
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                num_records=100,
                output_location=output_location,
            )
            mock_process.return_value = mock_result

            # Act
            response = lambda_handler(valid_event, context)

            # Assert
            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["status"] == "success"
            assert body["result"]["num_records"] == 100
            assert body["result"]["output_location"] == output_location

    def test_lambda_handler_validation_error(self):
        """Test handling of validation errors by sending an empty event."""
        # Arrange
        event = {}  # Invalid event structure
        context = Mock(spec=LambdaContext)
        context.aws_request_id = "test-request-id"
        context.get_remaining_time_in_millis.return_value = 30000

        # Act
        response = lambda_handler(event, context)

        # Assert
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["status"] == "error"  # Direct event processing

        for text in [
            "2 validation errors for REDCapProcessingInputEvent",
            "Input should be a valid string",
            "parameter_path",
            "s3_suffix",
        ]:
            assert text in body["details"]

    def test_lambda_handler_processing_error(self, valid_event):
        """Test handling of processing errors."""
        # Arrange
        context = Mock(spec=LambdaContext)
        context.aws_request_id = "test-request-id"
        context.get_remaining_time_in_millis.return_value = 30000

        # Mock the business logic to raise an exception
        with patch(
            "redcap_report_processor_lambda.lambda_function.process_data"
        ) as mock_process:
            mock_process.side_effect = Exception("Processing failed")

            # Act
            response = lambda_handler(valid_event, context)

            # Assert
            assert response["statusCode"] == 500
            body = json.loads(response["body"])
            assert body["status"] == "error"
            assert "Internal processing error" in body["message"]
