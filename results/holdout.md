# Held out: a second schema the rules were never written against

```
decision-code freeze: POST-FREEZE (34 files hashed under sentinel/)
  frozen at: v5 decision code, hashed before the held-out schema, cases or labels existed
  changed: sentinel/agents/risk_officer.py
  changed: sentinel/agents/rollout_engineer.py
  changed: sentinel/coverage.py
  changed: sentinel/hazards.py
  changed: sentinel/llm/scripted.py
  changed: sentinel/orchestrator.py
  changed: sentinel/tools/query_corpus.py
  changed: sentinel/tools/shadow_db.py
  added: sentinel/rulebook.py
  -> the held-out numbers below are an AFTER-THE-FIX run. The frozen first-contact run is kept in results/holdout/frozen_run.json.
```

In sample: 12 cases, one SaaS billing schema, the set every earlier number in this repository was measured on.
Held out: 9 cases, a freight/logistics schema with its own corpus, its own row estimates, composite natural keys, JSONB, NUMERIC money and write paths in the corpus. No rule, threshold, hazard code or gap class was written or tuned against it before the first-contact run.

## The generalization table

| metric | Sentinel, in sample | Sentinel, held out | Baseline B, held out |
|---|---|---|---|
| **Unsafe approvals** (primary) | 0/12 | 0/9 | 1/9 |
| **Blocking cases given a clean verdict** (primary, v6) | 0/9 | 0/7 | 1/7 |
| Hazard recall (strict code) | 0.97 | 0.96 | 0.56 |
| Hazard recall excluding the label no arm can name | 0.97 | 1.0 | 0.583 |
| Hazard precision (strict code) | 0.97 | 1.0 | 0.737 |
| Severity agreement on matched hazards | 0.969 | 0.958 | 0.714 |
| False alarms on the deliberately clean case | 0 | 0 | 1 |
| Findings backed by machine evidence | 35/35 | 26/26 | 0/19 |
| Verified expand/contract plans | 12/12 | 9/9 | 0/9 |
| Blind spots named, with the object | 3 | 6 | 0 |
| Gap cases cleared without a sign-off | 0/2 | 0/4 | 1/4 |
| Modelled reviewer minutes per case | 9.2 | 10.7 | 33.4 |

Read the recall row with its neighbour. `holdout_06` carries `TRIGGER_WRITE_AMPLIFICATION`, a hazard code deliberately outside the shared vocabulary, so no arm can name it and every arm loses the same recall point on it. Excluding it, the pipeline finds every held-out label; including it, the honest figure is 0.96. A held-out set whose labels all fit the tool's vocabulary would have tested the rules and quietly exempted the vocabulary.

Precision is *higher* out of sample (1.0 vs 0.97) and severity agreement is slightly lower (0.958 vs 0.969). Both have the same cause: this world has no incident log. `memory/incidents.jsonl` belongs to the billing team, so out of sample nothing escalates a severity and nothing borrows a prior. See the `no_memory` row below, which is identical to `full` on every metric.

## What first contact found, before anything was fixed

| metric | frozen run (v5 code) | after the two v6 fixes |
|---|---|---|
| Unsafe approvals | 0/9 | 0/9 |
| **Blocking cases given a clean verdict** | 1/7 | 0/7 |
| Blind spots named, with the object | 5 | 6 |
| Gap objects named `unknown` | 1 | 0 |
| Modelled reviewer minutes per case | 10.3 | 10.7 |

Two defects, both invisible in sample, both fixed in `sentinel/coverage.py` and `sentinel/tools/shadow_db.py`:

1. **`holdout_07`, the fixture-bounded value scan.** `numeric(12,2) -> numeric(8,2)` on a 9.4M-row invoice table. The value scan ran over five seeded rows, found nothing that would be refused, filed a `medium`, and the packet printed *Shippable, but only as the staged plan below*. The scan was also wrong in kind: precision was treated as string truncation, so it could not have seen a 1,000,000.00 invoice even if one had been seeded. Fix: `offending_values` understands `numeric(p,s)`, and a clean scan over a fixture smaller than the declared row count is now a declared, irreversible coverage gap. Verdict moves `SAFE_WITH_PLAN` -> `NEEDS_COVERAGE_SIGNOFF`. No hazard invented, no severity moved.
2. **`holdout_06`, the gap called `unknown`.** `CREATE TRIGGER ... ON shipment_stops` is outside the parser's model, so the ledger opened a gap - against the literal string `unknown`, in the one component whose job is naming the affected object. Fix: `relation_hint` reads the relation out of the statement text and the gap carries `object_inferred: true`, so the reviewer gets the object *and* the provenance of the name.

