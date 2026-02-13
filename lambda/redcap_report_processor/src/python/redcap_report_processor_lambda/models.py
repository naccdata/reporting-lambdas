"""Data models for REDCap Report Processor lambda."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class REDCapProcessingInputEvent(BaseModel):
    """Model for REDCap report processor input events."""

    # should at minimum contain url and token
    parameter_path: str = Field(
        description="AWS Parameter path to REDCap project credentials."
    )
    report_id: Optional[str] = Field(
        default=None,
        description=(
            "The report ID to pull; if not provided, pulls all records from the project"
        ),
    )

    # full path will be built as
    # <s3_prefix>/<environment>/<s3_key>
    # e.g.
    # nacc-reporting/bronze-tables/redcap/prod/my-s3-postfix/to/some/file.parquet
    s3_postfix: str = Field(
        description="S3 postfix to write to; must contain parquet filename"
    )
    s3_prefix: str = Field(
        default="nacc-reporting/bronze-tables/redcap",
        description="The S3 prefix to write to",
    )
    environment: Literal["dev", "sandbox", "prod"] = Field(
        default="prod", description="Environment name (sandbox, dev, prod)"
    )

    mode: Literal["overwrite", "append"] = Field(
        default="overwrite",
        description="If writing to an existing file, whether to overwrite or append",
    )

    region: str = Field(default="us-west-2", description="AWS S3 region")

    @field_validator("parameter_path", "s3_prefix", mode="after")
    @classmethod
    def strip_slashes(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("s3_postfix", mode="after")
    @classmethod
    def validate_s3_postfix(cls, value: str) -> str:
        value = value.rstrip("/")
        assert value.endswith(".parquet"), "Expecting parquet file"

        return value

    @property
    def s3_uri(self) -> str:
        """Build the full S3 URI."""
        return f"{self.s3_prefix}/{self.environment}/{self.s3_postfix}"

    @property
    def s3_bucket(self) -> str:
        """Get the S3 bucket from the prefix."""
        return self.s3_prefix.split("/")[0]

    @property
    def s3_key(self) -> str:
        """Get the S3 by building the full path."""
        return "/".join(self.s3_uri.split("/")[1:])


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
