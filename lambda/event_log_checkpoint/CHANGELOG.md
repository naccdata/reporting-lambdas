# Changelog

All notable changes to the Event Log Checkpoint Lambda will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

No unreleased changes.

## [1.1.0] - 2026-03-18

### Added

- Concurrent S3 file retrieval using `ThreadPoolExecutor` (default 50 threads) to handle 20k+ files within Lambda timeout
- Global timestamp cutoff: handler now scans existing checkpoint parquet files on startup and passes the earliest last-processed timestamp to the retriever, skipping already-processed files at fetch time
- Configurable `max_workers` parameter on `S3EventRetriever` for tuning concurrency

### Changed

- `S3EventRetriever.retrieve_and_validate_events()` now processes files concurrently instead of sequentially
- Lambda handler uses global `since_timestamp` from existing checkpoints to avoid re-fetching all files on incremental runs
- Exception handling in `_find_earliest_checkpoint_timestamp` narrowed from broad `Exception` to specific `CheckpointError`, `ClientError`, `OSError`

### Performance

- First run with 24,903 files: ~10 minutes (previously timed out at 15 minutes)
- Incremental runs with no new files: seconds (previously ~10 minutes re-fetching everything)

## [1.0.1] - 2026-03-18

### Fixed

- S3 pagination: replaced single `list_objects_v2` call with paginator to handle buckets with more than 1,000 objects
- File pattern regex updated to match new visit_date filename format (`YYYY-MM-DD`) instead of visit number

## [1.0.0] - 2026-02-04

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

This section maps semantic versions (git tags) to AWS Lambda versions for each environment.

### Production Environment

- **Semantic Version**: v1.1.0
- **Git Tag**: v1.1.0
- **AWS Lambda Version**: 7
- **Deployed**: 2026-03-18

### Staging Environment

- **Semantic Version**: Not yet deployed
- **Git Tag**: N/A
- **AWS Lambda Version**: N/A

### Development Environment

- **Semantic Version**: v1.0.0
- **Git Tag**: v1.0.0
- **AWS Lambda Version**: 14
- **Deployed**: 2026-02-04

---

## How to Use This Changelog

### For Developers

1. Add changes to the `[Unreleased]` section as you work
2. Use the categories: Added, Changed, Deprecated, Removed, Fixed, Security
3. Write clear, user-focused descriptions
4. Follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format

### For Releases

When ready to create a new release:

1. **Determine Version Number** using [Semantic Versioning](https://semver.org/):
   - **MAJOR** (x.0.0): Breaking changes (incompatible API changes)
   - **MINOR** (0.x.0): New features (backward compatible)
   - **PATCH** (0.0.x): Bug fixes (backward compatible)

2. **Update CHANGELOG.md**:
   - Move items from `[Unreleased]` to a new version section
   - Add version number and date: `## [1.1.0] - 2026-02-15`
   - Keep `[Unreleased]` section empty for future changes

3. **Create Git Tag**:
   ```bash
   git tag -a v1.1.0 -m "Release v1.1.0: Description of changes"
   git push origin v1.1.0
   ```

4. **Deploy to Environments**:
   ```bash
   # Deploy to dev first
   cd lambda/event_log_checkpoint
   terraform workspace select dev
   terraform apply -var-file=terraform.dev.tfvars
   
   # Then staging
   terraform workspace select staging
   terraform apply -var-file=terraform.staging.tfvars
   
   # Finally production
   terraform workspace select prod
   terraform apply -var-file=terraform.prod.tfvars
   ```

5. **Update Version Mapping**:
   - Note the AWS Lambda version number from deployment output
   - Update the "Version Mapping" section with:
     - Semantic version (e.g., v1.1.0)
     - Git tag (e.g., v1.1.0)
     - AWS Lambda version (from deployment)
     - Deployment date

### Semantic Versioning Examples

**MAJOR version (1.0.0 → 2.0.0)**: Breaking changes
```markdown
## [2.0.0] - 2026-03-01

### Changed
- **BREAKING**: Checkpoint key template now requires {environment} placeholder
- **BREAKING**: Removed support for flat directory structure
```

**MINOR version (1.0.0 → 1.1.0)**: New features
```markdown
## [1.1.0] - 2026-02-15

### Added
- Support for custom event filters via configuration
- New CloudWatch metrics for checkpoint size
```

**PATCH version (1.0.0 → 1.0.1)**: Bug fixes
```markdown
## [1.0.1] - 2026-02-10

### Fixed
- Timezone handling for events crossing daylight saving time
- Memory leak in parquet file processing
```

### Version Rollback

To rollback to a previous version:

```bash
# Checkout the version tag
git checkout v1.0.0

# Deploy to the environment
cd lambda/event_log_checkpoint
terraform workspace select dev
terraform apply -var-file=terraform.dev.tfvars

# Update Version Mapping to reflect rollback
```
