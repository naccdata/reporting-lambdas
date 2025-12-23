# Event Log Checkpoint Lambda

An AWS Lambda function that processes visit event logs from S3 storage and creates queryable checkpoint parquet files for analytical reporting. The Lambda supports incremental processing, validating events against schema specifications, and aggregating data for monthly reporting queries.

## Overview

This Lambda function scrapes event log files from the NACC Flywheel instance stored in S3, validates them using Pydantic models, and creates/updates a checkpoint parquet file optimized for analytical queries. The system follows an incremental processing approach: it reads the previous checkpoint (if it exists), retrieves only new JSON event files since the last checkpoint, validates them, and merges them to create an updated checkpoint file.

### Key Features

- **Incremental Processing**: Only processes new events since the last checkpoint, significantly improving performance
- **Schema Validation**: Uses Pydantic models to validate event structure and data types
- **Error Resilience**: Continues processing valid events even when some files fail validation
- **Analytical Optimization**: Outputs parquet files optimized for monthly reporting queries
- **Observability**: Full logging, tracing, and metrics using AWS Lambda Powertools
- **Event Evolution Support**: Preserves all event versions to track data completeness over time

## Architecture

The system follows a pipeline architecture with these components:

1. **CheckpointReader**: Reads previous checkpoint and determines what new events to process
2. **S3EventRetriever**: Retrieves event log files from S3 with timestamp filtering
3. **EventValidator**: Validates events using Pydantic models
4. **CheckpointMerger**: Merges previous checkpoint data with newly validated events
5. **ParquetWriter**: Writes merged events to parquet format and uploads to S3

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

## Development Workflow

All development uses the established dev container workflow:

### Starting Development

```bash
./bin/start-devcontainer.sh
```

### Running Quality Checks

```bash
./bin/exec-in-devcontainer.sh pants fix lint check test ::
```

### Building Lambda

```bash
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::
```

### Running Tests

```bash
./bin/exec-in-devcontainer.sh pants test lambda/event_log_checkpoint/test/python::
```

### Interactive Development

```bash
./bin/terminal.sh  # For exploration and debugging only
```

### Stopping Development

```bash
./bin/stop-devcontainer.sh
```

**Important**: Use `./bin/exec-in-devcontainer.sh <command>` for all pants and terraform commands. Terraform is only available inside the dev container.

## Project Structure

```
lambda/event_log_checkpoint/
├── src/python/checkpoint_lambda/
│   ├── lambda_function.py          # Main Lambda handler
│   ├── models.py                   # Pydantic VisitEvent model
│   ├── checkpoint_reader.py        # Reads previous checkpoints
│   ├── s3_retriever.py            # Retrieves events from S3
│   ├── validator.py               # Validates events
│   ├── merger.py                  # Merges checkpoint data
│   └── parquet_writer.py          # Writes parquet files
├── test/python/                   # Unit and property tests
├── main.tf                        # Terraform configuration
├── variables.tf                   # Terraform variables
└── outputs.tf                     # Terraform outputs
```

## Event Schema

The Lambda processes visit events with the following structure:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| action | str | Yes | Event type: submit, pass-qc, not-pass-qc, delete |
| study | str | Yes | Study identifier (default: "adrc") |
| pipeline_adcid | int | Yes | Pipeline/center identifier |
| project_label | str | Yes | Flywheel project label |
| center_label | str | Yes | Center/group label |
| gear_name | str | Yes | Gear that logged the event |
| ptid | str | Yes | Participant ID (pattern: ^[A-Z0-9]+$, max 10 chars) |
| visit_date | date | Yes | Visit date (ISO format YYYY-MM-DD) |
| visit_number | str | Yes | Visit number |
| datatype | str | Yes | Data type (form, dicom, etc.) |
| module | str | No | Module name (UDS, FTLD, etc.) |
| packet | str | No | Packet type (I, F, etc.) |
| timestamp | datetime | Yes | When action occurred (ISO 8601) |

## Deployment

### Lambda Layer Strategy

The deployment uses a multi-layer approach for optimal performance:

#### Layer 1: AWS Lambda Powertools

- **Contents**: AWS Lambda Powertools (includes boto3)
- **Size**: ~5MB
- **Update Frequency**: Low

#### Layer 2: Data Processing

- **Contents**: Pydantic and Polars libraries
- **Size**: ~15-20MB
- **Update Frequency**: Medium

### Building and Deploying

#### Build Lambda Packages

```bash
# Build Lambda function
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:lambda

# Build Powertools layer
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:powertools

# Build data processing layer
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:data_processing
```

#### Deploy with Terraform

From the lambda directory:

