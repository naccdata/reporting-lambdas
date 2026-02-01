"""Unit tests for template lambda data models.

These tests demonstrate testing patterns for Pydantic models including
validation, serialization, and property calculations.
"""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError
from template_lambda.models import (
    CustomerRecord,
    InputEvent,
    ProcessingResult,
    SampleDataRecord,
    TransactionRecord,
)


class TestInputEvent:
    """Test cases for InputEvent model."""

    def test_input_event_creation_success(self):
        """Test successful creation of InputEvent."""
        # Arrange & Act
        event = InputEvent(
            event_type="scheduled",
            source="eventbridge",
            data={"key": "value"},
            metadata={"rule": "daily"},
        )

        # Assert
        assert event.event_type == "scheduled"
        assert event.source == "eventbridge"
        assert event.data == {"key": "value"}
        assert event.metadata == {"rule": "daily"}

    def test_input_event_without_metadata(self):
        """Test InputEvent creation without metadata."""
        # Arrange & Act
        event = InputEvent(event_type="direct", source="api", data={"test": "data"})

        # Assert
        assert event.event_type == "direct"
        assert event.source == "api"
        assert event.data == {"test": "data"}
        assert event.metadata is None

    def test_input_event_serialization(self):
        """Test InputEvent JSON serialization."""
        # Arrange
        event = InputEvent(
            event_type="s3_trigger",
            source="s3",
            data={"bucket": "test-bucket"},
            metadata={"count": 1},
        )

        # Act
        json_str = event.model_dump_json()
        parsed = json.loads(json_str)

        # Assert
        assert parsed["event_type"] == "s3_trigger"
        assert parsed["source"] == "s3"
        assert parsed["data"]["bucket"] == "test-bucket"
        assert parsed["metadata"]["count"] == 1


class TestProcessingResult:
    """Test cases for ProcessingResult model."""

    def test_processing_result_creation(self):
        """Test successful creation of ProcessingResult."""
        # Arrange
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 30)

        # Act
        result = ProcessingResult(
            start_time=start_time,
            end_time=end_time,
            records_processed=100,
            records_failed=5,
            output_location="s3://bucket/output.parquet",
            errors=["Error 1", "Error 2"],
        )

        # Assert
        assert result.start_time == start_time
        assert result.end_time == end_time
        assert result.records_processed == 100
        assert result.records_failed == 5
        assert result.output_location == "s3://bucket/output.parquet"
        assert result.errors == ["Error 1", "Error 2"]

    def test_processing_result_defaults(self):
        """Test ProcessingResult with default values."""
        # Arrange
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 30)

        # Act
        result = ProcessingResult(start_time=start_time, end_time=end_time)

        # Assert
        assert result.records_processed == 0
        assert result.records_failed == 0
        assert result.output_location is None
        assert result.errors == []

    def test_duration_seconds_property(self):
        """Test duration_seconds calculated property."""
        # Arrange
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 2, 30)  # 2.5 minutes later

        result = ProcessingResult(start_time=start_time, end_time=end_time)

        # Act & Assert
        assert result.duration_seconds == 150.0  # 2.5 minutes = 150 seconds

    def test_success_rate_property_with_records(self):
        """Test success_rate calculated property with processed records."""
        # Arrange
        result = ProcessingResult(
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            records_processed=95,
            records_failed=5,
        )

        # Act & Assert
        assert result.success_rate == 95.0  # 95/100 * 100 = 95%

    def test_success_rate_property_no_records(self):
        """Test success_rate calculated property with no records."""
        # Arrange
        result = ProcessingResult(
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            records_processed=0,
            records_failed=0,
        )

        # Act & Assert
        assert result.success_rate == 0.0

    def test_success_rate_property_all_failed(self):
        """Test success_rate calculated property with all failed records."""
        # Arrange
        result = ProcessingResult(
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            records_processed=0,
            records_failed=10,
        )

        # Act & Assert
        assert result.success_rate == 0.0


