# Submission mechanics

Repo: <https://github.com/MahammadRiyazShek/migration-sentinel> ·
Live desk: <https://migration-sentinel-frvo.vercel.app/>

This file is the checklist for filling in the form. It deliberately **does not contain the description**.

Until v10 it carried its own v5-era copy, 9,753 characters under a "10,000 limit" note, with a
different title, no held-out section and the sentence "Twelve cases, one schema, ground truth I wrote"
that the freight schema had already made false. Two copies of the description were pinned to each
other by `tools/check_docs.py` and this third one was pinned to nothing - so it drifted, in the one
document that calls itself current state. Reasoning:
[`SUPERVISOR_LOG_V10.md`](SUPERVISOR_LOG_V10.md).

There is one description. It lives in [`SUBMISSION_FORM_TEXT.txt`](../SUBMISSION_FORM_TEXT.txt), is
mirrored byte-for-byte below the marker in
[`SUBMISSION_DESCRIPTION.md`](../SUBMISSION_DESCRIPTION.md), and every figure in it is re-read out of
`results/*.json` by `tools/check_submission_text.py`.

---

## Title field

```
Migration Sentinel: agents that replay your schema migration, verify the rollout plan they wrote, name what they could not see, and never let the model write the verdict
```

## Description field

Paste [`SUBMISSION_FORM_TEXT.txt`](../SUBMISSION_FORM_TEXT.txt) as-is. Do not reformat it:

- the field is **plain text and capped at 9,000 characters**, both read off the field's own label;
- the committed text is **8,897 characters as authored, 8,946 once line breaks are normalised to
  CRLF** - a form POST counts a line break as two characters and the counter in the page counts one,
  and it has to fit both;
- it is 7-bit ASCII with no markdown, because a table or a backtick renders literally there and a
  smart quote can be mangled;
- seven checks assert all of that plus every figure and nine load-bearing sentences:

```bash
python3 tools/check_submission_text.py
```

If that command does not print `7/7 submission-text checks hold`, the text in the form is not the text
this repository can back.

## Video URL field

```
https://www.youtube.com/watch?v=JGXnRwWWmrQ
```

The recording predates the coverage gate, the structural narrator and the held-out world.
Architecture, problem framing, baseline comparison and the walkthrough are unchanged; some on-screen
numbers are stale. [`VIDEO_ADDENDUM.md`](VIDEO_ADDENDUM.md) is the exhaustive on-screen-versus-repo
diff and carries a 90-second delta script if there is time to append one. Where the video and the
repository disagree, `results/comparison.md` and `results/model_invariance.md` are authoritative, and
the description says so.

## Source code field

Upload the archive built from the tree that passes:

```bash
python3 -m unittest discover -s tests    # 82 tests
python3 eval/run_eval.py --ablations     # 108 reviews
python3 eval/run_holdout.py --ablations  # 9 held-out cases, three arms
python3 eval/model_invariance.py         # 180 reviews
python3 tools/check_results.py           # 46/46 claims hold
python3 tools/check_docs.py              # 9 documentation checks
python3 tools/check_submission_text.py   # 7 submission-text checks
```

Check the uploaded filename before saving. An older archive beside a current description fails the
completeness and reproducibility gate before rubric scoring begins.

## Pre-submit checklist

- [ ] description pasted from `SUBMISSION_FORM_TEXT.txt`, unedited, `7/7` green
- [ ] title and video URL fields match the two blocks above
- [ ] source archive is the tree that prints `46/46 claims hold`, `9/9 documentation checks` and
      `0 decision differences` on both `check_determinism.py` and `check_cross_version.py`
- [ ] `agent_traces/INDEX.md` regenerated (`python3 tools/collect_agent_traces.py --write`) and secret
      scan clean
- [ ] live desk loads and its recorded packets match `results/`
