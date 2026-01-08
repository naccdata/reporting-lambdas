# AWS Helpers Module Usage

The `common.aws_helpers` module provides standardized AWS service interactions for lambdas, including S3 operations, Lambda utilities, and error handling patterns.

## Components

### S3Manager

S3 operations with retry logic and error handling.

#### Usage

```python
from common.aws_helpers import S3Manager
import polars as pl

# Initialize with bucket name
s3_manager = S3Manager(bucket_name="my-data-bucket")

# Initialize with custom region
s3_manager = S3Manager(bucket_name="my-data-bucket", region="us-west-2")
```

#### Methods

##### `__init__(bucket_name: str, region: str = "us-east-1")`

Initialize S3Manager with bucket and region configuration.

**Parameters:**
- `bucket_name`: S3 bucket name for operations
- `region`: AWS region (defaults to us-east-1)

##### `list_objects_with_prefix(prefix: str, since: Optional[datetime] = None) -> List[str]`

List S3 objects with optional timestamp filtering.

**Parameters:**
- `prefix`: S3 key prefix to filter objects
- `since`: Optional datetime to filter objects modified after this time

**Returns:**
- List of S3 object keys

**Example:**
```python
from datetime import datetime, timedelta

# List all objects with prefix
all_files = s3_manager.list_objects_with_prefix("logs/")

# List only recent files
recent_cutoff = datetime.utcnow() - timedelta(hours=24)
recent_files = s3_manager.list_objects_with_prefix("logs/", since=recent_cutoff)

logger.info("Found files", extra={
    "total_files": len(all_files),
    "recent_files": len(recent_files)
})
```

##### `download_json_object(key: str) -> Dict[str, Any]`

Download and parse JSON object from S3.

**Parameters:**
- `key`: S3 object key

**Returns:**
- Parsed JSON as dictionary

**Raises:**
- `S3ObjectNotFoundError`: If object doesn't exist
- `JSONDecodeError`: If object is not valid JSON

**Example:**
```python
try:
    config_data = s3_manager.download_json_object("config/settings.json")
    logger.info("Config loaded", extra={"keys": list(config_data.keys())})
except S3ObjectNotFoundError:
    logger.warning("Config file not found, using defaults")
    config_data = get_default_config()
except JSONDecodeError as e:
    logger.error("Invalid JSON in config file", extra={"error": str(e)})
    raise
```

##### `upload_parquet(df: pl.DataFrame, key: str) -> None`

Upload Polars DataFrame as parquet file to S3.

**Parameters:**
- `df`: Polars DataFrame to upload
- `key`: S3 key for the uploaded file

**Example:**
```python
import polars as pl

# Create DataFrame
df = pl.DataFrame({
    "timestamp": ["2024-01-01T10:00:00Z", "2024-01-01T11:00:00Z"],
    "value": [100, 200],
    "category": ["A", "B"]
})

# Upload to S3
s3_manager.upload_parquet(df, "data/processed/output.parquet")
logger.info("Data uploaded to S3", extra={"rows": len(df)})
```

##### `download_parquet(key: str) -> pl.DataFrame`

Download parquet file from S3 as Polars DataFrame.

**Parameters:**
- `key`: S3 object key

**Returns:**
- Polars DataFrame

**Example:**
```python
try:
    df = s3_manager.download_parquet("data/checkpoint.parquet")
    logger.info("Checkpoint loaded", extra={"rows": len(df)})
except S3ObjectNotFoundError:
    logger.info("No existing checkpoint found, starting fresh")
    df = pl.DataFrame()
```

##### `object_exists(key: str) -> bool`

Check if S3 object exists.

**Parameters:**
- `key`: S3 object key

**Returns:**
- True if object exists, False otherwise

**Example:**
```python
checkpoint_key = "checkpoints/latest.parquet"
if s3_manager.object_exists(checkpoint_key):
    checkpoint_df = s3_manager.download_parquet(checkpoint_key)
else:
    checkpoint_df = pl.DataFrame()
```

### LambdaUtils

Lambda-specific utilities and decorators.

#### Usage

```python
from common.aws_helpers import LambdaUtils
from aws_lambda_powertools import Logger

logger = Logger()

@LambdaUtils.with_error_handling
def lambda_handler(event, context):
    """Lambda handler with automatic error handling."""
    
    # Parse event
    parsed_event = LambdaUtils.parse_lambda_event(event, "s3")
    
    # Your processing logic
    result = process_data(parsed_event)
    
    return {
        "statusCode": 200,
        "body": result
    }
```

#### Methods

