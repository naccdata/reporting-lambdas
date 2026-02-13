# Checkpoint Parquet File Specification

## Overview

The Event Log Checkpoint Lambda creates a consolidated **checkpoint parquet file** that aggregates event log data from multiple JSON files into a single, queryable format optimized for analytical queries.

## File Location

### S3 Configuration

- **S3 Bucket**: Configurable via `CHECKPOINT_BUCKET` environment variable
  - Dev: `nacc-checkpoints-dev`
  - Staging: `nacc-checkpoints-staging`
  - Production: `nacc-checkpoints-prod`
- **S3 Key**: Configurable via `CHECKPOINT_KEY` environment variable
  - Default: `checkpoints/events.parquet`
- **Full Path Example**: `s3://nacc-checkpoints-prod/checkpoints/events.parquet`

## Schema Structure

The parquet file contains 13 columns with the following schema:

| Column | Data Type | Nullable | Description |
|--------|-----------|----------|-------------|
| `action` | String (Utf8) | No | Event type: "submit", "pass-qc", "not-pass-qc", "delete" |
| `study` | String (Utf8) | No | Study identifier (e.g., "adrc", "dvcid", "leads") |
| `pipeline_adcid` | Integer (Int32) | No | Pipeline/center identifier |
| `project_label` | String (Utf8) | No | Flywheel project label |
| `center_label` | String (Utf8) | No | Center/group label |
| `gear_name` | String (Utf8) | No | Gear that logged the event |
| `ptid` | String (Utf8) | No | Participant ID (max 10 characters) |
| `visit_date` | String (Utf8) | No | Visit date in ISO format (YYYY-MM-DD) |
| `visit_number` | String (Utf8) | Yes | Visit number (optional) |
| `datatype` | String (Utf8) | No | Data type (e.g., "form", "dicom") |
| `module` | String (Utf8) | Yes | Module name for forms (optional, required when datatype="form") |
| `packet` | String (Utf8) | Yes | Packet type (optional, e.g., "I", "F") |
| `timestamp` | Datetime (μs, UTC) | No | When the action occurred (timezone-aware UTC) |

### Data Type Details

- **String fields**: UTF-8 encoded strings (Polars `Utf8` type)
- **Integer fields**: 32-bit signed integers (Polars `Int32` type)
- **Datetime fields**: Microsecond precision with UTC timezone (Polars `Datetime("us", time_zone="UTC")`)

## Key Features

### Incremental Updates

The checkpoint file is updated incrementally:

- New events are appended without reprocessing historical data
- Lambda tracks the last processed timestamp
- Only events newer than the last checkpoint are added
- Existing events are preserved

### Data Ordering

- All events are **sorted chronologically** by the `timestamp` field
- Consistent ordering enables efficient time-based queries
- Natural ordering for sequential processing

### Optimized for Analytics

The parquet format provides:

- **Fast columnar queries**: Read only the columns you need
- **Efficient filtering**: Predicate pushdown for fast filtering
- **Compression**: Reduced storage costs (typically 5-10x compression)
- **Direct querying**: Compatible with AWS Athena, Polars, Pandas, DuckDB
- **Schema enforcement**: Type safety and validation

## Supported Analytical Queries

The parquet file is designed to efficiently support these common analytical queries:

### 1. Filter by Center

Get all events for a specific center:

```python
df.filter(pl.col("center_label") == "alpha")
```

### 2. Count by Action Type

Count events by action (e.g., count "not-pass-qc" events):

```python
df.filter(pl.col("action") == "not-pass-qc").height
```

### 3. Filter by Packet Type

Group and filter events by packet field:

```python
df.filter(pl.col("packet") == "I")
df.group_by("packet").agg(pl.len().alias("count"))
```

### 4. Date Range Filtering

Filter by visit_date or timestamp ranges:

```python
# By visit date
df.filter(pl.col("visit_date") >= "2024-01-01")
df.filter(pl.col("visit_date") <= "2024-12-31")

# By timestamp
df.filter(pl.col("timestamp") >= datetime(2024, 1, 1, tzinfo=timezone.utc))
```

