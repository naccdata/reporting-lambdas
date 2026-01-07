# Technology Stack

## Development Environment

**Dev Container** - Consistent development environment using Docker

This project uses dev containers for reproducible development environments. All commands should be executed inside the dev container.

### Container Management Scripts

Located in `bin/` directory:

- `start-devcontainer.sh` - Start the dev container (idempotent, safe to run multiple times)
- `stop-devcontainer.sh` - Stop the dev container
- `build-container.sh` - Rebuild the container after configuration changes
- `exec-in-devcontainer.sh` - Execute a command in the running container
- `terminal.sh` - Open an interactive shell in the container

**CRITICAL**: Always run `./bin/start-devcontainer.sh` before executing any commands to ensure the container is running.

## Build System

**Pants Build System** (v2.29.0) - <https://www.pantsbuild.org>

Pants is used for all builds, testing, linting, and packaging in this Lambda project.

## Language & Runtime

- **Python 3.12** (strict interpreter constraint: `==3.12.*`)
- **AWS Lambda Runtime**: Python 3.12
- Type checking with mypy
- Pydantic v2.7.1+ for data validation and parsing
- Dev container provides Python 3.12 pre-installed

## Key Dependencies

### AWS Lambda Libraries

- `aws-lambda-powertools[aws-sdk]>=2.37.0` - AWS Lambda Powertools for logging, tracing, and metrics
- `boto3>=1.34.0` - AWS SDK for Python
- `botocore>=1.34.0` - Low-level AWS service client library

### Data Processing Libraries

- `pydantic>=2.7.1` - Data validation and settings management with type hints
- `polars>=0.20.0` - Fast DataFrame library for data manipulation and parquet operations

### Testing Libraries

- `pytest>=7.2.0` - Testing framework
- `boto3-stubs` - Type stubs for boto3
- `botocore-stubs` - Type stubs for botocore

## Code Quality Tools

### Linting & Formatting

- **Ruff** - Fast Python linter and formatter
  - Line length: 88 characters
  - Indent: 4 spaces
  - Selected rules: A, B, E, W, F, I, RUF, SIM, C90, PLW0406, COM818, SLF001

### Preventing E501 Line Length Errors in Tests

**CRITICAL**: When writing tests, avoid E501 line length violations (lines > 88 characters) by using these patterns:

**❌ Avoid long strings inline:**
```python
test_files = [
    "log-submit-20240115-100000-42-ingest-form-alpha-110001-01.json",  # E501 error!
    "log-pass-qc-20240115-102000-42-ingest-form-alpha-110001-01.json",  # E501 error!
]
```

**✅ Use constants for long test data:**
```python
# At top of test file
SUBMIT_FULL_LOG = (
    "log-submit-20240115-100000-42-ingest-form-alpha-110001-01.json"
)
PASS_QC_FULL_LOG = (
    "log-pass-qc-20240115-102000-42-ingest-form-alpha-110001-01.json"
)

# In test methods
test_files = [
    SUBMIT_FULL_LOG,
    PASS_QC_FULL_LOG,
]
```

**✅ Alternative: Use string concatenation for very long strings:**
```python
long_filename = (
    "log-submit-20240115-100000-42-ingest-form-"
    "alpha-110001-01.json"
)
```

**Benefits:**
- No E501 linting errors
- Reusable test data across multiple test methods
- Easier to maintain and update test data
- Cleaner, more readable test code

### Type Checking

- **mypy** with Pydantic plugin
- `warn_unused_configs = True`
- `check_untyped_defs = True`

### Testing

- **pytest** with verbose output (`-vv`)
- **Hypothesis** for property-based testing (minimum 100 iterations per property test)

## Docker

### Dev Container

- Base image: Python 3.12 dev container
- Features: Docker-in-Docker, AWS CLI, Terraform
- VS Code extensions: Python, Docker, Ruff, Code Spell Checker, AWS Toolkit
- Configuration: `.devcontainer/devcontainer.json`

## AWS Lambda Development

### Lambda Layers

The project uses a multi-layer approach for optimal performance:

1. **powertools** - AWS Lambda Powertools library (~5MB)
2. **data_processing** - Pydantic and Polars libraries (~15-20MB)

### Lambda Function Structure

- **Runtime**: Python 3.12
- **Memory**: 3GB (configurable via Terraform)
- **Timeout**: 15 minutes (configurable via Terraform)
- **Architecture**: x86_64

### Infrastructure as Code

- **Terraform** for AWS resource management
- **S3** for event log storage and checkpoint files
- **CloudWatch** for logging and monitoring
- **X-Ray** for distributed tracing

## Common Commands

**IMPORTANT**: All commands must be executed inside the dev container. Use the wrapper scripts in `bin/` or open an interactive shell.

### Setup

```bash
# Ensure container is running (always run this first)
./bin/start-devcontainer.sh

# Install Pants
./bin/exec-in-devcontainer.sh bash get-pants.sh
```

### Building Lambda Functions

```bash
# Build Lambda function package
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:lambda

# Build Lambda layers
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:powertools
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:data_processing

# Build all Lambda targets
./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::
```

### Code Quality

**IMPORTANT**: Always run `pants fix` before `pants lint` to automatically fix formatting and import issues.

