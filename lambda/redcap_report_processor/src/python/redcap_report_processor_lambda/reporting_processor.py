"""REDCap report processor."""

import io
from datetime import datetime
from typing import Tuple

import boto3
import polars as pl
from aws_helpers.s3_manager import S3Manager
from aws_lambda_powertools import Logger
from pydantic import TypeAdapter
from redcap_api.recap_connection import REDCapConnection
from redcap_api.redcap_parameter_store import REDCapReportParameters
from redcap_api.redcap_project import REDCapProject

from .models import REDCapProcessingResult, REDCapReportInputEvent

logger = Logger()


def _get_redcap_project(parameter_path: str) -> REDCapProject:
    ssm_client = boto3.client("ssm")
    raw_params = ssm_client.get_parameters_by_path(
        Path=parameter_path, WithDecryption=True, Recursive=True
    )

    parameters = {
        x["Name"].split("/")[-1]: x["Value"] for x in raw_params["Parameters"]
    }
    type_adapter = TypeAdapter(REDCapReportParameters)
    redcap_params = type_adapter.validate_python(parameters)
    redcap_connection = REDCapConnection.create_from(redcap_params)
    return REDCapProject.create(redcap_connection)


def _build_output_path(
    output_prefix: str, report_group: str, pid: str, timestamp: str
) -> Tuple[str, str]:
    """Build output path.

    Returns the bucket and S3 key.
    """
    full_path = f"{output_prefix}/{report_group}/{pid}/{timestamp}"
    parts = full_path.split("/")
    return parts[0], "/".join(parts[1:])


def process_data(event: REDCapReportInputEvent) -> REDCapProcessingResult:
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
    bucket, prefix = None, None

    try:
        logger.info("Starting REDCap report processor")

        # connect to REDCap project
        redcap_project = _get_redcap_project(event.parameter_path)
        logger.info(
            f"Grabbed REDCap project with pid '{redcap_project.pid}' "
            + f"and title '{redcap_project.title}'"
        )

        bucket, prefix = _build_output_path(
            output_prefix=event.output_prefix,
            report_group=event.report_group,
            pid=redcap_project.pid,
            timestamp=timestamp,
        )

        # set up S3 manager
        s3_manager = S3Manager(bucket)

        # export records
        record = redcap_project.export_records(exp_format="csv")

        # write to parquet
        df_lazy = pl.scan_csv(io.StringIO(record))
        df = df_lazy.collect()

        # upload parquet to S3
        filename = f"{redcap_project.pid}.parquet"
        s3_manager.upload_parquet(df, f"{prefix}/{filename}")

        end_time = datetime.utcnow()
        return REDCapProcessingResult(
            start_time=start_time,
            end_time=end_time,
            num_records=df_lazy.select(pl.count()).collect()[0, 0],
            output_location=f"{bucket}/{prefix}/{filename}",
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

        return REDCapProcessingResult(
            start_time=start_time,
            end_time=end_time,
            num_records=0,
            output_location=None,
        )
