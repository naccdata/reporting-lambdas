# Event Log Checkpoint Lambda - Terraform Infrastructure

This directory contains Terraform configuration for deploying the Event Log Checkpoint Lambda function with optimized layer management.

## Overview

The infrastructure creates:

- AWS Lambda function with Python 3.12 runtime
- Lambda layers for dependencies (Powertools, Pydantic, Polars)
- IAM role with S3 read/write permissions
- CloudWatch log group with configurable retention
- CloudWatch alarms for monitoring
- X-Ray tracing configuration

## Layer Management Strategies

The configuration supports multiple layer management strategies for different use cases:

### Strategy 1: Automatic Layer Reuse (Recommended)

Best for most deployments. Reuses existing layers when possible, creates new ones when needed.

```hcl
reuse_existing_layers   = true
use_external_layer_arns = false
force_layer_update      = false
```

### Strategy 2: External Layer ARNs

Best for cross-project reuse or when layers are managed centrally.

```hcl
reuse_existing_layers   = false
use_external_layer_arns = true
external_layer_arns = [
  "arn:aws:lambda:region:account:layer:powertools:version",
  "arn:aws:lambda:region:account:layer:data-processing:version"
]
```

### Strategy 3: Force Layer Updates

Best for development environments where you always want the latest dependencies.

```hcl
reuse_existing_layers = false
use_external_layer_arns = false
force_layer_update = true
```

## Prerequisites

1. **Build Lambda packages** using Pants:
   ```bash
   ./bin/start-devcontainer.sh
   ./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::
   ```

2. **Terraform installed** (>= 1.0)

3. **AWS credentials configured** with appropriate permissions

4. **S3 buckets created** for event logs and checkpoints

## Quick Start

1. **Copy example variables file:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit terraform.tfvars** with your configuration:
   ```hcl
   source_bucket     = "your-event-logs-bucket"
   checkpoint_bucket = "your-checkpoint-bucket"
   environment       = "dev"
   ```

3. **Initialize and deploy:**
   ```bash
   ./bin/exec-in-devcontainer.sh terraform init
   ./bin/exec-in-devcontainer.sh terraform plan
   ./bin/exec-in-devcontainer.sh terraform apply
   ```

## Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `source_bucket` | S3 bucket containing event log files | `"nacc-event-logs"` |
| `checkpoint_bucket` | S3 bucket for checkpoint parquet files | `"nacc-checkpoints"` |

## Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `checkpoint_key` | `"checkpoints/events.parquet"` | S3 key for checkpoint file |
| `environment` | `"dev"` | Environment name (dev/staging/prod) |
| `log_level` | `"INFO"` | Lambda logging level |
| `lambda_timeout` | `900` | Lambda timeout in seconds (15 min) |
| `lambda_memory_size` | `3008` | Lambda memory in MB (3GB) |
| `log_retention_days` | `30` | CloudWatch log retention |
| `reuse_existing_layers` | `true` | Reuse existing layers if available |
| `use_external_layer_arns` | `false` | Use external layer ARNs |
| `force_layer_update` | `false` | Force layer updates |
| `alarm_sns_topic_arn` | `""` | SNS topic for alarms (optional) |

## Deployment Workflows

### Development Environment

Fast iteration with automatic layer management:

```bash
# Build packages
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::

# Deploy with layer reuse
./bin/exec-in-devcontainer.sh terraform apply -var="reuse_existing_layers=true"
```

### Production Environment

Use specific layer versions for stability:

```bash
# Deploy with external layer ARNs
./bin/exec-in-devcontainer.sh terraform apply \
  -var="use_external_layer_arns=true" \
  -var="external_layer_arns=[\"arn:aws:lambda:us-east-1:123456789012:layer:powertools:5\",\"arn:aws:lambda:us-east-1:123456789012:layer:data-processing:3\"]"
```

### Function-Only Updates

For code changes without dependency updates:

```bash
# Build only function package
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:lambda

# Deploy only function
./bin/exec-in-devcontainer.sh terraform apply -target=aws_lambda_function.event_log_checkpoint
```

## Outputs

The configuration provides comprehensive outputs:

- **Lambda function details**: ARN, name, version
- **Layer information**: ARNs and versions (when managed)
- **IAM role details**: ARN and name
- **CloudWatch resources**: Log group and alarms
- **Configuration summary**: Environment variables and settings

## Monitoring

The infrastructure includes CloudWatch alarms for:

- **Lambda errors**: Triggers when error count > 0
- **Lambda duration**: Triggers when execution time > 10 minutes

Configure SNS notifications by setting `alarm_sns_topic_arn`.

## Cost Optimization

### Layer Storage

- Each layer version consumes storage space
- Old versions can be cleaned up after successful deployments
- Use `reuse_existing_layers=true` to minimize layer creation

### Deployment Time

- **Layer reuse**: ~30 seconds faster
- **Function-only updates**: ~60 seconds faster
- **External layer ARNs**: Fastest option

## Troubleshooting

### Common Issues

1. **Missing build artifacts**: Ensure Pants packages are built before deployment
2. **Layer size limits**: Each layer must be < 250MB unzipped
3. **Permission errors**: Verify AWS credentials and S3 bucket permissions
4. **Layer not found**: Check layer names and regions match

### Debugging

1. **Check CloudWatch logs**: `/aws/lambda/event-log-checkpoint`
2. **Review X-Ray traces**: For performance analysis
3. **Monitor CloudWatch metrics**: For execution patterns

## Security

The Lambda function has minimal required permissions:

- **S3 read access**: Source bucket (event logs)
- **S3 read/write access**: Checkpoint bucket
- **CloudWatch logs**: Write access
- **X-Ray**: Trace write access

## Cleanup

To destroy all resources:

```bash
./bin/exec-in-devcontainer.sh terraform destroy
```

Note: This will delete the Lambda function but preserve S3 buckets and their contents.