```bash
# Standard deployment (reuses existing layers)
./bin/exec-in-devcontainer.sh bash -c "cd lambda/event_log_checkpoint && terraform apply"

# Force layer updates
./bin/exec-in-devcontainer.sh bash -c "cd lambda/event_log_checkpoint && terraform apply -var='reuse_existing_layers=false'"

# Function-only deployment (fastest for code changes)
./bin/exec-in-devcontainer.sh bash -c "cd lambda/event_log_checkpoint && terraform apply -target=aws_lambda_function.event_log_checkpoint"
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| SOURCE_BUCKET | S3 bucket containing event logs | nacc-events |
| CHECKPOINT_BUCKET | S3 bucket for checkpoint files | nacc-checkpoints |
| CHECKPOINT_KEY | S3 key for checkpoint parquet file | checkpoints/events.parquet |
| LOG_LEVEL | Logging level | INFO |
| POWERTOOLS_SERVICE_NAME | Service name for tracing | event-log-checkpoint |

## Usage

### Lambda Event Format

```json
{
  "source_bucket": "nacc-event-logs",
  "prefix": "logs/",
  "checkpoint_bucket": "nacc-checkpoints", 
  "checkpoint_key": "checkpoints/events.parquet"
}
```

### Response Format

```json
{
  "statusCode": 200,
  "checkpoint_path": "s3://nacc-checkpoints/checkpoints/events.parquet",
  "new_events_processed": 150,
  "total_events": 10250,
  "events_failed": 2,
  "last_processed_timestamp": "2024-01-15T14:30:00Z",
  "execution_time_ms": 45000
}
```

## Incremental Processing

The Lambda supports efficient incremental processing:

### First Run

- Processes all event log files in S3
- Creates initial checkpoint parquet file
- Returns total events processed

### Subsequent Runs

- Reads previous checkpoint to get last processed timestamp
- Only retrieves and processes events with timestamp > last checkpoint
- Merges new events with previous checkpoint data
- Overwrites checkpoint file with merged data

This approach provides significant performance benefits:

- **Reduced S3 Operations**: Only reads new files
- **Lower Memory Usage**: Only processes new events
- **Faster Execution**: Typical incremental runs complete in 30-60 seconds
- **Cost Savings**: Shorter execution time = lower Lambda costs

## Event Evolution Support

The system handles evolving event data intelligently:

- **Multiple Events**: Preserves all events for the same visit with different timestamps
- **Data Evolution**: Events may become more complete over time (e.g., module/packet fields populated later)
- **Audit Trail**: All event versions preserved for compliance and analysis
- **Latest Data**: Analysts can query for most recent event per visit to get complete data

## Analytical Queries

The checkpoint parquet file supports various analytical patterns:

### Latest Event Per Visit

```sql
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

### Monthly Error Counts

```sql
SELECT center_label, COUNT(*) as error_count
FROM checkpoint_events
WHERE action = 'not-pass-qc' 
  AND visit_date >= '2024-01-01' 
  AND visit_date < '2024-02-01'
GROUP BY center_label
```

### QC Timing Analysis

```sql
SELECT 
  center_label,
  AVG(DATEDIFF(timestamp, visit_date)) as avg_qc_days
FROM checkpoint_events
WHERE action IN ('pass-qc', 'not-pass-qc')
GROUP BY center_label
```

## Testing

The project includes comprehensive testing:

### Unit Tests

- Component-specific tests for each module
- Error handling and edge cases
- S3 integration tests

### Property-Based Tests

- Uses Hypothesis library for property verification
- Tests universal properties across many inputs
- Minimum 100 iterations per property test

### Integration Tests

- End-to-end Lambda execution
- Real S3 integration (using LocalStack or test buckets)
- CloudWatch logs and metrics verification

### Running Tests

```bash
# Run all tests
./bin/exec-in-devcontainer.sh pants test lambda/event_log_checkpoint/test/python::

# Run specific test file
./bin/exec-in-devcontainer.sh pants test lambda/event_log_checkpoint/test/python:test_validator

# Run with coverage
./bin/exec-in-devcontainer.sh pants test --coverage-py-report=html lambda/event_log_checkpoint/test/python::
```

## Monitoring

### CloudWatch Metrics

- `NewEventsProcessed`: Count of newly processed events
- `TotalEvents`: Total events in checkpoint
- `EventsFailed`: Count of failed events
- `ExecutionTime`: Total execution time
- `CheckpointFileSize`: Size of checkpoint file

### X-Ray Tracing

- S3 operations tracing
- Validation performance
- Parquet write operations

### Recommended Alarms

- Lambda errors > 0
- Lambda duration > 10 minutes
- EventsFailed > 10% of EventsProcessed

## Performance

### Expected Performance

- **First run**: 5-10 minutes for 10,000+ historical events
- **Incremental runs**: 30-60 seconds for 100-1000 new events
- **Memory**: 3GB to handle large datasets
- **Timeout**: 15 minutes maximum

### Optimization Features

- Incremental processing reduces processing time by 90%+
- Efficient parquet merge operations
- Snappy compression for optimal size/speed balance
- Connection pooling for S3 operations

## Error Handling

The Lambda handles errors gracefully:

- **Malformed JSON**: Logs error and continues processing
- **Schema validation failures**: Logs specific errors and continues
- **S3 permission errors**: Logs error and fails execution
- **Partial failures**: Includes valid events in output, logs failed events
- **Unexpected exceptions**: Logs full error details and fails execution

## Contributing

1. Follow the established dev container workflow
2. Run quality checks before committing: `./bin/exec-in-devcontainer.sh pants fix lint check test ::`
3. Add tests for new functionality
4. Update documentation for significant changes
5. Use property-based tests for universal behaviors

## License

See LICENSE file for details.
