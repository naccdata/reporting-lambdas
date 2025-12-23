# Design Document

## Overview

The event log checkpoint Lambda is an AWS Lambda function that processes visit event logs from S3 storage and creates or updates a checkpoint parquet file for analytical queries. The Lambda supports incremental processing: it reads the previous checkpoint (if it exists), retrieves only new JSON event files since the last checkpoint, validates them using Pydantic models, and appends them to create an updated checkpoint file.

The system follows a pipeline architecture: load previous checkpoint → retrieve new events → validate → merge → write. This incremental approach significantly improves performance by avoiding reprocessing of historical events. Each stage handles errors gracefully to ensure partial failures don't prevent processing of valid data.

The Lambda is implemented as `checkpoint_lambda` in the `lambda/event_log_checkpoint/` directory following NACC project structure patterns.

## Architecture

### High-Level Architecture

```
┌─────────────┐         ┌─────────────┐
│   S3 Bucket │         │  S3 Bucket  │
│ (Event Logs)│         │ (Checkpoint)│
└──────┬──────┘         └──────┬──────┘
       │                       │
       │ List & Read New       │ Read Previous
       │                       │
       ▼                       ▼
┌──────────────────────────────────────────┐
│         AWS Lambda Function              │
│                                          │
│  ┌────────────────┐  ┌──────────────┐  │
│  │Checkpoint      │  │  S3 Client   │  │
│  │Reader          │  │              │  │
│  └────────┬───────┘  └──────┬───────┘  │
│           │                  │           │
│           │                  ▼           │
│           │          ┌──────────────┐  │
│           │          │  Validator   │  │
│           │          │  (Pydantic)  │  │
│           │          └──────┬───────┘  │
│           │                  │           │
│           ▼                  ▼           │
│        ┌──────────────────────────┐    │
│        │   Checkpoint Merger      │    │
│        │ (Append new to existing) │    │
│        └──────────┬───────────────┘    │
│                   │                     │
│                   ▼                     │
│            ┌──────────────┐            │
│            │Parquet Writer│            │
│            └──────┬───────┘            │
└───────────────────┼────────────────────┘
                    │
                    │ Write Updated
                    ▼
             ┌─────────────┐
             │  S3 Bucket  │
             │ (Checkpoint)│
             └─────────────┘
```

### Component Responsibilities

1. **Checkpoint Reader**: Reads the previous checkpoint parquet file and extracts the latest timestamp
2. **S3 Client**: Handles all S3 operations (list, read, write) with filtering for new events
3. **Validator**: Validates event logs using Pydantic models
4. **Checkpoint Merger**: Combines previous checkpoint data with newly validated events
5. **Parquet Writer**: Converts merged events to parquet format and writes to S3

### Technology Stack

- **Runtime**: Python 3.12
- **Build System**: Pants 2.29
- **Development Environment**: Dev container with devcontainer CLI
- **Infrastructure**: Terraform
- **Libraries**:
  - AWS Lambda Powertools (logging, tracing, metrics)
  - Pydantic (data validation)
  - Polars (DataFrame operations and parquet file generation)
  - Boto3 (AWS SDK)

## Components and Interfaces

### 1. Lambda Handler

**Purpose**: Entry point for Lambda execution, orchestrates the incremental pipeline

**Interface**:

```python
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """
    Main Lambda handler function.
    
    Args:
        event: Lambda event containing:
            - source_bucket: S3 bucket containing event logs
            - prefix: Optional S3 prefix to filter event logs
            - checkpoint_bucket: S3 bucket for checkpoint file
            - checkpoint_key: S3 key for checkpoint file
        context: Lambda context object
        
    Returns:
        dict: Response containing:
            - statusCode: HTTP status code
            - checkpoint_path: S3 path to updated checkpoint file
            - new_events_processed: Count of newly processed events
            - total_events: Total count of events in checkpoint
            - events_failed: Count of failed events
            - last_processed_timestamp: Latest timestamp in checkpoint
            - execution_time_ms: Total execution time
    """
```

### 2. CheckpointReader

**Purpose**: Reads previous checkpoint and determines what new events to process

**Interface**:

```python
import polars as pl

class CheckpointReader:
    def __init__(self, bucket: str, key: str):
        """Initialize with S3 checkpoint location."""
        
    def checkpoint_exists(self) -> bool:
        """
        Check if a previous checkpoint exists.
        
        Returns:
            True if checkpoint file exists in S3
        """
        
    def read_checkpoint(self) -> Optional[pl.DataFrame]:
        """
        Read the previous checkpoint parquet file.
        
        Returns:
            DataFrame containing previous events, or None if no checkpoint exists
        """
        
    def get_last_processed_timestamp(self, df: pl.DataFrame) -> Optional[datetime]:
        """
        Extract the latest timestamp from the checkpoint.
        
        Args:
            df: DataFrame from previous checkpoint
            
        Returns:
            Latest timestamp value, or None if DataFrame is empty
        """
```

### 3. S3EventRetriever

**Purpose**: Retrieves event log files from S3, with filtering for incremental processing

**Interface**:

