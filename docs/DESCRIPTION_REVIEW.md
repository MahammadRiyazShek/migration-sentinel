# Supervisor pass over the submitted description (v16 repository, no code change)

This pass changed no code and no result. It audited the one artefact a judge reads before
they read anything else, and which no tool had previously been able to fail on substance:
the 9000-character plain-text Description pasted into the micro1 form.

## Log: three hidden assumptions in the description as submitted

1. **"The audit passes, so the text is right."** `tools/check_submission_text.py` proved every
   figure in the description matched raw JSON. It could not prove the description carried the
   repository's most load-bearing finding, because absence is not a mismatch. The v16 plan
   audit - the layer that caught this pipeline shipping defective SQL of its own under a
   printed `plan verified: true` - appeared nowhere in the judged text. The strongest evidence
   for both Measured Improvement and Hot Take was sitting in `results/redteam3.md` only.
2. **"A bullet and its prose cannot disagree."** They did. The ablation block printed
   `Replay only: 1/12` and then claimed "Replay alone is worse than rules alone, 2 unsafe
   approvals against 1". Both statements are true, of different arms: 2/12 needs
   `plan_audit=False`. The figure checker validated the row, the sentence went unchecked, and
   a judge reading four lines apart would have found the contradiction before any tool did.
3. **"Length is a formatting problem."** It is an editorial one. At 7 spare characters the
   description could not absorb a new finding without a decision about what was worth less
   than it. Treating the budget as slack rather than as a ranking is how the newest result
   ends up omitted while three paragraphs of superseded v13 narration stay.

## Log: two radically different ways to solve it, and why neither shipped

- **Rewrite the description around the v16 layer as the headline.** Rejected: the primary
  metric of the entry is unsafe approvals on the labelled corpus, and leading with the
  self-audit of the generated plan would demote 0/12 and 0/9 to supporting detail. The plan
  audit is the best story in the repository and not the best answer to "does it work".
- **Teach `check_submission_text.py` to fail on omission - require a sentence per results
  file.** Rejected under the same rule the rulebook layer was built on: a checker written from
  the same list as the text it checks only tests what the author already remembered. It also
  cannot be validated inside the window. Recorded as the next thing to build, not shipped.

What shipped instead: one new paragraph, `THE PLAN IT WRITES ITSELF`, funded by 800 characters
cut from superseded v13 narration; the contradicting ablation sentence corrected to the scored
arm; and the v16 lesson folded into the hot take.

## Re-read: three defects in this pass, found and fixed before it closed

1. First draft of the new paragraph pushed the text to 9761 CRLF characters and would have
   been silently truncated by the form. Fixed by cutting rather than by hoping: 8998 of 9000,
   audited on the stricter CRLF count, not the counter in the page.
2. First draft asserted "the audit found 7 defects" without the denominator the rest of the
   description is careful about. Fixed to "7 defects across 6 of them" out of 34 labelled
   cases, with `moved 0 verdicts` in the same sentence.
3. First draft dropped the unflattering half. The v16 layer costs reviewer minutes (9.2 to
   10.0) and cost the entry its cleanest ablation line. Both are now in the paragraph, in the
   same voice as the ten other claims that make this pipeline look worse.

## Evidence

`python3 tools/check_results.py` 75/75 - `python3 tools/check_submission_text.py` 7/7 -
`python3 tools/check_docs.py` 9/9 - `make verify` green. `SUBMISSION_FORM_TEXT.txt` and the
text below the marker in `SUBMISSION_DESCRIPTION.md` are byte-identical, enforced.

---

# Second pass: the string nobody was counting (no code change, no result change)

The description above passed every audit in this repository and the platform refused it:

    description_text: Ensure this field has no more than 10000 characters.

The text was 8,952 plain characters against a limit of 10,000, and both numbers were right.
The field is a rich-text editor. What the server counts is `description_text`, the HTML the
editor emits, and a styled paste of that text renders roughly 12,100 characters: a block
wrapper and a style attribute per paragraph, an empty paragraph per blank line, and an anchor
around each bare URL. Roughly 3,100 characters of markup nobody typed and no checker measured.

This is the v9/v10 defect one layer further out, for the third time. v9 asserted a cap it had
never read off the field. v10 measured a length it had already declared legal. v16 measured the
authored string and the CRLF string, and the server sees neither.

**Fixed.** `tools/check_fits_the_form` now models the rendered string and enforces the only
number the platform has ever volunteered - 10,000, quoted from its own rejection rather than
from a label that has already moved once. It reports all three counts and the styled-paste
figure, and it prints the paste mode that makes the difference.

**Also cut.** About 300 characters of prose that were not carrying evidence, so the rendered
plain-text paste lands at 9,217 of 10,000 with 783 to spare instead of fitting by luck. No
figure, no load-bearing claim and no required disclosure was removed: all 9 claim regexes, the
12 post-freeze filenames and every audited arm still match raw JSON.

**How to paste it.** Ctrl+Shift+V, or paste into a plain editor first. A normal Ctrl+V from a
rendered page carries the style attributes that caused the rejection, and no amount of cutting
survives a paste that adds 90 characters of markup per paragraph.

**Lesson, same shape as the rest of this repository.** Every checker measures a string, and the
string it measures is a choice. Ask which one the thing that can reject you is counting, then
measure that one. An audit of the artefact you authored is not an audit of the artefact you
submit.
