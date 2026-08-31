.PHONY: help cases review baseline eval invariance test site artifact serve verify clean

help:
	@echo "make cases     regenerate the 12 evaluation cases"
	@echo "make review    run the pipeline on the hard case and print the packet"
	@echo "make baseline  run the one-prompt baseline on the same case"
	@echo "make eval      full comparison + ablations (about 1 second, \$$0)"
	@echo "make invariance 12 cases x 4 models x guard on/off, hostile narrators"
	@echo "make test      stdlib tests"
	@echo "make verify    eval + assert every claim the README makes"
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

verify: eval invariance
	python3 tools/check_results.py

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
