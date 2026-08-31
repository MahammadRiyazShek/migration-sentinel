# Baseline review (prompt_with_schema): Release train: six fleet changes in one migration

```
Verdict: REQUEST_CHANGES

- [HIGH] DESTRUCTIVE_NO_EXPAND_CONTRACT: The diff drops a column or table in a single step; old application code will break.
- [HIGH] INDEX_LOCK_NO_CONCURRENT: CREATE INDEX without CONCURRENTLY takes a lock that blocks writes.
- [HIGH] CONSTRAINT_VALIDATION_LOCK: ADD CONSTRAINT without NOT VALID validates the whole table under a lock.
- [HIGH] UNBATCHED_BACKFILL: The backfill is one unbounded UPDATE; it will hold locks for its whole duration.
- [MEDIUM] MISSING_ROLLBACK: No rollback statements are included in the file.
- [HIGH] VIEW_BREAKAGE: View driver_roster reads a table this migration alters and may stop resolving.
```