##### `@staticmethod with_error_handling(func: Callable) -> Callable`

Decorator that adds standardized error handling to lambda functions.

**Features:**
- Catches and logs all exceptions
- Returns proper HTTP status codes
- Includes request correlation IDs
- Handles both expected and unexpected errors

**Example:**
```python
@LambdaUtils.with_error_handling
def my_lambda_handler(event, context):
    # Your lambda logic here
    # Exceptions are automatically caught and handled
    return {"statusCode": 200, "body": "Success"}
```

##### `@staticmethod parse_lambda_event(event: Dict[str, Any], event_type: str) -> ParsedEvent`

Parse and validate lambda event based on event type.

**Parameters:**
- `event`: Raw lambda event
- `event_type`: Expected event type ("s3", "api_gateway", "cloudwatch", "custom")

**Returns:**
- `ParsedEvent` object with structured event data

**Example:**
```python
# Parse S3 event
parsed = LambdaUtils.parse_lambda_event(event, "s3")
for record in parsed.s3_records:
    bucket = record.bucket_name
    key = record.object_key
    logger.info("Processing S3 object", extra={"bucket": bucket, "key": key})

# Parse API Gateway event
parsed = LambdaUtils.parse_lambda_event(event, "api_gateway")
logger.info("API request", extra={
    "method": parsed.http_method,
    "path": parsed.path,
    "query_params": parsed.query_parameters
})
```

##### `@staticmethod create_response(status_code: int, body: Any, headers: Optional[Dict] = None) -> Dict[str, Any]`

Create standardized lambda response.

**Parameters:**
- `status_code`: HTTP status code
- `body`: Response body (will be JSON serialized)
- `headers`: Optional HTTP headers

**Returns:**
- Formatted lambda response dictionary

**Example:**
```python
# Success response
success_response = LambdaUtils.create_response(200, {
    "message": "Processing completed",
    "records_processed": 150
})

# Error response
error_response = LambdaUtils.create_response(400, {
    "error": "Invalid input format",
    "details": "Missing required field 'timestamp'"
}, headers={"Content-Type": "application/json"})
```

##### `@staticmethod get_environment_config() -> Dict[str, str]`

Get lambda environment variables with validation.

**Returns:**
- Dictionary of environment variables

**Example:**
```python
config = LambdaUtils.get_environment_config()

# Access required environment variables
source_bucket = config.get("SOURCE_BUCKET")
if not source_bucket:
    raise ValueError("SOURCE_BUCKET environment variable is required")

logger.info("Lambda configuration", extra={
    "source_bucket": source_bucket,
    "log_level": config.get("LOG_LEVEL", "INFO")
})
```

## Best Practices

### S3 Operations

1. **Use appropriate methods for data types:**
   ```python
   # For JSON data
   json_data = s3_manager.download_json_object("config.json")
   
   # For parquet data
   df = s3_manager.download_parquet("data.parquet")
   ```

2. **Handle missing objects gracefully:**
   ```python
   if s3_manager.object_exists("checkpoint.parquet"):
       checkpoint = s3_manager.download_parquet("checkpoint.parquet")
   else:
       checkpoint = create_empty_checkpoint()
   ```

3. **Use prefix filtering for efficiency:**
   ```python
   # More efficient than listing all objects
   recent_files = s3_manager.list_objects_with_prefix(
       "logs/2024/01/", 
       since=datetime.utcnow() - timedelta(days=1)
   )
   ```

### Lambda Error Handling

1. **Always use the error handling decorator:**
   ```python
   @LambdaUtils.with_error_handling
   def lambda_handler(event, context):
       # Your logic here
       pass
   ```

2. **Parse events appropriately:**
   ```python
   # Match event type to your trigger
   if "Records" in event and "s3" in event["Records"][0]:
       parsed = LambdaUtils.parse_lambda_event(event, "s3")
   elif "httpMethod" in event:
       parsed = LambdaUtils.parse_lambda_event(event, "api_gateway")
   ```

3. **Return consistent responses:**
   ```python
   return LambdaUtils.create_response(200, {
       "status": "success",
       "data": result
   })
   ```

### Environment Configuration

```python
# Validate required environment variables at startup
config = LambdaUtils.get_environment_config()
required_vars = ["SOURCE_BUCKET", "DESTINATION_BUCKET"]

for var in required_vars:
    if not config.get(var):
        raise ValueError(f"Required environment variable {var} is not set")
```

## Common Patterns

### S3 Event Processing

