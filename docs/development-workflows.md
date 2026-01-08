# Development Workflows

This guide provides comprehensive workflows for developing, testing, and deploying reporting lambdas in the monorepo. It covers both individual lambda development and multi-lambda workflows.

## Prerequisites

### Development Environment Setup

1. **Start the dev container** (always run this first):
   ```bash
   ./bin/start-devcontainer.sh
   ```

2. **Install Pants** (if not already installed):
   ```bash
   ./bin/exec-in-devcontainer.sh bash get-pants.sh
   ```

3. **Verify setup**:
   ```bash
   ./bin/exec-in-devcontainer.sh pants --version
   ```

## Individual Lambda Development

Use this workflow when working on a single lambda without affecting others.

### Creating a New Lambda

#### Step 1: Copy Template

```bash
# Copy the lambda template
cp -r templates/lambda-template lambda/{your-lambda-name}
cd lambda/{your-lambda-name}
```

#### Step 2: Customize Template

```bash
# Replace template_lambda with your lambda name
find . -type f -name "*.py" -exec sed -i 's/template_lambda/{your-lambda-name}_lambda/g' {} +
find . -type f -name "*.tf" -exec sed -i 's/template-lambda/{your-lambda-name}/g' {} +

# Rename the main module directory
mv src/python/template_lambda src/python/{your-lambda-name}_lambda
```

#### Step 3: Generate BUILD Files

```bash
# Generate Pants BUILD files
./bin/exec-in-devcontainer.sh pants tailor lambda/{your-lambda-name}::
```

#### Step 4: Implement Your Logic

1. **Update the handler** (`src/python/{your-lambda-name}_lambda/lambda_function.py`)
2. **Implement business logic** (`src/python/{your-lambda-name}_lambda/reporting_processor.py`)
3. **Add data models** if needed
4. **Update Terraform configuration** (`main.tf`, `variables.tf`)
5. **Update tests** with your specific test cases

### Development Cycle

#### Code Quality Checks

Always run these commands in order:

```bash
# Format code (ALWAYS run this first)
./bin/exec-in-devcontainer.sh pants fix lambda/{your-lambda-name}::

# Run linters (after formatting)
./bin/exec-in-devcontainer.sh pants lint lambda/{your-lambda-name}::

# Type checking
./bin/exec-in-devcontainer.sh pants check lambda/{your-lambda-name}::
```

#### Testing

```bash
# Run all tests for your lambda
./bin/exec-in-devcontainer.sh pants test lambda/{your-lambda-name}/test/python::

# Run specific test file
./bin/exec-in-devcontainer.sh pants test lambda/{your-lambda-name}/test/python/test_lambda_function.py

# Run tests with coverage
./bin/exec-in-devcontainer.sh pants test --coverage-py-report=html lambda/{your-lambda-name}/test/python::

# Run specific test method
./bin/exec-in-devcontainer.sh pants test lambda/{your-lambda-name}/test/python/test_lambda_function.py -- -k test_method_name
```

#### Building

```bash
# Build lambda function
./bin/exec-in-devcontainer.sh pants package lambda/{your-lambda-name}/src/python/{your-lambda-name}_lambda:lambda

# Build lambda layers
./bin/exec-in-devcontainer.sh pants package lambda/{your-lambda-name}/src/python/{your-lambda-name}_lambda:powertools
./bin/exec-in-devcontainer.sh pants package lambda/{your-lambda-name}/src/python/{your-lambda-name}_lambda:data_processing

# Build all targets for your lambda
./bin/exec-in-devcontainer.sh pants package lambda/{your-lambda-name}/src/python/{your-lambda-name}_lambda::
```

### Deployment

#### Infrastructure Deployment

```bash
# Navigate to lambda directory
cd lambda/{your-lambda-name}

# Initialize Terraform (first time only)
./bin/exec-in-devcontainer.sh terraform init

# Plan deployment
./bin/exec-in-devcontainer.sh terraform plan

# Apply deployment
./bin/exec-in-devcontainer.sh terraform apply

# Deploy with specific variables
./bin/exec-in-devcontainer.sh terraform apply -var="source_bucket=my-source-bucket"
```

#### Environment-Specific Deployment

```bash
# Deploy to development
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{your-lambda-name} && terraform workspace select dev && terraform apply"

# Deploy to staging
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{your-lambda-name} && terraform workspace select staging && terraform apply"

# Deploy to production
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{your-lambda-name} && terraform workspace select prod && terraform apply"
```

#### Function-Only Updates

For code changes without infrastructure changes:

