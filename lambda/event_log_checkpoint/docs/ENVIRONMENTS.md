# Environment Management Guide

This document describes how to manage multiple environments (dev, staging, prod) for the Event Log Checkpoint Lambda.

## Overview

The Lambda uses Terraform with environment-specific variable files to manage separate deployments for development, staging, and production environments.

## Environment Configuration Files

Each environment has its own `.tfvars` file:

- `terraform.dev.tfvars` - Development environment
- `terraform.staging.tfvars` - Staging environment  
- `terraform.prod.tfvars` - Production environment

## Environment Differences

### Development (dev)

**Purpose:** Active development and testing

**Configuration:**

- Log level: `DEBUG` (verbose logging)
- Log retention: 7 days (cost optimization)
- S3 buckets: `nacc-event-logs-dev`, `nacc-checkpoints-dev`
- Alerts: Optional (can be disabled)
- Resource naming: `event-log-checkpoint-dev`

**Use cases:**

- Testing new features
- Debugging issues
- Experimenting with configurations
- Integration testing

### Staging (staging)

**Purpose:** Pre-production validation

**Configuration:**

- Log level: `INFO` (standard logging)
- Log retention: 30 days (standard retention)
- S3 buckets: `nacc-event-logs-staging`, `nacc-checkpoints-staging`
- Alerts: Recommended (test alert delivery)
- Resource naming: `event-log-checkpoint-staging`

**Use cases:**

- Final validation before production
- Performance testing with production-like data
- Testing deployment procedures
- Validating monitoring and alerts

### Production (prod)

**Purpose:** Live production workloads

**Configuration:**

- Log level: `INFO` (standard logging)
- Log retention: 90 days (compliance/audit)
- S3 buckets: `nacc-event-logs-prod`, `nacc-checkpoints-prod`
- Alerts: **Required** (must configure SNS topic)
- Resource naming: `event-log-checkpoint-prod`
- Additional tags: `Criticality = "high"`

**Use cases:**

- Production data processing
- Business-critical operations

## Deployment Workflow

### Initial Setup

1. **Ensure dev container is running:**

   ```bash
   ./bin/start-devcontainer.sh
   ```

2. **Build Lambda packages** (required before first deployment):

   ```bash
   ./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::
   ```

3. **Initialize Terraform** (one-time per environment):

   ```bash
   cd lambda/event_log_checkpoint
   ./bin/exec-in-devcontainer.sh terraform init
   ```

### Deploy to Development

```bash
cd lambda/event_log_checkpoint

# Plan deployment
./bin/exec-in-devcontainer.sh terraform plan -var-file=terraform.dev.tfvars

# Apply deployment
./bin/exec-in-devcontainer.sh terraform apply -var-file=terraform.dev.tfvars
```

### Deploy to Staging

```bash
cd lambda/event_log_checkpoint

# Plan deployment
./bin/exec-in-devcontainer.sh terraform plan -var-file=terraform.staging.tfvars

# Apply deployment
./bin/exec-in-devcontainer.sh terraform apply -var-file=terraform.staging.tfvars
```

### Deploy to Production

```bash
cd lambda/event_log_checkpoint

# Plan deployment (review carefully!)
./bin/exec-in-devcontainer.sh terraform plan -var-file=terraform.prod.tfvars

# Apply deployment (requires approval)
./bin/exec-in-devcontainer.sh terraform apply -var-file=terraform.prod.tfvars
```

## Function-Only Updates

When only Lambda code changes (no infrastructure changes), you can deploy faster:

```bash
# Rebuild Lambda package
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:lambda

# Deploy function only (dev example)
cd lambda/event_log_checkpoint
./bin/exec-in-devcontainer.sh terraform apply -var-file=terraform.dev.tfvars -target=aws_lambda_function.event_log_checkpoint
```

## Layer Updates

When dependencies change (Powertools, Pydantic, Polars):

```bash
# Rebuild layers
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:powertools
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:data_processing

# Deploy with layer updates (dev example)
cd lambda/event_log_checkpoint
./bin/exec-in-devcontainer.sh terraform apply -var-file=terraform.dev.tfvars -var='force_layer_update=true'
```

## Resource Naming Convention

All resources include the environment suffix to prevent conflicts:

| Resource Type | Naming Pattern | Example (dev) |
|--------------|----------------|---------------|
| Lambda Function | `event-log-checkpoint-{env}` | `event-log-checkpoint-dev` |
| IAM Role | `event-log-checkpoint-lambda-role-{env}` | `event-log-checkpoint-lambda-role-dev` |
| IAM Policy | `event-log-checkpoint-s3-policy-{env}` | `event-log-checkpoint-s3-policy-dev` |
| CloudWatch Log Group | `/aws/lambda/event-log-checkpoint-{env}` | `/aws/lambda/event-log-checkpoint-dev` |
| Lambda Layer (Powertools) | `event-log-checkpoint-powertools-{env}` | `event-log-checkpoint-powertools-dev` |
| Lambda Layer (Data Processing) | `event-log-checkpoint-data-processing-{env}` | `event-log-checkpoint-data-processing-dev` |
| CloudWatch Alarm (Errors) | `event-log-checkpoint-errors-{env}` | `event-log-checkpoint-errors-dev` |
| CloudWatch Alarm (Duration) | `event-log-checkpoint-duration-{env}` | `event-log-checkpoint-duration-dev` |

