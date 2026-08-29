# Baseline review (prompt_with_schema): Narrow customers.country_code to varchar(2)

```
Verdict: REQUEST_CHANGES

- [HIGH] TABLE_REWRITE_LOCK: A column type change rewrites the table under an exclusive lock.
- [HIGH] VIEW_BREAKAGE: View customer_billing_summary reads a table this migration alters and may stop resolving.
```
