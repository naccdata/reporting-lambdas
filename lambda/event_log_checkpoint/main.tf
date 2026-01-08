# Event Log Checkpoint Lambda Infrastructure
# This configuration creates an AWS Lambda function with optimized layer management
# for processing event logs and creating checkpoint parquet files.

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Data sources to check for existing layers
data "aws_lambda_layer_version" "powertools" {
  count      = var.reuse_existing_layers && !var.use_external_layer_arns ? 1 : 0
  layer_name = "event-log-checkpoint-powertools"
}

data "aws_lambda_layer_version" "data_processing" {
  count      = var.reuse_existing_layers && !var.use_external_layer_arns ? 1 : 0
  layer_name = "event-log-checkpoint-data-processing"
}

# Lambda layers - only create if not reusing existing or if content changed
resource "aws_lambda_layer_version" "powertools" {
  count = var.use_external_layer_arns ? 0 : (
    var.reuse_existing_layers && length(data.aws_lambda_layer_version.powertools) > 0 && !var.force_layer_update ? 0 : 1
  )

  filename         = "../../dist/lambda.event_log_checkpoint.src.python.checkpoint_lambda/powertools.zip"
  layer_name       = "event-log-checkpoint-powertools"
  source_code_hash = filebase64sha256("../../dist/lambda.event_log_checkpoint.src.python.checkpoint_lambda/powertools.zip")

  compatible_runtimes = ["python3.12"]
  description         = "AWS Lambda Powertools layer for event log checkpoint function"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lambda_layer_version" "data_processing" {
  count = var.use_external_layer_arns ? 0 : (
    var.reuse_existing_layers && length(data.aws_lambda_layer_version.data_processing) > 0 && !var.force_layer_update ? 0 : 1
  )

  filename         = "../../dist/lambda.event_log_checkpoint.src.python.checkpoint_lambda/data_processing.zip"
  layer_name       = "event-log-checkpoint-data-processing"
  source_code_hash = filebase64sha256("../../dist/lambda.event_log_checkpoint.src.python.checkpoint_lambda/data_processing.zip")

  compatible_runtimes = ["python3.12"]
  description         = "Pydantic and Polars layer for data processing"

  lifecycle {
    create_before_destroy = true
  }
}

# Local values to determine which layer ARNs to use
locals {
  powertools_layer_arn = var.use_external_layer_arns ? var.external_layer_arns[0] : (
    var.reuse_existing_layers && length(data.aws_lambda_layer_version.powertools) > 0 && !var.force_layer_update ?
    data.aws_lambda_layer_version.powertools[0].arn :
    aws_lambda_layer_version.powertools[0].arn
  )

  data_processing_layer_arn = var.use_external_layer_arns ? var.external_layer_arns[1] : (
    var.reuse_existing_layers && length(data.aws_lambda_layer_version.data_processing) > 0 && !var.force_layer_update ?
    data.aws_lambda_layer_version.data_processing[0].arn :
    aws_lambda_layer_version.data_processing[0].arn
  )

  # Combine all layer ARNs
  layer_arns = var.use_external_layer_arns ? var.external_layer_arns : [
    local.powertools_layer_arn,
    local.data_processing_layer_arn,
  ]
}

# IAM role for Lambda function
resource "aws_iam_role" "lambda_role" {
  name = "event-log-checkpoint-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "event-log-checkpoint-lambda-role"
    Environment = var.environment
    Project     = "event-log-checkpoint"
  }
}

# S3 permissions for Lambda function
resource "aws_iam_role_policy" "lambda_s3_policy" {
  name = "event-log-checkpoint-s3-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.source_bucket}",
          "arn:aws:s3:::${var.source_bucket}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.checkpoint_bucket}",
          "arn:aws:s3:::${var.checkpoint_bucket}/*"
        ]
      }
    ]
  })
}

# Attach AWS managed policies
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_xray" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/event-log-checkpoint"
  retention_in_days = 30

  tags = {
    Name        = "event-log-checkpoint-logs"
    Environment = var.environment
    Project     = "event-log-checkpoint"
  }
}

# Lambda function
resource "aws_lambda_function" "event_log_checkpoint" {
  function_name = "event-log-checkpoint"
  role          = aws_iam_role.lambda_role.arn
  handler       = "checkpoint_lambda.lambda_function.lambda_handler"
  runtime       = "python3.12"
  timeout       = 900  # 15 minutes
  memory_size   = 3008 # 3GB

  filename         = "../../dist/lambda.event_log_checkpoint.src.python.checkpoint_lambda/lambda.zip"
  source_code_hash = filebase64sha256("../../dist/lambda.event_log_checkpoint.src.python.checkpoint_lambda/lambda.zip")

  layers = local.layer_arns

  environment {
    variables = {
      SOURCE_BUCKET           = var.source_bucket
      CHECKPOINT_BUCKET       = var.checkpoint_bucket
      CHECKPOINT_KEY          = var.checkpoint_key
      LOG_LEVEL               = var.log_level
      POWERTOOLS_SERVICE_NAME = "event-log-checkpoint"
    }
  }

  tracing_config {
    mode = "Active" # Enable X-Ray tracing
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy_attachment.lambda_xray,
    aws_cloudwatch_log_group.lambda_logs,
  ]

  tags = {
    Name        = "event-log-checkpoint"
    Environment = var.environment
    Project     = "event-log-checkpoint"
  }
}

# CloudWatch alarms for monitoring
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "event-log-checkpoint-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors lambda errors"
  alarm_actions       = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  dimensions = {
    FunctionName = aws_lambda_function.event_log_checkpoint.function_name
  }

  tags = {
    Name        = "event-log-checkpoint-errors"
    Environment = var.environment
    Project     = "event-log-checkpoint"
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "event-log-checkpoint-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "600000" # 10 minutes in milliseconds
  alarm_description   = "This metric monitors lambda duration"
  alarm_actions       = var.alarm_sns_topic_arn != "" ? [var.alarm_sns_topic_arn] : []

  dimensions = {
    FunctionName = aws_lambda_function.event_log_checkpoint.function_name
  }

  tags = {
    Name        = "event-log-checkpoint-duration"
    Environment = var.environment
    Project     = "event-log-checkpoint"
  }
}