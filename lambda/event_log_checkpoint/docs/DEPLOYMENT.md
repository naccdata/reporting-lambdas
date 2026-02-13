# Deployment Guide

This guide covers deploying the Event Log Checkpoint Lambda function to AWS. It assumes Terraform configuration is already set up (see [TERRAFORM.md](./TERRAFORM.md) for configuration details).

## Prerequisites

Before deploying, ensure you have:

1. **Dev container running**: `./bin/start-devcontainer.sh`
2. **AWS credentials configured**: `aws configure` (in dev container)
3. **Terraform initialized**: `terraform init` (in lambda/event_log_checkpoint directory)
4. **S3 buckets created**: Source and checkpoint buckets must exist

## Understanding Workspaces

This Lambda uses **Terraform workspaces** to manage multiple environments with isolated state.

### Available Workspaces

- **dev** - Development environment
- **staging** - Staging environment  
- **prod** - Production environment

### Check Current Workspace

Always verify which workspace you're in before deploying:

```bash
cd lambda/event_log_checkpoint
terraform workspace show
```

### Switch Workspaces

```bash
# Switch to dev
terraform workspace select dev

# Switch to staging
terraform workspace select staging

# Switch to prod
terraform workspace select prod
```

## Quick Deployment

For most deployments, follow these steps:

```bash
# 1. Ensure dev container is running
./bin/start-devcontainer.sh

# 2. Navigate to lambda directory
cd lambda/event_log_checkpoint

# 3. Select workspace
terraform workspace select dev  # or staging, or prod

# 4. Update dependencies (optional, skip if not needed)
./bin/exec-in-devcontainer.sh pants generate-lockfiles

# 5. Run code quality checks
./bin/exec-in-devcontainer.sh pants fix ::
./bin/exec-in-devcontainer.sh pants lint ::
./bin/exec-in-devcontainer.sh pants check ::

# 6. Run tests
./bin/exec-in-devcontainer.sh pants test lambda/event_log_checkpoint/test/python::

# 7. Build Lambda packages
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::

# 8. Deploy with Terraform
terraform apply -var-file="terraform.dev.tfvars"  # Match workspace!
```

## Understanding Deployment Options

Deployments have two dimensions:

1. **Environment**: Which environment to deploy to (dev/staging/prod)
2. **Deployment type**: What to deploy (full, code-only, layers, etc.)

These are combined using Terraform command-line options:

```bash
# Environment selection (choose one)
-var-file="terraform.dev.tfvars"      # Deploy to dev
-var-file="terraform.staging.tfvars"  # Deploy to staging
-var-file="terraform.prod.tfvars"     # Deploy to production

# Deployment type options (optional, can combine)
-var="force_layer_update=true"        # Force new layer versions
-target=aws_lambda_function.event_log_checkpoint  # Deploy only function
```

**Examples of combining options**:

```bash
# Deploy to dev with forced layer update
terraform apply -var-file="terraform.dev.tfvars" -var="force_layer_update=true"

# Deploy only function to staging
terraform apply -var-file="terraform.staging.tfvars" -target=aws_lambda_function.event_log_checkpoint

# Deploy to production (uses defaults from prod tfvars)
terraform apply -var-file="terraform.prod.tfvars"
```

## Deployment Workflows by Environment

### Development Environment

Fast iteration with automatic layer reuse:

```bash
# Build packages
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::

# Deploy to dev
cd lambda/event_log_checkpoint
terraform workspace select dev
terraform apply -var-file="terraform.dev.tfvars"
```

### Staging Environment

Test with production-like configuration:

```bash
# Build packages
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::

# Deploy to staging
cd lambda/event_log_checkpoint
terraform workspace select staging
terraform apply -var-file="terraform.staging.tfvars"
```

### Production Environment

Deploy with specific layer versions for stability:

```bash
# Build packages
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::

# Deploy to production
cd lambda/event_log_checkpoint
terraform workspace select prod
terraform apply -var-file="terraform.prod.tfvars"
```

**Important**: Always match the workspace with the tfvars file!

