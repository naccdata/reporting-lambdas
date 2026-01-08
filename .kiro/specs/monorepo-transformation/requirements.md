# Requirements Document

## Introduction

Transform the current single-lambda repository into a proper monorepo structure for hosting multiple reporting lambdas that pull data from different sources and create parquet tables for analytical use. The repository should support shared code, consistent build patterns, and scalable organization for multiple data processing lambdas.

## Glossary

- **Monorepo**: A single repository containing multiple related projects (lambdas) with shared tooling and dependencies
- **Reporting_Lambda**: An AWS Lambda function that extracts data from sources and creates parquet files for analytics
- **Shared_Code**: Common utilities, models, and libraries used across multiple lambdas
- **Data_Source**: External systems from which lambdas extract data (APIs, databases, S3 buckets, etc.)
- **Parquet_Table**: Columnar data format optimized for analytical queries
- **Lambda_Template**: Standardized project structure and configuration for new lambdas

## Requirements

### Requirement 1: Establish Common Code Structure

**User Story:** As a developer, I want to create common utilities and models that can be reused across multiple reporting lambdas, so that I can avoid code duplication and maintain consistency.

#### Acceptance Criteria

1. THE Repository SHALL create a `common/` directory at the root level following the established pattern from context/docs/project-structure.md
2. THE Repository SHALL organize common code into logical modules (utils, models, aws_helpers, data_processing, etc.)
3. WHEN a lambda needs common functionality, THE Build_System SHALL automatically include common dependencies
4. THE Common_Code SHALL be versioned and testable independently with proper BUILD files
5. THE Repository SHALL provide common Pydantic models for data validation and parquet processing patterns

### Requirement 2: Standardize Lambda Organization

**User Story:** As a developer, I want a consistent directory structure for all reporting lambdas following the established patterns, so that I can easily navigate and understand any lambda in the repository.

#### Acceptance Criteria

1. THE Repository SHALL maintain the existing `lambda/` directory as the root for all lambda functions
2. WHEN creating a new lambda, THE Repository SHALL follow the pattern `lambda/{lambda-name}/` with standardized subdirectories
3. THE Lambda_Structure SHALL include: `src/python/{lambda_name}_lambda/`, `test/python/`, and Terraform files at lambda root
4. THE Repository SHALL provide a lambda template based on context/docs/lambda-patterns.md for consistent project initialization
5. THE Build_System SHALL support building all lambdas with a single command using Pants patterns

### Requirement 3: Update Documentation Structure

**User Story:** As a developer, I want clear documentation that explains the monorepo structure and how to work with multiple reporting lambdas, so that I can efficiently develop and maintain data processing functions.

#### Acceptance Criteria

1. THE Repository SHALL update the README.md to reflect the monorepo purpose for reporting lambdas and data processing
2. THE Documentation SHALL provide clear instructions for creating new reporting lambdas using the established patterns
3. THE Repository SHALL document common code usage patterns and best practices for data processing workflows
4. THE Documentation SHALL include examples of common reporting lambda patterns (S3 processing, data transformation, parquet generation)
5. THE Repository SHALL maintain individual README files for each lambda with specific data source and output details

### Requirement 4: Enhance Build System Configuration

**User Story:** As a developer, I want the build system to efficiently handle multiple lambdas with common dependencies, so that I can build, test, and deploy lambdas independently or collectively.

#### Acceptance Criteria

1. THE Build_System SHALL support building individual lambdas independently using Pants targets
2. THE Build_System SHALL support building all lambdas with a single command (pants package lambda::)
3. WHEN common code changes, THE Build_System SHALL identify affected lambdas for testing through dependency tracking
4. THE Repository SHALL configure Pants to handle common code dependencies automatically using proper BUILD file patterns
5. THE Build_System SHALL support lambda-specific and common testing strategies with separate test targets

### Requirement 5: Create Lambda Development Template

**User Story:** As a developer, I want a standardized template for creating new reporting lambdas, so that I can quickly bootstrap new data processing functions with consistent structure and tooling.

#### Acceptance Criteria

1. THE Repository SHALL provide a lambda template with standard directory structure following context/docs patterns
2. THE Template SHALL include boilerplate code for common reporting patterns (S3 processing, data validation, parquet generation)
3. THE Template SHALL include standard Terraform configuration for lambda deployment with proper IAM roles and monitoring
4. THE Template SHALL include example tests (unit and property-based) following established testing patterns
5. THE Template SHALL integrate with common code and follow established BUILD file patterns for dependencies

### Requirement 6: Maintain Backward Compatibility

**User Story:** As a developer, I want the existing event_log_checkpoint lambda to continue working without changes, so that current functionality is preserved during the monorepo transformation.

#### Acceptance Criteria

1. THE Repository SHALL preserve the existing `lambda/event_log_checkpoint/` structure
2. THE Existing_Lambda SHALL continue to build and deploy without modification
3. THE Repository SHALL maintain all existing build targets and commands
4. THE Transformation SHALL not break existing CI/CD pipelines
5. THE Repository SHALL preserve all existing documentation for the event_log_checkpoint lambda

### Requirement 7: Establish Common Infrastructure Patterns

**User Story:** As a developer, I want standardized Terraform modules and infrastructure patterns for reporting lambdas, so that I can consistently deploy lambdas with proper monitoring and permissions.

#### Acceptance Criteria

1. THE Repository SHALL create common Terraform modules for standard lambda infrastructure patterns
2. THE Common_Modules SHALL include standard IAM roles for S3 access, CloudWatch logging, and X-Ray tracing
3. THE Repository SHALL provide templates for common S3 bucket access patterns and data processing permissions
4. THE Repository SHALL standardize environment variable patterns for data sources and output destinations
5. THE Common_Infrastructure SHALL support both individual lambda deployments and batch deployments

### Requirement 8: Update Development Workflow

**User Story:** As a developer, I want clear development workflows for working with multiple lambdas in the monorepo, so that I can efficiently develop, test, and deploy reporting functions.

#### Acceptance Criteria

1. THE Repository SHALL document workflows for developing individual lambdas
2. THE Repository SHALL document workflows for making changes that affect multiple lambdas
3. THE Development_Workflow SHALL integrate with the existing dev container setup
4. THE Repository SHALL provide commands for testing all lambdas or specific subsets
5. THE Workflow SHALL support both local development and CI/CD integration