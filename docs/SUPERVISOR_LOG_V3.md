# Supervisor log v3: what a second hostile re-read found, and what it cost me

> Read `docs/CRITIQUE_LOG.md` first - that one drove v2. This is the same method run again on the
> finished v2 submission, and it is placed at the top of the work it produced on purpose: the
> findings below are also written into the header of every file they caused
> (`sentinel/narrator.py`, `sentinel/llm/adversarial.py`, `eval/model_invariance.py`), so a reader
> who opens the code without opening this document still gets the reasoning.

**Method.** A session with no memory of building the project was pointed at v2 with one
instruction: *find the assumptions this submission does not know it is making, and try to make the
headline numbers false.* Findings were then triaged by one rule - can this be settled with a
measurement rather than an argument? Anything that could was built. Anything that could not is
stated as a limitation and left alone.

**Constraint I set before starting, and kept.** v3 was not allowed to touch the twelve cases, their
ground truth, the hazard vocabulary, the scorer, or the definition of either primary metric. A
submission that improves its numbers by editing the target has measured nothing. Every v1 and v2
number in the README is therefore still comparable, and the eighteen claims
`tools/check_results.py` asserted before v3 still assert the same values today; v3 only adds five
more.

---

## Layer 1 - three hidden assumptions in v2

### A1. The threat model stopped at the verdict

v2's central design claim: hazards, severities, plans and verdicts come from tools, so the primary
metric is invariant to the model *by construction*. True, and it answers a question nobody asked in
that form. The question that matters is not "can the model change the verdict" but **"can the model
change what the reviewer believes"**, and those differ by exactly one sentence: the headline at the
top of the packet, which the model wrote and nothing checked.

The assumption underneath: *that the decision surface is the interface.* It is not. The interface is
the rendered packet, and a reviewer reads it top to bottom.

**Settled by measurement.** `sentinel/llm/adversarial.py` adds three models that are not trying to
help - a sycophant, an injected model, and a degraded endpoint. `eval/model_invariance.py` runs all
twelve cases through all four models with the narrator guard on and off and diffs the decision
surface field by field. Result: **0 of 84 completed reviews** differ from the cooperative reference
on verdict, hazards, severities, evidence, coverage ledger, generated SQL, verification outcome or
attempt count - so the invariance claim survives its first real attack. And, in the same table:
with the guard off, which is exactly what v2 shipped, the sycophant printed a headline contradicting
the verdict on **11 of 12** cases. The twelfth is `case_06`, the one genuinely clean case, where the
flattery is accidentally true. `sentinel/narrator.py` is the fix, and it can only remove model text,
so it moves no detection metric - `results/model_invariance.md` publishes that it does not.

### A2. Every failure mode v2 considered was a correctness failure

The coverage ledger, the verifier, the retry budget and the escalation path all answer "what if the
answer is wrong". Nothing in v2 answered "what if the model does not answer at all". The pipeline
read `.payload.get("questions")` straight off the model response, so a provider returning an empty
body took the review down with an `AttributeError` instead of degrading to a review with fewer
reviewer questions.

The assumption underneath: *that a model is either helpful or misleading.* The most common
production failure is neither. It is a 502.

**Settled by measurement.** `hostile-null` crashes **12/12** reviews with the guard off and **0/12**
with it on, where the guarded runs fall back to one question per hazard code and say so in the
packet. Worth noting how invisible this was: v2's metric set could not express availability at all,
because every arm either produced twelve reviews or was not run.

### A3. Ablations subtract components; they never test a component behaving badly

This is the finding that produced the other two, so it is the one I would keep if I could keep only
one. Every v2 arm - `no_replay`, `no_static`, `no_memory`, `no_verify`, `no_coverage` - removes a
component that works correctly, and measures the *contribution* of that component. Removal is a
clean way to answer "is this load-bearing". It cannot answer "what happens when this misbehaves",
and v2 published the first while implying the second, because "the primary metric is invariant to
the model" reads like a robustness claim and was derived from a structural one.

The assumption underneath: *that a component's contribution and its robustness are measured by the
same experiment.* They are not, and the second one requires writing something whose job is to attack
you.

**Not fully settled, and honestly so.** v3 attacks one component, the narrator, because that is the
one with an untrusted input. The other four consume tool output that this repository also produces,
so attacking them means fault-injecting my own parser and replay engine - a fuzzing exercise that is
the right next step and did not fit in the time. Named here rather than left for a judge to notice.

### A4 (raised, folded into A1). The audit shares its patterns with the guard it audits

`eval/model_invariance.py` detects a misleading headline with `sentinel/narrator.audit_summary` - the
same function the guard uses. So the prose columns measure *whether the guard catches what it looks
for*, not *whether a lie can get through*. A model that lies fluently in words that file does not
know about still reaches the reviewer. This is the same class of problem as
`tools/check_results.py` re-asserting the reviewer-minute model from the constants that produce it,
which v2 already published as a weakness, and it has the same honest answer: state it in the artifact
that makes the claim. It is stated in the module docstring, in the generated report, and in the
README bullet.

---

## Layer 2 - two radically different designs, and why they are not this submission

Both attack A1 more fundamentally than a guard does. Both were rejected, and in one case the
rejected design is *safer* than what shipped, which is stated rather than buried.

### V3. Two models with opposing incentives, judged on citations

