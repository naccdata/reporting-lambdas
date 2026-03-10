"""Template Lambda function with standard error handling and logging.

This template provides a standardized starting point for reporting
lambdas that process data from various sources and create parquet files
for analytics.
"""

import json
import os
from typing import Any, Dict, Optional

from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from .models import REDCapProcessingInputEvent, REDCapProcessingResult
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
    try:
        # Parse and validate input event
        parsed_event = parse_input_event(event, context)

        # Process business logic
        result = process_data(parsed_event)
        logger.info(
            "Data processing completed",
            extra={
                "num_records": result.num_records,
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
        return create_error_response(500, "Internal processing error", str(e))


@tracer.capture_method
def parse_input_event(
    event: Dict[str, Any], context: LambdaContext
) -> REDCapProcessingInputEvent:
    """Parse and validate the input event.

    Args:
        event: Raw lambda event
        context: Lambda context object

    Returns:
        Validated REDCapProcessingInputEvent object

    Raises:
        ValidationError: If event format is invalid
    """
    # Parse event parameters
    parameter_path = event.get("parameter_path")
    report_id = event.get("report_id")
    s3_suffix = event.get("s3_suffix")
    mode = event.get("mode", "overwrite")

    s3_prefix = os.environ.get("S3_PREFIX", "nacc-reporting/bronze-tables/redcap")
    environment = os.environ.get("ENVIRONMENT", "prod")
    region = os.environ.get("REGION", "us-west-2")
    log_level = os.environ.get("LOG_LEVEL", "INFO")

    logger.setLevel(level=log_level.upper())

    # Log invocation parameters using Lambda Powertools Logger (Requirement 11.1)
    logger.info(
        "Lambda execution started",
        extra={
            "invocation_parameters": {
                "parameter_path": parameter_path,
                "report_id": report_id,
                "s3_suffix": s3_suffix,
                "s3_prefix": s3_prefix,
                "environment": environment,
                "mode": mode,
                "region": region,
                "log_level": log_level,
            },
            "lambda_request_id": context.aws_request_id,
            "function_name": context.function_name,
            "function_version": context.function_version,
        },
    )

    return REDCapProcessingInputEvent(
        parameter_path=parameter_path,  # type: ignore
        report_id=report_id if report_id else None,
        s3_suffix=s3_suffix,  # type: ignore
        s3_prefix=s3_prefix,
        environment=environment,  # type: ignore
        mode=mode,
        region=region,
    )


def create_success_response(result: REDCapProcessingResult) -> Dict[str, Any]:
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
                "message": "REDCap report processing completed successfully",
                "result": {
                    "num_records": result.num_records,
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
