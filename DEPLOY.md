# Deploying the review desk

`site/` is a static folder: one HTML file, one JSON bundle, and a copy of the Python
package that the page mounts into WebAssembly at runtime. There is no server, no build
step you are forced to run, and no environment variable to set. Any static host works.

Everything in `site/` is generated. Regenerate it after any change:

```bash
python3 eval/run_eval.py --ablations   # refresh results/ and trajectories/
python3 tools/check_results.py         # the numbers still hold
make site                              # -> site/data/bundle.json, site/py/, site/standalone.html
python3 -m http.server 8000 --directory site
```

Paths inside the page are relative, so it works from a subdirectory
(`https://you.github.io/migration-sentinel/`) as well as from a domain root.

---

## Option A: GitHub Pages via Actions (recommended)

The workflow in `.github/workflows/pages.yml` runs the tests, rebuilds the 12 cases,
re-runs both baselines and the pipeline, asserts every claim the README makes, packs the
site and publishes it. A regression fails the job and nothing gets published.

```bash
# from the repository root, first time only
git init -b main
git add .
git commit -m "Migration Sentinel: agentic migration review + review desk"

# with the GitHub CLI (gh auth login first)
gh repo create migration-sentinel --public --source=. --remote=origin --push

# or by hand
git remote add origin https://github.com/OWNER/migration-sentinel.git
git push -u origin main
```

Then, once:

1. GitHub → your repository → **Settings → Pages**
2. **Build and deployment → Source: GitHub Actions**
3. Push anything (or **Actions → verify and deploy → Run workflow**)

The URL appears in the workflow summary and under Settings → Pages, in the form
`https://OWNER.github.io/migration-sentinel/`. First run takes about a minute, nearly all
of it Actions setup: the evaluation itself is under a second.

With the CLI, the same thing without opening the browser:

```bash
gh api -X POST repos/OWNER/migration-sentinel/pages -f build_type=workflow
gh workflow run "verify and deploy"
gh run watch
```

## Option B: GitHub Pages from a branch, no Actions

Useful if Actions are disabled in your org. Publishes the `site/` folder as the root of a
`gh-pages` branch:

```bash
make site
git add -f site && git commit -m "build site"
git subtree push --prefix site origin gh-pages
```

Then Settings → Pages → Source: **Deploy from a branch** → `gh-pages` / `/ (root)`.

`site/.nojekyll` is committed on purpose: without it Jekyll drops
`py/sentinel/agents/prompts/_shared.md`, and the live engine fails to mount.

## Option C: Vercel

`vercel.json` pins the output directory, so the import needs no clicking:

```bash
npm i -g vercel
vercel            # preview deployment, accept the detected settings
vercel --prod
```

Or in the dashboard: **Add New → Project → import the repository → Deploy**. Framework
preset **Other**; `vercel.json` already sets `outputDirectory: site` and rebuilds the
bundle with `python3` from the build image. If your project has Python unavailable at
build time, clear the `buildCommand` in `vercel.json`: `site/data` and `site/py` are
committed, so the folder deploys as-is.

Netlify, Cloudflare Pages and S3 behave the same way: publish directory `site`, no build
command required.

---

## What to expect on the deployed page

* The docket and all 12 recorded review packets render immediately, from
  `data/bundle.json`.
* **Boot the engine in this browser** downloads Pyodide 0.26.4 from jsDelivr (about 12 MB,
  browser-cached), mounts the ~38 files listed in `py/manifest.json` into its virtual
  filesystem and imports `sentinel` from there.
* **Run this case live** executes the same `sentinel.orchestrator.review` call the CLI
  makes, in the tab. The page then diffs the live packet against the recorded one and
  prints whether the verdict, the hazard set with severities, the phase-1 SQL and the
  verification result all match.
* Editing the SQL and running it produces a real review of your migration. There is no
  ground truth for it, so the page says so instead of scoring it.
* No network call carries your SQL anywhere: the runtime is in the tab, and the only
  requests are for the Pyodide assets and this site's own files.

## Troubleshooting

| symptom | cause | fix |
|---|---|---|
| "Could not load data/bundle.json" | opened as `file://`, so `fetch` is blocked | serve the folder, or open `site/standalone.html`, which inlines everything |
| 404 on `py/manifest.json` | `make site` was never run, or `site/py` is gitignored | `make site`, commit `site/` |
| engine says "unavailable" | jsDelivr blocked by a network policy or CSP | the recorded runs still work; for offline hosting, vendor the Pyodide files and point `PYODIDE` in `index.html` at them |
| live run differs from the recorded packet | the pipeline changed after the results were regenerated | `python3 eval/run_eval.py --ablations && make site` |
| Pages published an empty page | Pages source still set to a branch without `.nojekyll` | Option A, or commit `site/.nojekyll` |
