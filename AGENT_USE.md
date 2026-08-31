# Coding-agent use and tool disclosure

micro1 requires coding-agent use, requires participants to disclose the tools they used, and gates
rubric scoring behind a trace check. This file is that disclosure.

It covers the agents that **built** Migration Sentinel. The five agents that **run inside** it are a
different thing and their runtime traces are separate: [`trajectories/`](trajectories/) and
[`docs/AGENT_TRAJECTORIES.md`](docs/AGENT_TRAJECTORIES.md).

## Agents and tools used to build this project

| tool | model | interface | what it was used for |
|---|---|---|---|
| Claude Opus 5 (Anthropic) | `claude-opus-5` | conversational, in-context; not an autonomous CLI harness with shell access | Implementation of everything under `sentinel/`, `baseline/`, `eval/` (harness and scorer code, not the labels), `site/`, `tools/` and `tests/`, from a design and a hazard vocabulary I set first. Also the prose in `README.md`, `REPRODUCTION.md` and `docs/`. |
| Claude Opus 5, second session, supervisor role | `claude-opus-5` | separate context, given only the built repository and the challenge rules | An adversarial review pass over the finished submission: unzip, run, try to falsify the claims. It produced `eval/report_components.py`, `eval/time_sensitivity.py`, `tools/collect_agent_traces.py` and the first draft of this file. It did not touch pipeline code. |
| Claude Opus 5, third session, supervisor role | `claude-opus-5` | separate context, given the finished v1 submission text and the shipped repository, with one instruction: find the assumptions this submission does not know it is making and try to make the headline numbers false | Produced the critique in [`docs/CRITIQUE_LOG.md`](docs/CRITIQUE_LOG.md), the two rejected alternative designs written up there, and the implementation of v2: `sentinel/coverage.py`, the verdict cap, the whole-relation maintenance rule, the `no_coverage` ablation arm, the new scorer fields and the five `TestCoverageLedger` tests. Its sharpest finding lowered nothing and *raised* a published cost: the reviewer-minute claim got worse and two adversarial constant sets went from collapsing to reversing. |

| Claude Opus 5, fifth session, supervisor role (ClickUp Brain agentic assistant) | `claude-opus-5` | separate context, given the v2 source archive and the submission form text, with a sandboxed Python shell and **no network access**; same instruction as the third session | Produced [`docs/SUPERVISOR_LOG_V3.md`](docs/SUPERVISOR_LOG_V3.md) and the implementation of v3: `sentinel/narrator.py`, `sentinel/llm/adversarial.py`, `eval/model_invariance.py`, the `--no-narrator-guard` switch, five new claims in `tools/check_results.py` and the five `TestNarratorGuard` tests. It ran the eval, the invariance harness, the tests and the claim audit itself in the sandbox. It did not touch the twelve cases, the ground truth, the hazard vocabulary, the scorer or either primary metric, and no detection number moved. |

| Final packaging audit, fourth session | not disclosed to participant (Genspark AI assistant) | separate context, given the v2 source archive and the submission form text | Found that `agent_traces/INDEX.md` was referenced but absent; populated `agent_traces/` from real session artefacts only, regenerated the index with `tools/collect_agent_traces.py --write`, and re-ran the eval, tests and claim audit. It did not touch pipeline code, cases, ground truth or the scorer. |

No other coding agent, autocomplete or code-generation tool was used. No agent had shell access to a
machine of mine, a network credential, or write access to a repository; every change arrived as text I
read, applied and ran.

**The second session is disclosed for a reason.** Its whole job was to attack the first session's
output, and it found three things worth having: that the repo contained no tool disclosure at all
(this file), that two of five components looked decorative because the ablation was reported as
per-arm scores instead of cost-of-removal (`eval/report_components.py`), and that the reviewer-minute
claim was audited by `tools/check_results.py` using the same four constants that produce it, which
cannot fail (`eval/time_sensitivity.py`, which found the collapse case). Same model, different
context, adversarial framing. Two of those three findings are now committed artefacts, and the third
one lowered a headline claim.

**The fifth session is the one to read the log of.** Its instruction was the third session's: attack
the finished submission. What it found was not a wrong number, it was a wrong *audience* - every metric
in v2 read the decision surface, and the reviewer reads the headline sentence, which was the one thing
a model wrote and nothing checked. It also found a plain bug that four earlier sessions and I had all
walked past: `.payload.get("questions")` on a raw model response, so a provider returning an empty body
crashed the review instead of degrading it. Neither finding was reachable by removing a component,
which is the only kind of experiment v2 ran. Three mistakes in its own first fix are logged in
`docs/SUPERVISOR_LOG_V3.md` (M1-M3), including a version of the guard that rejected the cooperative
narrator's own correct summary while still publishing "0 misleading headlines".

