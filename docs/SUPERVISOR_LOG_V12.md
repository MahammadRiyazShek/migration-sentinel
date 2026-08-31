# Supervisor log v12: the interpreter, the run id, and the audit's own docstring

An external supervisor pass over the **v11 archive as submitted**, run in a separate context with
a sandboxed shell and no network, on the standing instruction: critique the approach, generate
radically different alternatives, write the findings down *before* executing, then execute and do
not hand the work back.

Everything the suite can see was already green, twice, on the first attempt:

| command | result | interpreter |
|---|---|---|
| `python3 -m unittest discover -s tests` | 69 tests OK | 3.12.13 and 3.11.2 |
| `python3 tools/check_results.py` | `44/44 claims hold` | both |
| `python3 tools/check_docs.py` | `7/7 documentation checks` | both |
| `python3 tools/check_submission_text.py` | `7/7 submission-text checks` | both |
| `python3 tools/check_determinism.py` | 144 files, 0 decision differences | both |

So this session went looking for what none of those five commands can see. Four things, in the
order they were found.

---

## 1. The critique, written before anything was executed

**Hidden assumption 1: "3.11 and 3.12 verified" is a statement about the numbers.** It is not. It
was a statement about *exceptions*: the tests do not raise on either. Nothing in this repository
had ever compared the two `results/` trees. Dict ordering, float repr, `round`, the `re` module
and the bundled `sqlite3` are all plausible routes from an interpreter upgrade to a moved verdict,
and none of them raises. A judge reading "verified" reads it as "the packet you see is the packet
I saw", which was never checked.

**Hidden assumption 2: the committed evidence is what the harness wrote.** `JUDGE_START_HERE.md`
invites a judge to run one packet first, and `python3 -m sentinel review` writes to `results/` by
default. It mints `run-<8 hex>` where the harness writes `eval-<case>`. So a judge who follows the
documentation *in the order it is written* makes `tools/check_determinism.py` print `FAIL` on the
flagship reproducibility command - because of a random hex string, on a packet that is otherwise
byte-identical. This was not a hypothesis. It happened to this session on its second command, and
it is what a judge would read as "the numbers do not reproduce".

**Hidden assumption 3: the audits' own counts are audited.** `tools/check_docs.py` reads markdown,
because that is where a judge reads a number. Its own module docstring announced **"Six checks"**
while running seven, and `tools/check_submission_text.py` announced **"Eight checks"** while
running seven. The tool that exists because a count was typed twice had its own count typed twice,
in the first paragraph anyone reads about it. In the same file, a first definition of
`_current_claim_count` sat shadowed and dead by a second one, with a stricter regex: the audit
against stale duplication, carrying a stale duplicate.

**And the version, found while reading for the above.** Three live documents said **"the repository
is v10"** with `docs/SUPERVISOR_LOG_V11.md` sitting in the tree - including the first line of the
video notice, whose entire job is to tell a judge which artefact is newer than which.

---

## 2. Two radically different ways to spend the remaining window

**Option A: ship no code. Re-record the video against v12.** End-to-end quality is 20% of the
rubric and the submitted video is nine releases old; the addendum discloses it honestly, but a
judge still watches stale numbers for five minutes. This is the largest single scoring delta
available, and it is the one deliverable a repository cannot produce for itself.
*Adopted in part.* A single-take script written against the current numbers is committed as
[`VIDEO_SCRIPT_V12.md`](VIDEO_SCRIPT_V12.md), timed to 4:40 with the exact commands and the exact
on-screen figures, so the re-record is a recording task rather than an authoring task. The
addendum stays authoritative until it happens.

**Option B: delete the count audits and generate the documents.** Every drifted number in eleven
releases has been the same defect: one quantity typed in two places. Generate `README.md`,
`JUDGE_START_HERE.md` and the form text from templates fed by `results/*.json`, and drift becomes
structurally impossible - no audit required.
*Rejected*, for a reason worth writing down: it removes the drift by removing the prose. A
generated README reads like a generated README, and the rubric row that is 20% of the score asks
whether the output "reads as clearly AI generated" rather than as something a person would sign.
The value here is a human argument with checkable numbers in it, not a report with no author. So
the numbers stay hand-written and audited, and the audit's *perimeter* got the work instead: it
now reads the two places it structurally could not see.

**Also considered and rejected: fix the run-id trap in `sentinel/cli.py`.** The clean fix is for
`review` to write to a scratch directory unless asked. `sentinel/` is the frozen decision tree,
and `results/holdout/decision_code_manifest.json` attests that exactly three files changed after
the held-out labels were written. Touching `cli.py` makes that four, and spends a held-out claim
on a documentation defect. Fixed in `tools/` and the docs instead, where the freeze does not
reach.

