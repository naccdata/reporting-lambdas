# Models Module Usage

The `common.models` module provides shared Pydantic models for common data structures used across reporting lambdas. These models ensure consistent data validation and serialization patterns.

## Components

### ReportingEvent

Base model for lambda execution metadata and cross-lambda communication.

#### Usage

```python
from common.models import ReportingEvent
from datetime import datetime

# Create a reporting event
event = ReportingEvent(
    timestamp=datetime.utcnow(),
    source="api_ingestion",
    event_type="data_received",
    data={"records": 150, "source_system": "crm"}
)

# Serialize to JSON
event_json = event.model_dump_json()

# Parse from dictionary
event_dict = {
    "timestamp": "2024-01-01T10:00:00Z",
    "source": "database_export",
    "event_type": "export_completed",
    "data": {"table": "customers", "rows": 1000}
}
event = ReportingEvent(**event_dict)
```

#### Fields

- `timestamp` (datetime): Event timestamp (required)
- `source` (str): Data source identifier (required)
- `event_type` (str): Type of event (required)
- `data` (Dict[str, Any]): Event payload (required)
- `metadata` (Optional[Dict[str, Any]]): Additional metadata (optional)

#### Methods

##### `model_dump() -> Dict[str, Any]`

Convert model to dictionary with proper serialization.

**Example:**
```python
event_dict = event.model_dump()
logger.info("Event created", extra=event_dict)
```

##### `model_dump_json() -> str`

Convert model to JSON string with datetime serialization.

**Example:**
```python
event_json = event.model_dump_json()
# Store in database or send to API
store_event(event_json)
```

### DataSourceConfig

Configuration model for data sources used by lambdas.

#### Usage

```python
from common.models import DataSourceConfig

# S3 data source
s3_config = DataSourceConfig(
    name="customer_data",
    type="s3",
    connection_params={
        "bucket": "customer-data-bucket",
        "prefix": "exports/",
        "region": "us-east-1"
    },
    polling_interval=3600,  # 1 hour
    output_format="parquet"
)

# API data source
api_config = DataSourceConfig(
    name="sales_api",
    type="api",
    connection_params={
        "base_url": "https://api.example.com",
        "auth_token": "secret_token",
        "endpoints": ["sales", "customers"]
    },
    polling_interval=900,  # 15 minutes
    output_format="json"
)

# Database data source
db_config = DataSourceConfig(
    name="analytics_db",
    type="database",
    connection_params={
        "host": "db.example.com",
        "database": "analytics",
        "table": "events",
        "connection_string": "postgresql://user:pass@host:5432/db"
    },
    output_format="parquet"
)
```

#### Fields

- `name` (str): Data source name (required)
- `type` (Literal["s3", "api", "database", "sqs"]): Source type (required)
- `connection_params` (Dict[str, Any]): Connection parameters (required)
- `polling_interval` (Optional[int]): Polling interval in seconds (optional)
- `output_format` (Literal["parquet", "json", "csv"]): Output format (default: "parquet")

#### Validation

The model validates that connection parameters are appropriate for the source type:

```python
# This will raise ValidationError - missing required S3 parameters
invalid_config = DataSourceConfig(
    name="bad_s3",
    type="s3",
    connection_params={"invalid": "params"}
)
```

### ProcessingMetrics

Standardized model for lambda processing operations metrics.

#### Usage

```python
from common.models import ProcessingMetrics
from datetime import datetime

# Create metrics during processing
start_time = datetime.utcnow()

# ... processing logic ...

end_time = datetime.utcnow()

metrics = ProcessingMetrics(
    start_time=start_time,
    end_time=end_time,
    records_processed=1500,
    records_failed=25,
    bytes_processed=1024000,  # 1MB
    output_files_created=3,
    errors=["Invalid timestamp in record 100", "Missing required field in record 250"]
)

# Use computed properties
logger.info("Processing completed", extra={
    "duration_seconds": metrics.duration_seconds,
    "success_rate": metrics.success_rate,
    "throughput_per_second": metrics.records_processed / metrics.duration_seconds
})
```

#### Fields

- `start_time` (datetime): Processing start time (required)
- `end_time` (datetime): Processing end time (required)
- `records_processed` (int): Number of successfully processed records (default: 0)
- `records_failed` (int): Number of failed records (default: 0)
- `bytes_processed` (int): Total bytes processed (default: 0)
- `output_files_created` (int): Number of output files created (default: 0)
- `errors` (List[str]): List of error messages (default: empty list)

#### Computed Properties

##### `duration_seconds -> float`

Calculate processing duration in seconds.

**Example:**
```python
duration = metrics.duration_seconds
logger.info(f"Processing took {duration:.2f} seconds")
```

