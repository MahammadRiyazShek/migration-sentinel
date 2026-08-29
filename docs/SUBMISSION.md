# Submission form content (paste-ready)

## Title

Migration Sentinel: an agent pipeline that replays your schema migration before a human approves it

## Live demo and source

* **Live review desk:** https://OWNER.github.io/migration-sentinel/ (replace with your deployed URL)
* **Source:** https://github.com/OWNER/migration-sentinel
* The desk is static. Recorded packets render immediately; one button boots CPython 3.12 on
  WebAssembly (Pyodide 0.26.4), mounts the same `sentinel` package the CLI imports and runs the real
  pipeline in the visitor's tab, on the case they pick or on SQL they paste. Nothing is uploaded.
* Every live run is diffed against the packet recorded in `results/`, and the page prints the diff.
  `tools/test_browser_driver.py` runs the same driver under CPython: 12/12 parity.
* Deploy from a clean checkout in about two minutes: `DEPLOY.md` (GitHub Pages via the committed
  workflow, or Vercel via the committed `vercel.json`).

## Description

**Who has the problem.** The platform or data engineer on the schema-migration review rota at a
20-to-300 engineer company. One Postgres primary, a dozen services and a BI layer reading it,
migration PRs arriving from teams that own their feature but not the database.

**The bottleneck.** Reviewing a two-line `ALTER TABLE` honestly means answering six questions that
are not in the diff: which of our live statements touch this column, does anything read `SELECT *`
off the affected view, how big is the table, what data is in it right now, who deploys the code that
breaks, and have we been burned by this pattern before. That is 20 to 40 minutes per PR. It gets 5.
So review degrades to pattern matching on the diff text, which catches the obvious `DROP COLUMN` and
misses the `DROP VIEW` a worker reads every minute.

**The solution.** Five agents in a fixed pipeline: Cartographer (parse to an exact change set),
Blast Radius (static dependents, then execute the entire query corpus against shadow pre/post
databases), Risk Officer (lock, volume and intent rules plus exact-key recall over the team's
incident log, which may only raise a severity and must cite the incident), Rollout Engineer (rewrite
the migration as expand/contract SQL with a rollback and explicit human gates), Verifier (re-parse and
replay the generated plan; feed failures back; escalate to a human after three attempts). Tools decide
facts, the model writes prose. Nothing touches a database without a named human approval.

**Measured improvement** over two fair baselines (one prompt; one prompt plus full schema and row
counts), same 12 cases, same hazard vocabulary, same scorer:

| metric | Baseline A | Baseline B | Sentinel |
|---|---|---|---|
| Unsafe approvals (primary) | 1/12 | 1/12 | **0/12** |
| Hazard recall / precision | 0.545 / 0.947 | 0.606 / 0.690 | **0.939 / 0.969** |
| Severity agreement | 0.611 | 0.550 | **0.968** |
| Findings backed by machine evidence | 0/19 | 0/29 | **34/34** |
| Verified rollout plans | 0/12 | 0/12 | **12/12** |
| Modelled reviewer minutes per case | 29.7 | 34.7 | **8.5** |

An ablation isolates the contribution of each component. The headline finding: **replay-only scored
worse than rules-only** on the primary metric (2 unsafe approvals vs 1), because lock and
integrity hazards fail nothing, so execution alone says "nothing broke, ship it".

**Reproducibility.** Python 3.11+ standard library, zero pip dependencies, no API key, no network.
The full evaluation (96 reviews including ablations) runs in **0.62 s for $0.00** and returns
byte-identical numbers: `python eval/run_eval.py --ablations`. 15 tests, including a determinism test
and tests for the escalation path and the approval gate. The same prompts run against a hosted model
with `--provider openai` (about $0.02 for the whole evaluation); because the model does not decide
hazards, that changes wording and cost, not the primary metric.

**Data and ethics.** Entirely synthetic: a fictional SaaS billing schema, `example`-domain emails, an
invented incident log. No customer data, no credentials, nothing scraped. Consequential actions are
sandboxed (in-memory SQLite copy) behind an approval gate that refuses without a named reviewer, and
the plan explicitly refuses to decide dedupe rules, truncation rules and cutover windows on a human's
behalf.

**Main failure mode.** The corpus is the world: two ground-truth hazards are missed by construction
(a dbt model outside the corpus, and a `CLUSTER` statement the parser does not model). Both surface in
the packet as unmodelled or unchecked, because a tool that quietly narrows its own scope launders a gap
into a green check.

**Hot take.** Give an agent a tool that can be loudly wrong, and pair it with rules that can be
quietly wrong. Verification is not a synonym for correctness, it is a sensor with a specific blind
spot. And detection was not the win: adding plan generation and verification moved detection metrics
by zero and cut reviewer minutes by two thirds.

Read first: `README.md`, then `docs/DESIGN_LOG.md`, then
`trajectories/case_01_rename_with_compat_view.md`.

## Video URL

Record from `docs/VIDEO_SCRIPT.md` (4:40 shot list, every spoken number is on screen) and paste the
link here.

## Source code

Upload `migration-sentinel.zip` (about 200 KB, well under the 50 MB limit).
