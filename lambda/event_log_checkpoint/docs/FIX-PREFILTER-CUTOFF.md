# Fix: Replace event-timestamp cutoff with LastModified high-water mark

## Problem

The pre-filter in `S3EventRetriever.list_event_files()` compared `file.LastModified < since_timestamp` where `since_timestamp` was the max **event timestamp** from existing checkpoints. These are different time domains — a file uploaded today can contain an old event (backfill). Combined with the `max_files` cap (which previously returned files in S3's lexicographic key order), this caused unprocessed files to be permanently skipped.

### Root Cause

Three different orderings were conflated:

1. **S3 key (lexicographic)** — what `list_objects_v2` returns by default
2. **S3 LastModified** — when the file was uploaded
3. **Event timestamp** (inside JSON) — when the action occurred; what the checkpoint tracks

The per-file invariant `LastModified >= event_timestamp` is always true. But comparing a file's `LastModified` against a cutoff derived from **event timestamps** is incorrect because ordering between files is not preserved across these domains.

Additionally, capping in lexicographic order means files from a later batch (alphabetically) could have an *earlier* `LastModified` than files in the first batch, so even a `LastModified`-vs-`LastModified` comparison would skip files if the cap is applied before sorting.

### Failure Scenario

1. First run (no checkpoint): lists all 67k files, cap at 25k, processes first 25k alphabetically
2. Those 25k include events with recent timestamps → checkpoint max event timestamp is e.g. Jul 6
3. Second run: `since_timestamp = Jul 6`, pre-filter skips files with `LastModified < Jul 6`
4. Remaining files uploaded Jul 2–5 get permanently skipped despite containing unprocessed events

## Fix

Two changes working together:

### 1. Sort by LastModified before capping (`s3_retriever.py`)

- `list_event_files()` now paginates through the **entire** S3 listing (no early exit)
- Collects all matching `(key, LastModified)` tuples that pass the pre-filter
- **Sorts by `LastModified` ascending** — oldest-uploaded files first
- Applies `max_files` cap **after sorting**
- Sets `self.max_last_modified` to the `LastModified` of the last file in the returned batch

This ensures the cap always takes the oldest unprocessed files, and the high-water mark advances monotonically.

### 2. Track max `LastModified` in a state file (`processing_state.py` + `lambda_function.py`)

- New `ProcessingState` class manages a JSON state file in S3:
  ```json
  {"max_processed_last_modified": "2026-07-05T14:30:00+00:00"}
  ```
- **On startup**: lambda reads this file for the `since_timestamp` cutoff. Missing file → `None` (no filter, first-run behavior).
- **After successful processing**: lambda writes `max(current_mark, retriever.max_last_modified)` — only advances forward, never backward.
- Replaces `_find_earliest_checkpoint_timestamp()` which scanned parquet checkpoints for event timestamps (wrong domain).
- State file lives at `{checkpoint_prefix}processing_state.json` alongside the checkpoint parquets.

### Why This Works

The invariant is: **"All files with `LastModified <= high_water_mark` have been processed."**

- Run 1 processes the n files with the smallest `LastModified` values. After success, `high_water_mark = max LastModified` of those n files.
- Run 2's pre-filter skips everything with `LastModified < high_water_mark`. The remaining files all have `LastModified >= high_water_mark` — exactly the unprocessed set. Take the next n in `LastModified` order. Advance mark. Repeat.
- No file is ever skipped because key ordering is irrelevant to the cap.
- Backfilled files (old events uploaded today) are not skipped because their `LastModified` is today.

### Tradeoff: Full Pagination

For ~67k files the full listing is a few hundred `list_objects_v2` pages (1000 keys each). The API cost is negligible, and collecting all keys into memory is only a few MB. The early-exit optimization we lost was the source of the bug.

### What Doesn't Change

- `Checkpoint` — content-based upsert in `add_events()` completely independent
- `CheckpointStore` — read/write parquet, no changes
- `EventFilter` — sandbox filtering
- `EventGrouper` — study-datatype partitioning
- `VisitEvent` model — validation
- The `since_timestamp` parameter on `S3EventRetriever` — same interface, just fed the correct value now

## Files Changed

- `s3_retriever.py` — full pagination, sort by `LastModified`, cap after sort, track `max_last_modified`
- `processing_state.py` — **new** — `ProcessingState` class for reading/writing the JSON state file
- `lambda_function.py` — removed `_find_earliest_checkpoint_timestamp()`; reads/writes state file instead

## Post-Fix Deployment Steps

1. Deploy the fix
2. Remove `MAX_FILES_PER_RUN` env var override (or set via Terraform; the lambda still respects it for incremental progress)
3. Delete existing checkpoint: `aws s3 rm s3://submission-events/prod/checkpoints/adrc/form/events.parquet`
4. Delete state file if it exists: `aws s3 rm s3://submission-events/prod/checkpoints/adrc/processing_state.json`
5. Invoke lambda to reprocess from scratch (may need multiple runs if >15 min)
6. Re-enable schedule: `aws events enable-rule --name event-log-checkpoint-schedule-prod`
