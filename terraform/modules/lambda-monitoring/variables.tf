# Variables for Lambda Monitoring Module

variable "lambda_name" {
  description = "Name of the Lambda function to monitor"
  type        = string

  validation {
    condition     = length(var.lambda_name) > 0 && length(var.lambda_name) <= 64
    error_message = "Lambda name must be between 1 and 64 characters."
  }
}

# Log Group Configuration
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

# Alarm Actions
variable "alarm_actions" {
  description = "List of ARNs to notify when alarm triggers (e.g., SNS topic ARNs)"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for arn in var.alarm_actions : can(regex("^arn:aws:sns:[a-z0-9-]+:[0-9]+:[a-zA-Z0-9-_]+$", arn))
    ])
    error_message = "All alarm action ARNs must be valid SNS topic ARNs."
  }
}

variable "ok_actions" {
  description = "List of ARNs to notify when alarm returns to OK state"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for arn in var.ok_actions : can(regex("^arn:aws:sns:[a-z0-9-]+:[0-9]+:[a-zA-Z0-9-_]+$", arn))
    ])
    error_message = "All OK action ARNs must be valid SNS topic ARNs."
  }
}

# Error Alarm Configuration
variable "enable_error_alarm" {
  description = "Whether to create error rate alarm"
  type        = bool
  default     = true
}

variable "error_alarm_threshold" {
  description = "Error count threshold for alarm"
  type        = number
  default     = 0

  validation {
    condition     = var.error_alarm_threshold >= 0
    error_message = "Error alarm threshold must be non-negative."
  }
}

variable "error_alarm_evaluation_periods" {
  description = "Number of evaluation periods for error alarm"
  type        = number
  default     = 2

  validation {
    condition     = var.error_alarm_evaluation_periods >= 1 && var.error_alarm_evaluation_periods <= 100
    error_message = "Error alarm evaluation periods must be between 1 and 100."
  }
}

variable "error_alarm_period" {
  description = "Period in seconds for error alarm evaluation"
  type        = number
  default     = 300

  validation {
    condition     = var.error_alarm_period >= 60
    error_message = "Error alarm period must be at least 60 seconds."
  }
}

# Duration Alarm Configuration
variable "enable_duration_alarm" {
  description = "Whether to create duration alarm"
  type        = bool
  default     = true
}

variable "duration_alarm_threshold" {
  description = "Duration threshold in milliseconds for alarm"
  type        = number
  default     = 600000 # 10 minutes

  validation {
    condition     = var.duration_alarm_threshold > 0
    error_message = "Duration alarm threshold must be positive."
  }
}

variable "duration_alarm_evaluation_periods" {
  description = "Number of evaluation periods for duration alarm"
  type        = number
  default     = 2

  validation {
    condition     = var.duration_alarm_evaluation_periods >= 1 && var.duration_alarm_evaluation_periods <= 100
    error_message = "Duration alarm evaluation periods must be between 1 and 100."
  }
}

variable "duration_alarm_period" {
  description = "Period in seconds for duration alarm evaluation"
  type        = number
  default     = 300

  validation {
    condition     = var.duration_alarm_period >= 60
    error_message = "Duration alarm period must be at least 60 seconds."
  }
}

# Throttle Alarm Configuration
variable "enable_throttle_alarm" {
  description = "Whether to create throttle alarm"
  type        = bool
  default     = true
}

variable "throttle_alarm_threshold" {
  description = "Throttle count threshold for alarm"
  type        = number
  default     = 0

  validation {
    condition     = var.throttle_alarm_threshold >= 0
    error_message = "Throttle alarm threshold must be non-negative."
  }
}

variable "throttle_alarm_evaluation_periods" {
  description = "Number of evaluation periods for throttle alarm"
  type        = number
  default     = 2

  validation {
    condition     = var.throttle_alarm_evaluation_periods >= 1 && var.throttle_alarm_evaluation_periods <= 100
    error_message = "Throttle alarm evaluation periods must be between 1 and 100."
  }
}

variable "throttle_alarm_period" {
  description = "Period in seconds for throttle alarm evaluation"
  type        = number
  default     = 300

  validation {
    condition     = var.throttle_alarm_period >= 60
    error_message = "Throttle alarm period must be at least 60 seconds."
  }
}

# Memory Alarm Configuration
variable "enable_memory_alarm" {
  description = "Whether to create memory utilization alarm"
  type        = bool
  default     = false
}

variable "memory_alarm_threshold" {
  description = "Memory utilization percentage threshold for alarm"
  type        = number
  default     = 80

  validation {
    condition     = var.memory_alarm_threshold >= 0 && var.memory_alarm_threshold <= 100
    error_message = "Memory alarm threshold must be between 0 and 100."
  }
}

variable "memory_alarm_evaluation_periods" {
  description = "Number of evaluation periods for memory alarm"
  type        = number
  default     = 2

  validation {
    condition     = var.memory_alarm_evaluation_periods >= 1 && var.memory_alarm_evaluation_periods <= 100
    error_message = "Memory alarm evaluation periods must be between 1 and 100."
  }
}

variable "memory_alarm_period" {
  description = "Period in seconds for memory alarm evaluation"
  type        = number
  default     = 300

  validation {
    condition     = var.memory_alarm_period >= 60
    error_message = "Memory alarm period must be at least 60 seconds."
  }
}

# Custom Alarms
variable "custom_alarms" {
  description = "Map of custom alarm configurations"
  type = map(object({
    comparison_operator   = string
    evaluation_periods    = number
    metric_name           = string
    namespace             = string
    period                = number
    statistic             = string
    threshold             = number
    description           = string
    treat_missing_data    = optional(string, "notBreaching")
    additional_dimensions = optional(map(string), {})
  }))
  default = {}
}

# Dashboard Configuration
variable "create_dashboard" {
  description = "Whether to create a CloudWatch dashboard for the Lambda"
  type        = bool
  default     = false
}

# Tags
variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}