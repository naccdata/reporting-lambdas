# Terraform Deployment Guide

This guide covers deploying the Event Log Checkpoint Lambda function using Terraform with optimized layer management strategies.

## Infrastructure Overview

The Terraform configuration creates:

- **AWS Lambda function** with Python 3.12 runtime
- **Lambda layers** for dependencies (Powertools, Pydantic, Polars)
- **IAM role** with S3 read/write permissions
- **CloudWatch log group** with configurable retention
- **CloudWatch alarms** for monitoring
- **X-Ray tracing** configuration

## Prerequisites

### 1. Build Lambda Packages

Build all Lambda artifacts using Pants:

```bash
./bin/start-devcontainer.sh
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::
```

This creates:

- `dist/lambda/event_log_checkpoint/src/python/checkpoint_lambda/lambda.zip` - Function code
- `dist/lambda/event_log_checkpoint/src/python/checkpoint_lambda/powertools.zip` - Powertools layer
- `dist/lambda/event_log_checkpoint/src/python/checkpoint_lambda/data_processing.zip` - Data processing layer

### 2. Terraform Installation

Ensure Terraform >= 1.0 is installed (available in dev container).

### 3. AWS Credentials

Configure AWS credentials with permissions for:

- Lambda function management
- IAM role creation
- CloudWatch logs and alarms
- S3 bucket access

### 4. S3 Buckets

Create S3 buckets for:

- **Event logs** (source bucket)
- **Checkpoints** (checkpoint bucket)

## Layer Management Strategies

The configuration supports three layer management strategies for different use cases.

### Strategy 1: Automatic Layer Reuse (Recommended)

**Best for**: Most deployments, balancing speed and flexibility.

Reuses existing layers when possible, creates new ones when needed.

```hcl
reuse_existing_layers   = true
use_external_layer_arns = false
force_layer_update      = false
```

**Behavior**:

- Checks for existing layers with matching names
- Reuses if found, creates new version if not
- Minimizes layer creation and storage costs

### Strategy 2: External Layer ARNs

**Best for**: Cross-project reuse or centrally managed layers.

Uses pre-existing layer ARNs from other deployments or accounts.

```hcl
reuse_existing_layers   = false
use_external_layer_arns = true
external_layer_arns = [
  "arn:aws:lambda:us-east-1:123456789012:layer:powertools:5",
  "arn:aws:lambda:us-east-1:123456789012:layer:data-processing:3"
]
```

**Behavior**:

- Uses specified layer ARNs directly
- No layer creation or management
- Fastest deployment option

### Strategy 3: Force Layer Updates

**Best for**: Development environments requiring latest dependencies.

Always creates new layer versions on every deployment.

```hcl
reuse_existing_layers   = false
use_external_layer_arns = false
force_layer_update      = true
```

**Behavior**:

- Creates new layer versions every time
- Ensures latest dependencies are deployed
- Increases layer storage costs

## Quick Start

### 1. Copy Example Variables

```bash
cd lambda/event_log_checkpoint
cp terraform.tfvars.example terraform.tfvars
```

### 2. Configure Variables

Edit `terraform.tfvars` with your configuration:

```hcl
source_bucket          = "your-event-logs-bucket"
checkpoint_bucket      = "your-checkpoint-bucket"
checkpoint_key_template = "checkpoints/{study}-{datatype}-events.parquet"
environment            = "dev"
log_level              = "INFO"
```

### 3. Initialize Terraform

```bash
./bin/exec-in-devcontainer.sh terraform init
```

### 4. Plan Deployment

```bash
./bin/exec-in-devcontainer.sh terraform plan
```

### 5. Apply Configuration

```bash
./bin/exec-in-devcontainer.sh terraform apply
```

## Configuration Variables

### Required Variables

| Variable            | Description                         | Example                |
| ------------------- | ----------------------------------- | ---------------------- |
| `source_bucket`     | S3 bucket containing event log files | `"submission-events"`  |
| `checkpoint_bucket` | S3 bucket for checkpoint files      | `"submission-events"`  |

