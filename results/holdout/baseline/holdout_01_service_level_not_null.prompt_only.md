# Baseline review (prompt_only): Add shipments.service_level as NOT NULL

```
Verdict: REQUEST_CHANGES

- [BLOCKER] NOT_NULL_NO_DEFAULT: NOT NULL without a default will reject existing rows and in-flight inserts.
```
