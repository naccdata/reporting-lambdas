# Implementation Plan

## Overview

This implementation plan builds upon the existing project structure that has already been set up, including the dev container environment, Pants build system, and basic Lambda skeleton.

**Test-Driven Development (TDD) Approach**: This plan follows TDD methodology where tests are written first, then implementation code is written to make those tests pass. This ensures high code quality, better design, and comprehensive test coverage from the start.

## Development Workflow

All development should be done using the established dev container workflow:

1. **Start development session**: `./bin/start-devcontainer.sh`
2. **Run quality checks**: `./bin/exec-in-devcontainer.sh pants fix lint check test ::`
3. **Build Lambda**: `./bin/exec-in-devcontainer.sh pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda::`
4. **Run specific tests**: `./bin/exec-in-devcontainer.sh pants test lambda/event_log_checkpoint/test/python::`
5. **Run Terraform commands**: `./bin/exec-in-devcontainer.sh terraform apply` (from lambda directory)
6. **Stop development session**: `./bin/stop-devcontainer.sh`

**Important Notes**:
- Use `./bin/terminal.sh` only for interactive exploration and debugging
- For all pants and terraform commands, use `./bin/exec-in-devcontainer.sh <command>`
- Terraform is only available inside the dev container

## Tasks

- [x] 1. Set up project structure and Pants build configuration
  - ✅ Directory structure created following NACC patterns
  - ✅ Pants 2.29 configured with Python 3.12 interpreter  
  - ✅ Python dependencies defined (AWS Lambda Powertools, Pydantic, Polars, Boto3)
  - ✅ BUILD files created for Lambda packaging with layer separation
  - ✅ Dev container environment with helper scripts in `bin/` directory
  - _Requirements: 8.1, 8.2, 8.4, 8.5, 9.1, 9.2, 9.3, 9.4, 9.5_

- [-] 1.1 Update BUILD file with additional Lambda layers
  - Add `data_processing` layer for Pydantic and Polars dependencies
  - Note: AWS Powertools already includes boto3, so no separate aws_sdk layer needed
  - Ensure layers are properly separated by concern
  - _Requirements: 8.1, 8.2_

- [ ] 2. Write tests for VisitEvent model (TDD)
  - Create test file `lambda/event_log_checkpoint/test/python/test_models.py`
  - Write unit tests for valid event validation
  - Write unit tests for invalid field validation (ptid pattern, action enum, required fields)
  - Write unit tests for type conversion (pipeline_adcid to int)
  - Write unit tests for null preservation in optional fields
  - Write unit tests for date/timestamp parsing
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 3.1, 3.2, 3.3, 3.5_

- [ ] 2.1 Write property test for VisitEvent validation
  - **Property 5: Validation enforcement**
  - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8**

- [ ] 2.2 Write property test for type conversion
  - **Property 6: Type conversion correctness**
  - **Validates: Requirements 3.2**

- [ ] 2.3 Write property test for null preservation
  - **Property 7: Null preservation**
  - **Validates: Requirements 3.3**

- [ ] 2.4 Write property test for serialization round-trip
  - **Property 8: Serialization round-trip**
  - **Validates: Requirements 3.4**

- [ ] 2.5 Implement Pydantic VisitEvent model to pass tests
  - Create VisitEvent Pydantic model with all required and optional fields in `lambda/event_log_checkpoint/src/python/checkpoint_lambda/models.py`
  - Implement field validators for ptid pattern, action enum, date formats
  - Add custom validators for visit_date and timestamp parsing
  - Run tests to ensure all pass
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 3.1, 3.2, 3.3, 3.5_

- [ ] 3. Write tests for CheckpointReader component (TDD)
  - Create test file `lambda/event_log_checkpoint/test/python/test_checkpoint_reader.py`
  - Write unit tests for checkpoint_exists with existing and non-existing files
  - Write unit tests for read_checkpoint with valid parquet file
  - Write unit tests for get_last_processed_timestamp with various DataFrames
  - Mock S3 operations for isolated testing
  - _Requirements: 1.1, 7.4_

- [ ] 3.1 Implement CheckpointReader component to pass tests
  - Create CheckpointReader class in `lambda/event_log_checkpoint/src/python/checkpoint_lambda/checkpoint_reader.py`
  - Implement checkpoint_exists method to check for previous checkpoint
  - Implement read_checkpoint method to load parquet from S3
  - Implement get_last_processed_timestamp to extract max timestamp
  - Run tests to ensure all pass
  - _Requirements: 1.1, 7.4_

