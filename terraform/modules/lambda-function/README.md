# Lambda Function Module

This module creates standardized Lambda functions for reporting lambdas with comprehensive configuration options including triggers, scheduling, VPC support, and versioning.

## Features

- **Complete Lambda Configuration**: Runtime, memory, timeout, architecture, and environment variables
- **Layer Support**: Attach multiple Lambda layers for shared dependencies
- **Event Triggers**: S3, SQS, and API Gateway trigger support
- **Scheduling**: EventBridge-based scheduling with cron and rate expressions
- **Versioning & Aliases**: Support for Lambda versioning and aliases
- **VPC Support**: Optional VPC configuration for private resource access
- **X-Ray Tracing**: Built-in X-Ray tracing support
- **Dead Letter Queues**: Error handling with DLQ support
- **Concurrency Control**: Reserved concurrency configuration

## Usage

### Basic Usage

```hcl
module "lambda_function" {
  source = "../../terraform/modules/lambda-function"

  function_name      = "my-reporting-lambda"
  execution_role_arn = module.lambda_iam.role_arn
  package_path       = "dist/my-lambda.zip"
  
  environment_variables = {
    INPUT_BUCKET  = "my-input-bucket"
    OUTPUT_BUCKET = "my-output-bucket"
    LOG_LEVEL     = "INFO"
  }

  tags = {
    Environment = "prod"
    Project     = "reporting-lambdas"
  }
}
```

### Advanced Usage with Scheduling and Triggers

```hcl
module "lambda_function" {
  source = "../../terraform/modules/lambda-function"

  function_name      = "advanced-reporting-lambda"
  execution_role_arn = module.lambda_iam.role_arn
  package_path       = "dist/advanced-lambda.zip"
  
  # Lambda configuration
  runtime      = "python3.12"
  handler      = "lambda_function.lambda_handler"
  timeout      = 600  # 10 minutes
  memory_size  = 2048 # 2GB
  architectures = ["x86_64"]
  
  # Layers
  layer_arns = [
    "arn:aws:lambda:us-east-1:123456789012:layer:powertools:1",
    "arn:aws:lambda:us-east-1:123456789012:layer:data-processing:2"
  ]
  
  # Environment variables
  environment_variables = {
    INPUT_BUCKET        = var.input_bucket_name
    OUTPUT_BUCKET       = var.output_bucket_name
    OUTPUT_PREFIX       = "processed/"
    LOG_LEVEL          = "INFO"
    POWERTOOLS_SERVICE_NAME = "advanced-reporting-lambda"
  }
  
  # Scheduling - run every hour
  schedule_expression = "rate(1 hour)"
  schedule_enabled    = true
  schedule_input      = jsonencode({
    source = "scheduled"
    batch_size = 1000
  })
  
  # S3 triggers
  s3_triggers = {
    "input-bucket" = {
      bucket_name   = var.input_bucket_name
      bucket_arn    = var.input_bucket_arn
      events        = ["s3:ObjectCreated:*"]
      filter_prefix = "incoming/"
      filter_suffix = ".json"
    }
  }
  
  # SQS triggers
  sqs_triggers = {
    "processing-queue" = {
      queue_arn                          = var.processing_queue_arn
      batch_size                         = 10
      maximum_batching_window_in_seconds = 5
    }
  }
  
  # Versioning and aliases
  create_alias           = true
  alias_name            = "production"
  alias_function_version = "1"
  
  # Error handling
  dead_letter_queue_arn = var.dlq_arn
  
  # Concurrency
  reserved_concurrency = 50
  
  # X-Ray tracing
  enable_xray = true

  tags = {
    Environment = "prod"
    Project     = "reporting-lambdas"
    Owner       = "data-team"
  }
  
  depends_on_resources = [
    module.lambda_iam,
    module.lambda_monitoring
  ]
}
```

### VPC Configuration

```hcl
module "lambda_function" {
  source = "../../terraform/modules/lambda-function"

  function_name      = "vpc-lambda"
  execution_role_arn = module.lambda_iam.role_arn
  package_path       = "dist/vpc-lambda.zip"
  
  # VPC configuration for private resource access
  vpc_subnet_ids = [
    "subnet-12345678",
    "subnet-87654321"
  ]
  
  vpc_security_group_ids = [
    "sg-12345678"
  ]
  
  # Increase timeout for VPC cold starts
  timeout = 900
  
  tags = var.tags
}
```

### Integration with Other Modules