**Note**: For first-time deployment to a new environment (staging or prod), the tfvars files are pre-configured with `reuse_existing_layers = false`. After the first successful deployment, you can change this to `true` in the tfvars file for faster subsequent deployments.

## Deployment Scenarios

### Scenario 1: Code-Only Changes

When you've only changed Lambda function code (no dependency updates).

**Any environment**:

```bash
# 1. Build only function package
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:lambda

# 2. Deploy only function to desired environment
cd lambda/event_log_checkpoint
./bin/exec-in-devcontainer.sh terraform apply \
  -var-file="terraform.{env}.tfvars" \
  -target=aws_lambda_function.event_log_checkpoint
```

**Examples**:

```bash
# Deploy code-only to dev
terraform apply -var-file="terraform.dev.tfvars" -target=aws_lambda_function.event_log_checkpoint

# Deploy code-only to production
terraform apply -var-file="terraform.prod.tfvars" -target=aws_lambda_function.event_log_checkpoint
```

**Deployment time**: ~30-45 seconds

### Scenario 2: Dependency Updates

When you've updated Python dependencies and need new layer versions.

**Any environment**:

```bash
# 1. Update lockfiles
./bin/exec-in-devcontainer.sh pants generate-lockfiles

# 2. Run all checks
./bin/exec-in-devcontainer.sh pants fix ::
./bin/exec-in-devcontainer.sh pants lint ::
./bin/exec-in-devcontainer.sh pants check ::
./bin/exec-in-devcontainer.sh pants test ::

# 3. Build all packages (function + layers)
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::

# 4. Deploy to desired environment
# Terraform will automatically detect changed layer zip files via source_code_hash
cd lambda/event_log_checkpoint
./bin/exec-in-devcontainer.sh terraform apply -var-file="terraform.{env}.tfvars"
```

**Examples**:

```bash
# Deploy with dependency updates to dev
terraform apply -var-file="terraform.dev.tfvars"

# Deploy with dependency updates to staging
terraform apply -var-file="terraform.staging.tfvars"

# Deploy with dependency updates to production
terraform apply -var-file="terraform.prod.tfvars"
```

**Note**: Terraform automatically detects changes to layer zip files using `source_code_hash`. You only need `force_layer_update=true` if you want to force a new layer version when reusing existing layers without content changes (rare).

**Deployment time**: ~90 seconds

### Scenario 3: Force Layer Update (Rare)

When you need to force new layer versions without content changes (e.g., testing layer deployment).

**Any environment**:

```bash
# 1. Build layer packages
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:powertools
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:data_processing

# 2. Deploy with force update to desired environment
cd lambda/event_log_checkpoint
./bin/exec-in-devcontainer.sh terraform apply \
  -var-file="terraform.{env}.tfvars" \
  -var="force_layer_update=true"
```

**Examples**:

```bash
# Force layer update in dev
terraform apply -var-file="terraform.dev.tfvars" -var="force_layer_update=true"

# Force layer update in production
terraform apply -var-file="terraform.prod.tfvars" -var="force_layer_update=true"
```

**Note**: This is rarely needed. Terraform automatically detects layer content changes via `source_code_hash`. Use this only when you need to force a new layer version for testing or troubleshooting.

**Deployment time**: ~60-90 seconds

### Scenario 4: Full Deployment (Default)

When deploying everything with default layer behavior (reuse existing layers).

**Any environment**:

```bash
# 1. Build all packages
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::

# 2. Deploy to desired environment
cd lambda/event_log_checkpoint
./bin/exec-in-devcontainer.sh terraform apply -var-file="terraform.{env}.tfvars"
```

**Examples**:

```bash
# Full deployment to dev
terraform apply -var-file="terraform.dev.tfvars"

# Full deployment to staging
terraform apply -var-file="terraform.staging.tfvars"

# Full deployment to production
terraform apply -var-file="terraform.prod.tfvars"
```

**Deployment time**: ~60 seconds

## Pre-Deployment Checklist

Before deploying to production, verify:

- [ ] **Correct workspace selected**: `terraform workspace show`
- [ ] All tests pass: `pants test lambda/event_log_checkpoint/test/python::`
- [ ] Code quality checks pass: `pants fix lint check ::`
- [ ] Terraform plan reviewed: `terraform plan -var-file="terraform.{env}.tfvars"`
- [ ] Environment variables configured correctly in tfvars file
- [ ] Workspace and tfvars file match (e.g., prod workspace + terraform.prod.tfvars)
- [ ] S3 buckets exist and are accessible
- [ ] AWS credentials have required permissions
- [ ] Changes documented in CHANGELOG.md
- [ ] Deployment tested in staging environment

## Post-Deployment Verification

After deployment, verify the Lambda is working:

### 1. Check Terraform Outputs

```bash
./bin/exec-in-devcontainer.sh terraform output
```

Verify:
- Lambda function ARN
- Layer versions
- CloudWatch log group name

### 2. Test Lambda Invocation

Invoke the Lambda manually to test:

```bash
aws lambda invoke \
  --function-name event-log-checkpoint-{environment} \
  --payload '{}' \
  response.json

cat response.json
```

### 3. Check CloudWatch Logs

View recent logs:

```bash
aws logs tail /aws/lambda/event-log-checkpoint-{environment} --follow
```

### 4. Verify CloudWatch Alarms

Check alarm status:

```bash
aws cloudwatch describe-alarms \
  --alarm-names event-log-checkpoint-{environment}-errors \
               event-log-checkpoint-{environment}-duration
```

### 5. Monitor Metrics

Check Lambda metrics in CloudWatch console:
- Invocations
- Duration
- Errors
- Throttles

## Rollback Procedures

If deployment causes issues, rollback using one of these methods:

### Method 1: Revert to Previous Lambda Version

```bash
# 1. List Lambda versions
aws lambda list-versions-by-function \
  --function-name event-log-checkpoint-{environment}

# 2. Update alias to previous version
aws lambda update-alias \
  --function-name event-log-checkpoint-{environment} \
  --name {environment} \
  --function-version {previous-version}
```

### Method 2: Redeploy Previous Code

```bash
# 1. Checkout previous commit
git checkout {previous-commit}

# 2. Build packages
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::

# 3. Deploy
cd lambda/event_log_checkpoint
./bin/exec-in-devcontainer.sh terraform apply
```

### Method 3: Terraform State Rollback

```bash
# 1. List Terraform state versions (if using S3 backend with versioning)
aws s3api list-object-versions \
  --bucket terraform-state-bucket \
  --prefix lambda/event-log-checkpoint/terraform.tfstate

# 2. Restore previous state version
aws s3api get-object \
  --bucket terraform-state-bucket \
  --key lambda/event-log-checkpoint/terraform.tfstate \
  --version-id {previous-version-id} \
  terraform.tfstate

# 3. Apply previous state
./bin/exec-in-devcontainer.sh terraform apply
```

## Deployment Time Optimization

| Deployment Type          | Time    | When to Use                           |
|--------------------------|---------|---------------------------------------|
| Function-only update     | ~30s    | Code changes only                     |
| Layer reuse              | ~60s    | Most deployments                      |
| Force layer update       | ~90s    | Dependency updates                    |
| External layer ARNs      | ~30s    | Production with pinned layers         |

## Troubleshooting Deployments

### Build Failures

**Issue**: Pants build fails

**Solutions**:
1. Check Python syntax errors: `pants check ::`
2. Verify dependencies are compatible: `pants generate-lockfiles`
3. Clear Pants cache: `rm -rf .pants.d`

### Terraform Errors

**Issue**: Terraform apply fails

**Solutions**:
1. Validate configuration: `terraform validate`
2. Check AWS credentials: `aws sts get-caller-identity`
3. Review Terraform plan: `terraform plan`
4. Enable debug logging: `export TF_LOG=DEBUG`

### Permission Errors

**Issue**: AccessDeniedException during deployment

