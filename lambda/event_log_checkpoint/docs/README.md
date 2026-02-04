# Event Log Checkpoint Lambda Documentation

This directory contains comprehensive documentation for the Event Log Checkpoint Lambda function.

## Documentation Index

### Getting Started

- **[../README.md](../README.md)** - Main overview and quick start guide for the Lambda function

### Architecture & Design

- **[BACKEND-ARCHITECTURE.md](BACKEND-ARCHITECTURE.md)** - Detailed architecture documentation including component design, data flow, and technical decisions

### Data Specifications

- **[PARQUET-FILE-SPECIFICATION.md](PARQUET-FILE-SPECIFICATION.md)** - Complete specification of the checkpoint parquet file format, schema, and usage examples

### Infrastructure & Deployment

- **[TERRAFORM.md](TERRAFORM.md)** - Terraform infrastructure documentation and deployment guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Step-by-step deployment procedures and workflows
- **[ENVIRONMENTS.md](ENVIRONMENTS.md)** - Environment-specific configuration (dev, staging, production)
- **[VERSIONING.md](VERSIONING.md)** - Semantic versioning strategy and release process
- **[EVENT-LOG-ARCHIVAL.md](EVENT-LOG-ARCHIVAL.md)** - S3 lifecycle policies for event log management

### Operations

- **[PRODUCTION-READINESS.md](PRODUCTION-READINESS.md)** - Production readiness checklist, monitoring, and operational considerations

## Quick Links by Topic

### For Developers

1. Start with [../README.md](../README.md) for an overview
2. Review [BACKEND-ARCHITECTURE.md](BACKEND-ARCHITECTURE.md) to understand the design
3. Check [PARQUET-FILE-SPECIFICATION.md](PARQUET-FILE-SPECIFICATION.md) for data format details

### For DevOps/Infrastructure

1. Review [TERRAFORM.md](TERRAFORM.md) for infrastructure setup
2. Check [ENVIRONMENTS.md](ENVIRONMENTS.md) for environment configuration
3. Read [VERSIONING.md](VERSIONING.md) for release process
4. Review [DEPLOYMENT.md](DEPLOYMENT.md) for deployment procedures
5. Check [PRODUCTION-READINESS.md](PRODUCTION-READINESS.md) for deployment checklist

### For Data Analysts

1. Read [PARQUET-FILE-SPECIFICATION.md](PARQUET-FILE-SPECIFICATION.md) for schema and query examples
2. Check [../README.md](../README.md) for data flow overview

## Related Documentation

### Project-Level Documentation

Located in `context/docs/`:
- **[../../context/docs/event-log-format.md](../../context/docs/event-log-format.md)** - Source event log format specification
- **[../../context/docs/lambda-patterns.md](../../context/docs/lambda-patterns.md)** - Common Lambda patterns and best practices
- **[../../context/docs/project-structure.md](../../context/docs/project-structure.md)** - Overall project structure

### Common Code Documentation

Located in `docs/`:
- **[../../docs/aws-helpers-usage.md](../../docs/aws-helpers-usage.md)** - AWS helper utilities
- **[../../docs/data-processing-usage.md](../../docs/data-processing-usage.md)** - Data processing utilities
- **[../../docs/models-usage.md](../../docs/models-usage.md)** - Common data models

## Contributing

When adding new documentation:
1. Place it in this `docs/` directory
2. Update this README with a link and description
3. Use clear, descriptive filenames in UPPERCASE-WITH-DASHES.md format
4. Include cross-references to related documentation
