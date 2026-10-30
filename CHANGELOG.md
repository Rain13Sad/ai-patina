# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] — 2026-10-30

The script catches up with the document. v1.0 argued well and measured poorly:
the checker was Chinese-only, could not compare two drafts, could not say which
line was wrong, and ignored the genre table the skill spends a page on.

### Added

- `--genre` with six threshold profiles (`general`, `academic`, `essay`, `copy`,
  `novel`, `report`) and per-genre exemptions — enumeration in a report, zero
  colloquialism in a paper. `--list-genres` prints the table.
- `--compare BASE` — a delta table with direction and a one-line verdict. This
  is now the primary verb of S5; two independent reports were never a
  comparison.
- `--ui-lang zh|en` — report language independent of text language. An English
  draft now gets an English report by default.
- Severity model (`blocker` / `major` / `minor`) with ranking. Findings are
  sorted by severity instead of insertion order, so a mechanical tell can no
  longer be pushed off the list by six soft stylistic ones.
- Line-anchored evidence for every mechanical finding (`L12: …`).
- `--fail-on blocker|major` and exit code `2`, for CI and pre-commit.
- `--md`, `--max-flags`, `--list-genres`, `--version`, and stdin via `-`.
- English tells promoted from a word list to actual findings: tricolon
  stacking, em-dash density, "not just X, but Y", and the
  `delve/tapestry/robust` cluster. Plus `genuinely/quietly/truly` as a
  *pseudo-human* tell — the shortcut has become its own fingerprint.
- `findings[].moves` maps every finding to the rewrite move that fixes it
  (M1–M14), so an agent can act without re-reading the skill.
- Versioned JSON envelope (`schema_version`, `generator`).
- `references/cli.md`, `docs/cli.md`, `docs/roadmap.md`, `examples/` fixtures
  in both languages, `tests/` (42 cases), `Makefile`, GitHub Actions CI.

### Changed

- Comparison skips metrics whose sample is too small to be stable, and treats
  sub-epsilon deltas as flat. A 0.006 drop in hapax ratio is noise; calling it
  "worse" would manufacture a conclusion.
- Reliability is measured in words for English, not characters. 300 characters
  is 50 words, not "medium confidence".
- Text under 60 characters (30 English words) now keeps mechanical findings and
  drops statistical ones, instead of going silent or reporting noise.
- `general` genre now expects at least one colloquial trace, matching v1.0
  behaviour; `academic` and `report` do not.

### Fixed

- `像` matched inside 图像 / 像素 / 成像 / 肖像, inflating simile density on any
  technical text.
- A single newline was treated as a sentence break, so hard-wrapped prose
  reported roughly twice the sentence count and a collapsed CV.
- `--text ""` silently produced an empty run (argparse truthiness).
- File read errors surfaced as a traceback; now a one-line message and exit 1.
- Non-UTF-8 Windows consoles raised `UnicodeEncodeError` on `═` and `≤`.
- English `first_person` counted `we` case-sensitively only.
- `and` / `the` topped the "repeated word" finding because English stopwords
  were never filtered.
- JSON output mutated the caller's result dict while localising the note.

## [1.0.0] — 2026-10-22

Initial release.

### Added

- `human-voice` skill (`SKILL.md`) — five-dimension audit, six-stage workflow,
  genre-density table, three-part self-check, and hard boundaries stated in the
  skill body rather than only in the README.
- `references/rewrite-moves.md` — 14 rewrite moves in three groups (structure,
  syntax, diction), each with a counterexample, a corrected version, and caveats.
- `references/en-writing-guide.md` — the same method rebuilt for English, with
  English-specific tells (tricolon, em dash density, "It's not just X, it's Y",
  `delve`/`tapestry`/`robust` vocabulary) and English thresholds.
- `references/traces-checklist.md` — the mechanical sweep, with a Chinese
  six-tell table and an exemption list for genres where numbered points and
  formal connectives are *required*.
- `references/voice-profile.md` — six-dimension voice extraction and eight
  persona archetypes for writing from scratch.
- `references/detector-model.md` — the four-layer detection stack, why scores
  are not reproducible, and a practical "how far to go" standard.
- `references/before-after.md` — three full case studies (commentary, personal
  essay, academic abstract).
- `scripts/humanity_check.py` — bilingual heuristic self-check (sentence-length
  CV, short-sentence ratio, paragraph CV, hapax ratio, repeated n-grams, digit
  spacing, inflated vocabulary, connector dependency). Standard library only.
  Deliberately reports metrics, not an "AI rate."
- `docs/ai-text-detection-landscape.md` — background research on how AI-text
  detection works and where it fails.
