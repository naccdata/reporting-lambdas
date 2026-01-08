# Implementation Plan: Monorepo Transformation

## Overview

This implementation plan transforms the current single-lambda repository into a comprehensive monorepo for hosting multiple reporting lambdas. The approach preserves existing functionality while establishing scalable patterns for future lambda development.

## Tasks

- [x] 1. Create common code directory structure
  - Create `common/` directory with subdirectories for `src/python/` and `test/python/`
  - Create module subdirectories: `data_processing/`, `aws_helpers/`, `models/`, `utils/`
  - Run `pants tailor ::` to automatically generate BUILD files
  - _Requirements: 1.1, 1.2, 1.4_

- [ ]* 1.1 Write property test for common directory structure
  - **Property 1: Repository structure consistency**
  - **Validates: Requirements 1.1, 1.2**

- [x] 2. Implement common code modules
  - [x] 2.1 Create data_processing module with ParquetWriter and DataValidator classes
    - Implement ParquetWriter with compression and schema validation
    - Implement DataValidator for common validation patterns
    - _Requirements: 1.5_

  - [x] 2.2 Create aws_helpers module with S3Manager and LambdaUtils classes
    - Implement S3Manager with retry logic and error handling
    - Implement LambdaUtils with decorators and event parsing
    - _Requirements: 1.5_

  - [x] 2.3 Create models module with common Pydantic models
    - Implement ReportingEvent, DataSourceConfig, and ProcessingMetrics models
    - _Requirements: 1.5_

  - [x] 2.4 Create utils module with general utilities
    - Implement error handling utilities and common helper functions
    - _Requirements: 1.5_

- [ ]* 2.5 Write property tests for common code modules
  - **Property 2: Common code dependency resolution**
  - **Validates: Requirements 1.3**

- [x] 3. Create lambda template structure
  - Create `templates/lambda-template/` directory with standardized structure
  - Include `src/python/template_lambda/`, `test/python/`, and Terraform files
  - Run `pants tailor ::` to generate BUILD files after creating Python files
  - _Requirements: 2.2, 2.3, 5.1_

- [x] 4. Implement lambda template content
  - [x] 4.1 Create template lambda handler with standard error handling
    - Implement lambda_function.py with common patterns
    - Include reporting processor separation and logging
    - _Requirements: 5.2_

  - [x] 4.2 Create template Terraform configuration
    - Include main.tf, variables.tf, outputs.tf with IAM roles and monitoring
    - _Requirements: 5.3_

  - [x] 4.3 Run pants tailor to generate BUILD files
    - Use `pants tailor ::` to automatically create proper BUILD files
    - Verify dependency declarations for common code are correct
    - _Requirements: 5.5_

  - [x] 4.4 Create template test files
    - Include unit test and property test examples
    - _Requirements: 5.4_

- [ ]* 4.5 Write property test for lambda template structure
  - **Property 1: Repository structure consistency**
  - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

- [x] 5. Update build system configuration
  - Update pants.toml to include common code source roots
  - Run `pants tailor ::` to ensure all BUILD files are properly generated
  - Ensure build system supports individual and batch lambda building
  - _Requirements: 4.1, 4.2, 4.4_

- [ ]* 5.1 Write property test for build system functionality
  - **Property 2: Common code dependency resolution**
  - **Property 5: Build system lambda independence**
  - **Validates: Requirements 4.1, 4.3**

- [x] 6. Create Terraform modules for common infrastructure
  - Create `terraform/modules/` directory structure
  - Implement modules for IAM roles, monitoring, and lambda infrastructure
  - _Requirements: 7.1, 7.2, 7.3_

- [ ]* 6.1 Write property test for environment variable consistency
  - **Property 3: Environment variable naming consistency**
  - **Validates: Requirements 7.4**

- [ ] 7. Update documentation
  - [ ] 7.1 Update main README.md for monorepo structure
    - Document monorepo purpose and organization
    - Include lambda development workflows
    - _Requirements: 3.1, 3.2_

  - [ ] 7.2 Document common code usage patterns
    - Create documentation for each common module
    - Include best practices and examples
    - _Requirements: 3.3, 3.4_

  - [ ] 7.3 Create lambda template README
    - Document template usage and customization
    - _Requirements: 2.4_

  - [ ] 7.4 Document development workflows
    - Include individual lambda and multi-lambda workflows
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ]* 7.5 Write property test for lambda README completeness
  - **Property 4: Lambda README completeness**
  - **Validates: Requirements 3.5**

- [ ] 8. Checkpoint - Verify existing lambda preservation
  - Ensure `lambda/event_log_checkpoint/` structure is unchanged
  - Verify existing build targets still work
  - Test that existing lambda builds and deploys successfully
  - _Requirements: 6.1, 6.2, 6.3, 6.5_

- [ ] 9. Validate build system integration
  - Test building individual lambdas independently
  - Test building all lambdas with single command
  - Verify common code dependency resolution
  - _Requirements: 4.1, 4.2, 4.5_

- [ ]* 9.1 Write integration tests for build system
  - Test that `pants package lambda::` builds all lambdas
  - Test that individual lambda builds work independently
  - **Validates: Requirements 4.2, 4.5**

- [ ] 10. Final validation and testing
  - Run all property tests to validate correctness properties
  - Verify all examples work as documented
  - Test development workflows with dev container
  - _Requirements: All_

- [ ] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The existing `event_log_checkpoint` lambda must remain fully functional throughout the transformation