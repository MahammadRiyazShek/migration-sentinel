# Supervisor session 11: the doc auditor, audited

**Role.** External supervisor. Not the author. The job is to find what the repository's own
verification cannot see, on the assumption that everything it *can* see is already green -
which it was: 52 tests OK, `44/44 claims hold`, `6/6 documentation checks`, `7/7 submission-text
checks`, 12/12 packets, on a clean unzip of the submitted archive, Python 3.12.13, offline,
first attempt, 0.7 s for the whole evaluation.

So a green suite is the starting condition of this session, not its result.

---

## 1. Critique layer: three hidden assumptions in the approach as submitted

**A1. "The audits cover the docs."** They cover the *phrasings the author had already seen go
stale*. `check_docs.py` looks for the literal shape `N/N claims`. The judge entry point says
`27/27 published claims`. One adjective, inserted between the fraction and the noun, and the
guard is blind - so the first file a judge opens advertises `27/27` for a command that prints
`44/44`. This is not a new defect class. It is v7's defect class, in v7's own guard, and the
repository already published the lesson: *a defence audited in its own vocabulary reports on
the attacker's imagination, not on itself.* Iteration 10 applied that lesson to the narrator
and left the doc auditor holding the same bag.

**A2. "Counts that matter are claim counts and test counts."** Those two have audits. The
number of *checks* an audit runs has none, and it had already drifted: `JUDGE_START_HERE.md`
says `6 checks on the description in the submission form` on line 22 and `Seven checks:` on
line 94. Same document, same tool, two numbers, and the tool prints `7/7`. A judge who reads
top to bottom hits the contradiction before the evidence.

**A3. "If it renders for me, it renders."** `REPRODUCTION.md` is missing one closing fence at
line 263. From §5a to the end of the file - the human approval gate, the hosted-model path,
bring-your-own-migration, the review desk - headings render inside a code block and commands
render as prose on GitHub. Nothing in 52 tests reads prose, and the mojibake check reads bytes,
not structure. The reproducibility row is 15% of the score and its guide is the one document
whose *layout* is load-bearing.

**Bonus, A4, the one I could not fix by editing text.** Rerunning the evaluation rewrites 80
files under `results/`. Every one of them differs. A judge who reproduces and then diffs sees
80 modified files against a submission whose entire pitch is verified determinism. The diffs
are wall-clock `ms` fields and nothing else - but "trust me, it is only the timings" is exactly
the sentence this project exists to refuse.

---

## 2. Variation operator: two radically different ways to answer this

**V1 - Delete the numbers.** Strip every count from the prose and have the docs cite commands
instead of results: no `44/44`, no `52 tests`, no `7 checks`, just "run it and read the last
line". A claim you never write cannot go stale.
*Rejected.* It is the cheapest possible fix and it destroys the thing that makes this submission
legible in five minutes. A judge on a rota wants the number in the document *and* the command
that re-asserts it. Removing the number to protect the guard optimises for the guard.

**V2 - Generate the docs.** Make `JUDGE_START_HERE.md` a template rendered from `results/*.json`
at build time, the way `results/*.md` already are. Staleness becomes structurally impossible,
which is strictly stronger than any regex.
*Rejected, with regret, and this is the honest reason:* the entry point is prose a human wrote
for humans, and templating it three hours before a deadline swaps a known bug class for an
unknown one in the highest-stakes file in the repository. The v10 log already records what
happens when this text is edited outside the reach of a checker. What V2 gets right is kept:
**the truth is read out of the tool at run time, never typed twice** - the fix below reads the
totals by executing the tools, and only the *pattern* is loosened.

**Chosen: V3, the synthesis.** Keep the numbers in the prose. Read every quantity out of the
tool that owns it. Make the pattern loose enough to catch phrasings nobody has written yet, and
allow a stale number only where the line *dates itself* - so changelogs and supervisor logs stay
honest records instead of becoming lies the audit has to whitelist one at a time.

---

## 3. Findings log, which is what the execution below follows