## State Management

### Current Setup (Local State)

Currently, Terraform state is stored locally in `terraform.tfstate`. This works for single-user development but has limitations:

- No state locking (risk of concurrent modifications)
- No state sharing across team members
- No state backup/recovery
- State files can be accidentally committed to Git

### Recommended Setup (Remote State)

For production use, configure S3 backend for remote state management. See the commented backend configuration in `main.tf`:

```hcl
backend "s3" {
  bucket         = "nacc-terraform-state"
  key            = "lambda/event-log-checkpoint/terraform.tfstate"
  region         = "us-east-1"
  encrypt        = true
  dynamodb_table = "nacc-terraform-locks"
  
  workspace_key_prefix = "workspaces"
}
```

**Setup steps:**

1. Create S3 bucket for state storage
2. Create DynamoDB table for state locking
3. Uncomment backend configuration in `main.tf`
4. Run `terraform init -migrate-state` to migrate existing state

## Environment Variables

Each environment sets these Lambda environment variables:

| Variable | Dev | Staging | Prod |
|----------|-----|---------|------|
| `SOURCE_BUCKET` | `nacc-event-logs-dev` | `nacc-event-logs-staging` | `nacc-event-logs-prod` |
| `CHECKPOINT_BUCKET` | `nacc-checkpoints-dev` | `nacc-checkpoints-staging` | `nacc-checkpoints-prod` |
| `CHECKPOINT_KEY` | `checkpoints/events.parquet` | `checkpoints/events.parquet` | `checkpoints/events.parquet` |
| `LOG_LEVEL` | `DEBUG` | `INFO` | `INFO` |
| `ENVIRONMENT` | `dev` | `staging` | `prod` |
| `POWERTOOLS_SERVICE_NAME` | `event-log-checkpoint-dev` | `event-log-checkpoint-staging` | `event-log-checkpoint-prod` |

## Monitoring Configuration

### Development

- CloudWatch alarms created but no SNS notifications
- Useful for testing alarm thresholds
- Can add SNS topic for testing alert delivery

### Staging

- CloudWatch alarms with optional SNS notifications
- Recommended to configure alerts to test notification flow
- Validates monitoring setup before production

### Production

- CloudWatch alarms with **required** SNS notifications
- Must configure `alarm_sns_topic_arn` in `terraform.prod.tfvars`
- Critical for incident response

## Best Practices

### Development Environment

1. Use DEBUG logging for troubleshooting
2. Test with realistic data volumes
3. Experiment freely - it's safe to break things
4. Keep costs low with shorter log retention

### Staging Environment

1. Mirror production configuration as closely as possible
2. Test deployment procedures before production
3. Validate monitoring and alerting
4. Use production-like data volumes for performance testing

### Production Environment

1. **Never deploy directly** - always deploy to staging first
2. Review Terraform plan carefully before applying
3. Configure SNS alerts before deployment
4. Document all changes in CHANGELOG
5. Have rollback plan ready
6. Deploy during maintenance windows when possible

## Troubleshooting

### Wrong Environment Deployed

If you accidentally deploy to the wrong environment:

```bash
# Check current resources
./bin/exec-in-devcontainer.sh terraform show

# Destroy incorrect deployment
./bin/exec-in-devcontainer.sh terraform destroy -var-file=terraform.{wrong-env}.tfvars

# Deploy to correct environment
./bin/exec-in-devcontainer.sh terraform apply -var-file=terraform.{correct-env}.tfvars
```

### State File Conflicts

If you get state locking errors:

```bash
# Force unlock (use with caution!)
./bin/exec-in-devcontainer.sh terraform force-unlock <lock-id>
```

### Layer Version Conflicts

If layers aren't updating:

```bash
# Force layer update
./bin/exec-in-devcontainer.sh terraform apply -var-file=terraform.dev.tfvars -var='force_layer_update=true'
```

## Migration Path

### From Single Environment to Multi-Environment

If you have an existing deployment without environment separation:

1. **Backup existing state:**

   ```bash
   cp terraform.tfstate terraform.tfstate.backup
   ```

2. **Choose target environment** (usually dev for existing deployments)

3. **Update resource names** to include environment suffix

4. **Import existing resources:**

   ```bash
   ./bin/exec-in-devcontainer.sh terraform import -var-file=terraform.dev.tfvars \
     aws_lambda_function.event_log_checkpoint event-log-checkpoint-dev
   ```

5. **Verify plan shows no changes:**

   ```bash
   ./bin/exec-in-devcontainer.sh terraform plan -var-file=terraform.dev.tfvars
   ```

## Next Steps

After setting up environment separation:

1. ✅ Configure remote state backend (S3 + DynamoDB)
2. ✅ Set up SNS topics for alerts
3. ✅ Create deployment runbook
4. ✅ Implement Lambda versioning and aliases
5. ✅ Set up CI/CD pipeline for automated deployments

## Related Documentation

- [TERRAFORM.md](./TERRAFORM.md) - Terraform deployment guide
- [README.md](./README.md) - Lambda overview
- [PRODUCTION-READINESS.md](./PRODUCTION-READINESS.md) - Production readiness checklist
