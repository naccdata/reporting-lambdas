# Variables for Lambda IAM Role Module

variable "lambda_name" {
  description = "Name of the Lambda function (used for role naming)"
  type        = string

  validation {
    condition     = length(var.lambda_name) > 0 && length(var.lambda_name) <= 64
    error_message = "Lambda name must be between 1 and 64 characters."
  }
}

variable "s3_bucket_arns" {
  description = "List of S3 bucket ARNs that the Lambda needs access to"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for arn in var.s3_bucket_arns : can(regex("^arn:aws:s3:::[a-z0-9.-]+$", arn))
    ])
    error_message = "All S3 bucket ARNs must be valid S3 bucket ARNs."
  }
}

variable "s3_permissions" {
  description = "List of S3 permissions to grant to the Lambda"
  type        = list(string)
  default = [
    "s3:GetObject",
    "s3:PutObject",
    "s3:DeleteObject",
    "s3:ListBucket"
  ]

  validation {
    condition = alltrue([
      for perm in var.s3_permissions : can(regex("^s3:[A-Za-z]+$", perm))
    ])
    error_message = "All permissions must be valid S3 actions (e.g., s3:GetObject)."
  }
}

variable "enable_xray" {
  description = "Whether to enable X-Ray tracing for the Lambda"
  type        = bool
  default     = true
}

variable "custom_policies" {
  description = "Map of custom policy names to policy documents (JSON strings)"
  type        = map(string)
  default     = {}
}

variable "additional_policy_arns" {
  description = "List of additional managed policy ARNs to attach to the role"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for arn in var.additional_policy_arns : can(regex("^arn:aws:iam::(aws|[0-9]+):policy/.+$", arn))
    ])
    error_message = "All policy ARNs must be valid IAM policy ARNs."
  }
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}