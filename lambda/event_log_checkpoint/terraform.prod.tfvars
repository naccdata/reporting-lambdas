# Production Environment Configuration
# Event Log Checkpoint Lambda

# Environment
environment = "prod"
log_level   = "INFO"

# S3 Configuration
source_bucket           = "submission-events"
checkpoint_bucket       = "submission-events" # Using same bucket for checkpoints
checkpoint_key_template = "prod/checkpoints/{study}/{datatype}/events.parquet"

# Lambda Configuration
lambda_timeout     = 900  # 15 minutes
lambda_memory_size = 3008 # 3GB
log_retention_days = 90   # Longer retention for production

# Layer Management
# IMPORTANT: For first deployment, set reuse_existing_layers = false
# After first deployment, change to true for faster deployments
reuse_existing_layers   = true  # Set to true after first deployment
use_external_layer_arns = false
force_layer_update      = false

# Monitoring
# REQUIRED: Add SNS topic ARN for production alerts
# alarm_sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:event-log-checkpoint-prod-alerts"
alarm_sns_topic_arn = ""

# Event Log Filtering
# Optional: filter to specific date range
# event_log_prefix = "logs/"

# S3 Lifecycle Management
# Production: Full archival strategy with long-term retention
manage_source_bucket_lifecycle     = true
enable_event_log_archival          = true
days_until_glacier_transition      = 90  # Archive to Glacier after 90 days
days_until_deep_archive_transition = 365 # Move to Deep Archive after 1 year
days_until_expiration              = 0   # Keep forever (compliance requirement)

# Tags
additional_tags = {
  Environment = "prod"
  Owner       = "data-engineering"
  CostCenter  = "analytics"
  Application = "event-log-processing"
  ManagedBy   = "terraform"
  Criticality = "high"
}
