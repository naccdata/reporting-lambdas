# Requirements Document

## Introduction

This document specifies the requirements for an AWS Lambda function that scrapes event log files from S3 storage within the NACC Flywheel instance and creates a checkpoint parquet file for analytical queries. The Lambda will process visit event logs stored in JSON format, validate them against the event log specification, aggregate them into a queryable dataset, and output a parquet file that supports monthly reporting queries.

The Lambda will be built using Python 3.12, AWS Lambda Powertools for observability and utilities, Pydantic for data validation and parsing, and Polars for DataFrame operations and parquet file generation. The project follows the established NACC development patterns using Pants build system 2.29 and dev container workflow.

## Glossary

- **Lambda**: The AWS Lambda function that performs event log scraping (implemented as `checkpoint_lambda`)
- **S3**: Amazon Simple Storage Service where event logs are stored
- **Event Log**: A JSON file containing a single visit event (submit, pass-qc, not-pass-qc, or delete)
- **ADCID**: Integer identifier for a pipeline/center
- **Visit Event**: A structured record of an action performed on a visit in the Flywheel system
- **Flywheel**: The NACC data management platform that generates event logs
- **QC**: Quality Control validation process for visits
- **Checkpoint File**: A parquet file containing aggregated event data for analytical queries
- **Parquet**: A columnar storage file format optimized for analytical queries
- **Dev Container**: Containerized development environment using devcontainer CLI

## Requirements

### Requirement 1

**User Story:** As a data engineer, I want the Lambda to retrieve event log files from S3, so that I can process visit events for downstream analytics.

#### Acceptance Criteria

1. WHEN the Lambda is invoked with an S3 bucket name and optional path prefix THEN the Lambda SHALL list all JSON files matching the pattern log-{action}-{YYYYMMDD}.json
2. WHEN the Lambda retrieves a file from S3 THEN the Lambda SHALL read the complete file content as JSON
3. WHEN the Lambda encounters an S3 access error THEN the Lambda SHALL log the error with the file path and continue processing remaining files
4. WHEN the Lambda completes file retrieval THEN the Lambda SHALL return a collection of all successfully retrieved event objects

### Requirement 2

**User Story:** As a data engineer, I want the Lambda to validate event log files against the specification, so that I can ensure data quality before downstream processing.

#### Acceptance Criteria

1. WHEN the Lambda reads an event log file THEN the Lambda SHALL validate the JSON structure against the event schema
2. WHEN an event log contains all required fields with valid types THEN the Lambda SHALL mark the event as valid
3. WHEN an event log is missing required fields THEN the Lambda SHALL mark the event as invalid and log the validation error
4. WHEN an event log contains invalid field values THEN the Lambda SHALL mark the event as invalid and log the specific validation failures
5. WHEN the Lambda validates the ptid field THEN the Lambda SHALL verify it matches the pattern for printable non-whitespace characters and has maximum length of 10 characters
6. WHEN the Lambda validates the action field THEN the Lambda SHALL verify it is one of: submit, pass-qc, not-pass-qc, or delete
7. WHEN the Lambda validates the study field THEN the Lambda SHALL verify it is a non-empty string with default value adrc
8. WHEN the Lambda validates the visit_date field THEN the Lambda SHALL verify it matches ISO date format YYYY-MM-DD as a string
9. WHEN the Lambda validates the timestamp field THEN the Lambda SHALL verify it is a valid ISO 8601 datetime string
10. WHEN the Lambda validates the datatype field THEN the Lambda SHALL verify it is one of: apoe, biomarker, dicom, enrollment, form, genetic-availability, gwas, imputation, or scan-analysis
11. WHEN the Lambda validates the module field for form datatype THEN the Lambda SHALL require module to be one of: UDS, FTLD, LBD, or MDS
12. WHEN the Lambda validates the module field for non-form datatype THEN the Lambda SHALL require module to be null
13. WHEN the Lambda validates the visit_number field THEN the Lambda SHALL treat it as optional and allow null values

### Requirement 3

**User Story:** As a data engineer, I want the Lambda to parse and extract structured data from event logs using Pydantic, so that I can work with validated typed objects rather than raw JSON.

#### Acceptance Criteria

1. WHEN the Lambda parses a valid event log THEN the Lambda SHALL create a Pydantic VisitEvent model with all fields properly typed and validated
2. WHEN the Lambda parses the pipeline_adcid field THEN the Lambda SHALL convert it to an integer type
3. WHEN the Lambda parses optional fields that are null THEN the Lambda SHALL preserve the null values in the structured object
4. WHEN the Lambda serializes a VisitEvent object to JSON THEN the Lambda SHALL produce output equivalent to the original parsed input
5. WHEN Pydantic validates an event log THEN the Lambda SHALL leverage Pydantic's built-in validation for field types and constraints

### Requirement 4

**User Story:** As a data engineer, I want the Lambda to aggregate event logs into a checkpoint parquet file, so that I can perform analytical queries for monthly reports.

#### Acceptance Criteria

1. WHEN the Lambda processes all event logs THEN the Lambda SHALL create a single parquet file containing all valid events
2. WHEN the Lambda writes the parquet file THEN the Lambda SHALL preserve all event fields with appropriate data types
3. WHEN the Lambda writes the parquet file THEN the Lambda SHALL store it in a designated S3 location
4. WHEN the Lambda writes the parquet file THEN the Lambda SHALL use columnar compression for efficient storage
5. WHEN the Lambda completes successfully THEN the Lambda SHALL output the S3 path of the created checkpoint file

### Requirement 5

**User Story:** As a data analyst, I want the checkpoint parquet file to support analytical queries for monthly reports, so that I can generate insights about visit processing and quality control.

#### Acceptance Criteria

