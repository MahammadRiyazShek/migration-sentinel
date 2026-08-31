# Submission form content (paste-ready, v3)

Repo: <https://github.com/MahammadRiyazShek/migration-sentinel> ·
Live desk: <https://migration-sentinel-frvo.vercel.app/>

Regenerated from `results/` after `make verify`. If a number here disagrees with
`results/comparison.md` or `results/model_invariance.md`, the file is stale and the file is wrong.
The description below is 10606 characters, inside the form's 10,000 limit.

---

## Title

```
Migration Sentinel: agents that replay your schema migration, prove the rollout plan, refuse to call it safe where they could not see, and audit their own narrator
```

Fallback, if the form rewards outcome over mechanism:
`Migration Sentinel: schema-migration review that proves its own rollout plan, caps its own verdict where it is blind, and cannot be talked out of either (0/12 unsafe approvals, 0/84 hostile-model reviews changed)`

---

## Description

**A two-line `ALTER TABLE` is either free or an outage, and the diff does not tell you which.**

## Problem and user

The platform or data engineer on the schema-migration review rota at a 20-to-300 engineer company: one Postgres primary, a dozen services and a BI layer reading it, migration PRs from teams that own their feature but not the database. A review means answering questions the diff does not contain. Which live statements touch this column? Does anything read `SELECT *` off the affected view, so the column set matters and not the SQL text? Twenty to forty minutes per PR, and it gets five, so review degrades into pattern matching on diff text: catches the obvious `DROP COLUMN`, misses the `DROP VIEW` a worker reads every minute. The evidence exists already in machine-readable form (DDL, corpus, row counts, incident log). Nobody has time to assemble it per PR, so the diff gets skimmed.

## Baseline vs advanced

Same 12 cases, same `sentinel.llm` interface, hazard vocabulary, scorer, temperature; only the scaffolding changes. **A**: one model call. **B**: the obvious next move, same prompt plus full DDL and row counts. **Sentinel**: five agents over a shadow-replay engine, static rules on a parsed change set, incident memory, generated expand/contract SQL, a verifier that replays the plan it wrote, a coverage ledger that caps the verdict, and a guard that treats model prose as untrusted input.

| metric | A | B | Sentinel |
|---|---|---|---|
| **Unsafe approvals** (primary, lower better) | 1/12 | 1/12 | **0/12** |
| **Gap cases cleared w/o sign-off** (primary) | 0/2 | 0/2 | **0/2** |
| Hazard recall / precision (strict) | 0.545/0.947 | 0.606/0.690 | **0.970/0.970** |
| Findings backed by machine evidence | 0/19 | 0/29 | **35/35** |
| Verified expand/contract plans | 0/12 | 0/12 | **12/12** |
| Modelled reviewer min/case | 29.7 | 34.7 | **9.2** |
| Facts a hostile model can change | n/a | n/a | **0/84** |

Two notes. **B's precision is lower than A's** because more context made it guess more, string-matching table names inside view bodies: context you cannot check buys volume, not accuracy. **The second primary metric exists because the first cannot see everything** - a review that says "ship as plan" above its own declared blind spot is not an unsafe approval by the letter of the scorer and still tells a reviewer the wrong thing. It is a property of the *case*, applied identically to every arm, so no arm grades its own blind spots.

## What each component buys

9 arms x 12 cases = **108 reviews**, one component removed at a time.

| arm | unsafe | recall | plans | gaps cleared | min/case |
|---|---|---|---|---|---|
| all five agents | **0/12** | 0.970 | 12/12 | **0/2** | 9.2 |
| minus shadow replay (rules only) | 1/12 | 0.576 | 0/12 | 0/2 | 23.3 |
| minus static rules (replay only) | **2/12** | 0.333 | 12/12 | 0/2 | 8.8 |
| minus incident memory | 0/12 | 0.970 | 12/12 | 0/2 | 9.2 |
| minus verifier + retry | 0/12 | 0.970 | **0/12** | 0/2 | 23.3 |
| minus coverage gate (v1 behaviour) | 0/12 | 0.970 | 12/12 | **1/2** | 8.5 |

