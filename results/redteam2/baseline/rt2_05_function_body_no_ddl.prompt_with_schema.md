# Baseline review (prompt_with_schema): Add a dunning audit trigger function and the column it stamps

```
Verdict: REQUEST_CHANGES

- [HIGH] VIEW_BREAKAGE: View open_invoices reads a table this migration alters and may stop resolving.
```
