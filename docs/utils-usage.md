# Utils Module Usage

The `common.utils` module provides general utilities for common operations including error handling, date processing, and string manipulation used across reporting lambdas.

## Components

### Error Handling (`common.utils.error_handling`)

Standardized error handling utilities for consistent error responses and logging.

#### Usage

```python
from common.utils.error_handling import (
    handle_validation_error,
    handle_processing_error,
    create_error_response,
    log_error_with_context
)
from pydantic import ValidationError
from aws_lambda_powertools import Logger

logger = Logger()

def lambda_handler(event, context):
    """Lambda handler with standardized error handling."""
    
    try:
        # Your processing logic
        result = process_data(event)
        return {"statusCode": 200, "body": result}
        
    except ValidationError as e:
        return handle_validation_error(e, context.aws_request_id)
        
    except Exception as e:
        return handle_processing_error(e, context.aws_request_id)
```

#### Functions

##### `handle_validation_error(error: ValidationError, request_id: str) -> Dict[str, Any]`

Handle Pydantic validation errors with standardized response format.

**Parameters:**
- `error`: Pydantic ValidationError
- `request_id`: Request correlation ID

**Returns:**
- Standardized error response dictionary

**Example:**
```python
from pydantic import BaseModel, ValidationError

class UserData(BaseModel):
    name: str
    age: int

try:
    user = UserData(**{"name": "John", "age": "invalid"})
except ValidationError as e:
    error_response = handle_validation_error(e, "req-123")
    # Returns: {"statusCode": 400, "body": {...}}
```

##### `handle_processing_error(error: Exception, request_id: str) -> Dict[str, Any]`

Handle general processing errors with logging and standardized response.

**Parameters:**
- `error`: Any exception
- `request_id`: Request correlation ID

**Returns:**
- Standardized error response dictionary

**Example:**
```python
try:
    result = risky_operation()
except Exception as e:
    return handle_processing_error(e, context.aws_request_id)
```

##### `create_error_response(status_code: int, message: str, details: Optional[Dict] = None) -> Dict[str, Any]`

Create standardized error response.

**Parameters:**
- `status_code`: HTTP status code
- `message`: Error message
- `details`: Optional additional error details

**Returns:**
- Formatted error response

**Example:**
```python
# Simple error response
error_response = create_error_response(404, "Resource not found")

# Error response with details
error_response = create_error_response(
    400, 
    "Invalid input", 
    details={"field": "timestamp", "issue": "Invalid format"}
)
```

##### `log_error_with_context(error: Exception, context: Dict[str, Any], logger: Logger) -> None`

Log error with additional context information.

**Parameters:**
- `error`: Exception to log
- `context`: Additional context information
- `logger`: Logger instance

**Example:**
```python
try:
    process_file(filename)
except Exception as e:
    log_error_with_context(e, {
        "filename": filename,
        "file_size": os.path.getsize(filename),
        "operation": "file_processing"
    }, logger)
    raise
```

### Date Helpers (`common.utils.date_helpers`)

Utilities for date and time processing commonly needed in reporting lambdas.

#### Usage

```python
from common.utils.date_helpers import (
    parse_iso_datetime,
    format_datetime_for_s3,
    get_date_range,
    is_business_day,
    get_month_boundaries
)
from datetime import datetime, date
```

#### Functions

##### `parse_iso_datetime(date_string: str) -> datetime`

Parse ISO format datetime string with timezone handling.

**Parameters:**
- `date_string`: ISO format datetime string

**Returns:**
- Parsed datetime object

**Example:**
```python
# Parse various ISO formats
dt1 = parse_iso_datetime("2024-01-01T10:00:00Z")
dt2 = parse_iso_datetime("2024-01-01T10:00:00+00:00")
dt3 = parse_iso_datetime("2024-01-01T10:00:00.123456Z")

logger.info("Parsed datetime", extra={"datetime": dt1.isoformat()})
```

##### `format_datetime_for_s3(dt: datetime) -> str`

Format datetime for S3 key naming (YYYY/MM/DD/HH format).

**Parameters:**
- `dt`: Datetime to format

**Returns:**
- S3-friendly path string

**Example:**
```python
now = datetime.utcnow()
s3_path = format_datetime_for_s3(now)
# Returns: "2024/01/15/14" for 2024-01-15 14:30:00

s3_key = f"data/{s3_path}/events.parquet"
# Results in: "data/2024/01/15/14/events.parquet"
```

