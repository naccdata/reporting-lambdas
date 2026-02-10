"""Data models for template lambda.

This module defines the data models specific to this lambda's business
logic. Common infrastructure models are imported from the common.models
module.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class REDCapReportInputEvent(BaseModel):
    """Model for REDCap report processor input events.

    Full output URI ends up being
    <output-prefix>/<report-group>/<report-pid>/<timestamp>/*.parquet

    e.g.
    nacc-reporting/redcap/clariti/123/20260209-060804/*.parquet
    """

    parameter_path: str = Field(
        description="AWS Parameter path to REDCap report credentials"
    )
    report_group: str = Field(description="The report group to write results under")
    output_prefix: str = Field(
        default="nacc-reporting/redcap",
        description="The output prefix. Defaults to nacc-reporting/redcap",
    )

    environment: Literal["dev", "staging", "prod"] = Field(
        default="prod", description="Environment name (dev, staging, prod)"
    )

    @field_validator("parameter_path", "output_prefix", mode="before")
    @classmethod
    def strip_slashes(self, value: str) -> str:
        return value.rstrip("/")


class REDCapProcessingResult(BaseModel):
    """Model for REDCap report processor results."""

    start_time: datetime = Field(description="Processing start time")
    end_time: datetime = Field(description="Processing end time")
    num_records: int = Field(
        default=0, description="Number of records pulled from REDCap"
    )
    output_location: Optional[str] = Field(
        default=None, description="Full S3 location of output"
    )

    @property
    def duration_seconds(self) -> float:
        """Calculate processing duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()
