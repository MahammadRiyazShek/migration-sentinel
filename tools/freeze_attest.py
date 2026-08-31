#!/usr/bin/env python3
"""Attest which decision code was frozen before the held-out cases were written.

WHY THIS EXISTS
---------------
A held-out claim is worth exactly as much as the evidence that the code did not
move after the labels were written. "I did not tune the rules on these cases" is
the least verifiable sentence in any evaluation report, and every earlier audit in
this repository refused to accept that shape of sentence from a model, so it should
not accept it from me either.

So the decision code is hashed before the held-out world exists, and the hash list
is committed:

    python3 tools/freeze_attest.py --freeze   # write the manifest (done once, v5 code)
    python3 tools/freeze_attest.py            # verify: what changed since the freeze?

`results/holdout/decision_code_manifest.json` carries a SHA-256 per file under
`sentinel/` - the only tree that can create, name, weight or suppress a finding.
`eval/`, `tools/`, `tests/` and `docs/` are deliberately outside the freeze: they
score and describe, they do not decide.

The verifier prints one of three states, and `eval/run_holdout.py` prints it at the
top of every held-out report so no reader has to take it on trust:

    CLEAN        no decision file changed since the freeze
    POST-FREEZE  decision files changed, listed by name - so the held-out numbers
                 are labelled as an after-the-fix run, and the frozen first-contact
                 run stays in results/holdout/frozen_run.json
    MISSING      no manifest, so no held-out claim can be made at all
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "results" / "holdout" / "decision_code_manifest.json"

# The tree that decides. Everything that can produce, name, weight or suppress a
# finding lives here; nothing that only scores or reports does.
DECISION_TREE = "sentinel"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot() -> dict[str, str]:
    out = {}
    for path in sorted((ROOT / DECISION_TREE).rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        out[path.relative_to(ROOT).as_posix()] = digest(path)
    return out


def freeze(note: str) -> int:
    files = snapshot()
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({
        "frozen_tree": DECISION_TREE,
        "note": note,
        "files": len(files),
        "sha256": files,
    }, indent=1) + "\n")
    print(f"froze {len(files)} decision files under {DECISION_TREE}/ -> "
          f"{MANIFEST.relative_to(ROOT)}")
    return 0


def verify() -> dict[str, object]:
    if not MANIFEST.exists():
        return {"state": "MISSING", "changed": [], "added": [], "removed": [],
                "note": "", "frozen_files": 0}
    man = json.loads(MANIFEST.read_text())
    frozen: dict[str, str] = man["sha256"]
    now = snapshot()
    changed = sorted(k for k in frozen if k in now and now[k] != frozen[k])
    added = sorted(k for k in now if k not in frozen)
    removed = sorted(k for k in frozen if k not in now)
    state = "CLEAN" if not (changed or added or removed) else "POST-FREEZE"
    return {"state": state, "changed": changed, "added": added, "removed": removed,
            "note": man.get("note", ""), "frozen_files": len(frozen)}


def render(v: dict[str, object]) -> str:
    lines = [f"decision-code freeze: {v['state']} ({v['frozen_files']} files hashed under "
             f"{DECISION_TREE}/)"]
    if v["note"]:
        lines.append(f"  frozen at: {v['note']}")
    for label in ("changed", "added", "removed"):
        for name in v[label]:  # type: ignore[index]
            lines.append(f"  {label}: {name}")
    if v["state"] == "POST-FREEZE":
        lines.append("  -> the held-out numbers below are an AFTER-THE-FIX run. The frozen "
                     "first-contact run is kept in results/holdout/frozen_run.json.")
    elif v["state"] == "CLEAN":
        lines.append("  -> no rule, threshold or gap class moved after the held-out labels "
                     "were written.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser("freeze_attest")
    ap.add_argument("--freeze", action="store_true",
                    help="write the manifest from the current tree")
    ap.add_argument("--note", default="v5 decision code, hashed before the held-out schema, "
                                      "cases or labels existed")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.freeze:
        return freeze(args.note)
    v = verify()
    print(json.dumps(v, indent=1) if args.json else render(v))
    return 0 if v["state"] != "MISSING" else 1


if __name__ == "__main__":
    sys.exit(main())
