# Baseline review (prompt_only): Add a concurrent index from inside the framework's DDL transaction

```
Verdict: REQUEST_CHANGES

- [BLOCKER] CONCURRENT_DDL_IN_TRANSACTION: CONCURRENTLY cannot run inside a transaction block; Postgres will refuse the statement.
```
