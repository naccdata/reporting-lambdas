# Development Environment Configuration
# Event Log Checkpoint Lambda

# Environment
environment = "dev"
log_level   = "DEBUG"

# S3 Configuration
source_bucket           = "submission-events"
checkpoint_bucket       = "submission-events" # Using same bucket for checkpoints
checkpoint_key_template = "dev/checkpoints/{study}/{datatype}/events.parquet"

# Lambda Configuration
lambda_timeout     = 900  # 15 minutes
lambda_memory_size = 3008 # 3GB
log_retention_days = 7    # Shorter retention for dev

# Layer Management
# First deployment: create new layers
reuse_existing_layers   = false
use_external_layer_arns = false
force_layer_update      = false

# Monitoring
# No SNS alerts in dev (optional: add for testing)
alarm_sns_topic_arn = ""

# Event Log Filtering
# Filter to dev folder
event_log_prefix = "dev/"

# S3 Lifecycle Management
# Dev: Delete files after 30 days (no archival needed for dev)
manage_source_bucket_lifecycle     = true
enable_event_log_archival          = false # Skip archival, just delete
days_until_glacier_transition      = 90    # Not used when archival disabled
days_until_deep_archive_transition = 0     # Not used when archival disabled
days_until_expiration              = 30    # Delete after 30 days

# Tags
additional_tags = {
  Environment = "dev"
  Owner       = "data-engineering"
  CostCenter  = "analytics"
  Application = "event-log-processing"
  ManagedBy   = "terraform"
}
