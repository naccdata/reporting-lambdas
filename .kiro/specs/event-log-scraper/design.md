# Design Document

## Overview

The event log checkpoint Lambda is an AWS Lambda function that processes visit event logs from S3 storage and creates or updates a checkpoint parquet file for analytical queries. The Lambda supports incremental processing: it reads the previous checkpoint (if it exists), retrieves only new JSON event files since the last checkpoint, validates them using Pydantic models, and appends them to create an updated checkpoint file.

**File Naming Pattern**: Event log files follow the pattern `log-{action}-{timestamp}-{adcid}-{project}-{ptid}-{visitnum}.json` where timestamp is in `YYYYMMDD-HHMMSS` format. The system also supports legacy files with the simpler pattern `log-{action}-{YYYYMMDD}.json` for backward compatibility. See `context/docs/event-log-format.md` for detailed examples of the actual file structure used by the NACC Flywheel logging system.

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
       │ List & Read New       │ Read/Write
       │                       │
       ▼                       ▼
┌──────────────────────────────────────────┐
│         AWS Lambda Function              │
│                                          │
│  ┌────────────────┐  ┌──────────────┐  │
│  │CheckpointStore │  │S3EventRetriever│ │
│  │(load/save)     │  │(retrieve &   │  │
│  └────────┬───────┘  │ validate)    │  │
│           │          └──────┬───────┘  │
│           │                  │           │
│           │                  ▼           │
│           │          ┌──────────────┐  │
│           │          │ VisitEvent   │  │
│           │          │ (validation) │  │
│           │          └──────┬───────┘  │
│           │                  │           │
│           ▼                  ▼           │
│        ┌──────────────────────────┐    │
│        │   Checkpoint.add_events  │    │
│        │ (merge new with existing)│    │
│        └──────────┬───────────────┘    │
│                   │                     │
│                   ▼                     │
│            ┌──────────────┐            │
│            │CheckpointStore│           │
│            │.save()       │            │
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

