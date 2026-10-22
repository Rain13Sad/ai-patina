# English Writing Guide

Same method as `rewrite-moves.md`, rebuilt for English. **Do not apply the Chinese checklist here** — none of the six Chinese tells (digit spacing, four-character parallelism, forced elevation) transfer. English has its own fingerprint.

---

## Why any of this works

Detectors do not read meaning. They measure **predictability** — how much the text looks like the token sequence a model would most likely produce. The places where a model is most predictable are the places a human is least likely to go: uniform sentence length, evenly distributed vocabulary, frictionless argument, a conclusion that always elevates.

So the work is not "swap words." It is **leaving the most likely path.** Humans are already off it, because humans have specific experience, opinions, and things they chose to leave out.

> **Never ask a model to "make this sound human."** The output is still a sample from the model distribution: surface randomness up, deep habits (intro-body-three-points-conclusion, balanced diction, final uplift) intact. Measured case: 62% AI → asked to humanize → 94%.

---

## The five-dimension audit

| Dimension | Ask | Symptom when missing | Move |
|---|---|---|---|
| **Stance** | What does the author actually think? | "On one hand… on the other… a balance must be struck" | M1 |
| **Specificity** | Is there a detail you can't swap out? | "many organizations", "significantly improved" | M2 |
| **Rhythm** | Does sentence length vary? | every sentence 20–30 words, every paragraph equal | M3 |
| **Omission** | What was cut? | covers everything, nothing can be deleted | M4 |
| **Friction** | Any counterexample, cost, uncertainty? | frictionless, unarguable | M5 |

If all five are empty, do not line-edit. Rewrite.

---

## A. Structural moves (highest leverage — 70% of the work)

### M1 Replace the skeleton

**Symptom**: definition → background → significance → thesis. Three paragraphs of runway before anything happens. This is the most predictable opening a model can produce.

**Move**: open on the most counterintuitive claim, or on one concrete encounter. Delete the definition; move the background to a footnote.

> **Before**: In today's fast-paced business environment, team collaboration efficiency has become a core element of corporate competitiveness. This article explores three paths to improving it.
>
> **After**: Last year we swapped the door badges of two ten-person teams for a week. By day seven, each team's weekly report had started mentioning the other's product.

### M2 Delete the uplift

**Symptom**: the last sentence always reaches for something larger. "navigate uncertainty", "write a new chapter", "a testament to what is possible."

**Move**: cut everything after the last concrete claim. If that feels unfinished, the argument was unfinished — go back and build it, don't fill the hole with elevation.

> **Before**: The key to remote work is not tools, it is trust. Only with trust as a foundation can organizations navigate uncertainty and write a new chapter of their own.
>
> **After**: The key to remote work is not tools, it is trust. And trust is not something you can patch in with a policy.

### M3 Cut 30%

**Symptom**: covering everything, each point shallow. "Comprehensive" is the polite word for "no position."

**Move**: fix one claim. Delete every paragraph that does not directly support it. Say one thing well instead of three things thinly.

**Test**: if you can delete a paragraph and nothing is lost, it was never load-bearing.

### M4 Add the counterexample

**Symptom**: every claim arrives with a supporting example and no counter-evidence. The text is generating support for a position, not thinking about whether the position holds.

**Move**: state the strongest opposing case **in terms its holder would accept**, then respond. Concede what is true.

> **Before**: Remote work improves efficiency because it eliminates commuting, letting employees spend that time on work.
>
> **After**: Remote work does eliminate commuting. But the two hours it frees don't necessarily go to work — in our own data, remote-day commits cluster after 10 p.m. We saved the commute and moved the working hours.

### M5 Replace the enumeration

**Symptom**: "first… second… third…" Coordination implies the points are unrelated, which is almost never true.

**Move**: find the real relationship — cause, cost, sequence, condition, mutual dependence — and write that instead.

> **Before**: Remote work has three benefits: first, lower costs; second, greater flexibility; third, stronger team cohesion.
>
> **After**: Costs did drop. The flexibility was a side effect of that, not the goal. As for cohesion — that's what got sacrificed, and nobody wanted to raise it in the quarterly review.

### M6 Inject an irreplaceable detail

**Symptom**: "many organizations", "significantly improved", "a range of challenges." Swapping these changes nothing, because they carry nothing.

**Move**: replace with one observed particular. **Irreplaceable** means: swap it out and the sentence collapses.

> **Before**: Many organizations face the loss of core technical talent.
>
> **After**: Three backend engineers left last year, all around their fourteenth month. HR says that's a coincidence.

**Warning**: the detail must be true. Fabricated specifics hit *factual consistency* checking — invented citations and invented numbers are the strongest AI signal there is, and no amount of rewriting rescues them. When you have no data, write "I don't have numbers, but my impression is…" — admitting you lack data is itself a human marker.

---

## B. Sentence-level moves (this is what "breathing" means)

### M7 Long-short surgery

**Move**: every 3–4 sentences, drop a sentence of eight words or fewer. Break a long sentence rather than joining it. Fragments are allowed. A one-sentence paragraph is allowed.

> **Before**: The proposal encountered resistance from multiple departments during implementation, concentrated in resource allocation and performance metrics, so progress fell short of expectations.
>
> **After**: The proposal didn't move. Two departments pushed back: one over headcount, one over metrics. Nobody wants to pay for someone else's KPI.

### M8 Break the tricolon

**Symptom**: three parallel clauses, three parallel metaphors. English AI output runs on threes.

**Move**: keep one, cut two, or let the third break form. **A human writes one bad metaphor.**

