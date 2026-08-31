# Migration review: Idempotent column cleanup wrapped in a DO block, as the framework generates it

**BLOCK - do not merge**

Do not ship this as written. 1 coverage gap(s) need a named sign-off before this can be called safe. 1 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements. (Written from the tool output. In this build the model never writes this line, whatever it returns.)

`run eval-rt2_02_do_block_hides_the_drop` · case `rt2_02_do_block_hides_the_drop` · owning service `platform` · 8.6 ms · model scripted-v1 (3 calls, $0.0000)

> **The headline above was written by the tools, not by the model.** In this build the narrator cannot write the sentence above the badge on any run (`sentinel/narrator.py`, mode `structural`), so a lie in wording no blocklist knows cannot become the verdict sentence. The model's prose, where it survives the guard, appears under *Model commentary* at the end, labelled unverified.

## Hazards

| # | Severity | Hazard | Where | Found by |
|---|---|---|---|---|
| 1 | **BLOCKER** | Schema change executes inside a procedural body | `migration script` | static |

### 1. [BLOCKER] Schema change executes inside a procedural body

1 schema or data statement(s) execute inside the $$ body of statement 0; the expand/contract analysis, the dependency map and the shadow replay all ran on the outer statement only

- evidence: statement 0: `DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns W`
- evidence: inside the body: `ALTER TABLE invoices DROP COLUMN tax_rate`

## Blast radius

- statements in the corpus that touch the changed objects: 0 (weighted score 0)
- shadow replay: 19/19 statements passed before, 19/19 after
- reproduced failures: 0 · silent column changes: 0 · data-migration failures: 0

## Recommended rollout

Plan generated on attempt 1 of 1; phase 1 **verified**: every statement in the corpus still passes after phase 1. That is a statement about phase 1 and about today's corpus only - the audit of all three generated scripts is the section below.

### Human decisions required (the tool will not decide these)

- statement 0 (procedural_block) is outside the tool's model and needs manual review: DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoic
- IRREVERSIBLE - coverage gap on `$$ body at statement 0` (procedural_body): a reviewer reads the $$ body of statement 0 in full, including every branch, before phase 1

### Questions for the reviewer (drafted by the model, guarded prose, not evidence)

- What is the accepted risk for PROCEDURAL_DDL_UNREVIEWED?

## Plan self-audit

The three scripts above are output from this pipeline, so they are reviewed like any other artefact it is handed: 0 generated statement(s) parsed, partitioned by the rule inventory in `sentinel/rulebook.py`, cross-checked against the code steps, and replayed. A defect here is a defect in *our* SQL, not in the migration under review, so it never enters the hazard table - it caps the verdict and becomes a human gate.

No defect found in the generated SQL: every destructive contract step is named by a human gate, no rollback statement removes something a code step in this packet asks the team to start using, and every generated statement has a kind something in this pipeline inspects.


## Coverage ledger

1 gap(s) between what this migration touches and what this review could actually observe. A gap is an absence of evidence, so it is recorded as a decision for a person rather than as a finding with a severity.

| object | gap | why it is a gap | closes when |
|---|---|---|---|
| `$$ body at statement 0` **(irreversible)** | procedural_body | the body holds 3 scanned statement(s) and nothing in this pipeline models a procedural block: the census below is a keyword scan, not a parse, so the packet knows that DDL is in there and not what the block does with it (branches, loops, exception handlers, dynamic SQL) | a reviewer reads the $$ body of statement 0 in full, including every branch, before phase 1 |

## What this review did not check

- Lock behaviour is inferred from declared row estimates and static rules; the shadow database is SQLite and cannot reproduce PostgreSQL lock queues.
- Fixture data is a small synthetic sample, so data-dependent hazards are detected only where the fixtures expose them.
- Application code is only visible through the query corpus; anything issuing dynamic SQL that is not in the corpus is invisible here.
- unmodelled statement: op 0 (procedural_block) not modelled structurally: DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.colu

## Approval

Nothing was executed against a real database. Phase 1 can be dry-run against a local sandbox copy with:

```bash
python -m sentinel execute --report results/rt2_02_do_block_hides_the_drop.json --i-approve --reviewer "your name"
```

A qualified reviewer signs off here before any deploy: ______________________

## Model commentary (unverified prose, not evidence)

> Do not ship this as written. 1 coverage gap(s) need a named sign-off before this can be called safe. 1 blocker, 0 high, 0 medium, 0 low. The rewritten phase-1 plan passes shadow replay with zero broken statements.

The narrator wrote the paragraph above. It passed the prose guard, which is a statement about its wording and not about its truth. Nothing in it produced, removed or reordered a single finding in this packet: every hazard, severity, plan statement and verdict above comes from a tool call recorded in the trajectory.