```bash
# Format code (ALWAYS run this first)
./bin/exec-in-devcontainer.sh pants fix ::

# Run linters (after fix)
./bin/exec-in-devcontainer.sh pants lint ::

# Type check
./bin/exec-in-devcontainer.sh pants check ::

# Run all checks (ALWAYS run fix first to auto-fix issues)
./bin/exec-in-devcontainer.sh pants fix :: && pants lint :: && pants check ::
```

### Testing

```bash
# Run all tests
./bin/exec-in-devcontainer.sh pants test ::

# Run tests for Lambda function
./bin/exec-in-devcontainer.sh pants test lambda/event_log_checkpoint/test/python::

# Run specific test file
./bin/exec-in-devcontainer.sh pants test lambda/event_log_checkpoint/test/python/test_lambda_function.py

# Run specific test method (use -- to pass pytest arguments)
./bin/exec-in-devcontainer.sh pants test lambda/event_log_checkpoint/test/python/test_s3_retriever.py -- -k test_json_retrieval_completeness

# Run specific test class
./bin/exec-in-devcontainer.sh pants test lambda/event_log_checkpoint/test/python/test_s3_retriever.py -- -k TestS3EventRetrieverPropertyTests

# Run tests with verbose output
./bin/exec-in-devcontainer.sh pants test lambda/event_log_checkpoint/test/python/test_s3_retriever.py -- -v

# Run tests with specific pytest options (combine as needed)
./bin/exec-in-devcontainer.sh pants test lambda/event_log_checkpoint/test/python/test_s3_retriever.py -- -k test_method_name -v -s
```

### Infrastructure Deployment

```bash
# Initialize Terraform (from lambda/event_log_checkpoint directory)
./bin/exec-in-devcontainer.sh terraform init

# Plan Terraform deployment
./bin/exec-in-devcontainer.sh terraform plan

# Apply Terraform deployment
./bin/exec-in-devcontainer.sh terraform apply
```

### Interactive Shell (Recommended for Multiple Commands)

```bash
# Open shell in container
./bin/terminal.sh

# Then run commands directly:
pants fix ::
pants lint ::
pants check ::
pants test ::
pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::
```

### Development Workflow

```bash
# Ensure container is running
./bin/start-devcontainer.sh

# Option 1: Run commands via wrapper
./bin/exec-in-devcontainer.sh pants fix ::
./bin/exec-in-devcontainer.sh pants lint ::
./bin/exec-in-devcontainer.sh pants check ::
./bin/exec-in-devcontainer.sh pants test ::

# Option 2: Open interactive shell
./bin/terminal.sh
# Then run: pants fix :: && pants lint :: && pants check :: && pants test ::

# Stop container when done
./bin/stop-devcontainer.sh
```

## Python Interpreter Setup

The dev container provides Python 3.12 pre-installed. No manual Python installation needed.

For local development outside the container, Pants searches for Python interpreters in:

1. System PATH
2. pyenv installations

Ensure Python 3.12 is available via one of these methods.

## Design Principles

### Dependency Injection over Flag Parameters

**Prefer dependency injection over boolean flags for configurable behavior.**

When designing classes that need configurable behavior, use dependency injection with strategy patterns rather than boolean flag parameters.

**❌ Avoid:**

```python
class EventProcessor:
    def __init__(self, events: List[dict], use_fast_mode: bool = False):
        self.events = events
        self.use_fast_mode = use_fast_mode
    
    def process(self):
        if self.use_fast_mode:
            return self._fast_process()
        else:
            return self._thorough_process()
```

**✅ Prefer:**

```python
ProcessingStrategy = Callable[[List[dict]], Any]

def fast_strategy(events: List[dict]) -> Any:
    # Fast processing implementation
    pass

def thorough_strategy(events: List[dict]) -> Any:
    # Thorough processing implementation
    pass

class EventProcessor:
    def __init__(self, events: List[dict], strategy: ProcessingStrategy = thorough_strategy):
        self.events = events
        self.strategy = strategy
    
    def process(self):
        return self.strategy(self.events)
```

**Benefits:**

- **Extensibility**: Easy to add new strategies without modifying existing code
- **Testability**: Each strategy can be tested independently
- **Single Responsibility**: Each strategy focuses on one approach
- **Open/Closed Principle**: Open for extension, closed for modification
- **Clear Intent**: Strategy names are more descriptive than boolean flags

### Lambda-Specific Design Patterns

#### Error Handling

- Use structured logging with Lambda Powertools Logger
- Return proper HTTP status codes in Lambda responses
- Handle partial failures gracefully (continue processing valid events)
- Use AWS X-Ray for distributed tracing

#### Data Processing

- Use Pydantic models for data validation and parsing
- Leverage Polars for efficient DataFrame operations
- Implement incremental processing to avoid reprocessing historical data
- Use parquet format for efficient analytical queries

## Lambda Deployment

### Layer Strategy

The deployment uses a multi-layer approach for optimal performance and maintainability:

- **powertools**: AWS Lambda Powertools library (~5MB, low update frequency)
- **data_processing**: Pydantic and Polars libraries (~15-20MB, medium update frequency)
- **Function code**: Application logic only (<1MB, high update frequency)

### Deployment Workflow

1. Build layers and function packages using Pants
2. Deploy infrastructure using Terraform
3. Upload function code and layers to AWS
4. Configure environment variables and permissions
