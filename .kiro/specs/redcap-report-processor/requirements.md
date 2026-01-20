# Requirements Document

## Introduction

This document specifies the requirements for an AWS Lambda function that retrieves report data from a REDCap instance using the redcap-api package and stores the data in S3 as parquet files. The Lambda will pull tabular report data by report ID, handle both overwrite and append operations, and support configurable REDCap API credentials via AWS Parameter Store.

The Lambda will be built using Python 3.12, AWS Lambda Powertools for observability, Pydantic for data validation, Polars for DataFrame operations and parquet file generation, and the redcap-api package for REDCap integration. The project follows the established NACC development patterns using Pants build system 2.29 and dev container workflow.

## Glossary

- **Lambda**: The AWS Lambda function that processes REDCap reports (implemented as `redcap_report_lambda`)
- **REDCap**: Research Electronic Data Capture system for building and managing online surveys and databases
- **Report**: A tabular view of survey data in REDCap, defined by report ID
- **Report_ID**: Integer identifier for a specific report configuration in REDCap
- **API_Token**: Authentication token for REDCap API access
- **Parameter_Store**: AWS Systems Manager Parameter Store for secure credential storage
- **Parquet**: A columnar storage file format optimized for analytical queries
- **S3**: Amazon Simple Storage Service for file storage
- **Overwrite_Mode**: Operation mode that replaces existing parquet file completely
- **Append_Mode**: Operation mode that adds new data to existing parquet file
- **Dev Container**: Containerized development environment using devcontainer CLI

## Requirements

### Requirement 1

**User Story:** As a data engineer, I want the Lambda to retrieve report data from REDCap using the redcap-api package, so that I can access structured survey data for analysis.

#### Acceptance Criteria

1. WHEN the Lambda is invoked with a report ID THEN the Lambda SHALL use the redcap-api package to connect to the REDCap instance
2. WHEN the Lambda connects to REDCap THEN the Lambda SHALL retrieve the API URL and token from AWS Parameter Store
3. WHEN the Lambda calls the REDCap API THEN the Lambda SHALL request report data using the specified report ID
4. WHEN the REDCap API returns report data THEN the Lambda SHALL receive the data in tabular format with consistent row structure
5. WHEN the Lambda encounters REDCap API errors THEN the Lambda SHALL log the error details and return a failure response
6. WHEN the Lambda successfully retrieves report data THEN the Lambda SHALL validate that all rows have identical schema structure

### Requirement 2

**User Story:** As a data engineer, I want the Lambda to handle REDCap API credentials securely, so that sensitive authentication information is protected.

#### Acceptance Criteria

1. WHEN the Lambda needs REDCap credentials THEN the Lambda SHALL retrieve the API URL from AWS Parameter Store using a configurable parameter name
2. WHEN the Lambda needs REDCap credentials THEN the Lambda SHALL retrieve the API token from AWS Parameter Store using a configurable parameter name
3. WHEN the Lambda retrieves parameters THEN the Lambda SHALL use secure string parameters for the API token
4. WHEN the Lambda encounters Parameter Store access errors THEN the Lambda SHALL log the error and return a failure response
5. WHEN the Lambda uses REDCap credentials THEN the Lambda SHALL not log or expose the API token in any output

### Requirement 3

**User Story:** As a data engineer, I want the Lambda to validate and parse REDCap report data using Pydantic, so that I can ensure data quality and type safety.

#### Acceptance Criteria

1. WHEN the Lambda receives report data from REDCap THEN the Lambda SHALL validate that all rows have consistent field names and types
2. WHEN the Lambda processes report data THEN the Lambda SHALL create a dynamic Pydantic model based on the first row's schema
3. WHEN the Lambda validates report rows THEN the Lambda SHALL apply type coercion for common data types (strings, numbers, dates)
4. WHEN the Lambda encounters validation errors THEN the Lambda SHALL log the specific validation failures and continue processing valid rows
5. WHEN the Lambda completes validation THEN the Lambda SHALL return both valid records and a summary of validation errors

### Requirement 4

**User Story:** As a data engineer, I want the Lambda to support both overwrite and append modes for parquet files, so that I can choose the appropriate data update strategy.

#### Acceptance Criteria

1. WHEN the Lambda is invoked with overwrite mode THEN the Lambda SHALL replace the existing parquet file completely with new data
2. WHEN the Lambda is invoked with append mode THEN the Lambda SHALL add new data to the existing parquet file while preserving existing records
3. WHEN the Lambda operates in append mode and no existing file exists THEN the Lambda SHALL create a new parquet file
4. WHEN the Lambda operates in append mode with an existing file THEN the Lambda SHALL validate schema compatibility between existing and new data
5. WHEN the Lambda encounters schema incompatibility in append mode THEN the Lambda SHALL log the error and return a failure response
6. WHEN the Lambda completes file operations THEN the Lambda SHALL log the final record count and file size

### Requirement 5

