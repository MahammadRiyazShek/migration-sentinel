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
  the band in `results/time_sensitivity.md` including the constant set where the claim collapses
* the decision to leave `case_09` and `case_12` as documented misses rather than extend the parser
  until the case set went green
* the rejection of the autonomous-shell architecture and of pure static analysis
  (`docs/DESIGN_LOG.md`)
* the human approval gate: that `sentinel review` never touches a database, that `sentinel execute`
  refuses without `--i-approve --reviewer "name"`, and that a `BLOCK` verdict needs a named override on
  the record

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
  trace is worse than a missing one, because it looks like evidence.
* **The in-product trajectories under `trajectories/` are recorded by the harness**
  (`sentinel/trace.py`) during `python eval/run_eval.py` and regenerate byte-identically from a clean
  clone. They are machine output, not edited narrative.
* **The committed numbers come from the offline scripted model** documented in
  `sentinel/llm/scripted.py`, not from a hosted model. The hosted path is wired and documented
  (`--provider openai`, plus a record/replay cassette so a hosted run can be re-run offline byte for
  byte), and no hosted run is committed, so no claim in the README depends on one.
* **No credentials, API keys, connection strings or personal data appear in any attached trace.** That
  is enforced by the secret scan in `tools/collect_agent_traces.py`, not asserted by eye.