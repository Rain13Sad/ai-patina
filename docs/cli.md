# CLI reference

`skills/human-voice/scripts/humanity_check.py` — one file, standard library only, no network.

```bash
python humanity_check.py draft.md
python humanity_check.py draft.md --genre essay --ui-lang en
python humanity_check.py examples/zh-after.md --compare examples/zh-before.md
cat draft.md | python humanity_check.py - --json
```

Requires Python 3.9+. Nothing to install; copy the file and run it.

## Flags

| Flag | Default | What it does |
|---|---|---|
| `FILES...` | — | `.md` / `.txt` files. `-` reads stdin. |
| `--text "..."` | — | Inline text instead of a file. `--text ""` is a valid, empty input. |
| `--genre` | `general` | Threshold profile. See the table below. |
| `--lang` | `auto` | Force the analysis language (`zh` / `en`). |
| `--ui-lang` | text language | Force the report language. An English draft gets an English report by default. |
| `--compare BASE` | — | Print a before/after delta table against `BASE`. |
| `--json` | off | Versioned JSON envelope. |
| `--md` | off | Markdown report, for pasting into a PR or a chat. |
| `--max-flags N` | 8 | Findings per file. `findings_total` in JSON still reports the real count. |
| `--fail-on` | `none` | `blocker` / `major` → exit 2 when a finding reaches that severity. |
| `--list-genres` | — | Print the threshold table and exit. |
| `--version` | — | Print the version and exit. |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Ran fine. Findings may still exist — this is not a verdict. |
| `1` | Usage or I/O error (unreadable file, no input). |
| `2` | A finding reached the `--fail-on` severity. |

The default is `0` even when findings exist. Turning a heuristic into a build failure should be a deliberate choice, not a surprise.

```yaml
# .github/workflows/text.yml
- run: python skills/human-voice/scripts/humanity_check.py docs/*.md --fail-on blocker
```

Only `blocker` is safe in CI. Blockers are mechanical (digit spacing), so they are facts about the file, not opinions about the prose.

## Genres

```bash
$ python humanity_check.py --list-genres
genre         CV  short%  paraCV  enum ok  connector%
general     0.45     8.0    0.42    False          30
academic     0.4     6.0    0.35     True          45
essay       0.45    12.0     0.4    False          25
copy        0.45    15.0    0.42    False          25
novel        0.5    20.0    0.45    False          15
report      0.42     8.0    0.36     True          45
```

- **CV / short% / paraCV** are targets, not pass-fail lines. Below target is a finding; far below is a major one.
- **enum ok** — `True` suppresses the "mechanical enumeration" finding. A report with numbered sections is following its format; an essay with the same is following a model.
- **connector%** — share of paragraphs allowed to open with 此外 / 然而 / Furthermore. Papers legitimately need these; a personal essay does not.

## Severity

| Level | Meaning | Example |
|---|---|---|
| `blocker` | Mechanically provable artifact, independent of style. | Digit spacing in Chinese text. |
| `major` | A structural signal a detector actually weighs. | Sentence-length CV below target; English AI vocabulary cluster; tricolon stacking. |
| `minor` | Polish. Worth doing, not worth blocking on. | One word repeated; no questions. |

Findings are sorted by severity, then by the order they were generated. `--max-flags` truncates the display, never the count.

## JSON schema (1.1)

```json
{
  "schema_version": "1.1",
  "generator": { "name": "humanity_check.py", "version": "1.1.0" },
  "results": [
    {
      "label": "draft.md",
      "lang": "zh",
      "genre": "general",
      "chars": 812,
      "words": 0,
      "reliability": { "level": "medium", "unit_count": 742, "note": "..." },
      "metrics": {
        "sentence":   { "count": 21, "mean": 35.3, "sd": 12.1, "cv": 0.34, "min": 8, "max": 61,
                        "short_ratio_pct": 9.5, "long_ratio_pct": 28.6,
                        "short_max": 10, "long_min": 45, "mean_adjacent_jump": 14.2 },
        "paragraph":  { "count": 5, "mean": 148.2, "cv": 0.21, "min": 96, "max": 210 },
        "vocabulary": { "tokens": 388, "types": 341, "ttr": 0.879, "content_types": 302,
                        "hapax_ratio": 0.742, "top_repeated": [["远程", 7]] },
        "repetition": { "top_ngrams": [["远程·办公·已", 3]] },
        "format":     { "digit_space": { "count": 2, "examples": ["L12: ..."] },
                        "enum_total": 4, "enum_kinds": { "...": {} },
                        "connector_ratio_pct": 40.0, "connector_hits": ["此外"] },
        "rhetoric":   { "simile_count": 1, "simile_per_1k": 1.2, "tricolon": 0,
                        "not_just_x": 0, "emdash_per_1k": 0.0 },
        "lexical":    { "grandiose": { "hits": ["赋能"], "count": 1 },
                        "en_tells": { "hits": [], "count": 0 },
                        "en_pseudo": { "hits": [], "count": 0 } },
        "human":      { "colloquial_count": 0, "colloquial_hits": [], "tail_particle": 0,
                        "hedge_count": 1, "hedge_hits": ["可能"], "first_person": 0,
                        "questions": 0, "dash": 2, "paren": 3, "numbers": 4,
                        "digit_density_pct": 1.2 }
      },
      "findings": [
        { "id": "format.digit_space", "severity": "blocker", "moves": [],
          "title": "数字两侧有空格", "detail": "...", "evidence": ["L12: ..."] }
      ],
      "findings_total": 7,
      "summary": { "blockers": 1, "majors": 3, "minors": 3, "total": 7 }
    }
  ]
}
```

`--compare` adds:

```json
"comparison": {
  "base": "before.md",
  "rows": [
    { "metric": "sentence.cv", "base": 0.34, "target": 0.52, "delta": 0.18,
      "direction": "up", "verdict": "better", "label": "after.md" }
  ]
}
```

`findings[].moves` points at the rewrite moves in `references/rewrite-moves.md` (`M1`–`M14`), so an agent can go from "this is wrong" to "do this" without re-reading the whole skill.

## What the numbers are not

They are not a detection score, and the script will never print one. It reports six surface families — sentence rhythm, paragraph rhythm, vocabulary spread, repetition, mechanical traces, human markers — each of which is independently explainable. A detector segments the text and classifies; its number moves when you change the paragraph breaks. These do not.
