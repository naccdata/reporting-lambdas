# Production Environment Configuration
# REDCap Report Processor Lambda

# Environment
environment = "prod"
log_level   = "INFO"

# S3 Configuration
s3_bucket               = "nacc-reporting"
s3_prefix               = "nacc-reporting/bronze-tables/redcap"
region                  = "us-west-2"

# Lambda Configuration
lambda_timeout     = 900  # 15 minutes
lambda_memory_size = 3008 # 3GB
log_retention_days = 30

# Layer Management
# First deployment: create new layers
reuse_existing_layers   = false
use_external_layer_arns = false
force_layer_update      = false

# Tags
additional_tags = {
  Environment = "prod"
  Owner       = "data-engineering"
  CostCenter  = "analytics"
  Application = "redcap-report-processor"
  ManagedBy   = "terraform"
}
