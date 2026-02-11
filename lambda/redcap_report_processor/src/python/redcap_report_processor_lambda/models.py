"""Data models for template lambda.

This module defines the data models specific to this lambda's business
logic. Common infrastructure models are imported from the common.models
module.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class REDCapProcessingInputEvent(BaseModel):
    """Model for REDCap report processor input events.

    Full output URI ends up being
    <output-prefix>/<environment>/<report-group>/<report-pid>/<timestamp>/<report-pid>.parquet

    e.g.
    nacc-reporting/bronze-tables/redcap/sandbox/clariti/123/20260209-060804/123.parquet
    """

    parameter_path: str = Field(
        description="AWS Parameter path to REDCap report credentials"
    )
    report_group: str = Field(description="The report group to write results under")
    output_prefix: str = Field(
        default="nacc-reporting/bronze-tables/redcap",
        description="The output prefix. Defaults to nacc-reporting/bronze-tables/redcap",
    )

    environment: Literal["dev", "sandbox", "prod"] = Field(
        default="prod", description="Environment name (sandbox, dev, prod)"
    )

    region: str = Field(default="us-west-2", description="AWS S3 region")

    @field_validator("parameter_path", "output_prefix", mode="after")
    @classmethod
    def strip_slashes(cls, value: str) -> str:
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