##### `success_rate -> float`

Calculate success rate as a percentage (0.0 to 1.0).

**Example:**
```python
success_rate = metrics.success_rate
if success_rate < 0.95:
    logger.warning(f"Low success rate: {success_rate:.2%}")
```

## Best Practices

### Event Modeling

1. **Use consistent event types:**
   ```python
   # Good: Consistent naming convention
   events = [
       ReportingEvent(source="api", event_type="data_received", ...),
       ReportingEvent(source="api", event_type="data_processed", ...),
       ReportingEvent(source="api", event_type="data_exported", ...)
   ]
   ```

2. **Include relevant metadata:**
   ```python
   event = ReportingEvent(
       timestamp=datetime.utcnow(),
       source="customer_api",
       event_type="sync_completed",
       data={"customers_synced": 150},
       metadata={
           "lambda_request_id": context.aws_request_id,
           "version": "1.2.0",
           "environment": "production"
       }
   )
   ```

### Configuration Management

1. **Validate configurations at startup:**
   ```python
   def load_data_source_config(config_dict: Dict[str, Any]) -> DataSourceConfig:
       """Load and validate data source configuration."""
       try:
           return DataSourceConfig(**config_dict)
       except ValidationError as e:
           logger.error("Invalid data source configuration", extra={
               "errors": e.errors(),
               "config": config_dict
           })
           raise
   ```

2. **Use environment variables for sensitive data:**
   ```python
   import os
   
   config = DataSourceConfig(
       name="secure_api",
       type="api",
       connection_params={
           "base_url": os.environ["API_BASE_URL"],
           "auth_token": os.environ["API_AUTH_TOKEN"]
       }
   )
   ```

### Metrics Collection

1. **Create metrics objects early:**
   ```python
   def process_data(data: List[Dict]) -> ProcessingMetrics:
       """Process data and return metrics."""
       start_time = datetime.utcnow()
       
       metrics = ProcessingMetrics(
           start_time=start_time,
           end_time=start_time  # Will be updated at the end
       )
       
       try:
           # Processing logic
           for record in data:
               try:
                   process_record(record)
                   metrics.records_processed += 1
               except Exception as e:
                   metrics.records_failed += 1
                   metrics.errors.append(f"Record {record.get('id', 'unknown')}: {str(e)}")
       
       finally:
           metrics.end_time = datetime.utcnow()
       
       return metrics
   ```

2. **Log metrics consistently:**
   ```python
   logger.info("Processing metrics", extra={
       "duration_seconds": metrics.duration_seconds,
       "records_processed": metrics.records_processed,
       "records_failed": metrics.records_failed,
       "success_rate": metrics.success_rate,
       "bytes_processed": metrics.bytes_processed
   })
   ```

## Common Patterns

### Event-Driven Processing

```python
from common.models import ReportingEvent, ProcessingMetrics
from common.aws_helpers import S3Manager

def process_reporting_events(events: List[Dict[str, Any]]) -> ProcessingMetrics:
    """Process a batch of reporting events."""
    
    start_time = datetime.utcnow()
    metrics = ProcessingMetrics(start_time=start_time, end_time=start_time)
    
    # Validate and parse events
    valid_events = []
    for event_data in events:
        try:
            event = ReportingEvent(**event_data)
            valid_events.append(event)
            metrics.records_processed += 1
        except ValidationError as e:
            metrics.records_failed += 1
            metrics.errors.append(f"Invalid event: {str(e)}")
    
    # Process valid events
    s3_manager = S3Manager("processed-events")
    
    if valid_events:
        # Convert to DataFrame for batch processing
        event_dicts = [event.model_dump() for event in valid_events]
        df = pl.DataFrame(event_dicts)
        
        # Upload processed events
        output_key = f"events/{datetime.utcnow().strftime('%Y/%m/%d')}/batch.parquet"
        s3_manager.upload_parquet(df, output_key)
        metrics.output_files_created = 1
        metrics.bytes_processed = len(df.write_parquet())
    
    metrics.end_time = datetime.utcnow()
    return metrics
```

### Configuration-Driven Lambda

