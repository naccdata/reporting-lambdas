# Lambda IAM Role Module

This module creates standardized IAM roles for reporting lambdas with common permissions for S3 access, CloudWatch logging, and X-Ray tracing.

## Features

- **Basic Lambda Execution**: Automatically includes AWS managed basic execution policy
- **X-Ray Tracing**: Optional X-Ray tracing permissions (enabled by default)
- **S3 Access**: Configurable S3 bucket access with customizable permissions
- **Custom Policies**: Support for additional custom inline policies
- **Managed Policies**: Support for additional AWS managed policy attachments
- **Standardized Naming**: Consistent naming patterns for roles and policies

## Usage

### Basic Usage

```hcl
module "lambda_iam" {
  source = "../../terraform/modules/lambda-iam"

  lambda_name = "my-reporting-lambda"
  
  s3_bucket_arns = [
    "arn:aws:s3:::my-input-bucket",
    "arn:aws:s3:::my-output-bucket"
  ]

  tags = {
    Environment = "prod"
    Project     = "reporting-lambdas"
  }
}
```

### Advanced Usage with Custom Policies

```hcl
module "lambda_iam" {
  source = "../../terraform/modules/lambda-iam"

  lambda_name = "advanced-reporting-lambda"
  
  s3_bucket_arns = [
    "arn:aws:s3:::data-source-bucket",
    "arn:aws:s3:::processed-data-bucket"
  ]
  
  s3_permissions = [
    "s3:GetObject",
    "s3:PutObject",
    "s3:ListBucket"
  ]
  
  enable_xray = true
  
  custom_policies = {
    "dynamodb-access" = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Effect = "Allow"
          Action = [
            "dynamodb:GetItem",
            "dynamodb:PutItem",
            "dynamodb:UpdateItem"
          ]
          Resource = "arn:aws:dynamodb:us-east-1:123456789012:table/my-table"
        }
      ]
    })
  }
  
  additional_policy_arns = [
    "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
  ]

  tags = {
    Environment = "prod"
    Project     = "reporting-lambdas"
    Owner       = "data-team"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| lambda_name | Name of the Lambda function (used for role naming) | `string` | n/a | yes |
| s3_bucket_arns | List of S3 bucket ARNs that the Lambda needs access to | `list(string)` | `[]` | no |
| s3_permissions | List of S3 permissions to grant to the Lambda | `list(string)` | `["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]` | no |
| enable_xray | Whether to enable X-Ray tracing for the Lambda | `bool` | `true` | no |
| custom_policies | Map of custom policy names to policy documents (JSON strings) | `map(string)` | `{}` | no |
| additional_policy_arns | List of additional managed policy ARNs to attach to the role | `list(string)` | `[]` | no |
| tags | Tags to apply to all resources | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| role_arn | ARN of the Lambda execution role |
| role_name | Name of the Lambda execution role |
| role_id | ID of the Lambda execution role |
| role_unique_id | Unique ID of the Lambda execution role |
| attached_policies | List of attached policy ARNs |
| custom_policy_names | Names of custom policies created |
| s3_access_enabled | Whether S3 access policy was created |
| s3_bucket_arns | S3 bucket ARNs that the role has access to |

## Common S3 Permission Patterns

### Read-Only Access
```hcl
s3_permissions = [
  "s3:GetObject",
  "s3:ListBucket"
]
```

### Write-Only Access
```hcl
s3_permissions = [
  "s3:PutObject",
  "s3:ListBucket"
]
```

### Full Access (Default)
```hcl
s3_permissions = [
  "s3:GetObject",
  "s3:PutObject",
  "s3:DeleteObject",
  "s3:ListBucket"
]
```

## Best Practices

1. **Principle of Least Privilege**: Only grant the minimum permissions required
2. **Use Specific Bucket ARNs**: Avoid wildcards in S3 bucket ARNs
3. **Tag Resources**: Always include environment and project tags
4. **Custom Policies**: Use custom policies for service-specific permissions
5. **Managed Policies**: Prefer AWS managed policies when available

## Integration with Lambda Module

This module is designed to work seamlessly with the `lambda-function` module:

```hcl
module "lambda_iam" {
  source = "../../terraform/modules/lambda-iam"
  
  lambda_name    = var.lambda_name
  s3_bucket_arns = [var.input_bucket_arn, var.output_bucket_arn]
  tags           = var.tags
}

module "lambda_function" {
  source = "../../terraform/modules/lambda-function"
  
  lambda_name     = var.lambda_name
  execution_role_arn = module.lambda_iam.role_arn
  # ... other configuration
}
```