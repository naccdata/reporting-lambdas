# Staging Environment Configuration
# Event Log Checkpoint Lambda

# Environment
environment = "staging"
log_level   = "INFO"

# S3 Configuration
source_bucket     = "nacc-event-logs-staging"
checkpoint_bucket = "nacc-checkpoints-staging"
checkpoint_key    = "checkpoints/events.parquet"

# Lambda Configuration
lambda_timeout     = 900  # 15 minutes
lambda_memory_size = 3008 # 3GB
log_retention_days = 30   # Standard retention for staging

# Layer Management
# Reuse layers for faster deployments
reuse_existing_layers   = true
use_external_layer_arns = false
force_layer_update      = false

# Monitoring
# Add SNS topic ARN for staging alerts
# alarm_sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:event-log-checkpoint-staging-alerts"
alarm_sns_topic_arn = ""

# Event Log Filtering
# Optional: filter to specific date range
# event_log_prefix = "logs/"

# S3 Lifecycle Management
# Staging: Archive to Glacier, keep indefinitely
manage_source_bucket_lifecycle     = true
enable_event_log_archival          = true
days_until_glacier_transition      = 90 # Archive after 90 days
days_until_deep_archive_transition = 0  # Skip Deep Archive for staging
days_until_expiration              = 0  # Keep forever

# Tags
additional_tags = {
  Environment = "staging"
  Owner       = "data-engineering"
  CostCenter  = "analytics"
  Application = "event-log-processing"
  ManagedBy   = "terraform"
}
