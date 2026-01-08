# Data Processing Module Usage

The `common.data_processing` module provides utilities for data validation, transformation, and parquet file generation. This module standardizes data processing patterns across all reporting lambdas.

## Components

### ParquetWriter

Standardized parquet file creation with compression and schema validation.

#### Usage

```python
from common.data_processing import ParquetWriter
import polars as pl

# Initialize with default settings
writer = ParquetWriter()

# Initialize with custom compression
writer = ParquetWriter(compression="gzip")

# Write DataFrame to parquet
df = pl.DataFrame({
    "id": [1, 2, 3],
    "name": ["Alice", "Bob", "Charlie"],
    "timestamp": ["2024-01-01T10:00:00Z", "2024-01-01T11:00:00Z", "2024-01-01T12:00:00Z"]
})

writer.write_dataframe(df, "output.parquet")
```

#### Methods

##### `__init__(compression: str = "snappy", schema: Optional[Schema] = None)`

Initialize ParquetWriter with optional compression and schema validation.

**Parameters:**
- `compression`: Compression algorithm ("snappy", "gzip", "lz4", "zstd")
- `schema`: Optional Polars schema for validation

**Example:**
```python
import polars as pl

# With schema validation
schema = {
    "id": pl.Int64,
    "name": pl.Utf8,
    "timestamp": pl.Datetime
}
writer = ParquetWriter(compression="gzip", schema=schema)
```

##### `write_dataframe(df: pl.DataFrame, output_path: str) -> None`

Write DataFrame to parquet file with configured compression.

**Parameters:**
- `df`: Polars DataFrame to write
- `output_path`: Local file path for output

**Raises:**
- `ValueError`: If DataFrame doesn't match configured schema
- `IOError`: If file cannot be written

**Example:**
```python
try:
    writer.write_dataframe(df, "/tmp/output.parquet")
    logger.info("Parquet file written successfully")
except ValueError as e:
    logger.error("Schema validation failed", extra={"error": str(e)})
```

##### `append_to_parquet(df: pl.DataFrame, existing_path: str) -> None`

Append DataFrame to existing parquet file.

**Parameters:**
- `df`: DataFrame to append
- `existing_path`: Path to existing parquet file

**Example:**
```python
# Append new data to existing file
new_data = pl.DataFrame({"id": [4], "name": ["David"]})
writer.append_to_parquet(new_data, "existing.parquet")
```

### DataValidator

Common validation patterns for reporting data.

#### Usage

```python
from common.data_processing import DataValidator
from common.models import ReportingEvent
from pydantic import ValidationError

validator = DataValidator()

# Validate single record
data = {
    "timestamp": "2024-01-01T10:00:00Z",
    "source": "api",
    "event_type": "user_action",
    "data": {"user_id": 123}
}

try:
    result = validator.validate_schema(data, ReportingEvent)
    if result.is_valid:
        logger.info("Validation passed")
    else:
        logger.warning("Validation failed", extra={"errors": result.errors})
except ValidationError as e:
    logger.error("Validation error", extra={"error": str(e)})
```

#### Methods

##### `validate_schema(data: Dict[str, Any], schema: BaseModel) -> ValidationResult`

Validate single record against Pydantic model.

**Parameters:**
- `data`: Dictionary to validate
- `schema`: Pydantic model class

**Returns:**
- `ValidationResult`: Object with `is_valid`, `validated_data`, and `errors` attributes

**Example:**
```python
from common.models import ProcessingMetrics

metrics_data = {
    "start_time": "2024-01-01T10:00:00Z",
    "end_time": "2024-01-01T10:05:00Z",
    "records_processed": 100,
    "records_failed": 2
}

result = validator.validate_schema(metrics_data, ProcessingMetrics)
if result.is_valid:
    metrics = result.validated_data
    logger.info("Processing completed", extra={
        "duration": metrics.duration_seconds,
        "success_rate": metrics.success_rate
    })
```

##### `validate_batch(data_batch: List[Dict[str, Any]], schema: BaseModel) -> BatchValidationResult`

Validate multiple records against schema.

**Parameters:**
- `data_batch`: List of dictionaries to validate
- `schema`: Pydantic model class

**Returns:**
- `BatchValidationResult`: Object with `valid_records`, `invalid_records`, and `error_summary`

**Example:**
```python
batch_data = [
    {"timestamp": "2024-01-01T10:00:00Z", "source": "api", "event_type": "login"},
    {"timestamp": "invalid", "source": "api", "event_type": "logout"},  # Invalid
    {"timestamp": "2024-01-01T10:02:00Z", "source": "web", "event_type": "click"}
]

batch_result = validator.validate_batch(batch_data, ReportingEvent)

logger.info("Batch validation completed", extra={
    "valid_count": len(batch_result.valid_records),
    "invalid_count": len(batch_result.invalid_records),
    "error_summary": batch_result.error_summary
})

# Process valid records
for valid_record in batch_result.valid_records:
    # Process the validated ReportingEvent object
    process_event(valid_record)
```

## Best Practices

### Schema Validation

