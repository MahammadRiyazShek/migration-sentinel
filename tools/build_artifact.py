"""Fold the review desk into one self-contained HTML file.

    python3 tools/build_artifact.py        ->  site/standalone.html

Same page, same renderer, bundle inlined and trimmed. It carries every recorded run,
so it works from a file:// URL, over email, or as a submission attachment. It cannot
do live runs: those need site/py/ served next to the page.
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
TRUNC = 180


def slim(bundle: dict) -> dict:
    out = json.loads(json.dumps(bundle))
    for c in out["cases"]:
        c.pop("seed", None)
        c.pop("markdown", None)
        c.get("baselines", {}).pop("prompt_only", None)
        for ev in c["trajectory"]:
            for k in ("args", "result", "inputs", "output"):
                if k in ev and isinstance(ev[k], str) and len(ev[k]) > TRUNC:
                    ev[k] = ev[k][:TRUNC] + "\n… truncated in the single-file copy"
    return out


def main() -> int:
    html = (SITE / "index.html").read_text()
    bundle = slim(json.loads((SITE / "data" / "bundle.json").read_text()))
    inline = ("<script>window.__STANDALONE__=true;window.__BUNDLE__="
              + json.dumps(bundle, separators=(",", ":")) + ";</script>")
    marker = "<script>\n/* ------------------------------------------------------------------ *"
    assert marker in html, "index.html changed shape: cannot find the first script block"
    html = html.replace(marker, inline + "\n" + marker, 1)
    html = html.replace("<title>Migration Sentinel — review desk</title>",
                        "<title>Migration Sentinel — review desk (single file)</title>")
    out = SITE / "standalone.html"
    out.write_text(html)
    print(f"site/standalone.html      {out.stat().st_size / 1024:,.0f} KB "
          f"({len(bundle['cases'])} recorded cases, no live engine)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
