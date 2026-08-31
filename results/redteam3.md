# Red team, round 3: the plan is an artefact too

Round 1 asked whether a hazard class existed that nobody had enumerated. Round 2 asked whether the op list is the migration. Both aimed at the file a human wrote, because every honesty layer in this repository aims at the file a human wrote.

This round aimed at the file *this pipeline* writes. Three scripts per run - phase 1, phase 2, a rollback - printed in the packet, one of them checked, by replay, which `results/ablation.md` has called the weaker half of the design since v2.

```sql
-- rt3_01, the migration. Genuinely safe, and v15 correctly says so.
ALTER TABLE customers ADD COLUMN billing_email TEXT NOT NULL DEFAULT '';

-- rt3_01, two of the things v15 then printed under 'phase 1 verified':
--   code step: deploy code that always writes customers.billing_email
--   rollback:  ALTER TABLE "customers" DROP COLUMN "billing_email";
```

Run those in the order the packet prints them and every write from the deploy the packet asked for fails. Shadow replay of that rollback breaks zero corpus statements, which is why no amount of execution could have found it: the statements that break are the ones the packet is asking someone to write tomorrow. It is a property of two artefacts, and every check in this repository until v16 was a property of one.

## The three probes

| case | v15 verdict | v15 plan | v16 verdict | defects present | v15 reported | v16 reported |
|---|---|---|---|---|---|---|
| `rt3_01_additive_column_with_dependent_rollback` | SAFE | verified | NEEDS_COVERAGE_SIGNOFF | 2 | 0 | 2 |
| `rt3_02_validate_constraint_ungated` | SAFE | verified | NEEDS_COVERAGE_SIGNOFF | 1 | 0 | 1 |
| `rt3_03_additive_column_nobody_depends_on` | SAFE | verified | SAFE | 0 | 0 | 0 |

| metric | Sentinel v15 | Sentinel v16 |
|---|---|---|
| plan defects present in the SQL the arm generated | 3 | 3 |
| plan defects reported to the reviewer | 0 | 3 |
| plan defects shipped unreviewed | **3** | **0** |
| clean verdict printed over a defective plan | **2/2** | **0/2** |
| false alarms on the canary (`rt3_03`) | 0 | 0 |
| human gates in the plans | 0 | 3 |

The defect count for v15 is not a claim about v15's opinion of its own plan - v15 has no opinion, it never looks. It is v15's generated SQL, audited afterwards by the v16 auditor, recomputed from the artefact rather than read out of a report.

## The number to read first: 34 labelled cases, nothing moved

`no_plan_audit` reproduces v15 exactly. Across all 34 labelled cases in `eval/cases`, `eval/holdout`, `eval/redteam` and `eval/redteam2`, `full` and `no_plan_audit` are identical on every input verdict, every hazard code, every severity and every coverage-gap count: **0 case(s) moved**.

That is by construction, and the construction is the argument. A plan defect is a property of our output, so it cannot enter the hazard list without corrupting every recall, precision and severity number in `results/` - those labels describe the input. It caps the verdict and becomes a human gate instead, exactly where v2 put a declared coverage gap.

On those same 34 cases the audit finds **7 defect(s)** across **6 case(s)** in plans this repository has been shipping since v2, **6 of them** under a printed `plan verified: true`:

| case | set | defect | script | generated statement |
|---|---|---|---|---|
| `case_01_rename_with_compat_view` | cases | ROLLBACK_WINDOW_UNSTATED | rollback | `ALTER TABLE "customers" DROP COLUMN "name"` |
| `case_10_add_fk_constraint` | cases | CONTRACT_STEP_UNGATED | phase2 | `ALTER TABLE "invoices" VALIDATE CONSTRAINT "invoices_customer_fk"` |
| `case_12_release_train` | cases | ROLLBACK_WINDOW_UNSTATED | rollback | `ALTER TABLE "subscriptions" DROP COLUMN "billing_interval"` |
| `holdout_07_narrow_invoice_amount` | holdout | ROLLBACK_WINDOW_UNSTATED | rollback | `ALTER TABLE "carrier_invoices" DROP COLUMN "amount_new"` |
| `holdout_08_release_train_fleet` | holdout | CONTRACT_STEP_UNGATED | phase2 | `ALTER TABLE "carrier_invoices" VALIDATE CONSTRAINT "carrier_invoices_shipment_fk"` |
| `holdout_08_release_train_fleet` | holdout | ROLLBACK_WINDOW_UNSTATED | rollback | `ALTER TABLE "drivers" DROP COLUMN "phone_e164"` |
| `rt2_03_unterminated_literal` | redteam2 | GENERATED_TEXT_UNPARSED | phase1 | `{'kind': 'string', 'start': 29, 'end': 200, 'text': '\'open WHERE id = 1; ALTER TABLE invoices DROP COLUMN tax_rate AND` |

## The number this layer moved, and it was not the shipped one

`full` is unchanged on all 34 labelled cases. One ablation arm is not, and the correction belongs here rather than in a commit message.

| arm | unsafe approvals on the 12 in-sample cases |
|---|---|
| replay only, plan audit off (the v2 through v15 number) | **2/12** |
| replay only, plan audit on | **1/12** |
| rules only | **3/12** |

`results/ablation.md` has read *replay alone is worse than rules alone* off that first row since v2. With the audit on, replay-only loses one of its two unsafe approvals - on `case_10`, where no rule priced the 48M-row constraint validation and the plan the pipeline wrote for the migration it had not understood contained an ungated `VALIDATE CONSTRAINT`. The verdict was capped instead of cleared.

That is a real safety gain and a bad diagnosis. The reviewer is told that a generated step has no human gate. Nobody says the words *48 million rows*. So the v2 sentence is corrected rather than kept: **execution alone is not sufficient**, and the arithmetic that used to demonstrate it now needs `plan_audit=False` to reproduce. A plan is a second, independent view of the same risk, and a tool that refuses for the wrong reason is still a tool that refused.


## What this round did not fix

- **The gate matcher reads names, not questions.** A destructive contract step counts as gated when a human gate names its object. A gate that names the object and asks the wrong question passes. Every time this audit trusted a sentence it says so: `audit_gate_text_only` is in the gap list of the packet, and the count is in the report. It is R1 from `sentinel/rulebook.py` one level up again, declared rather than closed.
- **`GENERATED_TEXT_UNPARSED` was written as a hypothesis and turned out to be the third defect class.** It went into the audit because the Rollout Engineer is a text producer and this repository has already been wrong once about a text producer (`eval/redteam2`). It fires on `rt2_03`, which nobody wrote for it: the input carries an unterminated string literal, v14 onwards correctly refuses to certify a file it cannot read - and the Rollout Engineer then built a keyset-batched UPDATE out of the mangled parse and the packet printed it under *Phase 1 - expand (safe to run now)*. The verdict was already BLOCK, so nobody would have run it; the packet was still handing a reviewer SQL that Postgres refuses, formatted as the recommendation. v16 names it, gates it, and `sentinel/report.py` stops presenting an unreadable script as runnable. The fix this round did **not** make: the engineer still generates a plan from a parse the pipeline has already declared unreliable. Refusing to plan at all is the right answer and it is a behaviour change to the arm under measurement, so it is written down here rather than shipped in the last hour of a deadline.
- **There is no baseline column.** A one-prompt review never writes a plan, so it cannot produce this defect class, and it cannot avoid it either. The only fair comparison on this axis is against the previous release of the advanced solution, which is what the table above is.
- **Phase 2 is still not proved safe, only replayed and counted.** The generated contract phase is *supposed* to break today's statements; that is what the code steps are for. The audit publishes which corpus statements it breaks so a reviewer can check that each one has a code step, instead of being told that it does.
