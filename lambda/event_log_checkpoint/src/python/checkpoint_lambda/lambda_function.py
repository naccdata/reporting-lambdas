import os
import time
from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

from checkpoint_lambda.checkpoint_key_template import CheckpointKeyTemplate
from checkpoint_lambda.checkpoint_store import CheckpointError, CheckpointStore
from checkpoint_lambda.config import LambdaConfig
from checkpoint_lambda.event_filter import EventFilter
from checkpoint_lambda.event_grouper import EventGrouper
from checkpoint_lambda.s3_retriever import S3EventRetriever

# Initialize Lambda Powertools components
logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="EventLogCheckpoint")


@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics
def lambda_handler(  # noqa: C901
    event: dict[str, Any], context: LambdaContext
) -> dict[str, Any]:
    """Main Lambda handler function with filtering and grouping support.

    Workflow:
    1. Load configuration (bucket, prefix, template)
    2. Retrieve events from S3
    3. Filter sandbox events
    4. Group by study-datatype
    5. Process each group independently:
       - Load existing checkpoint
       - Merge new events
       - Save updated checkpoint
    6. Emit metrics and logs

    Args:
        event: Lambda event (unused for scheduled invocation)
        context: Lambda context object

    Returns:
        dict: Response containing:
            - statusCode: HTTP status code (200 for success, 207 for partial
              success, 4xx/5xx for errors)
            - body: Processing summary with group details
    """
    start_time = time.time()

    # Log invocation parameters
    logger.info(
        "Lambda execution started",
        extra={
            "lambda_request_id": context.aws_request_id,
            "function_name": context.function_name,
            "function_version": context.function_version,
        },
    )

    # Load configuration from environment variables
    try:
        config = LambdaConfig(
            bucket=os.environ.get("BUCKET", ""),
            prefix=os.environ.get("PREFIX", ""),
            checkpoint_key_template=os.environ.get("CHECKPOINT_KEY_TEMPLATE", ""),
        )
        # Validate template has required placeholders
        config.validate_template()
    except ValueError as e:
        error_msg = f"Configuration validation error: {e!s}"
        logger.error(error_msg, extra={"exception": str(e)})
        return {
            "statusCode": 400,
            "error": "ValidationError",
            "message": error_msg,
        }
    except Exception as e:
        error_msg = f"Configuration error: {e!s}"
        logger.error(error_msg, extra={"exception": str(e)})
        return {
            "statusCode": 500,
            "error": "InternalServerError",
            "message": error_msg,
        }

    # Log configuration
    logger.info(
        "Configuration loaded",
        extra={
            "bucket": config.bucket,
            "prefix": config.prefix,
            "checkpoint_key_template": config.checkpoint_key_template,
        },
    )

    # Initialize S3EventRetriever (no timestamp filtering - we'll filter per group)
    event_retriever = S3EventRetriever(
        bucket=config.bucket,
        prefix=config.prefix,
        since_timestamp=None,  # Retrieve all events, filter per group
    )

    # Retrieve and validate events
    try:
        all_events, validation_errors = event_retriever.retrieve_and_validate_events()

        # Log file processing counts
        total_files_processed = len(all_events) + len(validation_errors)
        logger.info(
            "File processing completed",
            extra={
                "files_retrieved": total_files_processed,
                "files_processed_successfully": len(all_events),
                "files_failed": len(validation_errors),
                "source_bucket": config.bucket,
                "prefix": config.prefix,
            },
        )

        # Log validation errors if any
        if validation_errors:
            for error in validation_errors:
                logger.warning(
                    f"Validation error in file {error['source_key']}: "
                    f"{error['errors']}",
                    extra={
                        "source_key": error["source_key"],
                        "error_details": error["errors"],
                        "error_type": "validation_error",
                    },
                )
            logger.warning(
                "Validation errors encountered during processing",
                extra={
                    "error_count": len(validation_errors),
                    "total_files_processed": total_files_processed,
                    "success_rate": len(all_events) / total_files_processed
                    if total_files_processed > 0
                    else 0,
                },
            )

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
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Event retrieval failed: {e!s}"
        logger.error(
            error_msg,
            extra={"exception": str(e), "execution_time_ms": execution_time_ms},
        )
        return {
            "statusCode": 500,
            "error": "InternalServerError",
            "message": error_msg,
        }

    # Apply EventFilter to remove sandbox events
    filtered_events, filtered_count = EventFilter.filter_sandbox_events(all_events)

    # Log filtering results
    logger.info(
        "Filtered sandbox events",
        extra={
            "total_events": len(all_events),
            "filtered_count": filtered_count,
            "remaining_events": len(filtered_events),
        },
    )

    # Emit filtering metrics
    metrics.add_metric(name="EventsFiltered", unit="Count", value=filtered_count)

    # Apply EventGrouper to partition by study-datatype
    grouped_events = EventGrouper.group_by_study_datatype(filtered_events)

    # Log grouping results
    logger.info(
        "Grouped events by study-datatype",
        extra={
            "group_count": len(grouped_events),
            "groups": [
                {"study": study, "datatype": datatype, "event_count": len(events)}
                for (study, datatype), events in grouped_events.items()
            ],
        },
    )

    # Initialize checkpoint key template
    try:
        key_template = CheckpointKeyTemplate(config.checkpoint_key_template)
    except ValueError as e:
        error_msg = f"Template validation error: {e!s}"
        logger.error(error_msg, extra={"exception": str(e)})
        return {
            "statusCode": 400,
            "error": "ValidationError",
            "message": error_msg,
        }

    # Process each group independently
    successful_groups = []
    failed_groups = []

    for (study, datatype), events in grouped_events.items():
        try:
            # Generate checkpoint key for this study-datatype combination
            checkpoint_key = key_template.generate_key(study, datatype)

            # Initialize CheckpointStore for this group
            checkpoint_store = CheckpointStore(config.bucket, checkpoint_key)

            # Load existing checkpoint
            try:
                checkpoint = checkpoint_store.get_checkpoint()
                since_timestamp = checkpoint.get_last_processed_timestamp()

                # Filter events by timestamp for incremental processing
                new_events = (
                    [e for e in events if e.timestamp > since_timestamp]
                    if since_timestamp
                    else events
                )

            except CheckpointError:
                # No existing checkpoint - process all events
                checkpoint = checkpoint_store.get_checkpoint()
                new_events = events

            # Merge new events if any
            if new_events:
                updated_checkpoint = checkpoint.add_events(new_events)

                # Save updated checkpoint
                checkpoint_store.save(updated_checkpoint)

                # Log checkpoint save
                logger.info(
                    "Saved checkpoint",
                    extra={
                        "study": study,
                        "datatype": datatype,
                        "checkpoint_key": checkpoint_key,
                        "event_count": updated_checkpoint.get_event_count(),
                        "new_events_added": len(new_events),
                    },
                )

                # Emit metrics for this group
                metrics.add_dimension(name="Study", value=study)
                metrics.add_dimension(name="Datatype", value=datatype)
                metrics.add_metric(
                    name="EventsProcessedByStudyDatatype",
                    unit="Count",
                    value=len(new_events),
                )
                metrics.add_metric(
                    name="CheckpointsSaved",
                    unit="Count",
                    value=1,
                )

                successful_groups.append(
                    {
                        "study": study,
                        "datatype": datatype,
                        "events": len(new_events),
                        "checkpoint_key": checkpoint_key,
                    }
                )
            else:
                # No new events for this group
                logger.info(
                    "No new events for group",
                    extra={
                        "study": study,
                        "datatype": datatype,
                        "checkpoint_key": checkpoint_key,
                    },
                )

        except CheckpointError as e:
            error_msg = f"Checkpoint error: {e!s}"
            logger.error(
                "Failed to save checkpoint",
                extra={
                    "study": study,
                    "datatype": datatype,
                    "checkpoint_key": checkpoint_key,
                    "error": str(e),
                },
                exc_info=True,
            )

            # Emit failure metric
            metrics.add_dimension(name="Study", value=study)
            metrics.add_dimension(name="Datatype", value=datatype)
            metrics.add_metric(
                name="CheckpointSaveFailures",
                unit="Count",
                value=1,
            )

            failed_groups.append(
                {
                    "study": study,
                    "datatype": datatype,
                    "error": error_msg,
                }
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            error_msg = f"S3 error: {error_message}"
            logger.error(
                "S3 error saving checkpoint",
                extra={
                    "study": study,
                    "datatype": datatype,
                    "checkpoint_key": checkpoint_key,
                    "error_code": error_code,
                    "error_message": error_message,
                },
                exc_info=True,
            )

            # Emit failure metric
            metrics.add_dimension(name="Study", value=study)
            metrics.add_dimension(name="Datatype", value=datatype)
            metrics.add_metric(
                name="CheckpointSaveFailures",
                unit="Count",
                value=1,
            )

            failed_groups.append(
                {
                    "study": study,
                    "datatype": datatype,
                    "error": error_msg,
                }
            )

        except Exception as e:
            error_msg = f"Unexpected error: {e!s}"
            logger.error(
                "Unexpected error processing group",
                extra={
                    "study": study,
                    "datatype": datatype,
                    "error": str(e),
                },
                exc_info=True,
            )

            # Emit failure metric
            metrics.add_dimension(name="Study", value=study)
            metrics.add_dimension(name="Datatype", value=datatype)
            metrics.add_metric(
                name="CheckpointSaveFailures",
                unit="Count",
                value=1,
            )

            failed_groups.append(
                {
                    "study": study,
                    "datatype": datatype,
                    "error": error_msg,
                }
            )

    # Calculate execution time
    execution_time_ms = int((time.time() - start_time) * 1000)

    # Log processing summary
    logger.info(
        "Checkpoint processing complete",
        extra={
            "total_events_retrieved": len(all_events),
            "filtered_count": filtered_count,
            "groups_processed": len(successful_groups),
            "groups_failed": len(failed_groups),
            "execution_time_ms": execution_time_ms,
        },
    )

    # Emit execution time metric
    metrics.add_metric(
        name="ExecutionTime",
        unit="Milliseconds",
        value=execution_time_ms,
    )

    # Determine response status code
    if failed_groups and successful_groups:
        # Partial success
        status_code = 207
    elif failed_groups:
        # Complete failure
        status_code = 500
    else:
        # Complete success
        status_code = 200

    # Return summary response
    return {
        "statusCode": status_code,
        "body": {
            "total_events": len(all_events),
            "filtered_events": filtered_count,
            "groups_processed": len(successful_groups),
            "groups_failed": len(failed_groups),
            "successful_groups": successful_groups,
            "failed_groups": failed_groups,
        },
    }
