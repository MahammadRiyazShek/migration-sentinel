# Submission form content (paste-ready)

Repo: <https://github.com/MahammadRiyazShek/migration-sentinel> ·
Live desk: <https://migration-sentinel-frvo.vercel.app/>

---

## Title

```
Migration Sentinel: an agent pipeline that replays your schema migration before a human approves it
```

Alternate, if the form rewards the outcome over the mechanism:
`Migration Sentinel: schema-migration review that proves its own rollout plan (0/12 unsafe approvals vs 1/12 for a prompt)`

---

## Description

**A two-line `ALTER TABLE` is either free or an outage, and the diff does not tell you which.**

**Who has the problem.** The platform or data engineer on the schema-migration review rota at a
20-to-300 engineer company: one Postgres primary, a dozen services and a BI layer reading it,
migration PRs arriving from teams that own their feature but not the database.

**The bottleneck.** Reviewing that PR honestly means answering six questions that are not in the
diff. Which of our live statements touch this column? Does anything read `SELECT *` off the affected
view, so the column set matters and not just the SQL? How big is the table, and does that turn this
index build into a write stall? What data is in there right now that will not survive? Who deploys
the code that breaks, and does the schema or the code land first? Have we been burned by this exact
pattern before? Answering all six by hand is 20 to 40 minutes per PR. It gets 5. So review degrades
into pattern matching on the diff text, which catches the obvious `DROP COLUMN` and misses the
`DROP VIEW` a worker reads every minute. The evidence for a correct answer already exists in machine
readable form (DDL, query corpus, row counts, the incident log); nobody has time to assemble it per PR.

**The solution: one command per PR, and a review packet a human signs.**

```bash
python -m sentinel review --case eval/cases/case_01_rename_with_compat_view.json
```

Five agents, fixed order, one feedback loop. Instructions for each are in `sentinel/agents/prompts/`.

1. **Cartographer** parses the migration into an exact change set.
2. **Blast Radius** resolves dependents, then materialises **two shadow databases** (pre and post
   schema, seeded with fixtures) and executes the entire query corpus against both. Hazards quote the
   engine's own error text, and column-set diffing catches the worst real failure: the query that
   still runs and returns different columns, so tests stay green while the dashboard goes wrong.
3. **Risk Officer** adds lock, volume and intent rules over the parsed ops and declared row counts,
   then does exact-key recall over the team's incident log. Memory may only **raise** a severity and
   must cite the incident id: surviving something once is not evidence of safety.
4. **Rollout Engineer** rewrites the migration as executable expand/contract SQL with a rollback, and
   refuses to decide dedupe rules, truncation rules or cutover windows on a human's behalf.
5. **Verifier** re-parses and replays the generated plan. Failures go back to the Rollout Engineer
   with the error text; after three attempts it escalates to a person instead of shipping a plan it
   cannot prove.

Tools decide facts, the model writes prose. Swap the model and the wording changes, not the verdict.

**Measured improvement.** Same 12 cases, same hazard vocabulary, same scorer, against two fair
baselines: one prompt with the migration and the hazard list, and the obvious next move, that same
prompt plus the full DDL and row counts. The pipeline makes **no unsafe approvals (0/12 vs 1/12)**,
raises hazard recall from 0.545 to 0.939, backs **34/34** findings with machine evidence where the
baselines back 0, and ships **12/12** verified rollout plans where the baselines ship none.

| metric | Baseline A (prompt) | Baseline B (prompt + schema) | Migration Sentinel |
|---|---|---|---|
| Unsafe approvals (primary) | 1/12 | 1/12 | **0/12** |
| Hazard recall / precision | 0.545 / 0.947 | 0.606 / 0.690 | **0.939 / 0.969** |
| Severity agreement | 0.611 | 0.550 | **0.968** |
| False alarms on the clean case | 1 | 1 | **0** |
| Findings backed by machine evidence | 0/19 | 0/29 | **34/34** |
| Verified rollout plans | 0/12 | 0/12 | **12/12** |
| Modelled reviewer minutes per case | 29.7 | 34.7 | **8.5** |

Baseline B is instructive on its own: more context made it *guess more*. Family recall rose to 0.864
while strict precision fell to 0.690, because it started string-matching table names inside view
bodies. Context without the ability to check the context buys volume, not accuracy.

