# Reporting Lambdas Monorepo

A comprehensive monorepo for hosting multiple AWS Lambda functions that extract data from various sources and create parquet tables for analytical use. This repository provides shared utilities, standardized patterns, and consistent tooling for developing data processing lambdas that support analytical reporting workflows.

## Overview

This monorepo contains multiple reporting lambdas that extract data from different sources (APIs, databases, S3 buckets, etc.) and transform them into parquet files optimized for analytical queries. Each lambda follows consistent patterns for data validation, error handling, and incremental processing while leveraging shared code for common functionality.

### Monorepo Benefits

- **Shared Code**: Common utilities, models, and AWS helpers reduce duplication
- **Consistent Patterns**: Standardized lambda structure and development workflows
- **Unified Tooling**: Single build system, testing framework, and deployment pipeline
- **Scalable Organization**: Easy to add new reporting lambdas following established patterns

### Key Features

- **Monorepo Architecture**: Multiple reporting lambdas with shared code and consistent patterns
- **Common Code Libraries**: Reusable utilities for data processing, AWS operations, and validation
- **Incremental Processing**: Lambdas support efficient incremental data processing patterns
- **Schema Validation**: Standardized Pydantic models for data validation across lambdas
- **Error Resilience**: Robust error handling that continues processing valid data
- **Analytical Optimization**: Parquet output optimized for analytical queries
- **Observability**: Comprehensive logging, tracing, and metrics using AWS Lambda Powertools
- **Template-Based Development**: Standardized lambda template for rapid development

## Repository Structure

The monorepo is organized to support multiple reporting lambdas with shared code:

```
reporting-lambdas/
├── .devcontainer/              # Dev container configuration
├── .github/                    # GitHub workflows and templates
├── .kiro/                      # Kiro specs and steering files
├── bin/                        # Dev container management scripts
├── common/                     # Shared code across all lambdas
│   ├── src/python/
│   │   ├── data_processing/    # Parquet, validation utilities
│   │   ├── aws_helpers/        # S3, Lambda utilities
│   │   ├── models/             # Common Pydantic models
│   │   └── utils/              # General utilities
│   └── test/python/            # Tests for common modules
├── lambda/                     # Lambda functions directory
│   ├── event_log_checkpoint/   # Event log processing lambda
│   └── template/               # Template for new lambdas
├── terraform/                  # Global infrastructure modules
│   └── modules/                # Reusable Terraform modules
├── context/                    # Documentation and examples
├── BUILD                       # Root build configuration
├── pants.toml                  # Pants build system configuration
├── requirements.txt            # Project dependencies
└── README.md                   # This file
```

### Lambda Organization

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
│       └── reporting_processor.py   # Business logic
└── test/python/
    ├── BUILD                        # Test build configuration
    ├── test_lambda_function.py      # Handler tests
    └── test_reporting_processor.py  # Business logic tests
```

### Technology Stack

- **Runtime**: Python 3.12
- **Build System**: Pants 2.29
- **Development Environment**: Dev container with devcontainer CLI
- **Infrastructure**: Terraform
- **Libraries**:
  - AWS Lambda Powertools (logging, tracing, metrics)
  - Pydantic (data validation)
  - Polars (DataFrame operations and parquet generation)
  - Boto3 (AWS SDK - included with Powertools)

## Lambda Development Workflows

The monorepo supports both individual lambda development and multi-lambda workflows.

### Individual Lambda Development

For working on a single lambda:

```bash
# Start dev container
./bin/start-devcontainer.sh

# Run quality checks for specific lambda
./bin/exec-in-devcontainer.sh pants fix lambda/{lambda_name}::
./bin/exec-in-devcontainer.sh pants lint lambda/{lambda_name}::
./bin/exec-in-devcontainer.sh pants check lambda/{lambda_name}::

# Test specific lambda
./bin/exec-in-devcontainer.sh pants test lambda/{lambda_name}/test/python::

# Build specific lambda
./bin/exec-in-devcontainer.sh pants package lambda/{lambda_name}/src/python/{lambda_name}_lambda::

# Deploy specific lambda
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{lambda_name} && terraform apply"
```

### Multi-Lambda Development

For changes affecting multiple lambdas or common code:

```bash
# Start dev container
./bin/start-devcontainer.sh

