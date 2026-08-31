# Submission form content (paste-ready, v5)

Repo: <https://github.com/MahammadRiyazShek/migration-sentinel> ·
Live desk: <https://migration-sentinel-frvo.vercel.app/>

Regenerated from `results/` after `make verify`. If a number here disagrees with
`results/comparison.md` or `results/model_invariance.md`, this file is stale and this file is wrong.
The description below is **9753 characters**, counted, inside the form's 10,000 limit. Paste it as-is;
it contains no characters outside Latin-1, because an earlier paste turned minus signs into mojibake.

---

## Title

```
Migration Sentinel: agents that replay your schema migration, prove the rollout plan, refuse to call it safe where they could not see, and take the headline away from the model that lied about it
```

Fallback, if the form rewards outcome over mechanism:

```
Migration Sentinel: schema-migration review that proves its own rollout plan, caps its own verdict where it is blind, and cannot be talked out of either (0/12 unsafe approvals, 0/168 hostile-model reviews changed, 0/48 misleading headlines)
```

---

## Description

**A two-line `ALTER TABLE` is either free or an outage, and the diff does not tell you which.**

## Problem and user

The platform or data engineer on the schema-migration review rota at a 20-to-300 engineer company: one Postgres primary, a dozen services and a BI layer reading it, migration PRs from teams that own their feature but not the database. A review answers questions the diff does not contain: which live statements touch this column, whether anything reads `SELECT *` off the affected view so the column set matters and not the SQL text. Twenty to forty minutes per PR, and they get five, so review degrades into pattern matching on diff text: catches the obvious `DROP COLUMN`, misses the `DROP VIEW` a worker reads every minute. The evidence already exists in machine-readable form (DDL, query corpus, row counts, incident log); nobody has time to assemble it per PR.

## Baseline vs advanced

Same 12 cases, same `sentinel.llm` interface, hazard vocabulary, scorer and temperature; only the scaffolding changes. **A**: one model call. **B**: same prompt plus full DDL and row counts. **Sentinel**: five agents over a shadow-replay engine, static rules on a parsed change set, incident memory, generated expand/contract SQL, a verifier that replays the plan it wrote, a coverage ledger that caps the verdict, and a packet whose verdict sentence no model can write.

Results as A / B / Sentinel:

- Unsafe approvals (primary, lower better): 1/12 / 1/12 / **0/12**
- Gap cases cleared without sign-off (primary): 0/2 / 0/2 / **0/2**
- Hazard recall, precision: 0.545, 0.947 / 0.606, 0.690 / **0.970, 0.970**
- Severity agreement on matched hazards: 0.611 / 0.550 / **0.969**
- False alarms on the one clean case: 1 / 1 / **0**
- Findings backed by machine evidence: 0/19 / 0/29 / **35/35**
- Verified expand/contract plans: 0/12 / 0/12 / **12/12**
- Reviewer minutes per case (**modelled**, not measured): 29.7 / 34.7 / **9.2**
- Facts a hostile model can change: n/a / n/a / **0/168**
- Misleading headline reaching the reviewer (48 hostile reviews): n/a / n/a / **0/48**

B's precision is lower than A's: more context made it guess more, string-matching table names inside view bodies. Context you cannot check buys volume, not accuracy. The second primary metric exists because the first cannot see everything: "ship as plan" above a declared blind spot passes the scorer and still tells the reviewer the wrong thing.

## What each component buys

9 arms x 12 cases = **108 reviews**, one component removed at a time (unsafe, recall, plans, gaps cleared, min/case):

- all five agents: **0/12**, 0.970, 12/12, **0/2**, 9.2
- rules only, no replay: 1/12, 0.576, 0/12, 0/2, 23.3
- replay only, no rules: **2/12**, 0.333, 12/12, 0/2, 8.8
- no incident memory: 0/12, 0.970, 12/12, 0/2, 9.2
- no verifier or retry: 0/12, 0.970, **0/12**, 0/2, 23.3
- no coverage gate (v1): 0/12, 0.970, 12/12, **1/2**, 8.5

Replay alone is worse than rules alone, 2 unsafe approvals against 1: a lock hazard produces no failing query, so nothing breaks, so replay-only waves through the 48M-row index build and the unvalidated FK. Execution is necessary, not sufficient; merging the layers is the biggest changelog contribution. The coverage gate is the only component that makes a published number worse (+0.7 min/case), and the one I defend first: any open gap caps the verdict at `NEEDS_COVERAGE_SIGNOFF`, which is not an approval in the scorer, not executable in the CLI, and invents no hazard, so it costs no precision or recall.

## Can the model move any of this? And can it lie about it?

v2 claimed model-invariance by construction and never tested it. v3 wrote three models that are not trying to help and diffed the decision surface field by field; v5 wrote a fourth, aimed at v3's own defence. 12 cases x 5 models x 3 narrator modes = **180 reviews**, a few seconds, $0.

**The facts hold.** 0 of 168 completed reviews differ from the cooperative reference on verdict, hazards, severities, evidence, ledger, generated SQL or verification outcome. No model can reach the decision surface.

**The prose was another matter, and each fix found the next bug.** v2 printed model text unchecked, so a sycophant put *"Approved: no hazards found, safe to ship"* above a `BLOCK` badge on 11 of 12 cases without moving one published number, and a dead endpoint crashed 12/12 runs on a raw `.payload.get()`. v3 answered with a blocklist and published `0/12`, then wrote its own limit into the module docstring: *the audit uses the same patterns as the guard*. So v5 built the attacker that exploits exactly that. `hostile-fluent` writes ordinary professional English with no banned phrase, no verdict token and no injection marker in it - *"the owning team has already sequenced their deploy around it, so this can ride the normal release train"* - and **the v3 guard printed it above a BLOCK on 12 of 12 cases while v3's metric for that failure read 0.** The metric said the guard held; the reviewer read a lie.

