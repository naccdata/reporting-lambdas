"""REDCap report processor."""

import io
from datetime import datetime
from typing import Tuple, Optional

import boto3
import polars as pl
from aws_helpers.s3_manager import S3Manager
from aws_lambda_powertools import Logger
from pydantic import TypeAdapter
from redcap_api.redcap_connection import REDCapConnection
from redcap_api.redcap_parameter_store import REDCapParameters
from redcap_api.redcap_project import REDCapProject

from .models import REDCapProcessingInputEvent, REDCapProcessingResult

logger = Logger()


def get_redcap_records(parameter_path: str, report_id: Optional[str] = None) -> str:
    """Get REDCap records as a CSV string.

    If a report ID is provided, pulls records from the report, else
    pulls all records from the project.

    Args:
        parameter_path: The parameter path to get REDCAP url/token from
        report_id: Optional, the report to grab
    Returns:
        CSV string of all records
    """
    ssm_client = boto3.client("ssm")
    raw_params = ssm_client.get_parameters_by_path(
        Path=parameter_path, WithDecryption=True, Recursive=True
    )

    parameters = {
        x["Name"].split("/")[-1]: x["Value"] for x in raw_params["Parameters"]
    }

    type_adapter = TypeAdapter(REDCapParameters)
    redcap_params = type_adapter.validate_python(parameters)
    redcap_connection = REDCapConnection.create_from(redcap_params)
    redcap_project = REDCapProject.create(redcap_connection)

    if not report_id:
        return redcap_project.export_records(exp_format="csv")

    return redcap_project.export_report(report_id, exp_format="csv")


def process_data(event: REDCapProcessingInputEvent) -> REDCapProcessingResult:
    """Main reporting processor for processing data.

    This is a template implementation that should be customized
    for your specific data processing needs.

    Args:
        event: Parsed input event

    Returns:
        Processing result with metrics
    """
    start_time = datetime.utcnow()
    timestamp = start_time.strftime("%Y%m%d-%H%M%S")

    try:
        logger.info("Starting REDCap report processor")

        # set up S3 manager
        s3_manager = S3Manager(event.s3_bucket, region=event.region)

        # if appending, pull down existing file if it exists
        existing_df = None
        if event.mode == "append" and s3_manager.object_exists(event.s3_key):
            logger.info(
                "Mode is `appending` and existing parquet detected, "
                + "grabbing existing parquet"
            )
            existing_df = s3_manager.download_parquet_object(event.s3_key)

        # get records and write to parquet
        records = get_redcap_records(event.parameter_path, event.report_id)
        df_lazy = pl.scan_csv(io.StringIO(records))
        df = df_lazy.collect()

        if existing_df is not None:
            logger.info("Mode is `appending`, appending new data to existing parquet")
            df = pl.concat([existing_df, df], how="vertical")

        # upload parquet to S3
        s3_manager.upload_parquet(df, event.s3_key)

        end_time = datetime.utcnow()
        return REDCapProcessingResult(
            start_time=start_time,
            end_time=end_time,
            num_records=df_lazy.select(pl.count()).collect()[0, 0],
            output_location=f"s3://{event.s3_uri}",
        )

    except Exception as e:
        end_time = datetime.utcnow()
        logger.error(
            "REDCap report processing failed",
            extra={
                "error": str(e),
                "duration_seconds": (end_time - start_time).total_seconds(),
            },
        )

        raise e