# Run quality checks across entire repository
./bin/exec-in-devcontainer.sh pants fix ::
./bin/exec-in-devcontainer.sh pants lint ::
./bin/exec-in-devcontainer.sh pants check ::

# Test all lambdas and common code
./bin/exec-in-devcontainer.sh pants test ::

# Build all lambdas
./bin/exec-in-devcontainer.sh pants package lambda::

# Test affected lambdas after common code changes
./bin/exec-in-devcontainer.sh pants test --changed-since=HEAD~1 ::
```

### Creating New Lambdas

Use the lambda template to create new reporting lambdas:

```bash
# Copy template to new lambda directory
cp -r templates/lambda-template lambda/{new_lambda_name}

# Update lambda-specific files (see template README for details)
# - Update Terraform variables
# - Customize handler and business logic
# - Update BUILD files with correct dependencies

# Generate BUILD files
./bin/exec-in-devcontainer.sh pants tailor lambda/{new_lambda_name}::

# Test new lambda
./bin/exec-in-devcontainer.sh pants test lambda/{new_lambda_name}/test/python::
```

## Common Code Libraries

The `common/` directory provides shared utilities used across all lambdas:

### Data Processing (`common/src/python/data_processing/`)

- **ParquetWriter**: Standardized parquet file creation with compression and schema validation
- **DataValidator**: Common validation patterns for reporting data
- **SchemaManager**: Schema evolution and compatibility checking

### AWS Helpers (`common/src/python/aws_helpers/`)

- **S3Manager**: S3 operations with retry logic and error handling
- **LambdaUtils**: Lambda-specific utilities and decorators
- **CloudWatchLogger**: Structured logging for reporting lambdas

### Models (`common/src/python/models/`)

- **ReportingEvent**: Base model for lambda execution metadata
- **DataSourceConfig**: Configuration for data sources
- **ProcessingMetrics**: Standardized processing result format

### Utils (`common/src/python/utils/`)

- **Error Handling**: Standardized error handling utilities
- **Date Utilities**: Common date/time processing functions
- **String Processing**: Text processing and validation utilities

## Current Lambdas

### Event Log Checkpoint (`lambda/event_log_checkpoint/`)

Processes event log files from S3, validates them using Pydantic models, and creates/updates checkpoint parquet files optimized for analytical queries.

**Key Features:**
- Incremental processing for performance optimization
- Schema validation using Pydantic models
- Error resilience with partial failure handling
- Event evolution support for audit trails

**Data Sources:** S3 event log files
**Output:** Parquet checkpoint files for analytical queries

See [lambda/event_log_checkpoint/README.md](lambda/event_log_checkpoint/README.md) for detailed documentation.

## Build System

The monorepo uses Pants build system for efficient dependency management and builds:

### Building Individual Lambdas

```bash
# Build specific lambda
./bin/exec-in-devcontainer.sh pants package lambda/{lambda_name}/src/python/{lambda_name}_lambda::

# Build lambda layers
./bin/exec-in-devcontainer.sh pants package lambda/{lambda_name}/src/python/{lambda_name}_lambda:powertools
./bin/exec-in-devcontainer.sh pants package lambda/{lambda_name}/src/python/{lambda_name}_lambda:data_processing
```

### Building All Lambdas

```bash
# Build all lambdas at once
./bin/exec-in-devcontainer.sh pants package lambda::

# Build with dependency tracking
./bin/exec-in-devcontainer.sh pants package --changed-since=HEAD~1 lambda::
```

### Common Code Dependencies

The build system automatically resolves dependencies on common code:

- Lambdas declare dependencies on common modules in their BUILD files
- Pants tracks changes to common code and rebuilds affected lambdas
- Common code is included in lambda packages automatically

## Deployment

### Infrastructure as Code

Each lambda includes Terraform configuration for infrastructure deployment:

- **Individual Deployment**: Deploy single lambdas independently
- **Batch Deployment**: Deploy multiple lambdas using shared modules
- **Common Infrastructure**: Reusable Terraform modules for standard patterns

### Lambda Layer Strategy

All lambdas use a consistent multi-layer approach:

#### Layer 1: AWS Lambda Powertools
- **Contents**: AWS Lambda Powertools (includes boto3)
- **Size**: ~5MB
- **Update Frequency**: Low

#### Layer 2: Data Processing
- **Contents**: Pydantic and Polars libraries
- **Size**: ~15-20MB
- **Update Frequency**: Medium

#### Layer 3: Function Code
- **Contents**: Lambda-specific code and common utilities
- **Size**: <1MB
- **Update Frequency**: High

### Deployment Commands

```bash
# Deploy individual lambda
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{lambda_name} && terraform apply"

