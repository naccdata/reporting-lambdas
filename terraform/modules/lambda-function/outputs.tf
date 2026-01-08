# Outputs for Lambda Function Module

# Function Outputs
output "function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.function.arn
}

output "function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.function.function_name
}

output "function_invoke_arn" {
  description = "Invoke ARN of the Lambda function (for API Gateway integration)"
  value       = aws_lambda_function.function.invoke_arn
}

output "function_qualified_arn" {
  description = "Qualified ARN of the Lambda function (includes version)"
  value       = aws_lambda_function.function.qualified_arn
}

output "function_version" {
  description = "Latest published version of the Lambda function"
  value       = aws_lambda_function.function.version
}

output "function_last_modified" {
  description = "Date the Lambda function was last modified"
  value       = aws_lambda_function.function.last_modified
}

output "function_source_code_hash" {
  description = "Base64-encoded SHA256 hash of the package file"
  value       = aws_lambda_function.function.source_code_hash
}

output "function_source_code_size" {
  description = "Size in bytes of the function .zip file"
  value       = aws_lambda_function.function.source_code_size
}

# Configuration Outputs
output "handler" {
  description = "Lambda function handler"
  value       = aws_lambda_function.function.handler
}

output "runtime" {
  description = "Lambda runtime"
  value       = aws_lambda_function.function.runtime
}

output "timeout" {
  description = "Lambda function timeout in seconds"
  value       = aws_lambda_function.function.timeout
}

output "memory_size" {
  description = "Lambda function memory size in MB"
  value       = aws_lambda_function.function.memory_size
}

output "architectures" {
  description = "Instruction set architecture for Lambda function"
  value       = aws_lambda_function.function.architectures
}

output "reserved_concurrency" {
  description = "Reserved concurrency for the Lambda function"
  value       = aws_lambda_function.function.reserved_concurrent_executions
}

# Environment and Layers
output "environment_variables" {
  description = "Environment variables configured for the Lambda function"
  value       = aws_lambda_function.function.environment[0].variables
  sensitive   = false
}

output "layer_arns" {
  description = "List of Lambda layer ARNs attached to the function"
  value       = aws_lambda_function.function.layers
}

# Alias Outputs
output "alias_arn" {
  description = "ARN of the Lambda alias (null if not created)"
  value       = var.create_alias ? aws_lambda_alias.function_alias[0].arn : null
}

output "alias_name" {
  description = "Name of the Lambda alias (null if not created)"
  value       = var.create_alias ? aws_lambda_alias.function_alias[0].name : null
}

output "alias_invoke_arn" {
  description = "Invoke ARN of the Lambda alias (null if not created)"
  value       = var.create_alias ? aws_lambda_alias.function_alias[0].invoke_arn : null
}

# Scheduling Outputs
output "schedule_rule_name" {
  description = "Name of the EventBridge schedule rule (null if not created)"
  value       = var.schedule_expression != "" ? aws_cloudwatch_event_rule.schedule[0].name : null
}

output "schedule_rule_arn" {
  description = "ARN of the EventBridge schedule rule (null if not created)"
  value       = var.schedule_expression != "" ? aws_cloudwatch_event_rule.schedule[0].arn : null
}

output "schedule_enabled" {
  description = "Whether the schedule is enabled"
  value       = var.schedule_expression != "" ? var.schedule_enabled : null
}

# Trigger Outputs
output "s3_trigger_count" {
  description = "Number of S3 triggers configured"
  value       = length(var.s3_triggers)
}

output "sqs_trigger_count" {
  description = "Number of SQS triggers configured"
  value       = length(var.sqs_triggers)
}

output "api_gateway_trigger_count" {
  description = "Number of API Gateway triggers configured"
  value       = length(var.api_gateway_triggers)
}

output "s3_trigger_buckets" {
  description = "List of S3 bucket names configured as triggers"
  value       = [for trigger in var.s3_triggers : trigger.bucket_name]
}

output "sqs_trigger_queues" {
  description = "List of SQS queue ARNs configured as triggers"
  value       = [for trigger in var.sqs_triggers : trigger.queue_arn]
}

# VPC Configuration
output "vpc_config" {
  description = "VPC configuration for the Lambda function"
  value = length(var.vpc_subnet_ids) > 0 ? {
    subnet_ids         = var.vpc_subnet_ids
    security_group_ids = var.vpc_security_group_ids
    vpc_id             = aws_lambda_function.function.vpc_config[0].vpc_id
  } : null
}

# Summary Output
output "lambda_configuration" {
  description = "Complete Lambda function configuration summary"
  value = {
    function_name        = aws_lambda_function.function.function_name
    function_arn         = aws_lambda_function.function.arn
    runtime              = aws_lambda_function.function.runtime
    handler              = aws_lambda_function.function.handler
    timeout              = aws_lambda_function.function.timeout
    memory_size          = aws_lambda_function.function.memory_size
    architectures        = aws_lambda_function.function.architectures
    reserved_concurrency = aws_lambda_function.function.reserved_concurrent_executions
    layers               = aws_lambda_function.function.layers
    xray_enabled         = var.enable_xray
    alias_created        = var.create_alias
    schedule_configured  = var.schedule_expression != ""
    vpc_enabled          = length(var.vpc_subnet_ids) > 0
    trigger_count = {
      s3          = length(var.s3_triggers)
      sqs         = length(var.sqs_triggers)
      api_gateway = length(var.api_gateway_triggers)
    }
  }
}

# Deployment Information
output "deployment_info" {
  description = "Information about the Lambda deployment"
  value = {
    package_path     = var.package_path
    source_code_hash = aws_lambda_function.function.source_code_hash
    source_code_size = aws_lambda_function.function.source_code_size
    last_modified    = aws_lambda_function.function.last_modified
    version          = aws_lambda_function.function.version
    qualified_arn    = aws_lambda_function.function.qualified_arn
  }
}