```bash
# Build and deploy function code only (fastest)
./bin/exec-in-devcontainer.sh pants package lambda/{your-lambda-name}/src/python/{your-lambda-name}_lambda:lambda
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{your-lambda-name} && terraform apply -target=aws_lambda_function.{your-lambda-name}"
```

## Multi-Lambda Development

Use this workflow when making changes that affect multiple lambdas or common code.

### Working with Common Code

#### Making Changes to Common Code

```bash
# 1. Make changes to common modules
# Edit files in common/src/python/

# 2. Test common code
./bin/exec-in-devcontainer.sh pants test common/test/python::

# 3. Test affected lambdas
./bin/exec-in-devcontainer.sh pants test --changed-since=HEAD~1 lambda::

# 4. Run quality checks on everything
./bin/exec-in-devcontainer.sh pants fix ::
./bin/exec-in-devcontainer.sh pants lint ::
./bin/exec-in-devcontainer.sh pants check ::
```

#### Adding New Common Functionality

```bash
# 1. Add new module or extend existing module
# Create new files in common/src/python/{module}/

# 2. Add comprehensive tests
# Create tests in common/test/python/

# 3. Update BUILD files (if needed)
./bin/exec-in-devcontainer.sh pants tailor common::

# 4. Test new functionality
./bin/exec-in-devcontainer.sh pants test common/test/python/test_{new_module}.py

# 5. Update documentation
# Update docs/{module}-usage.md

# 6. Test integration with existing lambdas
./bin/exec-in-devcontainer.sh pants test lambda::
```

### Repository-Wide Operations

#### Quality Checks Across All Code

```bash
# Format all code (ALWAYS run first)
./bin/exec-in-devcontainer.sh pants fix ::

# Lint all code
./bin/exec-in-devcontainer.sh pants lint ::

# Type check all code
./bin/exec-in-devcontainer.sh pants check ::

# Run all tests
./bin/exec-in-devcontainer.sh pants test ::
```

#### Building All Lambdas

```bash
# Build all lambda functions
./bin/exec-in-devcontainer.sh pants package lambda::

# Build specific lambda targets across all lambdas
./bin/exec-in-devcontainer.sh pants package 'lambda/*/src/python/*_lambda:lambda'

# Build all layers across all lambdas
./bin/exec-in-devcontainer.sh pants package 'lambda/*/src/python/*_lambda:powertools'
./bin/exec-in-devcontainer.sh pants package 'lambda/*/src/python/*_lambda:data_processing'
```

#### Testing Strategies

```bash
# Test only changed code since last commit
./bin/exec-in-devcontainer.sh pants test --changed-since=HEAD~1 ::

# Test only changed code since main branch
./bin/exec-in-devcontainer.sh pants test --changed-since=origin/main ::

# Test specific lambda and its dependencies
./bin/exec-in-devcontainer.sh pants test lambda/{lambda-name}:: common::

# Run tests with specific tags
./bin/exec-in-devcontainer.sh pants test :: -- -m "not slow"
```

## Continuous Integration Workflow

### Pre-Commit Checks

Before committing code, always run:

```bash
# Complete quality check pipeline
./bin/exec-in-devcontainer.sh pants fix ::
./bin/exec-in-devcontainer.sh pants lint ::
./bin/exec-in-devcontainer.sh pants check ::
./bin/exec-in-devcontainer.sh pants test ::
```

### Branch-Based Development

#### Feature Branch Workflow

```bash
# 1. Create feature branch
git checkout -b feature/your-feature-name

# 2. Make your changes
# Edit code, add tests, update documentation

# 3. Run quality checks
./bin/exec-in-devcontainer.sh pants fix ::
./bin/exec-in-devcontainer.sh pants lint ::
./bin/exec-in-devcontainer.sh pants check ::

# 4. Test only changed code
./bin/exec-in-devcontainer.sh pants test --changed-since=origin/main ::

# 5. Commit changes
git add .
git commit -m "feat: add new lambda for customer data processing"

# 6. Push and create pull request
git push origin feature/your-feature-name
```

#### Hotfix Workflow

```bash
# 1. Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/fix-critical-issue

# 2. Make minimal fix
# Edit only necessary files

# 3. Test affected components
./bin/exec-in-devcontainer.sh pants test lambda/{affected-lambda}::

# 4. Deploy to staging for verification
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{affected-lambda} && terraform workspace select staging && terraform apply"

# 5. Commit and deploy to production
git add .
git commit -m "fix: resolve critical data processing issue"
git push origin hotfix/fix-critical-issue

# 6. Deploy to production after approval
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{affected-lambda} && terraform workspace select prod && terraform apply"
```