- [ ] 4. Write tests for S3EventRetriever component (TDD)
  - Create test file `lambda/event_log_checkpoint/test/python/test_s3_retriever.py`
  - Write unit tests for list_event_files with various S3 scenarios
  - Write unit tests for retrieve_event with valid/invalid JSON
  - Write unit tests for should_process_event with timestamp filtering
  - Write unit tests for error handling with S3 access errors
  - Mock S3 operations for isolated testing
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 6.1, 6.3_

- [ ] 4.1 Write property test for file pattern matching
  - **Property 1: File pattern matching correctness**
  - **Validates: Requirements 1.1**

- [ ] 4.2 Write property test for JSON retrieval
  - **Property 2: JSON retrieval completeness**
  - **Validates: Requirements 1.2**

- [ ] 4.3 Write property test for timestamp filtering
  - **Property 3: Timestamp filtering correctness**
  - **Validates: Requirements 1.1, 7.4**

- [ ] 4.4 Write property test for error resilience
  - **Property 4: Error resilience in retrieval**
  - **Validates: Requirements 1.3, 1.4**

- [ ] 4.5 Implement S3EventRetriever component to pass tests
  - Create S3EventRetriever class in `lambda/event_log_checkpoint/src/python/checkpoint_lambda/s3_retriever.py`
  - Implement list_event_files to list files matching log-{action}-{YYYYMMDD}.json pattern
  - Implement retrieve_event to fetch and parse JSON from S3
  - Implement should_process_event to filter by timestamp
  - Add error handling for S3 access errors with logging
  - Run tests to ensure all pass
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 6.1, 6.3_

- [ ] 5. Write tests for EventValidator component (TDD)
  - Create test file `lambda/event_log_checkpoint/test/python/test_validator.py`
  - Write unit tests for validate_event with valid events
  - Write unit tests for validation failures for missing fields
  - Write unit tests for validation failures for invalid field values
  - Write unit tests for error tracking and logging
  - Mock Pydantic validation for isolated testing
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 6.2, 10.3_

- [ ] 5.1 Implement EventValidator component to pass tests
  - Create EventValidator class in `lambda/event_log_checkpoint/src/python/checkpoint_lambda/validator.py`
  - Implement validate_event method using Pydantic VisitEvent model
  - Implement get_validation_errors to track all validation failures
  - Add structured logging for validation errors with file paths
  - Run tests to ensure all pass
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 6.2, 10.3_

- [ ] 6. Write tests for CheckpointMerger component (TDD)
  - Create test file `lambda/event_log_checkpoint/test/python/test_merger.py`
  - Write unit tests for events_to_dataframe conversion
  - Write unit tests for merge with None previous_df (first run)
  - Write unit tests for merge with existing previous_df
  - Write unit tests for timestamp ordering in merged DataFrame
  - Mock Polars operations for isolated testing
  - _Requirements: 4.1, 4.2, 7.1, 7.2, 7.3_

- [ ] 6.1 Write property test for incremental checkpoint correctness
  - **Property 0: Incremental checkpoint correctness**
  - **Validates: Requirements 4.1, 7.1**

- [ ] 6.2 Write property test for event evolution preservation
  - **Property 15: Event evolution preservation**
  - **Validates: Requirements 7.1, 7.3, 7.4**

- [ ] 6.3 Write property test for timestamp ordering
  - **Property 16: Timestamp ordering**
  - **Validates: Requirements 7.2, 7.4**

- [ ] 6.4 Write property test for event completeness analysis
  - **Property 17: Event completeness analysis**
  - **Validates: Requirements 7.5, 7.6**

- [ ] 6.5 Implement CheckpointMerger component to pass tests
  - Create CheckpointMerger class in `lambda/event_log_checkpoint/src/python/checkpoint_lambda/merger.py`
  - Implement events_to_dataframe to convert VisitEvent list to Polars DataFrame
  - Implement merge method to combine previous and new Polars DataFrames
  - Ensure merged DataFrame is sorted by timestamp
  - Handle case where previous_df is None (first run)
  - Run tests to ensure all pass
  - _Requirements: 4.1, 4.2, 7.1, 7.2, 7.3_

- [ ] 7. Write tests for ParquetWriter component (TDD)
  - Create test file `lambda/event_log_checkpoint/test/python/test_parquet_writer.py`
  - Write unit tests for writing DataFrame with various data types
  - Write unit tests for writing empty DataFrame
  - Write unit tests for S3 upload success
  - Write unit tests for compression verification
  - Mock S3 operations for isolated testing
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 7.1 Write property test for parquet round-trip
  - **Property 9: Parquet round-trip**
  - **Validates: Requirements 4.2**

