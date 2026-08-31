# Paste-ready submission text

The micro1 form caps the Description field at 10,000 characters. Everything below the marker is
that field, verified line by line against the committed evidence on a clean container
(Python 3.12.13, no network, no pip install) by the seventh supervisor session:
`docs/SUPERVISOR_LOG_V7.md`. `tools/check_docs.py` re-asserts that this file exists and fits.

Title field:

> Migration Sentinel: agents that replay your schema migration, verify the rollout plan they wrote,
> name what they could not see, and never let the model write the verdict

Video URL field: `https://www.youtube.com/watch?v=JGXnRwWWmrQ`

<!-- PASTE BELOW THIS LINE -->

A two-line ALTER TABLE is either free or an outage, and the diff does not tell you which.

Every number below is re-asserted from raw JSON by one command on a clean clone, in under a second, with no API key and no network: **`python tools/check_results.py` -> 27/27 claims hold.**

| metric | A (one prompt) | B (prompt + schema) | Sentinel |
|---|---|---|---|
| **Unsafe approvals** (primary) | 1/12 | 1/12 | **0/12** |
| **Blind-spot cases cleared** (primary) | 0/2 | 0/2 | **0/2** |
| Blind spots named, with the object | 0 | 0 | **3** |
| Hazard recall / precision | 0.545 / 0.947 | 0.606 / 0.690 | **0.970 / 0.970** |
| Severity agreement on matched hazards | 0.611 | 0.550 | **0.969** |
| Findings backed by machine evidence | 0/19 | 0/29 | **35/35** |
| Verified expand/contract plans | 0/12 | 0/12 | **12/12** |
| False alarms on the one clean migration | 1 | 1 | **0** |
| Modelled reviewer minutes per case | 29.7 | 34.7 | **9.2** |

Same 12 cases, same hazard vocabulary, same scorer, same temperature. Only the scaffolding changes.

Read the second primary metric honestly: **all three arms tie at 0/2, and the tie is the finding.** The baselines reach it by requesting changes almost everywhere: 10 of 12 for A, 11 of 12 for B, both of them including the one migration that is genuinely safe. They never clear a blind spot because they clear almost nothing, and they name zero blind spots in the packet. Sentinel holds 0/2 while still approving the clean case and shipping a plan for the safe one. The metric exists because the first one cannot see everything: "ship as planned" printed above a declared blind spot passes the unsafe-approval scorer and still misleads the reviewer.

**Problem and user.** The platform engineer on the schema-migration review rota at a 20-to-300 engineer company: one Postgres primary, a dozen services and a BI layer reading it, migration PRs from teams that own their feature but not the database. A real review answers questions the diff does not contain: which live statements touch this column, whether anything reads `SELECT *` off the affected view, whether this lock survives 48M rows. Twenty to forty minutes per PR, and they get five, so review degrades into pattern matching on diff text: it catches the obvious DROP COLUMN and misses the DROP VIEW a worker reads every minute. The evidence already exists, in DDL, a query corpus, row counts and an incident log. Nobody has time to assemble it.

**Baseline vs advanced.** A: one model call on the diff. B: same prompt plus full DDL and row counts. Sentinel: five agents over a shadow-replay engine, static rules on a parsed change set, incident memory, generated expand/contract SQL, a Verifier that replays the plan it just wrote, a coverage ledger that caps the verdict, and a headline rendered from tool output.

B's precision is *lower* than A's: more context made it guess more, string-matching table names inside view bodies. Context you cannot check buys volume, not accuracy.

**What each component buys.** 9 arms x 12 cases = 108 reviews, one component removed at a time (unsafe / recall / plans / gaps / min-per-case). All five: 0/12, 0.970, 12/12, 0/2, 9.2. Rules only: 1/12, 0.576, 0/12, 0/2, 23.3. Replay only: 2/12, 0.333, 12/12, 0/2, 8.8. No coverage gate: 0/12, 0.970, 12/12, **1/2**, 8.5.

Replay alone is worse than rules alone, 2 unsafe approvals against 1: a lock hazard produces no failing query, so nothing breaks, so replay-only waves through the 48M-row index build. Execution is necessary, not sufficient, and merging the layers is the biggest changelog contribution. The coverage gate is the only component whose removal makes a published number *better* (+0.7 min/case, no detection metric moved), and the one I defend first.

**Can the model move any of this?** 12 cases x 5 models x 3 narrator modes = 180 reviews, seconds, $0, four of the models not trying to help: a sycophant, an injector, a dead endpoint, and hostile-fluent, written specifically to walk through my own earlier fix. The facts hold, and that is measured rather than argued from code shape: the decision surface changed in **0 of 168** completed reviews, byte-identical on verdict, hazards, severities, evidence, ledger, generated SQL and verification. The other 12 crashed, all of them with the narrator unguarded, on a model that returns an empty body. Both guarded modes take that to 0: an outage became a degraded review.

