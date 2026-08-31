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
with an exit code, like everything else here. Nine checks, standard library, no network.

The eighth and ninth checks are the twelfth session's, and both close a hole in this file
rather than in the documentation it reads:

  * this audit reads markdown. The three tools that count things state their own size in
    their own module docstring, in prose, where nothing had ever looked - so
    `check_docs.py` said "Six checks" while running seven, and
    `check_submission_text.py` said "Eight checks" while running seven. The audit that
    exists because a count was typed twice had its own count typed twice.
  * three live documents said "the repository is v10" while `docs/SUPERVISOR_LOG_V11.md`
    sat in the tree, including the first paragraph of the video notice, whose entire job is
    to tell a judge which artefact is newer. The version of the repository is now read from
    the newest supervisor log rather than retyped.

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

# v11: the README used to be exempt from the claim audit wholesale, because its Improvement
# Changelog cites the claim counts of older runs and those citations are honest. Exempting the
# file to protect the changelog also exempted its repository-layout section, which is how
# `check_results.py (27 claims about the numbers)` survived to the submitted archive. The
# exemption is now per line and is granted by tense, not by filename: see _is_dated.
COUNT_DOCS = LIVE_DOCS + ("README.md",)
TEST_COUNT_DOCS = COUNT_DOCS

# v11: `CLAIM_COUNT` used to be exactly r"\b(\d+)/(\d+) claims\b", so
# `JUDGE_START_HERE.md` line 20 - "27/27 published claims re-asserted from raw JSON", against a
# command that prints 44/44 - passed the audit for three releases, in the first file a judge
# opens. One adjective between the fraction and the noun was the whole attack.
#
# That is this repository's own hot take arriving as a bug report against this repository: a
# defence audited in its own vocabulary reports on the author's imagination, not on itself. The
# counter is not a longer list of phrasings. It is to read the quantity out of the tool at run
# time and let the pattern be loose enough to catch the phrasing nobody has typed yet.
CLAIM_COUNT = re.compile(r"\b(\d+)\s*/\s*(\d+)(?:\s+[A-Za-z][A-Za-z-]*){0,3}\s+claims\b")
CLAIM_TOTAL = re.compile(r"\b(\d+)(?:\s+[A-Za-z][A-Za-z-]*){0,3}\s+claims\b")

# A line may cite an out-of-date count when it dates itself: a changelog row, a "was N, now M"
# sentence, an "as of v5". Allow-lists of line numbers rot; a rule that reads the line's own
# tense does not.
DATED = re.compile(r"->|-->|\bas of\b|\bwas\b|\bused to\b|\bthen\b")
OLD_VERSION = re.compile(r"\bv(\d+)\b")


def _is_dated(line):
    """A line dates itself, so an older count on it is a record rather than a drift.

    v13: the version range used to be spelled out - `v(?:[1-9]|10|11)` - which is the same
    hand-maintained list this file exists to catch elsewhere, and it went stale the moment v12
    shipped: every honest changelog row citing a v12 count started failing this audit for
    reasons that had nothing to do with the row. The range is read off docs/ now, so "v12"
    counts as dated once v13 exists and never before.
    """
    if DATED.search(line):
        return True
    truth = newest_release()
    if truth is None:
        return False
    return any(int(m.group(1)) < truth for m in OLD_VERSION.finditer(line))


def _stale_counts(text, pattern, truth, group=None):
    """Every match of `pattern` on an undated line whose captured number is not `truth`.

    Returns (line_no, matched_text, found) triples. `group` selects which capture carries the
    number; None means "the last group", which is the total in both `N/N x claims` and `N x
    claims`.
    """
    out = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if _is_dated(line):
            continue
        for m in pattern.finditer(line):
            found = int(m.group(group if group is not None else m.lastindex))
            if found != truth:
                out.append((line_no, m.group(0).strip(), found))
    return out


# v12: a first definition of `_current_claim_count` used to sit here, shadowed by the one below
# it and dead for two releases - the audit that reads other files for stale duplication carrying a
# stale duplicate of its own. It parsed the same output with a stricter regex, so it would have
# disagreed with the live one the moment a count moved.


def _tool_total(script, noun):
    """Run one of this repository's audits and read its own total out of its last line."""
    import subprocess
    out = subprocess.run([sys.executable, str(ROOT / script)],
                         capture_output=True, text=True, cwd=ROOT).stdout.strip()
    last = out.splitlines()[-1] if out else ""
    m = re.search(rf"\b(\d+)\s*/\s*(\d+)[^.]*?\b{noun}\b", last)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _current_claim_count():
    """Ask tools/check_results.py how many claims it actually asserts."""
    return _tool_total("tools/check_results.py", "claims")


