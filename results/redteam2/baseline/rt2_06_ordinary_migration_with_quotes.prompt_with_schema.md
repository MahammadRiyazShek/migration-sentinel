# Baseline review (prompt_with_schema): Add a dunning note column whose default contains a double hyphen

```
Verdict: REQUEST_CHANGES

- [HIGH] VIEW_BREAKAGE: View open_invoices reads a table this migration alters and may stop resolving.
```
