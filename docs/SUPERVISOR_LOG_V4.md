# Supervisor log, v4

External-supervisor pass over the finished v3 submission. Nothing under `sentinel/`, `eval/` or
`results/` was modified: v4 changes what the submission *says* and what it *refuses to hide*. Read
`docs/CRITIQUE_LOG.md` (v2) and `docs/SUPERVISOR_LOG_V3.md` (v3) first; this file assumes them.

---

## 0. Memory log (written before the work, then used to drive it)

**M1. The engine was re-verified from a clean container before a word was written.** Python 3.12.13,
no network, no pip install: `27/27` tests, the `--ablations` sweep (9 arms x 12 cases = 108 reviews)
in **1.0 s wall clock**, `eval/model_invariance.py` (96 reviews, three hostile models) in ~2 s, and
`tools/check_results.py` re-asserting **23/23** published claims from raw JSON. One live review,
`case_12_release_train`, prints `BLOCK (3 blocker / 5 high)`. So the v3 claims are not the weak part
of this submission and v4 must not spend its time there.

**M2. The binding constraint at v4 is the submission form, not the engine.** The description field
hard-caps at 10,000 characters and the v3 text was ~12.1k, so the form rejected it. A submission that
cannot be saved scores zero on all six rubric rows. Every sentence added to the description now costs
another sentence, so the cut has to come out of prose and never out of a number.

**M3. Three hidden assumptions survive v3.** Two are disclosure failures, fixable in the text. One is
a real open experiment that cannot be closed before the deadline, so it gets written down rather than
buried (section 1).

**M4. Two radically different architectures were specified and rejected with reasons** (section 2).
One of them, Breaker vs Builder, attacks precisely the failure mode the README names as fatal, so it
is logged as the roadmap mechanism instead of as a variant that lost an argument.

---

## 1. Critique layer: three hidden assumptions in the shipped approach

### C1. The answer key and the detector share an author, and worse, an ontology
`0.970` strict F1 is measured against twelve labels written by the same person who wrote
`sentinel/hazards.py` and `eval/scoring.py`.

*Evidence for the defence, run rather than asserted:* every identifier appearing in the twelve case
files (`customers`, `invoices`, `mrr_cents`, `country_code`, `invoice_number`, ...) was grepped
against `sentinel/hazards.py`, `sentinel/agents/risk_officer.py` and `sentinel/coverage.py`. **Zero
matches.** The rules are schema-agnostic; they were not fitted to these twelve schemas.

*Why that is necessary and not sufficient:* the **hazard vocabulary** was chosen after reading the
cases, so the label and the detector still share an ontology. A hazard class that is not in the
vocabulary is invisible to the pipeline *and* to the scorer, and a case containing only such a hazard
would be scored as a clean pass by both. The untested claim is generalization to a schema and a
hazard class chosen by somebody else.

*Cheapest falsification, not in this submission:* freeze the code, have a second engineer write
case 13 against a different schema, publish whatever falls out. Anything I write myself inherits the
same ontology and proves nothing.

### C2. "Reproducible" was quietly doing the work of "deterministic"
Every headline number is produced against a scripted/cassette model. That is exactly what makes
`0/84` measurable and `$0.00` honest, and it also means **no published number was produced against a
real frontier model over a real network**. `sentinel/llm/remote.py` exists and is deliberately off
the evidence path. A judge can reasonably read "0/12 unsafe approvals" as "0/12 with a real model",
which is not what was measured.

The true scope is stronger and stranger than the one v3 implied: *with any model, including three
built to sabotage the review, because the model cannot reach the decision surface at all.* v3 owned
that in `results/model_invariance.md` and never said it in the description. **Fixed in v4:** the
headline table now carries `Facts a hostile model can change: 0/84` beside the detection metrics, and
the invariance section states the scope in one sentence.

### C3. The only claim whose sign depends on my own choices was printed beside the hard counts
Reviewer minutes are modelled from four constants, and `eval/time_sensitivity.py` shows **two of six**
constant sets flip the sign (-12% cheap-plan/dear-gate, -5% reading-dominates). In v3 that number sat
in the same table as unsafe approvals and hazard recall, borrowing their credibility, with the word
"modelled" in a footnote two screens below. **Fixed in v4:** the cell itself reads
"Reviewer min/case (**modelled**, not measured)", and the reproducibility section reports *both*
reversals instead of the one that was easier to explain.

