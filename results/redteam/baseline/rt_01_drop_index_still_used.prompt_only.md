# Baseline review (prompt_only): Drop the customer index on invoices during an unused-index cleanup

```
Verdict: APPROVE

- [MEDIUM] ACCESS_PATH_REMOVED: An index is dropped; queries that relied on it may get much slower - check usage first.
```