##### `get_date_range(start_date: date, end_date: date) -> List[date]`

Generate list of dates between start and end dates (inclusive).

**Parameters:**
- `start_date`: Start date
- `end_date`: End date

**Returns:**
- List of date objects

**Example:**
```python
from datetime import date

start = date(2024, 1, 1)
end = date(2024, 1, 5)
date_range = get_date_range(start, end)
# Returns: [date(2024, 1, 1), date(2024, 1, 2), ..., date(2024, 1, 5)]

# Process data for each date
for process_date in date_range:
    process_daily_data(process_date)
```

##### `is_business_day(check_date: date) -> bool`

Check if a date is a business day (Monday-Friday, excluding common holidays).

**Parameters:**
- `check_date`: Date to check

**Returns:**
- True if business day, False otherwise

**Example:**
```python
today = date.today()
if is_business_day(today):
    logger.info("Processing business day data")
    process_business_data()
else:
    logger.info("Skipping weekend/holiday processing")
```

##### `get_month_boundaries(year: int, month: int) -> Tuple[datetime, datetime]`

Get start and end datetime for a given month.

**Parameters:**
- `year`: Year
- `month`: Month (1-12)

**Returns:**
- Tuple of (start_datetime, end_datetime)

**Example:**
```python
start, end = get_month_boundaries(2024, 1)
# Returns: (datetime(2024, 1, 1, 0, 0, 0), datetime(2024, 1, 31, 23, 59, 59))

# Use for monthly reporting
monthly_data = get_data_for_period(start, end)
```

### String Helpers (`common.utils.string_helpers`)

String processing and validation utilities.

#### Usage

```python
from common.utils.string_helpers import (
    sanitize_filename,
    validate_s3_key,
    extract_numbers,
    normalize_whitespace,
    truncate_string
)
```

#### Functions

##### `sanitize_filename(filename: str) -> str`

Sanitize filename for safe filesystem usage.

**Parameters:**
- `filename`: Original filename

**Returns:**
- Sanitized filename

**Example:**
```python
# Remove unsafe characters
safe_name = sanitize_filename("my file (2024).txt")
# Returns: "my_file_2024.txt"

# Use for generating output filenames
output_file = f"processed_{sanitize_filename(input_filename)}"
```

##### `validate_s3_key(key: str) -> bool`

Validate S3 object key format.

**Parameters:**
- `key`: S3 key to validate

**Returns:**
- True if valid, False otherwise

**Example:**
```python
# Validate S3 keys before upload
keys_to_upload = ["data/file1.parquet", "logs/2024/01/events.json"]

for key in keys_to_upload:
    if validate_s3_key(key):
        upload_to_s3(key, data)
    else:
        logger.warning("Invalid S3 key", extra={"key": key})
```

##### `extract_numbers(text: str) -> List[int]`

Extract all numbers from a string.

**Parameters:**
- `text`: Input string

**Returns:**
- List of integers found in the string

**Example:**
```python
# Extract numbers from filenames or IDs
filename = "report_2024_01_15_v2.pdf"
numbers = extract_numbers(filename)
# Returns: [2024, 1, 15, 2]

# Use for parsing structured filenames
year, month, day, version = numbers
```

##### `normalize_whitespace(text: str) -> str`

Normalize whitespace in text (remove extra spaces, tabs, newlines).

**Parameters:**
- `text`: Input text

**Returns:**
- Normalized text

**Example:**
```python
# Clean up messy text data
messy_text = "  Hello    world  \n\t  "
clean_text = normalize_whitespace(messy_text)
# Returns: "Hello world"

# Use for data cleaning
cleaned_data = [normalize_whitespace(item) for item in raw_data]
```

##### `truncate_string(text: str, max_length: int, suffix: str = "...") -> str`

Truncate string to maximum length with optional suffix.

**Parameters:**
- `text`: Input text
- `max_length`: Maximum allowed length
- `suffix`: Suffix to add when truncating (default: "...")

**Returns:**
- Truncated string

**Example:**
```python
# Truncate long descriptions for logging
long_description = "This is a very long description that needs to be truncated"
short_desc = truncate_string(long_description, 30)
# Returns: "This is a very long descrip..."

# Use for database fields with length limits
truncated_comment = truncate_string(user_comment, 255)
```

## Best Practices