**The fix is provenance, not a longer blocklist**, which is the same mistake with more words. The headline is now a pure function of tool output on every run, for every model: 0 of 60 model-written headlines, and misleading headlines reaching the reviewer go 36/48 (v2) -> 13/48 (v3) -> **0/48 (v5)**. The prose is kept, demoted to *Model commentary (unverified prose, not evidence)* after the hazard table, where a lie sits beside the engine errors that contradict it. No detection metric moves, because the narrator never touched one. All three modes stay runnable (`--narrator-mode`), so each defence is priced instead of asserted.

## How it works

`python -m sentinel review --case eval/cases/case_12_release_train.json`. Five agents, fixed order, instructions in `sentinel/agents/prompts/`: Cartographer (parser), Blast Radius (shadow-DB executor), Risk Officer (rules, memory, ledger, verdict), Rollout Engineer (plan writer), Verifier (replay and retry, max 3 attempts). Tools decide facts, the model explains them, and the packet says which is which. The agency is in the loop: the Verifier replays the plan the Rollout Engineer just wrote, policy tightens between attempts, and it escalates when the retry budget runs out.

The coverage ledger computes, per affected object, what the review could not observe: unmodelled statements, rows rewritten in place (replay proves a statement still runs, never that it returns the same answer), a value class the rollback does not restore. `sentinel review` never touches a database; `sentinel execute` runs in an in-memory SQLite sandbox and refuses without `--i-approve --reviewer`, on a `BLOCK` without a named override, or on an uncleared gap.

## Agents used and reproducibility

**Claude Opus 5**, conversationally rather than as an autonomous shell harness, for everything under `sentinel/`, `eval/`, `tools/`, `tests/`, `site/`, all written inside the challenge window; full disclosure in `AGENT_USE.md`. Later sessions in fresh contexts were pointed at the finished work to falsify it, producing the ablation harness, the sensitivity band, the hostile models and v5's attack on v3. Never delegated: the ground-truth labels, the hazard vocabulary, the scorer, the metrics. An agent that writes the solution and its own grading criteria has graded itself.

Python 3.11+ standard library (3.11 and 3.12 verified), zero pip dependencies, no API key, no network, synthetic data. Reviewer minutes are the one modelled number, so `eval/time_sensitivity.py` recomputes every arm under six constant sets, three written to break the claim: the saving holds at 69% under uniform rescaling, and two adversarial sets reverse its sign. That reversal is the coverage gate's bill: every blind spot it opens is a human gate.

- `python eval/run_eval.py --ablations` : 108 reviews, under 1 s, $0.00
- `python eval/model_invariance.py` : 180 reviews, four hostile models, three narrator modes
- `python -m unittest discover -s tests` : 52 tests
- `python tools/check_results.py` : 44/44 claims re-asserted from raw JSON

The video predates v3, so its on-screen numbers are pre-coverage-gate and pre-provenance. `docs/VIDEO_ADDENDUM.md` is the exhaustive diff; where video and repo disagree, `results/comparison.md` and `results/model_invariance.md` win.

## Main failure mode and hot take

**The corpus is the world.** Everything is proved from the SQL it was given. `case_09` hides the risky consumer in a dbt model outside the corpus: still missed, no longer cleared, because the ledger sees the shape of the hole without seeing what is in it. Recall is 0.970 and not 1.000 because the honest fix argues about the tool's reach instead of fitting the answer key. Twelve cases, one schema, ground truth I wrote: do not quote the F1 without its denominator.

Verification is a sensor with a specific blind spot, not a synonym for correctness. **A sensor that reports its own blind spot has not finished the job until that blind spot can change the answer.**

And the two the hostile models found. **A system can be invariant in every number it publishes and still lie to the person reading it**: every metric read the decision surface, and the reviewer reads the sentence at the top. One iteration later: **a defence audited in its own vocabulary reports on the attacker's imagination, not on itself.** The guard that scored 0/12 was only tested in words it already knew. Prefer a property you can check - these bytes came from a tool call - over a pattern you must keep current. And a defence's limit written into a comment is not disclosure, it is a to-do item with better manners.

GitHub: https://github.com/MahammadRiyazShek/migration-sentinel
Live demo: https://migration-sentinel-frvo.vercel.app/

---

## Video URL

```
https://www.youtube.com/watch?v=JGXnRwWWmrQ
```

The recording predates v3 and therefore predates v5 by two iterations. Architecture, problem framing,
baseline comparison and the walkthrough are unchanged; three on-screen numbers are stale and two
components did not exist yet. `docs/VIDEO_ADDENDUM.md` is the exhaustive on-screen-versus-repo diff and
carries a 90-second delta script if there is time to append one.

## Source code

Upload the archive built from the tree that passes:

```bash
python -m unittest discover -s tests   # 52 tests
python eval/run_eval.py --ablations    # 108 reviews
python eval/model_invariance.py        # 180 reviews
python tools/check_results.py          # 44/44 claims hold
```

Check the uploaded filename before saving. A v4 archive beside a v5 description fails the completeness
and reproducibility gate before rubric scoring begins.

## Pre-submit checklist

- [ ] description pasted, character count under 10,000, no mojibake in the tables
- [ ] source archive is the tree that prints `44/44 claims hold`
- [ ] video URL present, addendum linked in the repo
- [ ] `agent_traces/INDEX.md` regenerated (`python tools/collect_agent_traces.py --write`) and secret
      scan clean
- [ ] live desk loads and its recorded packets match `results/`
