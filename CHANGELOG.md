# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
