#!/bin/bash
# Setup script for Terraform remote state backend
# This script creates SHARED infrastructure for ALL lambdas in the monorepo
# 
# Creates:
# - One S3 bucket for all Terraform state files
#
# Each lambda uses a different 'key' path within the bucket:
# - lambda/event-log-checkpoint/terraform.tfstate
# - lambda/another-lambda/terraform.tfstate
# - etc.
#
# This script only needs to be run ONCE for the entire monorepo.
#
# Note: DynamoDB state locking is intentionally omitted.
# Team coordination should be done via communication (Slack, etc.)

set -e

# Configuration
BUCKET_NAME="nacc-terraform-state"
REGION="us-east-1"

echo "Setting up SHARED Terraform remote state backend..."
echo "This infrastructure will be used by ALL lambdas in the monorepo"
echo ""
echo "Bucket: ${BUCKET_NAME}"
echo "Region: ${REGION}"
echo "State Locking: DISABLED (coordinate via team communication)"
echo ""

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS credentials not configured"
    exit 1
fi

echo "Creating S3 bucket for Terraform state..."
if aws s3 ls "s3://${BUCKET_NAME}" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3api create-bucket \
        --bucket "${BUCKET_NAME}" \
        --region "${REGION}" \
        --create-bucket-configuration LocationConstraint="${REGION}" 2>/dev/null || \
    aws s3api create-bucket \
        --bucket "${BUCKET_NAME}" \
        --region us-east-1
    
    echo "✓ S3 bucket created"
else
    echo "✓ S3 bucket already exists"
fi

echo "Enabling versioning on S3 bucket..."
aws s3api put-bucket-versioning \
    --bucket "${BUCKET_NAME}" \
    --versioning-configuration Status=Enabled
echo "✓ Versioning enabled"

echo "Enabling encryption on S3 bucket..."
aws s3api put-bucket-encryption \
    --bucket "${BUCKET_NAME}" \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }]
    }'
echo "✓ Encryption enabled"

echo "Blocking public access on S3 bucket..."
aws s3api put-public-access-block \
    --bucket "${BUCKET_NAME}" \
    --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
echo "✓ Public access blocked"

echo ""
echo "✅ Backend setup complete!"
echo ""
echo "This shared infrastructure can now be used by ALL lambdas in the monorepo."
echo ""
echo "⚠ Note: State locking is DISABLED"
echo "  - Coordinate terraform runs via team communication (Slack, etc.)"
echo "  - Avoid running terraform on the same lambda simultaneously"
echo ""
echo "Next steps for event-log-checkpoint lambda:"
echo "1. Uncomment the backend configuration in lambda/event_log_checkpoint/main.tf"
echo "2. Run: cd lambda/event_log_checkpoint && terraform init -migrate-state"
echo "3. Confirm state migration when prompted"
echo "4. Verify state is in S3: aws s3 ls s3://${BUCKET_NAME}/lambda/event-log-checkpoint/"
echo ""
echo "Backend configuration (already in main.tf):"
echo "  backend \"s3\" {"
echo "    bucket  = \"${BUCKET_NAME}\""
echo "    key     = \"lambda/event-log-checkpoint/terraform.tfstate\""
echo "    region  = \"${REGION}\""
echo "    encrypt = true"
echo "  }"
echo ""
echo "For other lambdas:"
echo "1. Configure backend in their main.tf with a unique key path:"
echo "   key = \"lambda/{lambda-name}/terraform.tfstate\""
echo "2. Run terraform init -migrate-state in each lambda directory"
echo ""
echo "State file organization:"
echo "  s3://${BUCKET_NAME}/"
echo "  ├── lambda/event-log-checkpoint/terraform.tfstate"
echo "  ├── lambda/another-lambda/terraform.tfstate"
echo "  └── (each lambda has its own state file)"
