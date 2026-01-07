import time
from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

from checkpoint_lambda.checkpoint_store import CheckpointError, CheckpointStore
from checkpoint_lambda.s3_retriever import S3EventRetriever

# Initialize Lambda Powertools components
logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="EventLogCheckpoint")


def _update_checkpoint(  # noqa: C901
    source_bucket: str,
    checkpoint_bucket: str,
    checkpoint_key: str,
    prefix: str,
    start_time: float,
) -> dict[str, Any]:
    """Process events and return response.

    Args:
        source_bucket: S3 bucket containing event logs
        checkpoint_bucket: S3 bucket for checkpoint file
        checkpoint_key: S3 key for checkpoint file
        prefix: S3 prefix to filter event logs
        start_time: Lambda execution start time for error logging

    Returns:
        dict: Response object with statusCode and optional error details
    """
    # Initialize CheckpointStore
    checkpoint_store = CheckpointStore(checkpoint_bucket, checkpoint_key)

    try:
        checkpoint = checkpoint_store.get_checkpoint()
        since_timestamp = checkpoint.get_last_processed_timestamp()
    except CheckpointError as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Checkpoint error: {e!s}"
        logger.error(
            error_msg,
            extra={"exception": str(e), "execution_time_ms": execution_time_ms},
        )
        return {
            "statusCode": 500,
            "error": "CheckpointError",
            "message": error_msg,
        }
    except ClientError as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        error_msg = f"S3 error: {error_message}"
        logger.error(
            f"S3 permission error accessing checkpoint bucket: {e}",
            extra={
                "error_code": error_code,
                "error_message": error_message,
                "execution_time_ms": execution_time_ms,
            },
        )
        return {
            "statusCode": 500,
            "error": "InternalServerError",
            "message": error_msg,
        }

    # Initialize S3EventRetriever with timestamp filtering for incremental processing
    event_retriever = S3EventRetriever(
        bucket=source_bucket,
        prefix=prefix,
        since_timestamp=since_timestamp,
    )

    # Retrieve and validate new events
    try:
        valid_events, validation_errors = event_retriever.retrieve_and_validate_events()
    except ClientError as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        error_msg = f"S3 error: {error_message}"
        logger.error(
            f"S3 permission error accessing source bucket: {e}",
            extra={
                "error_code": error_code,
                "error_message": error_message,
                "execution_time_ms": execution_time_ms,
            },
        )
        return {
            "statusCode": 500,
            "error": "InternalServerError",
            "message": error_msg,
        }

    # Log validation errors if any
    if validation_errors:
        # Log individual validation errors for debugging first
        for error in validation_errors:
            logger.warning(
                f"Validation error in file {error['source_key']}: {error['errors']}"
            )
        # Then log summary
        logger.warning(
            "Validation errors encountered",
            extra={"error_count": len(validation_errors)},
        )

    # Determine if we need to save a checkpoint
    updated_checkpoint = checkpoint

    if valid_events:
        updated_checkpoint = checkpoint.add_events(valid_events)

        # Only save if checkpoint contains events
        if not updated_checkpoint.is_empty():
            try:
                checkpoint_path = checkpoint_store.save(updated_checkpoint)
                logger.info(
                    "Checkpoint saved", extra={"checkpoint_path": checkpoint_path}
                )
            except CheckpointError as e:
                execution_time_ms = int((time.time() - start_time) * 1000)
                error_msg = f"Checkpoint error: {e!s}"
                logger.error(
                    f"Failed to save checkpoint: {e}",
                    extra={"exception": str(e), "execution_time_ms": execution_time_ms},
                )
                return {
                    "statusCode": 500,
                    "error": "CheckpointError",
                    "message": error_msg,
                }
            except ClientError as e:
                execution_time_ms = int((time.time() - start_time) * 1000)
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_message = e.response.get("Error", {}).get("Message", str(e))
                error_msg = f"S3 error: {error_message}"
                logger.error(
                    f"S3 permission error saving checkpoint: {e}",
                    extra={
                        "error_code": error_code,
                        "error_message": error_message,
                        "execution_time_ms": execution_time_ms,
                    },
                )
                return {
                    "statusCode": 500,
                    "error": "InternalServerError",
                    "message": error_msg,
                }
    else:
        # For first run with no valid events, don't create empty checkpoint
        # For incremental run with no new events, don't overwrite existing checkpoint
        pass

    # Emit CloudWatch metrics for processing statistics
    metrics.add_metric(name="EventsProcessed", unit="Count", value=len(valid_events))
    metrics.add_metric(name="EventsFailed", unit="Count", value=len(validation_errors))
    if valid_events:
        metrics.add_metric(
            name="TotalEvents", unit="Count", value=updated_checkpoint.get_event_count()
        )

    # Return success response
    return {"statusCode": 200}


@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Main Lambda handler function.

    Args:
        event: Lambda event containing:
            - source_bucket: S3 bucket containing event logs
            - prefix: Optional S3 prefix to filter event logs
            - checkpoint_bucket: S3 bucket for checkpoint file
            - checkpoint_key: S3 key for checkpoint file
        context: Lambda context object

    Returns:
        dict: Response containing:
            - statusCode: HTTP status code (200 for success, 4xx/5xx for errors)
            - error: Error type (only present on failure)
            - message: Error message (only present on failure)
    """
    start_time = time.time()

    # Parse Lambda event parameters
    source_bucket = event.get("source_bucket")
    checkpoint_bucket = event.get("checkpoint_bucket")
    checkpoint_key = event.get("checkpoint_key")
    prefix = event.get("prefix", "")  # Optional parameter with default empty string

    # Validate required parameters
    if not checkpoint_bucket or not checkpoint_key:
        error_msg = (
            "Missing required parameters: checkpoint_bucket "
            "and checkpoint_key are required"
        )
        logger.error(error_msg)
        return {
            "statusCode": 400,
            "error": "ValidationError",
            "message": error_msg,
        }

    if not source_bucket:
        error_msg = "Missing required parameter: source_bucket is required"
        logger.error(error_msg)
        return {
            "statusCode": 400,
            "error": "ValidationError",
            "message": error_msg,
        }

    try:
        # Process events
        response = _update_checkpoint(
            source_bucket, checkpoint_bucket, checkpoint_key, prefix, start_time
        )

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Lambda execution failed: {e!s}"
        logger.error(
            error_msg,
            extra={"exception": str(e), "execution_time_ms": execution_time_ms},
        )

        return {
            "statusCode": 500,
            "error": "InternalServerError",
            "message": error_msg,
        }

    # If response indicates an error, return it directly
    if response["statusCode"] == 200:
        # Calculate execution time and emit CloudWatch metrics
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Emit CloudWatch metrics (but don't return them in response)
        # Note: Metrics will be emitted by the metrics decorator
        metrics.add_metric(
            name="ExecutionTime", unit="Milliseconds", value=execution_time_ms
        )

    return response