## How the work was divided

I delegated implementation and kept specification, ground truth and judgement. The design log in
[`docs/DESIGN_LOG.md`](docs/DESIGN_LOG.md) was written before implementation and it is the document the
agent worked from, so the architecture is not an agent artefact even though almost every line of code
is.

Four specific moments, because "I supervised it" is not evidence:

* **I overruled the obvious architecture.** The agent's first proposal, and the one it kept returning
  to, was a single autonomous agent with a shell and a real PostgreSQL container: restore a dump, apply
  the migration, grep the repo, run the tests. Strictly more capable, and it would have caught the
  `CLUSTER` statement in `case_12`. I rejected it because two runs take different paths, so a reviewer
  cannot distinguish "checked and clean" from "did not look there", and the audit trail degenerates into
  a shell history. A fixed pipeline where every claim maps to a named tool call is worth more at a step
  that gates a production deploy. Rejection and reasoning are in `docs/DESIGN_LOG.md` under Variation 1.
* **I ran the experiment that contradicted the plan, and kept the result.** The replay-only arm scored
  *worse* than rules-only on the primary metric (2 unsafe approvals against 1). The tempting move was
  to bury it as an implementation detail of orchestration. It is now the load-bearing row of the
  changelog and the hot take.
* **I refused to edit ground truth after seeing a result.** On `case_04` the pipeline flagged
  `CROSS_SERVICE_UNCOORDINATED` because a billing-owned migration breaks the web signup insert. That is
  correct and my ground truth had forgotten it. Changing the label would have raised strict precision.
  It is still counted against the pipeline as a false positive.
* **A test caught an agent-introduced bug that no metric would have caught.** The first column parser
  used a greedy `[\w ]+` for type names, so `ADD COLUMN x TEXT NOT NULL` parsed as nullable and the
  `NOT_NULL_NO_DEFAULT` hazard silently vanished. Recall barely moved, which is exactly why it was
  dangerous. Fixed and pinned by `tests/test_all.py::TestParser`. It is the scariest bug class in this
  project: a parser that fails quietly makes the whole pipeline confidently wrong.

I also fixed the agent's unfair baseline. Its first baseline prompt did not receive the rollback
script, so the baseline flagged `MISSING_ROLLBACK` on every case including the six that ship one, which
inflated the gap. The baseline now sees the rollback and those false positives are gone. A rigged
baseline makes the whole report worthless even when the real gap is large.

## Human checkpoints

Every one of these was my decision, not the agent's:

* the twelve case definitions and their ground-truth hazard sets ([`eval/cases/`](eval/cases/), built
  by `eval/build_cases.py`), written before the first pipeline run
* the hazard vocabulary and the severity ladder ([`sentinel/hazards.py`](sentinel/hazards.py))
* the scorer and its matching rules ([`eval/scoring.py`](eval/scoring.py))
* the primary metric: unsafe approvals rather than F1, chosen before any number existed
* the four reviewer-minute constants (`TIME_MODEL` in `eval/scoring.py`), and the decision to publish
  the band in `results/time_sensitivity.md` including the constant sets where the claim collapses - and,
  in v2, the two where it now reverses. The agent's first instinct on seeing the reversal was to
  reprice `decide_human_gate_minutes`. I overruled it: repricing a constant to make an inconvenient row
  disappear, in the one file whose purpose is to stop me doing that, is the most self-serving edit
  available in this project. The number is published as it fell out and `tools/check_results.py` now
  asserts the coverage gate *costs* reviewer minutes, so the trade cannot be quietly reversed later.
* the second primary metric in v2 (coverage-gap cases cleared without a sign-off) is defined as a
  property of the **case**, computed once from the migration and the corpus and applied identically to
  every arm, so no arm gets to grade its own blind spots. The agent's first draft measured each arm
  against its own declared gaps, which would have let a reviewer that declares nothing score perfectly.
* the decision to leave `case_09` as a documented miss rather than write a rule shaped like its label.
  The consumer it hides is a dbt model in another repository; a rule that pattern-matched
  `UPDATE ... WHERE col IS NULL` straight onto `CROSS_SERVICE_UNCOORDINATED` would have taken recall to
  33/33 by fitting the answer key. What shipped instead argues about the tool's own reach - an in-place
  rewrite is unobservable to replay - so the verdict is capped and the hazard is still counted as missed.
  Recall is 0.970, not 1.000, and that is the honest number.
