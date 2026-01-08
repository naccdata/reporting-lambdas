"""S3 operations with retry logic and error handling."""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

import boto3
import polars as pl
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class S3Error(Exception):
    """Exception raised for S3 operation errors."""

    pass


class S3Manager:
    """S3 operations with retry logic and error handling."""

    def __init__(
        self, bucket_name: str, region: str = "us-east-1", max_retries: int = 3
    ):
        """Initialize S3Manager.

        Args:
            bucket_name: Name of the S3 bucket
            region: AWS region
            max_retries: Maximum number of retry attempts
        """
        self.bucket_name = bucket_name
        self.region = region
        self.max_retries = max_retries

        try:
            self.s3_client = boto3.client("s3", region_name=region)
        except NoCredentialsError as e:
            raise S3Error(f"AWS credentials not found: {e!s}") from e

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
        for attempt in range(self.max_retries + 1):
            try:
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

            except ClientError as e:
                if attempt == self.max_retries:
                    error_msg = f"Failed to list objects with prefix '{prefix}': {e!s}"
                    logger.error(error_msg)
                    raise S3Error(error_msg) from e

                wait_time = 2**attempt
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e!s}"
                )
                time.sleep(wait_time)

        # This should never be reached due to the loop structure, but added for
        # type safety
        raise S3Error(
            f"Failed to list objects with prefix '{prefix}' after "
            f"{self.max_retries} retries"
        )

    def download_json_object(self, key: str) -> Dict[str, Any]:
        """Download and parse JSON object from S3.

        Args:
            key: S3 object key

        Returns:
            Parsed JSON data as dictionary

        Raises:
            S3Error: If download or parsing fails after retries
        """
        for attempt in range(self.max_retries + 1):
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                content = response["Body"].read().decode("utf-8")
                data = json.loads(content)

                logger.debug(f"Successfully downloaded JSON object: {key}")
                return data

            except ClientError as e:
                if attempt == self.max_retries:
                    error_msg = f"Failed to download object '{key}': {e!s}"
                    logger.error(error_msg)
                    raise S3Error(error_msg) from e

                wait_time = 2**attempt
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e!s}"
                )
                time.sleep(wait_time)
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse JSON from object '{key}': {e!s}"
                logger.error(error_msg)
                raise S3Error(error_msg) from e

        # This should never be reached due to the loop structure, but added for
        # type safety
        raise S3Error(
            f"Failed to download object '{key}' after {self.max_retries} retries"
        )

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
        import os
        import tempfile

        for attempt in range(self.max_retries + 1):
            try:
                # Write DataFrame to temporary parquet file
                with tempfile.NamedTemporaryFile(
                    suffix=".parquet", delete=False
                ) as tmp_file:
                    tmp_path = tmp_file.name

                try:
                    df.write_parquet(
                        tmp_path, compression=compression, use_pyarrow=True
                    )

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

            except Exception as e:
                if attempt == self.max_retries:
                    error_msg = f"Failed to upload parquet file to '{key}': {e!s}"
                    logger.error(error_msg)
                    raise S3Error(error_msg) from e

                wait_time = 2**attempt
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e!s}"
                )
                time.sleep(wait_time)

    def upload_json_object(self, data: Dict[str, Any], key: str) -> None:
        """Upload dictionary as JSON object to S3.

        Args:
            data: Dictionary to upload as JSON
            key: S3 object key

        Raises:
            S3Error: If upload fails after retries
        """
        for attempt in range(self.max_retries + 1):
            try:
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
                return

            except Exception as e:
                if attempt == self.max_retries:
                    error_msg = f"Failed to upload JSON object to '{key}': {e!s}"
                    logger.error(error_msg)
                    raise S3Error(error_msg) from e

                wait_time = 2**attempt
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e!s}"
                )
                time.sleep(wait_time)

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
