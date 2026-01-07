# Variables for Event Log Checkpoint Lambda Infrastructure

# Required variables
variable "source_bucket" {
  description = "S3 bucket containing event log files"
  type        = string

  validation {
    condition     = length(var.source_bucket) > 0
    error_message = "Source bucket name cannot be empty."
  }
}

variable "checkpoint_bucket" {
  description = "S3 bucket for checkpoint parquet files"
  type        = string

  validation {
    condition     = length(var.checkpoint_bucket) > 0
    error_message = "Checkpoint bucket name cannot be empty."
  }
}

# Optional variables with defaults
variable "checkpoint_key" {
  description = "S3 key for checkpoint parquet file"
  type        = string
  default     = "checkpoints/events.parquet"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "log_level" {
  description = "Logging level for Lambda function"
  type        = string
  default     = "INFO"

  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL."
  }
}

# Layer management variables
variable "reuse_existing_layers" {
  description = "Whether to reuse existing Lambda layers if they exist (recommended for faster deployments)"
  type        = bool
  default     = true
}

variable "use_external_layer_arns" {
  description = "Whether to use externally provided layer ARNs instead of creating layers (useful for cross-project reuse)"
  type        = bool
  default     = false
}

variable "external_layer_arns" {
  description = "List of external layer ARNs to use when use_external_layer_arns is true. Must include: [powertools_arn, data_processing_arn]"
  type        = list(string)
  default     = []

  validation {
    condition = var.use_external_layer_arns ? length(var.external_layer_arns) >= 2 : true
    error_message = "When use_external_layer_arns is true, external_layer_arns must contain at least 2 ARNs (powertools and data_processing layers)."
  }

  validation {
    condition = var.use_external_layer_arns ? alltrue([
      for arn in var.external_layer_arns : can(regex("^arn:aws:lambda:[a-z0-9-]+:[0-9]+:layer:[a-zA-Z0-9-_]+:[0-9]+$", arn))
    ]) : true
    error_message = "All external layer ARNs must be valid Lambda layer ARNs."
  }
}

variable "force_layer_update" {
  description = "Force update of Lambda layers even if they exist (useful for development environments)"
  type        = bool
  default     = false
}

# Monitoring variables
variable "alarm_sns_topic_arn" {
  description = "SNS topic ARN for CloudWatch alarms (optional)"
  type        = string
  default     = ""

  validation {
    condition = var.alarm_sns_topic_arn == "" || can(regex("^arn:aws:sns:[a-z0-9-]+:[0-9]+:[a-zA-Z0-9-_]+$", var.alarm_sns_topic_arn))
    error_message = "SNS topic ARN must be a valid ARN or empty string."
  }
}

# Lambda configuration variables
variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 900 # 15 minutes

  validation {
    condition     = var.lambda_timeout >= 60 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 60 and 900 seconds."
  }
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 3008 # 3GB

  validation {
    condition     = var.lambda_memory_size >= 128 && var.lambda_memory_size <= 10240
    error_message = "Lambda memory size must be between 128 and 10240 MB."
  }
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30

  validation {
    condition = contains([
      1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653
    ], var.log_retention_days)
    error_message = "Log retention days must be one of the valid CloudWatch retention periods."
  }
}

# S3 prefix for event logs (optional)
variable "event_log_prefix" {
  description = "S3 prefix to filter event log files (optional)"
  type        = string
  default     = ""
}

# Tags
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}