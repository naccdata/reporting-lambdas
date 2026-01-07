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

## Current Implementation Status

### ✅ Completed Components

All core components have been successfully implemented and tested:

1. **VisitEvent Model** - Fully implemented Pydantic model with comprehensive validation
2. **Checkpoint Class** - Complete implementation with event merging, timestamp handling, and utility methods
3. **CheckpointStore** - Full S3 read/write operations for parquet files
4. **S3EventRetriever** - Complete S3 event retrieval with validation and error handling
5. **Property-Based Tests** - Comprehensive property tests covering all major correctness properties
6. **Unit Tests** - Full unit test coverage for all components
7. **Build System** - Pants packaging configured for Lambda function and layers

### 🔄 Remaining Work

The main remaining tasks focus on:
- Lambda handler implementation (currently just a stub)
- Terraform infrastructure configuration
- Query validation functionality
- Final integration and deployment

## Tasks

- [x] 1. Set up project structure and Pants build configuration
  - ✅ Directory structure created following NACC patterns
  - ✅ Pants 2.29 configured with Python 3.12 interpreter  
  - ✅ Python dependencies defined (AWS Lambda Powertools, Pydantic, Polars, Boto3)
  - ✅ BUILD files created for Lambda packaging with layer separation
  - ✅ Dev container environment with helper scripts in `bin/` directory
  - _Requirements: 8.1, 8.2, 8.4, 8.5, 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 1.1 Update BUILD file with additional Lambda layers
  - Add `data_processing` layer for Pydantic and Polars dependencies
  - Note: AWS Powertools already includes boto3, so no separate aws_sdk layer needed
  - Ensure layers are properly separated by concern
  - _Requirements: 8.1, 8.2_

- [x] 2. Write unit tests for VisitEvent model
  - Create test file `lambda/event_log_checkpoint/test/python/test_models.py`
  - Write unit tests for valid event validation
  - Write unit tests for invalid field validation (ptid pattern, action enum, required fields)
  - Write unit tests for type conversion (pipeline_adcid to int)
  - Write unit tests for null preservation in optional fields
  - Write unit tests for date/timestamp parsing
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 3.1, 3.2, 3.3, 3.5_

- [x] 3. Write property test for VisitEvent validation
  - **Property 5: Validation enforcement**
  - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8**

- [x] 4. Write property test for type conversion
  - **Property 6: Type conversion correctness**
  - **Validates: Requirements 3.2**

- [x] 5. Write property test for null preservation
  - **Property 7: Null preservation**
  - **Validates: Requirements 3.3**

- [x] 6. Write property test for serialization round-trip
  - **Property 8: Serialization round-trip**
  - **Validates: Requirements 3.4**

- [x] 7. Implement Pydantic VisitEvent model to pass tests
  - Create VisitEvent Pydantic model with all required and optional fields in `lambda/event_log_checkpoint/src/python/checkpoint_lambda/models.py`
  - Implement field validators for ptid pattern, action enum, date formats
  - Add custom validators for visit_date and timestamp parsing
  - Run tests to ensure all pass
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 3.1, 3.2, 3.3, 3.5_

- [x] 8. Write unit tests for CheckpointStore component
  - ✅ Renamed test file from test_checkpoint_reader.py to test_checkpoint_store.py
  - ✅ Updated tests for exists() method with existing and non-existing files
  - ✅ Updated tests for load() method returning Checkpoint objects
  - ✅ Added tests for save() method writing checkpoints to S3
  - ✅ Use moto.server for realistic S3 operations with polars
  - _Requirements: 1.1, 4.1, 4.2, 4.5, 7.4_

- [x] 9. Implement CheckpointStore component to pass tests
  - ✅ Renamed CheckpointReader class to CheckpointStore in checkpoint_store.py
  - ✅ Implemented exists() method to check for previous checkpoint
  - ✅ Implemented load() method to load parquet from S3 and return Checkpoint object
  - ✅ Implemented save() method to write checkpoint as parquet to S3
  - ✅ Combined functionality of previous CheckpointReader + ParquetWriter
  - _Requirements: 1.1, 4.1, 4.2, 4.5, 7.4_

