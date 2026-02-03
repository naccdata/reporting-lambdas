# Requirements Document

## Introduction

This specification defines enhancements to the Event Log Checkpoint Lambda to support filtering sandbox projects and grouping checkpoint data by datatype. Currently, the Lambda processes all event logs and creates a single checkpoint file. This enhancement will filter out sandbox project events and create separate checkpoint files for each datatype (form, dicom, etc.), enabling more efficient analytical queries and better data organization.

## Glossary

- **Event_Log_Checkpoint_Lambda**: AWS Lambda function that processes event log files from S3 and creates checkpoint files in Parquet format
- **Checkpoint_File**: Parquet file containing processed event data, used for analytical queries
- **Sandbox_Project**: Project with label matching pattern "sandbox-*" (e.g., "sandbox-form", "sandbox-dicom"), used by centers to practice submission of a datatype without submitting live data
- **Datatype**: Category of event data (form, dicom, apoe, biomarker, etc.) specified in the event's datatype field
- **Project_Label**: Flywheel project label field in event data (e.g., "ingest-form", "sandbox-form-leads")
- **VisitEvent**: Pydantic model representing a validated event log entry
- **CheckpointStore**: Component responsible for reading and writing checkpoint files to S3
- **S3EventRetriever**: Component responsible for retrieving and validating event log files from S3

## Requirements

### Requirement 1: Filter Sandbox Projects

**User Story:** As a data analyst, I want sandbox project events excluded from checkpoint files, so that production analytical queries only include live data and not practice submissions.

#### Acceptance Criteria

1. WHEN processing event logs, THE Event_Log_Checkpoint_Lambda SHALL exclude events where project_label matches pattern "sandbox-*"
2. WHEN an event has project_label "sandbox-form", THE Event_Log_Checkpoint_Lambda SHALL not include it in any checkpoint file
3. WHEN an event has project_label "sandbox-dicom-leads", THE Event_Log_Checkpoint_Lambda SHALL not include it in any checkpoint file
4. WHEN an event has project_label "ingest-form", THE Event_Log_Checkpoint_Lambda SHALL include it in checkpoint processing
5. WHEN filtering is applied, THE Event_Log_Checkpoint_Lambda SHALL log the count of filtered events for monitoring

### Requirement 2: Group Checkpoints by Study and Datatype

**User Story:** As a data analyst, I want separate checkpoint files for each study and datatype combination, so that I can query specific data categories efficiently without loading unrelated data.

#### Acceptance Criteria

1. WHEN processing events, THE Event_Log_Checkpoint_Lambda SHALL group events by their study and datatype field values
2. WHEN events contain study "adrc" and datatype "form", THE Event_Log_Checkpoint_Lambda SHALL write them to a checkpoint file named "adrc-form-events.parquet"
3. WHEN events contain study "adrc" and datatype "dicom", THE Event_Log_Checkpoint_Lambda SHALL write them to a checkpoint file named "adrc-dicom-events.parquet"
4. WHEN events contain study "dvcid" and datatype "form", THE Event_Log_Checkpoint_Lambda SHALL write them to a checkpoint file named "dvcid-form-events.parquet"
5. WHEN events contain study "leads" and datatype "dicom", THE Event_Log_Checkpoint_Lambda SHALL write them to a checkpoint file named "leads-dicom-events.parquet"
6. WHEN events contain any valid study and datatype combination, THE Event_Log_Checkpoint_Lambda SHALL write them to a checkpoint file named "{study}-{datatype}-events.parquet"

### Requirement 3: Independent Checkpoint Management

**User Story:** As a system operator, I want each study-datatype checkpoint to track its own processing state independently, so that issues with one checkpoint don't affect others.

#### Acceptance Criteria

1. WHEN loading checkpoints, THE Event_Log_Checkpoint_Lambda SHALL load each study-datatype checkpoint independently
2. WHEN determining last processed timestamp, THE Event_Log_Checkpoint_Lambda SHALL use the timestamp from the specific study-datatype checkpoint file
3. WHEN saving checkpoints, THE Event_Log_Checkpoint_Lambda SHALL save each study-datatype checkpoint independently
4. WHEN one study-datatype checkpoint fails to save, THE Event_Log_Checkpoint_Lambda SHALL continue processing and saving other study-datatype checkpoints
5. WHEN a study-datatype combination has no existing checkpoint, THE Event_Log_Checkpoint_Lambda SHALL process all historical events for that study-datatype combination

### Requirement 4: Configuration via Template

**User Story:** As a system operator, I want to configure checkpoint file paths using a template with placeholders, so that I can control the S3 path structure without changing code.

#### Acceptance Criteria

1. WHEN CHECKPOINT_KEY_TEMPLATE environment variable is set with "{study}" and "{datatype}" placeholders, THE Event_Log_Checkpoint_Lambda SHALL create separate checkpoint files per study-datatype combination
2. WHEN CHECKPOINT_KEY_TEMPLATE is "checkpoints/{study}-{datatype}-events.parquet", THE Event_Log_Checkpoint_Lambda SHALL generate paths like "checkpoints/adrc-form-events.parquet"
3. WHEN CHECKPOINT_KEY_TEMPLATE is not set, THE Event_Log_Checkpoint_Lambda SHALL return a validation error
4. WHEN CHECKPOINT_KEY_TEMPLATE is set but missing required placeholders, THE Event_Log_Checkpoint_Lambda SHALL return a validation error

### Requirement 5: Structured Logging for Filtering and Grouping

**User Story:** As a system operator, I want detailed logs about filtering and grouping operations, so that I can monitor and troubleshoot the Lambda's behavior.

#### Acceptance Criteria

1. WHEN filtering sandbox events, THE Event_Log_Checkpoint_Lambda SHALL log the count of filtered events with structured context
2. WHEN grouping events by study and datatype, THE Event_Log_Checkpoint_Lambda SHALL log the count of events per study-datatype combination with structured context
3. WHEN saving study-datatype checkpoints, THE Event_Log_Checkpoint_Lambda SHALL log each checkpoint path and event count with structured context
4. WHEN a study-datatype checkpoint save fails, THE Event_Log_Checkpoint_Lambda SHALL log the error with study and datatype context
5. WHEN processing completes, THE Event_Log_Checkpoint_Lambda SHALL log a summary including total events processed, filtered count, and checkpoint counts per study-datatype combination

### Requirement 6: CloudWatch Metrics for Filtering and Grouping

**User Story:** As a system operator, I want CloudWatch metrics for filtering and grouping operations, so that I can monitor system health and create alarms.

#### Acceptance Criteria

1. WHEN filtering sandbox events, THE Event_Log_Checkpoint_Lambda SHALL emit a CloudWatch metric "EventsFiltered" with the count of filtered events
2. WHEN grouping events by study and datatype, THE Event_Log_Checkpoint_Lambda SHALL emit CloudWatch metrics "EventsProcessedByStudyDatatype" with study and datatype dimensions
3. WHEN saving checkpoints, THE Event_Log_Checkpoint_Lambda SHALL emit CloudWatch metrics "CheckpointsSaved" with count of successfully saved checkpoints
4. WHEN checkpoint save fails, THE Event_Log_Checkpoint_Lambda SHALL emit CloudWatch metric "CheckpointSaveFailures" with study and datatype dimensions
