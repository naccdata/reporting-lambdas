"""Shared test fixtures for all test modules.

This module provides shared pytest fixtures for moto.server testing,
allowing realistic S3 operations across all test files.
"""

import os

import boto3
import pytest
from moto.server import ThreadedMotoServer


@pytest.fixture(scope="module")
def moto_server():
    """Fixture to run a mocked AWS server for testing.

    This fixture provides a ThreadedMotoServer instance that can be used
    across all test modules for realistic S3 operations.
    """
    # Use port=0 to get a random free port
    server = ThreadedMotoServer(port=0)
    server.start()
    host, port = server.get_host_and_port()
    yield f"http://{host}:{port}"
    server.stop()


@pytest.fixture
def s3_client(moto_server):
    """S3 client configured to use moto server.

    This fixture provides a boto3 S3 client configured to use the moto
    server for realistic S3 operations in tests.
    """
    return boto3.client(
        "s3",
        endpoint_url=moto_server,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        aws_session_token="testing",
        region_name="us-east-1",
    )


@pytest.fixture
def setup_s3_environment(moto_server):
    """Configure environment for AWS services to use moto server.

    This fixture sets up environment variables so that both boto3 and
    polars can use the moto server for S3 operations. It properly
    restores the original environment after the test.
    """
    # Store original environment variables
    original_endpoint = os.environ.get("AWS_ENDPOINT_URL")
    original_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    original_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    original_session_token = os.environ.get("AWS_SESSION_TOKEN")
    original_region = os.environ.get("AWS_DEFAULT_REGION")

    # Set environment variables for moto server
    os.environ["AWS_ENDPOINT_URL"] = moto_server
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    yield moto_server

    # Restore original environment
    if original_endpoint is not None:
        os.environ["AWS_ENDPOINT_URL"] = original_endpoint
    else:
        os.environ.pop("AWS_ENDPOINT_URL", None)

    if original_access_key is not None:
        os.environ["AWS_ACCESS_KEY_ID"] = original_access_key
    else:
        os.environ.pop("AWS_ACCESS_KEY_ID", None)

    if original_secret_key is not None:
        os.environ["AWS_SECRET_ACCESS_KEY"] = original_secret_key
    else:
        os.environ.pop("AWS_SECRET_ACCESS_KEY", None)

    if original_session_token is not None:
        os.environ["AWS_SESSION_TOKEN"] = original_session_token
    else:
        os.environ.pop("AWS_SESSION_TOKEN", None)

    if original_region is not None:
        os.environ["AWS_DEFAULT_REGION"] = original_region
    else:
        os.environ.pop("AWS_DEFAULT_REGION", None)


@pytest.fixture
def lambda_config_env(setup_s3_environment):
    """Configure Lambda environment variables for testing.

    This fixture sets up the Lambda configuration environment variables
    (BUCKET, PREFIX, CHECKPOINT_KEY_TEMPLATE) and restores them after
    the test. It depends on setup_s3_environment to ensure AWS
    credentials are configured.

    By default, uses a template that supports study-datatype grouping.
    Tests can override these by setting environment variables before
    calling the handler.
    """
    # Store original environment variables
    original_bucket = os.environ.get("BUCKET")
    original_prefix = os.environ.get("PREFIX")
    original_template = os.environ.get("CHECKPOINT_KEY_TEMPLATE")

    # Set default Lambda configuration
    # Note: Tests should override BUCKET as needed
    os.environ["BUCKET"] = os.environ.get("BUCKET", "test-default-bucket")
    os.environ["PREFIX"] = os.environ.get("PREFIX", "")
    os.environ["CHECKPOINT_KEY_TEMPLATE"] = os.environ.get(
        "CHECKPOINT_KEY_TEMPLATE",
        "checkpoints/{study}-{datatype}-events.parquet",
    )

    yield

    # Restore original environment
    if original_bucket is not None:
        os.environ["BUCKET"] = original_bucket
    else:
        os.environ.pop("BUCKET", None)

    if original_prefix is not None:
        os.environ["PREFIX"] = original_prefix
    else:
        os.environ.pop("PREFIX", None)

    if original_template is not None:
        os.environ["CHECKPOINT_KEY_TEMPLATE"] = original_template
    else:
        os.environ.pop("CHECKPOINT_KEY_TEMPLATE", None)
