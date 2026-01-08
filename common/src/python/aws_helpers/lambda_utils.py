"""Lambda-specific utilities and decorators."""

import functools
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class ParsedEvent:
    """Parsed Lambda event with common attributes."""

    def __init__(self, raw_event: Dict[str, Any], event_type: str):
        self.raw_event = raw_event
        self.event_type = event_type
        self.timestamp = datetime.utcnow()

        # Extract common attributes based on event type
        if event_type == "s3":
            self._parse_s3_event()
        elif event_type == "sqs":
            self._parse_sqs_event()
        elif event_type == "api_gateway":
            self._parse_api_gateway_event()
        else:
            self._parse_generic_event()

    def _parse_s3_event(self) -> None:
        """Parse S3 event structure."""
        self.records = self.raw_event.get("Records", [])
        self.s3_objects = []

        for record in self.records:
            if "s3" in record:
                s3_info = record["s3"]
                self.s3_objects.append(
                    {
                        "bucket": s3_info["bucket"]["name"],
                        "key": s3_info["object"]["key"],
                        "size": s3_info["object"].get("size", 0),
                        "event_name": record.get("eventName", "unknown"),
                    }
                )

    def _parse_sqs_event(self) -> None:
        """Parse SQS event structure."""
        self.records = self.raw_event.get("Records", [])
        self.messages = []

        for record in self.records:
            self.messages.append(
                {
                    "message_id": record.get("messageId"),
                    "body": record.get("body"),
                    "attributes": record.get("messageAttributes", {}),
                    "receipt_handle": record.get("receiptHandle"),
                }
            )

    def _parse_api_gateway_event(self) -> None:
        """Parse API Gateway event structure."""
        self.http_method = self.raw_event.get("httpMethod")
        self.path = self.raw_event.get("path")
        self.query_parameters = self.raw_event.get("queryStringParameters") or {}
        self.headers = self.raw_event.get("headers") or {}
        self.body = self.raw_event.get("body")

        # Parse JSON body if present
        if self.body:
            try:
                self.json_body = json.loads(self.body)
            except json.JSONDecodeError:
                self.json_body = None
        else:
            self.json_body = None

    def _parse_generic_event(self) -> None:
        """Parse generic event structure."""
        self.source = self.raw_event.get("source", "unknown")
        self.detail_type = self.raw_event.get("detail-type")
        self.detail = self.raw_event.get("detail", {})


class LambdaUtils:
    """Lambda-specific utilities and decorators."""

    @staticmethod
    def with_error_handling(func: Callable) -> Callable:
        """Decorator that adds standardized error handling to Lambda functions.

        Args:
            func: Lambda handler function to wrap

        Returns:
            Wrapped function with error handling
        """

        @functools.wraps(func)
        def wrapper(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
            request_id = getattr(context, "aws_request_id", "unknown")

            try:
                logger.info(
                    f"Processing request {request_id}",
                    extra={
                        "request_id": request_id,
                        "event_source": event.get("source", "unknown"),
                    },
                )

                result = func(event, context)

                logger.info(f"Successfully processed request {request_id}")
                return result

            except Exception as e:
                logger.error(
                    f"Error processing request {request_id}: {e!s}",
                    extra={
                        "request_id": request_id,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                )

                return {
                    "statusCode": 500,
                    "body": json.dumps(
                        {
                            "error": "Internal server error",
                            "request_id": request_id,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    ),
                }

        return wrapper

    @staticmethod
    def parse_lambda_event(event: Dict[str, Any], event_type: str) -> ParsedEvent:
        """Parse Lambda event into structured format.

        Args:
            event: Raw Lambda event dictionary
            event_type: Type of event (s3, sqs, api_gateway, generic)

        Returns:
            ParsedEvent with structured event data
        """
        return ParsedEvent(event, event_type)

    @staticmethod
    def create_success_response(
        data: Any, status_code: int = 200, headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create standardized success response.

        Args:
            data: Response data to include in body
            status_code: HTTP status code
            headers: Optional response headers

        Returns:
            Formatted Lambda response dictionary
        """
        response = {
            "statusCode": status_code,
            "body": json.dumps(data, default=str),
            "headers": headers
            or {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        }

        return response

    @staticmethod
    def create_error_response(
        status_code: int,
        error_message: str,
        error_code: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create standardized error response.

        Args:
            status_code: HTTP status code
            error_message: Human-readable error message
            error_code: Optional application-specific error code
            headers: Optional response headers

        Returns:
            Formatted Lambda error response dictionary
        """
        error_body = {
            "error": error_message,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if error_code:
            error_body["error_code"] = error_code

        response = {
            "statusCode": status_code,
            "body": json.dumps(error_body),
            "headers": headers
            or {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        }

        return response

    @staticmethod
    def extract_correlation_id(event: Dict[str, Any]) -> Optional[str]:
        """Extract correlation ID from various event sources.

        Args:
            event: Lambda event dictionary

        Returns:
            Correlation ID if found, None otherwise
        """
        # Try different locations where correlation ID might be stored
        correlation_sources = [
            # API Gateway
            lambda e: e.get("headers", {}).get("x-correlation-id"),
            lambda e: e.get("headers", {}).get("X-Correlation-ID"),
            # SQS
            lambda e: e.get("Records", [{}])[0]
            .get("messageAttributes", {})
            .get("correlationId", {})
            .get("stringValue"),
            # S3 (from metadata)
            lambda e: e.get("Records", [{}])[0]
            .get("s3", {})
            .get("object", {})
            .get("metadata", {})
            .get("correlation-id"),
            # Generic event detail
            lambda e: e.get("detail", {}).get("correlationId"),
            lambda e: e.get("correlationId"),
        ]

        for extractor in correlation_sources:
            try:
                correlation_id = extractor(event)
                if correlation_id:
                    return correlation_id
            except (KeyError, IndexError, TypeError):
                continue

        return None
