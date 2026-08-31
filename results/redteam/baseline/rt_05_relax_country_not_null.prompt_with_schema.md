# Baseline review (prompt_with_schema): Make country_code nullable again

```
Verdict: REQUEST_CHANGES

- [HIGH] VIEW_BREAKAGE: View customer_billing_summary reads a table this migration alters and may stop resolving.
```
