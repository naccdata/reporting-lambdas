# Lambda Function Module
# Provides standardized Lambda function infrastructure for reporting lambdas

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Lambda function
resource "aws_lambda_function" "function" {
  function_name = var.function_name
  role         = var.execution_role_arn
  handler      = var.handler
  runtime      = var.runtime
  timeout      = var.timeout
  memory_size  = var.memory_size
  architectures = var.architectures

  filename         = var.package_path
  source_code_hash = var.source_code_hash != "" ? var.source_code_hash : filebase64sha256(var.package_path)

  layers = var.layer_arns

  environment {
    variables = var.environment_variables
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  dead_letter_config {
    target_arn = var.dead_letter_queue_arn
  }

  vpc_config {
    subnet_ids         = var.vpc_subnet_ids
    security_group_ids = var.vpc_security_group_ids
  }

  # Reserved concurrency
  reserved_concurrency = var.reserved_concurrency

  tags = merge(var.tags, {
    Name    = var.function_name
    Module  = "lambda-function"
    Purpose = "Reporting Lambda function"
  })

  depends_on = var.depends_on_resources
}

# Lambda function alias (for versioning)
resource "aws_lambda_alias" "function_alias" {
  count            = var.create_alias ? 1 : 0
  name             = var.alias_name
  description      = "Alias for ${var.function_name}"
  function_name    = aws_lambda_function.function.function_name
  function_version = var.alias_function_version

  routing_config {
    additional_version_weights = var.alias_routing_config
  }
}

# EventBridge rule for scheduled execution
resource "aws_cloudwatch_event_rule" "schedule" {
  count               = var.schedule_expression != "" ? 1 : 0
  name                = "${var.function_name}-schedule"
  description         = "Schedule for ${var.function_name}"
  schedule_expression = var.schedule_expression
  state               = var.schedule_enabled ? "ENABLED" : "DISABLED"

  tags = merge(var.tags, {
    Name    = "${var.function_name}-schedule"
    Module  = "lambda-function"
    Purpose = "Lambda schedule"
  })
}

# EventBridge target
resource "aws_cloudwatch_event_target" "lambda_target" {
  count     = var.schedule_expression != "" ? 1 : 0
  rule      = aws_cloudwatch_event_rule.schedule[0].name
  target_id = "TargetLambda"
  arn       = var.create_alias ? aws_lambda_alias.function_alias[0].arn : aws_lambda_function.function.arn

  input = var.schedule_input
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  count         = var.schedule_expression != "" ? 1 : 0
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.function.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule[0].arn
  qualifier     = var.create_alias ? aws_lambda_alias.function_alias[0].name : null
}

# S3 trigger permissions (if configured)
resource "aws_lambda_permission" "allow_s3" {
  for_each      = var.s3_triggers
  statement_id  = "AllowExecutionFromS3-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.function.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = each.value.bucket_arn
  qualifier     = var.create_alias ? aws_lambda_alias.function_alias[0].name : null
}

# S3 bucket notifications (if configured)
resource "aws_s3_bucket_notification" "s3_notifications" {
  for_each = var.s3_triggers
  bucket   = each.value.bucket_name

  lambda_function {
    lambda_function_arn = var.create_alias ? aws_lambda_alias.function_alias[0].arn : aws_lambda_function.function.arn
    events              = each.value.events
    filter_prefix       = each.value.filter_prefix
    filter_suffix       = each.value.filter_suffix
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

# SQS trigger permissions (if configured)
resource "aws_lambda_permission" "allow_sqs" {
  for_each      = var.sqs_triggers
  statement_id  = "AllowExecutionFromSQS-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.function.function_name
  principal     = "sqs.amazonaws.com"
  source_arn    = each.value.queue_arn
  qualifier     = var.create_alias ? aws_lambda_alias.function_alias[0].name : null
}

# SQS event source mappings (if configured)
resource "aws_lambda_event_source_mapping" "sqs_triggers" {
  for_each                       = var.sqs_triggers
  event_source_arn              = each.value.queue_arn
  function_name                 = aws_lambda_function.function.arn
  batch_size                    = each.value.batch_size
  maximum_batching_window_in_seconds = each.value.maximum_batching_window_in_seconds
  
  depends_on = [aws_lambda_permission.allow_sqs]
}

# API Gateway permissions (if configured)
resource "aws_lambda_permission" "allow_api_gateway" {
  for_each      = var.api_gateway_triggers
  statement_id  = "AllowExecutionFromAPIGateway-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.function.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = each.value.source_arn
  qualifier     = var.create_alias ? aws_lambda_alias.function_alias[0].name : null
}