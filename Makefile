PY ?= python
SCRIPT := skills/human-voice/scripts/humanity_check.py

.PHONY: help test demo demo-en compare compare-en json blockers genres

help:
	@echo "make test        run the unit tests"
	@echo "make demo        check the Chinese before/after fixtures"
	@echo "make demo-en     same, in English"
	@echo "make compare     delta table: zh-before -> zh-after"
	@echo "make compare-en  delta table: en-before -> en-after"
	@echo "make json        machine-readable output for the Chinese fixture"
	@echo "make blockers    fail if the AI-style fixture has any major finding"
	@echo "make genres      list the threshold profiles"

test:
	$(PY) -m unittest discover -s tests -v

demo:
	$(PY) $(SCRIPT) examples/zh-before.md examples/zh-after.md

demo-en:
	$(PY) $(SCRIPT) examples/en-before.md examples/en-after.md

compare:
	$(PY) $(SCRIPT) examples/zh-after.md --compare examples/zh-before.md

compare-en:
	$(PY) $(SCRIPT) examples/en-after.md --compare examples/en-before.md

json:
	$(PY) $(SCRIPT) examples/zh-before.md --json

blockers:
	$(PY) $(SCRIPT) examples/zh-before.md --fail-on major

genres:
	$(PY) $(SCRIPT) --list-genres