1. **Checkpoint**: Encapsulates checkpoint data and provides operations for working with event collections, including merging new events
2. **CheckpointStore**: Handles reading and writing checkpoints to/from S3 storage (combines previous CheckpointReader + ParquetWriter functionality)
3. **S3EventRetriever**: Handles S3 operations for event log retrieval and validation using VisitEvent Pydantic model directly
4. **Lambda Handler**: Orchestrates the incremental pipeline

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
            
    Workflow:
        1. CheckpointStore loads previous checkpoint (or None if first run)
        2. Get last processed timestamp for incremental processing
        3. S3EventRetriever retrieves and validates new events since last timestamp
        4. Checkpoint.add_events() merges previous checkpoint with new events
        5. CheckpointStore saves updated checkpoint to S3
        6. Return processing summary
    """
```

### 2. Checkpoint

**Purpose**: Data model that encapsulates checkpoint event data and provides operations

**Interface**:

```python
import polars as pl
from typing import List, Optional
from datetime import datetime

class Checkpoint:
    def __init__(self, events_df: Optional[pl.DataFrame] = None):
        """
        Initialize checkpoint with event data.
        
        Args:
            events_df: DataFrame containing event data, None for empty checkpoint
        """
        
    @classmethod
    def from_events(cls, events: List[VisitEvent]) -> 'Checkpoint':
        """
        Create checkpoint from list of VisitEvent objects.
        
        Args:
            events: List of validated events
            
        Returns:
            Checkpoint instance with events converted to DataFrame
        """
        
    @classmethod
    def empty(cls) -> 'Checkpoint':
        """
        Create an empty checkpoint.
        
        Returns:
            Empty checkpoint instance
        """
        
    def get_last_processed_timestamp(self) -> Optional[datetime]:
        """
        Get the latest timestamp from checkpoint events.
        
        Returns:
            Latest timestamp, or None if checkpoint is empty
        """
        
    def add_events(self, new_events: List[VisitEvent]) -> 'Checkpoint':
        """
        Create new checkpoint with additional events merged in.
        
        This method handles the merging logic internally:
        - Converts new events to DataFrame
        - Merges with existing events
        - Sorts by timestamp
        - Returns new Checkpoint instance
        
        Args:
            new_events: List of new validated events to add
            
        Returns:
            New checkpoint instance with merged events, sorted by timestamp
        """
        
    def get_event_count(self) -> int:
        """
        Get total number of events in checkpoint.
        
        Returns:
            Number of events
        """
        
    def is_empty(self) -> bool:
        """
        Check if checkpoint contains any events.
        
        Returns:
            True if checkpoint is empty
        """
        
    @property
    def dataframe(self) -> pl.DataFrame:
        """
        Get underlying DataFrame for operations that absolutely need direct access.
        
        Note: This should be used sparingly. Prefer adding methods to Checkpoint
        for common operations rather than exposing the implementation.
        
        Returns:
            Polars DataFrame containing event data
        """
```

### 3. CheckpointStore

**Purpose**: Handles reading and writing checkpoints to/from S3 storage

**Interface**:

```python
class CheckpointStore:
    def __init__(self, bucket: str, key: str):
        """
        Initialize with S3 checkpoint location.
        
        Args:
            bucket: S3 bucket name
            key: S3 key for checkpoint file
        """
        
    def exists(self) -> bool:
        """
        Check if a checkpoint exists in S3.
        
        Returns:
            True if checkpoint file exists in S3
        """
        
    def load(self) -> Optional[Checkpoint]:
        """
        Load checkpoint from S3.
        
        Returns:
            Checkpoint object containing previous events, or None if no checkpoint exists
            
        Raises:
            CheckpointCorruptedError: If checkpoint file exists but is corrupted
        """
        
    def save(self, checkpoint: Checkpoint) -> str:
        """
        Save checkpoint to S3 as parquet file.
        
        Args:
            checkpoint: Checkpoint object to save
            
        Returns:
            S3 URI of written checkpoint file (s3://bucket/key)
        """
```

### 4. S3EventRetriever

**Purpose**: Retrieves event log files from S3, with filtering for incremental processing and validation using VisitEvent Pydantic model directly

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
        
    def retrieve_and_validate_events(self) -> tuple[List[VisitEvent], List[dict]]:
        """
        Retrieve all new event files, validate them, and return results.
        
        This method handles the complete retrieval and validation pipeline:
        - Lists event files matching the pattern
        - Retrieves and parses JSON from each file
        - Filters by timestamp if since_timestamp is set
        - Validates each event using VisitEvent Pydantic model directly
        - Collects validation errors for logging
        
        Returns:
            Tuple of (valid_events, validation_errors)
            - valid_events: List of successfully validated VisitEvent objects
            - validation_errors: List of error dicts with keys:
                - source_key: S3 key of failed event
                - errors: Pydantic validation errors
        """
```

### 5. VisitEvent Model

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
    ptid: str = Field(pattern=r"^[!-~]{1,10}$", max_length=10)
    visit_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    visit_number: Optional[str] = Field(default=None)
    datatype: Literal["apoe", "biomarker", "dicom", "enrollment", "form", 
                     "genetic-availability", "gwas", "imputation", "scan-analysis"]
    module: Optional[Literal["UDS", "FTLD", "LBD", "MDS"]] = Field(default=None)
    packet: Optional[str] = Field(default=None)
    timestamp: datetime
    
    @model_validator(mode='after')
    def validate_module(self) -> Self:
        """Validate module field based on datatype.
        
        Rules:
        - If datatype != "form" and module is not None: raise error
        - If datatype == "form" and module is None: raise error
        """
```

## Incremental Processing Workflow

### First Run (No Previous Checkpoint)

1. CheckpointStore checks if checkpoint exists at S3 location → No
2. CheckpointStore.load() returns None
3. Set `since_timestamp` to None (process all events)
4. S3EventRetriever retrieves and validates all event log files from S3 using VisitEvent model directly
5. Create empty checkpoint: `checkpoint = Checkpoint.empty()`
6. Add validated events: `updated_checkpoint = checkpoint.add_events(valid_events)`
7. CheckpointStore saves updated checkpoint to S3
8. Return summary with total events processed

### Subsequent Runs (Checkpoint Exists)

1. CheckpointStore checks if checkpoint exists at S3 location → Yes
2. CheckpointStore.load() returns previous Checkpoint object
3. Extract maximum timestamp: `last_timestamp = checkpoint.get_last_processed_timestamp()`
4. Set `since_timestamp` to `last_timestamp`
5. S3EventRetriever retrieves and validates only new event files (timestamp > last_timestamp) using VisitEvent model directly
6. Add new events to checkpoint: `updated_checkpoint = checkpoint.add_events(new_valid_events)`
7. CheckpointStore saves updated checkpoint to S3 (overwrites previous)
8. Return summary with new events processed and total events

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

T1: log-submit-20240115-100000-42-ingest-form-alpha-ABC123-01.json
{
  "action": "submit",
  "ptid": "ABC123",
  "visit_date": "2024-01-15",
  "visit_number": "01",
  "timestamp": "2024-01-15T10:00:00Z",
  "module": null,        // Not yet determined
  "packet": null         // Not yet determined
}

T2: log-submit-20240115-100000-42-ingest-form-alpha-ABC123-01.json (updated file)
{
  "action": "submit",
  "ptid": "ABC123", 
  "visit_date": "2024-01-15",
  "visit_number": "01",
  "timestamp": "2024-01-15T10:00:00Z",
  "module": "UDS",       // Now determined
  "packet": "I"          // Now determined
}

T3: log-pass-qc-20240115-103000-42-ingest-form-alpha-ABC123-01.json
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
| ptid | str | Yes | Pattern: ^[!-~]{1,10}$, max_length=10 | Participant ID (printable non-whitespace) |
| visit_date | str | Yes | Pattern: ^\d{4}-\d{2}-\d{2}$ | Visit date in ISO format YYYY-MM-DD |
| visit_number | str | No | - | Visit number (optional) |
| datatype | str | Yes | Enum: apoe, biomarker, dicom, enrollment, form, genetic-availability, gwas, imputation, scan-analysis | Data type |
| module | str | No | Enum: UDS, FTLD, LBD, MDS (required if datatype=form, must be null otherwise) | Module name |
| packet | str | No | - | Packet type (optional) |
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
    'visit_date': pl.Utf8,  # String format YYYY-MM-DD
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

*For any* S3 bucket and environment prefix combination, the list_event_files function should return only files matching the pattern `log-{action}-{timestamp}-{adcid}-{project}-{ptid}-{visitnum}.json` where action is one of (submit, pass-qc, not-pass-qc, delete), timestamp is in format YYYYMMDD-HHMMSS, and other components are valid identifiers.
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

*For any* event data dictionary, the validator should apply all schema constraints including required fields, type checking, pattern matching for ptid (printable non-whitespace characters), enum validation for action and datatype, study field validation with default value, visit_date string format validation, and module validation rules based on datatype.
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12, 2.13**

### Property 6: Type conversion correctness

*For any* valid event with pipeline_adcid as a numeric string or integer, parsing should convert it to Python int type.
**Validates: Requirements 3.2**

### Property 7: Null preservation

*For any* event with null values in optional fields (visit_number, module, packet), parsing should preserve those null values in the VisitEvent object.
**Validates: Requirements 3.3**

### Property 8: Serialization round-trip

*For any* valid VisitEvent object, serializing to JSON and then parsing back should produce an equivalent VisitEvent object with all fields matching.
**Validates: Requirements 3.4**

### Property 9: Parquet round-trip

*For any* collection of VisitEvent objects, writing to parquet and reading back should preserve all fields with correct data types (strings as strings, integers as integers, visit_date as string, timestamps as timestamps).
**Validates: Requirements 4.2**

### Property 10: Output path correctness

*For any* successful Lambda execution, the response should contain the S3 URI (s3://bucket/key) of the updated checkpoint file.
**Validates: Requirements 4.5**

### Property 11: Query filtering correctness

*For any* parquet checkpoint file and any filter criteria (center_label, action, packet, date range), querying should return exactly the events matching all specified criteria and no others.
**Validates: Requirements 5.1, 5.2, 5.5, 5.6**

### Property 12: Temporal calculation support

*For any* event in the checkpoint file with action "submit" or "pass-qc", the system should support calculating the time difference in days between visit_date (string format YYYY-MM-DD) and timestamp without data loss or type errors.
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

### Testing Architecture

The testing strategy uses **moto.server** (ThreadedMotoServer) to provide realistic S3 mocking while keeping polars methods unmocked. This approach allows polars to perform actual S3 operations against a mocked S3 server, providing more realistic test scenarios than direct method mocking.

**Key Benefits:**

- **Realistic S3 Operations**: Polars performs actual S3 read/write operations against mocked server
- **End-to-End Testing**: Complete S3 → polars → parquet workflow testing
- **Error Simulation**: Real S3 error conditions (access denied, file not found, etc.)
- **Performance Testing**: Actual network and serialization overhead

### Test Infrastructure Setup

**moto.server Configuration:**

```python
import pytest
from moto.server import ThreadedMotoServer

@pytest.fixture(scope="module")
def moto_server():
    """Fixture to run a mocked AWS server for testing."""
    # Use port=0 to get a random free port
    server = ThreadedMotoServer(port=0)
    server.start()
    host, port = server.get_host_and_port()
    yield f"http://{host}:{port}"
    server.stop()

@pytest.fixture
def s3_client(moto_server):
    """S3 client configured to use moto server."""
    import boto3
    return boto3.client("s3", endpoint_url=moto_server)
```

**Environment Configuration:**

- Set `AWS_ENDPOINT_URL` environment variable to moto server URL
- Configure boto3 clients to use moto server endpoint
- Polars automatically uses boto3 configuration for S3 operations

### Unit Testing

Unit tests will verify specific examples and edge cases using moto.server:

1. **S3 Operations Tests**
   - Test listing files with various prefixes using real S3 operations
   - Test retrieving valid JSON files through actual S3 get operations
   - Test error handling for missing files with real S3 errors
   - Test S3 permissions and access denied scenarios

2. **Validation Tests**
   - Test valid events pass validation with real JSON from mocked S3
   - Test invalid ptid patterns fail validation
   - Test missing required fields fail validation
   - Test invalid action values fail validation

3. **Parquet Operations Tests**
   - Test writing empty DataFrame to mocked S3 using polars
   - Test writing DataFrame with null values using polars S3 operations
   - Test reading parquet files from mocked S3 using polars
   - Test S3 upload/download success with actual polars operations

4. **Handler Tests**
   - Test successful end-to-end execution with mocked S3 server
   - Test handling of mixed valid/invalid files with real S3 operations
   - Test error response format with actual S3 error conditions

### Integration Testing with moto.server

**Complete Workflow Testing:**

```python
def test_complete_workflow_with_moto_server(moto_server, s3_client):
    """Test complete Lambda workflow with mocked S3 server."""
    # 1. Setup test data in mocked S3
    s3_client.create_bucket(Bucket="test-events")
    s3_client.create_bucket(Bucket="test-checkpoints")
    
    # 2. Upload test event files
    test_events = [...]  # Real JSON event data
    for i, event in enumerate(test_events):
        s3_client.put_object(
            Bucket="test-events",
            Key=f"log-submit-2024011{i}.json",
            Body=json.dumps(event)
        )
    
    # 3. Execute Lambda handler (polars will use real S3 operations)
    response = lambda_handler({
        "source_bucket": "test-events",
        "checkpoint_bucket": "test-checkpoints", 
        "checkpoint_key": "checkpoint.parquet"
    }, mock_context)
    
    # 4. Verify results using real S3 operations
    # Polars will actually read from mocked S3
    checkpoint_df = pl.read_parquet("s3://test-checkpoints/checkpoint.parquet")
    assert len(checkpoint_df) == len(test_events)
```

**Incremental Processing Testing:**

```python
def test_incremental_processing_with_moto_server(moto_server, s3_client):
    """Test incremental processing with real S3 operations."""
    # 1. Setup initial checkpoint in mocked S3
    initial_events = [...]
    initial_df = pl.DataFrame(initial_events)
    initial_df.write_parquet("s3://test-checkpoints/checkpoint.parquet")
    
    # 2. Add new events to mocked S3
    new_events = [...]
    for event in new_events:
        s3_client.put_object(...)
    
    # 3. Run incremental processing
    # CheckpointStore will use real polars S3 operations
    # S3EventRetriever will use real boto3 S3 operations
    response = lambda_handler(...)
    
    # 4. Verify incremental merge worked correctly
    updated_df = pl.read_parquet("s3://test-checkpoints/checkpoint.parquet")
    assert len(updated_df) == len(initial_events) + len(new_events)
```

### Property-Based Testing

Property-based tests will verify universal properties across many inputs using the **Hypothesis** library for Python with **moto.server** for realistic S3 operations.

**Configuration**: Each property test will run a minimum of 100 iterations.

**Test Infrastructure**: Property tests use the same moto.server fixture to ensure polars and boto3 perform real S3 operations against the mocked server.

**Test Tagging**: Each property-based test will include a comment explicitly referencing the correctness property using this format:

```python
# Feature: event-log-scraper, Property 1: File pattern matching correctness
def test_file_pattern_matching_property(moto_server, s3_client):
    """Property test with real S3 operations via moto.server."""
    # Hypothesis generates test data
    # S3 operations use real boto3 calls to mocked server
    # Polars operations use real S3 read/write to mocked server
```

**Property Test Coverage with moto.server:**

1. **Property 0: Incremental checkpoint** - Generate previous checkpoint and new events, use real polars S3 operations to verify merge correctness
2. **Property 1: File pattern matching** - Generate random S3 keys, upload to mocked S3, verify pattern matching with real S3 list operations
3. **Property 2: JSON retrieval** - Generate random JSON structures, upload to mocked S3, verify round-trip with real S3 operations
4. **Property 3: Timestamp filtering** - Generate events with various timestamps, upload to mocked S3, verify filtering with real retrieval
5. **Property 4: Error resilience** - Generate mixed valid/invalid file sets in mocked S3, verify continuation with real S3 errors
6. **Property 5: Validation enforcement** - Generate random event data, upload to mocked S3, verify all constraints with real JSON retrieval
7. **Property 6: Type conversion** - Generate random pipeline_adcid values, verify int conversion with real S3 JSON operations
8. **Property 7: Null preservation** - Generate events with various null combinations, test with real S3 round-trip
9. **Property 8: Serialization round-trip** - Generate random VisitEvents, test with real S3 JSON operations
10. **Property 9: Parquet round-trip** - Generate random event collections, verify parquet round-trip with real polars S3 operations
11. **Property 10: Output path** - Generate random output configurations, verify path with real S3 operations
12. **Property 11: Query filtering** - Generate random datasets, upload to mocked S3, test filtering with real polars S3 operations
13. **Property 12: Temporal calculations** - Generate random events, verify time calculations with real parquet operations
14. **Property 13: Aggregation** - Generate random datasets, verify group counts with real polars S3 operations
15. **Property 14: Partial failure** - Generate mixed valid/invalid files in mocked S3, verify output with real error handling
16. **Property 15: Event evolution** - Generate datasets with evolving events, test with real S3 operations
17. **Property 16: Timestamp ordering** - Generate random timestamp sequences, verify ordering with real parquet operations
18. **Property 17: Event completeness** - Generate events with varying completeness, verify latest identification with real S3 operations
19. **Property 18: Logging** - Generate various execution scenarios, verify log content with real S3 operations

### Error Simulation with moto.server

**Realistic Error Testing:**

- **S3 Access Denied**: Configure mocked S3 to return real AccessDenied errors
- **File Not Found**: Test with missing files in mocked S3 bucket
- **Network Timeouts**: Simulate connection issues with moto server
- **Corrupted Files**: Upload invalid parquet/JSON to mocked S3
- **Permission Errors**: Configure bucket policies in mocked S3

**Example Error Test:**

```python
def test_s3_access_denied_with_moto_server(moto_server, s3_client):
    """Test handling of real S3 access denied errors."""
    # Create bucket but don't grant permissions
    s3_client.create_bucket(Bucket="restricted-bucket")
    
    # Configure retriever to use restricted bucket
    retriever = S3EventRetriever("restricted-bucket")
    
    # This will generate real S3 access denied error
    with pytest.raises(ClientError) as exc_info:
        retriever.list_event_files()
    
    assert exc_info.value.response['Error']['Code'] == 'AccessDenied'
```

### Integration Testing

Integration tests will verify the Lambda function works correctly with moto.server providing realistic S3 operations:

1. **S3 Integration with moto.server**
   - Test reading from mocked S3 bucket using real polars operations
   - Test writing parquet to mocked S3 using real polars operations
   - Test handling real S3 errors generated by moto.server

2. **End-to-End Tests with moto.server**
   - Test complete Lambda execution with sample event logs in mocked S3
   - Test querying resulting parquet file using real polars S3 operations
   - Verify CloudWatch logs and metrics with realistic S3 interactions

**Example Integration Test:**

```python
def test_end_to_end_lambda_execution(moto_server, s3_client):
    """Test complete Lambda execution with mocked S3 server."""
    # Setup test buckets
    s3_client.create_bucket(Bucket="test-events")
    s3_client.create_bucket(Bucket="test-checkpoints")
    
    # Upload test event files using real S3 operations
    test_events = [
        {"action": "submit", "ptid": "ABC123", ...},
        {"action": "pass-qc", "ptid": "ABC123", ...}
    ]
    
    for i, event in enumerate(test_events):
        s3_client.put_object(
            Bucket="test-events",
            Key=f"log-submit-2024011{i}.json",
            Body=json.dumps(event)
        )
    
    # Execute Lambda handler
    # All S3 operations (boto3 and polars) will use mocked server
    response = lambda_handler({
        "source_bucket": "test-events",
        "checkpoint_bucket": "test-checkpoints",
        "checkpoint_key": "checkpoint.parquet"
    }, mock_context)
    
    # Verify results using real polars S3 operations
    checkpoint_df = pl.read_parquet(
        "s3://test-checkpoints/checkpoint.parquet",
        storage_options={"endpoint_url": moto_server}
    )
    
    assert len(checkpoint_df) == len(test_events)
    assert response["statusCode"] == 200
    assert response["new_events_processed"] == len(test_events)
```

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

- **Contents**: AWS Lambda Powertools library (includes boto3)
- **Size**: ~5MB
- **Update Frequency**: Low (only when Powertools version changes)
- **Reusability**: High (can be shared across multiple Lambda functions)

#### Layer 2: Data Processing (`data_processing`)

- **Contents**: Pydantic and Polars libraries
- **Size**: ~15-20MB
- **Update Frequency**: Medium (when data processing libraries update)
- **Reusability**: High (useful for any data processing Lambda)

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

# Local values to determine which layer ARNs to use
locals {
  powertools_layer_arn = var.reuse_existing_layers && length(data.aws_lambda_layer_version.powertools) > 0 ? 
    data.aws_lambda_layer_version.powertools[0].arn : 
    aws_lambda_layer_version.powertools[0].arn
    
  data_processing_layer_arn = var.reuse_existing_layers && length(data.aws_lambda_layer_version.data_processing) > 0 ? 
    data.aws_lambda_layer_version.data_processing[0].arn : 
    aws_lambda_layer_version.data_processing[0].arn
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

output "all_layer_arns" {
  description = "All layer ARNs used by the Lambda function"
  value = var.use_external_layer_arns ? var.external_layer_arns : [
    local.powertools_layer_arn,
    local.data_processing_layer_arn,
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