1. **Always validate external data:**
   ```python
   # Validate data from APIs, files, etc.
   result = validator.validate_schema(external_data, ExpectedSchema)
   if not result.is_valid:
       logger.warning("Invalid data received", extra={"errors": result.errors})
       return
   ```

2. **Use batch validation for performance:**
   ```python
   # More efficient for large datasets
   batch_result = validator.validate_batch(large_dataset, Schema)
   # Process valid records, log invalid ones
   ```

### Parquet Generation

1. **Use appropriate compression:**
   ```python
   # Snappy: Fast compression/decompression (default)
   writer = ParquetWriter(compression="snappy")
   
   # Gzip: Better compression ratio, slower
   writer = ParquetWriter(compression="gzip")
   ```

2. **Validate schema before writing:**
   ```python
   schema = {
       "timestamp": pl.Datetime,
       "value": pl.Float64,
       "category": pl.Utf8
   }
   writer = ParquetWriter(schema=schema)
   ```

3. **Handle large datasets efficiently:**
   ```python
   # Process in chunks for large datasets
   chunk_size = 10000
   for i in range(0, len(large_df), chunk_size):
       chunk = large_df[i:i + chunk_size]
       if i == 0:
           writer.write_dataframe(chunk, output_path)
       else:
           writer.append_to_parquet(chunk, output_path)
   ```

### Error Handling

```python
from common.utils.error_handling import handle_processing_error

try:
    writer.write_dataframe(df, output_path)
except Exception as e:
    return handle_processing_error(e, request_id)
```

## Performance Tips

1. **Use Polars for data processing** - Much faster than Pandas for large datasets
2. **Choose compression wisely** - Snappy for speed, Gzip for size
3. **Validate in batches** - More efficient than individual validation
4. **Stream large files** - Don't load entire datasets into memory

## Common Patterns

### Incremental Processing

```python
from datetime import datetime
import polars as pl

def process_incremental_data(new_data: List[Dict], checkpoint_path: str):
    """Process new data and merge with existing checkpoint."""
    
    # Validate new data
    validator = DataValidator()
    batch_result = validator.validate_batch(new_data, ReportingEvent)
    
    if not batch_result.valid_records:
        logger.warning("No valid records to process")
        return
    
    # Convert to DataFrame
    new_df = pl.DataFrame([record.model_dump() for record in batch_result.valid_records])
    
    # Merge with existing data
    writer = ParquetWriter()
    if os.path.exists(checkpoint_path):
        writer.append_to_parquet(new_df, checkpoint_path)
    else:
        writer.write_dataframe(new_df, checkpoint_path)
    
    logger.info("Incremental processing completed", extra={
        "new_records": len(batch_result.valid_records),
        "failed_records": len(batch_result.invalid_records)
    })
```

### Data Quality Reporting

```python
def generate_data_quality_report(df: pl.DataFrame) -> Dict[str, Any]:
    """Generate data quality metrics for a DataFrame."""
    
    total_rows = len(df)
    
    quality_report = {
        "total_rows": total_rows,
        "null_counts": {},
        "duplicate_rows": df.is_duplicated().sum(),
        "data_types": {}
    }
    
    # Check null values per column
    for column in df.columns:
        null_count = df[column].null_count()
        quality_report["null_counts"][column] = {
            "count": null_count,
            "percentage": (null_count / total_rows) * 100 if total_rows > 0 else 0
        }
    
    # Data type information
    for column, dtype in zip(df.columns, df.dtypes):
        quality_report["data_types"][column] = str(dtype)
    
    return quality_report
```

## Testing

### Unit Testing

```python
import pytest
import polars as pl
from common.data_processing import ParquetWriter, DataValidator

def test_parquet_writer():
    """Test ParquetWriter functionality."""
    writer = ParquetWriter()
    df = pl.DataFrame({"id": [1, 2], "name": ["A", "B"]})
    
    with tempfile.NamedTemporaryFile(suffix='.parquet') as f:
        writer.write_dataframe(df, f.name)
        
        # Verify file was created and can be read
        read_df = pl.read_parquet(f.name)
        assert len(read_df) == 2
        assert read_df.columns == ["id", "name"]

def test_data_validator():
    """Test DataValidator functionality."""
    validator = DataValidator()
    
    valid_data = {
        "timestamp": "2024-01-01T10:00:00Z",
        "source": "test",
        "event_type": "test_event",
        "data": {}
    }
    
    result = validator.validate_schema(valid_data, ReportingEvent)
    assert result.is_valid
    assert isinstance(result.validated_data, ReportingEvent)
```

### Property-Based Testing

```python
from hypothesis import given, strategies as st

@given(
    df=st.builds(
        pl.DataFrame,
        {"id": st.lists(st.integers(), min_size=1, max_size=100)}
    )
)
def test_parquet_round_trip(df):
    """Property: Writing then reading parquet should preserve data."""
    writer = ParquetWriter()
    
    with tempfile.NamedTemporaryFile(suffix='.parquet') as f:
        writer.write_dataframe(df, f.name)
        read_df = pl.read_parquet(f.name)
        
        assert len(read_df) == len(df)
        assert read_df.columns == df.columns
```