* the `case_12` decision in the other direction: `CLUSTER` is one of a documented family of
  whole-relation commands, so recognising it is a rule about a class rather than a patch for a case. The
  guard is that it stays in the coverage ledger, which is asserted by a test
* the rejection of the autonomous-shell architecture and of pure static analysis
  (`docs/DESIGN_LOG.md`)
* the human approval gate: that `sentinel review` never touches a database, that `sentinel execute`
  refuses without `--i-approve --reviewer "name"`, that a `BLOCK` verdict needs a named override on the
  record, and that an uncleared coverage gap is refused the same way
* in v3, the rule that the narrator guard may only **remove** model text, never rewrite it. The
  tempting version strips the false clause and keeps the sentence, which produces prose that neither
  the model nor the tool wrote and that nobody can attribute in a postmortem. What shipped replaces the
  headline wholesale and prints what the model tried to say, verbatim, next to the reason it was
  rejected
* in v3, the decision to publish `results/model_invariance.md` with every detection number identical to
  v2. A robustness change that appears to improve accuracy is a changelog to distrust, and the guard is
  structurally incapable of it: it can only delete text a metric never read
* in v3, the rejection of the *safer* design. Deleting the narrator entirely (render every word from
  tool output, demote the model to read-only Q&A) makes the whole class of problem impossible instead of
  guarded. It also deletes the per-hazard explanation reviewers actually read, so it is named as the
  next experiment in `sentinel/narrator.py` rather than shipped, and the weaker choice is stated as a
  choice
* the rule that a coverage gap is never expressed as a hazard. Absence of evidence gets a named human
  decision, not a severity. An agent that converts "I could not check this" into a finding is inflating
  its own recall with its own ignorance

The first four matter most. **The agent wrote the solution; it did not write the exam.** If it had
written both, every metric in the README would be self-graded and worth nothing.

## Trace index

Development-agent traces are indexed in [`agent_traces/INDEX.md`](agent_traces/INDEX.md). That index is
**generated, not written**:

```bash
python tools/collect_agent_traces.py --write
```

It enumerates the files actually present under `agent_traces/`, records size and a SHA-256 prefix for
each, greps every one for key, token and connection-string shapes, and exits non-zero rather than write
an index on a hit or on an empty directory. So the index cannot claim a trace the repository does not
contain, which is the same discipline `tools/check_results.py` applies to the results.

Runtime traces of the five in-product agents, which are challenge deliverable 04 and a separate thing
from this disclosure:

| file | agent | what it shows |
|---|---|---|
| [`trajectories/case_01_rename_with_compat_view.md`](trajectories/case_01_rename_with_compat_view.md) | all five | one full review including the Verifier rejecting the first plan and the retry that fixed it |
| [`docs/AGENT_TRAJECTORIES.md`](docs/AGENT_TRAJECTORIES.md) | all five | instructions, tool calls and tool responses, agent by agent |
| `trajectories/<case>.jsonl` | all five | one machine-readable trajectory per case, twelve of them, regenerated by `python eval/run_eval.py` |

## What is not in these traces

Stated plainly, because a gap I declare costs nothing and a gap a judge finds costs the integrity
check.

* **Anything not listed in `agent_traces/INDEX.md` was not captured.** The index is generated from disk,
  so that sentence is checkable rather than rhetorical. Early exploratory turns and anything in a
  context that was cleared are gone. I have not reconstructed a transcript after the fact: a rebuilt
  trace is worse than a missing one, because it looks like evidence. Sessions one and two predate the
  trace-capture decision, so their committed artefacts stand where transcripts would, and the
  index says so per file.
* **The in-product trajectories under `trajectories/` are recorded by the harness**
  (`sentinel/trace.py`) during `python eval/run_eval.py` and regenerate byte-identically from a clean
  clone. They are machine output, not edited narrative.
* **The committed numbers come from the offline scripted model** documented in
  `sentinel/llm/scripted.py`, not from a hosted model. The hosted path is wired and documented
  (`--provider openai`, plus a record/replay cassette so a hosted run can be re-run offline byte for
  byte), and no hosted run is committed, so no claim in the README depends on one.
* **No credentials, API keys, connection strings or personal data appear in any attached trace.** That
  is enforced by the secret scan in `tools/collect_agent_traces.py`, not asserted by eye.