## Development Environment Workflows

### Interactive Development

For exploration and debugging:

```bash
# Open interactive shell in dev container
./bin/terminal.sh

# Then run commands directly:
pants fix ::
pants lint ::
pants test lambda/my-lambda/test/python::
pants package lambda/my-lambda/src/python/my_lambda_lambda::

# Exit when done
exit
```

### Container Management

```bash
# Start container (idempotent - safe to run multiple times)
./bin/start-devcontainer.sh

# Stop container when done
./bin/stop-devcontainer.sh

# Rebuild container after configuration changes
./bin/build-container.sh
./bin/start-devcontainer.sh

# Execute single command in container
./bin/exec-in-devcontainer.sh pants --version
```

## Testing Workflows

### Unit Testing

```bash
# Run unit tests for specific lambda
./bin/exec-in-devcontainer.sh pants test lambda/{lambda-name}/test/python/test_lambda_function.py

# Run unit tests with verbose output
./bin/exec-in-devcontainer.sh pants test lambda/{lambda-name}/test/python:: -- -v

# Run specific test method
./bin/exec-in-devcontainer.sh pants test lambda/{lambda-name}/test/python/test_lambda_function.py -- -k test_success_case

# Run tests with debugging
./bin/exec-in-devcontainer.sh pants test lambda/{lambda-name}/test/python:: -- -s --pdb
```

### Property-Based Testing

```bash
# Run property-based tests (these may take longer)
./bin/exec-in-devcontainer.sh pants test lambda/{lambda-name}/test/python/test_properties.py

# Run property tests with more iterations
./bin/exec-in-devcontainer.sh pants test lambda/{lambda-name}/test/python/test_properties.py -- --hypothesis-max-examples=1000

# Run property tests with specific seed for reproducibility
./bin/exec-in-devcontainer.sh pants test lambda/{lambda-name}/test/python/test_properties.py -- --hypothesis-seed=12345
```

### Integration Testing

```bash
# Run integration tests (may require AWS credentials)
./bin/exec-in-devcontainer.sh pants test lambda/{lambda-name}/test/python/test_integration.py

# Run integration tests with LocalStack
docker run -d -p 4566:4566 localstack/localstack
./bin/exec-in-devcontainer.sh pants test lambda/{lambda-name}/test/python/test_integration.py -- --localstack
```

## Deployment Workflows

### Development Environment

```bash
# Deploy individual lambda to dev
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{lambda-name} && terraform workspace select dev && terraform apply"

# Deploy all lambdas to dev (use with caution)
for lambda_dir in lambda/*/; do
    lambda_name=$(basename "$lambda_dir")
    if [ "$lambda_name" != "template" ]; then
        ./bin/exec-in-devcontainer.sh bash -c "cd $lambda_dir && terraform workspace select dev && terraform apply -auto-approve"
    fi
done
```

### Staging Environment

```bash
# Deploy to staging for testing
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{lambda-name} && terraform workspace select staging && terraform plan"
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{lambda-name} && terraform workspace select staging && terraform apply"

# Run smoke tests against staging
./bin/exec-in-devcontainer.sh pants test lambda/{lambda-name}/test/python/test_smoke.py -- --environment=staging
```

### Production Environment

```bash
# Deploy to production (requires approval)
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{lambda-name} && terraform workspace select prod && terraform plan"

# Review plan carefully, then apply
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{lambda-name} && terraform workspace select prod && terraform apply"

# Monitor deployment
aws logs tail /aws/lambda/{lambda-name} --follow
```

### Rollback Procedures

```bash
# Rollback to previous version
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{lambda-name} && terraform workspace select prod && terraform apply -target=aws_lambda_function.{lambda-name} -var='lambda_version=previous'"

# Rollback infrastructure changes
git checkout HEAD~1 -- lambda/{lambda-name}/main.tf
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{lambda-name} && terraform apply"
```

## Monitoring and Debugging Workflows

### Log Analysis

```bash
# View recent lambda logs
aws logs tail /aws/lambda/{lambda-name} --since 1h

# Follow logs in real-time
aws logs tail /aws/lambda/{lambda-name} --follow

# Search logs for errors
aws logs filter-log-events --log-group-name /aws/lambda/{lambda-name} --filter-pattern "ERROR"

# Export logs for analysis
aws logs create-export-task --log-group-name /aws/lambda/{lambda-name} --from 1640995200000 --to 1641081600000 --destination s3-bucket-name
```