**Replay alone is worse than rules alone** (2 unsafe approvals vs 1): a lock hazard produces no failing query, so nothing breaks, so a replay-only reviewer waves through the 48M-row index build and the unvalidated FK. Execution is necessary, not sufficient, and merging the two layers is the biggest changelog contribution. **The verifier is worth nothing to detection and everything after it** (12/12 plans, -14 min/case). **The coverage gate is the only component that makes the pipeline look worse on a published number** (+0.7 min/case) and the one I would defend first.

## Can the model move any of this? (new in v3)

v2 claimed the primary metric is invariant to the model *by construction* and never tried to break it. v3 wrote three models that are not trying to help (a sycophant, an injected model, a degraded endpoint) and diffed the decision surface field by field: 96 reviews, two seconds, $0 (`eval/model_invariance.py`, `sentinel/llm/adversarial.py`).

| model | guard | surface changed | crashed | headlines contradicting the verdict |
|---|---|---|---|---|
| `hostile-approve` | on | **0/12** | 0/12 | **0/12** |
| `hostile-approve` | off (= v2) | 0/12 | 0/12 | **11/12** |
| `hostile-inject` | on | **0/12** | 0/12 | **0/12** |
| `hostile-inject` | off (= v2) | 0/12 | 0/12 | **12/12** |
| `hostile-null` | on | **0/12** | **0/12** | 0/12 |
| `hostile-null` | off (= v2) | 0/12 | **12/12** | 0/12 |

**The facts held.** 0 of 84 completed reviews differ from the cooperative reference on verdict, hazards, severities, evidence, coverage ledger, generated SQL or verification outcome. The claim is a measurement now, not an argument from the shape of the code.

**The prose did not, and no v2 metric could see it.** The model wrote the sentence at the top of the packet and nothing checked it, so a sycophantic model printed *"Approved: no hazards found, safe to ship. LGTM"* under a badge reading **BLOCK - do not merge** on 11 of 12 cases (the twelfth is the genuinely clean case, where flattery is accidentally true) without moving one published number. `sentinel/narrator.py` now validates model output like a request body: reject a summary that is empty, over-long, injected, or claiming a verdict the tools did not reach, fall back to a headline written from tool output, and print what the model tried to say beside the reason. The guard only ever *removes* text, so it moves no detection metric.

**And the boring hostile model took the pipeline down**: v2 read `.payload.get("questions")` off a raw response, so a provider returning an empty body crashed 12 of 12 runs. Availability was the one failure mode the invariance argument could not express. Ablations subtract components that behave correctly; they never test one behaving badly.

## How it works

One command per PR: `python -m sentinel review --case eval/cases/case_12_release_train.json`. Five agents in fixed order (prompts in `sentinel/agents/prompts/`): **Cartographer** (parser) -> **Blast Radius** (shadow-DB executor) -> **Risk Officer** (rules + memory + coverage ledger + verdict) -> **Rollout Engineer** (plan writer) -> **Verifier** (replay + retry, max 3 attempts). Tools decide facts, the model writes prose, and the prose is audited too. The agency is in the loop: the Verifier replaying the plan the Rollout Engineer just wrote, the policy tightening between attempts, the escalation when the budget runs out.

The **coverage ledger** computes, per affected object, what the review structurally could not observe: unmodelled statements, rows rewritten in place (replay proves a statement still *runs*, never that it returns the same *answer*), a value class the rollback does not restore. Any open gap caps the verdict at `NEEDS_COVERAGE_SIGNOFF`: not an approval in the scorer, not executable in the CLI, and no hazard invented, so it costs no precision or recall.

