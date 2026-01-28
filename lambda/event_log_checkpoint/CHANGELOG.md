# Changelog

All notable changes to the Event Log Checkpoint Lambda will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

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

- **Lambda Version**: Not yet deployed
- **Alias**: `prod`
- **Changelog Version**: N/A

### Staging Environment

- **Lambda Version**: Not yet deployed
- **Alias**: `staging`
- **Changelog Version**: N/A

### Development Environment

- **Lambda Version**: Not yet deployed
- **Alias**: `dev`
- **Changelog Version**: N/A

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