### Performance Analysis

```bash
# View X-Ray traces
aws xray get-trace-summaries --time-range-type TimeRangeByStartTime --start-time 2024-01-01T00:00:00Z --end-time 2024-01-01T23:59:59Z

# Analyze CloudWatch metrics
aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Duration --dimensions Name=FunctionName,Value={lambda-name} --start-time 2024-01-01T00:00:00Z --end-time 2024-01-01T23:59:59Z --period 3600 --statistics Average,Maximum
```

### Local Debugging

```bash
# Run lambda locally with test event
./bin/exec-in-devcontainer.sh python -c "
import json
from lambda.{lambda-name}.src.python.{lambda-name}_lambda.lambda_function import lambda_handler

# Load test event
with open('test_event.json') as f:
    event = json.load(f)

# Mock context
class MockContext:
    aws_request_id = 'test-request-id'
    function_name = '{lambda-name}'

# Run handler
result = lambda_handler(event, MockContext())
print(json.dumps(result, indent=2))
"
```

## Troubleshooting Common Issues

### Build Issues

```bash
# Clear Pants cache
./bin/exec-in-devcontainer.sh pants clean-all

# Regenerate BUILD files
./bin/exec-in-devcontainer.sh pants tailor ::

# Check dependency graph
./bin/exec-in-devcontainer.sh pants dependencies lambda/{lambda-name}/src/python/{lambda-name}_lambda:lambda
```

### Test Issues

```bash
# Run tests with verbose output
./bin/exec-in-devcontainer.sh pants test lambda/{lambda-name}/test/python:: -- -v -s

# Run tests with debugging
./bin/exec-in-devcontainer.sh pants test lambda/{lambda-name}/test/python:: -- --pdb

# Check test discovery
./bin/exec-in-devcontainer.sh pants list lambda/{lambda-name}/test/python::
```

### Deployment Issues

```bash
# Check Terraform state
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{lambda-name} && terraform show"

# Validate Terraform configuration
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{lambda-name} && terraform validate"

# Check AWS credentials
./bin/exec-in-devcontainer.sh aws sts get-caller-identity

# Force refresh Terraform state
./bin/exec-in-devcontainer.sh bash -c "cd lambda/{lambda-name} && terraform refresh"
```

## Best Practices

### Code Quality

1. **Always run `pants fix` before `pants lint`** - formatting must come first
2. **Run quality checks before committing** - prevents CI failures
3. **Use property-based tests** - catches edge cases unit tests miss
4. **Keep functions small and focused** - easier to test and maintain

### Testing

1. **Write tests first** - helps design better APIs
2. **Test error conditions** - most bugs occur in error paths
3. **Use realistic test data** - avoid overly simple test cases
4. **Mock external dependencies** - tests should be fast and reliable

### Deployment

1. **Test in staging first** - catch issues before production
2. **Deploy during low-traffic periods** - minimize impact of issues
3. **Monitor after deployment** - watch for errors and performance issues
4. **Have rollback plan ready** - be prepared to revert quickly

### Performance

1. **Profile before optimizing** - measure to find real bottlenecks
2. **Use incremental processing** - only process new/changed data
3. **Monitor memory usage** - avoid out-of-memory errors
4. **Set appropriate timeouts** - balance reliability and cost

## Workflow Checklists

### New Lambda Checklist

- [ ] Copy template and customize names
- [ ] Generate BUILD files with `pants tailor`
- [ ] Implement handler and business logic
- [ ] Add comprehensive tests (unit and property-based)
- [ ] Update Terraform configuration
- [ ] Run quality checks (`fix`, `lint`, `check`, `test`)
- [ ] Deploy to development environment
- [ ] Test in development
- [ ] Update documentation
- [ ] Deploy to staging for final testing
- [ ] Deploy to production

### Code Change Checklist

- [ ] Make code changes
- [ ] Update tests if needed
- [ ] Run `pants fix` to format code
- [ ] Run `pants lint` to check style
- [ ] Run `pants check` for type checking
- [ ] Run `pants test` for affected components
- [ ] Test locally if possible
- [ ] Commit changes with descriptive message
- [ ] Deploy to staging for testing
- [ ] Deploy to production after approval

### Release Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] Staging deployment successful
- [ ] Performance testing completed
- [ ] Security review completed (if needed)
- [ ] Rollback plan prepared
- [ ] Monitoring alerts configured
- [ ] Production deployment
- [ ] Post-deployment monitoring
- [ ] Update release notes