### Checkpoint Configuration

| Variable                  | Default                                          | Description                                                      |
| ------------------------- | ------------------------------------------------ | ---------------------------------------------------------------- |
| `checkpoint_key_template` | `"checkpoints/{study}-{datatype}-events.parquet"` | Template for checkpoint keys with {study} and {datatype} placeholders |

**Important**: The `checkpoint_key_template` variable is required and must contain both `{study}` and `{datatype}` placeholders. The Lambda will validate this at startup and fail if placeholders are missing.

**Example templates**:

```hcl
# Production environment (recommended)
checkpoint_key_template = "prod/checkpoints/{study}-{datatype}-events.parquet"

# Development environment
checkpoint_key_template = "dev/checkpoints/{study}-{datatype}-events.parquet"

# Nested folder structure
checkpoint_key_template = "prod/checkpoints/{study}/{datatype}/events.parquet"
```

**Generated checkpoint files** (using production template):

- `prod/checkpoints/adrc-form-events.parquet`
- `prod/checkpoints/adrc-dicom-events.parquet`
- `prod/checkpoints/dvcid-form-events.parquet`
- `prod/checkpoints/leads-dicom-events.parquet`

### Optional Variables

| Variable                       | Default                                          | Description                           |
| ------------------------------ | ------------------------------------------------ | ------------------------------------- |
| `environment`                  | `"dev"`                                          | Environment name (dev/staging/prod)   |
| `log_level`                    | `"INFO"`                                         | Lambda logging level                  |
| `lambda_timeout`               | `900`                                            | Lambda timeout in seconds (15 min)    |
| `lambda_memory_size`           | `3008`                                           | Lambda memory in MB (3GB)             |
| `log_retention_days`           | `30`                                             | CloudWatch log retention              |
| `reuse_existing_layers`        | `true`                                           | Reuse existing layers if available    |
| `use_external_layer_arns`      | `false`                                          | Use external layer ARNs               |
| `force_layer_update`           | `false`                                          | Force layer updates                   |
| `external_layer_arns`          | `[]`                                             | List of external layer ARNs           |
| `alarm_sns_topic_arn`          | `""`                                             | SNS topic for alarms (optional)       |
| `manage_source_bucket_lifecycle` | `false`                                        | Manage S3 lifecycle policy            |
| `enable_event_log_archival`    | `true`                                           | Enable archival to Glacier            |
| `days_until_glacier_transition` | `90`                                            | Days before Glacier transition        |
| `days_until_deep_archive_transition` | `365`                                      | Days before Deep Archive (0=disable)  |
| `days_until_expiration`        | `0`                                              | Days before deletion (0=never)        |

### S3 Lifecycle Management

The configuration supports automatic archival of event log files to reduce storage costs. See [EVENT-LOG-ARCHIVAL.md](./EVENT-LOG-ARCHIVAL.md) for detailed information.

**Environment-specific configurations**:

- **Dev**: Delete files after 30 days (no archival)
- **Staging**: Archive to Glacier after 90 days, keep forever
- **Production**: Archive to Glacier (90 days) → Deep Archive (1 year), keep forever

To enable lifecycle management:

```hcl
manage_source_bucket_lifecycle     = true
enable_event_log_archival          = true
days_until_glacier_transition      = 90
days_until_deep_archive_transition = 365
days_until_expiration              = 0
```

## Deployment Workflows

### Development Environment

Fast iteration with automatic layer management:

```bash
# Build packages
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::

# Deploy with layer reuse
./bin/exec-in-devcontainer.sh terraform apply -var="reuse_existing_layers=true"
```

### Staging Environment

Test with specific layer versions:

```bash
# Deploy with layer reuse
./bin/exec-in-devcontainer.sh terraform apply \
  -var="environment=staging" \
  -var="reuse_existing_layers=true"
```

### Production Environment

Use specific layer versions for stability:

