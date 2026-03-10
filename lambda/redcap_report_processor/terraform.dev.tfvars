# Development Environment Configuration
# REDCap Report Processor Lambda

# Environment
environment = "dev"
log_level   = "DEBUG"

# S3 Configuration
s3_prefix               = "nacc-reporting/bronze-tables/redcap"
region                  = "us-west-2"

# Lambda Configuration
lambda_timeout     = 900  # 15 minutes
lambda_memory_size = 3008 # 3GB
log_retention_days = 7    # Shorter retention for dev

# Layer Management
# First deployment: create new layers
reuse_existing_layers   = false
use_external_layer_arns = false
force_layer_update      = false

# Tags
additional_tags = {
  Environment = "dev"
  Owner       = "data-engineering"
  CostCenter  = "analytics"
  Application = "redcap-report-processor"
  ManagedBy   = "terraform"
}
