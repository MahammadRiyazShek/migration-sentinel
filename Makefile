.PHONY: help cases review baseline eval invariance holdout redteam redteam2 redteam3 test site artifact serve verify docs form determinism crossversion clean

help:
	@echo "make cases     regenerate the 12 evaluation cases"
	@echo "make review    run the pipeline on the hard case and print the packet"
	@echo "make baseline  run the one-prompt baseline on the same case"
	@echo "make eval      full comparison + ablations (about 1 second, \$$0)"
	@echo "make invariance 12 cases x 4 models x guard on/off, hostile narrators"
	@echo "make holdout   9 held-out cases on the second schema, three arms"
	@echo "make redteam   7 cases written to make this pipeline approve an outage"
	@echo "make redteam2  6 cases the parser itself gets wrong (v14)"
	@echo "make redteam3  3 probes aimed at the SQL this pipeline writes itself (v16)"
	@echo "make test      stdlib tests"
	@echo "make verify    eval + assert every claim the README and the docs make"
	@echo "make docs      audit the documentation only (references, glyphs, stale counts)"
	@echo "make form      audit the submission form description against results/*.json"
	@echo "make determinism  rerun every generator in a temp copy and diff it back"
	@echo "make crossversion rerun it again on a second interpreter and diff the two trees"
	@echo "make site      regenerate site/data + site/py from the results"
	@echo "make serve     build the site and serve it at http://localhost:8000"

CASE ?= eval/cases/case_12_release_train.json

cases:
	python3 eval/build_cases.py

review:
	python3 -m sentinel review --case $(CASE) --print-report

baseline:
	python3 baseline/baseline_review.py --case $(CASE) --variant prompt_with_schema --print-review

eval:
	python3 eval/run_eval.py --ablations

invariance:
	python3 eval/model_invariance.py --write

test:
	python3 -m unittest discover -s tests -v

holdout:
	python3 eval/run_holdout.py --ablations

redteam:
	python3 eval/run_redteam.py

redteam2:
	python3 eval/run_redteam2.py

redteam3:
	python3 eval/run_redteam3.py

# v10: verify used to skip the tests and the held-out run, so a red suite and a failing
# submission-text audit could both sit outside the one command the docs tell you to run.
# v11: and it skipped the determinism proof, so "a rerun changes only the clock" was a sentence
# in a document rather than an exit code in the one command the docs tell you to run.
# v12: and the determinism proof reruns everything under one interpreter, so "3.11 and 3.12
# verified" was a claim about exceptions rather than about numbers until check_cross_version ran
# here too. It SKIPs with a printed reason on a machine with a single Python, rather than passing.
# v13: and it skipped the red-team set entirely, so the two holes an adversarial pass found
# were closed in the code and unproven by the one command the docs tell you to run.
# v14: and the round-2 set is here for the same reason. `redteam2` also recomputes what the
# retired splitter did to each file, so "the parse is a sample of the text" is an exit code
# rather than a paragraph.
# v16: and it skipped the round-3 set, so the audit of this pipeline's own output was
# green in a document rather than in the one command the docs tell you to run.
verify: eval invariance holdout redteam redteam2 redteam3
	python3 -m unittest discover -s tests
	python3 tools/check_results.py
	python3 tools/check_docs.py
	python3 tools/check_submission_text.py
	python3 tools/check_determinism.py
	python3 tools/check_cross_version.py

docs:
	python3 tools/check_docs.py

form:
	python3 tools/check_submission_text.py

determinism:
	python3 tools/check_determinism.py

crossversion:
	python3 tools/check_cross_version.py

site:
	python3 tools/build_site.py
	python3 tools/build_artifact.py

artifact:
	python3 tools/build_artifact.py

serve: site
	@echo "http://localhost:8000"
	python3 -m http.server 8000 --directory site

clean:
	rm -rf results trajectories site/data site/py site/standalone.html memory/learned.jsonl __pycache__ */__pycache__ */*/__pycache__
