# Baseline review (prompt_with_schema): Add the missing invoices -> customers foreign key

```
Verdict: REQUEST_CHANGES

- [HIGH] CONSTRAINT_VALIDATION_LOCK: ADD CONSTRAINT without NOT VALID validates the whole table under a lock.
- [HIGH] VIEW_BREAKAGE: View open_invoices reads a table this migration alters and may stop resolving.
```
