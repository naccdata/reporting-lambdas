# Changelog

All notable changes to the Event Log Checkpoint Lambda will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

No unreleased changes.

## [2026-02-04] - Event Filtering, Grouping, and Nested Directory Structure

### Added

- **Event Filtering**: Automatic filtering of sandbox events (e.g., `sandbox-form`, `ingest-form`)
- **Event Grouping**: Events grouped by study and datatype for separate checkpoint files
- **Configurable Templates**: Checkpoint key template with `{study}` and `{datatype}` placeholders
- **Configuration Module**: New `config.py` for centralized Lambda configuration with validation
- **Event Filter Module**: `event_filter.py` for sandbox event detection and filtering
- **Event Grouper Module**: `event_grouper.py` for study-datatype grouping logic
- **Template Module**: `checkpoint_key_template.py` for checkpoint path generation
- **Comprehensive Documentation**:
  - `docs/BACKEND-ARCHITECTURE.md` - Terraform state management
  - `docs/DEPLOYMENT.md` - Deployment procedures
  - `docs/ENVIRONMENTS.md` - Multi-environment setup
  - `docs/EVENT-LOG-ARCHIVAL.md` - S3 lifecycle policies
  - `docs/PARQUET-FILE-SPECIFICATION.md` - Parquet schema details
  - `docs/PRODUCTION-READINESS.md` - Production deployment checklist
  - `docs/TERRAFORM.md` - Terraform configuration guide
- **S3 Lifecycle Management**: Automatic archival of event logs to Glacier/Deep Archive
- **Backend Setup Script**: `scripts/backend-setup.sh` for Terraform state bucket creation
- **Dev Container**: Dockerfile and devcontainer.json for consistent development environment
- **AWS X-Ray**: Distributed tracing support added to dependencies

### Changed

- **BREAKING**: Checkpoint key template structure changed to nested directories
  - Dev: `dev/checkpoints/{study}/{datatype}/events.parquet`
  - Prod: `prod/checkpoints/{study}/{datatype}/events.parquet`
  - Staging: `staging/checkpoints/{study}/{datatype}/events.parquet`
- **Lambda Handler Refactored**: Complete rewrite to support filtering and grouping
- **Module Validation**: Relaxed to accept any string (not just predefined list)
- **Documentation Reorganized**: Moved from single TERRAFORM.md to structured `docs/` directory
- **README Updated**: Reflects new filtering and grouping capabilities
- **Dependencies Updated**: Added aws-xray-sdk for tracing
- Checkpoint file structure changed from flat to nested directories for Athena compatibility
- Documentation updated to show checkpoint template flexibility with multiple valid patterns

### Fixed

- Test suite updated to use correct checkpoint paths with new template structure
- Removed hardcoded checkpoint paths that would break with different templates
- Terraform environment variables aligned with Lambda configuration

### Migration Notes

- Old checkpoint files (flat structure) should be manually removed from S3
- New checkpoints will be created in nested directory structure
- Each study/datatype combination gets its own directory (Athena requirement)
- Sandbox events are now automatically filtered out of checkpoints

## [Initial Release]

### Added

- Multi-environment support (dev, staging, production)
- Environment-specific Terraform variable files
- S3 backend configuration for Terraform state management
- Lambda versioning and aliases per environment
- Timezone-aware datetime handling throughout checkpoint pipeline
- UTC timezone validation for all timestamps
- Parquet file specification documentation

### Changed

- Module name validation relaxed to accept any string (not just predefined list)
- All AWS resources now include environment suffix for isolation
- Lambda layer names include environment suffix
- IAM roles and policies include environment suffix

### Fixed

- Timezone handling for datetime fields in events and parquet files
- Parquet file loading now ensures UTC timezone on timestamp column

## Version Mapping

This section maps AWS Lambda versions to changelog entries for each environment.

### Production Environment

- **Lambda Version**: 2
- **Alias**: `prod`
- **Deployed**: 2026-02-04
- **Changelog Version**: [2026-02-04] - Event Filtering, Grouping, and Nested Directory Structure

### Staging Environment

- **Lambda Version**: Not yet deployed
- **Alias**: `staging`
- **Changelog Version**: N/A

### Development Environment

- **Lambda Version**: 14
- **Alias**: `dev`
- **Deployed**: 2026-02-04
- **Changelog Version**: [2026-02-04] - Event Filtering, Grouping, and Nested Directory Structure

---

## How to Use This Changelog

### For Developers

1. Add changes to the `[Unreleased]` section as you work
2. Use the categories: Added, Changed, Deprecated, Removed, Fixed, Security
3. Write clear, user-focused descriptions

### For Deployments

1. When deploying to an environment, note the AWS Lambda version number
2. Update the "Version Mapping" section with the Lambda version and date
3. Move unreleased changes to a new version section if this is a significant release

### Example Entry Format

```markdown
## [Unreleased]

### Added
- New feature description

### Fixed
- Bug fix description

## Deployment - 2024-01-28

### Production
- Lambda Version: 5
- Changes: Initial production deployment

### Staging  
- Lambda Version: 8
- Changes: Testing new timezone handling
```
