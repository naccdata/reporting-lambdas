# Implementation Plan: Checkpoint Filtering and Grouping

## Overview

This implementation plan breaks down the checkpoint filtering and grouping feature into discrete coding tasks. The approach follows a bottom-up strategy: implement core filtering and grouping components first, then integrate them into the Lambda handler, and finally add observability features (logging and metrics).

## Tasks

- [-] 1. Implement EventFilter component
  - [x] 1.1 Create event_filter.py module with EventFilter class
    - Implement `is_sandbox_project()` static method for pattern matching
    - Implement `filter_sandbox_events()` static method to filter event lists
    - Return both filtered events and count for metrics
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  
  - [ ]* 1.2 Write property test for sandbox filtering
    - **Property 1: Sandbox Event Filtering**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
    - Generate random events with various project_label patterns
    - Verify all filtered events do not start with "sandbox-"
  
  - [ ]* 1.3 Write unit tests for EventFilter
    - Test specific examples: "sandbox-form", "sandbox-dicom-leads", "ingest-form"
    - Test edge cases: empty string, None, special characters
    - Test empty event list
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 2. Implement EventGrouper component
  - [x] 2.1 Create event_grouper.py module with EventGrouper class
    - Define StudyDatatypeKey type alias
    - Implement `group_by_study_datatype()` static method
    - Use dictionary with (study, datatype) tuple keys
    - _Requirements: 2.1_
  
  - [ ]* 2.2 Write property test for event grouping
    - **Property 2: Event Grouping Completeness**
    - **Validates: Requirements 2.1**
    - Generate random events with various study-datatype combinations
    - Verify all events appear in exactly one group
    - Verify events in same group have identical study and datatype
    - Verify no events lost or duplicated
  
  - [ ]* 2.3 Write unit tests for EventGrouper
    - Test grouping with multiple study-datatype combinations
    - Test empty event list
    - Test single event
    - Test all events with same study-datatype
    - _Requirements: 2.1_

- [x] 3. Implement CheckpointKeyTemplate component
  - [x] 3.1 Create checkpoint_key_template.py module with CheckpointKeyTemplate class
    - Implement `__init__()` with template validation
    - Implement `validate()` method to check for required placeholders
    - Implement `generate_key()` method for template expansion
    - Raise ValueError for invalid templates with clear messages
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  
  - [ ]* 3.2 Write property test for template key generation
    - **Property 3: Template Key Generation**
    - **Validates: Requirements 2.2, 2.3, 2.4, 2.5, 2.6**
    - Generate random study and datatype strings
    - Verify template expansion produces correct format
    - Verify placeholders are replaced with actual values
  
  - [ ]* 3.3 Write property test for template validation
    - **Property 8: Template Validation**
    - **Validates: Requirements 4.1, 4.4**
    - Generate random template strings
    - Verify validation succeeds only when both placeholders present
    - Verify validation fails when placeholders missing
  
  - [ ]* 3.4 Write unit tests for CheckpointKeyTemplate
    - Test specific template: "checkpoints/{study}-{datatype}-events.parquet"
    - Test specific expansions: "adrc-form", "dvcid-form", "leads-dicom"
    - Test missing {study} placeholder
    - Test missing {datatype} placeholder
    - Test missing both placeholders
    - Test empty template
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement configuration model
  - [x] 5.1 Create config.py module with LambdaConfig class
    - Define Pydantic model with bucket, prefix, checkpoint_key_template fields
    - Implement `validate_template()` method
    - Add field descriptions and defaults
    - _Requirements: 4.1, 4.3, 4.4_
  
  - [ ]* 5.2 Write unit tests for LambdaConfig
    - Test valid configuration
    - Test missing CHECKPOINT_KEY_TEMPLATE
    - Test invalid template (missing placeholders)
    - Test default values
    - _Requirements: 4.1, 4.3, 4.4_

