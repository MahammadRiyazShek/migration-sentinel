# Baseline review (prompt_with_schema): Drop the shipments status CHECK constraint

```
Verdict: REQUEST_CHANGES

- [HIGH] VIEW_BREAKAGE: View active_shipments reads a table this migration alters and may stop resolving.
- [MEDIUM] INTEGRITY_CONSTRAINT_REMOVED: A constraint is dropped; nothing breaks immediately but invalid rows become possible.
```
