# Baseline review (prompt_with_schema): Idempotent column cleanup wrapped in a DO block, as the framework generates it

```
Verdict: REQUEST_CHANGES

- [HIGH] DESTRUCTIVE_NO_EXPAND_CONTRACT: The diff drops a column or table in a single step; old application code will break.
- [HIGH] VIEW_BREAKAGE: View open_invoices reads a table this migration alters and may stop resolving.
```
