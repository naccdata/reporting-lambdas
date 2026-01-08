"""Data validation utilities for common validation patterns."""

import logging
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of data validation."""

    def __init__(self, is_valid: bool, errors: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.errors = errors or []

    def __bool__(self) -> bool:
        return self.is_valid

    def __str__(self) -> str:
        if self.is_valid:
            return "Validation passed"
        return f"Validation failed: {'; '.join(self.errors)}"


class BatchValidationResult:
    """Result of batch data validation."""

    def __init__(self):
        self.total_records = 0
        self.valid_records = 0
        self.invalid_records = 0
        self.errors: List[Dict[str, Any]] = []

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_records == 0:
            return 0.0
        return (self.valid_records / self.total_records) * 100

    def add_valid_record(self) -> None:
        """Mark a record as valid."""
        self.total_records += 1
        self.valid_records += 1

    def add_invalid_record(self, index: int, errors: List[str]) -> None:
        """Mark a record as invalid with errors."""
        self.total_records += 1
        self.invalid_records += 1
        self.errors.append({"index": index, "errors": errors})

    def __str__(self) -> str:
        return (
            f"Batch validation: {self.valid_records}/{self.total_records} valid "
            f"({self.success_rate:.1f}% success rate)"
        )


class DataValidator:
    """Common validation patterns for reporting data."""

    @staticmethod
    def validate_schema(
        data: Dict[str, Any], schema: Type[BaseModel]
    ) -> ValidationResult:
        """Validate data against a Pydantic schema.

        Args:
            data: Data dictionary to validate
            schema: Pydantic model class to validate against

        Returns:
            ValidationResult with validation status and errors
        """
        try:
            schema(**data)
            return ValidationResult(is_valid=True)
        except ValidationError as e:
            errors = [
                f"{err['loc'][0] if err['loc'] else 'root'}: {err['msg']}"
                for err in e.errors()
            ]
            return ValidationResult(is_valid=False, errors=errors)
        except Exception as e:
            return ValidationResult(is_valid=False, errors=[f"Validation error: {e!s}"])

    @staticmethod
    def validate_batch(
        data_batch: List[Dict[str, Any]],
        schema: Type[BaseModel],
        fail_fast: bool = False,
    ) -> BatchValidationResult:
        """Validate a batch of data records against a schema.

        Args:
            data_batch: List of data dictionaries to validate
            schema: Pydantic model class to validate against
            fail_fast: If True, stop validation on first error

        Returns:
            BatchValidationResult with validation statistics and errors
        """
        result = BatchValidationResult()

        for index, record in enumerate(data_batch):
            validation_result = DataValidator.validate_schema(record, schema)

            if validation_result.is_valid:
                result.add_valid_record()
            else:
                result.add_invalid_record(index, validation_result.errors)
                if fail_fast:
                    break

        return result

    @staticmethod
    def validate_required_fields(
        data: Dict[str, Any], required_fields: List[str]
    ) -> ValidationResult:
        """Validate that all required fields are present and non-empty.

        Args:
            data: Data dictionary to validate
            required_fields: List of field names that must be present

        Returns:
            ValidationResult with validation status and errors
        """
        errors = []

        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
            elif data[field] is None:
                errors.append(f"Required field '{field}' cannot be None")
            elif isinstance(data[field], str) and not data[field].strip():
                errors.append(f"Required field '{field}' cannot be empty")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    @staticmethod
    def validate_data_types(
        data: Dict[str, Any], type_mapping: Dict[str, Union[type, tuple]]
    ) -> ValidationResult:
        """Validate data types for specified fields.

        Args:
            data: Data dictionary to validate
            type_mapping: Dictionary mapping field names to expected types

        Returns:
            ValidationResult with validation status and errors
        """
        errors = []

        for field, expected_type in type_mapping.items():
            if (
                field in data
                and data[field] is not None
                and not isinstance(data[field], expected_type)
            ):
                actual_type = type(data[field]).__name__
                if isinstance(expected_type, tuple):
                    expected_names = [t.__name__ for t in expected_type]
                    expected_str = " or ".join(expected_names)
                else:
                    expected_str = expected_type.__name__

                errors.append(
                    f"Field '{field}' has incorrect type. "
                    f"Expected: {expected_str}, Actual: {actual_type}"
                )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
