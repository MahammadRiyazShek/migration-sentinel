# Baseline review (prompt_only): Index invoices.status to speed up the dunning sweep

```
Verdict: REQUEST_CHANGES

- [HIGH] INDEX_LOCK_NO_CONCURRENT: CREATE INDEX without CONCURRENTLY takes a lock that blocks writes.
```
