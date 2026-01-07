from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from checkpoint_lambda.checkpoint import Checkpoint
from checkpoint_lambda.checkpoint_store import CheckpointStore

# Initialize Lambda Powertools components
logger = Logger()
tracer = Tracer()
metrics = Metrics()


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
            - statusCode: HTTP status code
            - checkpoint_status: Status of checkpoint (first_run or incremental)
            - checkpoint_exists: Whether previous checkpoint existed
    """
    logger.info("Lambda handler started", extra={"event": event})

    # Parse Lambda event parameters
    source_bucket = event.get("source_bucket")
    checkpoint_bucket = event.get("checkpoint_bucket")
    checkpoint_key = event.get("checkpoint_key")
    prefix = event.get("prefix", "")  # Optional parameter with default empty string

    logger.info(
        "Parsed event parameters",
        extra={
            "source_bucket": source_bucket,
            "checkpoint_bucket": checkpoint_bucket,
            "checkpoint_key": checkpoint_key,
            "prefix": prefix,
        },
    )

    # Validate required parameters
    if not checkpoint_bucket or not checkpoint_key:
        error_msg = "Missing required parameters: checkpoint_bucket and checkpoint_key are required"
        logger.error(error_msg)
        return {
            "statusCode": 400,
            "error": "ValidationError",
            "message": error_msg,
        }

    # Initialize CheckpointStore
    checkpoint_store = CheckpointStore(checkpoint_bucket, checkpoint_key)

    # Check if previous checkpoint exists
    checkpoint_exists = checkpoint_store.exists()
    logger.info(
        "Checkpoint existence check", extra={"checkpoint_exists": checkpoint_exists}
    )

    # Load previous checkpoint or create empty one for first run
    if checkpoint_exists:
        # Incremental run - load existing checkpoint
        checkpoint = checkpoint_store.load()
        checkpoint_status = "incremental"
        logger.info(
            "Loaded existing checkpoint",
            extra={"event_count": checkpoint.get_event_count()},
        )
    else:
        # First run - create empty checkpoint
        checkpoint = Checkpoint.empty()
        checkpoint_status = "first_run"
        logger.info("Created empty checkpoint for first run")

    # Return response with checkpoint status
    response = {
        "statusCode": 200,
        "checkpoint_status": checkpoint_status,
        "checkpoint_exists": checkpoint_exists,
    }

    logger.info("Lambda handler completed", extra={"response": response})

    return response
