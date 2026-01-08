"""Template Lambda function with standard error handling and logging.

This template provides a standardized starting point for reporting
lambdas that process data from various sources and create parquet files
for analytics.
"""

import json
from typing import Any, Dict, Optional

from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from .models import InputEvent, ProcessingResult
from .reporting_processor import process_data

# Initialize AWS Lambda Powertools
logger = Logger()

# Initialize tracer conditionally (avoid issues in testing)
try:
    from aws_lambda_powertools import Tracer

    tracer = Tracer()
except ImportError:
    # Mock tracer for testing environments
    class MockTracer:
        def capture_lambda_handler(self, func):
            return func

        def capture_method(self, func):
            return func

    tracer = MockTracer()  # type: ignore


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Template lambda handler with standard error handling and logging.

    Args:
        event: Lambda event data
        context: Lambda context object

    Returns:
        Dict containing status code and response body
    """
    logger.info(
        "Processing request",
        extra={
            "request_id": context.aws_request_id,
            "event_source": event.get("source", "unknown"),
            "remaining_time_ms": context.get_remaining_time_in_millis(),
        },
    )

    try:
        # Parse and validate input event
        parsed_event = parse_input_event(event)
        logger.info(
            "Input event parsed successfully",
            extra={
                "event_type": parsed_event.event_type,
                "source": parsed_event.source,
            },
        )

        # Process business logic
        result = process_data(parsed_event)
        logger.info(
            "Data processing completed",
            extra={
                "records_processed": result.records_processed,
                "records_failed": result.records_failed,
                "output_location": result.output_location,
                "success_rate": result.success_rate,
            },
        )

        # Return standardized success response
        return create_success_response(result)

    except ValidationError as e:
        logger.warning(
            "Invalid input format",
            extra={"error": str(e), "validation_errors": e.errors()},
        )
        return create_error_response(400, "Invalid input format", str(e))

    except Exception as e:
        logger.error(
            "Processing failed", extra={"error": str(e), "error_type": type(e).__name__}
        )
        return create_error_response(500, "Internal processing error")


@tracer.capture_method
def parse_input_event(event: Dict[str, Any]) -> InputEvent:
    """Parse and validate the input event.

    Args:
        event: Raw lambda event

    Returns:
        Validated InputEvent object

    Raises:
        ValidationError: If event format is invalid
    """
    # Handle different event sources (EventBridge, S3, API Gateway, etc.)
    if "source" in event and event["source"] == "aws.events":
        # EventBridge scheduled event
        return InputEvent(
            event_type="scheduled",
            source="eventbridge",
            data=event.get("detail", {}),
            metadata={
                "rule_name": event.get("detail-type", "unknown"),
                "account": event.get("account"),
                "region": event.get("region"),
            },
        )
    elif "Records" in event:
        # S3 event
        return InputEvent(
            event_type="s3_trigger",
            source="s3",
            data={"records": event["Records"]},
            metadata={"record_count": len(event["Records"])},
        )
    else:
        # Direct invocation or API Gateway
        return InputEvent(
            event_type="direct",
            source="api_gateway" if "httpMethod" in event else "direct",
            data=event,
            metadata={},
        )


def create_success_response(result: ProcessingResult) -> Dict[str, Any]:
    """Create a standardized success response.

    Args:
        result: Processing result object

    Returns:
        Lambda response dictionary
    """
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "status": "success",
                "message": "Data processing completed successfully",
                "result": {
                    "records_processed": result.records_processed,
                    "records_failed": result.records_failed,
                    "success_rate": result.success_rate,
                    "output_location": result.output_location,
                    "duration_seconds": result.duration_seconds,
                },
            }
        ),
    }


def create_error_response(
    status_code: int, message: str, details: Optional[str] = None
) -> Dict[str, Any]:
    """Create a standardized error response.

    Args:
        status_code: HTTP status code
        message: Error message
        details: Optional error details

    Returns:
        Lambda response dictionary
    """
    response_body = {"status": "error", "message": message}

    if details:
        response_body["details"] = details

    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(response_body),
    }
