"""S3 operations with retry logic and error handling."""

import io
import json
import logging
import os
import tempfile
import time
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

import boto3
import polars as pl
import pyarrow
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class S3Error(Exception):
    """Exception raised for S3 operation errors."""

    pass


def s3_retry(func, max_retries: int = 3):
    """Decorator to handle S3 retries."""

    def wrapper(*args, **kwargs):
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)

            except ClientError as e:
                if attempt == max_retries:
                    error_msg = f"Failed to execute S3 command: {e!s}"
                    logger.error(error_msg)
                    raise S3Error(error_msg) from e

                wait_time = 2**attempt
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e!s}"
                )
                time.sleep(wait_time)

        # This should never be reached due to the loop structure, but added for
        # type safety
        raise S3Error(f"Failed to execute S3 command after {self.max_retries} retries")

    return wrapper


class S3Manager:
    """S3 operations with retry logic and error handling."""

    def __init__(
        self,
        bucket_name: str,
        region: str = "us-west-2",
    ):
        """Initialize S3Manager.

        Args:
            bucket_name: Name of the S3 bucket
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.region = region

        try:
            self.s3_client = boto3.client("s3", region_name=region)
        except NoCredentialsError as e:
            raise S3Error(f"AWS credentials not found: {e!s}") from e

    @s3_retry
    def list_objects_with_prefix(
        self, prefix: str, since: Optional[datetime] = None, max_keys: int = 1000
    ) -> List[str]:
        """List objects in S3 bucket with given prefix.

        Args:
            prefix: Object key prefix to filter by
            since: Optional datetime to filter objects modified after this time
            max_keys: Maximum number of keys to return

        Returns:
            List of object keys matching criteria

        Raises:
            S3Error: If listing fails after retries
        """
        paginator = self.s3_client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(
            Bucket=self.bucket_name,
            Prefix=prefix,
            PaginationConfig={"MaxItems": max_keys},
        )

        objects = []
        for page in page_iterator:
            if "Contents" in page:
                for obj in page["Contents"]:
                    # Filter by modification time if specified
                    if (
                        since is None
                        or obj["LastModified"].replace(tzinfo=None) >= since
                    ):
                        objects.append(obj["Key"])

        logger.info(f"Found {len(objects)} objects with prefix '{prefix}'")
        return objects

    @s3_retry
    def download_json_object(self, key: str) -> Dict[str, Any]:
        """Download and parse JSON object from S3.

        Args:
            key: S3 object key

        Returns:
            Parsed JSON data as dictionary

        Raises:
            S3Error: If download or parsing fails after retries
        """
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        content = response["Body"].read().decode("utf-8")
        data = json.loads(content)

        logger.debug(f"Successfully downloaded JSON object: {key}")
        return data

    @s3_retry
    def download_parquet_object(self, key: str) -> pl.DataFrame:
        """Download a parquet file.

        Args:
            key: The S3 key to pull
        Returns:
            The dataframe, if successful
        """
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        parquet_bytes = response["Body"].read()
        df = pl.read_parquet(io.BytesIO(parquet_bytes))

        logger.debug(f"Successfully downloaded and loaded parquet object: {key}")
        return df

    @s3_retry
    def upload_parquet(
        self,
        df: pl.DataFrame,
        key: str,
        compression: Literal[
            "snappy", "gzip", "lz4", "zstd", "uncompressed"
        ] = "snappy",
    ) -> None:
        """Upload DataFrame as parquet file to S3.

        Args:
            df: Polars DataFrame to upload
            key: S3 object key for the parquet file
            compression: Compression algorithm to use

        Raises:
            S3Error: If upload fails after retries
        """
        # Write DataFrame to temporary parquet file
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            df.write_parquet(tmp_path, compression=compression, use_pyarrow=True)

            # Upload to S3
            self.s3_client.upload_file(tmp_path, self.bucket_name, key)

            logger.info(
                f"Successfully uploaded parquet file to s3://{self.bucket_name}/{key}"
            )
            return

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @s3_retry
    def upload_json_object(self, data: Dict[str, Any], key: str) -> None:
        """Upload dictionary as JSON object to S3.

        Args:
            data: Dictionary to upload as JSON
            key: S3 object key

        Raises:
            S3Error: If upload fails after retries
        """
        json_content = json.dumps(data, indent=2, default=str)

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=json_content,
            ContentType="application/json",
        )

        logger.info(
            f"Successfully uploaded JSON object to s3://{self.bucket_name}/{key}"
        )

    def object_exists(self, key: str) -> bool:
        """Check if an object exists in S3.

        Args:
            key: S3 object key to check

        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            # Re-raise other errors
            raise S3Error(f"Error checking if object exists '{key}': {e!s}") from e
