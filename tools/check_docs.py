#!/usr/bin/env python3
"""Assert the documentation makes no claim the repository cannot back.

`tools/check_results.py` does this for numbers: every published figure is re-asserted from
raw JSON. This does the same job for prose, because the seventh supervisor session found
three defects no results audit could ever see:

  * `docs/SUPERVISOR_LOG_V6.md` announced a file (`SUBMISSION_DESCRIPTION.md`) that was
    never committed - a claim about the repository that the repository contradicted;
  * two rival "Judges start here" pages sat at the root with different command lists and
    different runtime figures, so the documented entry point depended on which one a judge
    happened to open;
  * three table cells in the newest entry point rendered as a mis-decoded section sign -
    UTF-8 read as Latin-1 - invisible to all 33 tests, because no test reads prose.

None of that moves a metric. All of it is the first thing a judge sees. So it gets an audit
with an exit code, like everything else here. Six checks, standard library, no network.

The sixth check is the eighth session's: the claim-count audit below existed because a stale
"18/18 claims" survived two releases, and the test count sat in the same six documents with
no audit at all. Same defect class, same fix.

Standard library only, no network. Run from the repository root:

    python3 tools/check_docs.py
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Copies and build output, not authored documentation.
SKIP_DIRS = {".git", "site", "__pycache__", ".github"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".jsonl", ".yml", ".txt", ".html"}

# Byte sequences that mean UTF-8 was decoded as Latin-1 somewhere upstream.
MOJIBAKE = ("\u00c2\u00a7", "\u00c2\u00a0", "\u00e2\u0080\u0099", "\u00e2\u0080\u009c",
            "\u00e2\u0080\u009d", "\u00e2\u0080\u0093", "\u00e2\u0080\u0094")

BACKTICK_REF = re.compile(r"`([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:md|py|json|jsonl|html|yml|txt))`")
LINK_REF = re.compile(r"\[[^\]]*\]\((?!https?:|mailto:|#)([^)\s]+)\)")

# Bare filenames with no separator are shorthand inside a table whose heading already named
# the directory. Only references carrying a path separator are treated as resolvable claims.


def authored_files():
    out = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        out.append(path)
    return out


def _line_of(text, needle):
    return next((i for i, ln in enumerate(text.splitlines(), 1) if needle in ln), 0)


def check_no_mojibake(files):
    bad = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for seq in MOJIBAKE:
            if seq in text:
                bad.append(f"{path.relative_to(ROOT)}:{_line_of(text, seq)} mis-decoded {seq!r}")
    return bad


_ALL_PATHS = None


def _resolves(ref, from_file):
    """A reference resolves if it is a real path from the file, from the root, or a suffix of
    one - docs legitimately write `prompts/cartographer.md` for a file under
    `sentinel/agents/prompts/` when the surrounding heading already named the subtree."""
    global _ALL_PATHS
    if (from_file.parent / ref).exists() or (ROOT / ref).exists():
        return True
    if _ALL_PATHS is None:
        _ALL_PATHS = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file()]
    return any(p == ref or p.endswith("/" + ref) for p in _ALL_PATHS)


def check_references_resolve(files):
    bad = []
    for path in files:
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        refs = set(BACKTICK_REF.findall(text)) | set(LINK_REF.findall(text))
        for ref in sorted(refs):
            if "/" not in ref or "*" in ref or "<" in ref:
                continue
            if not _resolves(ref, path):
                bad.append(f"{path.relative_to(ROOT)}:{_line_of(text, ref)} references missing {ref}")
    return bad


def check_single_entry_point(_files):
    entries = sorted(p.name for p in ROOT.glob("*START_HERE*.md"))
    if entries == ["JUDGE_START_HERE.md"]:
        return []
    if not entries:
        return ["no JUDGE_START_HERE.md at the repository root"]
    return ["more than one judge entry point at the root, so the documented starting point "
            f"is ambiguous: {', '.join(entries)}"]


def check_paste_ready_description(_files):
    """The submission form caps the description at 9,000 characters, and says so on the field.

    v9: this check asserted 10,000 for two releases, and the markdown copy below the marker was
    9,744 - so a green check sat over a description the form would have truncated. The cap is
    read off the form now, and the two copies of the text are asserted identical instead of
    merely both existing: a markdown variant that cannot be pasted into a plain-text field is a
    second source of truth with no reader.
    """
    path = ROOT / "SUBMISSION_DESCRIPTION.md"
    if not path.exists():
        return ["SUBMISSION_DESCRIPTION.md is referenced by docs/SUPERVISOR_LOG_V6.md but absent"]
    body = path.read_text(encoding="utf-8")
    marker = "<!-- PASTE BELOW THIS LINE -->"
    if marker not in body:
        return [f"SUBMISSION_DESCRIPTION.md has no {marker} marker, so its length is not auditable"]
    paste = body.split(marker, 1)[1].strip()
    problems = []
    if len(paste) > 9000:
        problems.append(f"paste-ready description is {len(paste)} characters, over the form's "
                        f"9,000 limit by {len(paste) - 9000}")
    form = ROOT / "SUBMISSION_FORM_TEXT.txt"
    if not form.exists():
        problems.append("SUBMISSION_FORM_TEXT.txt is absent, so the text actually pasted into the "
                        "form is not committed")
    elif form.read_text(encoding="utf-8").strip() != paste:
        problems.append("SUBMISSION_DESCRIPTION.md and SUBMISSION_FORM_TEXT.txt disagree below the "
                        "marker: two copies of the one artefact that lives outside the repository")
    if problems:
        return problems
    print(f"        paste-ready description: {len(paste)} of 9,000 characters, byte-identical to "
          f"SUBMISSION_FORM_TEXT.txt")
    return []


# Documents that describe the repository as it is now, as opposed to the changelogs, supervisor
# logs and session traces, where an older claim count is the honest record of an older run.
LIVE_DOCS = ("JUDGE_START_HERE.md", "REPRODUCTION.md", "SUBMISSION_DESCRIPTION.md",
             "docs/SUBMISSION.md", "SUBMISSION_FORM_TEXT.txt")

# The README carries the Improvement Changelog, where an older claim count is the honest
# record of an older run, so it is not a current-state document for CLAIM_COUNT. Its
# Quickstart does state a live test count, and no changelog row phrases one as "N tests",
# so it is a current-state document for TEST_COUNT.
TEST_COUNT_DOCS = LIVE_DOCS + ("README.md",)
CLAIM_COUNT = re.compile(r"\b(\d+)/(\d+) claims\b")


def _current_claim_count():
    """Ask tools/check_results.py how many claims it actually asserts."""
    import subprocess
    out = subprocess.run([sys.executable, str(ROOT / "tools/check_results.py")],
                         capture_output=True, text=True, cwd=ROOT).stdout
    m = CLAIM_COUNT.search(out.strip().splitlines()[-1] if out.strip() else "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def check_claim_counts_current(_files):
    truth = _current_claim_count()
    if truth is None:
        return ["could not read a claim count out of tools/check_results.py"]
    held, total = truth
    bad = []
    if held != total:
        bad.append(f"tools/check_results.py reports {held}/{total}: a claim is failing")
    for rel in LIVE_DOCS:
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), 1):
            for m in CLAIM_COUNT.finditer(line):
                if (int(m.group(1)), int(m.group(2))) != truth:
                    bad.append(f"{rel}:{line_no} says {m.group(0)}, the audit asserts {total}")
    if not bad:
        print(f"        tools/check_results.py asserts {total} claims; the live docs all say so")
    return bad


TEST_COUNT = re.compile(r"\b(\d+) (?:unittest |stdlib )?tests\b")


def _current_test_count():
    """Ask unittest how many tests there actually are."""
    import subprocess
    out = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                         capture_output=True, text=True, cwd=ROOT)
    m = re.search(r"^Ran (\d+) tests?", out.stdout + out.stderr, re.M)
    return int(m.group(1)) if m else None


def check_test_counts_current(_files):
    """A stale claim count survived two releases before v7 caught it. The test count sits in
    the same documents and had no audit at all."""
    truth = _current_test_count()
    if truth is None:
        return ["could not read a test count out of `unittest discover`"]
    bad = []
    for rel in TEST_COUNT_DOCS:
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), 1):
            for m in TEST_COUNT.finditer(line):
                if int(m.group(1)) != truth:
                    bad.append(f"{rel}:{line_no} says {m.group(0)}, "
                               f"unittest discover runs {truth}")
    if not bad:
        print(f"        unittest discover runs {truth} tests; the live docs all say so")
    return bad


CHECKS = [
    ("no mis-decoded characters in authored text", check_no_mojibake),
    ("every path-shaped file reference resolves", check_references_resolve),
    ("exactly one judge entry point at the root", check_single_entry_point),
    ("paste-ready description exists and fits the form", check_paste_ready_description),
    ("no stale claim count in a current-state document", check_claim_counts_current),
    ("no stale test count in a current-state document", check_test_counts_current),
]


def main():
    files = authored_files()
    failed = 0
    for label, fn in CHECKS:
        problems = fn(files)
        if problems:
            failed += 1
            print(f"FAIL  {label}")
            for p in problems:
                print(f"        {p}")
        else:
            print(f"PASS  {label}")
    print()
    if failed:
        print(f"{len(CHECKS) - failed}/{len(CHECKS)} documentation checks hold - {failed} failed")
        return 1
    print(f"{len(CHECKS)}/{len(CHECKS)} documentation checks hold across {len(files)} authored files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
