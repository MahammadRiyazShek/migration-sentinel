# Baseline review (prompt_with_schema): Rename customers.full_name to name and refresh the BI view

```
Verdict: REQUEST_CHANGES

- [HIGH] DESTRUCTIVE_NO_EXPAND_CONTRACT: A rename is not backwards compatible with the currently deployed code.
- [MEDIUM] MISSING_ROLLBACK: No rollback statements are included in the file.
- [HIGH] VIEW_BREAKAGE: View customer_billing_summary reads a table this migration alters and may stop resolving.
```