# Which tool owns the number on a given line. A line naming a specific audit is making a claim
# about the size of *that* audit; anything else is talking about the claim ledger.
#
# v11: this mapping is the fix for a defect the previous audit could not have caught, because it
# had no notion of the size of an audit at all. `JUDGE_START_HERE.md` said "6 checks on the
# description in the submission form" on line 22 and "Seven checks:" on line 94 - one document,
# one tool, two numbers, and the tool prints 7/7. `README.md` called them "6 claims", which is
# how the same drift hid from a pattern looking for the word "checks".
WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}

# `N/N noun`, `N noun` and `Word noun`, with up to three words of prose in between, for the two
# nouns this repository counts things in.
COUNT_PATTERNS = [
    re.compile(r"\b(\d+)\s*/\s*(\d+)(?:\s+[A-Za-z][A-Za-z-]*){0,3}\s+(?:claims|checks)\b"),
    re.compile(r"\b(\d+)(?:\s+[A-Za-z][A-Za-z-]*){0,3}\s+(?:claims|checks)\b"),
    re.compile(r"\b(" + "|".join(WORD_NUMBERS) + r")(?:\s+[A-Za-z][A-Za-z-]*){0,2}\s+(?:claims|checks)\b",
               re.IGNORECASE),
]


def _owner_total(line, span, totals):
    """Resolve the number in `span` to the tool that owns it, by the noun first and the
    filename second. Returns (truth, owner) or (None, None) when nothing in the line claims
    the number - an unattributable "checks" is not audited rather than audited wrongly."""
    low, span_low = line.lower(), span.lower()
    if "documentation check" in span_low or "check_docs.py" in low and "check" in span_low:
        return totals["docs"], "tools/check_docs.py"
    if "submission-text check" in span_low or "submission text check" in span_low:
        return totals["submission_text"], "tools/check_submission_text.py"
    if "check_submission_text.py" in low:
        return totals["submission_text"], "tools/check_submission_text.py"
    if "check_docs.py" in low:
        return totals["docs"], "tools/check_docs.py"
    if "check_determinism.py" in low:
        return None, None            # counts nothing that could go stale
    if span_low.endswith("checks") or span_low.endswith("check"):
        return None, None            # a check count with no owner named on the line
    return totals["results"], "tools/check_results.py"


def stale_counts_in_line(line, totals):
    """Every count on one line that the tool owning it contradicts.

    Returns (span, found, truth, owner) tuples. Exposed as a function rather than buried in the
    file walk so `tests/test_all.py::TestDocAudit` can feed it the exact strings that defeated
    its predecessor - "27/27 published claims", "6 checks on ... check_submission_text.py", and
    the dated changelog rows that must stay exempt - instead of trusting a regex nobody attacks.
    """
    if _is_dated(line):
        return []
    spans = []
    for pattern in COUNT_PATTERNS:
        for m in pattern.finditer(line):
            spans.append((m.start(), m.end(), m.group(0).strip(), m.group(m.lastindex)))
    # The `N/N noun` and `N noun` patterns both fire on "44/44 claims"; keep the widest match at
    # each position so one drifted number is reported once.
    spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))
    kept, out = [], []
    for s in spans:
        if any(k[0] <= s[0] and s[1] <= k[1] for k in kept):
            continue
        kept.append(s)
    for _, _, span, raw in kept:
        truth, owner = _owner_total(line, span, totals)
        if truth is None:
            continue
        found = WORD_NUMBERS.get(raw.lower(), None)
        if found is None:
            found = int(raw)
        if found != truth:
            out.append((span, found, truth, owner))
    return out


def _tool_totals():
    """What each counting tool says its own size is, right now. `None` if one cannot be read."""
    results = _current_claim_count()
    submission = _tool_total("tools/check_submission_text.py", "checks")
    if results is None or submission is None:
        return None
    return {"results": results[1], "docs": len(CHECKS), "submission_text": submission[1],
            "_results_held": results[0]}


