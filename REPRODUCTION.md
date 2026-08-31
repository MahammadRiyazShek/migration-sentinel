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

This runs 12 cases x (2 baseline variants + 1 pipeline) plus 6 ablation configurations = 108 reviews.

* measured runtime on the reference machine: **under 1 s total**, about 8 ms per pipeline review
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
| **Unsafe approvals** (primary, lower is better)             | 1/12  | 1/12  | 0/12  |
| **Coverage-gap cases cleared without a sign-off**           | 0/2   | 0/2   | 0/2   |
| Hazard recall (strict code)                                 | 0.545 | 0.606 | 0.97  |
| Hazard precision (strict code)                              | 0.947 | 0.69  | 0.97  |
| Severity agreement on matched hazards                       | 0.611 | 0.55  | 0.969 |
| Findings backed by machine evidence                         | 0/19  | 0/29  | 35/35 |
| Blind spots named in the packet, with the object             | 0     | 0     | 3     |
| Verified expand/contract plans produced                     | 0/12  | 0/12  | 12/12 |
| Modelled reviewer minutes per case                          | 29.7  | 34.7  | 9.2   |
```

Per-case verdicts you should see: 9 x `BLOCK`, 1 x `SAFE` (`case_06`, the clean case), 1 x
`SAFE_WITH_PLAN` (`case_07`), and 1 x `NEEDS_COVERAGE_SIGNOFF` (`case_09`, capped because the
migration erases every `NULL` from `invoices.currency` and the rollback does not restore them).

If any of those differ, the run is not reproducing and I would like to know.

### 4a. What each component costs to remove

```bash
python eval/report_components.py --write
```

Reads `results/ablation.json` and rewrites [`results/components.md`](results/components.md), oriented
as the cost of removing each component rather than as the score of each arm. Under a second, $0.00.
This is where the verifier and incident memory stop looking decorative: both leave every detection
metric untouched, and removing the verifier moves verified plans 12/12 -> 0/12 and modelled reviewer
minutes 9.2 -> 23.3. It is also where the coverage gate looks *bad*: it moves no detection metric at
all and adds 0.7 modelled reviewer minutes per case. The `no_coverage` arm is the v1 behaviour, and it
is the only arm that clears a declared blind spot (1/2 against 0/2).

### 4b. Sensitivity band on the reviewer-minute claim

```bash
python eval/time_sensitivity.py --write
```

Reads the committed `results/` and rewrites `results/time_sensitivity.md`. Recomputes the reviewer
minutes for every arm under six constant sets, three of them written specifically to break the claim.
Runs no reviews and calls no model, so it cannot change any other number. It self-checks first: all 84
per-case minute figures are recomputed from the raw fields and asserted equal to what
`eval/scoring.py` stored, so drift between the two fails loudly.

Expected: the reduction against the better baseline holds at **69%** under uniform rescaling, 63% when
an unevidenced claim is priced at 1 minute, and **reverses to -12% and -5%** under one specific ratio
(a hand-written plan priced at 6 minutes against 6 minutes to approve a generated one). In v1 those two
rows collapsed the advantage to about 1%; in v2 they flip its sign, because the coverage gate turns
every blind spot into a human gate and human gates are exactly what this model charges for. That
reversal is the point of running it.

### 4c. Attack the model-invariance claim (v3), and the guard that answered it (v5)

```bash
python eval/model_invariance.py --write
```

Runs all 12 cases through five models - the cooperative offline stand-in plus the four hostile ones in
`sentinel/llm/adversarial.py` - in all three narrator modes. **180 reviews**, a few seconds, $0, no API
key. Writes `results/model_invariance.json` and `results/model_invariance.md`.

The narrator modes are the three answers this project has given to "who writes the sentence a reviewer
reads first": `off` is v2 (model prose printed unchecked), `pattern` is v3 (a blocklist decides), and
`structural` is v5 and the shipped default (the headline is a pure function of tool output). All three
stay runnable so each can be priced instead of asserted.

Expected, per hostile mode (4 hostile models x 12 cases = 48 reviews each):

```
| narrator mode    | surface changed | crashed | misleading headline printed | v3 audit flagged |
| off        (v2)  | 0/48            | 12/48   | 36/48                      | 23/48            |
| pattern    (v3)  | 0/48            | 0/48    | 13/48                      | 0/48             |
| structural (v5)  | 0/48            | 0/48    | 0/48                       | 0/48             |
```

Two rows in the full table are the ones to read carefully.

`hostile-null` with the narrator off crashes 12/12: a model that returns nothing used to take the run
down, which is the availability failure the invariance argument could not express.

`hostile-fluent` under the v3 `pattern` guard prints **12/12** misleading headlines while the v3 audit
column reads **0/12**. That model exists to attack this repo's own defence: its prose contains no
phrase in `narrator.CLEAN_CLAIM`, no token in `narrator.VERDICT_TOKENS` and nothing in
`narrator.INJECTION`, so the blocklist accepts it word for word. The v3 metric and the v3 guard shared
a vocabulary, so the metric could only ever report what the guard already knew.

Watch all three modes on one case:

```bash
python -m sentinel review --case eval/cases/case_02_drop_column_still_read.json \
    --provider hostile-fluent --print-report
