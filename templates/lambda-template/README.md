# Lambda Template

This template provides a standardized starting point for creating new reporting lambdas in the monorepo. It includes boilerplate code for common reporting patterns, standardized error handling, comprehensive testing examples, and Terraform infrastructure configuration.

## Quick Start

### 1. Copy Template

```bash
# Copy template to new lambda directory
cp -r templates/lambda-template lambda/{your-lambda-name}
cd lambda/{your-lambda-name}
```

### 2. Customize Template

```bash
# Replace template_lambda with your lambda name throughout the codebase
find . -type f -name "*.py" -exec sed -i 's/template_lambda/{your-lambda-name}_lambda/g' {} +
find . -type f -name "*.tf" -exec sed -i 's/template-lambda/{your-lambda-name}/g' {} +

# Rename the main module directory
mv src/python/template_lambda src/python/{your-lambda-name}_lambda
```

### 3. Generate BUILD Files

```bash
# Generate Pants BUILD files for your new lambda
./bin/exec-in-devcontainer.sh pants tailor lambda/{your-lambda-name}::
```

### 4. Implement Your Logic

- Update `lambda_function.py` with your handler logic
- Implement business logic in `reporting_processor.py`
- Add your data models if needed
- Update tests with your specific test cases

### 5. Deploy

```bash
# Test your lambda
./bin/exec-in-devcontainer.sh pants test lambda/{your-lambda-name}/test/python::

# Build lambda package
./bin/exec-in-devcontainer.sh pants package lambda/{your-lambda-name}/src/python/{your-lambda-name}_lambda::

# Deploy infrastructure
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{your-lambda-name} && terraform init && terraform apply"
```

## Template Structure

```
lambda/{your-lambda-name}/
├── main.tf                     # Terraform configuration
├── variables.tf                # Terraform variables
├── outputs.tf                  # Terraform outputs
├── terraform.tfvars.example    # Example Terraform variables
├── README.md                   # This file (customize for your lambda)
├── src/python/
│   └── {your-lambda-name}_lambda/
│       ├── BUILD                    # Pants build configuration
│       ├── lambda_function.py       # Main Lambda handler
│       └── reporting_processor.py   # Business logic module
└── test/python/
    ├── BUILD                        # Test build configuration
    ├── test_lambda_function.py      # Handler tests
    └── test_reporting_processor.py  # Business logic tests
```

## Customization Guide

### 1. Lambda Handler (`lambda_function.py`)

The template handler includes:

- Standardized error handling using common utilities
- Event parsing and validation
- Structured logging with correlation IDs
- Proper response formatting

**Customize for your use case:**

```python
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    TODO: Update this docstring with your lambda's purpose
    
    Processes [YOUR DATA SOURCE] and creates [YOUR OUTPUT FORMAT] for analytical use.
    """
    
    # TODO: Update event parsing for your trigger type
    # Options: "s3", "api_gateway", "cloudwatch", "custom"
    parsed_event = LambdaUtils.parse_lambda_event(event, "s3")
    
    # TODO: Implement your processing logic
    result = process_your_data(parsed_event)
    
    return create_success_response(result)
```

### 2. Business Logic (`reporting_processor.py`)

Implement your data processing logic:

```python
def process_your_data(event_data: Any) -> ProcessingMetrics:
    """
    TODO: Implement your specific data processing logic
    
    Args:
        event_data: Parsed event data from lambda handler
        
    Returns:
        ProcessingMetrics: Metrics about the processing operation
    """
    
    start_time = datetime.utcnow()
    
    # TODO: Add your processing logic here
    # Examples:
    # - Download data from S3/API/Database
    # - Validate and clean data
    # - Transform data for analytics
    # - Generate parquet files
    # - Upload results to S3
    
    metrics = ProcessingMetrics(
        start_time=start_time,
        end_time=datetime.utcnow(),
        records_processed=0,  # TODO: Update with actual counts
        records_failed=0,
        output_files_created=0
    )
    
    return metrics
```

### 3. Terraform Configuration

#### Variables (`variables.tf`)

Update variables for your lambda:

```hcl
variable "lambda_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "your-lambda-name"  # TODO: Update this
}

variable "source_bucket" {
  description = "S3 bucket containing source data"
  type        = string
  # TODO: Add your source bucket
}

variable "destination_bucket" {
  description = "S3 bucket for processed data"
  type        = string
  # TODO: Add your destination bucket
}

# TODO: Add additional variables for your specific needs
```

#### Main Configuration (`main.tf`)

The template includes:

- Lambda function with proper IAM roles
- Lambda layers for common dependencies
- CloudWatch log groups
- S3 bucket permissions
- Environment variables

**Customize IAM permissions:**

```hcl
# TODO: Update IAM policy for your specific S3 buckets and services
data "aws_iam_policy_document" "lambda_policy" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::${var.source_bucket}",
      "arn:aws:s3:::${var.source_bucket}/*",
      "arn:aws:s3:::${var.destination_bucket}",
      "arn:aws:s3:::${var.destination_bucket}/*"
    ]
  }
  
  # TODO: Add additional permissions as needed
  # Examples: RDS access, SQS access, API Gateway, etc.
}
```

### 4. Testing

#### Unit Tests (`test_lambda_function.py`)

Update tests for your handler:

```python
def test_lambda_handler_success():
    """Test successful lambda execution."""
    
    # TODO: Create test event for your lambda trigger
    test_event = {
        # Your test event structure
    }
    
    # TODO: Mock external dependencies
    with patch('your_lambda.reporting_processor.process_your_data') as mock_process:
        mock_process.return_value = ProcessingMetrics(
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            records_processed=100
        )
        
        response = lambda_handler(test_event, create_mock_context())
        
        assert response["statusCode"] == 200
        # TODO: Add your specific assertions
```

#### Property-Based Tests (`test_reporting_processor.py`)

Add property-based tests for your business logic:

```python
from hypothesis import given, strategies as st

@given(
    # TODO: Define your input data strategy
    input_data=st.lists(st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(st.text(), st.integers(), st.floats())
    ), min_size=1, max_size=100)
)
def test_data_processing_property(input_data):
    """
    Property: For any valid input data, processing should complete successfully
    and return valid metrics.
    """
    
    # TODO: Implement your property test
    result = process_your_data(input_data)
    
    # Universal properties that should always hold
    assert isinstance(result, ProcessingMetrics)
    assert result.start_time <= result.end_time
    assert result.records_processed >= 0
    assert result.records_failed >= 0
    assert 0.0 <= result.success_rate <= 1.0
```

## Common Patterns

### S3 Event Processing

For lambdas triggered by S3 events:

```python
@LambdaUtils.with_error_handling
def lambda_handler(event, context):
    """Process S3 events."""
    
    parsed_event = LambdaUtils.parse_lambda_event(event, "s3")
    
    results = []
    for s3_record in parsed_event.s3_records:
        bucket = s3_record.bucket_name
        key = s3_record.object_key
        
        # Process each S3 object
        result = process_s3_object(bucket, key)
        results.append(result)
    
    return LambdaUtils.create_response(200, {
        "processed_objects": len(results),
        "results": results
    })
```

### API Data Ingestion

For lambdas that pull data from APIs:

```python
def process_api_data(api_config: DataSourceConfig) -> ProcessingMetrics:
    """Process data from API source."""
    
    start_time = datetime.utcnow()
    
    # Use common HTTP utilities
    api_client = create_api_client(api_config.connection_params)
    
    # Fetch data with pagination
    all_data = []
    page = 1
    while True:
        response = api_client.get(f"/data?page={page}")
        if not response.data:
            break
        all_data.extend(response.data)
        page += 1
    
    # Validate and process data
    validator = DataValidator()
    batch_result = validator.validate_batch(all_data, YourDataModel)
    
    # Convert to parquet and upload
    if batch_result.valid_records:
        df = pl.DataFrame([record.model_dump() for record in batch_result.valid_records])
        s3_manager = S3Manager(api_config.connection_params["output_bucket"])
        s3_manager.upload_parquet(df, f"api_data/{datetime.utcnow().date()}/data.parquet")
    
    return ProcessingMetrics(
        start_time=start_time,
        end_time=datetime.utcnow(),
        records_processed=len(batch_result.valid_records),
        records_failed=len(batch_result.invalid_records),
        output_files_created=1 if batch_result.valid_records else 0
    )
```

### Database Export

For lambdas that export database data:

```python
def process_database_export(db_config: DataSourceConfig) -> ProcessingMetrics:
    """Export data from database to parquet."""
    
    start_time = datetime.utcnow()
    
    # Connect to database
    connection_string = db_config.connection_params["connection_string"]
    
    # Use Polars for efficient database reading
    query = f"SELECT * FROM {db_config.connection_params['table']} WHERE updated_at > %s"
    df = pl.read_database(query, connection_string, parameters=[get_last_export_time()])
    
    if len(df) > 0:
        # Upload to S3
        s3_manager = S3Manager(db_config.connection_params["output_bucket"])
        output_key = f"database_exports/{db_config.name}/{datetime.utcnow().date()}/export.parquet"
        s3_manager.upload_parquet(df, output_key)
        
        # Update last export time
        update_last_export_time(datetime.utcnow())
    
    return ProcessingMetrics(
        start_time=start_time,
        end_time=datetime.utcnow(),
        records_processed=len(df),
        output_files_created=1 if len(df) > 0 else 0
    )
```

