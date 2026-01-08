# Lambda Monitoring Module

This module creates standardized CloudWatch monitoring for reporting lambdas including log groups, alarms, and optional dashboards.

## Features

- **CloudWatch Log Group**: Automatically creates log group with configurable retention
- **Standard Alarms**: Error, duration, throttle, and memory utilization alarms
- **Custom Alarms**: Support for additional custom metric alarms
- **CloudWatch Dashboard**: Optional dashboard with key metrics and logs
- **SNS Integration**: Configurable alarm actions for notifications
- **Standardized Naming**: Consistent naming patterns for all monitoring resources

## Usage

### Basic Usage

```hcl
module "lambda_monitoring" {
  source = "../../terraform/modules/lambda-monitoring"

  lambda_name = "my-reporting-lambda"
  
  # SNS topic for alarm notifications
  alarm_actions = ["arn:aws:sns:us-east-1:123456789012:lambda-alerts"]
  
  tags = {
    Environment = "prod"
    Project     = "reporting-lambdas"
  }
}
```

### Advanced Usage with Custom Alarms

```hcl
module "lambda_monitoring" {
  source = "../../terraform/modules/lambda-monitoring"

  lambda_name        = "advanced-reporting-lambda"
  log_retention_days = 90
  
  # Standard alarm configuration
  enable_error_alarm    = true
  error_alarm_threshold = 1
  
  enable_duration_alarm    = true
  duration_alarm_threshold = 300000  # 5 minutes
  
  enable_throttle_alarm = true
  enable_memory_alarm   = true
  memory_alarm_threshold = 85
  
  # Custom alarms for business metrics
  custom_alarms = {
    "records-processed" = {
      comparison_operator = "LessThanThreshold"
      evaluation_periods  = 3
      metric_name        = "RecordsProcessed"
      namespace          = "Custom/Lambda"
      period             = 300
      statistic          = "Sum"
      threshold          = 100
      description        = "Alert when fewer than 100 records processed"
    }
    
    "processing-rate" = {
      comparison_operator = "LessThanThreshold"
      evaluation_periods  = 2
      metric_name        = "ProcessingRate"
      namespace          = "Custom/Lambda"
      period             = 600
      statistic          = "Average"
      threshold          = 10
      description        = "Alert when processing rate drops below 10 records/minute"
    }
  }
  
  # Notification configuration
  alarm_actions = [
    "arn:aws:sns:us-east-1:123456789012:critical-alerts",
    "arn:aws:sns:us-east-1:123456789012:lambda-alerts"
  ]
  
  ok_actions = [
    "arn:aws:sns:us-east-1:123456789012:lambda-alerts"
  ]
  
  # Create dashboard for monitoring
  create_dashboard = true

  tags = {
    Environment = "prod"
    Project     = "reporting-lambdas"
    Owner       = "data-team"
  }
}
```

### Integration with Lambda Function

