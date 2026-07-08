# Checkpoint Parquet Schema Changes — v1.2.0

## New Columns

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `naccid` | String (UTF-8) | Yes | NACC participant identifier (e.g., `NACC953400`). Present on most events; null for older submit events that predate the field. |
| `modality` | String (UTF-8) | Yes | Imaging modality (e.g., `MR`, `PT`, `CT`). Present only on `dicom` datatype events; null for all other datatypes. |

## Full Column Order

1. `action` — String, not null
2. `study` — String, not null
3. `pipeline_adcid` — Int32, not null
4. `project_label` — String, not null
5. `center_label` — String, not null
6. `gear_name` — String, not null
7. `ptid` — String, not null
8. `naccid` — String, nullable *(new)*
9. `visit_date` — String, not null
10. `visit_number` — String, nullable
11. `datatype` — String, not null
12. `module` — String, nullable (non-null for `form` datatype only)
13. `packet` — String, nullable
14. `modality` — String, nullable *(new)*
15. `timestamp` — Datetime (microsecond, UTC), not null

## Impact on Downstream Consumers

- Athena/Glue queries that use `SELECT *` will see two new columns — no breakage but results will be wider
- Queries that reference columns by name are unaffected
- Queries that reference columns by position index will break if they assumed the old 13-column layout
- The parquet file at `prod/checkpoints/{study}/{datatype}/events.parquet` will be rewritten with the new schema on the next successful run, replacing the old file
