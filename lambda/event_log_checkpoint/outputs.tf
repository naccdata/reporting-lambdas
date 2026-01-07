# Outputs for Event Log Checkpoint Lambda Infrastructure

# Lambda function outputs
output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.event_log_checkpoint.arn
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.event_log_checkpoint.function_name
}

output "lambda_function_invoke_arn" {
  description = "Invoke ARN of the Lambda function (for API Gateway integration)"
  value       = aws_lambda_function.event_log_checkpoint.invoke_arn
}

output "lambda_function_qualified_arn" {
  description = "Qualified ARN of the Lambda function (includes version)"
  value       = aws_lambda_function.event_log_checkpoint.qualified_arn
}

output "lambda_function_version" {
  description = "Latest published version of the Lambda function"
  value       = aws_lambda_function.event_log_checkpoint.version
}

# Layer outputs (only when not using external layers)
output "powertools_layer_arn" {
  description = "ARN of the Powertools layer (null when using external layers)"
  value = var.use_external_layer_arns ? null : (
    var.reuse_existing_layers && length(data.aws_lambda_layer_version.powertools) > 0 && !var.force_layer_update ?
    data.aws_lambda_layer_version.powertools[0].arn :
    length(aws_lambda_layer_version.powertools) > 0 ? aws_lambda_layer_version.powertools[0].arn : null
  )
}

output "powertools_layer_version" {
  description = "Version of the Powertools layer (null when using external layers)"
  value = var.use_external_layer_arns ? null : (
    var.reuse_existing_layers && length(data.aws_lambda_layer_version.powertools) > 0 && !var.force_layer_update ?
    data.aws_lambda_layer_version.powertools[0].version :
    length(aws_lambda_layer_version.powertools) > 0 ? aws_lambda_layer_version.powertools[0].version : null
  )
}

output "data_processing_layer_arn" {
  description = "ARN of the data processing layer (null when using external layers)"
  value = var.use_external_layer_arns ? null : (
    var.reuse_existing_layers && length(data.aws_lambda_layer_version.data_processing) > 0 && !var.force_layer_update ?
    data.aws_lambda_layer_version.data_processing[0].arn :
    length(aws_lambda_layer_version.data_processing) > 0 ? aws_lambda_layer_version.data_processing[0].arn : null
  )
}

output "data_processing_layer_version" {
  description = "Version of the data processing layer (null when using external layers)"
  value = var.use_external_layer_arns ? null : (
    var.reuse_existing_layers && length(data.aws_lambda_layer_version.data_processing) > 0 && !var.force_layer_update ?
    data.aws_lambda_layer_version.data_processing[0].version :
    length(aws_lambda_layer_version.data_processing) > 0 ? aws_lambda_layer_version.data_processing[0].version : null
  )
}

output "all_layer_arns" {
  description = "All layer ARNs used by the Lambda function"
  value       = local.layer_arns
}

# IAM outputs
output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_role.arn
}

output "lambda_role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.lambda_role.name
}

# CloudWatch outputs
output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.lambda_logs.arn
}

# Alarm outputs
output "error_alarm_name" {
  description = "Name of the error CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.lambda_errors.alarm_name
}

output "duration_alarm_name" {
  description = "Name of the duration CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.lambda_duration.alarm_name
}

# Configuration outputs
output "environment_variables" {
  description = "Environment variables configured for the Lambda function"
  value       = aws_lambda_function.event_log_checkpoint.environment[0].variables
  sensitive   = false
}

output "lambda_configuration" {
  description = "Lambda function configuration summary"
  value = {
    function_name = aws_lambda_function.event_log_checkpoint.function_name
    runtime       = aws_lambda_function.event_log_checkpoint.runtime
    handler       = aws_lambda_function.event_log_checkpoint.handler
    timeout       = aws_lambda_function.event_log_checkpoint.timeout
    memory_size   = aws_lambda_function.event_log_checkpoint.memory_size
    layers        = local.layer_arns
  }
}

# Layer management outputs
output "layer_management_strategy" {
  description = "Summary of layer management configuration"
  value = {
    reuse_existing_layers   = var.reuse_existing_layers
    use_external_layer_arns = var.use_external_layer_arns
    force_layer_update      = var.force_layer_update
    external_layer_arns     = var.external_layer_arns
  }
}

# Deployment information
output "deployment_info" {
  description = "Information about the deployment configuration"
  value = {
    source_bucket     = var.source_bucket
    checkpoint_bucket = var.checkpoint_bucket
    checkpoint_key    = var.checkpoint_key
    environment       = var.environment
    log_level         = var.log_level
  }
}