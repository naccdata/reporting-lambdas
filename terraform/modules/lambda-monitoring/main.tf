# Lambda Monitoring Module
# Provides standardized CloudWatch monitoring for reporting lambdas including log groups and alarms

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.lambda_name}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name    = "${var.lambda_name}-logs"
    Module  = "lambda-monitoring"
    Purpose = "Lambda function logs"
  })
}

# Error alarm
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  count               = var.enable_error_alarm ? 1 : 0
  alarm_name          = "${var.lambda_name}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = var.error_alarm_evaluation_periods
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = var.error_alarm_period
  statistic           = "Sum"
  threshold           = var.error_alarm_threshold
  alarm_description   = "Lambda function ${var.lambda_name} error rate alarm"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = var.lambda_name
  }

  tags = merge(var.tags, {
    Name    = "${var.lambda_name}-errors"
    Module  = "lambda-monitoring"
    Purpose = "Lambda error monitoring"
  })
}

# Duration alarm
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  count               = var.enable_duration_alarm ? 1 : 0
  alarm_name          = "${var.lambda_name}-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = var.duration_alarm_evaluation_periods
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = var.duration_alarm_period
  statistic           = "Average"
  threshold           = var.duration_alarm_threshold
  alarm_description   = "Lambda function ${var.lambda_name} duration alarm"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = var.lambda_name
  }

  tags = merge(var.tags, {
    Name    = "${var.lambda_name}-duration"
    Module  = "lambda-monitoring"
    Purpose = "Lambda duration monitoring"
  })
}

# Throttle alarm
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  count               = var.enable_throttle_alarm ? 1 : 0
  alarm_name          = "${var.lambda_name}-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = var.throttle_alarm_evaluation_periods
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = var.throttle_alarm_period
  statistic           = "Sum"
  threshold           = var.throttle_alarm_threshold
  alarm_description   = "Lambda function ${var.lambda_name} throttle alarm"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = var.lambda_name
  }

  tags = merge(var.tags, {
    Name    = "${var.lambda_name}-throttles"
    Module  = "lambda-monitoring"
    Purpose = "Lambda throttle monitoring"
  })
}

# Memory utilization alarm (requires custom metric or enhanced monitoring)
resource "aws_cloudwatch_metric_alarm" "lambda_memory" {
  count               = var.enable_memory_alarm ? 1 : 0
  alarm_name          = "${var.lambda_name}-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = var.memory_alarm_evaluation_periods
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/Lambda"
  period              = var.memory_alarm_period
  statistic           = "Average"
  threshold           = var.memory_alarm_threshold
  alarm_description   = "Lambda function ${var.lambda_name} memory utilization alarm"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = var.lambda_name
  }

  tags = merge(var.tags, {
    Name    = "${var.lambda_name}-memory"
    Module  = "lambda-monitoring"
    Purpose = "Lambda memory monitoring"
  })
}

# Custom metric alarms
resource "aws_cloudwatch_metric_alarm" "custom_alarms" {
  for_each = var.custom_alarms

  alarm_name          = "${var.lambda_name}-${each.key}"
  comparison_operator = each.value.comparison_operator
  evaluation_periods  = each.value.evaluation_periods
  metric_name         = each.value.metric_name
  namespace           = each.value.namespace
  period              = each.value.period
  statistic           = each.value.statistic
  threshold           = each.value.threshold
  alarm_description   = each.value.description
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  treat_missing_data  = lookup(each.value, "treat_missing_data", "notBreaching")

  dimensions = merge(
    { FunctionName = var.lambda_name },
    lookup(each.value, "additional_dimensions", {})
  )

  tags = merge(var.tags, {
    Name    = "${var.lambda_name}-${each.key}"
    Module  = "lambda-monitoring"
    Purpose = "Custom Lambda monitoring"
  })
}

# CloudWatch Dashboard (optional)
resource "aws_cloudwatch_dashboard" "lambda_dashboard" {
  count          = var.create_dashboard ? 1 : 0
  dashboard_name = "${var.lambda_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", var.lambda_name],
            [".", "Errors", ".", "."],
            [".", "Duration", ".", "."],
            [".", "Throttles", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "${var.lambda_name} - Key Metrics"
          period  = 300
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 6
        width  = 24
        height = 6

        properties = {
          query   = "SOURCE '/aws/lambda/${var.lambda_name}' | fields @timestamp, @message | sort @timestamp desc | limit 100"
          region  = data.aws_region.current.name
          title   = "${var.lambda_name} - Recent Logs"
        }
      }
    ]
  })
}

# Data source for current region
data "aws_region" "current" {}