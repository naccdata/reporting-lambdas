"""Error handling utilities for reporting lambdas."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standardized error response format."""

    error: str
    error_code: str
    request_id: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


def handle_validation_error(error: ValidationError, request_id: str) -> Dict[str, Any]:
    """Handle Pydantic validation errors.

    Args:
        error: Pydantic ValidationError
        request_id: Request identifier for tracking

    Returns:
        Standardized error response dictionary
    """
    logger.warning(f"Validation error for request {request_id}: {error!s}")

    return {
        "statusCode": 400,
        "body": ErrorResponse(
            error="Validation failed",
            error_code="VALIDATION_ERROR",
            request_id=request_id,
            timestamp=datetime.utcnow(),
            details={"validation_errors": error.errors()},
        ).model_dump_json(),
    }


def handle_processing_error(error: Exception, request_id: str) -> Dict[str, Any]:
    """Handle general processing errors.

    Args:
        error: Exception that occurred
        request_id: Request identifier for tracking

    Returns:
        Standardized error response dictionary
    """
    logger.error(
        f"Processing error for request {request_id}: {error!s}",
        extra={
            "error": str(error),
            "request_id": request_id,
            "error_type": type(error).__name__,
        },
    )

    return {
        "statusCode": 500,
        "body": ErrorResponse(
            error="Internal processing error",
            error_code="PROCESSING_ERROR",
            request_id=request_id,
            timestamp=datetime.utcnow(),
        ).model_dump_json(),
    }


def handle_not_found_error(resource: str, request_id: str) -> Dict[str, Any]:
    """Handle resource not found errors.

    Args:
        resource: Name/description of the resource that wasn't found
        request_id: Request identifier for tracking

    Returns:
        Standardized error response dictionary
    """
    logger.info(f"Resource not found for request {request_id}: {resource}")

    return {
        "statusCode": 404,
        "body": ErrorResponse(
            error=f"Resource not found: {resource}",
            error_code="NOT_FOUND",
            request_id=request_id,
            timestamp=datetime.utcnow(),
        ).model_dump_json(),
    }


def handle_timeout_error(operation: str, request_id: str) -> Dict[str, Any]:
    """Handle timeout errors.

    Args:
        operation: Description of the operation that timed out
        request_id: Request identifier for tracking

    Returns:
        Standardized error response dictionary
    """
    logger.warning(f"Timeout error for request {request_id}: {operation}")

    return {
        "statusCode": 408,
        "body": ErrorResponse(
            error=f"Operation timed out: {operation}",
            error_code="TIMEOUT_ERROR",
            request_id=request_id,
            timestamp=datetime.utcnow(),
        ).model_dump_json(),
    }


class ErrorCollector:
    """Utility class for collecting and managing errors during batch
    processing."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def add_error(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Add an error message with optional context."""
        error_entry = {
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {},
        }
        self.errors.append(error_entry)
        logger.error(message, extra=context or {})

    def add_warning(
        self, message: str, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a warning message with optional context."""
        warning_entry = {
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {},
        }
        self.warnings.append(warning_entry)
        logger.warning(message, extra=context or {})

    def has_errors(self) -> bool:
        """Check if any errors have been collected."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if any warnings have been collected."""
        return len(self.warnings) > 0

    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of collected errors and warnings."""
        return {
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def clear(self) -> None:
        """Clear all collected errors and warnings."""
        self.errors.clear()
        self.warnings.clear()
