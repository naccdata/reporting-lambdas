# Event Log Archival Strategy

## Overview

Event log JSON files accumulate in S3 over time. While the Lambda function processes them incrementally (only reading new files since the last checkpoint), the S3 LIST operation must scan all files, which can become a performance bottleneck as the file count grows.

This document describes the S3 lifecycle policy strategy for managing event log files cost-effectively while maintaining data availability.

## The Problem

### File Accumulation

The Lambda function:
1. Lists ALL event log files in the source bucket
2. Filters by timestamp to process only new files
3. Leaves original JSON files untouched

As files accumulate:
- **S3 LIST overhead**: Increases linearly with total file count
- **Processing overhead**: Stays constant (only processes new files)
- **Storage costs**: Increase with file count and retention period

### Why Not Delete?

Event log JSON files serve as:
- **Audit trail**: Historical record of all events
- **Disaster recovery**: Can rebuild checkpoint from scratch if needed
- **Debugging**: Investigate issues with specific events
- **Compliance**: May be required for regulatory purposes

## Solution: S3 Lifecycle Policies

Use S3 lifecycle policies to automatically transition files to cheaper storage tiers over time.

### Storage Tiers

| Tier | Cost (per GB/month) | Retrieval Time | Use Case |
|------|---------------------|----------------|----------|
| **S3 Standard** | $0.023 | Immediate | Active processing (recent files) |
| **Glacier** | $0.004 | 1-5 minutes | Occasional access (older files) |
| **Glacier Deep Archive** | $0.00099 | 12 hours | Long-term retention (archival) |

### Cost Savings Example

For 100,000 event files (~10 MB total):

| Strategy | Monthly Cost | Annual Cost |
|----------|--------------|-------------|
| All in S3 Standard | $0.23 | $2.76 |
| 90 days Standard, then Glacier | $0.08 | $0.96 |
| 90 days Standard, 1 year Glacier, then Deep Archive | $0.05 | $0.60 |

**Savings**: ~78% cost reduction with archival strategy

## Terraform Configuration

### Variables

The Terraform configuration includes these variables for lifecycle management:

```hcl
# Enable lifecycle policy management
manage_source_bucket_lifecycle = true  # Set to true to enable

# Archival configuration
enable_event_log_archival         = true  # Enable automatic archival
days_until_glacier_transition     = 90    # Move to Glacier after 90 days
days_until_deep_archive_transition = 365  # Move to Deep Archive after 1 year
days_until_expiration             = 0     # Permanently delete (0 = never)
```

### Environment-Specific Configuration

The lifecycle policy can be configured differently per environment using environment-specific tfvars files:

#### Development (`terraform.dev.tfvars`)

**Strategy**: Delete files after 30 days (no archival)

```hcl
manage_source_bucket_lifecycle     = true
enable_event_log_archival          = false  # Skip archival
days_until_expiration              = 30     # Delete after 30 days
```

**Rationale**: Dev environment doesn't need long-term retention. Quick cleanup reduces storage costs.

#### Staging (`terraform.staging.tfvars`)

**Strategy**: Archive to Glacier, keep indefinitely

```hcl
manage_source_bucket_lifecycle     = true
enable_event_log_archival          = true
days_until_glacier_transition      = 90   # Archive after 90 days
days_until_deep_archive_transition = 0    # Skip Deep Archive
days_until_expiration              = 0    # Keep forever
```

**Rationale**: Staging mirrors production behavior but skips Deep Archive for cost savings.

#### Production (`terraform.prod.tfvars`)

**Strategy**: Full archival with long-term retention

```hcl
manage_source_bucket_lifecycle     = true
enable_event_log_archival          = true
days_until_glacier_transition      = 90   # Archive after 90 days
days_until_deep_archive_transition = 365  # Deep Archive after 1 year
days_until_expiration              = 0    # Keep forever
```

**Rationale**: Production requires full audit trail and compliance retention.

### Lifecycle Policy

The policy creates two rules:

1. **Event log archival**: Transitions files through storage tiers
2. **Cleanup incomplete uploads**: Removes failed multipart uploads after 7 days

### Example Configurations

#### Conservative (Keep Forever)

Best for: Compliance requirements, unlimited retention

```hcl
days_until_glacier_transition     = 90   # Archive after 3 months
days_until_deep_archive_transition = 365  # Deep archive after 1 year
days_until_expiration             = 0    # Never delete
```

**Timeline**:
- Days 0-90: S3 Standard (active processing)
- Days 91-365: Glacier (occasional access)
- Days 366+: Deep Archive (long-term retention)

#### Moderate (7-Year Retention)

Best for: Regulatory compliance (e.g., HIPAA, SOX)

```hcl
days_until_glacier_transition     = 90    # Archive after 3 months
days_until_deep_archive_transition = 365   # Deep archive after 1 year
days_until_expiration             = 2555  # Delete after 7 years
```

**Timeline**:
- Days 0-90: S3 Standard
- Days 91-365: Glacier
- Days 366-2555: Deep Archive
- Day 2556: Permanently deleted

#### Aggressive (2-Year Retention)

Best for: Development/staging environments, cost optimization

```hcl
days_until_glacier_transition     = 90   # Archive after 3 months
days_until_deep_archive_transition = 0    # Skip Deep Archive
days_until_expiration             = 730  # Delete after 2 years
```

