# Baseline review (prompt_only): Idempotent column cleanup wrapped in a DO block, as the framework generates it

```
Verdict: REQUEST_CHANGES

- [HIGH] DESTRUCTIVE_NO_EXPAND_CONTRACT: The diff drops a column or table in a single step; old application code will break.
```