**User Story:** As a data engineer, I want the Lambda to handle S3 operations efficiently using Polars, so that parquet files are optimized for analytical queries.

#### Acceptance Criteria

1. WHEN the Lambda writes parquet files THEN the Lambda SHALL use Polars DataFrame operations for optimal performance
2. WHEN the Lambda writes parquet files THEN the Lambda SHALL apply appropriate compression (Snappy) for storage efficiency
3. WHEN the Lambda writes parquet files THEN the Lambda SHALL preserve data types from the validated Pydantic models
4. WHEN the Lambda reads existing parquet files for append operations THEN the Lambda SHALL use Polars to read directly from S3
5. WHEN the Lambda completes S3 operations THEN the Lambda SHALL return the S3 URI of the final parquet file

### Requirement 6

**User Story:** As a data engineer, I want the Lambda to handle request parameters flexibly, so that I can specify different reports, locations, and operation modes.

#### Acceptance Criteria

1. WHEN the Lambda is invoked THEN the Lambda SHALL accept a report_id parameter as an integer
2. WHEN the Lambda is invoked THEN the Lambda SHALL accept an s3_bucket parameter specifying the target S3 bucket
3. WHEN the Lambda is invoked THEN the Lambda SHALL accept an s3_key parameter specifying the target file path and name
4. WHEN the Lambda is invoked THEN the Lambda SHALL accept a mode parameter with values "overwrite" or "append"
5. WHEN the Lambda is invoked THEN the Lambda SHALL accept optional api_url_param and api_token_param parameters for Parameter Store key names
6. WHEN the Lambda is invoked with missing required parameters THEN the Lambda SHALL return a validation error response
7. WHEN the Lambda is invoked with invalid parameter values THEN the Lambda SHALL return a validation error response with specific details

### Requirement 7

**User Story:** As a data engineer, I want the Lambda to handle errors gracefully, so that partial failures and edge cases are managed appropriately.

#### Acceptance Criteria

1. WHEN the Lambda encounters REDCap API connection errors THEN the Lambda SHALL retry up to 3 times with exponential backoff
2. WHEN the Lambda encounters REDCap API authentication errors THEN the Lambda SHALL log the error and return a failure response without retrying
3. WHEN the Lambda encounters empty report data THEN the Lambda SHALL log a warning and return a success response without creating or modifying files
4. WHEN the Lambda encounters S3 permission errors THEN the Lambda SHALL log the error and return a failure response
5. WHEN the Lambda encounters unexpected exceptions THEN the Lambda SHALL log the full error details and return an error response
6. WHEN the Lambda processes report data with some invalid rows THEN the Lambda SHALL include valid rows in the output and log invalid row details

### Requirement 8

**User Story:** As a data engineer, I want the Lambda to provide comprehensive logging and monitoring, so that I can track performance and troubleshoot issues.

#### Acceptance Criteria

1. WHEN the Lambda starts execution THEN the Lambda SHALL log the invocation parameters (excluding sensitive credentials)
2. WHEN the Lambda retrieves report data THEN the Lambda SHALL log the report ID, row count, and column count
3. WHEN the Lambda processes data validation THEN the Lambda SHALL log the count of valid and invalid records
4. WHEN the Lambda performs S3 operations THEN the Lambda SHALL log the S3 bucket, key, and operation type
5. WHEN the Lambda completes execution THEN the Lambda SHALL log the total execution time and final status
6. WHEN the Lambda logs messages THEN the Lambda SHALL use Lambda Powertools structured logging with appropriate log levels
7. WHEN the Lambda executes THEN the Lambda SHALL use Lambda Powertools Tracer for X-Ray tracing of external API calls
8. WHEN the Lambda processes data THEN the Lambda SHALL emit CloudWatch metrics for record counts, processing duration, and error rates

### Requirement 9

**User Story:** As a developer, I want to use the established dev container workflow, so that I can develop consistently with other NACC projects.

#### Acceptance Criteria

1. WHEN a developer starts development THEN the system SHALL use the dev container with `./bin/start-devcontainer.sh`
2. WHEN a developer runs commands THEN the system SHALL support both interactive shell via `./bin/terminal.sh` and single commands via `./bin/exec-in-devcontainer.sh`
3. WHEN a developer runs quality checks THEN the system SHALL support `./bin/exec-in-devcontainer.sh pants fix lint check test ::` workflow
4. WHEN a developer builds the Lambda THEN the system SHALL use `./bin/exec-in-devcontainer.sh pants package lambda/redcap_report_processor/src/python/redcap_report_lambda::`
5. WHEN a developer stops development THEN the system SHALL clean up with `./bin/stop-devcontainer.sh`

### Requirement 10

**User Story:** As a developer, I want the Lambda to be built using the Pants build system version 2.29, so that dependencies are managed consistently and builds are reproducible.

#### Acceptance Criteria

