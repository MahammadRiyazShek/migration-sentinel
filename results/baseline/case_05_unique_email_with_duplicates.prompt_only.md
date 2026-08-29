# Baseline review (prompt_only): Enforce unique customer emails

```
Verdict: REQUEST_CHANGES

- [HIGH] INDEX_LOCK_NO_CONCURRENT: CREATE INDEX without CONCURRENTLY takes a lock that blocks writes.
- [HIGH] UNIQUE_VIOLATION_EXISTING_DATA: Adding uniqueness may fail if duplicates already exist - please check first.
```
