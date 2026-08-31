# Baseline review (prompt_with_schema): Swap the narrow index for the composite one, inside a transaction

```
Verdict: REQUEST_CHANGES

- [MEDIUM] ACCESS_PATH_REMOVED: An index is dropped; queries that relied on it may get much slower - check usage first.
- [BLOCKER] CONCURRENT_DDL_IN_TRANSACTION: CONCURRENTLY cannot run inside a transaction block; Postgres will refuse the statement.
```
