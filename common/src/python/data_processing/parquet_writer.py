"""Parquet file writing utilities with compression and schema validation."""

import logging
from pathlib import Path
from typing import Literal, Optional

import polars as pl

logger = logging.getLogger(__name__)


class ParquetWriteError(Exception):
    """Exception raised when parquet writing fails."""

    pass


class ParquetWriter:
    """Standardized parquet file creation with compression and schema
    validation."""

    def __init__(
        self,
        compression: Literal[
            "snappy", "gzip", "lz4", "zstd", "uncompressed"
        ] = "snappy",
        schema: Optional[pl.Schema] = None,
    ):
        """Initialize ParquetWriter.

        Args:
            compression: Compression algorithm to use (snappy, gzip, lz4, zstd,
                uncompressed)
            schema: Optional schema to validate against
        """
        self.compression = compression
        self.schema = schema

    def write_dataframe(self, df: pl.DataFrame, output_path: str) -> None:
        """Write DataFrame to parquet file.

        Args:
            df: Polars DataFrame to write
            output_path: Path where parquet file will be written

        Raises:
            ParquetWriteError: If writing fails
            ValueError: If schema validation fails
        """
        try:
            # Validate schema if provided
            if self.schema is not None:
                self._validate_schema(df)

            # Ensure output directory exists
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)

            # Write parquet file
            df.write_parquet(
                output_path, compression=self.compression, use_pyarrow=True
            )

            logger.info(f"Successfully wrote {len(df)} rows to {output_path}")

        except Exception as e:
            error_msg = f"Failed to write parquet file to {output_path}: {e!s}"
            logger.error(error_msg)
            raise ParquetWriteError(error_msg) from e

    def append_to_parquet(self, df: pl.DataFrame, existing_path: str) -> None:
        """Append DataFrame to existing parquet file.

        Args:
            df: Polars DataFrame to append
            existing_path: Path to existing parquet file

        Raises:
            ParquetWriteError: If appending fails
            ValueError: If schema validation fails
        """
        try:
            existing_path_obj = Path(existing_path)

            if existing_path_obj.exists():
                # Read existing data
                existing_df = pl.read_parquet(existing_path)

                # Validate schemas match
                if set(existing_df.columns) != set(df.columns):
                    raise ValueError(
                        f"Schema mismatch. Existing columns: {existing_df.columns}, "
                        f"New columns: {df.columns}"
                    )

                # Combine dataframes
                combined_df = pl.concat([existing_df, df])
            else:
                combined_df = df

            # Write combined data
            self.write_dataframe(combined_df, existing_path)

        except Exception as e:
            error_msg = f"Failed to append to parquet file {existing_path}: {e!s}"
            logger.error(error_msg)
            raise ParquetWriteError(error_msg) from e

    def _validate_schema(self, df: pl.DataFrame) -> None:
        """Validate DataFrame against expected schema.

        Args:
            df: DataFrame to validate

        Raises:
            ValueError: If schema validation fails
        """
        if self.schema is None:
            return

        # Check column names
        expected_columns = set(self.schema.names())
        actual_columns = set(df.columns)

        if expected_columns != actual_columns:
            missing = expected_columns - actual_columns
            extra = actual_columns - expected_columns

            error_parts = []
            if missing:
                error_parts.append(f"Missing columns: {missing}")
            if extra:
                error_parts.append(f"Extra columns: {extra}")

            raise ValueError(f"Schema validation failed. {', '.join(error_parts)}")

        # Check data types
        for name, expected_dtype in self.schema.items():
            actual_dtype = df[name].dtype
            if actual_dtype != expected_dtype:
                raise ValueError(
                    f"Column '{name}' has incorrect type. "
                    f"Expected: {expected_dtype}, Actual: {actual_dtype}"
                )
