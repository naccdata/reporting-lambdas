# Event Log Checkpoint Lambda

This Lambda function processes event log files from S3, creates incremental checkpoints in Parquet format, and enables efficient analytical queries on event data.

## What This Lambda Does

The Event Log Checkpoint Lambda:

1. **Reads event log files** from an S3 bucket (JSON format)
2. **Filters sandbox events** - Excludes events from projects matching "sandbox-*" pattern
3. **Groups events by study and datatype** - Creates separate checkpoints for each combination
4. **Loads existing checkpoints** (Parquet files) if available for each study-datatype
5. **Processes only new events** since the last checkpoint for each study-datatype
6. **Validates and transforms** event data using Pydantic models
7. **Writes updated checkpoints** back to S3 in Parquet format

This enables incremental processing of event logs without reprocessing historical data, making analytical queries fast and cost-effective. By grouping checkpoints by study and datatype, queries can efficiently target specific data categories.

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

### Sandbox Event Filtering

Automatically excludes events from sandbox projects (project_label matching "sandbox-*" pattern) to ensure production analytical queries only include live data. Sandbox projects are used by centers to practice submissions without affecting production data.

### Study-Datatype Grouping

Creates separate checkpoint files for each study-datatype combination, enabling:

- Efficient queries targeting specific data categories
- Independent processing state per study-datatype
- Isolated failure handling (one checkpoint failure doesn't affect others)
- Parallel processing opportunities

### Checkpoint File Naming

Checkpoint files follow a configurable template pattern with `{study}` and `{datatype}` placeholders.

**Default Template**: `checkpoints/{study}/{datatype}/events.parquet`

**Example Output**:
- `checkpoints/adrc/form/events.parquet`
- `checkpoints/adrc/dicom/events.parquet`
- `checkpoints/dvcid/form/events.parquet`
- `checkpoints/leads/dicom/events.parquet`

**Alternative Templates**:
- Flat structure: `checkpoints/{study}-{datatype}-events.parquet`
- With environment prefix: `prod/checkpoints/{study}/{datatype}/events.parquet`
- Custom naming: `data/{study}/checkpoints/{datatype}.parquet`

The template is configured via the `CHECKPOINT_KEY_TEMPLATE` environment variable and must contain both `{study}` and `{datatype}` placeholders.

### Incremental Processing

Only processes new event log files since the last checkpoint for each study-datatype combination, avoiding expensive reprocessing of historical data. Each study-datatype maintains its own processing timestamp.

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

| Variable                  | Description                                                      | Example                                          | Required |
| ------------------------- | ---------------------------------------------------------------- | ------------------------------------------------ | -------- |
| `BUCKET`                  | S3 bucket for event logs and checkpoints                         | `submission-events`                              | Yes      |
| `PREFIX`                  | S3 prefix for event log files                                    | `prod/logs/` or `""` (empty for root)            | No       |
| `CHECKPOINT_BUCKET`       | S3 bucket for checkpoint files (informational only)              | `submission-events`                              | No       |
| `CHECKPOINT_KEY_TEMPLATE` | Template for checkpoint keys with {study} and {datatype}         | `prod/checkpoints/{study}/{datatype}/events.parquet` | Yes      |
| `LOG_LEVEL`               | Logging level (INFO, DEBUG, WARNING)                             | `INFO`                                           | No       |
| `ENVIRONMENT`             | Environment name (dev/staging/prod)                              | `dev`                                            | No       |
| `POWERTOOLS_*`            | AWS Lambda Powertools configuration                              | Set automatically by framework                   | No       |

### CHECKPOINT_KEY_TEMPLATE

This variable defines the S3 key pattern for checkpoint files. It must contain two placeholders:

- `{study}` - Replaced with the study identifier (e.g., "adrc", "dvcid", "leads")
- `{datatype}` - Replaced with the datatype identifier (e.g., "form", "dicom", "apoe")

**Example templates**:

```bash
# Production environment
CHECKPOINT_KEY_TEMPLATE="prod/checkpoints/{study}/{datatype}/events.parquet"

# Development environment
CHECKPOINT_KEY_TEMPLATE="dev/checkpoints/{study}/{datatype}/events.parquet"

# Nested folder structure
CHECKPOINT_KEY_TEMPLATE="prod/checkpoints/{study}/{datatype}/events.parquet"
```

**Validation**: The Lambda will fail at startup if the template is missing either placeholder.

## Development Workflow

This repo has a devcontainer definition that can be used in development.
If you are working in an IDE that supports it, you can just use the devcontainer directly.
Otherwise, the `bin` directory includes scripts that use the devcontainer CLI to manage the devcontainer on the host machine.

## Event Processing Behavior

### Sandbox Event Filtering

The Lambda automatically filters out events from sandbox projects to ensure production data quality:

- **Pattern**: Events with `project_label` starting with "sandbox-" are excluded
- **Examples of filtered projects**:
  - `sandbox-form`
  - `sandbox-dicom-leads`
  - `sandbox-form-alpha`
- **Examples of included projects**:
  - `ingest-form`
  - `ingest-dicom`
  - `adrc-form`

**Monitoring**: The count of filtered events is logged and emitted as a CloudWatch metric (`EventsFiltered`).

### Study-Datatype Grouping

Events are grouped by their `study` and `datatype` fields, creating independent checkpoints:

- **Study field**: Identifies the research study (e.g., "adrc", "dvcid", "leads")
- **Datatype field**: Identifies the data category (e.g., "form", "dicom", "apoe", "biomarker")
- **Checkpoint independence**: Each study-datatype combination maintains its own:
  - Processing timestamp (last processed event)
  - Checkpoint file in S3
  - Processing state

**Benefits**:

- Queries can target specific study-datatype combinations without loading unrelated data
- Failures in one checkpoint don't affect others
- New study-datatype combinations are automatically detected and processed
- Each combination can be reprocessed independently if needed

**Monitoring**: Event counts per study-datatype are logged and emitted as CloudWatch metrics (`EventsProcessedByStudyDatatype`) with study and datatype dimensions.

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

See [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) for detailed deployment instructions.

Quick deployment:

```bash
# Build packages
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::

# Deploy with Terraform
cd lambda/event_log_checkpoint
./bin/exec-in-devcontainer.sh terraform apply
```

For Terraform configuration, see [docs/TERRAFORM.md](./docs/TERRAFORM.md).

## Monitoring

### CloudWatch Logs

View Lambda execution logs:

- Log group: `/aws/lambda/event-log-checkpoint`
- Structured JSON format with correlation IDs
- Configurable retention (default: 30 days)

**Key log events**:

- Sandbox event filtering with filtered count
- Study-datatype grouping with event counts per group
- Checkpoint save operations with study, datatype, and event count
- Checkpoint save failures with error details
- Processing summary with totals and group details

### CloudWatch Metrics

Custom metrics emitted by the Lambda:

| Metric Name                       | Type  | Dimensions         | Description                                    |
| --------------------------------- | ----- | ------------------ | ---------------------------------------------- |
| `EventsFiltered`                  | Count | None               | Number of sandbox events filtered out          |
| `EventsProcessedByStudyDatatype`  | Count | Study, Datatype    | Events processed per study-datatype group      |
| `CheckpointsSaved`                | Count | None               | Number of checkpoints successfully saved       |
| `CheckpointSaveFailures`          | Count | Study, Datatype    | Number of checkpoint save failures             |

**Namespace**: `EventLogCheckpoint`

**Use cases**:

- Monitor filtering effectiveness (how many sandbox events are excluded)
- Track processing volume per study-datatype combination
- Alert on checkpoint save failures for specific study-datatype groups
- Analyze processing patterns across different data categories

### CloudWatch Alarms

Automatic alarms for:

- **Error rate**: Triggers when errors occur
- **Duration**: Triggers when execution time exceeds threshold

**Recommended additional alarms**:

- Alert on `CheckpointSaveFailures` > 0 for critical study-datatype combinations
- Alert on `EventsFiltered` anomalies (unexpected spike in sandbox events)

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

- [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) - Deployment guide
- [docs/TERRAFORM.md](./docs/TERRAFORM.md) - Terraform configuration guide
- [docs/ENVIRONMENTS.md](./docs/ENVIRONMENTS.md) - Environment management guide (dev/staging/prod)
- [docs/EVENT-LOG-ARCHIVAL.md](./docs/EVENT-LOG-ARCHIVAL.md) - Event log archival and lifecycle management
- [docs/PRODUCTION-READINESS.md](./docs/PRODUCTION-READINESS.md) - Production readiness checklist
- [context/docs/lambda-patterns.md](../../context/docs/lambda-patterns.md) - Lambda design patterns
- [context/docs/event-log-format.md](../../context/docs/event-log-format.md) - Event log format specification