- [x] 10. Write unit tests for Checkpoint class
  - Create test file `lambda/event_log_checkpoint/test/python/test_checkpoint.py`
  - Write unit tests for from_events class method
  - Write unit tests for empty class method
  - Write unit tests for get_last_processed_timestamp with various DataFrames
  - Write unit tests for add_events method with merging logic (includes previous CheckpointMerger functionality)
  - Write unit tests for utility methods (get_event_count, is_empty, dataframe property)
  - _Requirements: 4.1, 4.2, 7.1, 7.2, 7.3, 7.4_

- [x] 11. Write property test for incremental checkpoint correctness
  - **Property 0: Incremental checkpoint correctness**
  - **Validates: Requirements 4.1, 7.1**

- [x] 12. Write property test for event evolution preservation
  - **Property 15: Event evolution preservation**
  - **Validates: Requirements 7.1, 7.3, 7.4**

- [x] 13. Write property test for timestamp ordering
  - **Property 16: Timestamp ordering**
  - **Validates: Requirements 7.2, 7.4**

- [x] 14. Write property test for event completeness analysis
  - **Property 17: Event completeness analysis**
  - **Validates: Requirements 7.5, 7.6**

- [x] 15. Implement Checkpoint class to pass tests
  - Create Checkpoint class in `lambda/event_log_checkpoint/src/python/checkpoint_lambda/checkpoint.py`
  - Implement from_events class method to create checkpoint from VisitEvent list
  - Implement empty class method to create empty checkpoint
  - Implement get_last_processed_timestamp to extract max timestamp
  - Implement add_events method to merge new events with existing (includes CheckpointMerger logic)
  - Implement utility methods (get_event_count, is_empty, dataframe property)
  - Run tests to ensure all pass
  - _Requirements: 4.1, 4.2, 7.1, 7.2, 7.3, 7.4_

- [x] 16. Write unit tests for S3EventRetriever component
  - Create test file `lambda/event_log_checkpoint/test/python/test_s3_retriever.py`
  - Write unit tests for list_event_files with various S3 scenarios
  - Write unit tests for retrieve_event with valid/invalid JSON
  - Write unit tests for should_process_event with timestamp filtering
  - Write unit tests for retrieve_and_validate_events with direct VisitEvent validation
  - Write unit tests for error handling with S3 access errors
  - Use moto.server for realistic S3 operations with boto3
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 6.1, 6.2, 6.3, 10.3_

- [x] 17. Write property test for file pattern matching
  - **Property 1: File pattern matching correctness**
  - **Validates: Requirements 1.1**

- [x] 18. Write property test for JSON retrieval
  - **Property 2: JSON retrieval completeness**
  - **Validates: Requirements 1.2**

- [x] 19. Write property test for timestamp filtering
  - **Property 3: Timestamp filtering correctness**
  - **Validates: Requirements 1.1, 7.4**

- [x] 20. Write property test for error resilience
  - **Property 4: Error resilience in retrieval**
  - **Validates: Requirements 1.3, 1.4**

- [x] 21. Implement S3EventRetriever component to pass tests
  - Create S3EventRetriever class in `lambda/event_log_checkpoint/src/python/checkpoint_lambda/s3_retriever.py`
  - Implement list_event_files to list files matching log-{action}-{timestamp}-{adcid}-{project}-{ptid}-{visitnum}.json pattern (with backward compatibility for legacy log-{action}-{YYYYMMDD}.json pattern)
  - Implement retrieve_event to fetch and parse JSON from S3
  - Implement should_process_event to filter by timestamp
  - Implement retrieve_and_validate_events to handle complete pipeline with direct VisitEvent validation
  - Add error handling for S3 access errors with logging
  - Run tests to ensure all pass
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 6.1, 6.2, 6.3, 10.3_
- [x] 22. Write unit tests for Lambda handler basic structure
  - Create test file `lambda/event_log_checkpoint/test/python/test_lambda_function.py`
  - Write test for Lambda event parsing (source_bucket, checkpoint_bucket, checkpoint_key, prefix)
  - Write test for basic response format structure
  - Use moto.server for realistic S3 operations in component dependencies
  - _Requirements: 10.1, 10.4_