```bash
# Deploy with external layer ARNs
./bin/exec-in-devcontainer.sh terraform apply \
  -var="environment=prod" \
  -var="use_external_layer_arns=true" \
  -var='external_layer_arns=["arn:aws:lambda:us-east-1:123456789012:layer:powertools:5","arn:aws:lambda:us-east-1:123456789012:layer:data-processing:3"]'
```

### Function-Only Updates

For code changes without dependency updates:

```bash
# Build only function package
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:lambda

# Deploy only function
./bin/exec-in-devcontainer.sh terraform apply -target=aws_lambda_function.event_log_checkpoint
```

### Layer-Only Updates

Update layers without changing function code:

```bash
# Build layer packages
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:powertools
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:data_processing

# Deploy with force update
./bin/exec-in-devcontainer.sh terraform apply -var="force_layer_update=true"
```

## Terraform Outputs

The configuration provides comprehensive outputs after deployment:

### Lambda Function Details

- `lambda_function_arn` - Lambda function ARN
- `lambda_function_name` - Lambda function name
- `lambda_function_version` - Lambda function version
- `lambda_function_invoke_arn` - ARN for invoking the function

### Layer Information

- `powertools_layer_arn` - Powertools layer ARN (when managed)
- `powertools_layer_version` - Powertools layer version
- `data_processing_layer_arn` - Data processing layer ARN (when managed)
- `data_processing_layer_version` - Data processing layer version

### IAM Resources

- `lambda_role_arn` - IAM role ARN
- `lambda_role_name` - IAM role name

### CloudWatch Resources

- `cloudwatch_log_group_name` - Log group name
- `cloudwatch_log_group_arn` - Log group ARN
- `error_alarm_arn` - Error alarm ARN
- `duration_alarm_arn` - Duration alarm ARN

### Configuration Summary

- `environment_variables` - Lambda environment variables
- `layer_strategy` - Active layer management strategy

## Monitoring and Alarms

### CloudWatch Alarms

The infrastructure includes two CloudWatch alarms:

#### Error Alarm

- **Metric**: Lambda errors
- **Threshold**: > 0 errors
- **Period**: 5 minutes
- **Evaluation**: 1 period

#### Duration Alarm

- **Metric**: Lambda duration
- **Threshold**: > 600,000 ms (10 minutes)
- **Period**: 5 minutes
- **Evaluation**: 1 period

### SNS Notifications

Configure SNS notifications by setting `alarm_sns_topic_arn`:

```hcl
alarm_sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:lambda-alarms"
```

### CloudWatch Logs

- **Log group**: `/aws/lambda/event-log-checkpoint-{environment}`
- **Retention**: Configurable (default: 30 days)
- **Format**: Structured JSON with correlation IDs

## Cost Optimization

### Layer Storage Costs

- Each layer version consumes storage space (~20-25MB total)
- Old versions can be cleaned up after successful deployments
- Use `reuse_existing_layers=true` to minimize layer creation

### Deployment Time Optimization

| Strategy                | Deployment Time | Use Case                    |
| ----------------------- | --------------- | --------------------------- |
| External layer ARNs     | ~30 seconds     | Production, stable layers   |
| Layer reuse             | ~60 seconds     | Development, most deploys   |
| Function-only update    | ~45 seconds     | Code changes only           |
| Force layer update      | ~90 seconds     | Dependency updates          |

### Lambda Execution Costs

- **Memory**: 3GB recommended for large datasets
- **Duration**: Most executions < 5 minutes
- **Invocations**: Depends on event log volume

Monitor CloudWatch metrics to optimize memory and timeout settings.

## Troubleshooting

### Common Issues

#### Missing Build Artifacts

**Error**: `Error: error creating Lambda Function: InvalidParameterValueException`

**Solution**: Ensure Pants packages are built before deployment:

```bash
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::
```

#### Layer Size Limits

**Error**: `Error: error creating Lambda Layer: InvalidParameterValueException: Unzipped size must be smaller than 262144000 bytes`