### Error Handling

1. **Use consistent error handling patterns:**
   ```python
   @LambdaUtils.with_error_handling
   def lambda_handler(event, context):
       try:
           result = process_data(event)
           return {"statusCode": 200, "body": result}
       except ValidationError as e:
           return handle_validation_error(e, context.aws_request_id)
       except Exception as e:
           return handle_processing_error(e, context.aws_request_id)
   ```

2. **Log errors with context:**
   ```python
   try:
       process_file(filename)
   except Exception as e:
       log_error_with_context(e, {
           "filename": filename,
           "operation": "file_processing",
           "lambda_request_id": context.aws_request_id
       }, logger)
       raise
   ```

### Date Processing

1. **Always use UTC for internal processing:**
   ```python
   # Parse input dates to UTC
   input_date = parse_iso_datetime(event["timestamp"])
   
   # Process in UTC
   processed_data = process_for_date(input_date)
   
   # Format for output/storage
   s3_path = format_datetime_for_s3(input_date)
   ```

2. **Handle timezone-aware operations:**
   ```python
   # For business logic that depends on business days
   process_date = datetime.utcnow().date()
   if is_business_day(process_date):
       run_business_day_processing()
   ```

### String Processing

1. **Sanitize user input:**
   ```python
   # Always sanitize filenames from user input
   user_filename = event.get("filename", "default.txt")
   safe_filename = sanitize_filename(user_filename)
   
   # Validate S3 keys before operations
   s3_key = event.get("s3_key")
   if not validate_s3_key(s3_key):
       return create_error_response(400, "Invalid S3 key format")
   ```

2. **Clean data consistently:**
   ```python
   # Normalize text data before processing
   cleaned_records = []
   for record in raw_records:
       cleaned_record = {
           key: normalize_whitespace(value) if isinstance(value, str) else value
           for key, value in record.items()
       }
       cleaned_records.append(cleaned_record)
   ```

## Common Patterns

### Robust File Processing

```python
from common.utils.error_handling import log_error_with_context
from common.utils.string_helpers import sanitize_filename, validate_s3_key
from common.utils.date_helpers import format_datetime_for_s3

def process_file_safely(filename: str, content: bytes, context) -> Dict[str, Any]:
    """Process file with comprehensive error handling and validation."""
    
    try:
        # Sanitize filename
        safe_filename = sanitize_filename(filename)
        
        # Generate S3 key with date partitioning
        now = datetime.utcnow()
        date_path = format_datetime_for_s3(now)
        s3_key = f"processed/{date_path}/{safe_filename}"
        
        # Validate S3 key
        if not validate_s3_key(s3_key):
            return create_error_response(400, "Generated S3 key is invalid")
        
        # Process file content
        processed_content = process_content(content)
        
        # Upload to S3
        upload_to_s3(s3_key, processed_content)
        
        return {
            "statusCode": 200,
            "body": {
                "original_filename": filename,
                "processed_filename": safe_filename,
                "s3_key": s3_key,
                "processed_at": now.isoformat()
            }
        }
        
    except Exception as e:
        log_error_with_context(e, {
            "filename": filename,
            "operation": "file_processing",
            "request_id": context.aws_request_id
        }, logger)
        
        return handle_processing_error(e, context.aws_request_id)
```

### Date-Based Data Processing

```python
from common.utils.date_helpers import get_date_range, is_business_day, get_month_boundaries

def process_monthly_report(year: int, month: int) -> ProcessingMetrics:
    """Process monthly report with business day filtering."""
    
    start_time = datetime.utcnow()
    metrics = ProcessingMetrics(start_time=start_time, end_time=start_time)
    
    # Get month boundaries
    month_start, month_end = get_month_boundaries(year, month)
    
    # Get all dates in month
    start_date = month_start.date()
    end_date = month_end.date()
    all_dates = get_date_range(start_date, end_date)
    
    # Filter to business days only
    business_days = [d for d in all_dates if is_business_day(d)]
    
    logger.info("Processing monthly report", extra={
        "year": year,
        "month": month,
        "total_days": len(all_dates),
        "business_days": len(business_days)
    })
    
    # Process each business day
    for process_date in business_days:
        try:
            daily_data = get_daily_data(process_date)
            processed_data = process_daily_data(daily_data)
            
            # Generate S3 key with date partitioning
            date_str = process_date.strftime("%Y/%m/%d")
            s3_key = f"reports/{date_str}/daily_report.parquet"
            
            upload_to_s3(s3_key, processed_data)
            
            metrics.records_processed += len(processed_data)
            metrics.output_files_created += 1
            
        except Exception as e:
            metrics.records_failed += 1
            metrics.errors.append(f"Failed to process {process_date}: {str(e)}")
            logger.error("Daily processing failed", extra={
                "date": process_date.isoformat(),
                "error": str(e)
            })
    
    metrics.end_time = datetime.utcnow()
    return metrics
```