**Timeline**:
- Days 0-90: S3 Standard
- Days 91-730: Glacier
- Day 731: Permanently deleted

## Important Considerations

### S3 Minimum Storage Duration

AWS enforces minimum storage durations for lifecycle transitions:

- **Glacier**: Minimum 30 days in S3 Standard before transition
- **Deep Archive**: Minimum 180 days in S3 Standard before transition

The Terraform variables include validation to enforce these requirements.

### Retrieval Costs

Retrieving files from Glacier incurs costs:

- **Glacier**: $0.01 per GB + $0.0004 per request
- **Deep Archive**: $0.02 per GB + $0.0004 per request

For disaster recovery (rebuilding checkpoint from scratch), retrieval costs are typically minimal since:
- Event files are small (~1-10 KB each)
- Retrieval is rare (only for disaster recovery or debugging)

### Lambda Performance Impact

The lifecycle policy does NOT affect Lambda performance:

- Lambda lists files regardless of storage tier
- Only file retrieval is affected (slower for archived files)
- Since Lambda only processes NEW files, archived files are never retrieved

### Bucket Ownership

**IMPORTANT**: Only enable `manage_source_bucket_lifecycle = true` if this Terraform configuration should manage the source bucket's lifecycle policy.

If the source bucket is managed by another Terraform configuration or team:
- Set `manage_source_bucket_lifecycle = false`
- Coordinate lifecycle policy with bucket owner
- Avoid conflicting lifecycle rules

## Deployment

### Step 1: Update terraform.tfvars

```hcl
# Enable lifecycle management
manage_source_bucket_lifecycle = true

# Configure archival strategy
enable_event_log_archival         = true
days_until_glacier_transition     = 90
days_until_deep_archive_transition = 365
days_until_expiration             = 0
```

### Step 2: Plan and Apply

```bash
# Ensure container is running
./bin/start-devcontainer.sh

# Review changes
./bin/exec-in-devcontainer.sh terraform plan

# Apply lifecycle policy
./bin/exec-in-devcontainer.sh terraform apply
```

### Step 3: Verify

Check the lifecycle policy in AWS Console:
1. Navigate to S3 bucket
2. Go to "Management" tab
3. View "Lifecycle rules"
4. Verify rule is active

Or use AWS CLI:

```bash
aws s3api get-bucket-lifecycle-configuration --bucket your-event-logs-bucket
```

## Monitoring

### CloudWatch Metrics

Monitor these S3 metrics to track archival effectiveness:

- **NumberOfObjects**: Total file count (should stabilize with expiration)
- **BucketSizeBytes**: Total storage size
- **StorageClassAnalysis**: Distribution across storage tiers

### Cost Tracking

Use AWS Cost Explorer to track:
- S3 storage costs by storage class
- Retrieval costs (should be near zero)
- Overall cost trend (should decrease after archival)

## Disaster Recovery

### Rebuilding Checkpoint from Archived Files

If you need to rebuild the checkpoint from scratch:

1. **Initiate bulk retrieval** (Glacier):
   ```bash
   aws s3 cp s3://bucket/prefix/ ./local-copy/ --recursive --force-glacier-transfer
   ```

2. **Wait for retrieval** (1-5 minutes for Glacier, 12 hours for Deep Archive)

3. **Delete existing checkpoint**:
   ```bash
   aws s3 rm s3://checkpoint-bucket/checkpoints/events.parquet
   ```

4. **Run Lambda** to rebuild from all files

**Cost**: For 100,000 files (~10 MB total):
- Glacier retrieval: ~$0.10
- Deep Archive retrieval: ~$0.20

## Best Practices

1. **Start conservative**: Begin with longer retention periods, adjust based on usage
2. **Test retrieval**: Periodically test retrieving archived files to verify process
3. **Document policy**: Ensure team understands archival timeline and retrieval process
4. **Monitor costs**: Track S3 costs to verify savings from archival
5. **Coordinate with stakeholders**: Ensure retention policy meets compliance requirements

## FAQ

### Q: Will archival affect Lambda performance?

**A**: No. The Lambda lists all files regardless of storage tier, but only retrieves NEW files (which are always in S3 Standard). Archived files are never retrieved during normal operation.

### Q: Can I retrieve archived files if needed?

**A**: Yes. Archived files can be retrieved, but with delays:
- Glacier: 1-5 minutes
- Deep Archive: 12 hours

### Q: What if I need to rebuild the checkpoint?

**A**: Initiate bulk retrieval of archived files, wait for retrieval to complete, then delete the checkpoint and run the Lambda. The Lambda will rebuild from all available files.

### Q: Should I enable expiration?

**A**: Depends on your requirements:
- **Compliance**: May require specific retention periods (e.g., 7 years)
- **Cost optimization**: Expiration reduces long-term storage costs
- **Disaster recovery**: Longer retention provides more recovery options

### Q: What happens to files during transition?

**A**: Files remain accessible during transition. S3 handles the transition transparently, and the Lambda can still list and retrieve files (though retrieval may be slower for archived files).

## Related Documentation

- [AWS S3 Lifecycle Configuration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- [AWS S3 Storage Classes](https://aws.amazon.com/s3/storage-classes/)
- [Event Log Format Specification](../../../context/docs/event-log-format.md)
- [Lambda README](../README.md)