- [x] 23. Implement Lambda handler basic structure to pass tests
  - Update existing `lambda/event_log_checkpoint/src/python/checkpoint_lambda/lambda_function.py`
  - Initialize Lambda Powertools Logger, Tracer, and Metrics
  - Parse Lambda event for source_bucket, checkpoint_bucket, checkpoint_key, prefix
  - Return basic response structure with statusCode
  - Run tests to ensure all pass
  - _Requirements: 10.1, 10.4_

- [x] 24. Write unit tests for Lambda handler first run scenario
  - Add tests for first run (no previous checkpoint exists)
  - Test CheckpointStore.exists() returns False
  - Test CheckpointStore.load() creates empty checkpoint
  - Use moto.server for realistic S3 operations with S3EventRetriever and Checkpoint components
  - _Requirements: 6.3, 10.5_

- [x] 25. Implement Lambda handler first run logic to pass tests
  - Add checkpoint loading logic with CheckpointStore.exists() check
  - Handle empty checkpoint creation for first run
  - Update response to include checkpoint status
  - Run tests to ensure all pass
  - _Requirements: 6.3, 10.5_

- [x] 26. Update CheckpointStore tests to use moto.server (vertical slice)
  - ✅ Updated test_checkpoint_store.py to use moto.server fixture instead of direct S3 mocking
  - ✅ Created moto_server pytest fixture for CheckpointStore tests
  - ✅ Configured polars to use moto.server endpoint for S3 operations in CheckpointStore tests
  - ✅ Verified all existing CheckpointStore tests pass with realistic S3 operations
  - ✅ Ensured polars can read/write parquet files via mocked S3 server
  - ✅ Tested that polars operations work with actual S3 URIs (s3://bucket/key format)
  - ✅ Updated CheckpointStore implementation to handle additional exception types (OSError, FileNotFoundError) from polars S3 operations
  - _Requirements: 4.1, 4.2, 4.5, 7.4_

- [ ] 26b. Update S3EventRetriever tests to use moto.server (after 26 succeeds)
  - Update test_s3_retriever.py to use moto.server for realistic boto3 S3 operations
  - Extend moto_server fixture pattern from CheckpointStore tests
  - Verify all existing S3EventRetriever tests pass with realistic S3 operations
  - Test real S3 error conditions (AccessDenied, NoSuchKey, etc.)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 6.1, 6.2, 6.3_

- [ ] 26c. Update Lambda handler tests to use moto.server (after 26b succeeds)
  - Update test_lambda_function.py to use moto.server for end-to-end testing
  - Create shared moto_server pytest fixture for all test files
  - Test complete workflow with realistic S3 operations
  - Verify end-to-end integration with mocked S3 server
  - _Requirements: 10.1, 10.4, 10.5_

- [ ] 29. Write unit tests for Lambda handler incremental run scenario
  - Add tests for incremental run (previous checkpoint exists)
  - Test CheckpointStore.load() returns existing checkpoint
  - Test event retrieval with timestamp filtering
  - Use moto.server for realistic S3 operations in event processing pipeline
  - _Requirements: 6.4, 10.6_

- [ ] 30. Implement Lambda handler incremental run logic to pass tests
  - Add event retrieval with S3EventRetriever.retrieve_and_validate_events()
  - Add checkpoint merging with Checkpoint.add_events()
  - Add checkpoint saving with CheckpointStore.save()
  - Update response to include processing metrics
  - Run tests to ensure all pass
  - _Requirements: 6.4, 10.6_

- [ ] 31. Write unit tests for Lambda handler error handling
  - Add tests for S3 permission errors
  - Add tests for invalid JSON handling
  - Add tests for mixed valid/invalid files
  - Test error response format
  - _Requirements: 6.1, 6.2, 6.5, 10.7_

- [ ] 32. Implement Lambda handler error handling to pass tests
  - Add try-catch blocks for S3 permissions and unexpected exceptions
  - Add partial failure handling for mixed valid/invalid files
  - Return appropriate error responses with statusCode and error details
  - Run tests to ensure all pass
  - _Requirements: 6.1, 6.2, 6.5, 10.7_

- [ ] 33. Write unit tests for Lambda handler response completeness
  - Add tests for complete response format with all required fields
  - Test response includes: checkpoint_path, new_events_processed, total_events, events_failed, last_processed_timestamp, execution_time_ms
  - Test integration with all components working together
  - _Requirements: 10.2, 10.3_

- [ ] 34. Implement Lambda handler response completeness to pass tests
  - Add execution timing measurement
  - Add comprehensive response building with all metrics
  - Add final integration of all pipeline components
  - Run tests to ensure all pass
  - _Requirements: 10.2, 10.3_

- [ ] 35. Write property test for parquet round-trip
  - **Property 9: Parquet round-trip**
  - **Validates: Requirements 4.2**

- [ ] 36. Write property test for output path correctness
  - **Property 10: Output path correctness**
  - **Validates: Requirements 4.5**

- [ ] 37. Write property test for partial failure handling
  - **Property 14: Partial failure handling**
  - **Validates: Requirements 6.1, 6.2, 6.4**

- [ ] 38. Write property test for logging completeness
  - **Property 18: Logging completeness**
  - **Validates: Requirements 10.2, 10.3**

- [ ] 39. Implement Lambda handler property-based test fixes
  - Run property tests and fix any issues found
  - Ensure all property tests pass
  - _Requirements: 4.2, 4.5, 6.1, 6.2, 6.4, 10.2, 10.3_

- [ ] 40. Write unit tests for query validation basic functionality
  - Create test file `lambda/event_log_checkpoint/test/python/test_query_validation.py`
  - Write tests to verify parquet file supports filtering by center_label
  - Write tests to verify counting events by action type
  - Create sample parquet files for testing
  - _Requirements: 5.1, 5.2_

- [ ] 41. Implement query validation basic functionality to pass tests
  - Create utility functions for center_label filtering
  - Create utility functions for action type counting
  - Ensure parquet schema supports basic filtering operations
  - Run tests to ensure all pass
  - _Requirements: 5.1, 5.2_

- [ ] 42. Write unit tests for query validation advanced filtering
  - Add tests to verify filtering by packet type
  - Add tests to verify date range filtering
  - Add tests to verify grouping and counting by multiple fields
  - _Requirements: 5.3, 5.5, 5.6_

- [ ] 43. Implement query validation advanced filtering to pass tests
  - Add packet type filtering functionality
  - Add date range filtering functionality
  - Add multi-field grouping and counting functionality
  - Run tests to ensure all pass
  - _Requirements: 5.3, 5.5, 5.6_

- [ ] 44. Write unit tests for query validation temporal calculations
  - Add tests to verify temporal calculations (visit_date to timestamp differences)
  - Add tests for complex temporal query patterns
  - _Requirements: 5.4, 5.7, 5.8_

- [ ] 45. Implement query validation temporal calculations to pass tests
  - Add temporal calculation utility functions
  - Ensure parquet schema supports all temporal operations
  - Verify all tests pass with actual parquet files
  - Run tests to ensure all pass
  - _Requirements: 5.4, 5.7, 5.8_

- [ ] 46. Write property test for query filtering correctness
  - **Property 11: Query filtering correctness**
  - **Validates: Requirements 5.1, 5.2, 5.5, 5.6**

- [ ] 47. Write property test for temporal calculation support
  - **Property 12: Temporal calculation support**
  - **Validates: Requirements 5.3, 5.4**

- [ ] 48. Write property test for aggregation correctness
  - **Property 13: Aggregation correctness**
  - **Validates: Requirements 5.7, 5.8**

- [ ] 49. Implement query validation property-based test fixes
  - Run property tests and fix any issues found
  - Ensure all property tests pass for query validation
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

- [ ] 50. Create Terraform infrastructure configuration with layer optimization
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

- [ ] 51. Build Lambda deployment packages with Pants
  - Build Lambda function: `pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:lambda`
  - Build Powertools layer: `pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:powertools`
  - Build data processing layer: `pants package lambda/event_log_checkpoint/src/python/checkpoint_lambda:data_processing`
  - Verify all packages are created with correct structure
  - Test that function code is separate from dependency layers
  - _Requirements: 8.1, 8.2, 8.3_

- [ ] 52. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
