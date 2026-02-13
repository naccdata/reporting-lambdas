"""Common fixtures for REDCap report procesor testing."""

import pytest
from redcap_report_processor_lambda.models import REDCapProcessingInputEvent
from testing.moto_fixtures import *  # noqa: F403


@pytest.fixture(scope="function")
def valid_event():
    return {
        "parameter_path": "/redcap/aws/pid_0/",
        "report_id": "123",
        "s3_suffix": "testing/file.parquet",
        "s3_prefix": "dummy-bucket/redcap/",
        "environment": "sandbox",
        "mode": "overwrite",
        "region": "us-west-2",
        "log_level": "INFO",
    }


@pytest.fixture(scope="function")
def valid_input(valid_event):
    return REDCapProcessingInputEvent(
        parameter_path=valid_event["parameter_path"],
        report_id=valid_event["report_id"],
        s3_suffix=valid_event["s3_suffix"],
        s3_prefix=valid_event["s3_prefix"],
        environment=valid_event["environment"],
        mode=valid_event["mode"],
        region=valid_event["region"],
    )
