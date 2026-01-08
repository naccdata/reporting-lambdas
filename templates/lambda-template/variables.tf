variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "lambda_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "lambda_package_path" {
  description = "Path to the Lambda deployment package"
  type        = string
}

variable "lambda_layers" {
  description = "List of Lambda layer ARNs"
  type        = list(string)
  default     = []
}

variable "input_bucket_name" {
  description = "Name of the S3 bucket for input data"
  type        = string
}

variable "input_bucket_arn" {
  description = "ARN of the S3 bucket for input data"
  type        = string
}

variable "output_bucket_name" {
  description = "Name of the S3 bucket for output data"
  type        = string
}

variable "output_bucket_arn" {
  description = "ARN of the S3 bucket for output data"
  type        = string
}

variable "output_prefix" {
  description = "S3 prefix for output files"
  type        = string
  default     = "processed-data/"
}

variable "timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 900
}

variable "memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 3008
}

variable "log_level" {
  description = "Log level for the Lambda function"
  type        = string
  default     = "INFO"
  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARNING, ERROR."
  }
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}

variable "schedule_expression" {
  description = "EventBridge schedule expression (e.g., 'rate(1 hour)' or 'cron(0 12 * * ? *)')"
  type        = string
  default     = ""
}