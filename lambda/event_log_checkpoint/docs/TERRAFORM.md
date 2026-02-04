# Terraform Configuration Guide

This guide covers configuring Terraform for the Event Log Checkpoint Lambda function. For deployment instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## Infrastructure Overview

The Terraform configuration creates:

- **AWS Lambda function** with Python 3.12 runtime
- **Lambda layers** for dependencies (Powertools, Pydantic, Polars)
- **IAM role** with S3 read/write permissions
- **CloudWatch log group** with configurable retention
- **CloudWatch alarms** for monitoring
- **X-Ray tracing** configuration

## Workspace Management

This Lambda uses **Terraform workspaces** to manage multiple environments (dev, staging, prod) with isolated state.

### Available Workspaces

- **dev** - Development environment
- **staging** - Staging environment
- **prod** - Production environment

### Workspace Commands

```bash
# List workspaces (current marked with *)
terraform workspace list

# Switch workspace
terraform workspace select dev
terraform workspace select staging
terraform workspace select prod

# Show current workspace
terraform workspace show
```

**Important**: Always verify you're in the correct workspace before running Terraform commands!

## Initial Setup

### 1. Initialize Terraform

```bash
cd lambda/event_log_checkpoint
./bin/exec-in-devcontainer.sh terraform init
```

### 2. Select Workspace

```bash
# For dev environment
./bin/exec-in-devcontainer.sh terraform workspace select dev

# For staging environment
./bin/exec-in-devcontainer.sh terraform workspace select staging

# For prod environment
./bin/exec-in-devcontainer.sh terraform workspace select prod
```

### 3. Configure Environment Variables

Each environment has its own tfvars file:

- `terraform.dev.tfvars` - Development configuration
- `terraform.staging.tfvars` - Staging configuration
- `terraform.prod.tfvars` - Production configuration

Edit the appropriate file for your environment.

## Configuration Variables

### Required Variables

| Variable            | Description                          | Example               |
|---------------------|--------------------------------------|-----------------------|
| `source_bucket`     | S3 bucket containing event log files | `"submission-events"` |
| `checkpoint_bucket` | S3 bucket for checkpoint files       | `"submission-events"` |

### Checkpoint Configuration

| Variable                  | Default                                           | Description                                                           |
|---------------------------|---------------------------------------------------|-----------------------------------------------------------------------|
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

### Lambda Configuration

| Variable             | Default | Description                        |
|----------------------|---------|------------------------------------|
| `environment`        | `"dev"` | Environment name (dev/staging/prod) |
| `log_level`          | `"INFO"`| Lambda logging level               |
| `lambda_timeout`     | `900`   | Lambda timeout in seconds (15 min) |
| `lambda_memory_size` | `3008`  | Lambda memory in MB (3GB)          |

### CloudWatch Configuration

| Variable             | Default | Description                  |
|----------------------|---------|------------------------------|
| `log_retention_days` | `30`    | CloudWatch log retention     |
| `alarm_sns_topic_arn`| `""`    | SNS topic for alarms (optional) |

### Layer Management Configuration

| Variable                  | Default | Description                        |
|---------------------------|---------|------------------------------------|
| `reuse_existing_layers`   | `true`  | Reuse existing layers if available |
| `use_external_layer_arns` | `false` | Use external layer ARNs            |
| `force_layer_update`      | `false` | Force layer updates                |
| `external_layer_arns`     | `[]`    | List of external layer ARNs        |

### S3 Lifecycle Configuration

| Variable                             | Default | Description                          |
|--------------------------------------|---------|--------------------------------------|
| `manage_source_bucket_lifecycle`     | `false` | Manage S3 lifecycle policy           |
| `enable_event_log_archival`          | `true`  | Enable archival to Glacier           |
| `days_until_glacier_transition`      | `90`    | Days before Glacier transition       |
| `days_until_deep_archive_transition` | `365`   | Days before Deep Archive (0=disable) |
| `days_until_expiration`              | `0`     | Days before deletion (0=never)       |

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

**Best for**: Testing layer deployment or forcing new versions without content changes.

Always creates new layer versions on every deployment, even if content hasn't changed.

```hcl
reuse_existing_layers   = false
use_external_layer_arns = false
force_layer_update      = true
```

**Behavior**:

- Creates new layer versions every time
- Bypasses content hash checking
- Useful for testing or troubleshooting

**Note**: This is rarely needed in practice. Terraform automatically detects layer content changes via `source_code_hash` and creates new versions when the zip file changes. Use this only when you need to force a new version for testing purposes.