```python
class S3EventRetriever:
    def __init__(self, bucket: str, prefix: str = "", since_timestamp: Optional[datetime] = None):
        """
        Initialize with S3 bucket, optional prefix, and cutoff timestamp.
        
        Args:
            bucket: S3 bucket name
            prefix: Optional S3 prefix to filter paths
            since_timestamp: Only retrieve events with timestamp > this value
        """
        
    def list_event_files(self) -> List[str]:
        """
        List all event log JSON files in the S3 location.
        
        Returns:
            List of S3 keys matching event log naming pattern
        """
        
    def retrieve_event(self, key: str) -> Optional[dict]:
        """
        Retrieve and parse a single event log file.
        
        Args:
            key: S3 key of the event file
            
        Returns:
            Parsed JSON dict or None if retrieval fails
        """
        
    def should_process_event(self, event_data: dict) -> bool:
        """
        Determine if an event should be processed based on timestamp.
        
        Args:
            event_data: Parsed event dictionary
            
        Returns:
            True if event timestamp is after since_timestamp (or if no cutoff set)
        """
```

### 4. VisitEvent Model

**Purpose**: Pydantic model for event validation and parsing

**Interface**:

```python
from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional, Literal

class VisitEvent(BaseModel):
    """Pydantic model for visit event validation."""
    
    action: Literal["submit", "pass-qc", "not-pass-qc", "delete"]
    study: str = Field(default="adrc", min_length=1)
    pipeline_adcid: int = Field(gt=0)
    project_label: str = Field(min_length=1)
    center_label: str = Field(min_length=1)
    gear_name: str = Field(min_length=1)
    ptid: str = Field(pattern=r"^[A-Z0-9]+$", max_length=10)
    visit_date: date
    visit_number: str = Field(min_length=1)
    datatype: str = Field(min_length=1)
    module: Optional[str] = None
    packet: Optional[str] = None
    timestamp: datetime
    
    @field_validator('visit_date', mode='before')
    @classmethod
    def parse_visit_date(cls, v):
        """Parse visit_date from ISO string."""
        
    @field_validator('timestamp', mode='before')
    @classmethod
    def parse_timestamp(cls, v):
        """Parse timestamp from ISO 8601 string."""
```

### 5. EventValidator

**Purpose**: Validates events using Pydantic and handles validation errors

**Interface**:

```python
class EventValidator:
    def validate_event(self, event_data: dict, source_key: str) -> Optional[VisitEvent]:
        """
        Validate an event using Pydantic model.
        
        Args:
            event_data: Raw event dictionary
            source_key: S3 key for error logging
            
        Returns:
            Validated VisitEvent or None if validation fails
        """
        
    def get_validation_errors(self) -> List[dict]:
        """
        Get all validation errors encountered.
        
        Returns:
            List of error dictionaries with keys:
                - source_key: S3 key of failed event
                - errors: Pydantic validation errors
        """
```

### 6. CheckpointMerger

**Purpose**: Merges previous checkpoint data with newly validated events

**Interface**:

```python
import polars as pl

class CheckpointMerger:
    def merge(
        self, 
        previous_df: Optional[pl.DataFrame], 
        new_events: List[VisitEvent]
    ) -> pl.DataFrame:
        """
        Merge previous checkpoint with new events.
        
        Args:
            previous_df: DataFrame from previous checkpoint (None if first run)
            new_events: List of newly validated events
            
        Returns:
            Merged DataFrame with all events, sorted by timestamp
        """
        
    def events_to_dataframe(self, events: List[VisitEvent]) -> pl.DataFrame:
        """
        Convert list of VisitEvent objects to Polars DataFrame.
        
        Args:
            events: List of validated events
            
        Returns:
            DataFrame with proper column types for parquet
        """
```

### 7. ParquetWriter

**Purpose**: Writes events to parquet file and uploads to S3

**Interface**:

```python
import polars as pl

class ParquetWriter:
    def __init__(self, output_bucket: str, output_key: str):
        """Initialize with S3 output location."""
        
    def write_events(self, df: pl.DataFrame) -> str:
        """
        Write DataFrame to parquet and upload to S3.
        
        Args:
            df: DataFrame containing event data
            
        Returns:
            S3 URI of written parquet file (s3://bucket/key)
        """
```

## Incremental Processing Workflow

### First Run (No Previous Checkpoint)

1. Check if checkpoint exists at S3 location → No
2. Set `since_timestamp` to None (process all events)
3. List and retrieve all event log files from S3
4. Validate all events
5. Create DataFrame from valid events
6. Write parquet file to checkpoint location
7. Return summary with total events processed

### Subsequent Runs (Checkpoint Exists)

1. Check if checkpoint exists at S3 location → Yes
2. Read previous checkpoint parquet file
3. Extract maximum timestamp from checkpoint → `last_timestamp`
4. Set `since_timestamp` to `last_timestamp`
5. List all event log files from S3
6. For each file, retrieve and check if event timestamp > `last_timestamp`
7. Only process events newer than `last_timestamp`
8. Validate new events
9. Create DataFrame from new valid events
10. Merge previous checkpoint DataFrame with new events DataFrame
11. Sort merged DataFrame by timestamp
12. Write merged parquet file to checkpoint location (overwrites previous)
13. Return summary with new events processed and total events

### Timestamp Filtering Logic

The system uses the event's `timestamp` field (not the file's visit_date) for filtering:

```python
def should_process_event(event_data: dict, since_timestamp: datetime) -> bool:
    """
    Determine if event should be processed.
    
    Returns True if:
    - since_timestamp is None (first run), OR
    - event timestamp > since_timestamp
    """
    if since_timestamp is None:
        return True
    
    event_timestamp = parse_iso8601(event_data['timestamp'])
    return event_timestamp > since_timestamp
```

### Handling Edge Cases

1. **Clock skew**: Events may arrive out of order. The system processes all events with timestamp > last checkpoint, ensuring no events are missed even if they arrive late.

2. **Duplicate and evolving events**: The logging process may create multiple files for the same event as more information becomes available. The system preserves all occurrences with the following behavior:
   - **Identical events**: All occurrences preserved to maintain complete audit trail
   - **Evolving events**: Events for the same visit may have progressively more complete data (e.g., initially missing optional fields that are filled in later)
   - **Accumulative data**: Later events typically contain all information from earlier events plus additional fields
   - **Analysis support**: Analysts can query for the most recent event per visit to get the most complete data, or analyze the full timeline to understand data evolution

3. **Checkpoint corruption**: If checkpoint file is corrupted or unreadable, Lambda fails with error. Manual intervention required to restore or delete checkpoint.

4. **Empty incremental run**: If no new events exist, Lambda still succeeds and returns 0 new events processed.

### Event Evolution Pattern

The NACC Flywheel logging system often creates multiple event files for the same logical event as processing progresses:

```
Timeline for visit ptid=ABC123, visit_date=2024-01-15, visit_number=01:

T1: log-submit-20240115.json
{
  "action": "submit",
  "ptid": "ABC123",
  "visit_date": "2024-01-15",
  "visit_number": "01",
  "timestamp": "2024-01-15T10:00:00Z",
  "module": null,        // Not yet determined
  "packet": null         // Not yet determined
}

T2: log-submit-20240115.json (updated file)
{
  "action": "submit",
  "ptid": "ABC123", 
  "visit_date": "2024-01-15",
  "visit_number": "01",
  "timestamp": "2024-01-15T10:00:00Z",
  "module": "UDS",       // Now determined
  "packet": "I"          // Now determined
}

T3: log-pass-qc-20240115.json
{
  "action": "pass-qc",
  "ptid": "ABC123",
  "visit_date": "2024-01-15", 
  "visit_number": "01",
  "timestamp": "2024-01-15T10:30:00Z",
  "module": "UDS",
  "packet": "I"
}
```

**Checkpoint Behavior**: All three events are preserved in the checkpoint file, allowing analysts to:

- Get the most recent status: `pass-qc`
- See the complete timeline of the visit
- Understand how data fields were populated over time
- Maintain full audit trail for compliance

### Analytical Query Patterns for Evolving Events

The checkpoint file supports several query patterns to handle evolving event data:

#### 1. Latest Event Per Visit

```sql
-- Get the most recent event for each visit (most complete data)
SELECT *
FROM (
  SELECT *,
         ROW_NUMBER() OVER (
           PARTITION BY ptid, visit_date, visit_number 
           ORDER BY timestamp DESC
         ) as rn
  FROM checkpoint_events
) ranked
WHERE rn = 1
```

#### 2. Event Evolution Timeline

```sql
-- See how an event evolved over time
SELECT ptid, visit_date, visit_number, action, timestamp, module, packet
FROM checkpoint_events
WHERE ptid = 'ABC123' AND visit_date = '2024-01-15' AND visit_number = '01'
ORDER BY timestamp ASC
```

#### 3. Data Completeness Analysis

```sql
-- Find events where data became more complete over time
SELECT ptid, visit_date, visit_number,
       COUNT(*) as event_count,
       COUNT(DISTINCT module) as module_versions,
       COUNT(DISTINCT packet) as packet_versions
FROM checkpoint_events
GROUP BY ptid, visit_date, visit_number
HAVING COUNT(*) > 1
```

#### 4. Monthly Report Queries (Using Latest Events)

```sql
-- Count of visits with errors (using latest status)
WITH latest_events AS (
  SELECT *,
         ROW_NUMBER() OVER (
           PARTITION BY ptid, visit_date, visit_number 
           ORDER BY timestamp DESC
         ) as rn
  FROM checkpoint_events
)
SELECT center_label, COUNT(*) as error_count
FROM latest_events
WHERE rn = 1 AND action = 'not-pass-qc'
GROUP BY center_label
```

## Data Models

### VisitEvent Schema

The VisitEvent model represents a single visit event with the following fields:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| action | str | Yes | Enum: submit, pass-qc, not-pass-qc, delete | Event type |
| study | str | Yes | min_length=1, default="adrc" | Study identifier (adrc, dvcid, leads) |
| pipeline_adcid | int | Yes | > 0 | Pipeline/center identifier |
| project_label | str | Yes | min_length=1 | Flywheel project label |
| center_label | str | Yes | min_length=1 | Center/group label |
| gear_name | str | Yes | min_length=1 | Gear that logged the event |
| ptid | str | Yes | Pattern: ^[A-Z0-9]+$, max_length=10 | Participant ID |
| visit_date | date | Yes | ISO format YYYY-MM-DD | Visit date |
| visit_number | str | Yes | min_length=1 | Visit number |
| datatype | str | Yes | min_length=1 | Data type (form, dicom, etc.) |
| module | str | No | - | Module name (UDS, FTLD, etc.) |
| packet | str | No | - | Packet type (I, F, etc.) |
| timestamp | datetime | Yes | ISO 8601 | When action occurred |

