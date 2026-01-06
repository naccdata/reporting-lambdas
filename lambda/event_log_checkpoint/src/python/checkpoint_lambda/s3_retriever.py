"""S3 event retriever for processing event log files.

This module contains the S3EventRetriever class that handles S3
operations for event log retrieval, timestamp filtering, and validation
using VisitEvent Pydantic model directly.
"""

import json
import re
from datetime import datetime
from typing import List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError
from pydantic import ValidationError

from checkpoint_lambda.models import VisitEvent


class S3EventRetriever:
    """Repository for retrieving VisitEvent objects from S3 storage.

    This repository handles:
    - Listing event files matching the configured pattern
    - Retrieving and validating events as VisitEvent domain objects
    - Filtering events by timestamp for incremental processing
    - Collecting validation errors for logging
    """

    # Default pattern:
    #  log-{action}-{YYYYMMDD-HHMMSS}-{adcid}-{project}-{ptid}-{visitnum}.json
    DEFAULT_PATTERN = re.compile(
        r"^.*log-(submit|pass-qc|not-pass-qc|delete)-\d{8}-\d{6}-\d+-[\w\-]+-[\w]+-[\w]+\.json$"
    )

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        since_timestamp: Optional[datetime] = None,
        file_pattern: Optional[re.Pattern] = None,
    ):
        """Initialize with S3 bucket, optional prefix, and cutoff timestamp.

        Args:
            bucket: S3 bucket name
            prefix: Optional S3 prefix to filter paths
            since_timestamp: Only retrieve events with timestamp > this value
            file_pattern: Optional regex pattern for matching files
                          (default DEFAULT_PATTERN)
        """
        self.bucket = bucket
        self.prefix = prefix
        self.since_timestamp = since_timestamp
        self.file_pattern = file_pattern or self.DEFAULT_PATTERN

    def list_event_files(self) -> List[str]:
        """List event files matching the configured pattern.

        Returns:
            List of S3 keys matching the configured file pattern

        Raises:
            ClientError: If S3 access fails
        """
        s3_client = boto3.client("s3")

        matching_files = []

        # List objects from S3
        response = s3_client.list_objects_v2(Bucket=self.bucket, Prefix=self.prefix)

        # Filter files that match the configured pattern
        if "Contents" in response:
            for obj in response["Contents"]:
                key = obj["Key"]
                if self.file_pattern.match(key):
                    matching_files.append(key)

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

    def should_process_event(self, event: VisitEvent) -> bool:
        """Determine if event should be processed based on timestamp.

        Args:
            event: VisitEvent object

        Returns:
            True if event should be processed (timestamp > since_timestamp or no filter)
        """
        # If no timestamp filter is set, process all events
        if self.since_timestamp is None:
            return True

        # Only process events with timestamp > since_timestamp
        return event.timestamp > self.since_timestamp

    def retrieve_and_validate_events(
        self,
    ) -> Tuple[List[VisitEvent], List[dict[str, str]]]:
        """Retrieve all new event files, validate them, and return results.

        This method handles the complete retrieval and validation pipeline:
        - Lists event files matching the pattern
        - Retrieves and validates each file as VisitEvent objects
        - Filters by timestamp if since_timestamp is set
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
        valid_events = []
        validation_errors = []

        # List all matching event files
        try:
            event_files = self.list_event_files()
        except ClientError:
            # Re-raise S3 listing errors as they prevent processing
            raise

        # Process each file
        for file_key in event_files:
            try:
                # Retrieve and validate event from S3
                visit_event = self.retrieve_event(file_key)

                # Check if event should be processed based on timestamp
                if not self.should_process_event(visit_event):
                    continue

                valid_events.append(visit_event)

            except ClientError as e:
                # S3 access error - log and continue
                validation_errors.append(
                    {"source_key": file_key, "errors": f"S3 error: {e}"}
                )

            except json.JSONDecodeError as e:
                # JSON parsing error - log and continue
                validation_errors.append(
                    {"source_key": file_key, "errors": f"JSON decode error: {e}"}
                )

            except ValidationError as e:
                # Pydantic validation error - log and continue
                validation_errors.append(
                    {"source_key": file_key, "errors": str(e.errors())}
                )

        return valid_events, validation_errors