- [ ] 7.2 Implement ParquetWriter component to pass tests
  - Create ParquetWriter class in `lambda/event_log_checkpoint/src/python/checkpoint_lambda/parquet_writer.py`
  - Use Polars native parquet writing with automatic schema inference
  - Implement write_events to convert DataFrame to parquet with Snappy compression
  - Upload parquet file to S3
  - Return S3 URI of written file
  - Run tests to ensure all pass
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Write tests for Lambda handler (TDD)
  - Create test file `lambda/event_log_checkpoint/test/python/test_lambda_function.py`
  - Write integration tests for end-to-end execution with sample event logs
  - Write unit tests for first run (no previous checkpoint)
  - Write unit tests for incremental run (with previous checkpoint)
  - Write unit tests for handling of mixed valid/invalid files
  - Write unit tests for error response format
  - Mock all component dependencies for isolated testing
  - _Requirements: 6.3, 6.4, 6.5, 10.1, 10.2, 10.4, 10.5, 10.6, 10.7_

- [ ] 9.1 Write property test for output path correctness
  - **Property 10: Output path correctness**
  - **Validates: Requirements 4.5**

- [ ] 9.2 Write property test for partial failure handling
  - **Property 14: Partial failure handling**
  - **Validates: Requirements 6.1, 6.2, 6.4**

- [ ] 9.3 Write property test for logging completeness
  - **Property 18: Logging completeness**
  - **Validates: Requirements 10.2, 10.3**

- [ ] 9.4 Implement Lambda handler to pass tests
  - Update existing `lambda/event_log_checkpoint/src/python/checkpoint_lambda/lambda_function.py`
  - Initialize Lambda Powertools Logger, Tracer, and Metrics
  - Parse Lambda event for source_bucket, checkpoint_bucket, checkpoint_key, prefix
  - Orchestrate pipeline: CheckpointReader → S3EventRetriever → EventValidator → CheckpointMerger → ParquetWriter
  - Implement error handling for S3 permissions and unexpected exceptions
  - Return response with statusCode, checkpoint_path, new_events_processed, total_events, events_failed, last_processed_timestamp, execution_time_ms
  - Run tests to ensure all pass
  - _Requirements: 6.3, 6.4, 6.5, 10.1, 10.2, 10.4, 10.5, 10.6, 10.7_

- [ ] 10. Write tests for query validation (TDD)
  - Create test file `lambda/event_log_checkpoint/test/python/test_query_validation.py`
  - Write tests to verify parquet file supports filtering by center_label
  - Write tests to verify counting events by action type
  - Write tests to verify filtering by packet type
  - Write tests to verify date range filtering
  - Write tests to verify grouping and counting by multiple fields
  - Write tests to verify temporal calculations (visit_date to timestamp differences)
  - Create sample parquet files for testing
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

- [ ] 10.1 Write property test for query filtering correctness
  - **Property 11: Query filtering correctness**
  - **Validates: Requirements 5.1, 5.2, 5.5, 5.6**

- [ ] 10.2 Write property test for temporal calculation support
  - **Property 12: Temporal calculation support**
  - **Validates: Requirements 5.3, 5.4**

- [ ] 10.3 Write property test for aggregation correctness
  - **Property 13: Aggregation correctness**
  - **Validates: Requirements 5.7, 5.8**

- [ ] 10.4 Implement query validation functionality to pass tests
  - Create utility functions for common query patterns
  - Ensure parquet schema supports all required query operations
  - Verify all tests pass with actual parquet files
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

- [ ] 11. Create Terraform infrastructure configuration with layer optimization
  - Create `lambda/event_log_checkpoint/main.tf` with smart layer management
  - Create `lambda/event_log_checkpoint/variables.tf` with layer reuse options
  - Create `lambda/event_log_checkpoint/outputs.tf` with layer ARN outputs
  - Implement data sources to check for existing layers
  - Configure conditional layer creation based on existence and content changes
  - Add support for external layer ARNs for cross-project reuse
  - Configure Lambda with Python 3.12 runtime, 3GB memory, 15 minute timeout
  - Create IAM role with S3 read/write permissions
  - Attach AWSLambdaBasicExecutionRole and AWSXRayDaemonWriteAccess policies
  - Configure environment variables (SOURCE_BUCKET, CHECKPOINT_BUCKET, CHECKPOINT_KEY, LOG_LEVEL, POWERTOOLS_SERVICE_NAME)
  - Enable X-Ray tracing
  - Create CloudWatch log group with 30 day retention
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 12. Build Lambda deployment packages with Pants
  - Build Lambda function: `pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:lambda`
  - Build Powertools layer: `pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:powertools`
  - Build data processing layer: `pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:data_processing`
  - Verify all packages are created with correct structure
  - Test that function code is separate from dependency layers
  - _Requirements: 8.1, 8.2, 8.3_

- [ ] 13. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
