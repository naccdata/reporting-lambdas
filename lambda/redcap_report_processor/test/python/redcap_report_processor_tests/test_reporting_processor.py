"""Unit tests for template lambda reporting processor.

These tests demonstrate testing patterns for reporting processor
including data processing, validation, and error handling.
"""

from datetime import datetime
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st
from template_lambda.models import InputEvent, SampleDataRecord
from template_lambda.reporting_processor import (
    generate_sample_data,
    process_data,
    process_s3_event,
    process_scheduled_event,
    save_to_parquet,
    validate_record,
)


class TestDataProcessing:
    """Test cases for main data processing logic."""

    def test_process_data_scheduled_event(self):
        """Test processing of scheduled events."""
        # Arrange
        event = InputEvent(
            event_type="scheduled",
            source="eventbridge",
            data={"processing_date": "2024-01-01"},
            metadata={"rule_name": "daily-processing"},
        )

        # Act
        result = process_data(event)

        # Assert
        assert result.records_processed >= 0
        assert result.records_failed >= 0
        assert result.start_time <= result.end_time
        assert result.duration_seconds >= 0

    def test_process_data_s3_event(self):
        """Test processing of S3 events."""
        # Arrange
        event = InputEvent(
            event_type="s3_trigger",
            source="s3",
            data={
                "records": [
                    {
                        "s3": {
                            "bucket": {"name": "test-bucket"},
                            "object": {"key": "test-file.json"},
                        }
                    }
                ]
            },
            metadata={"record_count": 1},
        )

        # Act
        result = process_data(event)

        # Assert
        assert result.records_processed >= 0
        assert result.records_failed >= 0
        assert "s3://" in result.output_location

    def test_process_data_direct_event(self):
        """Test processing of direct events."""
        # Arrange
        event = InputEvent(
            event_type="direct",
            source="direct",
            data={"custom_data": "test"},
            metadata={},
        )

        # Act
        result = process_data(event)

        # Assert
        assert result.records_processed == 1
        assert result.records_failed == 0
        assert result.output_location == "direct_processing_complete"

    def test_process_data_handles_exceptions(self):
        """Test that processing handles exceptions gracefully."""
        # Arrange
        event = InputEvent(
            event_type="scheduled", source="eventbridge", data={}, metadata={}
        )

        # Mock generate_sample_data to raise an exception
        with patch(
            "template_lambda.reporting_processor.generate_sample_data"
        ) as mock_gen:
            mock_gen.side_effect = Exception("Data generation failed")

            # Act
            result = process_data(event)

            # Assert
            assert result.records_processed == 0
            assert result.records_failed == 0
            assert len(result.errors) > 0
            assert "Data generation failed" in result.errors[0]


class TestScheduledEventProcessing:
    """Test cases for scheduled event processing."""

    def test_process_scheduled_event_success(self):
        """Test successful scheduled event processing."""
        # Arrange
        event = InputEvent(
            event_type="scheduled",
            source="eventbridge",
            data={"batch_size": 50},
            metadata={},
        )

        # Act
        result = process_scheduled_event(event)

        # Assert
        assert result.records_processed > 0
        assert result.records_failed >= 0
        assert result.output_location is not None
        assert "s3://" in result.output_location

    @patch("template_lambda.reporting_processor.generate_sample_data")
    def test_process_scheduled_event_with_failures(self, mock_generate):
        """Test scheduled event processing with some record failures."""
        # Arrange
        event = InputEvent(
            event_type="scheduled", source="eventbridge", data={}, metadata={}
        )

        # Create sample data with one invalid record
        valid_record = SampleDataRecord(
            id="valid_1", name="Valid Record", value=100, timestamp=datetime.utcnow()
        )
        invalid_record = SampleDataRecord(
            id="",  # Invalid: empty ID
            name="Invalid Record",
            value=-50,  # Invalid: negative value
            timestamp=datetime.utcnow(),
        )
        mock_generate.return_value = [valid_record, invalid_record]

        # Act
        result = process_scheduled_event(event)

        # Assert
        assert result.records_processed == 1  # Only valid record processed
        assert result.records_failed == 1  # Invalid record failed


class TestS3EventProcessing:
    """Test cases for S3 event processing."""

    def test_process_s3_event_single_record(self):
        """Test processing S3 event with single record."""
        # Arrange
        event = InputEvent(
            event_type="s3_trigger",
            source="s3",
            data={
                "records": [
                    {
                        "s3": {
                            "bucket": {"name": "input-bucket"},
                            "object": {"key": "data/file1.json"},
                        }
                    }
                ]
            },
            metadata={"record_count": 1},
        )

        # Act
        result = process_s3_event(event)

        # Assert
        assert result.records_processed == 1
        assert result.records_failed == 0
        assert "output-bucket" in result.output_location

    def test_process_s3_event_multiple_records(self):
        """Test processing S3 event with multiple records."""
        # Arrange
        event = InputEvent(
            event_type="s3_trigger",
            source="s3",
            data={
                "records": [
                    {
                        "s3": {
                            "bucket": {"name": "input-bucket"},
                            "object": {"key": "data/file1.json"},
                        }
                    },
                    {
                        "s3": {
                            "bucket": {"name": "input-bucket"},
                            "object": {"key": "data/file2.json"},
                        }
                    },
                ]
            },
            metadata={"record_count": 2},
        )

        # Act
        result = process_s3_event(event)

        # Assert
        assert result.records_processed == 2
        assert result.records_failed == 0