- [x] 6. Update Lambda handler for filtering and grouping
  - [x] 6.1 Modify lambda_handler function in lambda_function.py
    - Load configuration from environment variables
    - Validate configuration using LambdaConfig
    - Retrieve events using S3EventRetriever
    - Apply EventFilter to remove sandbox events
    - Apply EventGrouper to partition by study-datatype
    - Iterate over groups and process each independently
    - Handle partial failures gracefully (continue on error)
    - Return summary response with success/failure details
    - _Requirements: 1.1, 2.1, 3.1, 3.3, 3.4, 4.1_
  
  - [ ]* 6.2 Write integration tests for Lambda handler
    - Test end-to-end workflow with multiple study-datatype groups
    - Test filtering removes sandbox events
    - Test each group creates separate checkpoint
    - Test partial failure handling (one group fails, others succeed)
    - Test empty event list
    - Test all events filtered out
    - _Requirements: 1.1, 2.1, 3.1, 3.3, 3.4_

- [ ] 7. Implement checkpoint independence properties
  - [ ]* 7.1 Write property test for checkpoint operation independence
    - **Property 4: Checkpoint Operation Independence**
    - **Validates: Requirements 3.1, 3.3**
    - Generate random study-datatype combinations
    - Verify loading/saving one checkpoint doesn't affect others
    - Use mocked S3 operations to verify independence
  
  - [ ]* 7.2 Write property test for checkpoint timestamp independence
    - **Property 5: Checkpoint Timestamp Independence**
    - **Validates: Requirements 3.2**
    - Create checkpoints with different timestamps
    - Verify each returns its own timestamp
    - Verify timestamps don't cross-contaminate
  
  - [ ]* 7.3 Write property test for partial failure isolation
    - **Property 6: Partial Failure Isolation**
    - **Validates: Requirements 3.4**
    - Simulate save failure for one checkpoint
    - Verify other checkpoints still saved successfully
    - Verify error handling doesn't stop processing
  
  - [ ]* 7.4 Write property test for new checkpoint processing
    - **Property 7: New Checkpoint Processing**
    - **Validates: Requirements 3.5**
    - Test study-datatype combination with no existing checkpoint
    - Verify all events processed (no timestamp filtering)
    - Verify checkpoint created with all events

- [x] 8. Add structured logging
  - [x] 8.1 Add logging to EventFilter
    - Log filtered event count with structured context
    - Use Lambda Powertools Logger
    - _Requirements: 5.1_
  
  - [x] 8.2 Add logging to EventGrouper
    - Log group count and events per group with structured context
    - _Requirements: 5.2_
  
  - [x] 8.3 Add logging to Lambda handler
    - Log checkpoint save operations with study, datatype, key, count
    - Log checkpoint save failures with error details
    - Log processing summary with totals and group details
    - _Requirements: 5.3, 5.4, 5.5_
  
  - [ ]* 8.4 Write unit tests for logging
    - Verify log messages contain expected fields
    - Verify structured context is correct
    - Use log capture fixtures
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 9. Add CloudWatch metrics
  - [x] 9.1 Add metrics to Lambda handler
    - Emit EventsFiltered metric with count
    - Emit EventsProcessedByStudyDatatype with dimensions
    - Emit CheckpointsSaved metric with count
    - Emit CheckpointSaveFailures with dimensions
    - Use Lambda Powertools Metrics
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  
  - [ ]* 9.2 Write unit tests for metrics
    - Verify metric names are correct
    - Verify metric dimensions are correct
    - Verify metric values are correct
    - Use metrics capture fixtures
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 10. Update environment configuration
  - [x] 10.1 Update Terraform configuration
    - Add CHECKPOINT_KEY_TEMPLATE environment variable
    - Set default value: "checkpoints/{study}-{datatype}-events.parquet"
    - Update Lambda function configuration
    - _Requirements: 4.1, 4.2_
  
  - [x] 10.2 Update documentation
    - Document new environment variable in README
    - Document checkpoint file naming convention
    - Document filtering behavior
    - _Requirements: 1.1, 2.1, 4.1_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- The implementation follows dependency order: core components → integration → observability