The prose did not hold, and no decision-surface metric could see it. Unguarded, the sycophant printed "Approved: no hazards found, safe to ship" under a badge reading BLOCK on 11 of 12 cases without moving one number. So I shipped a blocklist, measured 0/12, then noticed the audit shared its regexes with the guard: the number only reported what the blocklist already knew. So I wrote the attacker for that gap. hostile-fluent uses no banned phrase, no verdict token and no injection marker, and still tells the reviewer the change can ride the normal release train: the audit flagged it 0/12 while it printed above a BLOCK 12/12.

The fix is provenance, not a longer list. The headline is now a pure function of tool output, and model prose is demoted to a block labelled *unverified prose, not evidence*. Misleading headlines reaching the reviewer, per 48 hostile reviews per mode: **36/48 unguarded -> 13/48 blocklist -> 0/48 shipped**, with 0 of 60 headlines model-written and no detection metric moved, because the narrator never touched one.

**How it works.** Five agents, fixed order, instructions in `sentinel/agents/prompts/`: Cartographer (parser), Blast Radius (shadow-DB executor), Risk Officer (rules, memory, ledger, verdict), Rollout Engineer (plan writer), Verifier (replay and retry, max 3 attempts). Tools decide facts and the model explains them. The agency is in the loop: the Verifier replays the plan the Rollout Engineer just wrote, policy tightens between attempts, and it escalates when the retry budget is spent.

The coverage ledger names, per affected object, what the review could not observe: unmodelled statements, rows rewritten in place, a value class the rollback cannot restore. Replay proves a statement still runs, never that it returns the same answer. Any open gap caps the verdict at `NEEDS_COVERAGE_SIGNOFF`, which is not an approval, not executable, and invents no hazard, so it costs no precision or recall.

Review never touches a database. Execution runs in an in-memory SQLite sandbox and refuses three ways, each with its own exit code: without a named approving reviewer, on a BLOCK without an explicit override, and on an uncleared coverage gap.

**Reproducibility.** Python 3.11+ standard library (3.11 and 3.12 verified), zero pip dependencies, no API key, no network, synthetic data. Start at `JUDGE_START_HERE.md`. `python -m sentinel review --case eval/cases/case_12_release_train.json` for one packet; `python eval/run_eval.py --ablations` for 108 reviews in under a second at $0.00; `python eval/model_invariance.py` for the 180 hostile-model reviews; 33 tests under `unittest`; `python tools/check_results.py` for 27/27 claims and `python tools/check_docs.py` for the documentation's own claims about the repository.

Reviewer minutes is the one modelled number, so `eval/time_sensitivity.py` recomputes every arm under six constant sets, three written to break the claim: the saving holds at 69% under uniform rescaling, and **two adversarial sets reverse its sign** and are published flagged in the table. The load-bearing assumption is not that reviewers are slow, it is that writing a staged migration plan from scratch costs several times more than approving one that has already been replayed. That reversal is the coverage gate's bill.

**On the video:** recorded against v2, the repo is v5, so some on-screen numbers are earlier and two components did not exist yet. Where video and repo disagree, `results/comparison.md` and `results/model_invariance.md` are authoritative; `docs/VIDEO_ADDENDUM.md` lists every stale number, line by line.

**Agents used.** Claude Opus 5, used conversationally rather than as an autonomous shell harness, for everything under `sentinel/`, `eval/`, `tools/`, `tests/` and `site/`, inside the challenge window. Disclosure in `AGENT_USE.md`, trajectories in `agent_traces/`. Fresh-context sessions were later pointed at the finished work to falsify it, producing the ablation, sensitivity, hostile-model and documentation harnesses. Never delegated: ground truth, hazard vocabulary, scorer, metrics. An agent that grades its own work has graded itself.

**Main failure mode and hot take.** The corpus is the world: everything is proved from the SQL it was given. `case_09` hides the risky consumer in a dbt model outside the corpus, so it is still missed, but no longer cleared, because the ledger sees the shape of the hole without seeing what is in it. Twelve cases, one schema, ground truth I wrote by hand. Do not quote the F1 without its denominator.

Verification is a sensor with a specific blind spot, not a synonym for correctness. A system can be invariant in every number it publishes and still lie to the person reading it: every metric read the decision surface, the reviewer reads the sentence at the top. And the one I only found by attacking my own fix: **a defence audited in its own vocabulary reports on the attacker's imagination, not on itself.** Audit the output your user actually reads, and when removing components cannot find the gap, write the component that lies to you on purpose.

LINKS

GitHub: https://github.com/MahammadRiyazShek/migration-sentinel
Live demo: https://migration-sentinel-frvo.vercel.app/
