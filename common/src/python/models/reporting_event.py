"""ReportingEvent model for lambda execution metadata and cross-lambda
communication."""

from datetime import datetime
from typing import Any, ClassVar, Dict, Optional

from pydantic import BaseModel, Field


class ReportingEvent(BaseModel):
    """Base model for lambda execution metadata and cross-lambda
    communication."""

    timestamp: datetime = Field(
        description="Event timestamp", default_factory=datetime.utcnow
    )
    source: str = Field(
        description="Data source identifier", min_length=1, max_length=100
    )
    event_type: str = Field(description="Type of event", min_length=1, max_length=50)
    data: Dict[str, Any] = Field(description="Event payload", default_factory=dict)
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )

    class Config:
        json_encoders: ClassVar = {datetime: lambda v: v.isoformat()}
        # Allow extra fields for extensibility
        extra = "allow"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with ISO timestamp."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReportingEvent":
        """Create ReportingEvent from dictionary."""
        return cls(**data)