## Environment-Specific Configuration

### Development Environment

**File**: `terraform.dev.tfvars`

```hcl
environment                        = "dev"
source_bucket                      = "submission-events-dev"
checkpoint_bucket                  = "submission-events-dev"
checkpoint_key_template            = "dev/checkpoints/{study}-{datatype}-events.parquet"
log_level                          = "DEBUG"
log_retention_days                 = 7
reuse_existing_layers              = true
force_layer_update                 = false
manage_source_bucket_lifecycle     = true
enable_event_log_archival          = false
days_until_expiration              = 30
```

**Characteristics**:
- Debug logging enabled
- Short log retention (7 days)
- Automatic layer reuse
- Event logs deleted after 30 days (no archival)

### Staging Environment

**File**: `terraform.staging.tfvars`

```hcl
environment                        = "staging"
source_bucket                      = "submission-events-staging"
checkpoint_bucket                  = "submission-events-staging"
checkpoint_key_template            = "staging/checkpoints/{study}-{datatype}-events.parquet"
log_level                          = "INFO"
log_retention_days                 = 30
reuse_existing_layers              = true
force_layer_update                 = false
manage_source_bucket_lifecycle     = true
enable_event_log_archival          = true
days_until_glacier_transition      = 90
days_until_deep_archive_transition = 0
days_until_expiration              = 0
```

**Characteristics**:
- Info logging
- Standard log retention (30 days)
- Automatic layer reuse
- Event logs archived to Glacier after 90 days, kept forever

### Production Environment

**File**: `terraform.prod.tfvars`

```hcl
environment                        = "prod"
source_bucket                      = "submission-events-prod"
checkpoint_bucket                  = "submission-events-prod"
checkpoint_key_template            = "prod/checkpoints/{study}-{datatype}-events.parquet"
log_level                          = "INFO"
log_retention_days                 = 90
reuse_existing_layers              = true
force_layer_update                 = false
alarm_sns_topic_arn                = "arn:aws:sns:us-east-1:123456789012:lambda-alarms"
manage_source_bucket_lifecycle     = true
enable_event_log_archival          = true
days_until_glacier_transition      = 90
days_until_deep_archive_transition = 365
days_until_expiration              = 0
```

**Characteristics**:
- Info logging
- Extended log retention (90 days)
- SNS alerts configured
- Automatic layer reuse for stability
- Event logs: Glacier (90 days) → Deep Archive (1 year), kept forever

## S3 Lifecycle Management

The configuration supports automatic archival of event log files to reduce storage costs. See [EVENT-LOG-ARCHIVAL.md](./EVENT-LOG-ARCHIVAL.md) for detailed information.

### Enable Lifecycle Management

```hcl
manage_source_bucket_lifecycle     = true
enable_event_log_archival          = true
days_until_glacier_transition      = 90
days_until_deep_archive_transition = 365
days_until_expiration              = 0
```

### Lifecycle Transitions

**Standard → Glacier**:
- After `days_until_glacier_transition` days
- Reduces storage costs by ~90%
- Retrieval time: minutes to hours

**Glacier → Deep Archive**:
- After `days_until_deep_archive_transition` days
- Set to `0` to disable
- Reduces storage costs by ~95%
- Retrieval time: 12-48 hours

**Expiration**:
- After `days_until_expiration` days
- Set to `0` to keep forever
- Permanently deletes files

## Monitoring Configuration

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

## Security Configuration

### IAM Permissions

The Lambda function has minimal required permissions:

- **S3 read access**: Source bucket only
- **S3 read/write access**: Checkpoint bucket only
- **CloudWatch logs**: Write access for logging
- **X-Ray**: Write access for tracing

### Terraform State Management

Store Terraform state in S3 with encryption:

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

**Best practices**:
- Enable S3 versioning for state recovery
- Use DynamoDB for state locking (optional)
- Use separate state files per environment
- Encrypt state at rest

### Secrets Management

For sensitive values:

- Use AWS Secrets Manager or Parameter Store
- Never commit secrets to version control
- Use Terraform data sources to retrieve secrets

Example:

```hcl
data "aws_secretsmanager_secret_version" "api_key" {
  secret_id = "lambda/event-log-checkpoint/api-key"
}

resource "aws_lambda_function" "event_log_checkpoint" {
  environment {
    variables = {
      API_KEY = data.aws_secretsmanager_secret_version.api_key.secret_string
    }
  }
}
```