Neither fix moves an in-sample number: `tools/check_results.py` still asserts the same in-sample figures it did before this work, and `case_08` (the in-sample narrowing) has offenders in its fixture, so it opens no new gap.

## Ablation, out of sample

| configuration | unsafe approvals | blocking cases given a clean verdict | recall | verified plans | gaps cleared | minutes/case |
|---|---|---|---|---|---|---|
| `full` | 0/9 | 0/7 | 0.96 | 9/9 | 0/4 | 10.7 |
| `no_replay` | 0/9 | 1/7 | 0.56 | 0/9 | 0/4 | 22.8 |
| `no_static` | 0/9 | 0/7 | 0.32 | 9/9 | 0/4 | 10.0 |
| `no_memory` | 0/9 | 0/7 | 0.96 | 9/9 | 0/4 | 10.7 |
| `no_verify` | 0/9 | 0/7 | 0.96 | 0/9 | 0/4 | 22.8 |
| `no_coverage` | 1/9 | 3/7 | 0.96 | 9/9 | 3/4 | 8.7 |
| `no_rule_coverage` | 0/9 | 0/7 | 0.96 | 9/9 | 0/4 | 10.7 |

**The one component that looked like a tax in sample pays for itself out of sample.** Removing the coverage gate costs nothing in sample - 0 unsafe approvals either way - and saves 0.7 modelled minutes a case, which is why it is the only component whose removal makes a published in-sample number look better. Out of sample, removing it costs 1 unsafe approval and lets 3 of 7 blocking migrations reach a clean verdict: on `holdout_06` the hazard is a statement class the parser cannot model and the vocabulary cannot name, so refusing to certify it is the *only* correct behaviour available, and the gate is the only thing that does it.

**And the one component that is worth nothing here says so.** `no_memory` is identical to `full` on every metric out of sample (recall 0.96, unsafe 0/9). The incident log is the billing team's; a second team's tables have no history, so the memory layer contributes exactly zero. That is the correct value for a schema-specific component on a new schema, and no in-sample ablation could ever have told us.

## Hostile models, out of sample

`python3 eval/model_invariance.py --cases eval/holdout --out results/holdout` reruns the 5 models x 3 narrator modes harness on this world: 135 reviews. The numbers it produced in sample hold here too, on a schema none of it was tuned against.

| out-of-sample invariance | value |
|---|---|
| decision surface changed, any model, any mode | 0 of 126 completed reviews |
| headlines written by a model in the shipped `structural` mode | 0 of 45 |
| the fluent liar reaching the reviewer, shipped mode | 0 of 9 |
| crashes with the narrator unguarded (a null model response) | 9 |
| recorded held-out packets matching a fresh reference run | 9/9 |

## Per-case, held out

| case | ground truth | Sentinel verdict | missed | false alarms | coverage gaps |
|---|---|---|---|---|---|
| `holdout_01_service_level_not_null` | blocking | BLOCK | - | - | - |
| `holdout_02_composite_unique_invoices` | blocking | BLOCK | - | - | - |
| `holdout_03_rename_table_behind_view` | blocking | BLOCK | - | - | - |
| `holdout_04_safe_additive_language` | non-blocking | SAFE | - | - | - |
| `holdout_05_drop_status_check` | non-blocking | SAFE_WITH_PLAN | - | - | - |
| `holdout_06_audit_trigger` | blocking | NEEDS_COVERAGE_SIGNOFF | TRIGGER_WRITE_AMPLIFICATION | - | unmodelled_statement |
| `holdout_07_narrow_invoice_amount` | blocking | NEEDS_COVERAGE_SIGNOFF | - | - | fixture_bounded_value_scan |
| `holdout_08_release_train_fleet` | blocking | BLOCK | - | - | uncovered_object, in_place_data_mutation, unmodelled_statement |
| `holdout_09_drop_employment_type` | blocking | NEEDS_COVERAGE_SIGNOFF | - | - | uncovered_object |

Commands, from a clean clone, no key and no network:

```bash
python3 eval/build_holdout.py     # regenerate the 9 held-out cases
python3 eval/run_holdout.py --ablations   # 9 cases x 9 arms + the report
python3 tools/freeze_attest.py            # what changed in the decision code, by hash
```