---

## 3. What was executed

| # | finding | fix | evidence |
|---|---|---|---|
| F1 | "3.11 and 3.12 verified" was never a claim about the numbers | new `tools/check_cross_version.py`: reruns all four generators under both interpreters in two private copies and diffs the trees, raw then wall-clock-normalised | `results/cross_version.md`: **146 files, 0 decision differences** on CPython 3.11.2 and 3.12.13; two new claims in `check_results.py` |
| F2 | the documented first command overwrites a committed packet and fails the determinism audit | preflight in `check_determinism.py` that detects an interactive `run-<hex>` in `results/`, names the cause, and prints both fixes (`make eval`, or `--out`) | reproduced, then re-reproduced after the fix: the packet is identical on every byte except its own run id; `TestProvenancePreflight` |
| F3 | `check_docs.py` said "Six checks" (7), `check_submission_text.py` said "Eight checks" (7), and `check_docs.py` carried a dead shadowed duplicate | 8th documentation check: the three counting tools' own docstrings, with a quoted count treated as a citation rather than a claim; duplicate deleted | `9/9 documentation checks`, `TestDocAudit` cases for the word-number, the citation and the dated line |
| F4 | three live documents declared v10 at v11, including the video notice | 9th documentation check: the version is read from the newest `docs/SUPERVISOR_LOG_V<N>.md`, never retyped | four corrected statements; `TestDocAudit` regression on the exact sentence that defeated the first draft |

Claims **44 -> 46**. Documentation checks **7 -> 9**. Tests **69 -> 82**. No file under `sentinel/`
was touched: the freeze attestation still names the same three post-freeze files, and every
decision number was re-asserted *after* the edits rather than before - unsafe approvals 0/12 and
0/9, recall 0.970 and 0.96, plans 12/12 and 9/9, 9.2 and 10.7 modelled minutes, decision surface
0/180 and 0/126. None moved.

### The unflattering half of F1

The second cross-interpreter claim is that the published wall-clock figures are the one thing that
is **not** portable: 64 files moved on timing alone, worst delta 100% relative, 7.1 ms absolute,
over 634 numbers (a recorded run; both figures belong to the machine). Same machine, same data, different interpreter. It is in the ledger as a claim
rather than in a footnote, because "reproducible" in this repository means the decisions, and it
should be legible that it has never meant the milliseconds.

---

## 4. Reading it again: three mistakes in this session's own work

**Mistake 1 - the version check exempted the defect it was written for.** The first draft reused
`_is_dated`, which exempts any line carrying a version token. The defective sentence is *"The
submitted video was recorded against v2. The repository is v10"*: it dates itself with the version
of something else. The check passed on all four instances of the bug it existed to catch. This is
the repository's own hot take arriving for the third time - a guard tested only against the
example that motivated it. Fixed: the phrase is present tense by construction, only a quoted
citation is exempt, and the regression test feeds it that exact sentence.

**Mistake 2 - the timing disclosure was theatre.** The first report printed "worst wall-clock
delta: 100%", which is 0.0 ms against 0.1 ms wearing a percentage sign: precisely the unanchored
percentage this project refuses everywhere else. Fixed: relative *and* absolute, both in the JSON
and in the claim, and the report says which one to read.

**Mistake 3 - the new evidence file made an unaudited number stale.** Adding
`results/cross_version.{json,md}` grew the determinism comparison from 144 files to 146, and "144
files compared" was quoted in three live documents. No audit owns that number - it is not a claim,
a check or a test count - so nothing caught it and nothing would have. Corrected by hand, and the
perimeter is published rather than discovered: **a number no tool owns still goes stale here**,
which is the same sentence v11 wrote about counts and v5 wrote about guards.

---

## 5. What a judge should take from this

Three releases in a row, this repository has found its own thesis inside its own defences. v5: a
prose guard audited in its own vocabulary reports on the author's imagination. v11: the audit that
enforces "do not type a number twice" had typed its number twice. v12: the audit written to catch
a stale self-description exempted every stale self-description in the tree, on the first run,
because the sentence mentioned another version.

The lesson is not "add another check". It is that **every honesty layer has a perimeter drawn by
the examples its author had**, and the only reliable way to find that perimeter is to change the
world the layer lives in: a second schema (v6), a second attacker written against your own fix
(v5), a second interpreter (v12) - and, cheapest of all, following your own documentation in the
order a stranger would.