### 5. Timing Metrics

Calculate time differences between visit_date and event timestamps:

```python
# Submission timing
submit_events = df.filter(pl.col("action") == "submit")
submit_events.with_columns([
    (pl.col("timestamp").dt.date() - pl.col("visit_date").str.to_date())
    .dt.total_days()
    .alias("days_from_visit_to_submit")
])

# QC timing
qc_events = df.filter(pl.col("action") == "pass-qc")
qc_events.with_columns([
    (pl.col("timestamp").dt.date() - pl.col("visit_date").str.to_date())
    .dt.total_days()
    .alias("days_from_visit_to_qc")
])
```

### 6. Multi-field Grouping

Group by module, packet, and action type for volume analysis:

```python
df.group_by(["module", "packet", "action"]).agg(pl.len().alias("count"))
```

### 7. Combined Filters

Filter by multiple criteria:

```python
df.filter(
    (pl.col("center_label") == "alpha") & 
    (pl.col("action") == "not-pass-qc")
)
```

## Example Data

### Sample Rows

```python
# ADRC form submission
{
    "action": "submit",
    "study": "adrc",
    "pipeline_adcid": 42,
    "project_label": "ingest-form",
    "center_label": "alpha",
    "gear_name": "form-scheduler",
    "ptid": "110001",
    "visit_date": "2024-01-15",
    "visit_number": "01",
    "datatype": "form",
    "module": "UDS",
    "packet": "I",
    "timestamp": "2024-01-15T10:00:00+00:00"
}

# DVCID form with LBD module
{
    "action": "pass-qc",
    "study": "dvcid",
    "pipeline_adcid": 44,
    "project_label": "ingest-form-dvcid",
    "center_label": "beta",
    "gear_name": "form-scheduler",
    "ptid": "110003",
    "visit_date": "2024-01-15",
    "visit_number": "01",
    "datatype": "form",
    "module": "LBD",
    "packet": "I",
    "timestamp": "2024-01-15T10:20:00+00:00"
}

# LEADS DICOM submission
{
    "action": "submit",
    "study": "leads",
    "pipeline_adcid": 45,
    "project_label": "ingest-dicom-leads",
    "center_label": "gamma",
    "gear_name": "dicom-scheduler",
    "ptid": "220002",
    "visit_date": "2024-01-16",
    "visit_number": "02",
    "datatype": "dicom",
    "module": null,
    "packet": null,
    "timestamp": "2024-01-16T14:30:00+00:00"
}
```

## How the File is Created

### Lambda Processing Workflow

1. **Read Source Events**: Lambda reads JSON event log files from S3 source bucket
2. **Validate Events**: Each event is validated using Pydantic models for data integrity
3. **Load Existing Checkpoint**: Loads existing checkpoint parquet file (if it exists)
4. **Filter New Events**: Filters out events already processed (based on timestamp)
5. **Convert to DataFrame**: Converts new events to a Polars DataFrame
6. **Merge and Sort**: Merges with existing events and sorts by timestamp
7. **Write to S3**: Writes updated parquet file back to S3

### Incremental Processing Logic

```python
# Pseudocode for incremental processing
existing_checkpoint = load_checkpoint()  # Load existing parquet
last_timestamp = existing_checkpoint.get_last_processed_timestamp()

# Only process new events
new_events = [e for e in all_events if e.timestamp > last_timestamp]

# Merge and save
updated_checkpoint = existing_checkpoint.add_events(new_events)
save_checkpoint(updated_checkpoint)
```

## File Size and Performance

### Expected File Size

- **Initial size**: ~1KB (empty schema)
- **Growth rate**: ~200-500 bytes per event (with compression)
- **Example**: 1 million events ≈ 200-500 MB compressed

### Performance Characteristics

- **Read performance**: Fast columnar reads, only load needed columns
- **Write performance**: Single atomic write operation
- **Query performance**: Efficient filtering with predicate pushdown
- **Compression ratio**: Typically 5-10x compression vs. raw JSON