```python
from common.models import DataSourceConfig, ProcessingMetrics
from common.aws_helpers import S3Manager

def lambda_handler(event, context):
    """Lambda handler that uses configuration-driven processing."""
    
    # Load configuration from event or environment
    config_data = event.get("data_source_config")
    if not config_data:
        return {"statusCode": 400, "body": "Missing data_source_config"}
    
    try:
        config = DataSourceConfig(**config_data)
    except ValidationError as e:
        return {
            "statusCode": 400,
            "body": f"Invalid configuration: {e.errors()}"
        }
    
    # Process based on configuration
    if config.type == "s3":
        metrics = process_s3_source(config)
    elif config.type == "api":
        metrics = process_api_source(config)
    elif config.type == "database":
        metrics = process_database_source(config)
    else:
        return {
            "statusCode": 400,
            "body": f"Unsupported source type: {config.type}"
        }
    
    # Return processing results
    return {
        "statusCode": 200,
        "body": {
            "source_name": config.name,
            "processing_metrics": metrics.model_dump(),
            "success_rate": metrics.success_rate
        }
    }

def process_s3_source(config: DataSourceConfig) -> ProcessingMetrics:
    """Process S3 data source based on configuration."""
    start_time = datetime.utcnow()
    
    s3_manager = S3Manager(
        bucket_name=config.connection_params["bucket"],
        region=config.connection_params.get("region", "us-east-1")
    )
    
    # List and process files
    prefix = config.connection_params.get("prefix", "")
    files = s3_manager.list_objects_with_prefix(prefix)
    
    metrics = ProcessingMetrics(
        start_time=start_time,
        end_time=datetime.utcnow(),
        records_processed=len(files),
        output_files_created=1 if files else 0
    )
    
    return metrics
```

### Metrics Aggregation

```python
from typing import List
from common.models import ProcessingMetrics

def aggregate_metrics(metrics_list: List[ProcessingMetrics]) -> ProcessingMetrics:
    """Aggregate multiple processing metrics into a summary."""
    
    if not metrics_list:
        now = datetime.utcnow()
        return ProcessingMetrics(start_time=now, end_time=now)
    
    # Find overall time range
    start_time = min(m.start_time for m in metrics_list)
    end_time = max(m.end_time for m in metrics_list)
    
    # Aggregate counts
    total_processed = sum(m.records_processed for m in metrics_list)
    total_failed = sum(m.records_failed for m in metrics_list)
    total_bytes = sum(m.bytes_processed for m in metrics_list)
    total_files = sum(m.output_files_created for m in metrics_list)
    
    # Combine all errors
    all_errors = []
    for m in metrics_list:
        all_errors.extend(m.errors)
    
    return ProcessingMetrics(
        start_time=start_time,
        end_time=end_time,
        records_processed=total_processed,
        records_failed=total_failed,
        bytes_processed=total_bytes,
        output_files_created=total_files,
        errors=all_errors
    )
```

## Testing

### Unit Testing

```python
import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError
from common.models import ReportingEvent, DataSourceConfig, ProcessingMetrics

def test_reporting_event_creation():
    """Test ReportingEvent model creation and validation."""
    
    event = ReportingEvent(
        timestamp=datetime.utcnow(),
        source="test_source",
        event_type="test_event",
        data={"key": "value"}
    )
    
    assert event.source == "test_source"
    assert event.event_type == "test_event"
    assert event.data["key"] == "value"
    assert event.metadata is None

def test_processing_metrics_computed_properties():
    """Test ProcessingMetrics computed properties."""
    
    start = datetime.utcnow()
    end = start + timedelta(seconds=60)
    
    metrics = ProcessingMetrics(
        start_time=start,
        end_time=end,
        records_processed=100,
        records_failed=10
    )
    
    assert metrics.duration_seconds == 60.0
    assert metrics.success_rate == 100 / 110  # 100 / (100 + 10)

def test_data_source_config_validation():
    """Test DataSourceConfig validation."""
    
    # Valid configuration
    config = DataSourceConfig(
        name="test_source",
        type="s3",
        connection_params={"bucket": "test-bucket"}
    )
    assert config.name == "test_source"
    assert config.type == "s3"
    
    # Invalid type should raise ValidationError
    with pytest.raises(ValidationError):
        DataSourceConfig(
            name="invalid",
            type="invalid_type",
            connection_params={}
        )
```

### Property-Based Testing

```python
from hypothesis import given, strategies as st
from datetime import datetime

@given(
    records_processed=st.integers(min_value=0, max_value=10000),
    records_failed=st.integers(min_value=0, max_value=1000)
)
def test_processing_metrics_success_rate_property(records_processed, records_failed):
    """Property: Success rate should always be between 0 and 1."""
    
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(seconds=1)
    
    metrics = ProcessingMetrics(
        start_time=start_time,
        end_time=end_time,
        records_processed=records_processed,
        records_failed=records_failed
    )
    
    success_rate = metrics.success_rate
    assert 0.0 <= success_rate <= 1.0
    
    # If no records processed or failed, success rate should be 0
    if records_processed == 0 and records_failed == 0:
        assert success_rate == 0.0
```