class TestDataValidation:
    """Test cases for data validation logic."""

    def test_validate_record_success(self):
        """Test successful record validation."""
        # Arrange
        record = SampleDataRecord(
            id="test_123", name="Test Record", value=42.5, timestamp=datetime.utcnow()
        )

        # Act
        validated = validate_record(record)

        # Assert
        assert validated["id"] == "test_123"
        assert validated["name"] == "Test Record"
        assert validated["value"] == 42.5
        assert "timestamp" in validated
        assert "processed_at" in validated

    def test_validate_record_empty_id_fails(self):
        """Test that empty ID causes validation failure."""
        # Arrange
        record = SampleDataRecord(
            id="", name="Test Record", value=42.5, timestamp=datetime.utcnow()
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Record ID is required"):
            validate_record(record)

    def test_validate_record_negative_value_fails(self):
        """Test that negative value causes validation failure."""
        # Arrange
        record = SampleDataRecord(
            id="test_123", name="Test Record", value=-10.0, timestamp=datetime.utcnow()
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Record value must be non-negative"):
            validate_record(record)


class TestSampleDataGeneration:
    """Test cases for sample data generation."""

    def test_generate_sample_data_count(self):
        """Test that correct number of records is generated."""
        # Act
        data = generate_sample_data(10)

        # Assert
        assert len(data) == 10
        assert all(isinstance(record, SampleDataRecord) for record in data)

    def test_generate_sample_data_zero_count(self):
        """Test generating zero records."""
        # Act
        data = generate_sample_data(0)

        # Assert
        assert len(data) == 0
        assert isinstance(data, list)

    def test_generate_sample_data_properties(self):
        """Test properties of generated sample data."""
        # Act
        data = generate_sample_data(5)

        # Assert
        for i, record in enumerate(data):
            assert record.id == f"record_{i}"
            assert record.name == f"Sample Record {i}"
            assert record.value == i * 10
            assert isinstance(record.timestamp, datetime)


class TestParquetSaving:
    """Test cases for parquet saving logic."""

    def test_save_to_parquet_with_records(self):
        """Test saving records to parquet."""
        # Arrange
        records = [
            {
                "id": "test_1",
                "name": "Test Record 1",
                "value": 100,
                "timestamp": "2024-01-01T12:00:00",
                "processed_at": "2024-01-01T12:00:01",
            },
            {
                "id": "test_2",
                "name": "Test Record 2",
                "value": 200,
                "timestamp": "2024-01-01T12:00:00",
                "processed_at": "2024-01-01T12:00:01",
            },
        ]

        # Act
        output_location = save_to_parquet(records)

        # Assert
        assert output_location.startswith("s3://")
        assert "processed-data/" in output_location
        assert output_location.endswith(".parquet")

    def test_save_to_parquet_empty_records(self):
        """Test saving empty record list."""
        # Act
        output_location = save_to_parquet([])

        # Assert
        assert output_location == "no_output"


# Property-based tests using Hypothesis
class TestPropertyBasedValidation:
    """Property-based tests for data validation."""

    @given(
        record_id=st.text(min_size=1, max_size=50),
        name=st.text(min_size=1, max_size=100),
        value=st.floats(
            min_value=0, max_value=1000000, allow_nan=False, allow_infinity=False
        ),
        timestamp=st.datetimes(),
    )
    def test_validate_record_property(self, record_id, name, value, timestamp):
        """Property: For any valid record, validation should succeed and preserve data."""  # noqa: E501
        # Arrange
        record = SampleDataRecord(
            id=record_id, name=name, value=value, timestamp=timestamp
        )

        # Act
        validated = validate_record(record)

        # Assert
        assert validated["id"] == record_id
        assert validated["name"] == name
        assert validated["value"] == value
        assert validated["timestamp"] == timestamp.isoformat()
        assert "processed_at" in validated

    @given(count=st.integers(min_value=0, max_value=1000))
    def test_generate_sample_data_count_property(self, count):
        """Property: For any count, generate_sample_data should return exactly that many records."""  # noqa: E501
        # Act
        data = generate_sample_data(count)

        # Assert
        assert len(data) == count
        assert all(isinstance(record, SampleDataRecord) for record in data)

        # Verify uniqueness of IDs
        if count > 0:
            ids = [record.id for record in data]
            assert len(set(ids)) == len(ids)  # All IDs should be unique
