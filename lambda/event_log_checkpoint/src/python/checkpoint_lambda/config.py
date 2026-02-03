"""Configuration module for Lambda execution.

This module provides the LambdaConfig class that validates Lambda
configuration from environment variables, including checkpoint key
template validation.
"""

from pydantic import BaseModel, Field

from checkpoint_lambda.checkpoint_key_template import CheckpointKeyTemplate


class LambdaConfig(BaseModel):
    """Configuration for Lambda execution.

    This model validates Lambda configuration including S3 bucket
    settings and checkpoint key template with required placeholders.
    """

    bucket: str = Field(description="S3 bucket for event logs and checkpoints")
    prefix: str = Field(default="", description="S3 prefix for event logs")
    checkpoint_key_template: str = Field(
        description="Template for checkpoint keys with {study} and {datatype}"
    )

    def validate_template(self) -> None:
        """Validate checkpoint key template has required placeholders.

        This method creates a CheckpointKeyTemplate instance which performs
        validation. If the template is missing required placeholders, a
        ValueError will be raised.

        Raises:
            ValueError: If template missing {study} or {datatype} placeholders
        """
        CheckpointKeyTemplate(self.checkpoint_key_template)
