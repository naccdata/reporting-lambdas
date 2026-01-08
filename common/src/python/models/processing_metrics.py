"""ProcessingMetrics model for lambda processing operations."""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, validator


class ProcessingMetrics(BaseModel):
    """Metrics for lambda processing operations - used for monitoring and logging."""

    start_time: datetime = Field(description="Processing start time")
    end_time: datetime = Field(description="Processing end time")
    records_processed: int = Field(
        default=0, description="Number of records processed successfully", ge=0
    )
    records_failed: int = Field(
        default=0, description="Number of records that failed processing", ge=0
    )
    bytes_processed: int = Field(default=0, description="Total bytes processed", ge=0)
    output_files_created: int = Field(
        default=0, description="Number of output files created", ge=0
    )
    errors: List[str] = Field(
        default_factory=list, description="List of error messages"
    )

    @validator("end_time")
    def end_time_after_start_time(cls, v, values):
        """Validate that end_time is after start_time."""
        start_time = values.get("start_time")
        if start_time and v < start_time:
            raise ValueError("end_time must be after start_time")
        return v

    @property
    def duration_seconds(self) -> float:
        """Calculate processing duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage (0.0 to 100.0)."""
        total = self.records_processed + self.records_failed
        return (self.records_processed / total * 100.0) if total > 0 else 0.0

    @property
    def total_records(self) -> int:
        """Calculate total number of records."""
        return self.records_processed + self.records_failed

    @property
    def throughput_records_per_second(self) -> float:
        """Calculate throughput in records per second."""
        duration = self.duration_seconds
        return self.records_processed / duration if duration > 0 else 0.0

    @property
    def throughput_bytes_per_second(self) -> float:
        """Calculate throughput in bytes per second."""
        duration = self.duration_seconds
        return self.bytes_processed / duration if duration > 0 else 0.0

    def add_error(self, error_message: str) -> None:
        """Add an error message to the metrics."""
        self.errors.append(error_message)

    def increment_processed(self, count: int = 1) -> None:
        """Increment the count of processed records."""
        self.records_processed += count

    def increment_failed(self, count: int = 1) -> None:
        """Increment the count of failed records."""
        self.records_failed += count

    def add_bytes_processed(self, bytes_count: int) -> None:
        """Add to the total bytes processed."""
        self.bytes_processed += bytes_count

    def increment_output_files(self, count: int = 1) -> None:
        """Increment the count of output files created."""
        self.output_files_created += count

    def to_summary_dict(self) -> dict:
        """Convert to a summary dictionary for logging."""
        return {
            "duration_seconds": round(self.duration_seconds, 2),
            "records_processed": self.records_processed,
            "records_failed": self.records_failed,
            "success_rate_percent": round(self.success_rate, 2),
            "throughput_records_per_second": round(
                self.throughput_records_per_second, 2
            ),
            "throughput_bytes_per_second": round(self.throughput_bytes_per_second, 2),
            "bytes_processed": self.bytes_processed,
            "output_files_created": self.output_files_created,
            "error_count": len(self.errors),
        }
