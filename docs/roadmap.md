# Development plan — v1.1

Written after reading four comparable projects. The point of this file is to record *why* each change exists, so the next contributor does not re-litigate it.

## What the neighbours are doing

| Project | Form | What works | What we should not copy |
|---|---|---|---|
| [`lynote-ai/humanize-text`](https://github.com/lynote-ai/humanize-text) · 3.5k★ | CLI + n8n + Docker, LLM rewrite + translation chain | Transparent pipeline; every step is readable code. README openly scopes claims as "relative gains". 5 fully traced examples anyone can rerun. | The translation chain destroys citations and technical terms, and it requires API keys. It also optimises the score directly, which is the thing we refuse to do. |
| [`lynote-ai/ai-text-detector`](https://github.com/lynote-ai/ai-text-detector) · 652★ | CLI + Python API + **agent skill** | Output carries `signals`, `caveats`, `next_steps`. Short-text guardrail refuses to score weak evidence. A "Not For" list is printed, not buried. | Their score is still a 0–100 number. We keep refusing to emit one. |
| [`lynote-ai/best-humanizer-handbook`](https://github.com/lynote-ai/best-humanizer-handbook) · 367★ | Handbook | Genre-specific guidance beats one universal checklist. | Marketing framing. |
| Commercial humanizers (Undetectable, StealthWriter, HIX) | Web app | Instant feedback loop, per-sentence highlighting. | Everything else. Paywalled, opaque, and their claims do not survive a benchmark. |

## The gap this version closes

Our v1.0 was a well-argued document with a script attached. The script was the weak half:

1. **Chinese-only output.** An English user gets a Chinese report. The `description` advertises English triggers, so this is a broken promise, not a missing nicety.
2. **No before/after comparison.** The documented workflow is "run it twice and compare", but the tool prints two independent reports and leaves the diff to the reader. That is the single most-used operation in the skill and it had no support.
3. **No location.** "Digit spaces: 3 hits" without telling you *which line* means the agent has to re-scan the document. Mechanical fixes should be point-and-fix.
4. **No genre awareness.** `SKILL.md` has a genre table; the script ignores it. So it flags "no colloquial markers" in an academic paper — exactly the false positive the skill warns about.
5. **No exit code.** Cannot be used in CI or a pre-commit hook.
6. **Six-flag cap by insertion order, not severity.** A hard mechanical tell (digit spacing) can be pushed off the list by six soft stylistic ones.
7. **No tests.** Every threshold change was verified by eyeballing one sample.

## Design decisions

**Stay a single file.** `scripts/humanity_check.py` must remain copy-pasteable into any host. No package, no dependencies, no install step. Tests import it by path. This is why there is no `pyproject.toml`.

**No score, still.** `humanize-text` and `ai-text-detector` both ship a number. We do not, because the number is not reproducible across segmentation and length, and a skill that promises "62% → 12%" is lying in a way users cannot check. Findings + severity + evidence is more useful and more honest.

**Severity, not count.** `blocker` = mechanically provable artifact (digit spacing, watermark residue). `major` = a structural signal a detector will weigh. `minor` = polish. Only blockers should ever block a commit.

**Genre is a parameter, not a paragraph.** Thresholds move per genre; exemptions (enumeration in a report, connectives in a paper) are encoded as profile fields rather than prose the model has to remember.

**Comparison is the primary verb.** `--compare baseline.md draft.md` returns a delta table. This is what makes iteration possible.

## Shipped in v1.1

- `--ui-lang zh|en` — report language, independent of text language.
- `--genre general|academic|essay|copy|novel|report` — threshold profiles + exemption switches.
- `--compare BASE` — per-metric delta with direction, plus a one-line verdict.
- Line-anchored evidence for every mechanical finding (`L12: …`).
- Severity model + `--fail-on blocker|major` exit codes for CI.
- English tells promoted from a word list to actual findings: tricolon, em-dash density, "not just X, but Y", `delve/tapestry` cluster.
- `--json` now emits a versioned envelope (`schema_version`, `generator`) so consumers can pin.
- `--md` for a report you can paste into a PR or a chat.
- stdin via `-`.

## Fixed in v1.1

| Bug | Effect |
|---|---|
| `像` matched inside 图像 / 像素 / 成像 / 肖像 | simile density inflated on any tech text |
| Single `\n` treated as a sentence break | hard-wrapped prose reported ~2× the sentence count, CV collapsed |
| English reliability measured in characters | 300 chars ≈ 50 words was reported as "medium confidence" |
| `--text ""` silently produced an empty run | argparse truthiness bug |
| Flag list truncated before ranking | blockers dropped |
| Non-UTF-8 Windows console | `UnicodeEncodeError` on `═` and `≤` |
| File read error surfaced as a traceback | now a one-line message + exit 1 |
| English `first_person` counted `we` case-sensitively only | "We" missed |

## Not doing

- **A detector.** Different product, different failure modes, and it would make the tool's advice circular.
- **Auto-rewrite.** The skill's core discipline is that the model must not "rewrite to sound human" in one pass. Shipping a button that does exactly that would delete the thesis.
- **A hosted API.** No server, no keys, no telemetry. The skill runs where the text already is.
- **A numeric score.** See above.

## Next, if anyone asks

- `--diff` word-level highlighting of what changed between two drafts.
- A `--profile` file to store per-user thresholds and their own "偏科" word list.
- Golden-file tests against a small labelled corpus, to calibrate thresholds instead of guessing them.