```hcl
module "lambda_monitoring" {
  source = "../../terraform/modules/lambda-monitoring"
  
  lambda_name = var.lambda_name
  
  # Configure alarms based on lambda timeout
  duration_alarm_threshold = var.lambda_timeout * 1000 * 0.8  # 80% of timeout
  
  alarm_actions = var.sns_topic_arns
  tags          = var.tags
  
  depends_on = [module.lambda_function]
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| lambda_name | Name of the Lambda function to monitor | `string` | n/a | yes |
| log_retention_days | CloudWatch log retention in days | `number` | `30` | no |
| alarm_actions | List of ARNs to notify when alarm triggers | `list(string)` | `[]` | no |
| ok_actions | List of ARNs to notify when alarm returns to OK state | `list(string)` | `[]` | no |
| enable_error_alarm | Whether to create error rate alarm | `bool` | `true` | no |
| error_alarm_threshold | Error count threshold for alarm | `number` | `0` | no |
| error_alarm_evaluation_periods | Number of evaluation periods for error alarm | `number` | `2` | no |
| error_alarm_period | Period in seconds for error alarm evaluation | `number` | `300` | no |
| enable_duration_alarm | Whether to create duration alarm | `bool` | `true` | no |
| duration_alarm_threshold | Duration threshold in milliseconds for alarm | `number` | `600000` | no |
| duration_alarm_evaluation_periods | Number of evaluation periods for duration alarm | `number` | `2` | no |
| duration_alarm_period | Period in seconds for duration alarm evaluation | `number` | `300` | no |
| enable_throttle_alarm | Whether to create throttle alarm | `bool` | `true` | no |
| throttle_alarm_threshold | Throttle count threshold for alarm | `number` | `0` | no |
| throttle_alarm_evaluation_periods | Number of evaluation periods for throttle alarm | `number` | `2` | no |
| throttle_alarm_period | Period in seconds for throttle alarm evaluation | `number` | `300` | no |
| enable_memory_alarm | Whether to create memory utilization alarm | `bool` | `false` | no |
| memory_alarm_threshold | Memory utilization percentage threshold for alarm | `number` | `80` | no |
| memory_alarm_evaluation_periods | Number of evaluation periods for memory alarm | `number` | `2` | no |
| memory_alarm_period | Period in seconds for memory alarm evaluation | `number` | `300` | no |
| custom_alarms | Map of custom alarm configurations | `map(object)` | `{}` | no |
| create_dashboard | Whether to create a CloudWatch dashboard | `bool` | `false` | no |
| tags | Tags to apply to all resources | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| log_group_name | Name of the CloudWatch log group |
| log_group_arn | ARN of the CloudWatch log group |
| log_group_retention_days | Log retention period in days |
| error_alarm_name | Name of the error alarm (null if disabled) |
| error_alarm_arn | ARN of the error alarm (null if disabled) |
| duration_alarm_name | Name of the duration alarm (null if disabled) |
| duration_alarm_arn | ARN of the duration alarm (null if disabled) |
| throttle_alarm_name | Name of the throttle alarm (null if disabled) |
| throttle_alarm_arn | ARN of the throttle alarm (null if disabled) |
| memory_alarm_name | Name of the memory alarm (null if disabled) |
| memory_alarm_arn | ARN of the memory alarm (null if disabled) |
| custom_alarm_names | Names of custom alarms created |
| custom_alarm_arns | ARNs of custom alarms created |
| dashboard_name | Name of the CloudWatch dashboard (null if not created) |
| dashboard_arn | ARN of the CloudWatch dashboard (null if not created) |
| dashboard_url | URL of the CloudWatch dashboard (null if not created) |
| monitoring_summary | Summary of monitoring configuration |
| all_alarm_arns | List of all alarm ARNs created by this module |
| all_alarm_names | List of all alarm names created by this module |

## Alarm Thresholds

### Recommended Thresholds by Environment

#### Production
```hcl
error_alarm_threshold    = 0      # Any error triggers alarm
duration_alarm_threshold = 300000 # 5 minutes (adjust based on expected runtime)
throttle_alarm_threshold = 0      # Any throttling triggers alarm
memory_alarm_threshold   = 85     # 85% memory utilization
```

#### Staging
```hcl
error_alarm_threshold    = 1      # Allow some errors for testing
duration_alarm_threshold = 600000 # 10 minutes
throttle_alarm_threshold = 1      # Allow some throttling
memory_alarm_threshold   = 90     # 90% memory utilization
```

#### Development
```hcl
enable_error_alarm    = false  # Disable in dev
enable_duration_alarm = false  # Disable in dev
enable_throttle_alarm = false  # Disable in dev
enable_memory_alarm   = false  # Disable in dev
```

## Custom Alarm Examples

### Business Logic Alarms
```hcl
custom_alarms = {
  "low-throughput" = {
    comparison_operator = "LessThanThreshold"
    evaluation_periods  = 3
    metric_name        = "RecordsProcessed"
    namespace          = "AWS/Lambda"
    period             = 300
    statistic          = "Sum"
    threshold          = 1000
    description        = "Alert when processing fewer than 1000 records per 5 minutes"
  }
}
```

### Data Quality Alarms
```hcl
custom_alarms = {
  "high-error-rate" = {
    comparison_operator = "GreaterThanThreshold"
    evaluation_periods  = 2
    metric_name        = "DataValidationErrors"
    namespace          = "Custom/DataProcessing"
    period             = 300
    statistic          = "Sum"
    threshold          = 10
    description        = "Alert when data validation errors exceed 10 per 5 minutes"
  }
}
```

## Best Practices

1. **Environment-Specific Configuration**: Use different thresholds for different environments
2. **SNS Topics**: Create separate SNS topics for different severity levels
3. **Log Retention**: Set appropriate retention based on compliance requirements
4. **Custom Metrics**: Use custom metrics for business-specific monitoring
5. **Dashboard Creation**: Enable dashboards for production environments
6. **Alarm Actions**: Configure both alarm and OK actions for complete notification lifecycle

## Integration with Other Modules

This module works seamlessly with other Lambda modules:

```hcl
# Create Lambda function
module "lambda_function" {
  source = "../../terraform/modules/lambda-function"
  # ... configuration
}

# Create monitoring
module "lambda_monitoring" {
  source = "../../terraform/modules/lambda-monitoring"
  
  lambda_name = module.lambda_function.function_name
  
  # Set duration alarm based on lambda timeout
  duration_alarm_threshold = module.lambda_function.timeout * 1000 * 0.8
  
  depends_on = [module.lambda_function]
}
```