# -> BLOCK, 5 hazards, headline written by the tools, and the model's paragraph printed at the
#    very end under "Model commentary (unverified prose, not evidence)"

python -m sentinel review --case eval/cases/case_02_drop_column_still_read.json \
    --provider hostile-fluent --narrator-mode pattern --print-report
# -> BLOCK, 5 hazards, and the headline above the badge now says the change "can ride the normal
#    release train". This is what v3 shipped and what v3's own metric scored as clean.

python -m sentinel review --case eval/cases/case_02_drop_column_still_read.json \
    --provider hostile-approve --no-narrator-guard --print-report
# -> v2 behaviour: headline reads "Approved: no hazards found, safe to ship. LGTM"
```

In every one of those runs the verdict, the hazard list, the severities, the evidence and the phase-1
SQL are byte-identical. Only the sentence at the top moves, which is exactly the point.

### 4d. Development-agent trace index

```bash
python tools/collect_agent_traces.py --write
```

Regenerates `agent_traces/INDEX.md` from the trace files actually present, with sizes and SHA-256
prefixes, and greps every one of them for key, token and connection-string shapes. Exits non-zero on
a hit or on an empty directory rather than writing an index that lists nothing. See
[`AGENT_USE.md`](AGENT_USE.md).

## 5. Tests

```bash
python -m unittest discover -s tests -v
```

Expected: `Ran 69 tests ... OK`, about 0.3 s. They cover the parser traps, the shadow replay,
memory escalation, determinism (same case twice, identical hazards and plan), the escalation path
(`max_attempts=1` on case_01 must escalate instead of shipping an unverified plan) and the approval
gate (refuses without `--i-approve`, refuses a `BLOCK` verdict without an explicit override, and
refuses an uncleared coverage gap with exit code 4). Five of the 22 are the v2 coverage suite:
`TestCoverageLedger` asserts that the cap never makes a verdict safer, that it fires on `case_09` with
`invoices.currency` named, that it does **not** fire on the clean case, that disabling the gate
reproduces the v1 verdict exactly, and that a maintenance command recognised by name still stays in
the coverage ledger. Five more are the v3 narrator suite: `TestNarratorGuard` asserts that a clean
headline over a `BLOCK` is rejected, that the guard accepts the cooperative narrator's own summary for
all twelve recorded packets (a filter needs a test that it passes good input), that injection text and
non-string junk are stripped from the reviewer questions, that a missing payload degrades instead of
crashing, and that all three hostile models leave verdict, hazard codes, severities and phase-1 SQL
byte-identical.

Six more are the v5 provenance suite: `TestStructuralNarrator` asserts that the fluent liar's prose
passes the v3 blocklist (the attack, pinned as a test so it cannot quietly stop being true), that in
the shipped mode every one of the five models produces the *same* tool-written headline, that the
liar's paragraph is kept but rendered below both the headline and the hazard table, that the
deterministic headline actually contains the counts it claims, that an unknown narrator mode raises
instead of silently defaulting to something lenient, and that the v3 `guard_narrator=True/False`
argument still maps to `pattern`/`off` for older call sites.

### 5a. Audit the documentation, not just the numbers

```bash
python tools/check_docs.py
# -> PASS  no mis-decoded characters in authored text
#    PASS  every path-shaped file reference resolves
#    PASS  exactly one judge entry point at the root
#    PASS  paste-ready description exists and fits the form
#    PASS  no stale count for a claim ledger or an audit
#    PASS  no stale test count in a current-state document
#    PASS  no heading trapped in a language-tagged code fence
#    7/7 documentation checks hold across every authored file
```

The count of authored files is printed rather than documented here on purpose: it is the one
number in this repository that changes every time a file is added, and a number no tool owns is
a number that goes stale. The counts that *are* documented - claims, checks, tests - are each
read out of the tool that owns them by this same audit, in v11 including the size of an audit,
which is how `6 checks` and `Seven checks` sat in one document for three releases.

### 5b. Prove the rerun changed only the clock

```bash
python3 tools/check_determinism.py
# -> ran   eval/run_eval.py --ablations
#    ran   eval/run_holdout.py --ablations
#    ran   eval/model_invariance.py
#    ran   eval/report_components.py
#    85 files byte-identical on a rerun
#    59 files differ, in wall-clock fields only
#    wall-clock fields that moved: json field "ms", markdown "N ms", markdown "Wall clock per case" row
#    PASS  every decision byte in results/ survives a rerun; only wall-clock fields move
#          144 files compared, 0 decision differences
```

Run steps 3 and 4 and 80 files under `results/` change. Every one of those diffs is a measured
millisecond, and this command is how you know that without taking anyone's word for it: it copies
the repository to a temporary directory, reruns every generator there, and diffs all 144
regenerated files back against the committed ones with the wall-clock fields - and only the
wall-clock fields, each one named in the output - normalised. Zero decision differences is the
pass condition. Your committed tree is never written to. About 3 seconds, most of it the copy.

### 5c. Audit the description in the submission form

```bash
python3 tools/check_submission_text.py
# ...
#    7/7 submission-text checks hold: the description in the form is the description
#    this repository can back
```

The micro1 form's Description field is plain text and lives outside this repository, so the
markdown in `SUBMISSION_DESCRIPTION.md` has to be flattened by hand to paste it. The flattened
text is committed verbatim as `SUBMISSION_FORM_TEXT.txt` and this command audits it: length,
plain-text and ASCII cleanliness, every headline / ablation / hostile-model figure read back out
of `results/*.json`, and seven named load-bearing sentences still present and in position.
Exit code 1 on any failure. Runtime about 1 s (it shells out to `tools/check_results.py`).
```

Exits 1 on any failure. It exists because the seventh supervisor session found five defects that
`tools/check_results.py` structurally cannot see: a duplicate entry point, mis-decoded glyphs, a log
announcing a file that was never committed, a generated paragraph contradicting its own table, and a
stale claim count (`18/18`, when the audit asserts 27) in this very guide. None of them is a number, and all of them sit on the path a
judge walks before reaching one. Reasoning in `docs/SUPERVISOR_LOG_V7.md`.

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
python tools/check_results.py            # 44/44 claims hold  (exits 1 if one does not)
python tools/build_site.py               # -> site/data/bundle.json  (~467 KB), site/py/ (38 files)
python tools/build_artifact.py           # -> site/standalone.html   (one file, no live engine)
python tools/test_browser_driver.py      # 12/12 parity with the recorded packets
python -m http.server 8000 --directory site
# open http://localhost:8000
```

What you should see, in order:

1. The masthead numbers, the docket of 12 cases and the first packet, rendered from the bundle. No
   network beyond this origin and Google Fonts.
2. **Boot the engine in this browser** â†’ about 12 MB of Pyodide from jsDelivr, then
   `38 files mounted`. Roughly 5 to 15 seconds on a first visit, under two on a warm cache.
3. **Run this case live** â†’ the packet re-renders with a `live run` chip, a wall-clock figure
   measured in the tab (typically 20 to 60 ms, slower than the ~8 ms CLI number because
   WebAssembly), and a parity line: *"the run in this tab reproduced the recorded packet exactly"*.
4. Edit the SQL in the Migration tab, press **Review this SQL** â†’ a real packet for your migration,
   with a note that there is no ground truth to score it against.

Runtime and cost for the whole section: about 20 seconds of wall clock, $0.00. Tested on Python
3.12.13 and Pyodide 0.26.4 (CPython 3.12) in Chromium and Firefox.

Publishing it: [`DEPLOY.md`](DEPLOY.md). GitHub Pages via the committed workflow, Vercel via the
committed `vercel.json`, or any static host with publish directory `site`. The Pages job re-runs the
tests, the evaluation, the claim checker and the driver parity check before it publishes, so a
deployed page that disagrees with the repository fails the build instead of shipping.

If you have no browser at hand, `site/standalone.html` opens from disk with every recorded packet
inlined, and the CLI in sections 2 to 4 is the reference implementation anyway.