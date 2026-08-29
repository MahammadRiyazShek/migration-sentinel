# Baseline review (prompt_only): Backfill invoices.currency and make it NOT NULL

```
Verdict: REQUEST_CHANGES

- [BLOCKER] NOT_NULL_NO_DEFAULT: NOT NULL without a default will reject existing rows and in-flight inserts.
- [HIGH] UNBATCHED_BACKFILL: The backfill is one unbounded UPDATE; it will hold locks for its whole duration.
```