## Environment Variables

Standard environment variables used by the template:

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `SOURCE_BUCKET` | S3 bucket for source data | Yes | `my-source-data` |
| `DESTINATION_BUCKET` | S3 bucket for processed data | Yes | `my-processed-data` |
| `LOG_LEVEL` | Logging level | No | `INFO` |
| `POWERTOOLS_SERVICE_NAME` | Service name for tracing | No | `your-lambda-name` |

**Add your custom environment variables:**

```hcl
# In main.tf
environment {
  variables = {
    SOURCE_BUCKET      = var.source_bucket
    DESTINATION_BUCKET = var.destination_bucket
    LOG_LEVEL         = var.log_level
    POWERTOOLS_SERVICE_NAME = var.lambda_name
    
    # TODO: Add your custom environment variables
    # API_BASE_URL     = var.api_base_url
    # DATABASE_HOST    = var.database_host
    # POLLING_INTERVAL = var.polling_interval
  }
}
```

## Development Workflow

### Local Development

```bash
# Start dev container
./bin/start-devcontainer.sh

# Run quality checks
./bin/exec-in-devcontainer.sh pants fix lambda/{your-lambda-name}::
./bin/exec-in-devcontainer.sh pants lint lambda/{your-lambda-name}::
./bin/exec-in-devcontainer.sh pants check lambda/{your-lambda-name}::

# Run tests
./bin/exec-in-devcontainer.sh pants test lambda/{your-lambda-name}/test/python::

# Build lambda
./bin/exec-in-devcontainer.sh pants package lambda/{your-lambda-name}/src/python/{your-lambda-name}_lambda::
```

### Testing Strategy

1. **Unit Tests**: Test individual functions and error handling
2. **Property-Based Tests**: Test universal properties with random inputs
3. **Integration Tests**: Test with real AWS services (using LocalStack or test accounts)

### Deployment

```bash
# Deploy to development environment
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{your-lambda-name} && terraform workspace select dev && terraform apply"

# Deploy to production environment
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{your-lambda-name} && terraform workspace select prod && terraform apply"
```

## Best Practices

### Code Organization

1. **Separate concerns**: Keep handler logic separate from business logic
2. **Use common utilities**: Leverage shared code from `common/` modules
3. **Follow naming conventions**: Use consistent naming patterns
4. **Add comprehensive logging**: Use structured logging with context

### Error Handling

1. **Use standardized error handling**: Always use `@LambdaUtils.with_error_handling`
2. **Handle partial failures**: Continue processing valid data when some records fail
3. **Log errors with context**: Include relevant information for debugging

### Performance

1. **Use incremental processing**: Only process new/changed data when possible
2. **Optimize memory usage**: Use streaming for large datasets
3. **Choose appropriate timeout**: Set realistic timeout values
4. **Monitor cold starts**: Use provisioned concurrency if needed

### Security

1. **Follow least privilege**: Only grant necessary IAM permissions
2. **Use environment variables**: Don't hardcode sensitive values
3. **Validate input**: Always validate external data
4. **Enable encryption**: Use encryption in transit and at rest

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure BUILD files include correct dependencies
2. **Permission errors**: Check IAM roles and S3 bucket policies
3. **Timeout errors**: Increase lambda timeout or optimize processing
4. **Memory errors**: Increase memory allocation or process data in chunks

### Debugging

1. **Check CloudWatch logs**: Lambda execution logs are in CloudWatch
2. **Use X-Ray tracing**: Enable tracing for performance analysis
3. **Test locally**: Use the dev container for local testing
4. **Monitor metrics**: Set up CloudWatch alarms for key metrics

## Documentation Checklist

When customizing this README for your lambda:

- [ ] Update the title and description
- [ ] Document your specific data source and output format
- [ ] Update environment variables table
- [ ] Add your specific deployment instructions
- [ ] Document any special configuration requirements
- [ ] Add examples of your input/output data formats
- [ ] Update troubleshooting section with lambda-specific issues
- [ ] Add monitoring and alerting recommendations
- [ ] Document any external dependencies or prerequisites