class TestSampleDataRecord:
    """Test cases for SampleDataRecord model."""

    def test_sample_data_record_creation(self):
        """Test successful creation of SampleDataRecord."""
        # Arrange
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        # Act
        record = SampleDataRecord(
            id="test_123", name="Test Record", value=42.5, timestamp=timestamp
        )

        # Assert
        assert record.id == "test_123"
        assert record.name == "Test Record"
        assert record.value == 42.5
        assert record.timestamp == timestamp

    def test_sample_data_record_json_serialization(self):
        """Test SampleDataRecord JSON serialization with datetime."""
        # Arrange
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        record = SampleDataRecord(
            id="test_123", name="Test Record", value=42.5, timestamp=timestamp
        )

        # Act
        json_str = record.model_dump_json()
        parsed = json.loads(json_str)

        # Assert
        assert parsed["id"] == "test_123"
        assert parsed["name"] == "Test Record"
        assert parsed["value"] == 42.5
        assert parsed["timestamp"] == "2024-01-01T12:00:00"

    def test_sample_data_record_validation_error(self):
        """Test SampleDataRecord validation errors."""
        # Act & Assert
        with pytest.raises(ValidationError):
            SampleDataRecord(
                id="",  # Empty ID should be invalid if we add validation
                name="Test",
                value="not_a_number",  # Should be float
                timestamp="not_a_datetime",  # Should be datetime
            )


class TestCustomerRecord:
    """Test cases for CustomerRecord model."""

    def test_customer_record_creation(self):
        """Test successful creation of CustomerRecord."""
        # Arrange
        reg_date = datetime(2024, 1, 1, 10, 0, 0)

        # Act
        customer = CustomerRecord(
            customer_id="cust_123",
            email="test@example.com",
            registration_date=reg_date,
            status="active",
        )

        # Assert
        assert customer.customer_id == "cust_123"
        assert customer.email == "test@example.com"
        assert customer.registration_date == reg_date
        assert customer.status == "active"

    def test_customer_record_json_serialization(self):
        """Test CustomerRecord JSON serialization."""
        # Arrange
        reg_date = datetime(2024, 1, 1, 10, 0, 0)
        customer = CustomerRecord(
            customer_id="cust_123",
            email="test@example.com",
            registration_date=reg_date,
            status="active",
        )

        # Act
        json_str = customer.model_dump_json()
        parsed = json.loads(json_str)

        # Assert
        assert parsed["customer_id"] == "cust_123"
        assert parsed["email"] == "test@example.com"
        assert parsed["registration_date"] == "2024-01-01T10:00:00"
        assert parsed["status"] == "active"


class TestTransactionRecord:
    """Test cases for TransactionRecord model."""

    def test_transaction_record_creation(self):
        """Test successful creation of TransactionRecord."""
        # Arrange
        trans_date = datetime(2024, 1, 1, 14, 30, 0)

        # Act
        transaction = TransactionRecord(
            transaction_id="txn_456",
            customer_id="cust_123",
            amount=99.99,
            transaction_date=trans_date,
            category="purchase",
        )

        # Assert
        assert transaction.transaction_id == "txn_456"
        assert transaction.customer_id == "cust_123"
        assert transaction.amount == 99.99
        assert transaction.transaction_date == trans_date
        assert transaction.category == "purchase"

    def test_transaction_record_json_serialization(self):
        """Test TransactionRecord JSON serialization."""
        # Arrange
        trans_date = datetime(2024, 1, 1, 14, 30, 0)
        transaction = TransactionRecord(
            transaction_id="txn_456",
            customer_id="cust_123",
            amount=99.99,
            transaction_date=trans_date,
            category="purchase",
        )

        # Act
        json_str = transaction.model_dump_json()
        parsed = json.loads(json_str)

        # Assert
        assert parsed["transaction_id"] == "txn_456"
        assert parsed["customer_id"] == "cust_123"
        assert parsed["amount"] == 99.99
        assert parsed["transaction_date"] == "2024-01-01T14:30:00"
        assert parsed["category"] == "purchase"


class TestModelValidation:
    """Test cases for model validation edge cases."""

    def test_input_event_missing_required_fields(self):
        """Test InputEvent validation with missing required fields."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            InputEvent()

        # Check that required fields are mentioned in the error
        error_messages = str(exc_info.value)
        assert "event_type" in error_messages
        assert "source" in error_messages
        assert "data" in error_messages

    def test_processing_result_missing_required_fields(self):
        """Test ProcessingResult validation with missing required fields."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ProcessingResult()

        # Check that required fields are mentioned in the error
        error_messages = str(exc_info.value)
        assert "start_time" in error_messages
        assert "end_time" in error_messages

    def test_sample_data_record_type_validation(self):
        """Test SampleDataRecord type validation."""
        # Act & Assert
        with pytest.raises(ValidationError):
            SampleDataRecord(
                id=123,  # Should be string
                name="Test",
                value="not_a_number",  # Should be float
                timestamp=datetime.utcnow(),
            )
