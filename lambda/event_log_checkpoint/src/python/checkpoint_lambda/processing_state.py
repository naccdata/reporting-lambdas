"""Processing state for tracking the LastModified high-water mark.

This module provides the ProcessingState class for reading and writing
a small JSON state file in S3 that records the maximum LastModified
timestamp of files successfully processed by the lambda.

The high-water mark is used as the since_timestamp cutoff for subsequent
runs, ensuring files are processed in LastModified order without gaps.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ProcessingState:
    """Manages the processing high-water mark state file in S3.

    The state file is a simple JSON object:
        {"max_processed_last_modified": "2026-07-05T14:30:00+00:00"}

    This tracks the maximum S3 LastModified timestamp across all files
    that have been successfully processed, allowing subsequent runs to
    skip already-processed files.
    """

    def __init__(self, bucket: str, key: str):
        """Initialize with S3 location of the state file.

        Args:
            bucket: S3 bucket containing the state file
            key: S3 key for the state file
        """
        self.bucket = bucket
        self.key = key
        self.s3_client = boto3.client("s3")

    def read(self) -> Optional[datetime]:
        """Read the high-water mark from the state file.

        Returns:
            The max_processed_last_modified datetime (timezone-aware UTC),
            or None if the state file does not exist.

        Raises:
            ClientError: For S3 errors other than missing file.
            ValueError: If the state file content is malformed.
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=self.key)
            content = response["Body"].read().decode("utf-8")
            data = json.loads(content)

            raw_ts = data.get("max_processed_last_modified")
            if raw_ts is None:
                return None

            ts = datetime.fromisoformat(raw_ts)
            # Ensure timezone-aware
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ("NoSuchKey", "NoSuchBucket", "404"):
                return None
            raise
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise ValueError(
                f"Malformed processing state file s3://{self.bucket}/{self.key}: {e}"
            ) from e

    def write(self, max_last_modified: datetime) -> None:
        """Write the high-water mark to the state file.

        Only advances the mark forward. If the existing mark is already
        >= the provided value, the write is skipped.

        Args:
            max_last_modified: The new high-water mark to write.
                Must be timezone-aware.
        """
        # Ensure timezone-aware
        if max_last_modified.tzinfo is None:
            max_last_modified = max_last_modified.replace(tzinfo=timezone.utc)

        # Read current state to avoid moving the mark backward
        current = self.read()
        if current is not None and current >= max_last_modified:
            logger.info(
                "High-water mark not advanced (current >= new)",
                extra={
                    "current": current.isoformat(),
                    "new": max_last_modified.isoformat(),
                },
            )
            return

        data = {
            "max_processed_last_modified": (max_last_modified.isoformat()),
        }
        body = json.dumps(data, indent=2)

        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=self.key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
        )

        logger.info(
            "Updated processing state high-water mark",
            extra={
                "bucket": self.bucket,
                "key": self.key,
                "max_processed_last_modified": (max_last_modified.isoformat()),
            },
        )