### Parquet Schema

The parquet file will use Polars' native schema which automatically maps to efficient parquet types:

```python
import polars as pl

# Polars will automatically infer optimal parquet schema from DataFrame
# Example schema that would be created:
schema = {
    'action': pl.Utf8,
    'study': pl.Utf8,
    'pipeline_adcid': pl.Int32,
    'project_label': pl.Utf8,
    'center_label': pl.Utf8,
    'gear_name': pl.Utf8,
    'ptid': pl.Utf8,
    'visit_date': pl.Date,
    'visit_number': pl.Utf8,
    'datatype': pl.Utf8,
    'module': pl.Utf8,
    'packet': pl.Utf8,
    'timestamp': pl.Datetime('us', time_zone='UTC')
}
```

**Compression**: Snappy compression (Polars default for parquet)
**Partitioning**: No partitioning (single file for simplicity)

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 0: Incremental checkpoint correctness

*For any* previous checkpoint and set of new events, the merged checkpoint should contain all events from the previous checkpoint plus all new events, with no duplicates removed and no data loss.
**Validates: Requirements 4.1, 7.1**

### Property 1: File pattern matching correctness

*For any* S3 bucket and environment prefix combination, the list_event_files function should return only files matching the pattern `log-{action}-{YYYYMMDD-HHMMSS}-{adcid}-{project}-{ptid}-{visitnum}.json` where action is one of (submit, pass-qc, not-pass-qc, delete), timestamp is in format YYYYMMDD-HHMMSS, and other components are valid identifiers.
**Validates: Requirements 1.1**

### Property 2: JSON retrieval completeness

*For any* valid JSON file in S3, the retrieve_event function should successfully parse and return the complete JSON structure without data loss.
**Validates: Requirements 1.2**

### Property 3: Timestamp filtering correctness

*For any* cutoff timestamp and collection of events, the retrieval system should process only events with timestamp strictly greater than the cutoff timestamp.
**Validates: Requirements 1.1, 7.4**

### Property 4: Error resilience in retrieval

*For any* collection of S3 files where some fail to retrieve, the system should continue processing remaining files and return all successfully retrieved events.
**Validates: Requirements 1.3, 1.4**

### Property 5: Validation enforcement

*For any* event data dictionary, the validator should apply all schema constraints including required fields, type checking, pattern matching for ptid, enum validation for action, study field validation with default value, and date format validation.
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9**

### Property 6: Type conversion correctness

*For any* valid event with pipeline_adcid as a numeric string or integer, parsing should convert it to Python int type.
**Validates: Requirements 3.2**

### Property 7: Null preservation

*For any* event with null values in optional fields (module, packet), parsing should preserve those null values in the VisitEvent object.
**Validates: Requirements 3.3**

### Property 8: Serialization round-trip

*For any* valid VisitEvent object, serializing to JSON and then parsing back should produce an equivalent VisitEvent object with all fields matching.
**Validates: Requirements 3.4**

### Property 9: Parquet round-trip

*For any* collection of VisitEvent objects, writing to parquet and reading back should preserve all fields with correct data types (strings as strings, integers as integers, dates as dates, timestamps as timestamps).
**Validates: Requirements 4.2**

### Property 10: Output path correctness

