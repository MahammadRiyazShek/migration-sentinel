#!/usr/bin/env python3
"""Prove that a rerun changes wall-clock numbers and nothing else.

`tools/check_results.py` re-asserts every published figure from raw JSON, and one of its claims
is that every recorded packet in `results/` matches a fresh reference run. It compares decisions,
which is the right comparison and is also why it says nothing about the 80 files a rerun rewrites.

That is a real problem for a judge, and it is the eleventh supervisor session's finding:

    $ python3 eval/run_eval.py --ablations && git status --short results/ | wc -l
    80

Eighty modified files, in a submission whose whole pitch is that its numbers are re-derivable.
Every one of those diffs is a wall-clock `ms` field - the shadow replay took 2.85 milliseconds
this time and 3.49 the last time - and no decision, hazard, severity, verdict, coverage gap,
generated statement or metric moves at all. But "trust me, it is only the timings" is exactly the
sentence this project exists to refuse, so it gets a command and an exit code.

What it does:

  1. copies the repository into a temporary directory, so the committed tree is never written to;
  2. reruns the evaluation, the ablations, the held-out set, the invariance sweep and the
     component report there;
  3. compares every regenerated file against the committed one twice - raw, then with wall-clock
     fields normalised;
  4. prints the exact set of field names that moved, and fails if anything outside that set did.

Standard library only, no network, no model. A few seconds, almost all of it the copy.

    python3 tools/check_determinism.py
    python3 tools/check_determinism.py --verbose   # name every file that moved, and how
"""

from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Everything that regenerates something under results/.
REGENERATORS = [
    ["eval/run_eval.py", "--ablations"],
    ["eval/run_holdout.py", "--ablations"],
    ["eval/model_invariance.py"],
    ["eval/report_components.py"],
]

# Wall-clock, and only wall-clock. Each pattern names the field it is allowed to blur, so the
# permission list reads as a list rather than as a catch-all for "numbers that annoy me".
WALL_CLOCK = [
    ('json field "ms"', re.compile(r'("(?:ms|wall_ms|wall_ms_per_case|elapsed_ms|duration_ms)"\s*:\s*)[0-9.]+')),
    ('json field "generated_at"', re.compile(r'("generated_at"\s*:\s*")[^"]*(")')),
    ('markdown "N ms"', re.compile(r"\b\d+(?:\.\d+)?(?= ms\b)")),
    ('markdown "N s"', re.compile(r"\b\d+(?:\.\d+)?(?= s\b)")),
    ("iso timestamp", re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?"
                                 r"(?:Z|[+-]\d{2}:?\d{2})?")),
    # A published comparison table carries one measured-wall-clock row per arm. It is labelled
    # "(ms, measured)" in the document precisely so a reader knows it is not a decision.
    ('markdown "Wall clock per case" row',
     re.compile(r"^(\|\s*Wall clock per case[^|]*\|)(.*)$", re.M)),
]


def normalise(text):
    """Blur wall-clock fields, and report which ones were present."""
    touched = []
    for label, pattern in WALL_CLOCK:
        if pattern.search(text):
            touched.append(label)
        if label == 'json field "generated_at"':
            text = pattern.sub(r"\1<wall-clock>\2", text)
        elif label.startswith("json field"):
            text = pattern.sub(r"\1<wall-clock>", text)
        elif label.startswith('markdown "Wall clock per case"'):
            text = pattern.sub(lambda m: m.group(1) + re.sub(r"[0-9.]+", "<wall-clock>",
                                                             m.group(2)), text)
        else:
            text = pattern.sub("<wall-clock>", text)
    return text, touched


def compare(committed, regenerated):
    identical, wall_clock_only, real, missing = [], [], [], []
    for path in sorted(regenerated.rglob("*")):
        if not path.is_file() or path.suffix not in {".json", ".md"}:
            continue
        rel = path.relative_to(regenerated)
        old = committed / rel
        if not old.exists():
            missing.append(str(rel))
            continue
        a = old.read_text(encoding="utf-8", errors="replace")
        b = path.read_text(encoding="utf-8", errors="replace")
        if a == b:
            identical.append(str(rel))
            continue
        na, touched_a = normalise(a)
        nb, touched_b = normalise(b)
        if na == nb:
            wall_clock_only.append((str(rel), sorted(set(touched_a) | set(touched_b))))
        else:
            real.append((str(rel), na, nb))
    return identical, wall_clock_only, real, missing


def main():
    ap = argparse.ArgumentParser("check_determinism")
    ap.add_argument("--verbose", action="store_true",
                    help="name every file that moved and which wall-clock fields it carried")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / "rerun"
        shutil.copytree(ROOT, work,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "site"))
        for cmd in REGENERATORS:
            done = subprocess.run([sys.executable, *cmd], cwd=work,
                                  capture_output=True, text=True)
            if done.returncode != 0:
                print(f"FAIL  {' '.join(cmd)} exited {done.returncode} on a clean copy")
                print((done.stderr or done.stdout)[-1500:])
                return 1
            print(f"ran   {' '.join(cmd)}")
        identical, wall_only, real, missing = compare(ROOT / "results", work / "results")

    fields = sorted({f for _, fs in wall_only for f in fs})
    print()
    print(f"      {len(identical)} files byte-identical on a rerun")
    print(f"      {len(wall_only)} files differ, in wall-clock fields only")
    print(f"      wall-clock fields that moved: {', '.join(fields) or 'none'}")
    if args.verbose:
        for rel, fs in wall_only:
            print(f"        {rel}: {', '.join(fs)}")
    print()

    if missing:
        print("FAIL  a rerun produced files absent from the committed results/")
        for rel in missing[:10]:
            print(f"        {rel}")
        return 1
    if real:
        print(f"FAIL  {len(real)} file(s) differ beyond wall-clock: a decision is not deterministic")
        for rel, na, nb in real[:5]:
            print(f"        {rel}")
            for line_a, line_b in zip(na.splitlines(), nb.splitlines()):
                if line_a != line_b:
                    print(f"          committed: {line_a.strip()[:100]}")
                    print(f"          rerun    : {line_b.strip()[:100]}")
                    break
        return 1

    print("PASS  every decision byte in results/ survives a rerun; only wall-clock fields move")
    print(f"      {len(identical) + len(wall_only)} files compared, {len(real)} decision differences")
    return 0


if __name__ == "__main__":
    sys.exit(main())
