# Reproduction guide

Written for someone who has just cloned this into an empty directory on a clean machine.

## 0. What you need

| thing | version used | notes |
|---|---|---|
| Python | 3.12.13 (3.11+ works) | `python3 -V` |
| SQLite | 3.40.1, bundled with Python | `python3 -c "import sqlite3;print(sqlite3.sqlite_version)"` |
| pip packages | **none** | standard library only, `requirements.txt` is intentionally empty |
| network | **not required** | the default run makes zero network calls |
| API key | **not required** | only for the optional hosted-model run |
| disk | < 5 MB | |

No virtualenv is needed, but if you want one:

```bash
python3 -m venv .venv && source .venv/bin/activate
```

## 1. Data

All data is synthetic and lives in the repo. Nothing to download.

* `eval/cases/*.json` - the 12 evaluation cases. Each is self-contained: the schema DDL, the row
  estimates, the 14-statement query corpus with service owners and criticality, the fixture rows, the
  proposed migration, its rollback (or the absence of one), and the ground-truth hazards.
* `memory/incidents.jsonl` - 5 fictional postmortems used as long-term memory.

Cases are generated so they stay consistent with each other. Regenerate them at any time:

```bash
python eval/build_cases.py
# -> wrote 12 cases to .../eval/cases
```

The generator is also where the ground truth lives, with a comment explaining that two hazards are
included specifically because the pipeline cannot find them.

## 2. Run the solution on one case

```bash
python -m sentinel cases                      # list the 12 cases and their ground truth shape
python -m sentinel review --case eval/cases/case_01_rename_with_compat_view.json
```

Expected stdout (one line):

```
case_01_rename_with_compat_view: BLOCK (2 blocker / 4 high) -> results/case_01_rename_with_compat_view.md
```

Expected files:

* `results/case_01_rename_with_compat_view.md` - the review packet a human reads
* `results/case_01_rename_with_compat_view.json` - the same thing structured, including every tool call
* `trajectories/case_01_rename_with_compat_view.md` - the agent trajectory
* `trajectories/case_01_rename_with_compat_view.jsonl` - the raw event log

Add `--print-report` to dump the packet to stdout. Runtime: about 10 ms. Cost: $0.

The most interesting case is the release train:

```bash
python -m sentinel review --case eval/cases/case_12_release_train.json --print-report
```

Expect `BLOCK`, 4 blockers, and a "What this review did not check" section that names the `CLUSTER`
statement it could not model.

## 3. Run the baseline on the same case

```bash
python baseline/baseline_review.py --case eval/cases/case_01_rename_with_compat_view.json \
    --variant prompt_with_schema --print-review
```

Expected: `REQUEST_CHANGES` with 3 findings, no evidence, no plan. Variant `prompt_only` gives 2.

## 4. Run the whole evaluation

```bash
python eval/run_eval.py --ablations
```

This runs 12 cases x (2 baseline variants + 1 pipeline) plus 5 ablation configurations = 96 reviews.

* measured runtime on the reference machine: **0.62 s total**, about 8.5 ms per pipeline review
* cost: **$0.00** (the default model is the offline scripted stand-in)
* stdout ends with the comparison table

Expected files:

| file | contents |
|---|---|
| `results/comparison.md` | the headline table plus per-case detail for the pipeline and baseline B |
| `results/evaluation.json` | every per-case score, the aggregates, and the reviewer-minute assumptions |
| `results/ablation.md` / `.json` | one component removed at a time |
| `results/<case>.md` / `.json` | 12 review packets |
| `results/baseline/<case>.<variant>.md` | 24 baseline reviews |
| `trajectories/<case>.md` / `.jsonl` | 12 trajectories |

Headline numbers you should see, byte for byte:

```
| **Unsafe approvals** (primary, lower is better) | 1/12 | 1/12 | 0/12 |
| Hazard recall (strict code)                     | 0.545 | 0.606 | 0.939 |
| Hazard precision (strict code)                  | 0.947 | 0.69  | 0.969 |
| Severity agreement on matched hazards           | 0.611 | 0.55  | 0.968 |
| Verified expand/contract plans produced         | 0/12  | 0/12  | 12/12 |
```

If any of those differ, the run is not reproducing and I would like to know.

## 5. Tests

```bash
python -m unittest discover -s tests -v
```

Expected: `Ran 15 tests ... OK`, about 0.1 s. They cover the parser traps, the shadow replay,
memory escalation, determinism (same case twice, identical hazards and plan), the escalation path
(`max_attempts=1` on case_01 must escalate instead of shipping an unverified plan) and the approval
gate (refuses without `--i-approve`, refuses a `BLOCK` verdict without an explicit override).

## 6. The human approval gate

`review` never touches a database. To dry-run phase 1 against a throwaway in-memory sandbox:

