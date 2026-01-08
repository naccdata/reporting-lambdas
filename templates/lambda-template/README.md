# Lambda Template

This template provides a standardized starting point for creating new reporting lambdas in the monorepo.

## Usage

1. Copy this template directory to `lambda/{your-lambda-name}/`
2. Rename `template_lambda` to `{your-lambda-name}_lambda` throughout the codebase
3. Update the Terraform variables and configuration for your specific use case
4. Implement your business logic in the appropriate modules
5. Run `pants tailor ::` to generate BUILD files
6. Update this README with your lambda-specific documentation

## Structure

- `src/python/template_lambda/` - Lambda function code
- `test/python/` - Test files
- `main.tf` - Terraform configuration
- `variables.tf` - Terraform variables
- `outputs.tf` - Terraform outputs

## Data Source and Output

**Data Source**: [Describe your data source here]
**Output Format**: Parquet files in S3
**Output Location**: [Describe output S3 location pattern]

## Deployment

```bash
# Build the lambda
pants package lambda/{your-lambda-name}/src/python/{your-lambda-name}_lambda:lambda

# Deploy infrastructure
terraform init
terraform plan
terraform apply
```

## Development

```bash
# Run tests
pants test lambda/{your-lambda-name}/test/python::

# Run linting
pants lint lambda/{your-lambda-name}::

# Format code
pants fix lambda/{your-lambda-name}::
```