# Deploy with layer updates
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{lambda_name} && terraform apply -var='reuse_existing_layers=false'"

# Function-only deployment (fastest for code changes)
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{lambda_name} && terraform apply -target=aws_lambda_function.{lambda_name}"
```

## Testing

The monorepo includes comprehensive testing for all lambdas and common code:

### Testing Strategy

- **Unit Tests**: Component-specific tests for each module
- **Property-Based Tests**: Universal properties tested across many inputs using Hypothesis
- **Integration Tests**: End-to-end lambda execution and AWS service integration

### Running Tests

```bash
# Test all lambdas and common code
./bin/exec-in-devcontainer.sh pants test ::

# Test specific lambda
./bin/exec-in-devcontainer.sh pants test lambda/{lambda_name}/test/python::

# Test common code modules
./bin/exec-in-devcontainer.sh pants test common/test/python::

# Test with coverage
./bin/exec-in-devcontainer.sh pants test --coverage-py-report=html ::

# Test only changed code
./bin/exec-in-devcontainer.sh pants test --changed-since=HEAD~1 ::
```

### Property-Based Testing

All lambdas include property-based tests that verify universal behaviors:

- Minimum 100 iterations per property test
- Tests tagged with feature and property references
- Validates correctness properties across random inputs

## Monitoring and Observability

### CloudWatch Metrics

Standard metrics across all lambdas:

- `EventsProcessed`: Count of processed events
- `EventsFailed`: Count of failed events
- `ExecutionTime`: Total execution time
- `OutputFileSize`: Size of generated files

### X-Ray Tracing

- S3 operations tracing
- Data processing performance
- Cross-service call tracing

### Logging

Structured logging using AWS Lambda Powertools:

- Consistent log format across all lambdas
- Request correlation IDs
- Performance metrics
- Error details with context

## Performance Optimization

### Common Patterns

All lambdas follow performance optimization patterns:

- **Incremental Processing**: Only process new data since last run
- **Efficient Data Structures**: Use Polars for fast DataFrame operations
- **Connection Pooling**: Reuse AWS service connections
- **Compression**: Use Snappy compression for optimal size/speed balance

### Expected Performance

- **First run**: 5-15 minutes for large historical datasets
- **Incremental runs**: 30-120 seconds for typical new data volumes
- **Memory**: 3GB to handle large datasets efficiently
- **Timeout**: 15 minutes maximum per lambda

## Error Handling

Standardized error handling across all lambdas:

- **Input Validation**: Return 400 with descriptive error messages
- **Processing Errors**: Log detailed information, return 500 with generic message
- **Partial Failures**: Continue processing valid data, log failed records
- **Infrastructure Errors**: Retry with exponential backoff

## Contributing

### Development Guidelines

1. Follow the established dev container workflow
2. Use the lambda template for new reporting lambdas
3. Add common functionality to shared modules when appropriate
4. Run quality checks before committing: `./bin/exec-in-devcontainer.sh pants fix lint check test ::`
5. Add comprehensive tests for new functionality
6. Update documentation for significant changes
7. Use property-based tests for universal behaviors

### Code Quality Standards

- **Linting**: Ruff with 88-character line length
- **Type Checking**: mypy with strict configuration
- **Testing**: Minimum 80% code coverage
- **Documentation**: Clear docstrings and README files

### Adding New Lambdas

1. Copy the lambda template: `cp -r templates/lambda-template lambda/{new_name}`
2. Customize the template for your specific data source and processing needs
3. Update BUILD files and dependencies
4. Add comprehensive tests
5. Update this README with lambda description
6. Create lambda-specific README with detailed documentation

## License

See LICENSE file for details.
