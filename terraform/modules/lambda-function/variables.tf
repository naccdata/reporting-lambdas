# Variables for Lambda Function Module

# Required Variables
variable "function_name" {
  description = "Name of the Lambda function"
  type        = string

  validation {
    condition     = length(var.function_name) > 0 && length(var.function_name) <= 64
    error_message = "Function name must be between 1 and 64 characters."
  }
}

variable "execution_role_arn" {
  description = "ARN of the IAM role for Lambda execution"
  type        = string

  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]+:role/.+$", var.execution_role_arn))
    error_message = "Execution role ARN must be a valid IAM role ARN."
  }
}

variable "package_path" {
  description = "Path to the Lambda deployment package (zip file)"
  type        = string

  validation {
    condition     = can(regex("\\.(zip|jar)$", var.package_path))
    error_message = "Package path must point to a .zip or .jar file."
  }
}

# Lambda Configuration
variable "handler" {
  description = "Lambda function handler"
  type        = string
  default     = "lambda_function.lambda_handler"
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.12"

  validation {
    condition = contains([
      "python3.8", "python3.9", "python3.10", "python3.11", "python3.12",
      "nodejs18.x", "nodejs20.x",
      "java8", "java8.al2", "java11", "java17", "java21",
      "dotnet6", "dotnet8",
      "go1.x",
      "ruby3.2", "ruby3.3",
      "provided", "provided.al2", "provided.al2023"
    ], var.runtime)
    error_message = "Runtime must be a valid Lambda runtime."
  }
}

variable "timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 900

  validation {
    condition     = var.timeout >= 1 && var.timeout <= 900
    error_message = "Timeout must be between 1 and 900 seconds."
  }
}

variable "memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 3008

  validation {
    condition     = var.memory_size >= 128 && var.memory_size <= 10240
    error_message = "Memory size must be between 128 and 10240 MB."
  }
}

variable "architectures" {
  description = "Instruction set architecture for Lambda function"
  type        = list(string)
  default     = ["x86_64"]

  validation {
    condition = alltrue([
      for arch in var.architectures : contains(["x86_64", "arm64"], arch)
    ])
    error_message = "Architectures must be either x86_64 or arm64."
  }
}

variable "reserved_concurrency" {
  description = "Reserved concurrency for the Lambda function (-1 for unreserved)"
  type        = number
  default     = -1

  validation {
    condition     = var.reserved_concurrency >= -1
    error_message = "Reserved concurrency must be -1 (unreserved) or a positive number."
  }
}

# Code and Layers
variable "source_code_hash" {
  description = "Base64-encoded SHA256 hash of the package file (optional, will be computed if not provided)"
  type        = string
  default     = ""
}

variable "layer_arns" {
  description = "List of Lambda layer ARNs to attach to the function"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for arn in var.layer_arns : can(regex("^arn:aws:lambda:[a-z0-9-]+:[0-9]+:layer:[a-zA-Z0-9-_]+:[0-9]+$", arn))
    ])
    error_message = "All layer ARNs must be valid Lambda layer ARNs."
  }
}

# Environment and Configuration
variable "environment_variables" {
  description = "Environment variables for the Lambda function"
  type        = map(string)
  default     = {}
}

variable "enable_xray" {
  description = "Whether to enable X-Ray tracing"
  type        = bool
  default     = true
}

variable "dead_letter_queue_arn" {
  description = "ARN of the dead letter queue (SQS or SNS)"
  type        = string
  default     = ""

  validation {
    condition     = var.dead_letter_queue_arn == "" || can(regex("^arn:aws:(sqs|sns):[a-z0-9-]+:[0-9]+:.+$", var.dead_letter_queue_arn))
    error_message = "Dead letter queue ARN must be empty or a valid SQS/SNS ARN."
  }
}

# VPC Configuration
variable "vpc_subnet_ids" {
  description = "List of VPC subnet IDs for Lambda function"
  type        = list(string)
  default     = []
}

variable "vpc_security_group_ids" {
  description = "List of VPC security group IDs for Lambda function"
  type        = list(string)
  default     = []
}

# Versioning and Aliases
variable "create_alias" {
  description = "Whether to create a Lambda alias"
  type        = bool
  default     = false
}

variable "alias_name" {
  description = "Name of the Lambda alias"
  type        = string
  default     = "live"
}

variable "alias_function_version" {
  description = "Lambda function version for the alias"
  type        = string
  default     = "$LATEST"
}

variable "alias_routing_config" {
  description = "Routing configuration for the alias (for blue/green deployments)"
  type        = map(number)
  default     = {}
}

# Scheduling
variable "schedule_expression" {
  description = "EventBridge schedule expression (e.g., 'rate(5 minutes)' or 'cron(0 12 * * ? *)')"
  type        = string
  default     = ""

  validation {
    condition     = var.schedule_expression == "" || can(regex("^(rate\\(.+\\)|cron\\(.+\\))$", var.schedule_expression))
    error_message = "Schedule expression must be empty or a valid rate() or cron() expression."
  }
}

variable "schedule_enabled" {
  description = "Whether the schedule is enabled"
  type        = bool
  default     = true
}

variable "schedule_input" {
  description = "JSON input for scheduled Lambda invocations"
  type        = string
  default     = "{}"

  validation {
    condition     = can(jsondecode(var.schedule_input))
    error_message = "Schedule input must be valid JSON."
  }
}

# Event Triggers
variable "s3_triggers" {
  description = "Map of S3 trigger configurations"
  type = map(object({
    bucket_name   = string
    bucket_arn    = string
    events        = list(string)
    filter_prefix = optional(string, "")
    filter_suffix = optional(string, "")
  }))
  default = {}
}

variable "sqs_triggers" {
  description = "Map of SQS trigger configurations"
  type = map(object({
    queue_arn                          = string
    batch_size                         = optional(number, 10)
    maximum_batching_window_in_seconds = optional(number, 0)
  }))
  default = {}
}

variable "api_gateway_triggers" {
  description = "Map of API Gateway trigger configurations"
  type = map(object({
    source_arn = string
  }))
  default = {}
}

# Tags
variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}