"""Unit tests for template lambda data models.

These tests demonstrate testing patterns for Pydantic models including
validation, serialization, and property calculations.
"""

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

    def test_input_event_creation_success(self):
        """Test successful creation of REDCapProcessingInputEvent."""
        # Arrange & Act
        event = REDCapProcessingInputEvent(
            parameter_path="/redcap/aws/pid_00/",
            report_group="testing",
            output_prefix="local-bucket/",
            environment="sandbox"
        )

        # Assert; check slashes stripped on parameter path and output prefix
        assert event.parameter_path == "/redcap/aws/pid_00"
        assert event.report_group == "testing"
        assert event.output_prefix == "local-bucket"
        assert event.environment == "sandbox"

    def test_input_event_serialization(self):
        """Test InputEvent JSON serialization."""
        # Arrange
        event = REDCapProcessingInputEvent(
            parameter_path="/redcap/aws/pid_00/",
            report_group="testing",
            output_prefix="local-bucket/",
            environment="sandbox"
        )

        # Act
        json_str = event.model_dump_json()
        parsed = json.loads(json_str)

        # Assert
        assert parsed["parameter_path"] == "/redcap/aws/pid_00"
        assert parsed["report_group"] == "testing"
        assert parsed["output_prefix"] == "local-bucket"
        assert parsed["environment"] == "sandbox"


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
        assert "report_group" in error_messages

    def test_processing_result_missing_required_fields(self):
        """Test ProcessingResult validation with missing required fields."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            REDCapProcessingResult()

        # Check that required fields are mentioned in the error
        error_messages = str(exc_info.value)
        assert "start_time" in error_messages
        assert "end_time" in error_messages