1. WHEN the Pants build is executed THEN the system SHALL resolve all Python dependencies including AWS Lambda Powertools, Pydantic, Polars, and redcap-api
2. WHEN the Pants build is executed THEN the system SHALL package the Lambda code and dependencies into a deployment artifact
3. WHEN the Pants build is executed THEN the system SHALL run all unit tests before creating the deployment artifact
4. WHEN the Pants build configuration is defined THEN the system SHALL specify Python 3.12 as the target interpreter
5. WHEN the Pants build configuration is defined THEN the system SHALL use Pants version 2.29

### Requirement 11

**User Story:** As a DevOps engineer, I want the Lambda to be deployed using Terraform, so that infrastructure is managed as code and reproducible.

#### Acceptance Criteria

1. WHEN Terraform is applied THEN the system SHALL create the Lambda function with Python 3.12 runtime
2. WHEN Terraform is applied THEN the system SHALL configure appropriate IAM roles with S3 read/write permissions and Parameter Store read permissions
3. WHEN Terraform is applied THEN the system SHALL set appropriate timeout and memory limits for the Lambda
4. WHEN Terraform is applied THEN the system SHALL configure environment variables for default Parameter Store parameter names and logging configuration
5. WHEN Terraform is applied THEN the system SHALL create CloudWatch log groups for Lambda execution logs

### Requirement 12

**User Story:** As a data engineer, I want the Lambda to leverage common code from the event log checkpoint lambda, so that shared functionality is reused and maintained consistently.

#### Acceptance Criteria

1. WHEN the Lambda needs S3 operations THEN the Lambda SHALL reuse S3 utility functions from common modules where applicable
2. WHEN the Lambda needs data validation patterns THEN the Lambda SHALL leverage Pydantic validation patterns from existing lambdas
3. WHEN the Lambda needs error handling THEN the Lambda SHALL use standardized error handling patterns from common modules
4. WHEN the Lambda needs logging configuration THEN the Lambda SHALL use Lambda Powertools configuration patterns from existing lambdas
5. WHEN the Lambda needs parquet operations THEN the Lambda SHALL reuse Polars DataFrame patterns from existing lambdas

### Requirement 13

**User Story:** As a data engineer, I want the Lambda to handle unknown report schemas dynamically, so that it can work with any REDCap report structure without prior configuration.

#### Acceptance Criteria

1. WHEN the Lambda receives report data with unknown column names THEN the Lambda SHALL dynamically create field definitions based on the first row
2. WHEN the Lambda encounters mixed data types in columns THEN the Lambda SHALL apply intelligent type inference (string as fallback)
3. WHEN the Lambda processes reports with optional fields THEN the Lambda SHALL handle null values appropriately in the parquet schema
4. WHEN the Lambda creates dynamic Pydantic models THEN the Lambda SHALL generate models that support the full range of REDCap field types
5. WHEN the Lambda validates dynamic schemas THEN the Lambda SHALL ensure all rows conform to the inferred schema structure

### Requirement 14

**User Story:** As a data engineer, I want the Lambda to support incremental data processing, so that I can efficiently update reports with only new or changed data.

#### Acceptance Criteria

1. WHEN the Lambda operates in append mode THEN the Lambda SHALL support adding only new records to existing parquet files
2. WHEN the Lambda appends data THEN the Lambda SHALL validate that new data schema matches existing file schema
3. WHEN the Lambda detects schema changes in append mode THEN the Lambda SHALL log the differences and fail with a descriptive error
4. WHEN the Lambda successfully appends data THEN the Lambda SHALL maintain proper parquet file structure and indexing
5. WHEN the Lambda completes append operations THEN the Lambda SHALL log the number of records added and the total record count

## Notes for Follow-up

**TODO: Research redcap-api package details once virtual environment is available**

The following items need investigation once the Pants lockfile generation completes and the redcap-api package can be imported:

1. **API Interface**: Examine the exact method signatures and parameters for the redcap-api package
   - How to initialize the REDCap client with URL and token
   - Method name and parameters for retrieving report data by ID
   - Response format and data structure returned by the API
   - Error handling patterns and exception types

2. **Data Format**: Understand the structure of data returned by REDCap reports
   - Whether data comes as list of dictionaries, pandas DataFrame, or other format
   - How missing values are represented
   - Data type handling for different REDCap field types (text, number, date, etc.)
   - Column naming conventions and any special characters to handle

3. **Authentication**: Verify the authentication mechanism
   - Whether the package handles token-based auth automatically
   - Any additional authentication parameters required
   - Connection timeout and retry configuration options

4. **Error Handling**: Document specific exception types
   - Network connection errors
   - Authentication failures
   - Invalid report ID errors
   - API rate limiting or quota errors

5. **Performance Considerations**: Investigate any performance-related features
   - Pagination support for large reports
   - Streaming capabilities for memory efficiency
   - Caching mechanisms if available

6. **Integration Patterns**: Determine best practices for integration
   - Whether to use async/await patterns
   - Connection pooling or reuse strategies
   - Logging integration with the package

This information will be used to refine the design document and ensure accurate implementation of the REDCap integration components.