```bash
python -m sentinel review --case eval/cases/case_06_safe_unique_index.json
python -m sentinel execute --report results/case_06_safe_unique_index.json \
    --case eval/cases/case_06_safe_unique_index.json
# -> REFUSED: phase 1 execution requires --i-approve and --reviewer "name".

python -m sentinel execute --report results/case_06_safe_unique_index.json \
    --case eval/cases/case_06_safe_unique_index.json --i-approve --reviewer "your name"
# -> sandbox: SQLite in-memory copy (never a live database)
#    corpus after phase 1: 16/16 passing
```

Trying the same on a `BLOCK` verdict exits 3 and tells you to use `--override-block` on the record.

## 7. Optional: run the same prompts against a hosted model

Nothing above needs this. The model writes prose, not hazards, so this changes the wording and the
cost, not the primary metric.

```bash
export OPENAI_API_KEY=...            # or ANTHROPIC_API_KEY
python -m sentinel review --case eval/cases/case_01_rename_with_compat_view.json \
    --provider openai --model gpt-4.1-mini
python baseline/baseline_review.py --case eval/cases/case_01_rename_with_compat_view.json \
    --provider openai --model gpt-4.1-mini --print-review
python eval/run_eval.py --provider openai --model gpt-4.1-mini
```

Approximate cost for the full hosted evaluation, at the prices in `sentinel/llm/base.py`
(gpt-4.1-mini, $0.40/$1.60 per Mtok): the pipeline sends about 25k prompt tokens and 3k completion
tokens across 12 cases, so roughly **$0.02** for the pipeline arm and **$0.01** for both baseline
arms. Wall clock is dominated by the API: expect 1 to 3 s per review instead of 8 ms.

To make a hosted run reproducible afterwards, record a cassette and replay it offline:

```bash
python -m sentinel review --case eval/cases/case_01_rename_with_compat_view.json \
    --provider openai --cassette cassettes/case_01.json --cassette-mode record
python -m sentinel review --case eval/cases/case_01_rename_with_compat_view.json \
    --provider openai --cassette cassettes/case_01.json     # no network, byte-identical
```

## 8. Optional: let the run write to memory

Off by default so the evaluation stays deterministic.

```bash
python -m sentinel review --case eval/cases/case_05_unique_email_with_duplicates.json --learn
cat memory/learned.jsonl
```

Blocking hazards are appended as learned patterns, deduplicated by (hazard code, tables). Delete the
file to reset. `eval/run_eval.py` never writes to memory.

## 9. Bringing your own migration

Copy any case JSON, replace `schema_sql`, `migration_sql`, `row_estimates`, `queries` and `seed`, drop
`ground_truth` (only the scorer needs it), then run `python -m sentinel review --case yours.json`.
The parser covers the PostgreSQL subset listed in `sentinel/tools/sql_parse.py`; anything outside it
is reported as an unmodelled statement rather than silently ignored.

## 10. The review desk, locally and deployed

The desk is static. `site/data/bundle.json` and `site/py/` are generated from `results/`, so build
them after the evaluation, never before.

```bash
python eval/run_eval.py --ablations      # writes results/ and trajectories/
python tools/check_results.py            # 13/13 claims hold  (exits 1 if one does not)
python tools/build_site.py               # -> site/data/bundle.json  (~467 KB), site/py/ (38 files)
python tools/build_artifact.py           # -> site/standalone.html   (one file, no live engine)
python tools/test_browser_driver.py      # 12/12 parity with the recorded packets
python -m http.server 8000 --directory site
# open http://localhost:8000
```

What you should see, in order:

1. The masthead numbers, the docket of 12 cases and the first packet, rendered from the bundle. No
   network beyond this origin and Google Fonts.
2. **Boot the engine in this browser** → about 12 MB of Pyodide from jsDelivr, then
   `38 files mounted`. Roughly 5 to 15 seconds on a first visit, under two on a warm cache.
3. **Run this case live** → the packet re-renders with a `live run` chip, a wall-clock figure
   measured in the tab (typically 20 to 60 ms, slower than the 8.5 ms CLI number because
   WebAssembly), and a parity line: *"the run in this tab reproduced the recorded packet exactly"*.
4. Edit the SQL in the Migration tab, press **Review this SQL** → a real packet for your migration,
   with a note that there is no ground truth to score it against.

Runtime and cost for the whole section: about 20 seconds of wall clock, $0.00. Tested on Python
3.12.13 and Pyodide 0.26.4 (CPython 3.12) in Chromium and Firefox.

Publishing it: [`DEPLOY.md`](DEPLOY.md). GitHub Pages via the committed workflow, Vercel via the
committed `vercel.json`, or any static host with publish directory `site`. The Pages job re-runs the
tests, the evaluation, the claim checker and the driver parity check before it publishes, so a
deployed page that disagrees with the repository fails the build instead of shipping.

If you have no browser at hand, `site/standalone.html` opens from disk with every recorded packet
inlined, and the CLI in sections 2 to 4 is the reference implementation anyway.
