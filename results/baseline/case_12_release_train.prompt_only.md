# Baseline review (prompt_only): Release train: six changes in one migration

```
Verdict: REQUEST_CHANGES

- [HIGH] DESTRUCTIVE_NO_EXPAND_CONTRACT: The diff drops a column or table in a single step; old application code will break.
- [HIGH] INDEX_LOCK_NO_CONCURRENT: CREATE INDEX without CONCURRENTLY takes a lock that blocks writes.
- [HIGH] UNIQUE_VIOLATION_EXISTING_DATA: Adding uniqueness may fail if duplicates already exist - please check first.
- [HIGH] UNBATCHED_BACKFILL: The backfill is one unbounded UPDATE; it will hold locks for its whole duration.
- [MEDIUM] MISSING_ROLLBACK: No rollback statements are included in the file.
```