### Data Cleaning Pipeline

```python
from common.utils.string_helpers import normalize_whitespace, truncate_string, extract_numbers

def clean_customer_data(raw_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean customer data with standardized string processing."""
    
    cleaned_records = []
    
    for record in raw_records:
        try:
            # Clean string fields
            cleaned_record = {
                "customer_id": str(record.get("customer_id", "")).strip(),
                "name": normalize_whitespace(record.get("name", "")),
                "email": record.get("email", "").strip().lower(),
                "phone": "".join(extract_numbers(record.get("phone", ""))),
                "address": normalize_whitespace(record.get("address", "")),
                "notes": truncate_string(
                    normalize_whitespace(record.get("notes", "")), 
                    500
                )
            }
            
            # Validate required fields
            if not cleaned_record["customer_id"] or not cleaned_record["name"]:
                logger.warning("Skipping record with missing required fields", extra={
                    "customer_id": cleaned_record["customer_id"],
                    "name": cleaned_record["name"]
                })
                continue
            
            cleaned_records.append(cleaned_record)
            
        except Exception as e:
            logger.error("Failed to clean record", extra={
                "record": record,
                "error": str(e)
            })
    
    logger.info("Data cleaning completed", extra={
        "input_records": len(raw_records),
        "output_records": len(cleaned_records),
        "cleaned_percentage": len(cleaned_records) / len(raw_records) * 100
    })
    
    return cleaned_records
```

## Testing

### Unit Testing

```python
import pytest
from datetime import datetime, date
from common.utils.error_handling import create_error_response
from common.utils.date_helpers import parse_iso_datetime, is_business_day
from common.utils.string_helpers import sanitize_filename, normalize_whitespace

def test_error_response_creation():
    """Test error response creation."""
    response = create_error_response(400, "Test error")
    
    assert response["statusCode"] == 400
    assert "Test error" in response["body"]

def test_date_parsing():
    """Test ISO datetime parsing."""
    dt = parse_iso_datetime("2024-01-01T10:00:00Z")
    
    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 10

def test_business_day_detection():
    """Test business day detection."""
    # Monday
    monday = date(2024, 1, 1)  # Assuming this is a Monday
    assert is_business_day(monday) == True
    
    # Saturday
    saturday = date(2024, 1, 6)  # Assuming this is a Saturday
    assert is_business_day(saturday) == False

def test_filename_sanitization():
    """Test filename sanitization."""
    unsafe_name = "my file (2024) [version 1].txt"
    safe_name = sanitize_filename(unsafe_name)
    
    assert " " not in safe_name
    assert "(" not in safe_name
    assert ")" not in safe_name
    assert "[" not in safe_name
    assert "]" not in safe_name

def test_whitespace_normalization():
    """Test whitespace normalization."""
    messy_text = "  Hello    world  \n\t  "
    clean_text = normalize_whitespace(messy_text)
    
    assert clean_text == "Hello world"
    assert "  " not in clean_text
    assert "\n" not in clean_text
    assert "\t" not in clean_text
```

### Property-Based Testing

```python
from hypothesis import given, strategies as st

@given(text=st.text())
def test_normalize_whitespace_property(text):
    """Property: Normalized text should not have consecutive spaces."""
    normalized = normalize_whitespace(text)
    
    # Should not contain consecutive spaces
    assert "  " not in normalized
    # Should not start or end with whitespace
    assert normalized == normalized.strip()

@given(
    filename=st.text(min_size=1, max_size=100),
    max_length=st.integers(min_value=10, max_value=50)
)
def test_truncate_string_property(filename, max_length):
    """Property: Truncated string should never exceed max length."""
    truncated = truncate_string(filename, max_length)
    
    assert len(truncated) <= max_length
    
    # If original was longer, should end with "..."
    if len(filename) > max_length:
        assert truncated.endswith("...")
```