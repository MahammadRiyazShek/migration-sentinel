# Migration review: Drop the customer index on invoices during an unused-index cleanup

**BLOCK - do not merge**

Do not ship this as written. 1 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-rt_01_drop_index_still_used` · case `rt_01_drop_index_still_used` · owning service `platform` · 9.9 ms · model scripted-v1 (3 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Index dropped while live statements still filter on it | `invoices.customer_id` | static+replay |

### 1. [BLOCKER] Index dropped while live statements still filter on it

dropping idx_invoices_customer removes the only declared index on invoices (customer_id) while 3 live statement(s) still filter, join or sort by it on a very large table (48,000,000 rows)

- evidence: statement 0: `DROP INDEX idx_invoices_customer`
- evidence: declared row estimate for invoices: 48,000,000
- evidence: q_billing_customer_invoices (billing-api, critical): `WHERE customer_id`
- evidence: q_support_open_for_customer (support-admin, high): `WHERE customer_id`
- evidence: q_bi_revenue_by_customer (bi, medium): `GROUP BY customer_id`
- services affected: bi, billing-api, support-admin

## Blast radius

- statements in the corpus that touch the changed objects: 0 (weighted score 0)
- shadow replay: 19/19 statements passed before, 19/19 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 0

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1.

### Phase 2 - contract (only after the code steps below)

```sql
DROP INDEX CONCURRENTLY idx_invoices_customer;
```

### Human decisions required (the tool will not decide these)

- read pg_stat_user_indexes.idx_scan for idx_invoices_customer over a full business cycle and confirm it is unused before phase 2 drops it

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- What is the accepted risk for ACCESS_PATH_REMOVED?

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/rt_01_drop_index_still_used.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Do not ship this as written. 1 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