```hcl
# Create IAM role
module "lambda_iam" {
  source = "../../terraform/modules/lambda-iam"
  
  lambda_name    = var.lambda_name
  s3_bucket_arns = [var.input_bucket_arn, var.output_bucket_arn]
  tags           = var.tags
}

# Create monitoring
module "lambda_monitoring" {
  source = "../../terraform/modules/lambda-monitoring"
  
  lambda_name   = var.lambda_name
  alarm_actions = var.sns_topic_arns
  tags          = var.tags
}

# Create Lambda function
module "lambda_function" {
  source = "../../terraform/modules/lambda-function"

  function_name      = var.lambda_name
  execution_role_arn = module.lambda_iam.role_arn
  package_path       = var.package_path
  
  # Configure timeout alarm based on lambda timeout
  timeout = var.lambda_timeout
  
  environment_variables = var.environment_variables
  layer_arns           = var.layer_arns
  schedule_expression  = var.schedule_expression
  
  tags = var.tags
  
  depends_on_resources = [
    module.lambda_iam,
    module.lambda_monitoring
  ]
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| function_name | Name of the Lambda function | `string` | n/a | yes |
| execution_role_arn | ARN of the IAM role for Lambda execution | `string` | n/a | yes |
| package_path | Path to the Lambda deployment package (zip file) | `string` | n/a | yes |
| handler | Lambda function handler | `string` | `"lambda_function.lambda_handler"` | no |
| runtime | Lambda runtime | `string` | `"python3.12"` | no |
| timeout | Lambda function timeout in seconds | `number` | `900` | no |
| memory_size | Lambda function memory size in MB | `number` | `3008` | no |
| architectures | Instruction set architecture for Lambda function | `list(string)` | `["x86_64"]` | no |
| reserved_concurrency | Reserved concurrency for the Lambda function | `number` | `-1` | no |
| source_code_hash | Base64-encoded SHA256 hash of the package file | `string` | `""` | no |
| layer_arns | List of Lambda layer ARNs to attach to the function | `list(string)` | `[]` | no |
| environment_variables | Environment variables for the Lambda function | `map(string)` | `{}` | no |
| enable_xray | Whether to enable X-Ray tracing | `bool` | `true` | no |
| dead_letter_queue_arn | ARN of the dead letter queue (SQS or SNS) | `string` | `""` | no |
| vpc_subnet_ids | List of VPC subnet IDs for Lambda function | `list(string)` | `[]` | no |
| vpc_security_group_ids | List of VPC security group IDs for Lambda function | `list(string)` | `[]` | no |
| create_alias | Whether to create a Lambda alias | `bool` | `false` | no |
| alias_name | Name of the Lambda alias | `string` | `"live"` | no |
| alias_function_version | Lambda function version for the alias | `string` | `"$LATEST"` | no |
| alias_routing_config | Routing configuration for the alias | `map(number)` | `{}` | no |
| schedule_expression | EventBridge schedule expression | `string` | `""` | no |
| schedule_enabled | Whether the schedule is enabled | `bool` | `true` | no |
| schedule_input | JSON input for scheduled Lambda invocations | `string` | `"{}"` | no |
| s3_triggers | Map of S3 trigger configurations | `map(object)` | `{}` | no |
| sqs_triggers | Map of SQS trigger configurations | `map(object)` | `{}` | no |
| api_gateway_triggers | Map of API Gateway trigger configurations | `map(object)` | `{}` | no |
| depends_on_resources | List of resources this Lambda depends on | `list(any)` | `[]` | no |
| tags | Tags to apply to all resources | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| function_arn | ARN of the Lambda function |
| function_name | Name of the Lambda function |
| function_invoke_arn | Invoke ARN of the Lambda function |
| function_qualified_arn | Qualified ARN of the Lambda function |
| function_version | Latest published version of the Lambda function |
| function_last_modified | Date the Lambda function was last modified |
| function_source_code_hash | Base64-encoded SHA256 hash of the package file |
| function_source_code_size | Size in bytes of the function .zip file |
| handler | Lambda function handler |
| runtime | Lambda runtime |
| timeout | Lambda function timeout in seconds |
| memory_size | Lambda function memory size in MB |
| architectures | Instruction set architecture for Lambda function |
| reserved_concurrency | Reserved concurrency for the Lambda function |
| environment_variables | Environment variables configured for the Lambda function |
| layer_arns | List of Lambda layer ARNs attached to the function |
| alias_arn | ARN of the Lambda alias (null if not created) |
| alias_name | Name of the Lambda alias (null if not created) |
| alias_invoke_arn | Invoke ARN of the Lambda alias (null if not created) |
| schedule_rule_name | Name of the EventBridge schedule rule (null if not created) |
| schedule_rule_arn | ARN of the EventBridge schedule rule (null if not created) |
| schedule_enabled | Whether the schedule is enabled |
| s3_trigger_count | Number of S3 triggers configured |
| sqs_trigger_count | Number of SQS triggers configured |
| api_gateway_trigger_count | Number of API Gateway triggers configured |
| s3_trigger_buckets | List of S3 bucket names configured as triggers |
| sqs_trigger_queues | List of SQS queue ARNs configured as triggers |
| vpc_config | VPC configuration for the Lambda function |
| lambda_configuration | Complete Lambda function configuration summary |
| deployment_info | Information about the Lambda deployment |

## Schedule Expression Examples

### Rate Expressions
```hcl
schedule_expression = "rate(5 minutes)"  # Every 5 minutes
schedule_expression = "rate(1 hour)"     # Every hour
schedule_expression = "rate(1 day)"      # Every day
```

### Cron Expressions
```hcl
schedule_expression = "cron(0 12 * * ? *)"      # Daily at noon UTC
schedule_expression = "cron(0 9 ? * MON-FRI *)" # Weekdays at 9 AM UTC
schedule_expression = "cron(0 0 1 * ? *)"       # First day of every month at midnight UTC
```

## S3 Trigger Configuration

```hcl
s3_triggers = {
  "data-input" = {
    bucket_name   = "my-data-bucket"
    bucket_arn    = "arn:aws:s3:::my-data-bucket"
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "incoming/"
    filter_suffix = ".json"
  }
  
  "config-updates" = {
    bucket_name   = "my-config-bucket"
    bucket_arn    = "arn:aws:s3:::my-config-bucket"
    events        = ["s3:ObjectCreated:Put"]
    filter_prefix = "configs/"
    filter_suffix = ".yaml"
  }
}
```

## SQS Trigger Configuration

```hcl
sqs_triggers = {
  "high-priority" = {
    queue_arn                          = "arn:aws:sqs:us-east-1:123456789012:high-priority-queue"
    batch_size                         = 1
    maximum_batching_window_in_seconds = 0
  }
  
  "batch-processing" = {
    queue_arn                          = "arn:aws:sqs:us-east-1:123456789012:batch-queue"
    batch_size                         = 10
    maximum_batching_window_in_seconds = 5
  }
}
```

## Best Practices

1. **Memory and Timeout**: Set appropriate memory and timeout based on workload requirements
2. **Environment Variables**: Use environment variables for configuration, not hardcoded values
3. **Layer Management**: Use layers for shared dependencies to reduce package size
4. **Error Handling**: Configure dead letter queues for error handling
5. **Monitoring**: Always pair with the lambda-monitoring module
6. **VPC Considerations**: Only use VPC when necessary due to cold start impact
7. **Concurrency**: Set reserved concurrency to prevent resource exhaustion
8. **Versioning**: Use aliases for production deployments

## Common Patterns

### Data Processing Lambda
```hcl
module "data_processor" {
  source = "../../terraform/modules/lambda-function"

  function_name = "data-processor"
  execution_role_arn = module.lambda_iam.role_arn
  package_path = "dist/data-processor.zip"
  
  timeout     = 900   # 15 minutes for large datasets
  memory_size = 3008  # 3GB for data processing
  
  schedule_expression = "rate(1 hour)"
  
  environment_variables = {
    INPUT_BUCKET  = var.raw_data_bucket
    OUTPUT_BUCKET = var.processed_data_bucket
    BATCH_SIZE    = "1000"
  }
}
```

### Event-Driven Lambda
```hcl
module "event_processor" {
  source = "../../terraform/modules/lambda-function"

  function_name = "event-processor"
  execution_role_arn = module.lambda_iam.role_arn
  package_path = "dist/event-processor.zip"
  
  timeout     = 300   # 5 minutes for event processing
  memory_size = 1024  # 1GB sufficient for events
  
  s3_triggers = {
    "events" = {
      bucket_name = var.events_bucket
      bucket_arn  = var.events_bucket_arn
      events      = ["s3:ObjectCreated:*"]
      filter_suffix = ".json"
    }
  }
  
  reserved_concurrency = 100  # Limit concurrent executions
}
```