**Solution**: Each layer must be < 250MB unzipped. Check layer contents and dependencies.

#### Permission Errors

**Error**: `Error: error creating Lambda Function: AccessDeniedException`

**Solution**: Verify AWS credentials and IAM permissions for Lambda, IAM, and CloudWatch.

#### Layer Not Found

**Error**: `Error: error creating Lambda Function: ResourceNotFoundException: Layer version not found`

**Solution**: Check layer names and regions match. Ensure layers are created before function.

### Debugging Terraform

#### Enable Debug Logging

```bash
export TF_LOG=DEBUG
./bin/exec-in-devcontainer.sh terraform apply
```

#### Validate Configuration

```bash
./bin/exec-in-devcontainer.sh terraform validate
```

#### Format Configuration

```bash
./bin/exec-in-devcontainer.sh terraform fmt
```

#### Show Current State

```bash
./bin/exec-in-devcontainer.sh terraform show
```

## Security Best Practices

### IAM Permissions

The Lambda function has minimal required permissions:

- **S3 read access**: Source bucket only
- **S3 read/write access**: Checkpoint bucket only
- **CloudWatch logs**: Write access for logging
- **X-Ray**: Write access for tracing

### Terraform State

- Store Terraform state in S3 with encryption
- Enable state locking with DynamoDB
- Use separate state files per environment

Example backend configuration:

```hcl
terraform {
  backend "s3" {
    bucket         = "terraform-state-bucket"
    key            = "lambda/event-log-checkpoint/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

### Secrets Management

- Use AWS Secrets Manager or Parameter Store for sensitive values
- Never commit secrets to version control
- Use Terraform data sources to retrieve secrets

## Multi-Environment Deployment

### Workspace Strategy

Use Terraform workspaces for multiple environments:

```bash
# Create workspaces
./bin/exec-in-devcontainer.sh terraform workspace new dev
./bin/exec-in-devcontainer.sh terraform workspace new staging
./bin/exec-in-devcontainer.sh terraform workspace new prod

# Switch workspace
./bin/exec-in-devcontainer.sh terraform workspace select dev

# Deploy to current workspace
./bin/exec-in-devcontainer.sh terraform apply
```

### Variable Files Strategy

Use separate variable files per environment:

```bash
# Development
./bin/exec-in-devcontainer.sh terraform apply -var-file="dev.tfvars"

# Staging
./bin/exec-in-devcontainer.sh terraform apply -var-file="staging.tfvars"

# Production
./bin/exec-in-devcontainer.sh terraform apply -var-file="prod.tfvars"
```

## Cleanup

### Destroy All Resources

```bash
./bin/exec-in-devcontainer.sh terraform destroy
```

**Note**: This will delete the Lambda function and layers but preserve S3 buckets and their contents.

### Destroy Specific Resources

```bash
# Destroy only Lambda function
./bin/exec-in-devcontainer.sh terraform destroy -target=aws_lambda_function.event_log_checkpoint

# Destroy only layers
./bin/exec-in-devcontainer.sh terraform destroy -target=aws_lambda_layer_version.powertools
./bin/exec-in-devcontainer.sh terraform destroy -target=aws_lambda_layer_version.data_processing
```

### Clean Up Old Layer Versions

Old layer versions are not automatically deleted. Clean them up manually:

```bash
# List layer versions
aws lambda list-layer-versions --layer-name event-log-checkpoint-powertools

# Delete specific version
aws lambda delete-layer-version --layer-name event-log-checkpoint-powertools --version-number 1
```

## Related Documentation

- [README.md](../README.md) - Lambda function overview
- [EVENT-LOG-ARCHIVAL.md](./EVENT-LOG-ARCHIVAL.md) - Event log archival and lifecycle management
- [terraform/modules/README.md](../../terraform/modules/README.md) - Terraform modules documentation
- [context/docs/deployment-guide.md](../../context/docs/deployment-guide.md) - General deployment guide