def check_counts_current(_files):
    """No current-state document states a count that the tool owning it contradicts.

    Covers the claim ledger (`tools/check_results.py`) and, from v11, the size of the two
    documentation audits, which had no audit of their own and had already drifted apart inside
    one file.
    """
    results = _current_claim_count()
    if results is None:
        return ["could not read a claim count out of tools/check_results.py"]
    held, total = results
    bad = []
    if held != total:
        bad.append(f"tools/check_results.py reports {held}/{total}: a claim is failing")
    submission = _tool_total("tools/check_submission_text.py", "checks")
    if submission is None:
        return bad + ["could not read a check count out of tools/check_submission_text.py"]
    totals = {"results": total, "docs": len(CHECKS), "submission_text": submission[1]}

    for rel in COUNT_DOCS:
        path = ROOT / rel
        if not path.exists():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace")
                                       .splitlines(), 1):
            for span, found, truth, owner in stale_counts_in_line(line, totals):
                bad.append(f"{rel}:{line_no} says {span!r}, but {owner} asserts {truth}")
    if not bad:
        print(f"        {total} claims, {len(CHECKS)} documentation checks, "
              f"{submission[1]} submission-text checks; the live docs all say so")
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
            if _is_dated(line):
                continue
            for m in TEST_COUNT.finditer(line):
                if int(m.group(1)) != truth:
                    bad.append(f"{rel}:{line_no} says {m.group(0)}, "
                               f"unittest discover runs {truth}")
    if not bad:
        print(f"        unittest discover runs {truth} tests; the live docs all say so")
    return bad


# v11: markdown structure, which no test in this repository read.
#
# `REPRODUCTION.md` was submitted missing one closing fence at line 263. From section 5a to the
# end of the file - the human approval gate, the hosted-model path, bring-your-own-migration,
# the review desk - every heading rendered inside a code block and every command rendered as
# prose. 52 tests pass on that file because none of them reads prose, and the mojibake check
# reads bytes rather than structure. The reproducibility row is 15% of the score and this is the
# document it is scored on.
#
# The scope is deliberately narrow: a heading at `##` level or deeper, inside a fence that was
# opened with a language tag. A shell comment is `# ...` and never `## ...`, and an untagged
# fence quoting tool output may legitimately contain a `###`. A check that fires 18 times to
# catch one defect gets switched off by whoever owns it - the first draft of this one did
# exactly that, and the narrowing is recorded in docs/SUPERVISOR_LOG_V11.md.
FENCE = re.compile(r"^\s*```+\s*(\S*)")
DEEP_HEADING = re.compile(r"^#{2,6} \S")


def trapped_headings(text):
    """(line_no, opener_line, heading) for every deep heading inside a language-tagged fence."""
    out, inside, opener, tagged = [], False, 0, False
    for line_no, line in enumerate(text.splitlines(), 1):
        fence = FENCE.match(line)
        if fence:
            if inside:
                inside = False
            else:
                inside, opener, tagged = True, line_no, bool(fence.group(1))
            continue
        if inside and tagged and DEEP_HEADING.match(line):
            out.append((line_no, opener, line.strip()))
    if inside and tagged:
        out.append((0, opener, "fence never closed before end of file"))
    return out


def check_no_trapped_headings(files):
    bad = []
    for path in files:
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, opener, heading in trapped_headings(text):
            where = f"{path.relative_to(ROOT)}:{line_no}" if line_no else \
                    f"{path.relative_to(ROOT)}"
            bad.append(f"{where} renders inside the code fence opened at line {opener}: "
                       f"{heading[:60]}")
    return bad


# v12. Two blind spots in this file, found by an external supervisor pass over this file.

# The tools that count things, and the noun each one counts. A module docstring is prose about
# the tool it sits in, so ownership is by file here rather than by what the line happens to name.
TOOL_COUNTS = {
    "tools/check_results.py": ("claims", "results"),
    "tools/check_docs.py": ("checks", "docs"),
    "tools/check_submission_text.py": ("checks", "submission_text"),
}

QUOTED = ('"', "'", "`")


def _is_citation(line, start, end):
    """A count in quotation marks or backticks is a citation of an older run, not a claim about
    this one: `a stale "18/18 claims" survived two releases` is the honest record of a defect.
    A bare count in a docstring is the tool describing itself."""
    before, after = line[:start], line[end:]
    return any(before.rstrip().endswith(q) or after.lstrip().startswith(q) for q in QUOTED)


def tool_docstring_counts(rel, docstring, noun, truth):
    """(line_no, span, found) for every self-description in `docstring` that `truth` contradicts."""
    out = []
    for line_no, line in enumerate(docstring.splitlines(), 1):
        if _is_dated(line):
            continue
        for pattern in COUNT_PATTERNS:
            for m in pattern.finditer(line):
                span = m.group(0).strip()
                if noun not in span.lower():
                    continue
                if _is_citation(line, m.start(), m.end()):
                    continue
                raw = m.group(m.lastindex)
                found = WORD_NUMBERS.get(raw.lower(), None)
                found = int(raw) if found is None else found
                if found != truth:
                    out.append((line_no, span, found))
    return out


