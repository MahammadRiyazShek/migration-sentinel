"""Run the browser's driver under CPython and diff it against the recorded packets.

    python3 tools/test_browser_driver.py

The review desk executes a short Python driver inside Pyodide (the `DRIVER` string in
site/index.html). This script extracts that exact string, points its `/app` paths at
site/py/ (the copy the browser mounts) and runs all 12 cases through it, comparing verdict,
hazard codes with severities, phase-1 SQL and the verification result against results/.

It cannot prove the WebAssembly build behaves identically. It does prove the driver, the
mounted file set and the recorded packets agree, which is where drift actually happens.
The page repeats the same comparison at runtime for whatever it just ran.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_driver() -> str:
    html = (ROOT / "site" / "index.html").read_text()
    m = re.search(r"const DRIVER = `(.*?)`;", html, re.S)
    if not m:
        raise SystemExit("could not find the DRIVER string in site/index.html")
    app = str((ROOT / "site" / "py").resolve())
    if not (ROOT / "site" / "py" / "manifest.json").exists():
        raise SystemExit("site/py is missing: run python3 tools/build_site.py first")
    return (m.group(1)
            .replace('"/app"', json.dumps(app))
            .replace('"/app/memory/incidents.jsonl"', json.dumps(app + "/memory/incidents.jsonl")))


def main() -> int:
    ns: dict = {}
    exec(compile(load_driver(), "<review desk driver>", "exec"), ns)
    run = ns["run_case_json"]
    key = lambda hs: sorted(h["code"] + ":" + h["severity"] for h in hs)  # noqa: E731
    failures = 0
    cases = sorted((ROOT / "eval" / "cases").glob("*.json"))
    for path in cases:
        case = json.loads(path.read_text())
        live = json.loads(run(json.dumps({"case": case})))["report"]
        rec = json.loads((ROOT / "results" / f"{case['id']}.json").read_text())
        diffs = []
        if live["verdict"] != rec["verdict"]:
            diffs.append(f"verdict {rec['verdict']} -> {live['verdict']}")
        if key(live["hazards"]) != key(rec["hazards"]):
            diffs.append("hazards " + str(set(key(rec["hazards"])) ^ set(key(live["hazards"]))))
        if live["plan"]["phase1_sql"] != rec["plan"]["phase1_sql"]:
            diffs.append("phase 1 SQL differs")
        if live["plan_verification"]["verified"] != rec["plan_verification"]["verified"]:
            diffs.append("verification differs")
        failures += bool(diffs)
        print(("PARITY" if not diffs else "DIFF  ") + f"  {case['id']}  {live['verdict']}, "
              f"{len(live['hazards'])} hazards" + ("" if not diffs else "  " + "; ".join(diffs)))

    # A migration nobody wrote a ground truth for still has to produce a packet.
    case = json.loads((ROOT / "eval" / "cases" / "case_01_rename_with_compat_view.json").read_text())
    case["migration_sql"] = "ALTER TABLE customers DROP COLUMN plan;"
    case.pop("ground_truth", None)
    out = json.loads(run(json.dumps({"case": case})))
    ad_hoc = out["report"]["verdict"] == "BLOCK" and "score" not in out
    print(("PASS  " if ad_hoc else "FAIL  ") + "  ad-hoc SQL reviewed without ground truth: "
          + out["report"]["verdict"] + f", {len(out['report']['hazards'])} hazards, "
          f"plan verified={out['report']['plan_verification']['verified']}")

    print(f"\n{len(cases) - failures}/{len(cases)} cases reproduce the recorded packet "
          "through the browser driver")
    return 1 if failures or not ad_hoc else 0


if __name__ == "__main__":
    sys.exit(main())
