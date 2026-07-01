"""S3 event retriever for processing event log files.

This module contains the S3EventRetriever class that handles S3
operations for event log retrieval and validation using VisitEvent
Pydantic model directly.
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Optional, Tuple, Union

import boto3
from botocore.exceptions import ClientError
from pydantic import ValidationError

from checkpoint_lambda.models import VisitEvent


class S3EventRetriever:
    """Repository for retrieving VisitEvent objects from S3 storage.

    This repository handles:
    - Listing event files matching the configured pattern
    - Retrieving and validating events as VisitEvent domain objects
    - Collecting validation errors for logging
    - Limiting files per invocation to ensure progress within timeouts
    """

    # Default pattern:
    #  log-{action}-{YYYYMMDD-HHMMSS}-{adcid}-{project}-{ptid}-{visit_date}.json
    #  where visit_date is YYYY-MM-DD
    DEFAULT_PATTERN = re.compile(
        r"^.*log-(submit|pass-qc|not-pass-qc|delete)"
        r"-\d{8}-\d{6}-\d+-[\w\-]+-[\w]+-\d{4}-\d{2}-\d{2}\.json$"
    )

    DEFAULT_MAX_WORKERS = 50
    DEFAULT_MAX_FILES = 5000

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        since_timestamp: Optional[datetime] = None,
        file_pattern: Optional[re.Pattern] = None,
        max_workers: Optional[int] = None,
        max_files: Optional[int] = None,
    ):
        """Initialize with S3 bucket, optional prefix, and cutoff timestamp.

        Args:
            bucket: S3 bucket name
            prefix: Optional S3 prefix to filter paths
            since_timestamp: Only retrieve events with timestamp > this value
            file_pattern: Optional regex pattern for matching files
                          (default DEFAULT_PATTERN)
            max_workers: Max concurrent S3 fetch threads
                         (default DEFAULT_MAX_WORKERS)
            max_files: Max number of files to retrieve per invocation
                       (default DEFAULT_MAX_FILES). Limits work per run
                       so the lambda makes incremental progress within
                       its timeout.
        """
        self.bucket = bucket
        self.prefix = prefix
        self.since_timestamp = since_timestamp
        self.file_pattern = file_pattern or self.DEFAULT_PATTERN
        self.max_workers = max_workers or self.DEFAULT_MAX_WORKERS
        self.max_files = max_files or self.DEFAULT_MAX_FILES

    def list_event_files(self) -> List[str]:
        """List event files matching the configured pattern.

        Paginates through S3 results, filtering by the file pattern and
        by S3 LastModified date when a since_timestamp is configured.
        Stops after collecting max_files matching files to bound work
        per invocation.

        Returns:
            List of S3 keys matching the configured file pattern,
            up to max_files entries

        Raises:
            ClientError: If S3 access fails
        """
        s3_client = boto3.client("s3")
        paginator = s3_client.get_paginator("list_objects_v2")

        matching_files: List[str] = []

        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.prefix):
            if "Contents" not in page:
                continue
            for obj in page["Contents"]:
                key = obj["Key"]
                if not self.file_pattern.match(key):
                    continue

                # Use S3 LastModified as a cheap pre-filter to skip
                # files that were uploaded before the cutoff timestamp.
                # This is safe because a file cannot be uploaded before
                # the event it contains occurred, so LastModified is
                # always >= the event timestamp inside.  We use strict
                # less-than so boundary cases are still downloaded and
                # validated after parsing.
                if self.since_timestamp is not None:
                    last_modified = obj["LastModified"]
                    # LastModified is timezone-aware (UTC) from boto3
                    if last_modified < self.since_timestamp:
                        continue

                matching_files.append(key)

                if len(matching_files) >= self.max_files:
                    return matching_files

        return matching_files

    def retrieve_event(self, key: str) -> VisitEvent:
        """Retrieve and validate event from S3.

        Args:
            key: S3 key of the event file

        Returns:
            Validated VisitEvent object

        Raises:
            ClientError: If S3 access fails
            json.JSONDecodeError: If JSON parsing fails
            ValidationError: If event validation fails
        """
        s3_client = boto3.client("s3")

        # Get object from S3
        response = s3_client.get_object(Bucket=self.bucket, Key=key)

        # Read and parse JSON content
        content = response["Body"].read()
        event_data = json.loads(content)

        # Validate and return VisitEvent object
        return VisitEvent.model_validate(event_data)

    def _fetch_and_validate(self, key: str) -> Union[VisitEvent, dict[str, str]]:
        """Fetch and validate a single event file from S3.

        Thread-safe: creates its own S3 client per call.

        Args:
            key: S3 key of the event file

        Returns:
            VisitEvent on success, or error dict on failure
        """
        try:
            return self.retrieve_event(key)
        except ClientError as e:
            return {
                "source_key": key,
                "errors": f"S3 error: {e}",
            }
        except json.JSONDecodeError as e:
            return {
                "source_key": key,
                "errors": f"JSON decode error: {e}",
            }
        except ValidationError as e:
            return {
                "source_key": key,
                "errors": str(e.errors()),
            }

    def retrieve_and_validate_events(
        self,
    ) -> Tuple[List[VisitEvent], List[dict[str, str]]]:
        """Retrieve all new event files, validate them, and return results.

        Uses concurrent threads for parallel S3 fetches to handle
        large file counts (20k+) within Lambda timeout limits.

        This method handles the complete retrieval and validation pipeline:
        - Lists event files matching the pattern
        - Retrieves and validates each file as VisitEvent objects
        - Collects validation errors for logging

        Returns:
            Tuple of (valid_events, validation_errors)
            - valid_events: List of successfully validated VisitEvent objects
            - validation_errors: List of error dicts with keys:
                - source_key: S3 key of failed event
                - errors: Error details

        Raises:
            ClientError: If S3 listing fails
            (retrieval errors are collected, not raised)
        """
        valid_events: List[VisitEvent] = []
        validation_errors: List[dict[str, str]] = []

        # List all matching event files
        try:
            event_files = self.list_event_files()
        except ClientError:
            raise

        if not event_files:
            return valid_events, validation_errors

        # Process files concurrently
        with ThreadPoolExecutor(
            max_workers=min(self.max_workers, len(event_files))
        ) as executor:
            future_to_key = {
                executor.submit(self._fetch_and_validate, key): key
                for key in event_files
            }

            for future in as_completed(future_to_key):
                result = future.result()
                if isinstance(result, VisitEvent):
                    valid_events.append(result)
                elif isinstance(result, dict):
                    validation_errors.append(result)

        return valid_events, validation_errors
