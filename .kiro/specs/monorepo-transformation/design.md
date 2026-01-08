# Design Document: Monorepo Transformation

## Overview

This design transforms the current single-lambda repository into a comprehensive monorepo for hosting multiple reporting lambdas. The transformation will establish a `common/` directory for shared code, standardize lambda organization patterns, update documentation, and create templates for rapid development of new data processing lambdas.

The design preserves the existing `event_log_checkpoint` lambda while establishing patterns that support scalable development of additional reporting functions that extract data from various sources and create parquet tables for analytical use.

## Architecture

### Repository Structure

The transformed repository will follow this structure:

```
reporting-lambdas/
├── .devcontainer/              # Existing dev container setup
├── .github/                    # GitHub workflows
├── .kiro/                      # Kiro specs and steering
├── bin/                        # Existing dev container scripts
├── common/                     # NEW: Shared code across lambdas
│   ├── src/python/
│   │   ├── data_processing/    # Parquet, validation utilities
│   │   ├── aws_helpers/        # S3, Lambda utilities
│   │   ├── models/             # Common Pydantic models
│   │   └── utils/              # General utilities
│   └── test/python/            # Tests for common modules
├── lambda/                     # Lambda functions directory
│   ├── event_log_checkpoint/   # EXISTING: Preserved as-is
│   └── template/               # NEW: Template for new lambdas
├── terraform/                  # NEW: Global infrastructure modules
│   └── modules/                # Reusable Terraform modules
├── docs/                       # Enhanced documentation
├── context/                    # EXISTING: Reference patterns
├── BUILD                       # Root build configuration
├── pants.toml                  # Enhanced Pants configuration
├── requirements.txt            # Project dependencies
└── README.md                   # Updated monorepo documentation
```

### Component Architecture

#### Common Code Organization

The `common/` directory will contain reusable modules organized by functionality:

1. **data_processing/**: Parquet generation, data validation, schema management
2. **aws_helpers/**: S3 operations, Lambda utilities, CloudWatch logging
3. **models/**: Shared Pydantic models for common data structures
4. **utils/**: General utilities (date handling, string processing, etc.)

#### Lambda Organization Pattern

Each lambda follows a consistent structure:

```
lambda/{lambda_name}/
├── main.tf                     # Terraform configuration
├── variables.tf                # Terraform variables
├── outputs.tf                  # Terraform outputs
├── README.md                   # Lambda-specific documentation
├── src/python/
│   └── {lambda_name}_lambda/
│       ├── BUILD                    # Pants build configuration
│       ├── lambda_function.py       # Main handler
│       └── reporting_processor.py   # Reporting processor modules
└── test/python/
    ├── BUILD                        # Test build configuration
    ├── test_lambda_function.py      # Handler tests
    └── test_reporting_processor.py  # Reporting processor tests
```

## Components and Interfaces

### Common Code Modules

#### DataProcessing Module

**Location**: `common/src/python/data_processing/`

**Purpose**: Provides utilities for data validation, transformation, and parquet file generation.

**Key Components**:
- `ParquetWriter`: Standardized parquet file creation with compression and schema validation
- `DataValidator`: Common validation patterns for reporting data
- `SchemaManager`: Schema evolution and compatibility checking
- `DataTransformer`: Common data transformation utilities

**Interface**:
```python
class ParquetWriter:
    def __init__(self, compression: str = "snappy", schema: Optional[Schema] = None)
    def write_dataframe(self, df: polars.DataFrame, output_path: str) -> None
    def append_to_parquet(self, df: polars.DataFrame, existing_path: str) -> None

class DataValidator:
    def validate_schema(self, data: Dict[str, Any], schema: BaseModel) -> ValidationResult
    def validate_batch(self, data_batch: List[Dict[str, Any]], schema: BaseModel) -> BatchValidationResult
```

#### AWSHelpers Module

**Location**: `common/src/python/aws_helpers/`

**Purpose**: Provides standardized AWS service interactions for lambdas.

**Key Components**:
- `S3Manager`: S3 operations with retry logic and error handling
- `LambdaUtils`: Lambda-specific utilities and decorators
- `CloudWatchLogger`: Structured logging for reporting lambdas

**Interface**:
```python
class S3Manager:
    def __init__(self, bucket_name: str, region: str = "us-east-1")
    def list_objects_with_prefix(self, prefix: str, since: Optional[datetime] = None) -> List[str]
    def download_json_object(self, key: str) -> Dict[str, Any]
    def upload_parquet(self, df: polars.DataFrame, key: str) -> None

class LambdaUtils:
    @staticmethod
    def with_error_handling(func: Callable) -> Callable
    @staticmethod
    def parse_lambda_event(event: Dict[str, Any], event_type: str) -> ParsedEvent
```

#### Models Module

**Location**: `common/src/python/models/`

**Purpose**: Shared Pydantic models for common data structures.

**Key Components**:
- `ReportingEvent`: Base model for all reporting events
- `DataSource`: Model for data source configurations
- `ProcessingResult`: Standardized processing result format

**Interface**:
```python
class ReportingEvent(BaseModel):
    timestamp: datetime
    source: str
    event_type: str
    data: Dict[str, Any]

class DataSource(BaseModel):
    name: str
    type: Literal["s3", "api", "database"]
    connection_params: Dict[str, Any]
    
class ProcessingResult(BaseModel):
    status: Literal["success", "partial", "failed"]
    records_processed: int
    records_failed: int
    output_location: Optional[str] = None
    errors: List[str] = []
```

### Lambda Template Structure

#### Template Components

The lambda template provides a standardized starting point for new reporting lambdas:

1. **Handler Template**: Basic lambda handler with error handling and logging
2. **Reporting Processor Template**: Separation of concerns with dedicated reporting processor module
3. **Terraform Template**: Standard infrastructure configuration
4. **Test Templates**: Unit and property-based test examples
5. **BUILD Configuration**: Proper dependency management and build targets

#### Template Handler Pattern

```python
# lambda/template/src/python/template_lambda/lambda_function.py
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Template lambda handler with standard error handling and logging."""
    logger.info("Processing request", extra={
        "request_id": context.aws_request_id,
        "event_type": event.get("source", "unknown")
    })
    
    try:
        # Parse and validate input
        parsed_event = parse_input_event(event)
        
        # Process reporting logic
        result = process_data(parsed_event)
        
        # Return standardized response
        return create_success_response(result)
        
    except ValidationError as e:
        logger.warning("Invalid input", extra={"error": str(e)})
        return create_error_response(400, "Invalid input format")
        
    except Exception as e:
        logger.error("Processing failed", extra={"error": str(e)})
        return create_error_response(500, "Internal processing error")
```

### Build System Integration

#### Pants Configuration Updates

The `pants.toml` will be enhanced to support the common code structure:

```toml
[source]
root_patterns = [
    "src/*", 
    "test/*",
    "common/src/*",
    "common/test/*"
]

[python-infer]
use_rust_parser = true
imports = true
string_imports = true
```

#### BUILD File Patterns

**Automated BUILD File Generation**:
After creating Python files, use `pants tailor ::` to automatically generate BUILD files with proper targets and dependencies.

**Common Module BUILD** (generated by `pants tailor`):
```python
# common/src/python/data_processing/BUILD
python_sources(name="lib")
```

**Lambda BUILD with Common Dependencies** (generated by `pants tailor`, then customized):
```python
# lambda/{name}/src/python/{name}_lambda/BUILD
python_sources(name="function")

python_aws_lambda_function(
    name="lambda",
    runtime="python3.12",
    handler="lambda_function.py:lambda_handler",
    include_requirements=False,
)

python_aws_lambda_layer(
    name="layer",
    runtime="python3.12",
    dependencies=[
        ":function",
        "//common/src/python/data_processing:lib",
        "//common/src/python/aws_helpers:lib",
        "//common/src/python/models:lib",
        "//:root#aws-lambda-powertools",
        "//:root#polars",
        "//:root#pydantic"
    ],
    include_sources=False,
)
```

## Data Models

### Common Infrastructure Models

The common models provide standardized structures for lambda infrastructure, execution metadata, and cross-lambda communication. Each individual lambda will define its own domain-specific data models for the data it processes.

#### ReportingEvent Model

```python
class ReportingEvent(BaseModel):
    """Base model for lambda execution metadata and cross-lambda communication"""
    timestamp: datetime = Field(description="Event timestamp")
    source: str = Field(description="Data source identifier")
    event_type: str = Field(description="Type of event")
    data: Dict[str, Any] = Field(description="Event payload")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

#### DataSourceConfig Model

```python
class DataSourceConfig(BaseModel):
    """Configuration for data sources - used by lambda infrastructure"""
    name: str = Field(description="Data source name")
    type: Literal["s3", "api", "database", "sqs"] = Field(description="Source type")
    connection_params: Dict[str, Any] = Field(description="Connection parameters")
    polling_interval: Optional[int] = Field(default=None, description="Polling interval in seconds")
    output_format: Literal["parquet", "json", "csv"] = Field(default="parquet", description="Output format")
```

#### ProcessingMetrics Model

```python
class ProcessingMetrics(BaseModel):
    """Metrics for lambda processing operations - used for monitoring and logging"""
    start_time: datetime
    end_time: datetime
    records_processed: int = 0
    records_failed: int = 0
    bytes_processed: int = 0
    output_files_created: int = 0
    errors: List[str] = Field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def success_rate(self) -> float:
        total = self.records_processed + self.records_failed
        return self.records_processed / total if total > 0 else 0.0
```

### Lambda-Specific Data Models

Each lambda defines its own models for the specific data it processes. These are separate from the common infrastructure models:

```python
# Example: lambda/api_ingestion/src/python/api_ingestion_lambda/models.py
class CustomerRecord(BaseModel):
    """Domain-specific model for customer data processing"""
    customer_id: str
    name: str
    email: str
    registration_date: date
    
# Example: lambda/database_export/src/python/database_export_lambda/models.py  
class SalesTransaction(BaseModel):
    """Domain-specific model for sales data processing"""
    transaction_id: str
    customer_id: str
    amount: Decimal
    transaction_date: datetime
    product_ids: List[str]
```

The common models handle infrastructure concerns (execution metadata, configuration, metrics) while lambda-specific models handle the actual business data being processed.

## Error Handling

### Standardized Error Handling Pattern

All lambdas will follow a consistent error handling approach:

1. **Input Validation Errors**: Return 400 with descriptive error messages
2. **Processing Errors**: Log detailed error information, return 500 with generic message
3. **Partial Failures**: Continue processing valid records, log failed records
4. **Infrastructure Errors**: Retry with exponential backoff, fail after max attempts

### Error Response Format

```python
class ErrorResponse(BaseModel):
    """Standardized error response format"""
    error: str = Field(description="Error message")
    error_code: str = Field(description="Application-specific error code")
    request_id: str = Field(description="Request identifier for tracking")
    timestamp: datetime = Field(description="Error timestamp")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
```

### Common Error Handling Utilities

```python
# common/src/python/utils/error_handling.py
def handle_validation_error(error: ValidationError, request_id: str) -> Dict[str, Any]:
    """Handle Pydantic validation errors"""
    return {
        "statusCode": 400,
        "body": ErrorResponse(
            error="Validation failed",
            error_code="VALIDATION_ERROR",
            request_id=request_id,
            timestamp=datetime.utcnow(),
            details={"validation_errors": error.errors()}
        ).model_dump_json()
    }

def handle_processing_error(error: Exception, request_id: str) -> Dict[str, Any]:
    """Handle general processing errors"""
    logger.error("Processing error", extra={
        "error": str(error),
        "request_id": request_id,
        "error_type": type(error).__name__
    })
    
    return {
        "statusCode": 500,
        "body": ErrorResponse(
            error="Internal processing error",
            error_code="PROCESSING_ERROR",
            request_id=request_id,
            timestamp=datetime.utcnow()
        ).model_dump_json()
    }
```

## Testing Strategy

### Dual Testing Approach

The monorepo will implement both unit testing and property-based testing:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all inputs using Hypothesis
- Both are complementary and necessary for comprehensive coverage

### Common Testing Utilities

#### Test Fixtures and Utilities

```python
# common/test/python/fixtures.py
@pytest.fixture
def sample_reporting_event():
    """Sample reporting event for testing"""
    return ReportingEvent(
        timestamp=datetime.utcnow(),
        source="test_source",
        event_type="test_event",
        data={"key": "value"}
    )

@pytest.fixture
def mock_s3_manager():
    """Mock S3Manager for testing"""
    with patch('common.aws_helpers.S3Manager') as mock:
        yield mock

@pytest.fixture
def temp_parquet_file():
    """Temporary parquet file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
        yield f.name
    os.unlink(f.name)
```

#### Property-Based Testing Patterns

```python
# Example property test for data processing
from hypothesis import given, strategies as st

@given(
    events=st.lists(
        st.builds(
            ReportingEvent,
            timestamp=st.datetimes(),
            source=st.text(min_size=1, max_size=50),
            event_type=st.text(min_size=1, max_size=20),
            data=st.dictionaries(st.text(), st.text())
        ),
        min_size=1,
        max_size=100
    )
)
def test_parquet_round_trip_property(events):
    """Property: For any list of events, writing to parquet then reading should preserve data"""
    # Write events to parquet
    df = polars.DataFrame([event.model_dump() for event in events])
    writer = ParquetWriter()
    
    with tempfile.NamedTemporaryFile(suffix='.parquet') as f:
        writer.write_dataframe(df, f.name)
        
        # Read back from parquet
        read_df = polars.read_parquet(f.name)
        
        # Verify data preservation
        assert len(read_df) == len(events)
        assert set(read_df.columns) == set(df.columns)
```

### Testing Configuration

Each lambda and common module will have comprehensive test coverage:

- **Minimum 100 iterations per property test** (due to randomization)
- **Property tests tagged with feature and property references**
- **Unit tests for specific examples and edge cases**
- **Integration tests for AWS service interactions**

### Test BUILD Configuration

```python
# common/test/python/BUILD
python_sources(name="test_utils")
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property-Based Testing Overview

Property-based testing (PBT) validates software correctness by testing universal properties across many generated inputs. Each property is a formal specification that should hold for all valid inputs.

### Converting EARS to Properties

Based on the prework analysis, the following properties will validate the monorepo transformation:

**Property 1: Repository structure consistency**
*For any* lambda directory in the repository, it should follow the standardized structure with `src/python/{lambda_name}_lambda/`, `test/python/`, and Terraform files at the root
**Validates: Requirements 2.2, 2.3**

**Property 2: Common code dependency resolution**
*For any* lambda that declares dependencies on common code modules, the build system should automatically include those dependencies in the lambda package
**Validates: Requirements 1.3, 4.1, 4.3**

**Property 3: Environment variable naming consistency**
*For any* lambda template or infrastructure module, environment variables should follow the standardized naming patterns for data sources and output destinations
**Validates: Requirements 7.4**

**Property 4: Lambda README completeness**
*For any* lambda directory, it should contain a README file with sections covering data source details, output specifications, and deployment instructions
**Validates: Requirements 3.5**

**Property 5: Build system lambda independence**
*For any* individual lambda, it should be buildable independently without requiring other lambdas to be built first
**Validates: Requirements 4.1**

### Example-Based Validation

The following specific examples will be validated:

**Example 1: Common directory structure**
The repository should contain a `common/` directory with subdirectories for `data_processing`, `aws_helpers`, `models`, and `utils`
**Validates: Requirements 1.1, 1.2**

**Example 2: Lambda template completeness**
The lambda template should include all required files: handler code, reporting processor, Terraform configuration, BUILD files, and test examples
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

**Example 3: Existing lambda preservation**
The `lambda/event_log_checkpoint/` directory should remain unchanged with all existing files and build targets working
**Validates: Requirements 6.1, 6.2, 6.3, 6.5**

**Example 4: Documentation updates**
The main README.md should contain sections for monorepo overview, lambda development workflows, and common code usage patterns
**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

**Example 5: Build system commands**
The command `pants package lambda::` should successfully build all lambdas in the repository
**Validates: Requirements 4.2**

**Example 6: Common code testability**
Each common code module should have its own BUILD file and be testable independently using `pants test common/src/python/{module}::`
**Validates: Requirements 1.4**

**Example 7: Terraform module structure**
The `terraform/modules/` directory should contain reusable modules for IAM roles, monitoring, and lambda infrastructure
**Validates: Requirements 7.1, 7.2, 7.3**

**Example 8: Development workflow documentation**
The documentation should include clear workflows for both individual lambda development and multi-lambda changes
**Validates: Requirements 8.1, 8.2, 8.3, 8.4**

**Example 9: Testing command availability**
The repository should support commands for testing all lambdas (`pants test lambda::`) and individual lambdas (`pants test lambda/{name}::`)
**Validates: Requirements 4.5**

**Example 10: Infrastructure deployment flexibility**
The Terraform modules should support both individual lambda deployment and batch deployment scenarios
**Validates: Requirements 7.5**

### Property Test Configuration

- **Minimum 100 iterations per property test** (due to randomization)
- **Each property test must reference its design document property**
- **Tag format**: **Feature: monorepo-transformation, Property {number}: {property_text}**
- **Property-based testing library**: Hypothesis (Python)

### Testing Strategy

**Dual Testing Approach**:
- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all inputs
- Both are complementary and necessary for comprehensive coverage

**Unit Testing Balance**:
- Unit tests focus on specific examples that demonstrate correct behavior
- Integration points between components
- Edge cases and error conditions
- Property tests focus on universal properties that hold for all inputs
- Comprehensive input coverage through randomization

The testing strategy ensures that the monorepo transformation maintains backward compatibility while establishing robust patterns for future lambda development.