*For any* successful Lambda execution, the response should contain the S3 URI (s3://bucket/key) of the updated checkpoint file.
**Validates: Requirements 4.5**

### Property 11: Query filtering correctness

*For any* parquet checkpoint file and any filter criteria (center_label, action, packet, date range), querying should return exactly the events matching all specified criteria and no others.
**Validates: Requirements 5.1, 5.2, 5.5, 5.6**

### Property 12: Temporal calculation support

*For any* event in the checkpoint file with action "submit" or "pass-qc", the system should support calculating the time difference in days between visit_date and timestamp without data loss or type errors.
**Validates: Requirements 5.3, 5.4**

### Property 13: Aggregation correctness

*For any* parquet checkpoint file, grouping events by any combination of fields (module, packet, action, center_label) and counting should produce accurate counts matching the actual number of events in each group.
**Validates: Requirements 5.7, 5.8**

### Property 14: Partial failure handling

*For any* collection of files where some contain malformed JSON or invalid schemas, the system should include all valid events in the output parquet file and log errors for failed files without halting execution.
**Validates: Requirements 6.1, 6.2, 6.4**

### Property 15: Event evolution preservation

*For any* collection of events including multiple events for the same visit with different levels of data completeness, all events should be included in the checkpoint file with their respective timestamps preserved, allowing analysis of data evolution over time.
**Validates: Requirements 7.1, 7.3, 7.4**

### Property 16: Timestamp ordering

*For any* collection of events, the checkpoint file should preserve or support ordering by timestamp to enable identification of the most recent event per visit.
**Validates: Requirements 7.2, 7.4**

### Property 17: Event completeness analysis

*For any* visit with multiple events, querying the checkpoint file should support identifying the most recent event (by timestamp) to get the most complete data available for that visit.
**Validates: Requirements 7.5, 7.6**

### Property 18: Logging completeness

*For any* Lambda execution, logs should contain file processing counts, and for any validation error encountered, logs should contain the specific error details with the source file path.
**Validates: Requirements 10.2, 10.3**

## Error Handling

### Error Categories

1. **Retrieval Errors**
   - S3 access denied: Log error and fail Lambda execution
   - File not found: Log warning and continue processing
   - Network timeout: Retry up to 3 times with exponential backoff

2. **Validation Errors**
   - Malformed JSON: Log error with file path and continue
   - Schema validation failure: Log Pydantic errors and continue
   - Missing required fields: Log specific missing fields and continue

3. **Processing Errors**
   - Parquet write failure: Log error and fail Lambda execution
   - Memory exhaustion: Fail Lambda execution with error details
   - Unexpected exceptions: Log full stack trace and fail execution

### Error Response Format

```python
{
    "statusCode": 500,
    "error": "Error type",
    "message": "Human-readable error message",
    "details": {
        "failed_files": ["s3://bucket/key1", "s3://bucket/key2"],
        "error_count": 2
    }
}
```

### Logging Strategy

- **INFO**: Normal execution milestones (start, file counts, completion)
- **WARNING**: Recoverable errors (malformed files, validation failures)
- **ERROR**: Critical failures (S3 permissions, parquet write failures)
- **DEBUG**: Detailed execution information (individual file processing)

All logs use structured JSON format via Lambda Powertools Logger.

## Testing Strategy

### Unit Testing

Unit tests will verify specific examples and edge cases:

1. **S3 Client Tests**
   - Test listing files with various prefixes
   - Test retrieving valid JSON files
   - Test error handling for missing files

2. **Validation Tests**
   - Test valid events pass validation
   - Test invalid ptid patterns fail validation
   - Test missing required fields fail validation
   - Test invalid action values fail validation

3. **Parquet Writer Tests**
   - Test writing empty DataFrame
   - Test writing DataFrame with null values
   - Test S3 upload success

4. **Handler Tests**
   - Test successful end-to-end execution
   - Test handling of mixed valid/invalid files
   - Test error response format

### Property-Based Testing

Property-based tests will verify universal properties across many inputs using the **Hypothesis** library for Python.

**Configuration**: Each property test will run a minimum of 100 iterations.

**Test Tagging**: Each property-based test will include a comment explicitly referencing the correctness property using this format:

```python
# Feature: event-log-scraper, Property 1: File pattern matching correctness
```

**Property Test Coverage**:

1. **Property 0: Incremental checkpoint** - Generate previous checkpoint and new events, verify merge correctness
2. **Property 1: File pattern matching** - Generate random S3 keys and verify pattern matching
3. **Property 2: JSON retrieval** - Generate random JSON structures and verify round-trip
4. **Property 3: Timestamp filtering** - Generate events with various timestamps and verify filtering
5. **Property 4: Error resilience** - Generate mixed valid/invalid file sets and verify continuation
6. **Property 5: Validation enforcement** - Generate random event data and verify all constraints
7. **Property 6: Type conversion** - Generate random pipeline_adcid values and verify int conversion
8. **Property 7: Null preservation** - Generate events with various null combinations
9. **Property 8: Serialization round-trip** - Generate random VisitEvents and verify round-trip
10. **Property 9: Parquet round-trip** - Generate random event collections and verify parquet round-trip
11. **Property 10: Output path** - Generate random output configurations and verify path in response
12. **Property 11: Query filtering** - Generate random datasets and filter criteria
13. **Property 12: Temporal calculations** - Generate random events and verify time calculations
14. **Property 13: Aggregation** - Generate random datasets and verify group counts
15. **Property 14: Partial failure** - Generate mixed valid/invalid files and verify output
16. **Property 15: Event evolution** - Generate datasets with evolving events and verify all preserved
17. **Property 16: Timestamp ordering** - Generate random timestamp sequences and verify ordering
18. **Property 17: Event completeness** - Generate events with varying completeness and verify latest identification
19. **Property 18: Logging** - Generate various execution scenarios and verify log content

### Integration Testing

Integration tests will verify the Lambda function works correctly with actual AWS services:

1. **S3 Integration**
   - Test reading from real S3 bucket (using LocalStack or test bucket)
   - Test writing parquet to S3
   - Test handling S3 errors

2. **End-to-End Tests**
   - Test complete Lambda execution with sample event logs
   - Test querying resulting parquet file
   - Verify CloudWatch logs and metrics

### Test Data

Test data will include:

- Sample event logs from the event-log-format.md specification
- Edge cases: events with null optional fields, various date formats
- Error cases: malformed JSON, missing fields, invalid values
- Large datasets: 1000+ events to test performance

## Deployment

### Lambda Layer Strategy

The deployment uses a multi-layer approach for optimal performance and maintainability:

#### Layer 1: AWS Lambda Powertools (`powertools`)

- **Contents**: AWS Lambda Powertools library
- **Size**: ~5MB
- **Update Frequency**: Low (only when Powertools version changes)
- **Reusability**: High (can be shared across multiple Lambda functions)

#### Layer 2: Data Processing (`data_processing`)

- **Contents**: Pydantic and Polars libraries
- **Size**: ~15-20MB
- **Update Frequency**: Medium (when data processing libraries update)
- **Reusability**: High (useful for any data processing Lambda)

#### Layer 3: AWS SDK (`aws_sdk`)

- **Contents**: Boto3 and botocore
- **Size**: ~10-15MB
- **Update Frequency**: Medium (when AWS SDK updates)
- **Reusability**: Very High (needed by most AWS Lambda functions)

#### Lambda Function Package

- **Contents**: Only application code (models, business logic, handlers)
- **Size**: <1MB
- **Update Frequency**: High (changes with every code deployment)
- **Benefits**: Fast deployments, small package size

### Deployment Workflow

#### Option 1: Automatic Layer Reuse (Recommended)

```bash
# Build layers and function
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:powertools
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:data_processing
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:aws_sdk
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:lambda

# Deploy with automatic layer reuse (from lambda directory)
./bin/exec-in-devcontainer.sh bash -c "cd lambda/event_log_checkpoint && terraform apply -var='reuse_existing_layers=true'"
```

#### Option 2: Use External Layer ARNs

```bash
# If you have existing layers from other projects
./bin/exec-in-devcontainer.sh bash -c "cd lambda/event_log_checkpoint && terraform apply \
  -var='use_external_layer_arns=true' \
  -var='external_layer_arns=[\"arn:aws:lambda:us-east-1:123456789012:layer:powertools:1\",\"arn:aws:lambda:us-east-1:123456789012:layer:data-processing:2\",\"arn:aws:lambda:us-east-1:123456789012:layer:aws-sdk:1\"]'"
```

#### Option 3: Force Layer Updates

```bash
# When you need to update layers regardless of existing versions
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:powertools
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:data_processing
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:aws_sdk
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:lambda
./bin/exec-in-devcontainer.sh bash -c "cd lambda/event_log_checkpoint && terraform apply -var='force_layer_update=true' -var='reuse_existing_layers=false'"
```

#### Option 4: Function-Only Deployment

```bash
# For code-only changes (fastest deployment)
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:lambda
./bin/exec-in-devcontainer.sh bash -c "cd lambda/event_log_checkpoint && terraform apply -target=aws_lambda_function.event_log_checkpoint"
```

### Layer Management Strategy

#### Development Environment

- **Approach**: Create new layer versions for each deployment
- **Benefit**: Ensures latest dependencies and easy rollback
- **Command**: `./bin/exec-in-devcontainer.sh bash -c "cd lambda/event_log_checkpoint && terraform apply -var='reuse_existing_layers=false'"`

#### Staging Environment

- **Approach**: Reuse layers when possible, update when dependencies change
- **Benefit**: Faster deployments while maintaining dependency updates
- **Command**: `./bin/exec-in-devcontainer.sh bash -c "cd lambda/event_log_checkpoint && terraform apply -var='reuse_existing_layers=true'"`

#### Production Environment

- **Approach**: Use specific layer ARNs from staging after validation
- **Benefit**: Maximum stability and predictability
- **Command**: `./bin/exec-in-devcontainer.sh bash -c "cd lambda/event_log_checkpoint && terraform apply -var='use_external_layer_arns=true' -var='external_layer_arns=[...]'"`

### Cost Optimization

#### Layer Storage Costs

- Each layer version consumes storage space
- AWS charges for layer storage ($0.0000000309 per GB-second)
- Old layer versions can be deleted after successful deployments

#### Deployment Time Optimization

- **Layer reuse**: ~30 seconds faster deployment
- **Function-only updates**: ~60 seconds faster than full deployment
- **External layer ARNs**: Fastest deployment option

#### Example Cleanup Script

```bash
# Clean up old layer versions (keep last 3)
aws lambda list-layer-versions --layer-name event-log-checkpoint-powertools \
  --query 'LayerVersions[3:].Version' --output text | \
  xargs -I {} aws lambda delete-layer-version \
    --layer-name event-log-checkpoint-powertools --version-number {}
```

### Pants Build Configuration

The Lambda uses a layered architecture to separate dependencies from function code for better deployment efficiency and reusability:

```python
# lambda/event_log_checkpoint/src/python/checkpoint_lambda/BUILD
python_sources(name="function")

# Lambda function (code only, no dependencies)
python_aws_lambda_function(
    name="lambda",
    runtime="python3.12",
    handler="lambda_function.py:lambda_handler",
    include_requirements=False,  # Dependencies come from layers
)

# AWS Lambda Powertools layer
python_aws_lambda_layer(
    name="powertools",
    runtime="python3.12",
    dependencies=["//:root#aws-lambda-powertools"],
    include_sources=False,
)

# Data processing layer (Pydantic + Polars)
python_aws_lambda_layer(
    name="data_processing",
    runtime="python3.12",
    dependencies=[
        "//:root#pydantic",
        "//:root#polars",
    ],
    include_sources=False,
)

# AWS SDK layer (if needed separately)
python_aws_lambda_layer(
    name="aws_sdk",
    runtime="python3.12",
    dependencies=["//:root#boto3"],
    include_sources=False,
)
```

### Layer Architecture Benefits

1. **Faster Deployments**: Only function code changes require redeployment
2. **Layer Reusability**: Layers can be shared across multiple Lambda functions
3. **Size Optimization**: Each layer can be optimized independently
4. **Caching**: AWS caches layers, improving cold start performance

### Terraform Configuration

```hcl
# Data sources to check for existing layers
data "aws_lambda_layer_version" "powertools" {
  layer_name = "event-log-checkpoint-powertools"
  
  # Only use existing layer if it exists
  count = var.reuse_existing_layers ? 1 : 0
}

data "aws_lambda_layer_version" "data_processing" {
  layer_name = "event-log-checkpoint-data-processing"
  
  count = var.reuse_existing_layers ? 1 : 0
}

data "aws_lambda_layer_version" "aws_sdk" {
  layer_name = "event-log-checkpoint-aws-sdk"
  
  count = var.reuse_existing_layers ? 1 : 0
}

# Lambda layers - only create if not reusing existing or if content changed
resource "aws_lambda_layer_version" "powertools" {
  count = var.reuse_existing_layers && length(data.aws_lambda_layer_version.powertools) > 0 ? 0 : 1
  
  filename         = "powertools_layer.zip"
  layer_name       = "event-log-checkpoint-powertools"
  source_code_hash = filebase64sha256("powertools_layer.zip")
  
  compatible_runtimes = ["python3.12"]
  description         = "AWS Lambda Powertools layer"
  
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lambda_layer_version" "data_processing" {
  count = var.reuse_existing_layers && length(data.aws_lambda_layer_version.data_processing) > 0 ? 0 : 1
  
  filename         = "data_processing_layer.zip"
  layer_name       = "event-log-checkpoint-data-processing"
  source_code_hash = filebase64sha256("data_processing_layer.zip")
  
  compatible_runtimes = ["python3.12"]
  description         = "Pydantic and Polars layer for data processing"
  
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lambda_layer_version" "aws_sdk" {
  count = var.reuse_existing_layers && length(data.aws_lambda_layer_version.aws_sdk) > 0 ? 0 : 1
  
  filename         = "aws_sdk_layer.zip"
  layer_name       = "event-log-checkpoint-aws-sdk"
  source_code_hash = filebase64sha256("aws_sdk_layer.zip")
  
  compatible_runtimes = ["python3.12"]
  description         = "AWS SDK (Boto3) layer"
  
  lifecycle {
    create_before_destroy = true
  }
}

# Local values to determine which layer ARNs to use
locals {
  powertools_layer_arn = var.reuse_existing_layers && length(data.aws_lambda_layer_version.powertools) > 0 ? 
    data.aws_lambda_layer_version.powertools[0].arn : 
    aws_lambda_layer_version.powertools[0].arn
    
  data_processing_layer_arn = var.reuse_existing_layers && length(data.aws_lambda_layer_version.data_processing) > 0 ? 
    data.aws_lambda_layer_version.data_processing[0].arn : 
    aws_lambda_layer_version.data_processing[0].arn
    
  aws_sdk_layer_arn = var.reuse_existing_layers && length(data.aws_lambda_layer_version.aws_sdk) > 0 ? 
    data.aws_lambda_layer_version.aws_sdk[0].arn : 
    aws_lambda_layer_version.aws_sdk[0].arn
}

resource "aws_lambda_function" "event_log_checkpoint" {
  function_name = "event-log-checkpoint"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"
  timeout       = 900  # 15 minutes
  memory_size   = 3008 # 3GB for large datasets
  
  filename         = "checkpoint_lambda.zip"
  source_code_hash = filebase64sha256("checkpoint_lambda.zip")
  
  # Use local values to reference appropriate layer ARNs
  layers = [
    local.powertools_layer_arn,
    local.data_processing_layer_arn,
    local.aws_sdk_layer_arn,
  ]
  
  environment {
    variables = {
      SOURCE_BUCKET       = var.event_log_bucket
      CHECKPOINT_BUCKET   = var.checkpoint_bucket
      CHECKPOINT_KEY      = "checkpoints/events.parquet"
      LOG_LEVEL           = "INFO"
      POWERTOOLS_SERVICE_NAME = "event-log-checkpoint"
    }
  }
  
  tracing_config {
    mode = "Active"  # Enable X-Ray tracing
  }
  
  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy_attachment.lambda_xray,
    aws_cloudwatch_log_group.lambda_logs,
  ]
}

# Alternative approach: Use external layer ARNs if provided
resource "aws_lambda_function" "event_log_checkpoint_with_external_layers" {
  count = var.use_external_layer_arns ? 1 : 0
  
  function_name = "event-log-checkpoint"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"
  timeout       = 900
  memory_size   = 3008
  
  filename         = "checkpoint_lambda.zip"
  source_code_hash = filebase64sha256("checkpoint_lambda.zip")
  
  # Use externally provided layer ARNs
  layers = var.external_layer_arns
  
  environment {
    variables = {
      SOURCE_BUCKET       = var.event_log_bucket
      CHECKPOINT_BUCKET   = var.checkpoint_bucket
      CHECKPOINT_KEY      = "checkpoints/events.parquet"
      LOG_LEVEL           = "INFO"
      POWERTOOLS_SERVICE_NAME = "event-log-checkpoint"
    }
  }
  
  tracing_config {
    mode = "Active"
  }
}

resource "aws_iam_role" "lambda_role" {
  name = "event-log-checkpoint-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_s3_policy" {
  name = "event-log-checkpoint-s3-policy"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.event_log_bucket}",
          "arn:aws:s3:::${var.event_log_bucket}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.checkpoint_bucket}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_xray" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/event-log-checkpoint"
  retention_in_days = 30
}
```

### Variables Configuration

```hcl
# variables.tf
variable "event_log_bucket" {
  description = "S3 bucket containing event log files"
  type        = string
}

variable "checkpoint_bucket" {
  description = "S3 bucket for checkpoint parquet files"
  type        = string
}

variable "reuse_existing_layers" {
  description = "Whether to reuse existing Lambda layers if they exist"
  type        = bool
  default     = true
}

variable "use_external_layer_arns" {
  description = "Whether to use externally provided layer ARNs instead of creating layers"
  type        = bool
  default     = false
}

variable "external_layer_arns" {
  description = "List of external layer ARNs to use (when use_external_layer_arns is true)"
  type        = list(string)
  default     = []
  
  validation {
    condition = var.use_external_layer_arns ? length(var.external_layer_arns) > 0 : true
    error_message = "external_layer_arns must be provided when use_external_layer_arns is true."
  }
}

variable "force_layer_update" {
  description = "Force update of Lambda layers even if they exist"
  type        = bool
  default     = false
}
```

### Outputs Configuration

```hcl
# outputs.tf
output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = var.use_external_layer_arns ? aws_lambda_function.event_log_checkpoint_with_external_layers[0].arn : aws_lambda_function.event_log_checkpoint.arn
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = var.use_external_layer_arns ? aws_lambda_function.event_log_checkpoint_with_external_layers[0].function_name : aws_lambda_function.event_log_checkpoint.function_name
}

output "powertools_layer_arn" {
  description = "ARN of the Powertools layer"
  value       = var.use_external_layer_arns ? null : local.powertools_layer_arn
}

output "data_processing_layer_arn" {
  description = "ARN of the data processing layer"
  value       = var.use_external_layer_arns ? null : local.data_processing_layer_arn
}

output "aws_sdk_layer_arn" {
  description = "ARN of the AWS SDK layer"
  value       = var.use_external_layer_arns ? null : local.aws_sdk_layer_arn
}

output "all_layer_arns" {
  description = "All layer ARNs used by the Lambda function"
  value = var.use_external_layer_arns ? var.external_layer_arns : [
    local.powertools_layer_arn,
    local.data_processing_layer_arn,
    local.aws_sdk_layer_arn,
  ]
}
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| SOURCE_BUCKET | S3 bucket containing event logs | nacc-events |
| CHECKPOINT_BUCKET | S3 bucket for checkpoint files | nacc-checkpoints |
| CHECKPOINT_KEY | S3 key for checkpoint parquet file | checkpoints/events.parquet |
| LOG_LEVEL | Logging level | INFO |
| POWERTOOLS_SERVICE_NAME | Service name for tracing | event-log-scraper |

## Performance Considerations

### Memory and Timeout

- **Memory**: 3GB to handle large datasets (10,000+ events)
- **Timeout**: 15 minutes to allow for S3 operations and parquet writing
- **Expected execution time**:
  - First run (full scrape): 5-10 minutes for 10,000+ historical events
  - Incremental runs: 30-60 seconds for typical daily/weekly new events (100-1000 events)

### Incremental Processing Benefits

The incremental approach provides significant performance improvements:

1. **Reduced S3 Operations**: Only reads new event files, not all historical files
2. **Lower Memory Usage**: Only processes new events in memory, previous checkpoint stays on disk until merge
3. **Faster Execution**: Typical incremental runs process 100-1000 new events vs 10,000+ historical events
4. **Cost Savings**: Shorter execution time = lower Lambda costs

### Optimization Strategies

1. **Incremental Processing**: Only process events with timestamp > last checkpoint timestamp
2. **Efficient Parquet Merge**: Read previous checkpoint as DataFrame, append new rows, write once
3. **Batch S3 Operations**: Use boto3's batch operations where possible
4. **Parquet Compression**: Use Snappy compression for balance of speed and size
5. **Connection Pooling**: Reuse boto3 clients across invocations
6. **Timestamp Indexing**: Ensure timestamp column is first for efficient filtering

### Scalability

The incremental design scales well:

- **Daily runs**: Process ~100-500 new events in <1 minute
- **Weekly runs**: Process ~500-2000 new events in 1-2 minutes
- **Monthly runs**: Process ~2000-10000 new events in 2-5 minutes

For datasets larger than 100,000 total events in checkpoint:

- Consider partitioning parquet by year or center
- Use columnar filtering to read only necessary columns
- Monitor checkpoint file size (should stay under 100MB for good performance)

## Monitoring and Observability

### CloudWatch Metrics

Custom metrics emitted via Lambda Powertools:

- `NewEventsProcessed`: Count of newly processed events in this run
- `TotalEvents`: Total count of events in checkpoint after merge
- `EventsFailed`: Count of failed events
- `ExecutionTime`: Total execution time in milliseconds
- `CheckpointFileSize`: Size of checkpoint parquet file in bytes
- `IncrementalRun`: Boolean indicating if this was an incremental run (1) or full scrape (0)

### X-Ray Tracing

X-Ray traces will capture:

- S3 list operations
- S3 get operations for each file
- Validation time per event
- Parquet write operation
- S3 put operation for checkpoint file

### Alarms

Recommended CloudWatch alarms:

- Lambda errors > 0
- Lambda duration > 10 minutes
- EventsFailed > 10% of EventsProcessed
