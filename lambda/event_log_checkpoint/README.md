# Event Log Checkpoint Lambda

This Lambda function processes event log files from S3, creates incremental checkpoints in Parquet format, and enables efficient analytical queries on event data.

## What This Lambda Does

The Event Log Checkpoint Lambda:

1. **Reads event log files** from an S3 bucket (JSON format)
2. **Loads existing checkpoint** (Parquet file) if available
3. **Processes only new events** since the last checkpoint
4. **Validates and transforms** event data using Pydantic models
5. **Writes updated checkpoint** back to S3 in Parquet format

This enables incremental processing of event logs without reprocessing historical data, making analytical queries fast and cost-effective.

## Directory Structure

```
lambda/event_log_checkpoint/
├── README.md                    # This file - Lambda overview
├── TERRAFORM.md                 # Terraform deployment documentation
├── src/                         # Lambda function source code
│   └── python/
│       └── checkpoint_lambda/
├── test/                        # Lambda function tests
│   └── python/
├── main.tf                      # Terraform main configuration
├── variables.tf                 # Terraform variables
├── outputs.tf                   # Terraform outputs
└── terraform.tfvars.example     # Example Terraform variables
```

## Lambda Configuration

- **Runtime**: Python 3.12
- **Memory**: 3GB (configurable)
- **Timeout**: 15 minutes (configurable)
- **Architecture**: x86_64
- **Layers**: AWS Lambda Powertools, Pydantic, Polars

## Key Features

### Incremental Processing

Only processes new event log files since the last checkpoint, avoiding expensive reprocessing of historical data.

### Efficient Data Format

Uses Parquet format for checkpoints, enabling:

- Fast analytical queries
- Columnar storage for better compression
- Schema enforcement and type safety

### Structured Logging

Uses AWS Lambda Powertools for:

- Structured JSON logging
- Correlation IDs for request tracking
- CloudWatch Logs integration

### Distributed Tracing

AWS X-Ray integration for:

- Performance analysis
- Dependency mapping
- Error tracking

## Environment Variables

The Lambda function uses these environment variables:

| Variable            | Description                          | Example                        |
| ------------------- | ------------------------------------ | ------------------------------ |
| `SOURCE_BUCKET`     | S3 bucket with event log files       | `nacc-event-logs`              |
| `CHECKPOINT_BUCKET` | S3 bucket for checkpoint files       | `nacc-checkpoints`             |
| `CHECKPOINT_KEY`    | S3 key for checkpoint Parquet file   | `checkpoints/events.parquet`   |
| `LOG_LEVEL`         | Logging level (INFO, DEBUG, WARNING) | `INFO`                         |
| `POWERTOOLS_*`      | AWS Lambda Powertools configuration  | Set automatically by framework |

## Development Workflow

This repo has a devcontainer definition that can be used in development.
If you are working in an IDE that supports it, you can just use the devcontainer directly.
Otherwise, the `bin` directory includes scripts that use the devcontainer CLI to manage the devcontainer on the host machine.

### Build Lambda Packages

Build all Lambda artifacts (function + layers):

```bash
./bin/start-devcontainer.sh
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::
```

Build specific targets:

```bash
# Function code only
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:lambda

# Powertools layer
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:powertools

# Data processing layer (Pydantic + Polars)
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:data_processing
```

### Run Tests

```bash
# All tests
./bin/exec-in-devcontainer.sh pants test lambda/event_log_checkpoint/test/python::

# Specific test file
./bin/exec-in-devcontainer.sh pants test lambda/event_log_checkpoint/test/python/test_lambda_function.py

# Specific test method
./bin/exec-in-devcontainer.sh pants test lambda/event_log_checkpoint/test/python/test_s3_retriever.py -- -k test_json_retrieval_completeness
```

### Code Quality

```bash
# Format code (always run first)
./bin/exec-in-devcontainer.sh pants fix ::

# Lint code
./bin/exec-in-devcontainer.sh pants lint ::

# Type check
./bin/exec-in-devcontainer.sh pants check ::
```

## Deployment

See [TERRAFORM.md](./TERRAFORM.md) for detailed deployment instructions using Terraform.

Quick deployment:

```bash
# Build packages
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::

# Deploy with Terraform
./bin/exec-in-devcontainer.sh terraform init
./bin/exec-in-devcontainer.sh terraform apply
```

## Monitoring

### CloudWatch Logs

View Lambda execution logs:

- Log group: `/aws/lambda/event-log-checkpoint`
- Structured JSON format with correlation IDs
- Configurable retention (default: 30 days)

### CloudWatch Alarms

Automatic alarms for:

- **Error rate**: Triggers when errors occur
- **Duration**: Triggers when execution time exceeds threshold

### X-Ray Tracing

Distributed tracing for:

- S3 operations
- Data processing steps
- Performance bottlenecks

## Troubleshooting

### Common Issues

**Missing build artifacts**

Ensure Pants packages are built before deployment:

```bash
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::
```

**Permission errors**

Verify IAM role has required S3 permissions:

- Read access to source bucket
- Read/write access to checkpoint bucket

**Memory or timeout errors**

Adjust Lambda configuration in Terraform:

- Increase `lambda_memory_size` (default: 3008 MB)
- Increase `lambda_timeout` (default: 900 seconds)

### Debugging

1. **Check CloudWatch logs** for error messages and stack traces
2. **Review X-Ray traces** for performance analysis
3. **Test locally** using pytest with mocked S3 operations
4. **Validate event data** using Pydantic models

## Security

The Lambda function follows least-privilege principles:

- **S3 read access**: Source bucket only
- **S3 read/write access**: Checkpoint bucket only
- **CloudWatch logs**: Write access for logging
- **X-Ray**: Write access for tracing

No access to:

- Other AWS services
- VPC resources
- Secrets or parameters

## Performance Considerations

### Memory Allocation

- **3GB recommended** for processing large event log files
- Polars DataFrame operations benefit from higher memory
- Adjust based on your data volume

### Timeout Configuration

- **15 minutes default** allows processing of large datasets
- Most executions complete in < 5 minutes
- Monitor CloudWatch metrics to optimize

### Layer Strategy

- **Powertools layer**: ~5MB, low update frequency
- **Data processing layer**: ~15-20MB, medium update frequency
- **Function code**: <1MB, high update frequency

Separate layers enable fast function-only deployments.

## Related Documentation

- [TERRAFORM.md](./TERRAFORM.md) - Terraform deployment guide
- [docs/EVENT-LOG-ARCHIVAL.md](./docs/EVENT-LOG-ARCHIVAL.md) - Event log archival and lifecycle management
- [ENVIRONMENTS.md](./ENVIRONMENTS.md) - Environment management guide (dev/staging/prod)
- [PRODUCTION-READINESS.md](./PRODUCTION-READINESS.md) - Production readiness checklist
- [context/docs/lambda-patterns.md](../../context/docs/lambda-patterns.md) - Lambda design patterns
- [context/docs/event-log-format.md](../../context/docs/event-log-format.md) - Event log format specification
