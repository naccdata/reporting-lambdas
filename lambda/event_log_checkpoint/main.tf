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

  # Backend configuration for remote state management
  backend "s3" {
    bucket  = "nacc-terraform-state"
    key     = "lambda/event-log-checkpoint/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true

    # Note: DynamoDB locking intentionally omitted
    # Team coordination via communication (Slack, etc.)
  }
}

# Data sources to check for existing layers
data "aws_lambda_layer_version" "powertools" {
  count      = var.reuse_existing_layers && !var.use_external_layer_arns ? 1 : 0
  layer_name = "event-log-checkpoint-powertools-${var.environment}"
}

data "aws_lambda_layer_version" "data_processing" {
  count      = var.reuse_existing_layers && !var.use_external_layer_arns ? 1 : 0
  layer_name = "event-log-checkpoint-data-processing-${var.environment}"
}

# Lambda layers - only create if not reusing existing or if content changed
resource "aws_lambda_layer_version" "powertools" {
  count = var.use_external_layer_arns ? 0 : (
    var.reuse_existing_layers && length(data.aws_lambda_layer_version.powertools) > 0 && !var.force_layer_update ? 0 : 1
  )

  filename         = "../../dist/lambda.event_log_checkpoint.src.python.checkpoint_lambda/powertools.zip"
  layer_name       = "event-log-checkpoint-powertools-${var.environment}"
  source_code_hash = filebase64sha256("../../dist/lambda.event_log_checkpoint.src.python.checkpoint_lambda/powertools.zip")

  compatible_runtimes = ["python3.12"]
  description         = "AWS Lambda Powertools layer for event log checkpoint function (${var.environment})"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lambda_layer_version" "data_processing" {
  count = var.use_external_layer_arns ? 0 : (
    var.reuse_existing_layers && length(data.aws_lambda_layer_version.data_processing) > 0 && !var.force_layer_update ? 0 : 1
  )

  filename         = "../../dist/lambda.event_log_checkpoint.src.python.checkpoint_lambda/data_processing.zip"
  layer_name       = "event-log-checkpoint-data-processing-${var.environment}"
  source_code_hash = filebase64sha256("../../dist/lambda.event_log_checkpoint.src.python.checkpoint_lambda/data_processing.zip")

  compatible_runtimes = ["python3.12"]
  description         = "Pydantic and Polars layer for data processing (${var.environment})"

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
  name = "event-log-checkpoint-lambda-role-${var.environment}"

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
  name = "event-log-checkpoint-s3-policy-${var.environment}"
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
  name              = "/aws/lambda/event-log-checkpoint-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "event-log-checkpoint-logs"
    Environment = var.environment
    Project     = "event-log-checkpoint"
  }
}

# Lambda function
resource "aws_lambda_function" "event_log_checkpoint" {
  function_name = "event-log-checkpoint-${var.environment}"
  role          = aws_iam_role.lambda_role.arn
  handler       = "checkpoint_lambda.lambda_function.lambda_handler"
  runtime       = "python3.12"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size

  filename         = "../../dist/lambda.event_log_checkpoint.src.python.checkpoint_lambda/lambda.zip"
  source_code_hash = filebase64sha256("../../dist/lambda.event_log_checkpoint.src.python.checkpoint_lambda/lambda.zip")

  layers = local.layer_arns

  environment {
    variables = {
      SOURCE_BUCKET           = var.source_bucket
      CHECKPOINT_BUCKET       = var.checkpoint_bucket
      CHECKPOINT_KEY_TEMPLATE = var.checkpoint_key_template
      LOG_LEVEL               = var.log_level
      ENVIRONMENT             = var.environment
      POWERTOOLS_SERVICE_NAME = "event-log-checkpoint-${var.environment}"
    }
  }

  tracing_config {
    mode = "Active" # Enable X-Ray tracing
  }

  # Enable versioning - creates new version on each deployment
  publish = true

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

# Lambda alias for stable endpoint
resource "aws_lambda_alias" "current" {
  name             = var.environment
  description      = "Alias for ${var.environment} environment - points to current version"
  function_name    = aws_lambda_function.event_log_checkpoint.function_name
  function_version = aws_lambda_function.event_log_checkpoint.version

  lifecycle {
    ignore_changes = [function_version]
  }
}

# CloudWatch alarms for monitoring
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "event-log-checkpoint-errors-${var.environment}"
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
    Name        = "event-log-checkpoint-errors-${var.environment}"
    Environment = var.environment
    Project     = "event-log-checkpoint"
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "event-log-checkpoint-duration-${var.environment}"
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
    Name        = "event-log-checkpoint-duration-${var.environment}"
    Environment = var.environment
    Project     = "event-log-checkpoint"
  }
}

# S3 lifecycle policy for event log archival
# This manages the lifecycle of event log JSON files in the source bucket
resource "aws_s3_bucket_lifecycle_configuration" "event_log_archival" {
  count  = var.manage_source_bucket_lifecycle ? 1 : 0
  bucket = var.source_bucket

  # Rule for archival or expiration
  rule {
    id     = "manage-event-logs-${var.environment}"
    status = "Enabled"

    # Apply to event log files only (matching the pattern)
    filter {
      prefix = var.event_log_prefix != "" ? var.event_log_prefix : ""
    }

    # Transition to Glacier (only if archival is enabled)
    dynamic "transition" {
      for_each = var.enable_event_log_archival ? [1] : []
      content {
        days          = var.days_until_glacier_transition
        storage_class = "GLACIER"
      }
    }

    # Optional: Transition to Deep Archive for long-term storage
    dynamic "transition" {
      for_each = var.enable_event_log_archival && var.days_until_deep_archive_transition > 0 ? [1] : []
      content {
        days          = var.days_until_deep_archive_transition
        storage_class = "DEEP_ARCHIVE"
      }
    }

    # Optional: Expire (delete) files after specified days
    dynamic "expiration" {
      for_each = var.days_until_expiration > 0 ? [1] : []
      content {
        days = var.days_until_expiration
      }
    }
  }

  # Cleanup incomplete multipart uploads after 7 days
  rule {
    id     = "cleanup-incomplete-uploads-${var.environment}"
    status = "Enabled"

    filter {
      prefix = var.event_log_prefix != "" ? var.event_log_prefix : ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}