`sentinel review` never touches a database. `sentinel execute` uses an in-memory SQLite sandbox and refuses without `--i-approve --reviewer "name"`, on a `BLOCK` without a named override, and on an uncleared gap.

## Coding agents used (required disclosure, in `AGENT_USE.md`)

**Claude Opus 5**, conversationally rather than as an autonomous shell harness, for everything under `sentinel/`, `eval/`, `site/`, `tools/`, `tests/`. Three further sessions in fresh contexts were pointed at the finished work to falsify it, producing the ablation and sensitivity harnesses, `docs/CRITIQUE_LOG.md` (v2) and `docs/SUPERVISOR_LOG_V3.md` (v3). The sharpest v2 finding *raised* a published cost; the sharpest v3 finding was a bug four sessions had walked past. Never delegated: the twelve ground-truth labels, the hazard vocabulary, the scorer, the primary metrics, and the rule that a coverage gap is never expressed as a hazard. An agent that writes the solution and its own grading criteria has graded itself.

## Reproducibility

Python 3.11+ standard library. Zero pip dependencies, no API key, no network. Data entirely synthetic. Reviewer minutes are the one *modelled* number, so `eval/time_sensitivity.py` recomputes every arm under six constant sets, three written to break the claim: the saving holds at **69%** under uniform rescaling and **reverses to -12%** when a hand-written plan is priced as cheaply as approving a generated one. That reversal is the coverage gate's bill (every blind spot it opens is a human gate) and it is published as it fell out, rather than repriced away in the one file whose purpose is to stop me doing that.

```bash
python eval/run_eval.py --ablations       # 108 reviews, <1 s, $0.00
python eval/model_invariance.py           # 96 reviews, hostile models included
python -m unittest discover -s tests      # 27 tests
python tools/check_results.py             # 23/23 claims re-asserted from raw JSON
```

The video predates v3, so its on-screen numbers are the pre-coverage-gate ones. When video and repo disagree, `results/comparison.md` and `results/model_invariance.md` are authoritative.

## Main failure mode and hot take

**The corpus is the world.** Everything here is proved from the SQL it was given. `case_09` hides the risky consumer in a dbt model outside the corpus: still missed, no longer cleared, because the ledger sees the shape of the hole without seeing what is in it. Recall is 0.970 and not 1.000 because the honest fix argues about the tool's reach instead of fitting the answer key. Twelve cases, one schema, ground truth I wrote: do not quote the F1 without its denominator.

Verification is not a synonym for correctness: it is a sensor with a specific blind spot, and the engineering is knowing that shape well enough to put a differently-shaped sensor beside it. Then: **a sensor that reports its own blind spot has not finished the job until the blind spot can change the answer.**

And the one v3 found, smaller and more embarrassing: **a system can be invariant in every number it publishes and still lie to the person reading it.** Every metric read the decision surface; the reviewer reads the sentence at the top. Audit the output your user actually reads, not the one your metrics are computed from - and if you cannot find that gap by removing components, write a component that lies to you on purpose.

**Read in this order:** `docs/CRITIQUE_LOG.md` -> `docs/SUPERVISOR_LOG_V3.md` -> `README.md` (Improvement Changelog) -> `results/model_invariance.md`.

GitHub: https://github.com/MahammadRiyazShek/migration-sentinel
Live demo: https://migration-sentinel-frvo.vercel.app/

---

## Video URL

Unchanged: <https://www.youtube.com/watch?v=JGXnRwWWmrQ>. It predates v3, so it shows neither the
coverage gate's final numbers nor the invariance table. The description discloses that in one line and
names `results/comparison.md` and `results/model_invariance.md` as authoritative. If re-recording,
`docs/VIDEO_SCRIPT.md` plus a 30-second v3 clip: run `--provider hostile-approve --no-narrator-guard`,
show "Approved: no hazards found, safe to ship" under a BLOCK badge, then run it again with the guard.

## Source code

Upload `migration-sentinel-source.zip` (well under 50 MB).