```python
@LambdaUtils.with_error_handling
def s3_event_handler(event, context):
    """Process S3 events with error handling."""
    
    parsed_event = LambdaUtils.parse_lambda_event(event, "s3")
    s3_manager = S3Manager(bucket_name=parsed_event.s3_records[0].bucket_name)
    
    results = []
    for record in parsed_event.s3_records:
        try:
            # Download and process file
            if record.object_key.endswith('.json'):
                data = s3_manager.download_json_object(record.object_key)
                processed_data = process_json_data(data)
            elif record.object_key.endswith('.parquet'):
                df = s3_manager.download_parquet(record.object_key)
                processed_data = process_dataframe(df)
            
            results.append({
                "key": record.object_key,
                "status": "success",
                "records": len(processed_data) if hasattr(processed_data, '__len__') else 1
            })
            
        except Exception as e:
            logger.error("Failed to process file", extra={
                "key": record.object_key,
                "error": str(e)
            })
            results.append({
                "key": record.object_key,
                "status": "failed",
                "error": str(e)
            })
    
    return LambdaUtils.create_response(200, {
        "processed_files": len(results),
        "results": results
    })
```

### Incremental Data Processing

```python
def process_incremental_data(source_prefix: str, checkpoint_key: str):
    """Process new data since last checkpoint."""
    
    config = LambdaUtils.get_environment_config()
    s3_manager = S3Manager(bucket_name=config["DATA_BUCKET"])
    
    # Get last checkpoint time
    last_checkpoint = None
    if s3_manager.object_exists(checkpoint_key):
        checkpoint_df = s3_manager.download_parquet(checkpoint_key)
        if len(checkpoint_df) > 0:
            last_checkpoint = checkpoint_df["timestamp"].max()
    
    # List new files
    new_files = s3_manager.list_objects_with_prefix(
        source_prefix, 
        since=last_checkpoint
    )
    
    if not new_files:
        logger.info("No new files to process")
        return
    
    # Process new files
    all_data = []
    for file_key in new_files:
        try:
            if file_key.endswith('.json'):
                data = s3_manager.download_json_object(file_key)
                all_data.extend(data if isinstance(data, list) else [data])
        except Exception as e:
            logger.error("Failed to process file", extra={
                "file": file_key,
                "error": str(e)
            })
    
    if all_data:
        # Convert to DataFrame and upload
        new_df = pl.DataFrame(all_data)
        s3_manager.upload_parquet(new_df, f"processed/{checkpoint_key}")
        
        logger.info("Incremental processing completed", extra={
            "new_files": len(new_files),
            "new_records": len(new_df)
        })
```

## Testing

### Unit Testing

```python
import pytest
from unittest.mock import Mock, patch
from common.aws_helpers import S3Manager, LambdaUtils

@patch('boto3.client')
def test_s3_manager_list_objects(mock_boto_client):
    """Test S3Manager list objects functionality."""
    
    # Mock S3 response
    mock_s3 = Mock()
    mock_boto_client.return_value = mock_s3
    mock_s3.list_objects_v2.return_value = {
        'Contents': [
            {'Key': 'logs/file1.json', 'LastModified': datetime.utcnow()},
            {'Key': 'logs/file2.json', 'LastModified': datetime.utcnow()}
        ]
    }
    
    s3_manager = S3Manager("test-bucket")
    files = s3_manager.list_objects_with_prefix("logs/")
    
    assert len(files) == 2
    assert "logs/file1.json" in files
    assert "logs/file2.json" in files

def test_lambda_utils_create_response():
    """Test LambdaUtils response creation."""
    
    response = LambdaUtils.create_response(200, {"message": "success"})
    
    assert response["statusCode"] == 200
    assert "message" in response["body"]
    assert response["headers"]["Content-Type"] == "application/json"
```

### Integration Testing

```python
import pytest
import boto3
from moto import mock_s3
import polars as pl

@mock_s3
def test_s3_manager_integration():
    """Integration test for S3Manager with mocked S3."""
    
    # Create mock S3 bucket
    s3_client = boto3.client('s3', region_name='us-east-1')
    s3_client.create_bucket(Bucket='test-bucket')
    
    # Test upload and download
    s3_manager = S3Manager('test-bucket')
    test_df = pl.DataFrame({"id": [1, 2], "name": ["A", "B"]})
    
    # Upload DataFrame
    s3_manager.upload_parquet(test_df, "test.parquet")
    
    # Download and verify
    downloaded_df = s3_manager.download_parquet("test.parquet")
    assert len(downloaded_df) == 2
    assert downloaded_df.columns == ["id", "name"]
```