"""Unit tests for CheckpointStore component.

This module contains unit tests for the CheckpointStore class, testing
S3 checkpoint file operations with mocked S3 interactions.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError
from polars import DataFrame
from polars.exceptions import ComputeError


class TestCheckpointStore:
    """Unit tests for CheckpointStore component."""

    def setup_method(self):
        """Set up test fixtures."""
        self.bucket = "test-checkpoint-bucket"
        self.key = "checkpoints/test-checkpoint.parquet"

    @patch("boto3.client")
    def test_exists_with_existing_file(self, mock_boto3_client):
        """Test exists returns True when file exists in S3."""
        # Import here to avoid import issues during test discovery
        from checkpoint_lambda.checkpoint_store import CheckpointStore

        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        # Mock successful head_object call (file exists)
        mock_s3.head_object.return_value = {"ContentLength": 1024}

        store = CheckpointStore(self.bucket, self.key)
        result = store.exists()

        assert result is True
        mock_s3.head_object.assert_called_once_with(Bucket=self.bucket, Key=self.key)

    @patch("boto3.client")
    def test_exists_with_non_existing_file(self, mock_boto3_client):
        """Test exists returns False when file does not exist in S3."""
        # Import here to avoid import issues during test discovery
        from checkpoint_lambda.checkpoint_store import CheckpointStore

        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        # Mock head_object raising NoSuchKey error (file doesn't exist)
        mock_s3.head_object.side_effect = ClientError(
            error_response={"Error": {"Code": "NoSuchKey"}}, operation_name="HeadObject"
        )

        store = CheckpointStore(self.bucket, self.key)
        result = store.exists()

        assert result is False
        mock_s3.head_object.assert_called_once_with(Bucket=self.bucket, Key=self.key)

    @patch("boto3.client")
    def test_exists_with_access_denied(self, mock_boto3_client):
        """Test exists raises CheckpointError for access denied errors."""
        # Import here to avoid import issues during test discovery
        from checkpoint_lambda.checkpoint_store import CheckpointError, CheckpointStore

        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        # Mock head_object raising AccessDenied error
        # CheckpointStore should wrap this in a CheckpointError
        mock_s3.head_object.side_effect = ClientError(
            error_response={"Error": {"Code": "AccessDenied"}},
            operation_name="HeadObject",
        )

        store = CheckpointStore(self.bucket, self.key)

        with pytest.raises(CheckpointError):
            store.exists()

    @patch("boto3.client")
    @patch("checkpoint_lambda.checkpoint_store.read_parquet")
    def test_load_with_valid_parquet_file(self, mock_read_parquet, mock_boto3_client):
        """Test load successfully reads parquet file from S3 and returns
        Checkpoint."""
        # Import here to avoid import issues during test discovery
        from checkpoint_lambda.checkpoint import Checkpoint
        from checkpoint_lambda.checkpoint_store import CheckpointStore

        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        # Create sample DataFrame that would be returned from parquet
        sample_data = {
            "action": ["submit", "pass-qc"],
            "ptid": ["ABC123", "XYZ789"],
            "timestamp": [
                datetime(2024, 1, 15, 10, 0, 0),
                datetime(2024, 1, 16, 11, 0, 0),
            ],
        }
        expected_df = DataFrame(sample_data)
        mock_read_parquet.return_value = expected_df

        store = CheckpointStore(self.bucket, self.key)
        result = store.load()

        # Verify the result
        assert result is not None
        assert isinstance(result, Checkpoint)

        # Verify S3 URI was constructed correctly
        expected_s3_uri = f"s3://{self.bucket}/{self.key}"
        mock_read_parquet.assert_called_once_with(expected_s3_uri)

    @patch("boto3.client")
    @patch("checkpoint_lambda.checkpoint_store.read_parquet")
    def test_load_with_non_existing_file(self, mock_read_parquet, mock_boto3_client):
        """Test load returns None when file does not exist."""
        # Import here to avoid import issues during test discovery
        from checkpoint_lambda.checkpoint_store import CheckpointStore

        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        # Mock polars raising FileNotFoundError (file doesn't exist)
        mock_read_parquet.side_effect = FileNotFoundError("No such file")

        store = CheckpointStore(self.bucket, self.key)
        result = store.load()

        assert result is None

    @patch("boto3.client")
    @patch("checkpoint_lambda.checkpoint_store.read_parquet")
    def test_load_with_corrupted_file(self, mock_read_parquet, mock_boto3_client):
        """Test load raises CheckpointError for corrupted parquet files."""
        # Import here to avoid import issues during test discovery
        from checkpoint_lambda.checkpoint_store import CheckpointError, CheckpointStore

        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        # Mock polars raising a ComputeError for corrupted file
        # CheckpointStore should wrap this in a CheckpointError
        mock_read_parquet.side_effect = ComputeError("Corrupted parquet file")

        store = CheckpointStore(self.bucket, self.key)

        with pytest.raises(CheckpointError):
            store.load()

    @patch("boto3.client")
    def test_save_with_valid_checkpoint(self, mock_boto3_client):
        """Test save successfully writes checkpoint to S3 as parquet."""
        # Import here to avoid import issues during test discovery
        from checkpoint_lambda.checkpoint import Checkpoint
        from checkpoint_lambda.checkpoint_store import CheckpointStore

        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        # Create sample checkpoint
        sample_data = {
            "action": ["submit", "pass-qc"],
            "ptid": ["ABC123", "XYZ789"],
            "timestamp": [
                datetime(2024, 1, 15, 10, 0, 0),
                datetime(2024, 1, 16, 11, 0, 0),
            ],
        }
        df = DataFrame(sample_data)
        checkpoint = Checkpoint(df)

        # Mock polars write_parquet function instead of the property
        with patch("polars.DataFrame.write_parquet") as mock_write_parquet:
            store = CheckpointStore(self.bucket, self.key)
            result = store.save(checkpoint)

            # Verify the result is the S3 URI
            expected_s3_uri = f"s3://{self.bucket}/{self.key}"
            assert result == expected_s3_uri

            # Verify write_parquet was called with correct S3 URI
            mock_write_parquet.assert_called_once_with(expected_s3_uri)

    @patch("boto3.client")
    def test_save_with_empty_checkpoint(self, mock_boto3_client):
        """Test save successfully writes empty checkpoint to S3."""
        # Import here to avoid import issues during test discovery
        from checkpoint_lambda.checkpoint import Checkpoint
        from checkpoint_lambda.checkpoint_store import CheckpointStore

        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        # Create empty checkpoint
        checkpoint = Checkpoint.empty()

        # Mock polars write_parquet function
        with patch("polars.DataFrame.write_parquet") as mock_write_parquet:
            store = CheckpointStore(self.bucket, self.key)
            result = store.save(checkpoint)

            # Verify the result is the S3 URI
            expected_s3_uri = f"s3://{self.bucket}/{self.key}"
            assert result == expected_s3_uri

            # Verify write_parquet was called
            mock_write_parquet.assert_called_once_with(expected_s3_uri)

    @patch("boto3.client")
    def test_save_with_s3_error(self, mock_boto3_client):
        """Test save raises CheckpointError when S3 write fails."""
        # Import here to avoid import issues during test discovery
        from checkpoint_lambda.checkpoint import Checkpoint
        from checkpoint_lambda.checkpoint_store import CheckpointError, CheckpointStore

        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3_client.return_value = mock_s3

        # Create sample checkpoint
        checkpoint = Checkpoint.empty()

        # Mock polars write_parquet function to raise error
        with patch("polars.DataFrame.write_parquet") as mock_write_parquet:
            mock_write_parquet.side_effect = ClientError(
                error_response={"Error": {"Code": "AccessDenied"}},
                operation_name="PutObject",
            )

            store = CheckpointStore(self.bucket, self.key)

            with pytest.raises(CheckpointError):
                store.save(checkpoint)
