"""Data models for template lambda.

This module defines the data models specific to this lambda's business
logic. Common infrastructure models are imported from the common.models
module.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class InputEvent(BaseModel):
    """Model for parsed lambda input events."""

    event_type: str = Field(description="Type of event (scheduled, s3_trigger, direct)")
    source: str = Field(
        description="Event source (eventbridge, s3, api_gateway, direct)"
    )
    data: Dict[str, Any] = Field(description="Event data payload")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )


class ProcessingResult(BaseModel):
    """Model for lambda processing results."""

    start_time: datetime = Field(description="Processing start time")
    end_time: datetime = Field(description="Processing end time")
    records_processed: int = Field(
        default=0, description="Number of records processed successfully"
    )
    records_failed: int = Field(
        default=0, description="Number of records that failed processing"
    )
    output_location: Optional[str] = Field(
        default=None, description="Location of output data"
    )
    errors: List[str] = Field(
        default_factory=list, description="List of error messages"
    )

    @property
    def duration_seconds(self) -> float:
        """Calculate processing duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        total = self.records_processed + self.records_failed
        return (self.records_processed / total * 100) if total > 0 else 0.0


class SampleDataRecord(BaseModel):
    """Sample data record model for template purposes.

    Replace this with your actual data models for the specific data
    you're processing in your lambda.
    """

    id: str = Field(description="Unique record identifier")
    name: str = Field(description="Record name or description")
    value: float = Field(description="Numeric value associated with record")
    timestamp: datetime = Field(description="Record timestamp")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


# Example of domain-specific models you might create:


class CustomerRecord(BaseModel):
    """Example model for customer data processing."""

    customer_id: str = Field(description="Unique customer identifier")
    email: str = Field(description="Customer email address")
    registration_date: datetime = Field(description="Customer registration date")
    status: str = Field(description="Customer status (active, inactive, etc.)")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class TransactionRecord(BaseModel):
    """Example model for transaction data processing."""

    transaction_id: str = Field(description="Unique transaction identifier")
    customer_id: str = Field(description="Associated customer ID")
    amount: float = Field(description="Transaction amount")
    transaction_date: datetime = Field(description="Transaction timestamp")
    category: str = Field(description="Transaction category")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