def check_tool_docstring_counts(_files):
    """No audit tool's own docstring states a size the tool contradicts.

    `check_counts_current` reads markdown, because that is where a judge reads a number. It is
    also why `check_docs.py` announced "Six checks" while running seven for a release, and
    `check_submission_text.py` announced "Eight checks" while running seven: the docstring is
    the first thing anyone reads about a tool and the only text about it that nothing checked.
    """
    import ast
    totals = _tool_totals()
    if totals is None:
        return ["could not read a size out of the counting tools"]
    bad = []
    for rel, (noun, owner) in TOOL_COUNTS.items():
        path = ROOT / rel
        if not path.exists():
            continue
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8")))
        if not doc:
            bad.append(f"{rel} has no module docstring, so it describes itself nowhere")
            continue
        for line_no, span, found in tool_docstring_counts(rel, doc, noun, totals[owner]):
            bad.append(f"{rel} docstring line {line_no} says {span!r}, but it runs "
                       f"{totals[owner]}")
    if not bad:
        print(f"        the three counting tools describe their own size correctly: "
              f"{totals['results']} claims, {totals['docs']} documentation checks, "
              f"{totals['submission_text']} submission-text checks")
    return bad


# The repository names its own version in prose, and the convention is one supervisor log per
# release, so the newest log is the version. Retyping it is what put "the repository is v10" in
# three live documents while `docs/SUPERVISOR_LOG_V11.md` was sitting in the tree.
VERSION_PHRASE = re.compile(r"\b(?:repository|repo) is v(\d+)\b")
VERSION_DOCS = LIVE_DOCS + ("README.md", "docs/VIDEO_ADDENDUM.md")


def newest_release():
    """The highest N in docs/SUPERVISOR_LOG_V<N>.md, which is this repository's version."""
    found = []
    for path in (ROOT / "docs").glob("SUPERVISOR_LOG_V*.md"):
        m = re.search(r"SUPERVISOR_LOG_V(\d+)\.md$", path.name)
        if m:
            found.append(int(m.group(1)))
    return max(found) if found else None


def stale_version_statements(text, truth):
    """((line_no, span, found) list, statements seen) for one document.

    Exposed as a function so `tests/test_all.py::TestDocAudit` can feed it the exact sentence
    that defeated the first draft - "the video was recorded against v2. The repository is v10" -
    rather than trusting that the file walk below would have caught it.
    """
    stale, seen = [], 0
    for line_no, line in enumerate(text.splitlines(), 1):
        for m in VERSION_PHRASE.finditer(line):
            # Not `_is_dated`. The first draft of this check used it, and every instance of the
            # defect was exempt on the first run: the sentence dates itself with the version of
            # something else, the video. Third generation of this repository's own hot take, a
            # guard tested only against the example that motivated it. The phrase is present
            # tense by construction ("is v10"); a record writes "was v10" and never matches.
            # Only a quoted citation is exempt.
            if _is_citation(line, m.start(), m.end()):
                continue
            seen += 1
            if int(m.group(1)) != truth:
                stale.append((line_no, m.group(0), int(m.group(1))))
    return stale, seen


def check_declared_version_current(_files):
    """No live document tells a judge the repository is an older release than it is.

    The worst instance was the video notice - the paragraph whose only job is to say which
    artefact is newer than which - which said v10 in three documents at v11. A judge reading
    it has been told, in writing, that the correction table they are about to trust is one
    release behind, by the only sentence that could have told them otherwise.
    """
    truth = newest_release()
    if truth is None:
        return ["no docs/SUPERVISOR_LOG_V<N>.md, so the repository states its version nowhere"]
    bad, seen = [], 0
    for rel in VERSION_DOCS:
        path = ROOT / rel
        if not path.exists():
            continue
        stale, counted = stale_version_statements(
            path.read_text(encoding="utf-8", errors="replace"), truth)
        seen += counted
        for line_no, span, _found in stale:
            bad.append(f"{rel}:{line_no} says {span!r}, but the newest release in "
                       f"docs/ is v{truth}")
    if not bad:
        print(f"        every live document that names a version says v{truth}, "
              f"matching docs/SUPERVISOR_LOG_V{truth}.md ({seen} statements)")
    return bad


CHECKS = [
    ("no mis-decoded characters in authored text", check_no_mojibake),
    ("every path-shaped file reference resolves", check_references_resolve),
    ("exactly one judge entry point at the root", check_single_entry_point),
    ("paste-ready description exists and fits the form", check_paste_ready_description),
    ("no stale count for a claim ledger or an audit", check_counts_current),
    ("no stale test count in a current-state document", check_test_counts_current),
    ("no heading trapped in a language-tagged code fence", check_no_trapped_headings),
    ("no counting tool misstates its own size in its docstring", check_tool_docstring_counts),
    ("no live document declares an older release than the newest one", check_declared_version_current),
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