## Data Quality and Validation

### Schema Validation

The Lambda enforces strict schema validation:

- All required fields must be present
- Data types must match schema
- Timestamps must be timezone-aware UTC
- String fields are trimmed of whitespace
- No extra fields allowed (strict mode)

### Timezone Handling

- All timestamps are stored in UTC
- Naive datetimes are assumed to be UTC
- Timezone-aware datetimes are converted to UTC
- Parquet preserves timezone information

### Null Handling

Optional fields that may contain null values:

- `visit_number`: May be null for some event types
- `module`: Null for non-form datatypes (required for forms)
- `packet`: May be null for some visits

## Usage Examples

### Reading with Polars

```python
import polars as pl

# Read entire file
df = pl.read_parquet("s3://nacc-checkpoints-prod/checkpoints/events.parquet")

# Read specific columns only
df = pl.read_parquet(
    "s3://nacc-checkpoints-prod/checkpoints/events.parquet",
    columns=["center_label", "action", "timestamp"]
)

# Read with filtering (predicate pushdown)
df = pl.scan_parquet("s3://nacc-checkpoints-prod/checkpoints/events.parquet") \
    .filter(pl.col("center_label") == "alpha") \
    .collect()
```

### Reading with Pandas

```python
import pandas as pd

# Read entire file
df = pd.read_parquet("s3://nacc-checkpoints-prod/checkpoints/events.parquet")

# Read specific columns
df = pd.read_parquet(
    "s3://nacc-checkpoints-prod/checkpoints/events.parquet",
    columns=["center_label", "action", "timestamp"]
)
```

### Querying with AWS Athena

```sql
-- Create external table
CREATE EXTERNAL TABLE event_checkpoints (
    action STRING,
    study STRING,
    pipeline_adcid INT,
    project_label STRING,
    center_label STRING,
    gear_name STRING,
    ptid STRING,
    visit_date STRING,
    visit_number STRING,
    datatype STRING,
    module STRING,
    packet STRING,
    timestamp TIMESTAMP
)
STORED AS PARQUET
LOCATION 's3://nacc-checkpoints-prod/checkpoints/';

-- Query events
SELECT center_label, action, COUNT(*) as event_count
FROM event_checkpoints
WHERE visit_date >= '2024-01-01'
GROUP BY center_label, action
ORDER BY center_label, action;
```

## Benefits Over Individual JSON Files

### Performance

- **10-100x faster queries**: Columnar format vs. scanning JSON files
- **Reduced I/O**: Read only needed columns, not entire files
- **Efficient filtering**: Predicate pushdown eliminates unnecessary reads

### Cost

- **5-10x storage reduction**: Compression reduces S3 storage costs
- **Fewer S3 requests**: Single file vs. thousands of LIST/GET operations
- **Lower query costs**: Athena charges by data scanned

### Simplicity

- **Single source of truth**: One file instead of thousands
- **No file management**: No need to track which files have been processed
- **Consistent schema**: Guaranteed data structure and types

## Maintenance and Operations

### Backup Strategy

- S3 versioning enabled on checkpoint bucket
- Previous versions retained for recovery
- Lambda creates new version on each update

### Monitoring

Key metrics to monitor:

- File size growth rate
- Lambda execution time
- Number of new events per execution
- S3 write errors

### Recovery

If checkpoint file becomes corrupted:

1. Delete corrupted file from S3
2. Re-run Lambda function
3. Lambda will rebuild checkpoint from all source JSON files

## Related Documentation

- [Event Log Format Specification](../../context/docs/event-log-format.md) - Source JSON event format
- [README.md](./README.md) - Lambda function overview
- [ENVIRONMENTS.md](./ENVIRONMENTS.md) - Environment configuration
- [Query Validation Module](./src/python/checkpoint_lambda/query_validation.py) - Query utility functions

## Version

**Current Version**: 1.0

This specification reflects the current implementation of the checkpoint parquet file format.
