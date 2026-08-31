# Baseline review (prompt_with_schema): Normalise the invoice currency default, then retire the unused tax column

```
Verdict: REQUEST_CHANGES

- [HIGH] DESTRUCTIVE_NO_EXPAND_CONTRACT: The diff drops a column or table in a single step; old application code will break.
- [HIGH] UNBATCHED_BACKFILL: The backfill is one unbounded UPDATE; it will hold locks for its whole duration.
- [HIGH] VIEW_BREAKAGE: View open_invoices reads a table this migration alters and may stop resolving.
```
