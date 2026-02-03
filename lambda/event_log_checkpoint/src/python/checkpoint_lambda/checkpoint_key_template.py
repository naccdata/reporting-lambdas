"""Checkpoint key template module for configurable S3 paths.

This module provides the CheckpointKeyTemplate class that validates and
generates checkpoint S3 keys from templates with {study} and {datatype}
placeholders.
"""


class CheckpointKeyTemplate:
    """Validates and generates checkpoint keys from templates."""

    def __init__(self, template: str):
        """Initialize with template string.

        Args:
            template: Template string with {study} and {datatype} placeholders

        Raises:
            ValueError: If template is missing required placeholders
        """
        self.template = template
        self.validate()

    def validate(self) -> None:
        """Validate template has required placeholders.

        Raises:
            ValueError: If template missing {study} or {datatype}
        """
        missing_placeholders = []

        if "{study}" not in self.template:
            missing_placeholders.append("{study}")

        if "{datatype}" not in self.template:
            missing_placeholders.append("{datatype}")

        if missing_placeholders:
            missing_str = ", ".join(missing_placeholders)
            raise ValueError(f"Template missing required placeholders: {missing_str}")

    def generate_key(self, study: str, datatype: str) -> str:
        """Generate checkpoint key for study-datatype combination.

        Args:
            study: Study identifier (e.g., "adrc", "dvcid")
            datatype: Datatype identifier (e.g., "form", "dicom")

        Returns:
            Checkpoint key with placeholders replaced
            Example: "checkpoints/adrc-form-events.parquet"
        """
        return self.template.format(study=study, datatype=datatype)
