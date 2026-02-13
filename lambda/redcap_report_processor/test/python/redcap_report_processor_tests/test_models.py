"""Unit tests for REDCap Report Processing lambda data models."""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError
from redcap_report_processor_lambda.models import (
    REDCapProcessingInputEvent,
    REDCapProcessingResult,
)


class TestREDCapProcessingInputEvent:
    """Test cases for REDCapProcessingInputEvent model."""

    def test_input_event_creation_success(self, valid_input):
        """Test successful creation of REDCapProcessingInputEvent."""
        assert valid_input.parameter_path == "/redcap/aws/pid_0"
        assert valid_input.report_id == "123"
        assert valid_input.s3_suffix == "testing/file.parquet"
        assert valid_input.s3_prefix == "dummy-bucket/redcap"
        assert valid_input.environment == "sandbox"
        assert valid_input.mode == "overwrite"
        assert valid_input.region == "us-west-2"

        # generated properties
        assert valid_input.s3_uri == "dummy-bucket/redcap/sandbox/testing/file.parquet"
        assert valid_input.s3_bucket == "dummy-bucket"
        assert valid_input.s3_key == "redcap/sandbox/testing/file.parquet"

    def test_input_event_serialization(self, valid_input):
        """Test InputEvent JSON serialization."""
        # Act
        json_str = valid_input.model_dump_json()
        parsed = json.loads(json_str)

        # Assert
        assert parsed["parameter_path"] == "/redcap/aws/pid_0"
        assert parsed["report_id"] == "123"
        assert parsed["s3_suffix"] == "testing/file.parquet"
        assert parsed["s3_prefix"] == "dummy-bucket/redcap"
        assert parsed["environment"] == "sandbox"
        assert parsed["mode"] == "overwrite"
        assert parsed["region"] == "us-west-2"


class TestREDCapProcessingResult:
    """Test cases for REDCapProcessingResult model."""

    def test_processing_result_creation(self):
        """Test successful creation of REDCapProcessingResult."""
        # Arrange
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 30)

        # Act
        result = REDCapProcessingResult(
            start_time=start_time,
            end_time=end_time,
            num_records=100,
            output_location="s3://bucket/output.parquet",
        )

        # Assert
        assert result.start_time == start_time
        assert result.end_time == end_time
        assert result.num_records == 100
        assert result.output_location == "s3://bucket/output.parquet"

    def test_processing_result_defaults(self):
        """Test ProcessingResult with default values."""
        # Arrange
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 30)

        # Act
        result = REDCapProcessingResult(start_time=start_time, end_time=end_time)

        # Assert
        assert result.num_records == 0
        assert result.output_location is None

    def test_duration_seconds_property(self):
        """Test duration_seconds calculated property."""
        # Arrange
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 2, 30)  # 2.5 minutes later

        result = REDCapProcessingResult(start_time=start_time, end_time=end_time)

        # Act & Assert
        assert result.duration_seconds == 150.0  # 2.5 minutes = 150 seconds


class TestModelValidation:
    """Test cases for model validation edge cases."""

    def test_input_event_missing_required_fields(self):
        """Test InputEvent validation with missing required fields."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            REDCapProcessingInputEvent()

        # Check that required fields are mentioned in the error
        error_messages = str(exc_info.value)
        assert "parameter_path" in error_messages
        assert "s3_suffix" in error_messages

    def test_processing_result_missing_required_fields(self):
        """Test ProcessingResult validation with missing required fields."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            REDCapProcessingResult()

        # Check that required fields are mentioned in the error
        error_messages = str(exc_info.value)
        assert "start_time" in error_messages
        assert "end_time" in error_messages
