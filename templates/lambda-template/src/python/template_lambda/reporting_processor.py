"""Reporting processor module for template lambda.

This module contains the core reporting and data processing logic separated from the
Lambda handler for better testability and maintainability.
"""

import os
from datetime import datetime
from typing import List

import polars as pl
from aws_lambda_powertools import Logger

# Import common modules (these will be available after common code is implemented)
# from common.aws_helpers import S3Manager
# from common.data_processing import ParquetWriter, DataValidator
# from common.models import ProcessingMetrics
from .models import InputEvent, ProcessingResult, SampleDataRecord

logger = Logger()


def process_data(event: InputEvent) -> ProcessingResult:
    """Main reporting processor for processing data.

    This is a template implementation that should be customized
    for your specific data processing needs.

    Args:
        event: Parsed input event

    Returns:
        Processing result with metrics
    """
    start_time = datetime.utcnow()

    try:
        logger.info(
            "Starting data processing",
            extra={"event_type": event.event_type, "source": event.source},
        )

        # Template processing logic - customize this for your use case
        if event.event_type == "scheduled":
            result = process_scheduled_event(event)
        elif event.event_type == "s3_trigger":
            result = process_s3_event(event)
        else:
            result = process_direct_event(event)

        end_time = datetime.utcnow()
        result.end_time = end_time

        logger.info(
            "Data processing completed",
            extra={
                "records_processed": result.records_processed,
                "records_failed": result.records_failed,
                "duration_seconds": result.duration_seconds,
            },
        )

        return result

    except Exception as e:
        end_time = datetime.utcnow()
        logger.error(
            "Data processing failed",
            extra={
                "error": str(e),
                "duration_seconds": (end_time - start_time).total_seconds(),
            },
        )

        return ProcessingResult(
            start_time=start_time,
            end_time=end_time,
            records_processed=0,
            records_failed=0,
            errors=[str(e)],
        )


def process_scheduled_event(event: InputEvent) -> ProcessingResult:
    """Process a scheduled event (e.g., from EventBridge).

    Args:
        event: Input event from scheduler

    Returns:
        Processing result
    """
    start_time = datetime.utcnow()

    # Template implementation - customize for your data source
    logger.info("Processing scheduled event")

    # Example: Fetch data from an API or database
    sample_data = generate_sample_data(100)  # Replace with actual data fetching

    # Process and validate data
    processed_records = []
    failed_records = 0

    for record in sample_data:
        try:
            # Validate and transform record
            validated_record = validate_record(record)
            processed_records.append(validated_record)
        except Exception as e:
            logger.warning(
                "Failed to process record",
                extra={"record_id": getattr(record, "id", "unknown"), "error": str(e)},
            )
            failed_records += 1

    # Save to parquet (template implementation)
    output_location = save_to_parquet(processed_records)

    return ProcessingResult(
        start_time=start_time,
        end_time=datetime.utcnow(),
        records_processed=len(processed_records),
        records_failed=failed_records,
        output_location=output_location,
    )


def process_s3_event(event: InputEvent) -> ProcessingResult:
    """Process an S3 event trigger.

    Args:
        event: Input event from S3

    Returns:
        Processing result
    """
    start_time = datetime.utcnow()

    logger.info(
        "Processing S3 event",
        extra={"record_count": len(event.data.get("records", []))},
    )

    # Template implementation - customize for your S3 processing needs
    records = event.data.get("records", [])
    processed_count = 0
    failed_count = 0

    # Define output location
    output_location = f"s3://{os.getenv('OUTPUT_BUCKET', 'output-bucket')}/processed/"

    for record in records:
        try:
            # Extract S3 object information
            bucket = record["s3"]["bucket"]["name"]
            key = record["s3"]["object"]["key"]

            logger.info("Processing S3 object", extra={"bucket": bucket, "key": key})

            # Process the S3 object (customize this)
            # result = process_s3_object(bucket, key)
            processed_count += 1

        except Exception as e:
            logger.warning(
                "Failed to process S3 record", extra={"record": record, "error": str(e)}
            )
            failed_count += 1

    return ProcessingResult(
        start_time=start_time,
        end_time=datetime.utcnow(),
        records_processed=processed_count,
        records_failed=failed_count,
        output_location=output_location,
    )


def process_direct_event(event: InputEvent) -> ProcessingResult:
    """Process a direct invocation event.

    Args:
        event: Direct input event

    Returns:
        Processing result
    """
    start_time = datetime.utcnow()

    logger.info("Processing direct event")

    # Template implementation for direct invocation
    # Customize based on your direct invocation needs

    return ProcessingResult(
        start_time=start_time,
        end_time=datetime.utcnow(),
        records_processed=1,
        records_failed=0,
        output_location="direct_processing_complete",
    )


def generate_sample_data(count: int) -> List[SampleDataRecord]:
    """Generate sample data for template purposes.

    Replace this with actual data fetching logic for your use case.

    Args:
        count: Number of sample records to generate

    Returns:
        List of sample data records
    """
    return [
        SampleDataRecord(
            id=f"record_{i}",
            name=f"Sample Record {i}",
            value=i * 10,
            timestamp=datetime.utcnow(),
        )
        for i in range(count)
    ]


def validate_record(record: SampleDataRecord) -> dict:
    """Validate and transform a data record.

    Args:
        record: Input data record

    Returns:
        Validated and transformed record as dictionary

    Raises:
        ValueError: If record validation fails
    """
    # Template validation logic
    if not record.id:
        raise ValueError("Record ID is required")

    if record.value < 0:
        raise ValueError("Record value must be non-negative")

    # Transform to dictionary for parquet storage
    return {
        "id": record.id,
        "name": record.name,
        "value": record.value,
        "timestamp": record.timestamp.isoformat(),
        "processed_at": datetime.utcnow().isoformat(),
    }


def save_to_parquet(records: List[dict]) -> str:
    """Save processed records to parquet format.

    This is a template implementation. In a real lambda, you would
    use the common ParquetWriter and S3Manager classes.

    Args:
        records: List of processed records

    Returns:
        Output location path
    """
    if not records:
        logger.info("No records to save")
        return "no_output"

    # Create DataFrame (for template demonstration)
    # In real implementation, this would be used with ParquetWriter
    _df = pl.DataFrame(records)

    # Template output location
    output_bucket = os.getenv("OUTPUT_BUCKET", "output-bucket")
    output_prefix = os.getenv("OUTPUT_PREFIX", "processed-data/")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_key = f"{output_prefix}data_{timestamp}.parquet"
    output_location = f"s3://{output_bucket}/{output_key}"

    logger.info(
        "Saving data to parquet",
        extra={"record_count": len(records), "output_location": output_location},
    )

    # In a real implementation, you would use:
    # s3_manager = S3Manager(output_bucket)
    # parquet_writer = ParquetWriter()
    # parquet_writer.write_dataframe(df, output_key)

    # For template purposes, just log the operation
    logger.info("Parquet save completed (template mode)")

    return output_location