"""Pydantic models for event log validation and parsing.

This module contains the VisitEvent model that validates and parses
visit event logs according to the NACC event log specification.
"""

from datetime import datetime, timezone
from typing import Literal, Optional, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Pattern definitions
PTID_PATTERN = r"^[!-~]{1,10}$"  # printable non-whitespace characters

# Type definitions
VisitEventType = Literal["submit", "delete", "not-pass-qc", "pass-qc"]

DatatypeNameType = Literal[
    "apoe",
    "biomarker",
    "dicom",
    "enrollment",
    "form",
    "genetic-availability",
    "gwas",
    "imputation",
    "scan-analysis",
]

ModuleName = str  # Type alias for readability - accepts any string module name


class VisitEvent(BaseModel):
    """Pydantic model for visit event validation.

    This model validates visit events according to the NACC event log
    specification, ensuring all required fields are present with correct
    types and constraints.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    action: VisitEventType = Field(description="Event action type")
    study: str = Field(default="adrc", description="Study identifier")
    pipeline_adcid: int = Field(description="Pipeline/center identifier")
    project_label: str = Field(description="Flywheel project label")
    center_label: str = Field(description="Center/group label")
    gear_name: str = Field(description="Gear that logged the event")
    ptid: str = Field(
        max_length=10,
        pattern=PTID_PATTERN,
        description="Participant ID",
    )
    visit_date: str = Field(
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Visit date in ISO format YYYY-MM-DD",
    )
    visit_number: Optional[str] = Field(
        default=None, description="Visit number - optional"
    )
    datatype: DatatypeNameType = Field(description="Data type")
    module: Optional[ModuleName] = Field(
        default=None, description="Module name - optional"
    )
    packet: Optional[str] = Field(default=None, description="Packet type - optional")
    timestamp: datetime = Field(description="When action occurred (ISO 8601 datetime)")

    @field_validator("timestamp", mode="after")
    @classmethod
    def ensure_utc_timezone(cls, v: datetime) -> datetime:
        """Ensure timestamp always has UTC timezone.
        
        If timestamp is naive (no timezone), assume it's UTC.
        If timestamp has a timezone, convert it to UTC.
        
        Args:
            v: Datetime value after Pydantic parsing
            
        Returns:
            Datetime with UTC timezone
        """
        if v.tzinfo is None:
            # Naive datetime - assume UTC
            return v.replace(tzinfo=timezone.utc)
        else:
            # Timezone-aware - convert to UTC
            return v.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_module(self) -> Self:
        """Validate module field based on datatype.

        Rules:
        - If datatype != "form" and module is not None: raise error
        - If datatype == "form" and module is None: raise error

        Returns:
            Self: Validated instance

        Raises:
            ValueError: If module validation fails
        """
        if self.datatype != "form" and self.module is not None:
            raise ValueError(
                f"Visit event has datatype {self.datatype}, "
                f"but has form module {self.module}"
            )
        if self.datatype == "form" and self.module is None:
            raise ValueError("Expected module name for form datatype")
        return self
