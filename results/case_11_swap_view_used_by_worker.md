# Migration review: Replace the open_invoices view with a v2 definition

**BLOCK - do not merge**

Do not ship this as written. 2 statement(s) the application issues today fail against the post-migration schema in shadow replay. 1 blocker, 1 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-case_11_swap_view_used_by_worker` · case `case_11_swap_view_used_by_worker` · owning service `billing-api` · 11.1 ms · model scripted-v1 (5 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Live query breaks after migration | `q_dunning_open` | replay |
| 2 | **HIGH** | Impact lands on a service owned by another team | `-` | static |
| 3 | **MEDIUM** | No rollback path supplied | `-` | static |

### 1. [BLOCKER] Live query breaks after migration

q_dunning_open fails after the migration: OperationalError: no such table: open_invoices

- evidence: shadow replay: `SELECT * FROM open_invoices` -> OperationalError: no such table: open_invoices
- services affected: dunning-worker

### 2. [HIGH] Impact lands on a service owned by another team

the migration is owned by `billing-api` but breakage lands in dunning-worker

- evidence: corpus ownership of failing statements: ['dunning-worker']
- services affected: dunning-worker

### 3. [MEDIUM] No rollback path supplied

the change ships without a rollback script

- evidence: case field `rollback_sql` is empty

## Blast radius

- statements in the corpus that touch the changed objects: 1 (weighted score 4)
- shadow replay: 16/16 statements passed before, 15/16 after
- reproduced failures: 2 · silent column changes: 0 · data-migration failures: 0

| statement | service | engine error |
|---|---|---|
| `q_dunning_open` | dunning-worker | OperationalError: no such table: open_invoices |
| `__view__open_invoices` | database | object removed by migration (view or table no longer exists) |

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1. That is a statement about phase 1 and about today's corpus only - the audit of all three generated scripts is the section below.

### Phase 1 - expand (safe to run now)

```sql
CREATE VIEW open_invoices_v2 AS SELECT id, customer_id, invoice_number, amount_cents, status, issued_at FROM invoices WHERE status IN ('draft','open');
```

### Phase 2 - contract (only after the code steps below)

```sql
DROP VIEW open_invoices;
```

### Human decisions required (the tool will not decide these)

- confirm nothing reads open_invoices before phase 2 removes it
- no rollback could be generated automatically; write one before shipping

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- Which deploy lands first: the query change or the schema change?
- Has the owning team agreed to the deploy order?
- What is the accepted risk for MISSING_ROLLBACK?

## Plan self-audit

The three scripts above are output from this pipeline, so they are reviewed like any other artefact it is handed: 2 generated statement(s) parsed, partitioned by the rule inventory in `sentinel/rulebook.py`, cross-checked against the code steps, and replayed. A defect here is a defect in *our* SQL, not in the migration under review, so it never enters the hazard table - it caps the verdict and becomes a human gate.

No defect found in the generated SQL: every destructive contract step is named by a human gate, no rollback statement removes something a code step in this packet asks the team to start using, and every generated statement has a kind something in this pipeline inspects.

What this audit trusted rather than checked:

- `open_invoices` (audit_gate_text_only, generated phase2): this step is treated as gated because a human gate names `open_invoices`; this audit read the name, not the question

- shadow replay of the generated phase2 script against the post-phase-1 schema: 2 of 16 corpus statement(s) break (__view__open_invoices, q_dunning_open) - expected for a contract step, which is what the code steps above are for; the number is printed so it can be checked rather than assumed

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/case_11_swap_view_used_by_worker.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Do not ship this as written. 2 statement(s) the application issues today fail against the post-migration schema in shadow replay. 1 blocker, 1 high, 1 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
