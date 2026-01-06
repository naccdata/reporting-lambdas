"""CheckpointStore component for reading and writing S3 checkpoint files.

This module provides the CheckpointStore class for managing checkpoint
parquet files in S3 storage, combining read and write operations.
"""

from typing import Optional

import boto3
from botocore.exceptions import ClientError
from polars import read_parquet
from polars.exceptions import ComputeError, PolarsError

from checkpoint_lambda.checkpoint import Checkpoint


class CheckpointError(Exception):
    """Exception raised for checkpoint-related errors.

    This exception wraps underlying storage or parsing errors to provide
    a consistent interface for checkpoint operations.
    """

    pass


class CheckpointStore:
    """Handles reading and writing checkpoints to/from S3 storage."""

    def __init__(self, bucket: str, key: str):
        """Initialize with S3 checkpoint location.

        Args:
            bucket: S3 bucket name containing checkpoint file
            key: S3 key for checkpoint file
        """
        self.bucket = bucket
        self.key = key
        self.s3_client = boto3.client("s3")

    def exists(self) -> bool:
        """Check if a checkpoint exists in S3.

        Returns:
            True if checkpoint file exists in S3

        Raises:
            CheckpointError: For S3 access errors other than NoSuchKey
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=self.key)
            return True
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                return False
            else:
                raise CheckpointError(f"S3 access error: {e}") from e

    def load(self) -> Optional[Checkpoint]:
        """Load checkpoint from S3.

        Returns:
            Checkpoint object containing previous events. None if none exists

        Raises:
            CheckpointError: If checkpoint file exists but is corrupted
        """
        try:
            s3_uri = f"s3://{self.bucket}/{self.key}"
            df = read_parquet(s3_uri)

            return Checkpoint(df)

        except FileNotFoundError:
            # File doesn't exist, return None for first run
            return None
        except (ComputeError, PolarsError) as e:
            # Polars-specific errors (corrupted file, schema issues, etc.)
            raise CheckpointError(f"Failed to load checkpoint: {e}") from e
        except ClientError as e:
            # S3-specific errors (permissions, network, etc.)
            raise CheckpointError(f"S3 error loading checkpoint: {e}") from e

    def save(self, checkpoint: Checkpoint) -> str:
        """Save checkpoint to S3 as parquet file.

        Args:
            checkpoint: Checkpoint object to save

        Returns:
            S3 URI of written checkpoint file (s3://bucket/key)

        Raises:
            CheckpointError: If S3 write operation fails
        """
        try:
            s3_uri = f"s3://{self.bucket}/{self.key}"
            checkpoint.dataframe.write_parquet(s3_uri)
            return s3_uri
        except (ComputeError, PolarsError) as e:
            # Polars-specific errors (write failures, schema issues, etc.)
            raise CheckpointError(f"Failed to write parquet: {e}") from e
        except ClientError as e:
            # S3-specific errors (permissions, network, etc.)
            raise CheckpointError(f"S3 error saving checkpoint: {e}") from e
