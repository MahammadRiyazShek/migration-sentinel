# Baseline review (prompt_only): Add customers.billing_email as NOT NULL

```
Verdict: REQUEST_CHANGES

- [BLOCKER] NOT_NULL_NO_DEFAULT: NOT NULL without a default will reject existing rows and in-flight inserts.
```