**Which component does the work.** An ablation removes one component at a time. The headline:
**replay-only is worse than rules-only** on the primary metric, 2 unsafe approvals against 1. A lock
hazard produces no failing query, so a replay-only reviewer sees nothing break and says ship it. The
two layers cover disjoint failure classes, which is the entire design rather than a nice-to-have.
Incident memory changed no verdict and moved severity agreement 0.935 to 0.968; it stayed because
severity is what decides whether a change waits for a maintenance window. Plan verification moved
detection by exactly zero and cut modelled reviewer minutes by two thirds.

**Human control.** `sentinel review` never touches a database. `sentinel execute` applies phase 1 to
an in-memory sandbox copy only, refuses without `--i-approve --reviewer "name"`, and refuses a BLOCK
verdict unless a named reviewer overrides it on the record. Every packet ends with the decisions the
tool will not make and an explicit list of what it did not check.

**Reproducibility.** Python 3.11+ standard library, zero pip dependencies, no API key, no network.
The full evaluation, 96 reviews including all ablations, runs in **under a second for $0.00** and
returns byte-identical numbers: `python eval/run_eval.py --ablations`. 15 stdlib tests cover
determinism, the escalation path and the approval gate. `tools/check_results.py` re-asserts all 13
headline claims from the raw result JSON and gates the deploy. The same prompts run against a hosted
model with `--provider openai` for roughly $0.02.

**The live desk** (<https://migration-sentinel-frvo.vercel.app/>) is not a mock. One button loads
CPython 3.12 on WebAssembly (Pyodide 0.26.4), mounts the same `sentinel` package the CLI imports and
runs `orchestrator.review` in your tab, on the twelve cases or on SQL you paste. Nothing is uploaded.
Every live run is diffed against the packet recorded in `results/` and the page prints the diff either
way, so you can catch the demo drifting from the repository without taking my word for it.
`tools/test_browser_driver.py` runs the same driver under CPython: 12/12 parity.

**Data and ethics.** Entirely synthetic: a fictional SaaS billing schema, `example`-domain emails, an
invented incident log and invented row counts. No customer data, no credentials, nothing scraped.

**What existed before.** The Python standard library, the expand/contract pattern as industry prior
art, and Pyodide (Mozilla, MPL-2.0, loaded unmodified from CDN). Everything else was built for this
challenge from scratch: the Postgres-subset parser and schema model, the shadow-replay engine, the
corpus and incident-memory tools, five agent instruction sets and implementations, the orchestrator
with its verify/retry loop, the CLI and approval gate, the model layer, the 12 cases and their ground
truth, the scorer, the ablation harness, the tests and the review desk.

**Main failure mode: the corpus is the world.** Two of the twelve cases exist to expose it.
`case_09` hides the risky consumer in a dbt model that is not in the corpus; `case_12` hides
`CLUSTER invoices USING …` outside the parser's model. Both are missed, by construction. The
mitigation is the part worth defending: an unparsed statement never becomes "safe", it travels
through as an explicit unknown and lands in the packet's coverage-gap section next to everything that
passed. A tool that quietly narrows its own scope launders a gap into a green check.

**Hot take.** Give an agent a tool that can be *loudly* wrong and pair it with rules that can be
*quietly* wrong. Verification is not a synonym for correctness, it is a sensor with a specific blind
spot, and the engineering is knowing that shape well enough to place a differently-shaped sensor next
to it. The corollary I did not expect: detection was never the win. Adding plan generation and
verification moved detection metrics by zero and still cut reviewer time by two thirds. Being right is
table stakes; the tool earns its place by doing the tedious thing the human would otherwise do at 3am.

**Read in this order:** `README.md` (includes the full Improvement Changelog, one row per iteration
with its evidence, including two experiments that were removed) → `REPRODUCTION.md` →
`trajectories/case_01_rename_with_compat_view.md` → `docs/AGENT_TRAJECTORIES.md`.

---

## Video URL

Record from `docs/VIDEO_SCRIPT.md` (4:40 shot list, every spoken number is on screen), then paste the
link. Structure: problem and baseline → one full execution of `case_01` → the comparison table → the
changelog, with iteration 3 (merging replay and rules) called out as the biggest contribution and the
additive-column drift alert as the experiment that was removed.

## Source code

Upload `migration-sentinel.zip` (~1.2 MB, well under the 50 MB limit). Repo:
<https://github.com/MahammadRiyazShek/migration-sentinel>