| # | defect | where | invisible to | fix |
|---|---|---|---|---|
| F1 | `27/27 published claims`, truth 44 | `JUDGE_START_HERE.md:20` | `CLAIM_COUNT` requires `N/N claims` with nothing between | loosen the pattern, date-exempt the honest history |
| F2 | `27 claims about the numbers`, truth 44 | `README.md:549` | README excluded wholesale from the claim audit because its changelog cites old counts | audit README too, exempt only *dated* lines |
| F3 | `6 checks` vs `Seven checks` vs `7/7` | `JUDGE_START_HERE.md:22` and `:94`, `README.md:354`, `docs/SUBMISSION.md:70` | no audit exists for the size of an audit | new check: read `len(CHECKS)` and the submission-text total from the tools |
| F4 | unclosed ```` ```bash ```` fence inverts the back half of the guide | `REPRODUCTION.md:263` | no test reads markdown structure | new check: no `##`-level heading inside a language-tagged fence |
| F5 | `193 authored files`, truth 292 | `REPRODUCTION.md:262` | same class as F1, fourth quantity | stop hard-coding a number the tool prints anyway |
| F6 | `Sixty seconds, four commands` over a block of six; "the fourth command" points at the wrong one | `JUDGE_START_HERE.md:13,25` | nothing counts the commands in the block | name the command instead of its position |
| F7 | 80 files differ on rerun, all wall-clock | `results/` | `check_results.py` compares decisions, and is right to | new tool: prove it, do not assert it |

---

## 4. Execution

1. **`tools/check_docs.py`**: `CLAIM_COUNT` loosened to allow up to three words between the
   fraction and `claims`; bare `N claims` added; `README.md` brought into the claim audit; a
   line is exempt only if it dates itself (`->`, `as of`, `was`, `v1`..`v10`). New check
   **`no stale count for the size of an audit`** runs `check_docs` (itself) and
   `check_submission_text` and asserts every doc line naming either tool agrees, in digits or
   in words. New check **`no heading trapped in a code fence`**, scoped to language-tagged
   fences, because an untagged fence quoting tool output may legitimately contain a `###`.
   Six checks become eight.
2. **`tools/check_determinism.py`**, new: copies the repository to a temporary directory, reruns
   the evaluation, the held-out set and the invariance sweep there, and diffs every regenerated
   file against the committed one with wall-clock fields normalised. Prints the exact set of
   fields that move and asserts nothing else does. F7 answered with a command instead of a
   claim. The committed tree is never written to.
3. **Docs**: F1-F6 corrected in the live documents only. No supervisor log, changelog row or
   session trace is rewritten - `27/27` was true in v5 and the audit now proves those lines are
   dated rather than stale.
4. **Tests**: `TestDocAudit` and `TestDeterminism` added. Each new pattern is fed the exact
   string that defeated its predecessor (`27/27 published claims`, `6 checks on ... check_submission_text.py`,
   a stripped closing fence) and asserted to fail, so no new regex is left undefended - the
   standard `TestSubmissionText` already set for the nine load-bearing sentences.

## 5. What this session did not fix, published in the same place as what it did

* **The video is still v2.** `docs/VIDEO_ADDENDUM.md` remains the correction table. Nothing in
  this session can be recorded in the time left, and a re-record with three hours on the clock
  is a worse risk than a documented delta.
* **The check-count audit only reads lines that name the tool.** `Seven checks:` at
  `JUDGE_START_HERE.md:94` names no file, so it was corrected by hand and is not defended by a
  pattern. That is a perimeter, it is drawn on purpose, and it is written down here rather than
  discovered by a judge.
* **Two ground-truth hazards are still missed on purpose** (`case_09`, `holdout_06`), the
  coverage gate still costs +0.7 modelled minutes, and the corpus is still the world. This
  session moved no decision metric, and asserts that it did not:
  unsafe approvals 0/12 and 0/9, recall 0.970 and 0.96, precision 0.970, plans 12/12 and 9/9,
  9.2 and 10.7 minutes per case, `0 of 180` and `0 of 126` decision surfaces moved. Every one
  re-asserted by `tools/check_results.py` after the edits, not before.

## 6. Self-review of this session's own first draft, since that was the instruction

* **Draft 1 fixed the three stale numbers and stopped.** That is the v3-blocklist mistake
  verbatim: patching the instances the supervisor happened to find, leaving the guard that
  missed them exactly as blind. The pattern had to move, or the next adjective wins.
* **Draft 1 audited README wholesale** and immediately failed on the Improvement Changelog,
  where `claims 23/23 -> 27/27` is the honest record of an older run. The first instinct was an
  allow-list of line numbers. The date-exemption rule replaced it: allow-lists rot, and a rule
  that reads the line's own tense does not.
* **Draft 1 flagged 19 "headings inside fences"**, of which 18 were shell comments (`# ->`) and
  one was intentional. A check that cries wolf 18 times out of 19 gets switched off by the
  person who owns it, so the scope narrowed to language-tagged fences and `##`-level headings,
  where the signal is 1/1 and the one real defect is the one that prints.
