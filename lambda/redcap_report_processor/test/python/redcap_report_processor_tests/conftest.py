"""Common fixtures for REDCap report procesor testing."""

import pytest
from redcap_report_processor_lambda.models import REDCapProcessingInputEvent


@pytest.fixture(scope="function")
def valid_event():
    return {
        "parameter_path": "/redcap/aws/pid_0",
        "report_group": "testing",
        "output_prefix": "dummy-bucket",
        "region": "us-west-2",
        "environment": "sandbox",
        "log_level": "INFO",
    }


@pytest.fixture(scope="function")
def valid_input(valid_event):
    return REDCapProcessingInputEvent(
        parameter_path=valid_event["parameter_path"],
        report_group=valid_event["report_group"],
        output_prefix=valid_event["output_prefix"],
        environment=valid_event["environment"],
        region=valid_event["region"],
    )
