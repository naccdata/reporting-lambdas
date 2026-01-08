# Outputs for Lambda Monitoring Module

# Log Group Outputs
output "log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.lambda_logs.arn
}

output "log_group_retention_days" {
  description = "Log retention period in days"
  value       = aws_cloudwatch_log_group.lambda_logs.retention_in_days
}

# Alarm Outputs
output "error_alarm_name" {
  description = "Name of the error alarm (null if disabled)"
  value       = var.enable_error_alarm ? aws_cloudwatch_metric_alarm.lambda_errors[0].alarm_name : null
}

output "error_alarm_arn" {
  description = "ARN of the error alarm (null if disabled)"
  value       = var.enable_error_alarm ? aws_cloudwatch_metric_alarm.lambda_errors[0].arn : null
}

output "duration_alarm_name" {
  description = "Name of the duration alarm (null if disabled)"
  value       = var.enable_duration_alarm ? aws_cloudwatch_metric_alarm.lambda_duration[0].alarm_name : null
}

output "duration_alarm_arn" {
  description = "ARN of the duration alarm (null if disabled)"
  value       = var.enable_duration_alarm ? aws_cloudwatch_metric_alarm.lambda_duration[0].arn : null
}

output "throttle_alarm_name" {
  description = "Name of the throttle alarm (null if disabled)"
  value       = var.enable_throttle_alarm ? aws_cloudwatch_metric_alarm.lambda_throttles[0].alarm_name : null
}

output "throttle_alarm_arn" {
  description = "ARN of the throttle alarm (null if disabled)"
  value       = var.enable_throttle_alarm ? aws_cloudwatch_metric_alarm.lambda_throttles[0].arn : null
}

output "memory_alarm_name" {
  description = "Name of the memory alarm (null if disabled)"
  value       = var.enable_memory_alarm ? aws_cloudwatch_metric_alarm.lambda_memory[0].alarm_name : null
}

output "memory_alarm_arn" {
  description = "ARN of the memory alarm (null if disabled)"
  value       = var.enable_memory_alarm ? aws_cloudwatch_metric_alarm.lambda_memory[0].arn : null
}

# Custom Alarm Outputs
output "custom_alarm_names" {
  description = "Names of custom alarms created"
  value       = { for k, v in aws_cloudwatch_metric_alarm.custom_alarms : k => v.alarm_name }
}

output "custom_alarm_arns" {
  description = "ARNs of custom alarms created"
  value       = { for k, v in aws_cloudwatch_metric_alarm.custom_alarms : k => v.arn }
}

# Dashboard Outputs
output "dashboard_name" {
  description = "Name of the CloudWatch dashboard (null if not created)"
  value       = var.create_dashboard ? aws_cloudwatch_dashboard.lambda_dashboard[0].dashboard_name : null
}

output "dashboard_arn" {
  description = "ARN of the CloudWatch dashboard (null if not created)"
  value       = var.create_dashboard ? aws_cloudwatch_dashboard.lambda_dashboard[0].dashboard_arn : null
}

output "dashboard_url" {
  description = "URL of the CloudWatch dashboard (null if not created)"
  value       = var.create_dashboard ? "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.lambda_dashboard[0].dashboard_name}" : null
}

# Summary Outputs
output "monitoring_summary" {
  description = "Summary of monitoring configuration"
  value = {
    log_group_name         = aws_cloudwatch_log_group.lambda_logs.name
    log_retention_days     = aws_cloudwatch_log_group.lambda_logs.retention_in_days
    error_alarm_enabled    = var.enable_error_alarm
    duration_alarm_enabled = var.enable_duration_alarm
    throttle_alarm_enabled = var.enable_throttle_alarm
    memory_alarm_enabled   = var.enable_memory_alarm
    custom_alarms_count    = length(var.custom_alarms)
    dashboard_created      = var.create_dashboard
    alarm_actions_count    = length(var.alarm_actions)
  }
}

output "all_alarm_arns" {
  description = "List of all alarm ARNs created by this module"
  value = compact([
    var.enable_error_alarm ? aws_cloudwatch_metric_alarm.lambda_errors[0].arn : null,
    var.enable_duration_alarm ? aws_cloudwatch_metric_alarm.lambda_duration[0].arn : null,
    var.enable_throttle_alarm ? aws_cloudwatch_metric_alarm.lambda_throttles[0].arn : null,
    var.enable_memory_alarm ? aws_cloudwatch_metric_alarm.lambda_memory[0].arn : null,
  ])
}

output "all_alarm_names" {
  description = "List of all alarm names created by this module"
  value = compact([
    var.enable_error_alarm ? aws_cloudwatch_metric_alarm.lambda_errors[0].alarm_name : null,
    var.enable_duration_alarm ? aws_cloudwatch_metric_alarm.lambda_duration[0].alarm_name : null,
    var.enable_throttle_alarm ? aws_cloudwatch_metric_alarm.lambda_throttles[0].alarm_name : null,
    var.enable_memory_alarm ? aws_cloudwatch_metric_alarm.lambda_memory[0].alarm_name : null,
  ])
}