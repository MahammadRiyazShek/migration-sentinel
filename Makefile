.PHONY: help cases review baseline eval invariance holdout test site artifact serve verify docs form determinism clean

help:
	@echo "make cases     regenerate the 12 evaluation cases"
	@echo "make review    run the pipeline on the hard case and print the packet"
	@echo "make baseline  run the one-prompt baseline on the same case"
	@echo "make eval      full comparison + ablations (about 1 second, \$$0)"
	@echo "make invariance 12 cases x 4 models x guard on/off, hostile narrators"
	@echo "make holdout   9 held-out cases on the second schema, three arms"
	@echo "make test      stdlib tests"
	@echo "make verify    eval + assert every claim the README and the docs make"
	@echo "make docs      audit the documentation only (references, glyphs, stale counts)"
	@echo "make form      audit the submission form description against results/*.json"
	@echo "make determinism  rerun every generator in a temp copy and diff it back"
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

# v10: verify used to skip the tests and the held-out run, so a red suite and a failing
# submission-text audit could both sit outside the one command the docs tell you to run.
# v11: and it skipped the determinism proof, so "a rerun changes only the clock" was a sentence
# in a document rather than an exit code in the one command the docs tell you to run.
verify: eval invariance holdout
	python3 -m unittest discover -s tests
	python3 tools/check_results.py
	python3 tools/check_docs.py
	python3 tools/check_submission_text.py
	python3 tools/check_determinism.py

docs:
	python3 tools/check_docs.py

form:
	python3 tools/check_submission_text.py

determinism:
	python3 tools/check_determinism.py

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
