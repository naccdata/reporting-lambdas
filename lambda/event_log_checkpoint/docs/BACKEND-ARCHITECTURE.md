# Terraform Backend Architecture

## Overview

This monorepo uses a **shared backend infrastructure** for all Lambda projects. One S3 bucket and one DynamoDB table serve all lambdas, with state isolation achieved through unique S3 key paths.

## Shared Infrastructure

### Created Once for Entire Monorepo

Run `backend-setup.sh` **once** to create:

1. **S3 Bucket**: `nacc-terraform-state`
   - Stores all Terraform state files
   - Versioning enabled (state history)
   - Encryption enabled (AES256)
   - Public access blocked

2. **DynamoDB Table**: `nacc-terraform-locks`
   - Provides state locking across all projects
   - Prevents concurrent modifications
   - Pay-per-request billing

## State File Organization

### Directory Structure

```
s3://nacc-terraform-state/
├── lambda/
│   ├── event-log-checkpoint/
│   │   └── terraform.tfstate
│   ├── another-lambda/
│   │   └── terraform.tfstate
│   └── third-lambda/
│       └── terraform.tfstate
├── terraform/
│   └── shared-infrastructure/
│       └── terraform.tfstate
└── workspaces/
    ├── dev/
    │   ├── lambda/event-log-checkpoint/terraform.tfstate
    │   └── lambda/another-lambda/terraform.tfstate
    ├── staging/
    │   └── ...
    └── prod/
        └── ...
```

### Key Path Convention

Each project uses a unique `key` parameter in its backend configuration:

| Project Type | Key Pattern | Example |
|--------------|-------------|---------|
| Lambda Functions | `lambda/{name}/terraform.tfstate` | `lambda/event-log-checkpoint/terraform.tfstate` |
| Shared Infrastructure | `terraform/{name}/terraform.tfstate` | `terraform/shared-vpc/terraform.tfstate` |
| Terraform Modules | `modules/{name}/terraform.tfstate` | `modules/lambda-monitoring/terraform.tfstate` |

## Backend Configuration Per Lambda

Each lambda's `main.tf` includes:

```hcl
terraform {
  backend "s3" {
    bucket         = "nacc-terraform-state"           # Shared bucket
    key            = "lambda/{lambda-name}/terraform.tfstate"  # Unique key
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "nacc-terraform-locks"           # Shared lock table
    
    workspace_key_prefix = "workspaces"               # For environments
  }
}
```

## Environment Separation with Workspaces

Terraform workspaces provide environment isolation:

```bash
# Create and switch to dev workspace
terraform workspace new dev
terraform workspace select dev

# State stored at: workspaces/dev/lambda/event-log-checkpoint/terraform.tfstate

# Create and switch to prod workspace
terraform workspace new prod
terraform workspace select prod

# State stored at: workspaces/prod/lambda/event-log-checkpoint/terraform.tfstate
```

### Workspace vs. Separate State Files

**Option 1: Workspaces** (Recommended for this project)
- ✅ Single backend configuration
- ✅ Easy to switch between environments
- ✅ Automatic state isolation
- ✅ Works with environment-specific tfvars files

**Option 2: Separate Keys**
- Different `key` for each environment
- More explicit but requires multiple backend configs
- Example: `lambda/event-log-checkpoint-dev/terraform.tfstate`

## State Locking

### How It Works

1. **Before Terraform operation**: Acquires lock in DynamoDB
2. **During operation**: Lock prevents other operations
3. **After operation**: Releases lock automatically

### Lock Information

DynamoDB table stores:
- Lock ID (unique identifier)
- Who acquired the lock (user/system)
- When lock was acquired
- Operation being performed

### Handling Lock Issues

If a lock gets stuck (rare):

```bash
# View lock info
aws dynamodb get-item \
  --table-name nacc-terraform-locks \
  --key '{"LockID":{"S":"nacc-terraform-state/lambda/event-log-checkpoint/terraform.tfstate"}}'

# Force unlock (use with caution!)
terraform force-unlock <lock-id>
```

## Adding New Lambdas

### Step 1: Configure Backend in Lambda's main.tf

