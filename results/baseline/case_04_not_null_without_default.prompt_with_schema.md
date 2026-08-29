# Baseline review (prompt_with_schema): Add customers.billing_email as NOT NULL

```
Verdict: REQUEST_CHANGES

- [BLOCKER] NOT_NULL_NO_DEFAULT: NOT NULL without a default will reject existing rows and in-flight inserts.
- [HIGH] VIEW_BREAKAGE: View customer_billing_summary reads a table this migration alters and may stop resolving.
```
