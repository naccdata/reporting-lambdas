# Implementation Plan: Content-Based Deduplication

## Overview

Replace timestamp-based event filtering with content-based deduplication in the checkpoint lambda. The implementation builds up the core upsert logic first, then removes the old timestamp filters, then adds property-based and integration tests.

## Tasks

- [x] 1. Implement content-based upsert in Checkpoint
  - [x] 1.1 Add IDENTITY_COLUMNS constant and update add_events method
    - Add `IDENTITY_COLUMNS` list constant to `checkpoint.py` with the seven identity fields: action, ptid, visit_date, timestamp, datatype, module, pipeline_adcid
    - Rewrite `Checkpoint.add_events` to perform content-based upsert:
      - Deduplicate new batch internally with `unique(subset=IDENTITY_COLUMNS, keep="last")`
      - Use anti-join with `join_nulls=True` to find existing events not in the new batch
      - Concatenate preserved existing events with deduplicated new events
      - Sort by (timestamp, ptid, action) for deterministic ordering
    - Handle empty batch case (return clone of current checkpoint)
    - Handle empty checkpoint case (skip anti-join, use new batch directly)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 6.1, 6.2, 6.3, 7.1, 7.2, 7.3_

  - [ ]* 1.2 Write property test: Identity Key Correctness
    - **Property 1: Identity Key Correctness**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
    - For any two VisitEvents, the upsert logic treats them as duplicates iff all identity fields are equal (including null-equality for module)

  - [x] 1.3 Write property test: Upsert Completeness
    - **Property 2: Upsert Completeness**
    - **Validates: Requirements 2.1, 2.5**
    - For any checkpoint and batch, after merging: every new event whose identity does not exist in the original appears in the result, and every existing event whose identity is not in the new batch is preserved

  - [ ]* 1.4 Write property test: Idempotence of Duplicate Merge
    - **Property 3: Idempotence of Duplicate Merge**
    - **Validates: Requirements 2.2, 2.6**
    - Merging a batch composed entirely of exact copies of existing events produces identical content to the original checkpoint

  - [x] 1.5 Write property test: Correction Replacement
    - **Property 4: Correction Replacement**
    - **Validates: Requirements 2.3**
    - For an event E in the checkpoint and a new event E' with the same identity but different non-identity fields, after merging E' appears and E does not

  - [ ]* 1.6 Write property test: Internal Batch Dedup (Last Wins)
    - **Property 5: Internal Batch Dedup (Last Wins)**
    - **Validates: Requirements 2.4**
    - For a batch with multiple events sharing the same identity, only the last occurrence from the original batch order is present in the result

  - [x] 1.7 Write property test: Sort Invariant
    - **Property 6: Sort Invariant**
    - **Validates: Requirements 6.1, 6.2, 6.3**
    - For any checkpoint after merging, all events are sorted ascending by (timestamp, ptid, action)

  - [ ]* 1.8 Write property test: Last Processed Timestamp is Maximum
    - **Property 7: Last Processed Timestamp is Maximum**
    - **Validates: Requirements 7.1, 7.2, 7.3**
    - For any non-empty checkpoint, get_last_processed_timestamp() returns the maximum timestamp; for empty, returns None; value never decreases after merge

- [x] 2. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Remove timestamp filters
  - [x] 3.1 Remove should_process_event from S3EventRetriever
    - Delete the `should_process_event` method from `s3_retriever.py`
    - Update `_fetch_and_validate` to return validated VisitEvent directly without calling `should_process_event`
    - Remove the "skipped" result path from `_fetch_and_validate`
    - Update `retrieve_and_validate_events` to remove handling of the "skipped" dict result
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 3.2 Remove per-group timestamp filter from lambda handler
    - In `lambda_function.py`, remove the per-group block that filters events by `timestamp > since_timestamp`
    - Pass all group events directly to `checkpoint.add_events(events)`
    - Remove the `since_timestamp` variable and the conditional list comprehension
    - Keep the `_find_earliest_checkpoint_timestamp` function (used for S3 LastModified pre-filter)
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 3.3 Write unit tests for filter removal
    - Verify `S3EventRetriever` no longer has `should_process_event` method
    - Verify `_fetch_and_validate` returns VisitEvent for valid events without filtering
    - Verify S3 LastModified pre-filter in `list_event_files` is retained and functioning
    - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 5.4_

- [x] 4. Filter removal checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Integration tests for backfill scenarios
  - [x] 5.1 Write integration test for backfilled events
    - Test end-to-end lambda invocation with events that have old timestamps
    - Verify backfilled events appear in the checkpoint after processing
    - Use mocked S3 (moto) for realistic integration testing
    - _Requirements: 3.1, 3.2, 2.1_

  - [ ]* 5.2 Write integration test for duplicate event handling
    - Test lambda invocation with duplicate events (same identity + same non-identity fields)
    - Verify checkpoint size does not grow when all events are duplicates
    - _Requirements: 2.2, 2.6_

  - [x] 5.3 Write integration test for correction events
    - Test lambda invocation with correction events (same identity, different non-identity fields)
    - Verify old versions are replaced by new versions in the checkpoint
    - _Requirements: 2.3_

- [x] 6. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All property tests use Hypothesis with `@settings(max_examples=100)` and the existing `valid_visit_event_for_checkpoint` composite strategy
- The S3 LastModified pre-filter is intentionally retained as a performance optimization (Requirement 5)
- Tests are organized in `test_checkpoint.py` (property tests) and `test_lambda_function.py` (integration tests)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.8"] },
    { "id": 2, "tasks": ["3.1", "3.2"] },
    { "id": 3, "tasks": ["3.3"] },
    { "id": 4, "tasks": ["5.1", "5.2", "5.3"] }
  ]
}
```
