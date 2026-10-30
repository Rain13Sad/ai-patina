# ai-patina

**English** · [简体中文](README.zh-CN.md)

[![CI](https://github.com/Rain13Sad/ai-patina/actions/workflows/ci.yml/badge.svg)](https://github.com/Rain13Sad/ai-patina/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](docs/cli.md)

> An agent skill that gives machine-written text a human voice — and lowers its AI-detection rate as a side effect.

*Patina* is what a thing acquires by being handled. That is the whole idea: text with patina has passed through someone's hands — their specifics, their opinions, the things they chose to leave out.

---

## What this is

A skill for AI agents (WorkBuddy, Claude-style skill hosts, or any agent that can read a `SKILL.md`) that rewrites AI-generated text so it reads like a person wrote it.

It works from one premise: **detectors do not read meaning, they measure predictability.** So the fix is not "swap the words for fancier ones." It is *leave the path the model would most likely take* — and humans are already off that path, because humans have specific experience, real opinions, and things they decided not to say.

## What this is not

Read this before installing.

| Not doing | Why |
|---|---|
| Removing watermarks, metadata, or invisible characters | Explicitly prohibited by China's *AI-Generated Content Labeling Measures* and GB 45438-2025; equivalent obligations under EU AI Act Art. 50 |
| Forging document structure, revision history, or writing-process evidence | Cannot be manufactured after the fact — and it is the one layer no rewrite can touch |
| Writing papers, homework, or peer reviews for submission as someone's own work | Out of scope |
| Promising a score | "96% AI" means *this text carries strong AI features*, not *96% was written by AI*. Scores shift with segmentation, length, and context. They are not reproducible |

**What it does do:** improve the writing, calibrate a voice, restore personal expression that got flattened, and prepare material for a false-positive appeal.

If someone asks "get my AI rate under 15% so I can submit," the skill's first move is to explain that the number is a probability classification, not evidence — Turnitin claims <1% document-level false positives while independent testing has found up to 50% on some samples; OpenAI's own classifier hit 26% accuracy and was retired. Then it offers the two honest paths: improve the text, and keep your drafts.

---

## The idea in four lines

1. A model is most predictable exactly where a human is least likely to go: uniform sentence length, evenly distributed vocabulary, complete coverage, frictionless argument, a conclusion that always elevates.
2. Therefore the leverage is structural, not lexical. Synonym swapping moves the surface; a supervised classifier reads the whole fingerprint.
3. **Never ask a model to "make this sound human."** The output is still a sample from the model distribution. Documented case: 62% AI → asked to humanize → 94%.
4. What actually works is a rewrite you do while writing: change the skeleton, cut a third, add the counterexample, put a specific person in it.

---

## Install

```bash
git clone https://github.com/Rain13Sad/ai-patina.git
cp -r ai-patina/skills/human-voice ~/.workbuddy-ai/skills/    # WorkBuddy
# cp -r ai-patina/skills/human-voice ~/.claude/skills/        # Claude-style hosts
```

For a single project, drop it in `.workbuddy-ai/skills/` or `.claude/skills/` instead.

No dependencies. The checker script is Python 3 standard library only, and stays that way — CI fails if a third-party import appears.

## Use

Just ask. The skill triggers on phrases like:

- 去 AI 味 / 写得像人 / 降低 AI 率 / 加人味 / 别这么机械
- "remove the AI smell" / "make this sound human" / "humanize this" / "rewrite so it doesn't read like ChatGPT"

Or run the checker directly:

```bash
python skills/human-voice/scripts/humanity_check.py draft.md --genre essay
python skills/human-voice/scripts/humanity_check.py draft.md --compare draft.before.md
python skills/human-voice/scripts/humanity_check.py draft.md --json --md
cat draft.md | python skills/human-voice/scripts/humanity_check.py -
```

Output on a typical AI paragraph (`--genre essay`):

```
═══ examples/zh-before.md  (353 字符, zh, 评论) ═══

[可信度]  中 —— 可看出趋势，但阈值判断会抖
[句长波动]  8 sentences  mean 39.1  sd 14.9  CV 0.38  range 18-67
            short(<=10 字) 0.0%   long(>=45 字) 25.0%   adjacent jump 22.4
[段落]  4  mean 78.2  CV 0.16  62-96
[格式痕迹]  digit-space 0  enum 2  grandiose 2  connectors 50.0%

── 待办（按严重度）──
1. [主要] 缺少短句：极短句仅占 0.0%，目标 ≥12.0%。整篇没有喘气的地方。
      -> M7
2. [主要] 段落等长：段落长度 CV=0.16，目标 ≥0.4。长短段交替，允许某段只有一句话。
      -> M1, M3
3. [主要] 主题升华：空转大词 2 个：['凝聚', '行稳致远']。删掉拔高，让结论停在具体层面。
      L7: 总而言之，远程办公是时代发展的必然趋势。唯有积极拥抱变革……
      -> M2
```

Every finding carries the move that fixes it (`M1`–`M14`), so the agent does not have to re-read the skill to act.

Then measure the rewrite against the draft, instead of eyeballing two reports:

```
═══ 对比：examples/zh-before.md → examples/zh-after.md ═══

                            before     after     delta
句长 CV                       0.38      0.53     +0.15  改善
短句占比 %                     0.0      15.4     +15.4  改善
段落 CV                       0.16      0.54     +0.38  改善
段首连接词 %                  50.0       0.0     -50.0  改善
空转大词                         2         0        -2  改善
枚举标记                         2         0        -2  改善

共 11 项指标：6 改善 / 0 退步 / 5 持平。
方向正确：结构信号在往人的一侧走。
```

The script is bilingual: an English draft gets an English report, a Chinese draft a Chinese one, and `--ui-lang` overrides either. It **deliberately does not output an "AI rate."** A single number would be false precision — the real one moves when you change your paragraph breaks.

Full flag reference and the JSON contract: [`docs/cli.md`](docs/cli.md).

## How it works

| Stage | Do |
|---|---|
| **S0** | Fix genre, reader, and how much "person" belongs in it. Getting this wrong makes everything downstream wrong |
| **S1** | Diagnose: run the checker with the right `--genre`, do the five-dimension audit, and check facts — invented citations cannot be rewritten away |
| **S2** | Rewrite the structure (70% of the work). Skeleton first; if the skeleton stays, no amount of word-swapping helps |
| **S3** | Rhythm surgery at sentence level. The goal is not fancier sentences, it is text that breathes |
| **S4** | Mechanical trace sweep. No judgment needed, but skipping one item wastes the rest |
| **S5** | Verify: `--compare` against the draft, read aloud, read backwards |

**Order matters.** S4 comes after S2/S3, and nothing gets "polished" afterwards — that flattens the surgery.

## The 14 moves

| # | Move | Fixes |
|---|---|---|
| A1 | Replace the skeleton | definition → background → significance openings |
| A2 | Delete the uplift | forced elevation in the final paragraph |
| A3 | Cut 30% | comprehensive coverage standing in for a position |
| A4 | Add the counterexample | self-confirming argument |
| A5 | Replace the enumeration | first/second/third with no real relationship |
| A6 | Inject an irreplaceable detail | "many organizations", "significantly improved" |
| B7 | Long-short surgery | uniform sentence length |
| B8 | Break the tricolon | three-way parallelism, three metaphors in a row |
| B9 | Interjections and self-correction | frictionless flow |
| B10 | Change the vantage point | synonym swapping that leaves the fingerprint intact |
| B11 | Drop the connector scaffold | *Furthermore / Moreover* paragraph openers |
| C12 | Cultivate a personal bias | evenly distributed vocabulary |
| C13 | Lower adjective density | "very important", "significantly" |
| C14 | Sharpen the term | abstraction stacking |

Full text with before/after examples: [`rewrite-moves.md`](skills/human-voice/references/rewrite-moves.md) (Chinese) · [`en-writing-guide.md`](skills/human-voice/references/en-writing-guide.md) (English).

## Repo layout

```
ai-patina/
├── README.md · README.zh-CN.md
├── CHANGELOG.md · LICENSE · Makefile
├── .github/workflows/ci.yml          # tests, JSON contract, stdlib-only check
├── docs/
│   ├── cli.md                        # flags, exit codes, JSON schema
│   ├── roadmap.md                    # why v1.1 looks like this
│   └── ai-text-detection-landscape.md
├── examples/                         # before/after fixtures, zh + en
├── tests/test_humanity_check.py      # 42 tests, stdlib unittest
└── skills/human-voice/
    ├── SKILL.md                      # the skill: boundaries, audit, workflow
    ├── references/
    │   ├── cli.md                    # the four commands that cover the workflow
    │   ├── rewrite-moves.md          # 14 moves, Chinese examples
    │   ├── en-writing-guide.md       # same method, English examples + English tells
    │   ├── traces-checklist.md       # S4 sweep + exemptions for formal genres
    │   ├── voice-profile.md          # six-dimension voice extraction, 8 archetypes
    │   ├── detector-model.md         # how detection works, how far to go
    │   └── before-after.md           # three full rewrite case studies
    └── scripts/humanity_check.py     # self-check, stdlib only, no score
```

## Development

```bash
make test        # python -m unittest discover -s tests -v
make compare     # delta table on the Chinese fixtures
make compare-en  # same, English
make blockers    # exits 2 — the CI contract
```

Thresholds live in one place: the `GENRES` table at the top of `humanity_check.py`. Changing a number there changes the finding, the comparison row, and the tests together.

Where the design came from, and what was deliberately left out: [`docs/roadmap.md`](docs/roadmap.md).

## Design principles

- **Craft, not evasion.** Lowering the detection rate is what happens when the text gets better, not the other way round.
- **No scores.** The checker reports interpretable metrics; it refuses to produce a number that pretends to be a measurement.
- **Human voice is genre-dependent.** In academic prose it means a sharp, falsifiable claim — not slang. Turning a paper into a newsletter is a different kind of failure. There is a genre table, and an exemption list for formal writing where numbered points and "in summary" are *required*, not tells.
- **The script has no opinions about facts.** Fabricated citations are the strongest AI signal and no rewrite survives them, so fact-checking is a separate, non-negotiable step.
- **Boundaries are in the skill, not just the README.** The agent reads them at runtime.

## Background

Built from a survey of how AI-text detection actually works — statistical features, zero-shot probability methods, supervised classifiers, watermarking, metadata labeling — and from what the evidence says about which countermeasures hold up. Short version: rewriting beats synonym-swapping; structure beats wording; and process evidence is the one layer nothing can fake.

See [`docs/ai-text-detection-landscape.md`](docs/ai-text-detection-landscape.md).

> Detectors are a screening tool, a compass — not a verdict. That holds for both sides: a score should not ground a disciplinary finding, and passing a detector does not mean the work is sound.

## License

MIT — see [LICENSE](LICENSE).
