# Supervisor log v9: the held-out session

An external-supervisor pass over the finished v5 submission. Same protocol as v3-v8: act as the
critic, name the hidden assumptions, generate rival designs, pick one, run it, publish what falls
out - including the parts that make the pipeline look worse.

## 1. Critique layer: three hidden assumptions in v5

**A1. "Recall 0.970 means the pipeline finds hazards."** It meant: in twelve cases, on one billing
schema, whose labels were written by the same person who wrote the rules. Nine ablation arms and 180
hostile-model reviews all vary the *scaffolding*. Not one of them varies the *data*. No published
number in v5 could tell "this pipeline works" apart from "these rules memorised twelve migrations".

**A2. "The coverage ledger names what the review could not see."** It named four gap classes, and
all four were derived from the same twelve cases. The perimeter of the honesty layer was itself
unaudited - the one thing this project claims to be about.

**A3. "Unsafe approvals is the primary metric."** It counts `APPROVE` and `SAFE`. A packet that
prints *Shippable, but only as the staged plan below* over a migration that fails in production
scores zero on it.

## 2. Variation operator: two rival designs

**V1, a held-out world.** A second schema, a second corpus, new hazard shapes, new labels, written
*after* hashing the decision code; run once with no rule edits allowed. Directly measures
out-of-sample behaviour. Costs one authored world, and is only as strong as the freeze evidence.

**V2, a metamorphic fuzzer.** Mutate the twelve migrations mechanically - reorder statements, insert
no-ops, rename identifiers, scale row estimates - and assert invariants instead of labels: a verdict
must never get *safer* when a hazardous statement is added. Needs no ground truth, scales to
thousands of inputs. But it can only find inconsistency, never a missed hazard class, so it cannot
answer A2.

**Chosen: V1**, because A2 is the claim this project is built on and only new hazard shapes can test
it. V2's central invariant is kept as `tests/test_all.py::TestHeldOutSet` rather than a harness.

## 3. Persistent memory: what the run found

Log carried at the top of `eval/build_holdout.py` and `eval/run_holdout.py`, so the finding sits in
the file that acts on it. Full report: `results/holdout.md`.

| assumption | verdict after the held-out run |
|---|---|
| A1 | **survived.** 0/9 unsafe approvals, strict recall 0.96, precision 1.0 on a schema the rules never saw. 1.0 excluding `holdout_06`, whose label is outside the shared vocabulary on purpose |
| A2 | **failed twice.** `holdout_07`: a narrowing whose offenders were absent from the fixture was a `medium` note under a "shippable" headline - the fixture is a sample of the data exactly as the corpus is a sample of the consumers, and only one of the two was in the ledger. `holdout_06`: the parser modelled nothing, so the gap was filed against the literal string `unknown` |
| A3 | **failed.** The `holdout_07` packet scored zero unsafe approvals. A second primary metric now counts blocking cases under any verdict that reads as "proceed on what is written here": first contact 1/7, after the fix 0/7 |

Two more results worth as much as the fixes:

* **The coverage gate pays for itself out of sample.** In sample its removal costs no unsafe approval
  and saves 0.7 modelled minutes a case - the only component whose removal makes a published number
  look better. Out of sample, removing it costs an unsafe approval and lets 3 of 7 blocking
  migrations reach a clean verdict.
* **The memory layer is worth exactly zero here, and says so.** `no_memory` is identical to `full` on
  every held-out metric. The incident log belongs to the billing team. No in-sample ablation could
  ever have told us that.

## 4. Self-review: three defects in this session's own first draft

1. **The freeze was a sentence, not evidence.** The first draft simply asserted that the rules were
   not tuned on the held-out cases - the least verifiable sentence in any evaluation report, and
   exactly the shape of claim this repository refuses to accept from a model. Fixed:
   `tools/freeze_attest.py` hashes all 34 files under `sentinel/`, `results/holdout/frozen_run.json`
   is the first-contact run, and every held-out report prints `CLEAN` or `POST-FREEZE` with the
   changed files named.
2. **The two fixed cases were still being called held out.** Once a fix is derived from a case, that
   case is in-sample for the fix. `holdout_06` and `holdout_07` are now labelled as such everywhere,
   including in the submission description.
3. **The form cap was never read off the form.** `tools/check_submission_text.py` asserted a
   10,000-character limit; the field says 9,000, and the submitted text was 9,422 - so the failure
   mode and hot take, the 5% rubric row, sat over the edge of a limit no checker had ever read. The
   cap is 9,000 now, the two copies of the description are asserted byte-identical, and the claim
   count in the lede is asked of `tools/check_results.py` instead of hardcoded.

## 5. What is still not proved

Twenty-one hand-labelled cases on two schemas, both written by me. Held-out labels are drawn in the
tool's own vocabulary, so out-of-sample recall measures whether the *rules* transfer, not whether the
*vocabulary* is complete - `holdout_06` is the single label that steps outside it, and it is the
single miss. Two worlds is not a distribution either. The next honest move is a third schema written
by somebody else.