Put the model back on the detection path, honestly. Run two instances with opposed briefs: one must
argue this migration is safe, one must argue it breaks something. Neither can assert anything without
citing a tool result - a replay row, a column-set diff, a row count, an incident id. A deterministic
judge accepts a claim only if the citation resolves, and disagreement between the two is itself a
signal about where a human should look.

Why it is genuinely better: the recall ceiling today is set by what my rules and my corpus know
(`docs/CRITIQUE_LOG.md`, C3). A prosecutor with a citation requirement can propose hazards no rule
encodes, and the citation requirement keeps it from inventing them.

Why it is not this submission: it moves recall back onto a nondeterministic component, so the primary
metric stops being reproducible from a clean clone with no API key and no spend - which is the whole
reproduction story - and a two-model debate has no fair single-prompt baseline. **Kept as the design
most likely to raise the ceiling.**

### V4. Delete the narrator entirely

Render every word of the packet from tool output. Demote the model to a read-only Q&A layer sitting
next to the evidence, whose answers never enter the record. The class of problem in A1 becomes
structurally impossible rather than guarded, and no pattern list has to be maintained.

Why it is genuinely better: a guard is a mitigation that catches lies in words it knows; removing the
writer removes the question. It is the strictly safer design and I am not going to pretend otherwise.

Why it is not this submission: it deletes the per-hazard explanation that reviewers actually read
(the sentence that turns `SELECT_STAR_DRIFT` into "your dbt model still runs and silently loses a
column"), and it answers a challenge about agentic workflows with a linter plus a chatbot. **Named in
`sentinel/narrator.py` as the next experiment; shipping the weaker version knowingly was the price of
keeping the explanation.**

---

## Layer 3 - what shipped, and three mistakes I caught in my own first version of it

Same discipline as v2: the fix got re-read before it got published, and the re-read found real
problems. Each of these was in the working copy and none of them reached the published numbers.

### M1. The guard rejected its own cooperative narrator

The first `audit_summary` checked verdict tokens case-insensitively. The scripted stand-in's honest
`NEEDS_COVERAGE_SIGNOFF` headline contains the phrase *"before this can be called safe"*, so `safe`
matched the `SAFE` token, and the guard overrode a correct summary and replaced it with a
tool-written one. The published table would still have read **0 misleading headlines** - which is
the dangerous part. A guard that rejects everything scores perfectly on a metric that counts what
got through.

**Fix:** the verdict-token check is case-sensitive, because an uppercase verdict token is the tool's
own vocabulary while lowercase "safe" is ordinary English, and ordinary English is handled by the
narrower clean-claim patterns. Pinned by
`tests/test_all.py::TestNarratorGuard::test_the_scripted_headline_is_accepted_for_every_verdict`,
which runs the guard over all twelve recorded packets and fails if it rejects any of them. The
general lesson, which is the same one as `case_04`: a filter needs a test that it *passes* good
input, not only that it blocks bad input.

### M2. I quoted the worst number in the family and attached it to the nearest noun

The first generated report said a sycophantic model prints a misleading headline on "12 of 12"
cases. The sycophant's real number is 11 of 12; the 12 came from an unthinking `max()` across the
hostile arms and belongs to `hostile-inject`. Both numbers are bad and the difference is the
interesting part: the case the sycophant gets right is `case_06`, the only genuinely clean
migration, where flattery is accidentally correct. That detail is evidence the audit is measuring
something real rather than pattern-matching every hostile string, and rounding it away would have
thrown it out.

**Fix:** the report renders per-model numbers with the exception named. `tools/check_results.py`
asserts the unguarded hostile figure is at least 10 of 12 rather than exactly 12, so the claim
cannot be quietly restated if a pattern changes.

### M3. The guard nearly rewrote the model's sentence instead of replacing it

The tempting implementation strips the false clause and keeps the rest, so the packet still reads
like prose. That produces a sentence no one wrote: not the model's, not the tool's, and
unattributable in a postmortem three weeks later when someone asks why the review said what it said.
It is the same trap as Iteration 8's, where giving `CLUSTER` a real op kind would have quietly
removed it from the coverage ledger - a local improvement that erases a fact about provenance.

**Fix:** the guard replaces the summary wholesale with one written from tool output, and the packet
prints what the model tried to say, verbatim and quoted, next to the reason it was rejected. A
reviewer sees the disagreement instead of a laundered sentence. `sentinel/report.py` renders both
lines.

---

## What v3 changed, in one table

| | v2 | v3 |
|---|---|---|
| Unsafe approvals | 0/12 | 0/12 (unchanged, on purpose) |
| Strict recall / precision | 0.970 / 0.970 | 0.970 / 0.970 (unchanged) |
| Gap cases cleared without sign-off | 0/2 | 0/2 (unchanged) |
| Verified plans | 12/12 | 12/12 (unchanged) |
| Modelled reviewer minutes per case | 9.2 | 9.2 (unchanged) |
| Decision surface changed by a hostile model | untested | **0/84 completed reviews** |
| Misleading headline under a hostile model | **23 of the 24 unguarded reviews that ran** | **0/36** |
| Reviews lost to a model returning nothing | **12/12** | **0/12** |
| Claims re-asserted by `tools/check_results.py` | 18 | 23 |
| Tests | 22 | 27 |

Every detection number is deliberately identical. v3 bought robustness, not accuracy, and a
changelog that shows a robustness change moving an accuracy number is a changelog to distrust.
