# Versioning Guide

This document describes the versioning strategy for the Event Log Checkpoint Lambda.

## Overview

We use [Semantic Versioning](https://semver.org/) (SemVer) with git tags to track releases. Each release is tagged in git and mapped to AWS Lambda versions per environment.

## Semantic Versioning

Version format: `MAJOR.MINOR.PATCH` (e.g., `1.2.3`)

- **MAJOR**: Breaking changes (incompatible API changes)
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### When to Bump Versions

**MAJOR (x.0.0)** - Breaking Changes:
- Changes to checkpoint file structure that require migration
- Removal of environment variables or configuration options
- Changes to Lambda handler signature or event format
- Breaking changes to Terraform module interface

**MINOR (0.x.0)** - New Features:
- New event filtering capabilities
- Additional CloudWatch metrics
- New configuration options (backward compatible)
- Performance improvements
- New documentation

**PATCH (0.0.x)** - Bug Fixes:
- Bug fixes that don't change functionality
- Documentation corrections
- Dependency updates (security patches)
- Test improvements

## Release Process

### 1. Prepare the Release

```bash
# Ensure you're on main branch and up to date
git checkout main
git pull origin main

# Run tests to ensure everything works
./bin/start-devcontainer.sh
./bin/exec-in-devcontainer.sh pants test ::
./bin/exec-in-devcontainer.sh pants lint ::
./bin/exec-in-devcontainer.sh pants check ::
```

### 2. Update CHANGELOG.md

Move items from `[Unreleased]` to a new version section:

```markdown
## [Unreleased]

No unreleased changes.

## [1.1.0] - 2026-02-15

### Added
- New event filtering capabilities
- Additional CloudWatch metrics

### Fixed
- Timezone handling bug
```

### 3. Commit Changelog

```bash
git add lambda/event_log_checkpoint/CHANGELOG.md
git commit -m "Prepare release v1.1.0"
git push origin main
```

### 4. Create Git Tag

```bash
# Create annotated tag
git tag -a v1.1.0 -m "Release v1.1.0: Event filtering improvements"

# Push tag to remote
git push origin v1.1.0
```

### 5. Deploy to Environments

Deploy in order: dev → staging → prod

```bash
cd lambda/event_log_checkpoint

# Development
terraform workspace select dev
terraform apply -var-file=terraform.dev.tfvars
# Note the Lambda version from output

# Staging
terraform workspace select staging
terraform apply -var-file=terraform.staging.tfvars
# Note the Lambda version from output

# Production
terraform workspace select prod
terraform apply -var-file=terraform.prod.tfvars
# Note the Lambda version from output
```

### 6. Update Version Mapping

Update the "Version Mapping" section in CHANGELOG.md:

```markdown
## Version Mapping

### Production Environment
- **Semantic Version**: v1.1.0
- **Git Tag**: v1.1.0
- **AWS Lambda Version**: 5
- **Deployed**: 2026-02-15

### Staging Environment
- **Semantic Version**: v1.1.0
- **Git Tag**: v1.1.0
- **AWS Lambda Version**: 8
- **Deployed**: 2026-02-15

### Development Environment
- **Semantic Version**: v1.1.0
- **Git Tag**: v1.1.0
- **AWS Lambda Version**: 15
- **Deployed**: 2026-02-15
```

### 7. Commit Version Mapping

```bash
git add lambda/event_log_checkpoint/CHANGELOG.md
git commit -m "Update version mapping for v1.1.0 deployment"
git push origin main
```

## Version Rollback

To rollback to a previous version:

### 1. Checkout Previous Version

```bash
# List available tags
git tag -l

# Checkout the version you want to rollback to
git checkout v1.0.0
```

### 2. Deploy Previous Version

```bash
cd lambda/event_log_checkpoint

# Deploy to the affected environment
terraform workspace select prod
terraform apply -var-file=terraform.prod.tfvars
```

### 3. Document Rollback

Update CHANGELOG.md to document the rollback:

```markdown
## [1.1.1] - 2026-02-16

### Fixed
- Rolled back to v1.0.0 due to critical bug in v1.1.0
- Issue: Event filtering was too aggressive, dropping valid events
```

## Hotfix Process

For urgent production fixes:

### 1. Create Hotfix Branch

```bash
# Create branch from production tag
git checkout v1.0.0
git checkout -b hotfix/1.0.1
```

### 2. Make Fix and Test

```bash
# Make your changes
# Run tests
./bin/exec-in-devcontainer.sh pants test ::
```

### 3. Update CHANGELOG

```markdown
## [1.0.1] - 2026-02-10

### Fixed
- Critical bug in timezone handling causing data loss
```

### 4. Commit, Tag, and Deploy

```bash
git add .
git commit -m "Fix timezone handling bug"
git tag -a v1.0.1 -m "Hotfix v1.0.1: Fix timezone bug"
git push origin hotfix/1.0.1
git push origin v1.0.1

# Deploy to production
cd lambda/event_log_checkpoint
terraform workspace select prod
terraform apply -var-file=terraform.prod.tfvars
```

### 5. Merge Back to Main

```bash
git checkout main
git merge hotfix/1.0.1
git push origin main
```

## Best Practices

1. **Always tag after merging to main** - Don't tag feature branches
2. **Use annotated tags** - Include a message describing the release
3. **Test before tagging** - Ensure all tests pass
4. **Deploy dev first** - Test in dev before staging/prod
5. **Document breaking changes** - Clearly mark breaking changes in CHANGELOG
6. **Keep CHANGELOG current** - Update as you work, not just at release time
7. **One version per release** - Don't skip versions
8. **Semantic versioning is a contract** - Follow it strictly

## Version History

See [CHANGELOG.md](../CHANGELOG.md) for complete version history.

## References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Git Tagging](https://git-scm.com/book/en/v2/Git-Basics-Tagging)
