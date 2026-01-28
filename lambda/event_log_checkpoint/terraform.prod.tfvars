# Production Environment Configuration
# Event Log Checkpoint Lambda

# Environment
environment = "prod"
log_level   = "INFO"

# S3 Configuration
source_bucket     = "nacc-event-logs-prod"
checkpoint_bucket = "nacc-checkpoints-prod"
checkpoint_key    = "checkpoints/events.parquet"

# Lambda Configuration
lambda_timeout     = 900  # 15 minutes
lambda_memory_size = 3008 # 3GB
log_retention_days = 90   # Longer retention for production

# Layer Management
# Reuse layers for faster deployments
reuse_existing_layers   = true
use_external_layer_arns = false
force_layer_update      = false

# Monitoring
# REQUIRED: Add SNS topic ARN for production alerts
# alarm_sns_topic_arn = "arn:aws:sns:us-east-1:123456789012:event-log-checkpoint-prod-alerts"
alarm_sns_topic_arn = ""

# Event Log Filtering
# Optional: filter to specific date range
# event_log_prefix = "logs/"

# Tags
additional_tags = {
  Environment = "prod"
  Owner       = "data-engineering"
  CostCenter  = "analytics"
  Application = "event-log-processing"
  ManagedBy   = "terraform"
  Criticality = "high"
}
