# Baseline review (prompt_with_schema): The same index swap, outside a transaction: a correct migration

```
Verdict: APPROVE

- [MEDIUM] ACCESS_PATH_REMOVED: An index is dropped; queries that relied on it may get much slower - check usage first.
```
