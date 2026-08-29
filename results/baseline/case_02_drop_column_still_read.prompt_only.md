# Baseline review (prompt_only): Drop customers.company_name after the product decision to remove it

```
Verdict: REQUEST_CHANGES

- [HIGH] DESTRUCTIVE_NO_EXPAND_CONTRACT: The diff drops a column or table in a single step; old application code will break.
- [MEDIUM] MISSING_ROLLBACK: No rollback statements are included in the file.
```
