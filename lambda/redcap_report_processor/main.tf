# REDCap Report Processor Lambda Infrastructure
# This configuration creates an AWS Lambda function with optimized layer management
# for processing REDCap reports.

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
    key     = "lambda/redcap-report-processor/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true

    # Note: DynamoDB locking intentionally omitted
    # Team coordination via communication (Slack, etc.)
  }
}

# Data sources to check for existing layers
data "aws_lambda_layer_version" "powertools" {
  count      = var.reuse_existing_layers && !var.use_external_layer_arns ? 1 : 0
  layer_name = "redcap-report-processor-powertools-${var.environment}"
}

data "aws_lambda_layer_version" "data_processing" {
  count      = var.reuse_existing_layers && !var.use_external_layer_arns ? 1 : 0
  layer_name = "redcap-report-processor-data-processing-${var.environment}"
}

data "aws_lambda_layer_version" "redcap_api" {
  count      = var.reuse_existing_layers && !var.use_external_layer_arns ? 1 : 0
  layer_name = "redcap-report-processor-redcap-api-${var.environment}"
}

data "aws_caller_identity" "current" {}

# Lambda layers - only create if not reusing existing or if content changed
resource "aws_lambda_layer_version" "powertools" {
  count = var.use_external_layer_arns ? 0 : (
    var.reuse_existing_layers && length(data.aws_lambda_layer_version.powertools) > 0 && !var.force_layer_update ? 0 : 1
  )

  filename         = "../../dist/lambda.redcap_report_processor.src.python.redcap_report_processor_lambda/powertools.zip"
  layer_name       = "redcap-report-processor-powertools-${var.environment}"
  source_code_hash = filebase64sha256("../../dist/lambda.redcap_report_processor.src.python.redcap_report_processor_lambda/powertools.zip")

  compatible_runtimes = ["python3.12"]
  description         = "AWS Lambda Powertools layer for REDCap report processor function (${var.environment})"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lambda_layer_version" "data_processing" {
  count = var.use_external_layer_arns ? 0 : (
    var.reuse_existing_layers && length(data.aws_lambda_layer_version.data_processing) > 0 && !var.force_layer_update ? 0 : 1
  )

  filename         = "../../dist/lambda.redcap_report_processor.src.python.redcap_report_processor_lambda/data_processing.zip"
  layer_name       = "redcap-report-processor-data-processing-${var.environment}"
  source_code_hash = filebase64sha256("../../dist/lambda.redcap_report_processor.src.python.redcap_report_processor_lambda/data_processing.zip")

  compatible_runtimes = ["python3.12"]
  description         = "Pydantic and Polars layer for data processing (${var.environment})"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lambda_layer_version" "redcap_api" {
  count = var.use_external_layer_arns ? 0 : (
    var.reuse_existing_layers && length(data.aws_lambda_layer_version.redcap_api) > 0 && !var.force_layer_update ? 0 : 1
  )

  filename         = "../../dist/lambda.redcap_report_processor.src.python.redcap_report_processor_lambda/redcap_api.zip"
  layer_name       = "redcap-report-processor-redcap-api-${var.environment}"
  source_code_hash = filebase64sha256("../../dist/lambda.redcap_report_processor.src.python.redcap_report_processor_lambda/redcap_api.zip")

  compatible_runtimes = ["python3.12"]
  description         = "REDCap API layer for communication with REDCap (${var.environment})"

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

  redcap_api_layer_arn = var.use_external_layer_arns ? var.external_layer_arns[1] : (
    var.reuse_existing_layers && length(data.aws_lambda_layer_version.redcap_api) > 0 && !var.force_layer_update ?
    data.aws_lambda_layer_version.redcap_api[0].arn :
    aws_lambda_layer_version.redcap_api[0].arn
  )

  # Combine all layer ARNs
  layer_arns = var.use_external_layer_arns ? var.external_layer_arns : [
    local.powertools_layer_arn,
    local.data_processing_layer_arn,
    local.redcap_api_layer_arn,
  ]
}

# IAM role for Lambda function
resource "aws_iam_role" "lambda_role" {
  name = "redcap-report-processor-lambda-role-${var.environment}"

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
    Name        = "redcap-report-processor-lambda-role"
    Environment = var.environment
    Project     = "redcap-report-processor"
  }
}

# S3 permissions for Lambda function
resource "aws_iam_role_policy" "lambda_s3_policy" {
  name = "redcap-report-processor-s3-policy-${var.environment}"
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
          "arn:aws:s3:::${var.s3_prefix}",
          "arn:aws:s3:::${var.s3_prefix}/*"
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
          "arn:aws:s3:::${var.s3_prefix}",
          "arn:aws:s3:::${var.s3_prefix}/*"
        ]
      }
    ]
  })
}

# SSM Parameter Store permissions for Lambda function
resource "aws_iam_role_policy" "lambda_ssm_policy" {
  name = "redcap-report-processor-ssm-policy-${var.environment}"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/redcap/aws/*"
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
  name              = "/aws/lambda/redcap-report-processor-${var.environment}"
  retention_in_days = 30

  tags = {
    Name        = "redcap-report-processor-logs"
    Environment = var.environment
    Project     = "redcap-report-processor"
  }
}

# Lambda function
resource "aws_lambda_function" "redcap_report_processor" {
  function_name = "redcap-report-processor-${var.environment}"
  role          = aws_iam_role.lambda_role.arn
  handler       = "redcap_report_processor_lambda.lambda_function.lambda_handler"
  runtime       = "python3.12"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size

  filename         = "../../dist/lambda.redcap_report_processor.src.python.redcap_report_processor_lambda/lambda.zip"
  source_code_hash = filebase64sha256("../../dist/lambda.redcap_report_processor.src.python.redcap_report_processor_lambda/lambda.zip")

  layers = local.layer_arns

  environment {
    variables = {
      S3_PREFIX               = var.s3_prefix
      REGION                  = var.region
      ENVIRONMENT             = var.environment
      LOG_LEVEL               = var.log_level
      POWERTOOLS_SERVICE_NAME = "redcap-report-processor"
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
    Name        = "redcap-report-processor"
    Environment = var.environment
    Project     = "redcap-report-processor"
  }
}
# Lambda alias for stable endpoint
resource "aws_lambda_alias" "current" {
  name             = var.environment
  description      = "Alias for ${var.environment} environment - points to current version"
  function_name    = aws_lambda_function.redcap_report_processor.function_name
  function_version = aws_lambda_function.redcap_report_processor.version

  lifecycle {
    ignore_changes = [function_version]
  }
}

# CloudWatch alarms for monitoring
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "redcap-report-processor-errors-${var.environment}"
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
    FunctionName = aws_lambda_function.redcap_report_processor.function_name
  }

  tags = {
    Name        = "redcap-report-processor-errors-${var.environment}"
    Environment = var.environment
    Project     = "redcap-report-processor"
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "redcap-report-processor-duration-${var.environment}"
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
    FunctionName = aws_lambda_function.redcap_report_processor.function_name
  }

  tags = {
    Name        = "redcap-report-processor-duration-${var.environment}"
    Environment = var.environment
    Project     = "redcap-report-processor"
  }
}