terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Lambda execution role
resource "aws_iam_role" "lambda_role" {
  name = "${var.lambda_name}-execution-role"

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
}

# Basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_role.name
}

# S3 access policy for data processing
resource "aws_iam_role_policy" "s3_access" {
  name = "${var.lambda_name}-s3-access"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${var.input_bucket_arn}",
          "${var.input_bucket_arn}/*",
          "${var.output_bucket_arn}",
          "${var.output_bucket_arn}/*"
        ]
      }
    ]
  })
}

# X-Ray tracing policy
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
  role       = aws_iam_role.lambda_role.name
}

# Lambda function
resource "aws_lambda_function" "template_lambda" {
  filename      = var.lambda_package_path
  function_name = var.lambda_name
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"
  timeout       = var.timeout
  memory_size   = var.memory_size
  architectures = ["x86_64"]

  source_code_hash = filebase64sha256(var.lambda_package_path)

  layers = var.lambda_layers

  environment {
    variables = {
      INPUT_BUCKET            = var.input_bucket_name
      OUTPUT_BUCKET           = var.output_bucket_name
      OUTPUT_PREFIX           = var.output_prefix
      LOG_LEVEL               = var.log_level
      POWERTOOLS_SERVICE_NAME = var.lambda_name
    }
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy.s3_access,
    aws_iam_role_policy_attachment.lambda_xray,
  ]
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.lambda_name}"
  retention_in_days = var.log_retention_days
}

# EventBridge rule for scheduled execution (optional)
resource "aws_cloudwatch_event_rule" "schedule" {
  count               = var.schedule_expression != "" ? 1 : 0
  name                = "${var.lambda_name}-schedule"
  description         = "Schedule for ${var.lambda_name}"
  schedule_expression = var.schedule_expression
}

# EventBridge target
resource "aws_cloudwatch_event_target" "lambda_target" {
  count     = var.schedule_expression != "" ? 1 : 0
  rule      = aws_cloudwatch_event_rule.schedule[0].name
  target_id = "TargetLambda"
  arn       = aws_lambda_function.template_lambda.arn
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  count         = var.schedule_expression != "" ? 1 : 0
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.template_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule[0].arn
}