```hcl
terraform {
  backend "s3" {
    bucket         = "nacc-terraform-state"
    key            = "lambda/new-lambda-name/terraform.tfstate"  # Unique key!
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "nacc-terraform-locks"
    workspace_key_prefix = "workspaces"
  }
}
```

### Step 2: Initialize Backend

```bash
cd lambda/new-lambda-name
terraform init
```

### Step 3: Create Workspaces (Optional)

```bash
terraform workspace new dev
terraform workspace new staging
terraform workspace new prod
```

## Migration from Local State

If you have existing local state files:

```bash
# 1. Add backend configuration to main.tf (commented out initially)

# 2. Uncomment backend configuration

# 3. Migrate state
terraform init -migrate-state

# 4. Confirm migration when prompted

# 5. Verify state in S3
aws s3 ls s3://nacc-terraform-state/lambda/your-lambda/

# 6. Delete local state file (after verification)
rm terraform.tfstate terraform.tfstate.backup
```

## State File Security

### Access Control

Recommended IAM policy for developers:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::nacc-terraform-state",
        "arn:aws:s3:::nacc-terraform-state/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:*:table/nacc-terraform-locks"
    }
  ]
}
```

### Encryption

- **At rest**: S3 server-side encryption (AES256)
- **In transit**: HTTPS/TLS for all S3 operations
- **Versioning**: Enabled for state history and recovery

## Backup and Recovery

### Automatic Backups

S3 versioning provides automatic state history:

```bash
# List all versions of a state file
aws s3api list-object-versions \
  --bucket nacc-terraform-state \
  --prefix lambda/event-log-checkpoint/terraform.tfstate

# Restore previous version
aws s3api get-object \
  --bucket nacc-terraform-state \
  --key lambda/event-log-checkpoint/terraform.tfstate \
  --version-id <version-id> \
  terraform.tfstate.restored
```

### Manual Backups

Before major changes:

```bash
# Download current state
aws s3 cp \
  s3://nacc-terraform-state/lambda/event-log-checkpoint/terraform.tfstate \
  backup-$(date +%Y%m%d-%H%M%S).tfstate
```

## Cost Considerations

### S3 Storage
- **State files**: Typically < 1MB per lambda
- **Versioning**: Keeps all historical versions
- **Cost**: ~$0.023 per GB/month (negligible for state files)

### DynamoDB
- **Pay-per-request**: Only charged when locks are acquired/released
- **Typical cost**: < $1/month for small teams

### Optimization
- Enable S3 lifecycle policies to delete old versions after 90 days
- Monitor DynamoDB usage (should be minimal)

## Troubleshooting

### State File Not Found

```bash
# Verify bucket exists
aws s3 ls s3://nacc-terraform-state/

# Verify key path
aws s3 ls s3://nacc-terraform-state/lambda/event-log-checkpoint/

# Check workspace
terraform workspace list
terraform workspace select <correct-workspace>
```

### Lock Timeout

```bash
# Check for stuck locks
aws dynamodb scan --table-name nacc-terraform-locks

# Force unlock if needed (after confirming no one else is running terraform)
terraform force-unlock <lock-id>
```

### Permission Denied

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://nacc-terraform-state/

# Test DynamoDB access
aws dynamodb describe-table --table-name nacc-terraform-locks
```

## Best Practices

1. **Never commit state files to Git**
   - Add `*.tfstate*` to `.gitignore`
   - Use remote backend exclusively

2. **Use workspaces for environments**
   - Keeps backend configuration simple
   - Automatic state isolation

3. **Unique key paths per project**
   - Prevents state file conflicts
   - Clear organization

4. **Regular state backups**
   - Before major infrastructure changes
   - S3 versioning provides automatic backups

5. **Monitor lock usage**
   - Investigate stuck locks promptly
   - Set up alerts for long-running locks

6. **Restrict state file access**
   - Use IAM policies to control access
   - Audit state file access regularly

## Related Documentation

- [ENVIRONMENTS.md](./ENVIRONMENTS.md) - Environment management guide
- [TERRAFORM.md](./TERRAFORM.md) - Terraform deployment guide
- [backend-setup.sh](./backend-setup.sh) - Backend setup script
