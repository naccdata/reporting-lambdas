# Common Code Usage Guide

This guide provides comprehensive documentation for using the shared code libraries in the `common/` directory. These modules provide standardized functionality for data processing, AWS operations, validation, and utilities that can be used across all reporting lambdas.

## Overview

The common code is organized into four main modules:

- **data_processing**: Parquet generation, data validation, and schema management
- **aws_helpers**: S3 operations, Lambda utilities, and AWS service interactions
- **models**: Shared Pydantic models for common data structures
- **utils**: General utilities for error handling, date processing, and string operations

## Module Documentation

### [Data Processing Module](data-processing-usage.md)

Utilities for data validation, transformation, and parquet file generation.

**Key Components:**
- `ParquetWriter`: Standardized parquet file creation
- `DataValidator`: Common validation patterns

### [AWS Helpers Module](aws-helpers-usage.md)

Standardized AWS service interactions for lambdas.

**Key Components:**
- `S3Manager`: S3 operations with retry logic
- `LambdaUtils`: Lambda-specific utilities and decorators

### [Models Module](models-usage.md)

Shared Pydantic models for common data structures.

**Key Components:**
- `ReportingEvent`: Base model for lambda execution metadata
- `DataSourceConfig`: Configuration for data sources
- `ProcessingMetrics`: Standardized processing result format

### [Utils Module](utils-usage.md)

General utilities for common operations.

**Key Components:**
- Error handling utilities
- Date and time processing functions
- String processing and validation utilities

## Best Practices

### Dependency Management

When using common code in your lambda:

1. **Add dependencies to BUILD file:**
   ```python
   python_sources(
       name="lib",
       dependencies=[
           "//common/src/python/data_processing:lib",
           "//common/src/python/aws_helpers:lib",
           "//common/src/python/models:lib",
       ]
   )
   ```

2. **Import modules consistently:**
   ```python
   from common.data_processing import ParquetWriter, DataValidator
   from common.aws_helpers import S3Manager, LambdaUtils
   from common.models import ReportingEvent, ProcessingMetrics
   ```

### Error Handling

Use standardized error handling patterns:

```python
from common.utils.error_handling import handle_validation_error, handle_processing_error

try:
    # Your processing logic
    result = process_data(event)
except ValidationError as e:
    return handle_validation_error(e, request_id)
except Exception as e:
    return handle_processing_error(e, request_id)
```

### Logging

Use consistent logging patterns:

```python
from aws_lambda_powertools import Logger
from common.models import ProcessingMetrics

logger = Logger()

# Log with structured data
logger.info("Processing started", extra={
    "request_id": context.aws_request_id,
    "event_type": event.get("source", "unknown")
})
```

### Testing Common Code

When testing lambdas that use common code:

```python
import pytest
from common.data_processing import ParquetWriter
from common.models import ReportingEvent

def test_lambda_with_common_code():
    # Test your lambda logic that uses common code
    writer = ParquetWriter()
    event = ReportingEvent(...)
    
    # Your test assertions
    assert writer is not None
```

## Development Workflow

### Making Changes to Common Code

1. **Update the common module**
2. **Run tests for common code:**
   ```bash
   ./bin/exec-in-devcontainer.sh pants test common/test/python::
   ```
3. **Test affected lambdas:**
   ```bash
   ./bin/exec-in-devcontainer.sh pants test --changed-since=HEAD~1 lambda::
   ```
4. **Update documentation if needed**

### Adding New Common Functionality

1. **Add new module or extend existing module**
2. **Add comprehensive tests**
3. **Update BUILD files**
4. **Update this documentation**
5. **Update lambda templates if applicable**

## Performance Considerations

### Import Optimization

- Import only what you need from common modules
- Use specific imports rather than wildcard imports
- Consider lazy imports for heavy modules if not always needed

### Memory Usage

- Common code is included in lambda packages
- Monitor lambda package size and memory usage
- Use efficient data structures (Polars DataFrames, etc.)

### Cold Start Impact

- Common code affects lambda cold start time
- Keep common modules lightweight
- Use lambda layers for heavy dependencies

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure BUILD files include correct dependencies
2. **Version Conflicts**: Check requirements.txt for version compatibility
3. **Missing Dependencies**: Run `pants tailor ::` to generate BUILD files

### Debugging

Use structured logging to debug common code usage:

```python
logger.debug("Using common code", extra={
    "module": "data_processing",
    "function": "ParquetWriter.write_dataframe",
    "parameters": {"compression": "snappy"}
})
```

## Examples

See the individual module documentation for detailed examples and usage patterns.