## Multi-Environment Configuration

This Lambda uses **Terraform workspaces** to isolate state between environments.

### Workspace-Based Deployment

Each environment has its own workspace and variable file:

```bash
# Deploy to dev
terraform workspace select dev
terraform apply -var-file="terraform.dev.tfvars"

# Deploy to staging
terraform workspace select staging
terraform apply -var-file="terraform.staging.tfvars"

# Deploy to prod
terraform workspace select prod
terraform apply -var-file="terraform.prod.tfvars"
```

### Workspace Isolation

Each workspace maintains separate state:

- **dev workspace** → Separate state for dev resources
- **staging workspace** → Separate state for staging resources  
- **prod workspace** → Separate state for prod resources

**Benefits**:
- Changes in dev don't affect staging or prod
- Deploy different versions to each environment
- Each environment has isolated AWS resources

### Resource Naming

Resources are named with the environment suffix:

- **Dev**: `event-log-checkpoint-dev`, `event-log-checkpoint-powertools-dev`
- **Staging**: `event-log-checkpoint-staging`, `event-log-checkpoint-powertools-staging`
- **Prod**: `event-log-checkpoint-prod`, `event-log-checkpoint-powertools-prod`

### Best Practices

1. **Always verify workspace** before running commands:
   ```bash
   terraform workspace show
   ```

2. **Match workspace and tfvars file**:
   ```bash
   # ✅ Correct
   terraform workspace select dev
   terraform apply -var-file="terraform.dev.tfvars"
   
   # ❌ Wrong - mismatched
   terraform workspace select dev
   terraform apply -var-file="terraform.prod.tfvars"
   ```

3. **Deploy in order**: dev → staging → prod

## Cost Optimization

### Layer Storage Costs

- Each layer version consumes storage space (~20-25MB total)
- Old versions can be cleaned up after successful deployments
- Use `reuse_existing_layers=true` to minimize layer creation

### Lambda Execution Costs

- **Memory**: 3GB recommended for large datasets
- **Duration**: Most executions < 5 minutes
- **Invocations**: Depends on event log volume

Monitor CloudWatch metrics to optimize memory and timeout settings.

### S3 Storage Costs

Use lifecycle policies to reduce storage costs:

- **Standard**: $0.023/GB/month
- **Glacier**: $0.004/GB/month (83% savings)
- **Deep Archive**: $0.00099/GB/month (96% savings)

## Terraform Utilities

### Validate Configuration

```bash
./bin/exec-in-devcontainer.sh terraform validate
```

### Format Configuration

```bash
./bin/exec-in-devcontainer.sh terraform fmt
```

### Show Current State

```bash
./bin/exec-in-devcontainer.sh terraform show
```

### Plan Changes

```bash
./bin/exec-in-devcontainer.sh terraform plan -var-file="terraform.prod.tfvars"
```

### Enable Debug Logging

```bash
export TF_LOG=DEBUG
./bin/exec-in-devcontainer.sh terraform apply
```

## Configuration Best Practices

### 1. Use Variable Files

Keep environment-specific configuration in separate tfvars files:

```hcl
# terraform.prod.tfvars
environment       = "prod"
source_bucket     = "submission-events-prod"
checkpoint_bucket = "submission-events-prod"
```

### 2. Never Commit Secrets

Use `.gitignore` to exclude sensitive files:

```
# .gitignore
terraform.tfvars
*.tfstate
*.tfstate.backup
.terraform/
```

### 3. Use Remote State

Store Terraform state in S3 with versioning enabled for recovery.

### 4. Document Configuration

Add comments to tfvars files explaining non-obvious settings:

```hcl
# Checkpoint key template must include {study} and {datatype} placeholders
checkpoint_key_template = "prod/checkpoints/{study}-{datatype}-events.parquet"

# Force layer update disabled for production stability
force_layer_update = false
```

### 5. Version Control Configuration

Commit to version control:
- `*.tf` files
- `terraform.tfvars.example`
- Environment-specific tfvars files (if no secrets)

Do not commit:
- `terraform.tfvars` (if contains secrets)
- `.terraform/` directory
- `*.tfstate` files

## Related Documentation

- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide
- [ENVIRONMENTS.md](./ENVIRONMENTS.md) - Environment management
- [EVENT-LOG-ARCHIVAL.md](./EVENT-LOG-ARCHIVAL.md) - S3 lifecycle management
- [README.md](../README.md) - Lambda function overview