**Solutions**:
1. Verify AWS credentials are configured
2. Check IAM permissions for Lambda, IAM, CloudWatch, S3
3. Ensure S3 buckets exist and are accessible

### Layer Size Errors

**Issue**: Layer exceeds 250MB unzipped size limit

**Solutions**:
1. Review layer dependencies
2. Remove unnecessary packages
3. Split into multiple layers if needed

### Missing Build Artifacts

**Issue**: Terraform can't find zip files

**Solutions**:
1. Ensure Pants build completed: `pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::`
2. Check dist directory exists: `ls -la dist/lambda/event_log_checkpoint/src/python/checkpoint_lambda/`
3. Verify file paths in Terraform configuration

## Multi-Environment Strategy

### Using Variable Files

Each environment has its own tfvars file:

```bash
# Development
./bin/exec-in-devcontainer.sh terraform apply -var-file="terraform.dev.tfvars"

# Staging
./bin/exec-in-devcontainer.sh terraform apply -var-file="terraform.staging.tfvars"

# Production
./bin/exec-in-devcontainer.sh terraform apply -var-file="terraform.prod.tfvars"
```

### Using Terraform Workspaces

Alternative approach using workspaces:

```bash
# Create workspaces (one-time setup)
./bin/exec-in-devcontainer.sh terraform workspace new dev
./bin/exec-in-devcontainer.sh terraform workspace new staging
./bin/exec-in-devcontainer.sh terraform workspace new prod

# Deploy to specific workspace
./bin/exec-in-devcontainer.sh terraform workspace select staging
./bin/exec-in-devcontainer.sh terraform apply
```

## Deployment Best Practices

### 1. Always Test Before Production

Deploy to dev → staging → production:

```bash
# Deploy to dev
./bin/exec-in-devcontainer.sh terraform apply -var-file="terraform.dev.tfvars"

# Test in dev, then deploy to staging
./bin/exec-in-devcontainer.sh terraform apply -var-file="terraform.staging.tfvars"

# Test in staging, then deploy to production
./bin/exec-in-devcontainer.sh terraform apply -var-file="terraform.prod.tfvars"
```

### 2. Review Terraform Plan

Always review the plan before applying:

```bash
./bin/exec-in-devcontainer.sh terraform plan -var-file="terraform.prod.tfvars"
```

### 3. Use Layer Reuse in Production

For production stability, use external layer ARNs or layer reuse:

```hcl
# In terraform.prod.tfvars
reuse_existing_layers = true
```

### 4. Document Deployments

Update CHANGELOG.md with:
- What changed
- Lambda version deployed to each environment
- Deployment date and deployer

### 5. Monitor After Deployment

Watch CloudWatch logs and metrics for 15-30 minutes after deployment to catch issues early.

## Cleanup

### Remove Lambda Function

```bash
cd lambda/event_log_checkpoint
./bin/exec-in-devcontainer.sh terraform destroy
```

**Note**: This preserves S3 buckets and their contents.

### Remove Specific Resources

```bash
# Remove only Lambda function
./bin/exec-in-devcontainer.sh terraform destroy -target=aws_lambda_function.event_log_checkpoint

# Remove only layers
./bin/exec-in-devcontainer.sh terraform destroy -target=aws_lambda_layer_version.powertools
./bin/exec-in-devcontainer.sh terraform destroy -target=aws_lambda_layer_version.data_processing
```

### Clean Up Old Layer Versions

Old layer versions consume storage. Clean them up periodically:

```bash
# List layer versions
aws lambda list-layer-versions --layer-name event-log-checkpoint-powertools-{environment}

# Delete old versions (keep latest 2-3)
aws lambda delete-layer-version \
  --layer-name event-log-checkpoint-powertools-{environment} \
  --version-number {old-version}
```

## Related Documentation

- [TERRAFORM.md](./TERRAFORM.md) - Terraform configuration guide
- [ENVIRONMENTS.md](./ENVIRONMENTS.md) - Environment management
- [PRODUCTION-READINESS.md](./PRODUCTION-READINESS.md) - Production readiness checklist
- [README.md](../README.md) - Lambda function overview
