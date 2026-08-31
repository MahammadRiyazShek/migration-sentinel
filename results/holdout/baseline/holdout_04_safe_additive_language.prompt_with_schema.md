# Baseline review (prompt_with_schema): Add drivers.preferred_language and index drivers.carrier_id concurrently

```
Verdict: REQUEST_CHANGES

- [HIGH] VIEW_BREAKAGE: View driver_roster reads a table this migration alters and may stop resolving.
```