### C4. Restated because it is the question a judge will ask
The narrator guard is audited with the same pattern family it enforces, so the audit measures whether
the guard catches what it already looks for. A fluent lie in words `sentinel/narrator.py` does not
know about still reaches the reviewer. The structural fix, specified and not shipped: never let the
model write the headline. Render it from tool output always and use the model only for the per-hazard
explanation, where a lie sits directly beside the engine error text that contradicts it.

---

## 2. Variation operator: two radically different designs, and why neither shipped

### V1. Compiler, not committee
Delete the five agents. Compile the migration plus the corpus into a dataflow IR and discharge
hazards as constraint obligations over column liveness, lock class and value-domain shrinkage: an SMT
solver instead of a rule list, with the model used only to explain an unsat core in English.

*What it buys:* soundness instead of recall. No prompt surface at all, so C2 becomes trivially true.
The coverage ledger falls out for free as "statements not expressible in the IR", which is a cleaner
definition of a blind spot than the one `sentinel/coverage.py` computes today.

*What it costs:* every new hazard needs an encoding before it can be detected, which is weeks and not
hours. Nothing in the submission would demonstrate agent orchestration, which is 30 of 100 points.
And the honest F1 of a half-finished encoder is worse than the honest F1 of rules plus replay.

*Verdict:* wrong for a three-day sprint, right for a product. Rejected, logged.

### V2. Breaker vs Builder, an adversarial game instead of a fixed pipeline
Replace the linear five-agent pipeline with two agents in a loop. A **Breaker** whose only job is to
author a query, view or workload that the proposed plan breaks. A **Builder** that must revise the
plan until the Breaker fails N rounds in a row. The corpus stops being the world, because the Breaker
*generates* consumers instead of reading the ones it was handed.

*What it buys:* it attacks the exact failure mode the README names as fatal, including the `case_09`
dbt model that lives outside the corpus. It is the only design considered here that could move recall
past 0.970 without touching the answer key.

*What it costs:* generated attacks have no ground truth, so the verdict degrades to "survived K
rounds", which cannot sit in the same table as a twelve-case answer key. The loop is
nondeterministic, which kills the invariance measurement that is v3's strongest single result. Cost
per review goes from `$0.00` to real money, and reproducibility from "run it and get the same bytes"
to "run it and get a distribution".

*Verdict:* rejected as this submission's architecture, adopted as the roadmap mechanism.

### What the variation operator actually changed
Nothing under `sentinel/`. It changed the failure-mode section: because V2 exists as a specified
design, the submission now names a *mechanism* for removing the corpus limit instead of admitting the
limit and stopping. That is the difference between a stated weakness and an engineering plan.

---

## 3. Self-review of the v3 submission text: what was wrong, and the rewrite

**Mistake 1, fatal and boring: the description was over the hard limit.** ~12.1k characters against a
10,000 cap, rejected by the form. Fixed: rewritten to **9,834 characters, counted rather than
estimated**, with the cut taken entirely out of prose. Two tables gained rows; no number was dropped.

**Mistake 2: the sensitivity claim under-reported its own counter-evidence.** v3 wrote "three written
to break the claim" and then quoted one reversal (-12%). Two of the three reverse (-12% and -5%).
Quoting one when two exist is exactly the repricing `eval/time_sensitivity.py` was written to
prevent, performed in the sentence describing it. Fixed: both reversals in the description.

**Mistake 3: hard favourable numbers were cut while soft prose stayed.** "False alarms on the one
clean case: 1 / 1 / **0**" and "severity agreement: 0.611 / 0.550 / **0.969**" were in
`results/comparison.md` and absent from the description, while two paragraphs restated the
coverage-gate argument. A judge reading only the description could not see that both baselines cry
wolf on the single genuinely safe migration, which is half the case for precision mattering. Fixed:
both rows restored, coverage-gate argument stated once.

**Mistake 4, outside the text: a submission-integrity risk.** The upload widget in the last screenshot
still names `...migration-sentinel-v2-source.zip`, while the description describes v3 behaviour
(`sentinel/narrator.py`, `sentinel/llm/adversarial.py`, the coverage gate). Verified in this session:
the archive under review *is* the v3 tree, containing both files, passing 27/27 tests and re-asserting
23/23 claims. A v2 zip beside a v3 description fails the completeness and reproducibility gate before
rubric scoring starts, so confirm the replace persisted before the deadline.

---

## 4. What v4 deliberately did not do

No file under `sentinel/`, `eval/`, `results/` or `trajectories/` was touched. Every number quoted
here was produced by re-running the shipped harnesses in a clean container with no network. A judge
diffing v3 against v4 should find the same engine and a more honest packet, which is the only kind of
improvement worth making twelve hours before a deadline.
