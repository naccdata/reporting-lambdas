# Requirements Document

## Introduction

Replace timestamp-based event filtering with content-based deduplication in the checkpoint lambda. Currently, the checkpoint lambda skips events whose timestamp is older than the checkpoint's last processed timestamp. This causes backfilled events with old timestamps to be silently dropped. The new approach deduplicates events based on their content identity so that any event not already present in the checkpoint is merged regardless of its timestamp age.

## Glossary

- **Checkpoint_Lambda**: The AWS Lambda function that processes event log files from S3 and merges them into per-study/datatype parquet checkpoint files.
- **S3_Event_Retriever**: The component responsible for listing, retrieving, and validating event log files from S3 storage.
- **Checkpoint**: A parquet file containing the accumulated set of deduplicated visit events for a specific study-datatype combination.
- **Checkpoint_Store**: The component responsible for reading and writing checkpoint parquet files to/from S3.
- **Visit_Event**: A validated event record representing a single action (submit, delete, pass-qc, not-pass-qc) for a participant visit.
- **Event_Identity**: The combination of fields that uniquely identifies a Visit_Event: (action, ptid, visit_date, timestamp, datatype, module, pipeline_adcid).
- **S3_LastModified_Filter**: The pre-filter that uses S3 object LastModified timestamps to avoid downloading files that were uploaded before the global cutoff timestamp.
- **Content_Deduplicator**: The component responsible for determining whether a Visit_Event already exists in a Checkpoint based on Event_Identity.

## Requirements

### Requirement 1: Define Event Identity

**User Story:** As a data engineer, I want a well-defined event identity based on content fields, so that duplicate events are detected regardless of when they were processed.

#### Acceptance Criteria

1. THE Content_Deduplicator SHALL identify a Visit_Event uniquely by the combination of: action, ptid, visit_date, timestamp, datatype, module, and pipeline_adcid, using case-sensitive exact-match comparison for all string fields.
2. WHEN two Visit_Events have identical values for all Event_Identity fields, THE Content_Deduplicator SHALL treat the two events as duplicates.
3. WHEN two Visit_Events differ in at least one Event_Identity field, THE Content_Deduplicator SHALL treat the two events as distinct.
4. WHEN the module field is null for both Visit_Events, THE Content_Deduplicator SHALL treat the module fields as matching for identity comparison purposes.
5. WHEN the module field is null for one Visit_Event and non-null for the other, THE Content_Deduplicator SHALL treat the module fields as not matching, and the two events as distinct.
6. IF a Visit_Event has a null value for any Event_Identity field other than module, THEN THE Content_Deduplicator SHALL treat that event as invalid and exclude it from deduplication processing.

### Requirement 2: Upsert Events at Merge Time

**User Story:** As a data engineer, I want events merged into a checkpoint using upsert semantics, so that new events are added, duplicate events are skipped, and corrected events replace their existing versions.

#### Acceptance Criteria

1. WHEN a new Visit_Event has an Event_Identity that does not exist in the current checkpoint, THE Checkpoint SHALL add the event.
2. WHEN a new Visit_Event has an Event_Identity that matches an existing event and all non-identity fields are also identical, THE Checkpoint SHALL skip the event as a true duplicate.
3. WHEN a new Visit_Event has an Event_Identity that matches an existing event but differs in one or more non-identity fields (study, project_label, center_label, gear_name, visit_number, packet), THE Checkpoint SHALL replace the existing event with the new event.
4. WHEN a batch of new events contains internal duplicates (same Event_Identity), THE Checkpoint SHALL retain only the last occurrence from the batch.
5. WHEN the Checkpoint merges a new batch, THE Checkpoint SHALL preserve all existing events whose Event_Identity does not appear in the new batch, ensuring no existing data is lost.
6. WHEN all new events in a batch are true duplicates of existing checkpoint events, THE Checkpoint SHALL remain unchanged.
7. WHEN the new event batch is empty, THE Checkpoint SHALL remain unchanged with no data loss.

### Requirement 3: Remove Per-Group Timestamp Filter

**User Story:** As a data engineer, I want the per-group timestamp filter removed from the lambda handler, so that backfilled events with old timestamps are not silently dropped.

#### Acceptance Criteria

1. THE Checkpoint_Lambda SHALL pass all events in a study-datatype group to the Checkpoint for merging without filtering by event timestamp.
2. WHEN a Visit_Event has a timestamp older than or equal to the checkpoint's last processed timestamp, THE Checkpoint_Lambda SHALL still include the event in the merge operation.
3. THE Checkpoint_Lambda SHALL not compare Visit_Event timestamps against the checkpoint's last processed timestamp for the purpose of including or excluding events from a merge operation.

### Requirement 4: Remove should_process_event Timestamp Filter

**User Story:** As a data engineer, I want the per-event timestamp filter in S3_Event_Retriever removed, so that retrieved events are not filtered out based on their event timestamp.

#### Acceptance Criteria

1. THE S3_Event_Retriever SHALL return all successfully validated Visit_Events from retrieved files without filtering by event timestamp.
2. WHEN a Visit_Event has a timestamp older than the since_timestamp, THE S3_Event_Retriever SHALL still include the event in the returned results.
3. THE S3_Event_Retriever SHALL remove the should_process_event method.

### Requirement 5: Retain S3 LastModified Pre-Filter

**User Story:** As a data engineer, I want the S3 LastModified pre-filter retained, so that the lambda avoids downloading files that are unlikely to contain new events.

#### Acceptance Criteria

1. WHILE a since_timestamp is configured, THE S3_Event_Retriever SHALL skip S3 objects whose LastModified timestamp is earlier than the since_timestamp.
2. THE S3_Event_Retriever SHALL use the S3 object LastModified timestamp only as a performance optimization to reduce file downloads, not as a correctness filter on event content.
3. WHEN an S3 object has a LastModified timestamp at or after the since_timestamp, THE S3_Event_Retriever SHALL download and validate the object regardless of the event timestamps contained within.
4. WHEN since_timestamp is not configured (null), THE S3_Event_Retriever SHALL download and validate all S3 objects without applying any LastModified filter.

### Requirement 6: Maintain Checkpoint Ordering

**User Story:** As a data engineer, I want the checkpoint to remain sorted by timestamp after merging, so that downstream consumers can rely on consistent event ordering.

#### Acceptance Criteria

1. WHEN new events are merged into a Checkpoint, THE Checkpoint SHALL sort all events by the timestamp field in ascending order.
2. WHEN two or more events share the same timestamp value, THE Checkpoint SHALL apply a stable secondary sort by ptid ascending and then by action ascending to produce a deterministic order.
3. WHEN backfilled events with old timestamps are added, THE Checkpoint SHALL place them in the correct ascending-timestamp position relative to existing events, applying the same tie-breaking rules.

### Requirement 7: Update Last Processed Timestamp Semantics

**User Story:** As a data engineer, I want the last processed timestamp to reflect the newest event in the checkpoint, so that the S3 LastModified pre-filter remains effective.

#### Acceptance Criteria

1. THE Checkpoint SHALL compute the last processed timestamp as the maximum timestamp across all events in the checkpoint, returning null when the checkpoint is empty.
2. WHEN backfilled events with old timestamps are merged, THE Checkpoint SHALL not reduce the last processed timestamp.
3. WHEN new events with timestamps newer than the current maximum are merged, THE Checkpoint SHALL update the last processed timestamp to the new maximum.
