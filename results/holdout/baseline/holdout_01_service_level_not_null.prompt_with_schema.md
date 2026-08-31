# Baseline review (prompt_with_schema): Add shipments.service_level as NOT NULL

```
Verdict: REQUEST_CHANGES

- [BLOCKER] NOT_NULL_NO_DEFAULT: NOT NULL without a default will reject existing rows and in-flight inserts.
- [HIGH] VIEW_BREAKAGE: View active_shipments reads a table this migration alters and may stop resolving.
```