1. WHEN querying the checkpoint file by center_label THEN the system SHALL return all events for that center efficiently
2. WHEN querying for visits with errors THEN the system SHALL support counting events where action equals not-pass-qc
3. WHEN calculating submission timing metrics THEN the system SHALL support computing time differences between visit_date and submit event timestamps
4. WHEN calculating QC timing metrics THEN the system SHALL support computing time differences between visit_date and pass-qc event timestamps
5. WHEN querying by packet type THEN the system SHALL support filtering and grouping events by the packet field
6. WHEN querying by date range THEN the system SHALL support filtering events where visit_date or timestamp falls within specified bounds
7. WHEN counting visit volumes THEN the system SHALL support grouping and counting events by module, packet, and action type
8. WHEN analyzing QC pass rates THEN the system SHALL support comparing counts of pass-qc versus not-pass-qc events

### Requirement 6

**User Story:** As a data engineer, I want the Lambda to handle errors gracefully, so that partial failures do not prevent processing of valid event logs.

#### Acceptance Criteria

1. WHEN the Lambda encounters a malformed JSON file THEN the Lambda SHALL log the error with the file path and continue processing remaining files
2. WHEN the Lambda encounters an invalid event schema THEN the Lambda SHALL log the validation errors and continue processing remaining files
3. WHEN the Lambda encounters an S3 permission error THEN the Lambda SHALL log the error and return a failure response
4. WHEN the Lambda completes with some failed files THEN the Lambda SHALL include both successful events in the parquet file and log a summary of failures
5. IF the Lambda encounters an unexpected exception THEN the Lambda SHALL log the full error details and return an error response

### Requirement 7

**User Story:** As a data engineer, I want the Lambda to handle duplicate and evolving events intelligently, so that the checkpoint file contains accurate and complete data for analysis.

#### Acceptance Criteria

1. WHEN the Lambda encounters multiple events for the same visit THEN the Lambda SHALL include all events in the checkpoint file with their respective timestamps
2. WHEN the Lambda processes events THEN the Lambda SHALL preserve event ordering based on timestamp values
3. WHEN the Lambda identifies events with identical content THEN the Lambda SHALL include all occurrences to maintain audit trail
4. WHEN the Lambda encounters events for the same visit with different field completeness THEN the Lambda SHALL preserve all versions to capture data evolution
5. WHEN querying for the latest event status THEN the system SHALL support identifying the most recent event per visit based on timestamp
6. WHEN analyzing event evolution THEN the system SHALL support tracking how event data becomes more complete over time

### Requirement 8

**User Story:** As a developer, I want to use the established dev container workflow, so that I can develop consistently with other NACC projects.

#### Acceptance Criteria

1. WHEN a developer starts development THEN the system SHALL use the dev container with `./bin/start-devcontainer.sh`
2. WHEN a developer runs commands THEN the system SHALL support both interactive shell via `./bin/terminal.sh` and single commands via `./bin/exec-in-devcontainer.sh`
3. WHEN a developer runs quality checks THEN the system SHALL support `./bin/exec-in-devcontainer.sh pants fix lint check test ::` workflow
4. WHEN a developer builds the Lambda THEN the system SHALL use `./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::`
5. WHEN a developer stops development THEN the system SHALL clean up with `./bin/stop-devcontainer.sh`

### Requirement 9

**User Story:** As a developer, I want the Lambda to be built using the Pants build system version 2.29, so that dependencies are managed consistently and builds are reproducible.

#### Acceptance Criteria

1. WHEN the Pants build is executed THEN the system SHALL resolve all Python dependencies including AWS Lambda Powertools, Pydantic, and Polars
2. WHEN the Pants build is executed THEN the system SHALL package the Lambda code and dependencies into a deployment artifact
3. WHEN the Pants build is executed THEN the system SHALL run all unit tests before creating the deployment artifact
4. WHEN the Pants build configuration is defined THEN the system SHALL specify Python 3.12 as the target interpreter
5. WHEN the Pants build configuration is defined THEN the system SHALL use Pants version 2.29

### Requirement 10

**User Story:** As a DevOps engineer, I want the Lambda to be deployed using Terraform, so that infrastructure is managed as code and reproducible.

#### Acceptance Criteria

1. WHEN Terraform is applied THEN the system SHALL create the Lambda function with Python 3.12 runtime
2. WHEN Terraform is applied THEN the system SHALL configure appropriate IAM roles with S3 read and write permissions
3. WHEN Terraform is applied THEN the system SHALL set appropriate timeout and memory limits for the Lambda
4. WHEN Terraform is applied THEN the system SHALL configure environment variables for source S3 bucket name and checkpoint output location
5. WHEN Terraform is applied THEN the system SHALL create CloudWatch log groups for Lambda execution logs

### Requirement 11

**User Story:** As a data engineer, I want the Lambda to log execution details using AWS Lambda Powertools, so that I can monitor performance and troubleshoot issues with structured logging and tracing.

#### Acceptance Criteria

1. WHEN the Lambda starts execution THEN the Lambda SHALL log the invocation parameters using Lambda Powertools Logger
2. WHEN the Lambda processes files THEN the Lambda SHALL log the count of files retrieved and processed with structured context
3. WHEN the Lambda encounters validation errors THEN the Lambda SHALL log the specific validation failures with file paths
4. WHEN the Lambda completes execution THEN the Lambda SHALL log the total execution time, event count, and checkpoint file size
5. WHEN the Lambda logs messages THEN the Lambda SHALL use Lambda Powertools structured logging with appropriate log levels
6. WHEN the Lambda executes THEN the Lambda SHALL use Lambda Powertools Tracer for X-Ray tracing of S3 operations
7. WHEN the Lambda processes events THEN the Lambda SHALL use Lambda Powertools Metrics to emit custom CloudWatch metrics for event counts and processing duration