> **Before**: The neon signs were like colored ribbons, the streetlamps like sentries at their posts, the headlights like a flowing river of stars.
>
> **After**: The neon turned the whole street pink. The streetlamps stayed on, like they hadn't gotten the memo.

### M9 Interjections and self-correction

**Move**: use dashes, parentheses, "or rather", "more precisely" to show a mind changing direction mid-sentence. Models don't revise themselves; people do.

> **After**: I've been quoting that number for three years — two and a half, actually. I first saw it in a December 2023 retro deck.

**Warning**: dashes are now an AI tell in their own right. Above three per thousand words, they stop helping.

### M10 Change the vantage point, not the synonym

**Symptom**: synonym substitution only moves the surface. A supervised classifier reads the whole statistical fingerprint; swap every word and the fingerprint is unchanged. This is the mechanism behind "edited all night, 15% → 19%."

**Move**: same event, different position — beneficiary, casualty, bystander, operator, dissenter.

> **Before (synonym swap)**: Remote work improved employee flexibility → Telework enhanced workforce elasticity.
>
> **After (vantage)**: For anyone with a toddler, remote isn't a perk. It's the difference between working and quitting.

### M11 Drop the connector scaffold

**Symptom**: every paragraph opens with *Furthermore / Moreover / Additionally / However / Consequently*. Logic is being outsourced to connectives.

**Move**: delete the opener; let content carry the transition. If it no longer reads, the two paragraphs were never related — merge or cut.

---

## C. Diction (finishing work, not the main effort)

### M12 Cultivate a personal bias

Stylometry research puts **"even use of non-repeated words"** at the top of the human/machine discriminators. People have vocabulary tics: a few words reused constantly, everything else chosen carelessly. Models distribute evenly because they were trained to avoid repetition.

**Move**: pick 3–5 private words for this piece and use them consistently. Don't rotate synonyms for one concept.

> **Before**: the text cycles through *efficiency, effectiveness, performance, output* for one idea.
>
> **After**: the text uses *efficiency* seven times.

**Not a contradiction**: one concept, one word (human) ≠ one sentence, one word four times (machine). Narrow vocabulary is human; impoverished phrasing is not.

### M13 Lower adjective density

**Move**: adjective → action or number. "significantly improved" → "from 62% to 71%". "very important" → "nothing works without it."

**Test**: delete every adjective. If meaning survives, they were decoration.

### M14 Sharpen the term

**Move**: abstraction → the specific thing.

| Inflated | Replace with |
|---|---|
| leverage synergies | two teams stop building the same thing twice |
| drive alignment | everyone agrees on the same number by Friday |
| holistic approach | we looked at all four steps, not one |
| robust solution | it didn't break when we doubled the load |
| unlock value | someone can now do this without asking us |

Abstractions live where the model is safest — highest predictability. One step toward the concrete drops it.

---

## English-specific tells (checklist)

**Vocabulary** — these are near-deterministic markers:
`delve, tapestry, landscape, realm, navigate, leverage, robust, seamless, holistic, paradigm, underscore, pivotal, intricate, multifaceted, nuanced, testament, foster, showcase, boast, myriad, embark, journey`

**Structures**
- [ ] "It's not just X, it's Y" — now the single most recognizable AI cadence. Use once, never twice
- [ ] Tricolons everywhere (three adjectives, three clauses, three examples)
- [ ] "Not only… but also…"
- [ ] "In today's fast-paced world" / "In an era of…" / "As we navigate…"
- [ ] "Let's dive in" / "Let's explore" / "Here's the thing:"
- [ ] Paragraph-initial *Furthermore / Moreover / Additionally / Consequently / Ultimately*
- [ ] Every paragraph 3–5 sentences, all similar length
- [ ] Bold lead-in on every bullet (`**Speed:** we…`)
- [ ] Em dash density above 3 per 1,000 words
- [ ] "genuinely / actually / quietly" used as faux-human intensifiers — the arms race has moved here; these now read as machine

**Format**
- [ ] Bulleted lists where prose belongs (three or more consecutive lists is a warning)
- [ ] Emoji as section markers
- [ ] Title Case Headings On Every Level

---

## Thresholds (same script, English mode)

| Metric | Pass | Weak | Suspicious |
|---|---|---|---|
| Sentence length CV | ≥0.45 | 0.35–0.45 | <0.35 |
| Short sentences (≤8 words) | ≥15% | 8–15% | <8% |
| Paragraph length CV | ≥0.42 | 0.30–0.42 | <0.30 |
| hapax ratio | ≥0.70 | 0.55–0.70 | <0.55 |
| English AI vocabulary hits | 0–1 | 2–3 | ≥4 |

Below 300 words nothing is reliable — including real detectors (OpenAI's requires ≥1,000 characters, Turnitin ≥300 words).

---

## The three self-checks

**1. Read it aloud.** Any sentence needing two breaths: break it. Any sentence that makes you wince because it's trying too hard: delete it.

**2. Read it backwards**, last paragraph first. Ask of each sentence: *does this exist only to carry the previous one?* Model sentences mostly do. Human sentences are often sudden arrivals.

**3. Two deletions.**
- Delete the first paragraph. If the piece still works, it was runway. People rarely build runway.
- Replace every proper noun and number with a fake. If nothing breaks, there was no information there.

---

## What "done" looks like

Not a score. Four conditions:

1. All six script metrics pass.
2. Reading backwards, no sentence exists only to carry the previous one.
3. Delete any paragraph and something is missing.
4. Replace the proper nouns and numbers and the text loses its footing.

When all four hold, you have reached the limit of what text-level work can do. What remains is process evidence — which no rewrite can manufacture, and which is why the honest answer is to keep your drafts, not to keep editing.
