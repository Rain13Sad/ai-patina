#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
humanity_check.py — 文本"人味"自查器 / a humanity self-check for text

用途：改写前后各跑一次，用可量化的表层指标定位 AI 痕迹，并给出可执行的修改方向。
性质：启发式自查，**不是检测器**。它测的是几个公开可解释的特征（句长波动、
      词汇多样性、n-gram 重复、格式痕迹、套话密度、人味标记），
      不产生"AI 率"这种数字——那个数字随分段、长度、上下文漂移，不可复现。

用法 / usage:
    python humanity_check.py draft.md
    python humanity_check.py draft.md --genre essay --ui-lang en
    python humanity_check.py --compare before.md after.md
    python humanity_check.py draft.md --json
    python humanity_check.py - < draft.md
    cat draft.md | python humanity_check.py -

仅依赖标准库 / standard library only.
"""

import argparse
import json
import math
import re
import sys
import unicodedata
from collections import Counter

__version__ = "1.1.0"
SCHEMA_VERSION = "1.1"

# ================================================================ 词表

# 中文虚词/高频功能词，用于过滤"高频实词"统计
STOP_ZH = set("""
的 了 是 在 和 与 也 就 都 而 及 或 被 把 让 使 对 从 到 为 以 于 之 其 这 那 有 我 你 他 她 它 我们 你们 他们
不 没 很 更 最 会 能 要 可以 一个 一些 这个 那个 这些 那些 上 下 中 里 外 后 前 时 个 们 过 着 地 得 等 但 却
如 若 则 即 又 再 还 已 曾 将 应 该 可 需 须 并 且 因 由 此 所 者 也 呢 吗 吧 啊 嘛 呀
""".split())

# 英文功能词：不滤掉的话，"and 出现 6 次"会占据待办榜首，毫无用处
STOP_EN = set("""
a an the and or but if then than that this these those of in on at to for from with without
by as is are was were be been being it its it's we our you your they their he she his her
i my me not no so such can could may might must should would will do does did have has had
which who whom whose what when where why how there here also just very more most other
""".split())

# 主题升华 / 空转大词：AI 中文最典型的"结尾拔高"标记
GRANDIOSE = """
折射 彰显 凝聚 赋能 闭环 抓手 生态位 底色 注脚 篇章 光芒 光辉 深刻变革 新时代
新篇章 价值坐标 精神内核 生动实践 时代答卷 行稳致远 久久为功 提质增效
深度融合 立体化 系统性重塑 势能 护城河 坐标系 新引擎 强引擎
""".split()

# 分点 / 机械枚举标记（按行匹配，pattern 里不要写 ^）
ENUM_PATTERNS_ZH = [
    (r"第[一二三四五六七八九十]+[、，,．.]", "第一、第二式"),
    (r"^\s*[①②③④⑤⑥⑦⑧⑨⑩]", "圈号列表"),
    (r"^\s*\d+[、.．)）]\s*\S", "阿拉伯数字列表"),
    (r"^\s*[-*+]\s+\S", "无序列表"),
    (r"首先[，,].{0,80}?其次[，,]", "首先/其次"),
    (r"一方面.{0,120}?另一方面", "一方面/另一方面"),
]
ENUM_PATTERNS_EN = [
    (r"^\s*\d+[.)]\s+\S", "numbered list"),
    (r"^\s*[-*+]\s+\S", "bullet list"),
    (r"\bfirst(?:ly)?\b.{0,80}?\bsecond(?:ly)?\b", "first/second"),
    (r"\bon one hand\b.{0,120}?\bon the other hand\b", "on one hand / on the other"),
]

# 段首连接词依赖：AI 极爱用这些开头起段
CONNECT_START_ZH = ("此外 然而 因此 同时 总之 综上 值得注意的是 更重要的是 与此同时 "
                    "另一方面 由此可见 总的来说 总而言之 需要指出的是").split()
CONNECT_START_EN = ["furthermore", "moreover", "additionally", "however", "therefore",
                    "consequently", "in addition", "ultimately", "overall", "notably",
                    "in conclusion", "that said"]

# 口语 / 人味正面标记
COLLOQUIAL_ZH = """
其实 说白了 老实说 说实话 反正 挺 蛮 说不清 我觉得 我猜 结果 后来 也就是说 换句话说
问题是 奇怪的是 意外的是 干脆 顺手 得了吧 谁知道 我印象里 我记得 折腾 靠谱 不像话
而已 干嘛 啥 咋 呗 算了 顶多 无非 压根 说白了就是 话又说回来 谁知道呢
""".split()
COLLOQUIAL_EN = ["kind of", "sort of", "pretty much", "i mean", "turns out", "anyway",
                 "to be fair", "no idea", "a bit", "honestly", "or so", "at best",
                 "which is", "the thing is"]

# 模糊限定语：人写作会留余地，模型倾向于给确定断言
HEDGE_ZH = "大概 可能 估计 差不多 某种意义上 至少 不太 好像 似乎 说不定 很难说 不一定 大体上".split()
HEDGE_EN = ["maybe", "perhaps", "probably", "roughly", "not sure", "i think",
            "sort of", "more or less", "give or take", "i suspect"]

# 英文 AI 高频词
EN_TELLS = """
delve tapestry landscape realm navigate leverage robust seamless holistic paradigm
underscore pivotal intricate multifaceted nuanced testament foster showcase crucial
vital myriad plethora embark myriad
""".split()

# 英文"伪人味"：这些词被当成加人味的快捷方式后，本身已变成新的机器味
EN_PSEUDO = ["genuinely", "quietly", "truly", "remarkably"]

# ================================================================ 正则

RE_ZH = re.compile(r"[\u4e00-\u9fff]")
RE_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
RE_DIGIT_SPACE = re.compile(r"[\u4e00-\u9fff][ \t]+\d[\d.,%]*|\d[\d.,%]*[ \t]+[\u4e00-\u9fff]")

# 中文分号「；」是分句符，不是句末符。按它切会把长句剁碎、把 CV 算低，
# 从而漏掉"句长过于均匀"这个最主要的信号。只按真正的句末符与空行切。
# 单个 \n 也不切：硬折行的文本否则会被算成两倍句数。
RE_SENT_END_ZH = re.compile(r"[。！？!?…]+|\n\s*\n")
RE_SENT_END_EN = re.compile(r"(?<![0-9])[.!?]+(?![0-9])|\n\s*\n")

RE_TAIL_PARTICLE = re.compile(r"[了吧呢啊嘛呗啦哦呀]\s*[。！？!?]?$")
# 比喻的「像」要先排掉构词：图像、像素、成像、肖像……逐字 lookbehind 排不干净
# （像素 的「像」前面是「素」），所以先删词再计数。
SIMILE_EXCLUDE_ZH = ("图像 像素 成像 肖像 雕像 偶像 镜像 影像 想像 画像 塑像 铜像 石像 "
                     "佛像 神像 人像 声像 录像 摄像 好像 像片 像话").split()
RE_SIMILE_ZH = re.compile(r"像|如同|仿佛|好似|宛如")
RE_SIMILE_EN = re.compile(r"\b(like|as if|as though)\b", re.I)
RE_TRICOLON = re.compile(
    r"\b[\w'-]+(?:\s+[\w'-]+){0,2},\s+[\w'-]+(?:\s+[\w'-]+){0,2},\s+(?:and|or)\s+[\w'-]+", re.I)
RE_NOT_JUST = re.compile(r"\bnot\s+(?:just|only|merely)\b[^.!?]{0,80}?\b(?:but|it'?s|it is)\b", re.I)
RE_NOT_X_ITS_Y = re.compile(r"\bit'?s\s+not\s+[^.!?]{0,60}[.!?]\s*it'?s\b", re.I)

# 英文缩写：切句前先保护，避免 e.g. / et al. 把句子切断
ABBREV = ["e.g.", "i.e.", "et al.", "vs.", "Dr.", "Mr.", "Ms.", "Mrs.", "Fig.",
          "No.", "cf.", "approx.", "etc.", "Prof.", "St."]
_PLACEHOLDER = "\x00"


# ================================================================ 体裁阈值

GENRES = {
    "general":  {"zh": "通用", "en": "general",  "cv": 0.45, "short": 8.0,  "pcv": 0.42,
                 "colloquial": 1, "hedge": 1, "enum_ok": False, "connect": 30},
    "academic": {"zh": "学术", "en": "academic", "cv": 0.40, "short": 6.0,  "pcv": 0.35,
                 "colloquial": 0, "hedge": 1, "enum_ok": True,  "connect": 45},
    "essay":    {"zh": "评论", "en": "essay",    "cv": 0.45, "short": 12.0, "pcv": 0.40,
                 "colloquial": 1, "hedge": 1, "enum_ok": False, "connect": 25},
    "copy":     {"zh": "文案", "en": "copy",     "cv": 0.45, "short": 15.0, "pcv": 0.42,
                 "colloquial": 2, "hedge": 1, "enum_ok": False, "connect": 25},
    "novel":    {"zh": "小说", "en": "novel",    "cv": 0.50, "short": 20.0, "pcv": 0.45,
                 "colloquial": 2, "hedge": 2, "enum_ok": False, "connect": 15},
    "report":   {"zh": "报告", "en": "report",   "cv": 0.42, "short": 8.0,  "pcv": 0.36,
                 "colloquial": 0, "hedge": 1, "enum_ok": True,  "connect": 45},
}

SEV_RANK = {"blocker": 0, "major": 1, "minor": 2}

# ================================================================ 输出文案

TXT = {
    "zh": {
        "header": "═══ {label}  ({chars} 字符, {lang}, {genre}) ═══",
        "sentence": "[句长波动]",
        "paragraph": "[段落]",
        "vocabulary": "[词汇]",
        "repetition": "[3-gram]",
        "format": "[格式痕迹]",
        "rhetoric": "[修辞]",
        "human": "[人味标记]",
        "english": "[英文套词]",
        "reliability": "[可信度]",
        "findings": "── 待办（按严重度）──",
        "clean": "── 表层指标全部通过。下一步只能靠人工判断：事实、判断力、有没有人真的想过。──",
        "note": ("注：以上是启发式自查，不是检测器分数。检测器把文本切段判定，"
                 "分数随分段、长度、上下文漂移，不可复现。"),
        "sev_blocker": "阻断",
        "sev_major": "主要",
        "sev_minor": "次要",
        "unit_char": "字",
        "unit_word": "词",
        "more": "（另有 {n} 条次要项，用 --max-flags 展开）",
        "rel": {
            "insufficient": "不适用 —— 有效词数 {n}，任何统计指标（包括真实检测器）都没有意义",
            "low": "低 —— 文本过短，阈值判断会大幅抖动",
            "medium": "中 —— 可看出趋势，但阈值判断会抖",
            "high": "较高 —— 长度已超过主流检测器的最低要求",
        },
        "compare_title": "═══ 对比：{base} → {target} ═══",
        "better": "改善",
        "worse": "退步",
        "same": "持平",
        "compare_sum": "共 {n} 项指标：{good} 改善 / {bad} 退步 / {flat} 持平。",
        "compare_verdict_good": "方向正确：结构信号在往人的一侧走。",
        "compare_verdict_bad": "有指标在反向走。先看退步项，再决定是否继续。",
        "genres": "可用体裁",
        "usage_hint": "用 - 从标准输入读取；没有输入时显示本帮助。",
    },
    "en": {
        "header": "═══ {label}  ({chars} chars, {lang}, {genre}) ═══",
        "sentence": "[sentence length]",
        "paragraph": "[paragraphs]",
        "vocabulary": "[vocabulary]",
        "repetition": "[3-grams]",
        "format": "[format traces]",
        "rhetoric": "[rhetoric]",
        "human": "[human markers]",
        "english": "[English tells]",
        "reliability": "[reliability]",
        "findings": "-- findings, by severity --",
        "clean": ("-- surface metrics all pass. What is left needs a human: facts, judgement, "
                  "whether anyone actually thought about this. --"),
        "note": ("Note: this is a heuristic self-check, not a detector score. Detectors segment "
                 "text before classifying; scores drift with segmentation, length and context."),
        "sev_blocker": "BLOCKER",
        "sev_major": "MAJOR",
        "sev_minor": "MINOR",
        "unit_char": "chars",
        "unit_word": "words",
        "more": "({n} more minor items; raise --max-flags to see them)",
        "rel": {
            "insufficient": "n/a -- {n} content words; no statistic, including a real detector, means anything here",
            "low": "low -- text too short, thresholds will swing wildly",
            "medium": "medium -- trend is visible, thresholds still noisy",
            "high": "high -- length is past what mainstream detectors require",
        },
        "compare_title": "═══ compare: {base} -> {target} ═══",
        "better": "better",
        "worse": "worse",
        "same": "flat",
        "compare_sum": "{n} metrics: {good} better / {bad} worse / {flat} flat.",
        "compare_verdict_good": "Direction is right: the structural signals are moving toward human.",
        "compare_verdict_bad": "Some metrics moved backwards. Read those first before going further.",
        "genres": "genres",
        "usage_hint": "Use - to read stdin; with no input this help is printed.",
    },
}


# ================================================================ 工具

def init_stdio():
    """Windows 控制台默认不是 UTF-8，打印 ═ / ≤ 会抛 UnicodeEncodeError。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            enc = (stream.encoding or "").lower()
            if enc not in ("utf-8", "utf8"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def resolve_lang(text, forced="auto"):
    if forced in ("zh", "en"):
        return forced
    return "zh" if len(RE_ZH.findall(text)) > len(RE_WORD.findall(text)) else "en"


def strip_markup(text):
    """去掉标题行、表格行、引用行与代码块，避免它们污染句长统计。"""
    out = []
    in_code = False
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        s = line.strip()
        if s.startswith("#") or s.startswith("|") or s.startswith(">"):
            continue
        out.append(line)
    return "\n".join(out)


def protect_abbrev(text):
    for a in ABBREV:
        text = text.replace(a, a.replace(".", _PLACEHOLDER))
    return text


def restore_abbrev(text):
    return text.replace(_PLACEHOLDER, ".")


def split_sentences(text, zh=True):
    body = strip_markup(text)
    if zh:
        parts = RE_SENT_END_ZH.split(body)
    else:
        parts = RE_SENT_END_EN.split(protect_abbrev(body))
    out = []
    for p in parts:
        p = p.strip()
        p = re.sub(r"^[#>\-\*\s]+", "", p)      # 去掉 markdown 标记
        # 阈值放到 2：像"是新人。"这种 3 字短句正是人类节奏的核心证据，不能被过滤
        n = len(RE_ZH.findall(p)) if zh else len(RE_WORD.findall(p))
        if n >= 2:
            out.append(p if zh else restore_abbrev(p))
    return out


def split_paragraphs(text, zh=True):
    out = []
    for block in re.split(r"\n\s*\n", text):
        b = block.strip()
        if not b or b.startswith("|") or b.startswith("```"):
            continue
        b = re.sub(r"^[#>\-\*\s]+", "", b)
        n = len(RE_ZH.findall(b)) if zh else len(RE_WORD.findall(b))
        if n >= (10 if zh else 6):
            out.append((b, n))
    return out


def char_bigrams(text):
    """无分词依赖的中文词近似：连续汉字取不重叠二元组。"""
    toks = []
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(run) == 1:
            toks.append(run)
            continue
        for i in range(0, len(run) - 1, 2):
            toks.append(run[i:i + 2])
    toks += [w.lower() for w in RE_WORD.findall(text)]
    return toks


def stats(nums):
    if not nums:
        return {"n": 0, "mean": 0.0, "sd": 0.0, "cv": 0.0, "min": 0, "max": 0}
    n = len(nums)
    m = sum(nums) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in nums) / n) if n > 1 else 0.0
    return {"n": n, "mean": round(m, 1), "sd": round(sd, 1),
            "cv": round(sd / m, 2) if m else 0.0, "min": min(nums), "max": max(nums)}


def locate_regex(pattern, text, limit=3):
    """按行定位，返回 L12: 片段。机械痕迹必须能点到具体行。"""
    out = []
    for i, line in enumerate(text.split("\n"), 1):
        if re.search(pattern, line):
            out.append(f"L{i}: {line.strip()[:70]}")
            if len(out) >= limit:
                break
    return out


def locate_words(words, text, limit=3):
    out = []
    for i, line in enumerate(text.split("\n"), 1):
        hit = [w for w in words if w in line]
        if hit:
            out.append(f"L{i}: {line.strip()[:70]}")
            if len(out) >= limit:
                break
    return out


def F(fid, sev, moves, zh_title, zh_detail, en_title, en_detail, evidence=None):
    return {"id": fid, "severity": sev, "moves": moves,
            "title_zh": zh_title, "detail_zh": zh_detail,
            "title_en": en_title, "detail_en": en_detail,
            "evidence": evidence or []}


# ================================================================ 主分析

def analyze(text, label="<text>", genre="general", lang="auto"):
    if genre not in GENRES:
        genre = "general"
    lang = resolve_lang(text, lang)
    zh = lang == "zh"
    prof = GENRES[genre]

    n_chars = len(text)
    n_words = len(RE_WORD.findall(text))
    unit = len(RE_ZH.findall(text)) if zh else n_words

    r = {"label": label, "lang": lang, "genre": genre,
         "chars": n_chars, "words": n_words or None}

    # 可信度：中文按字数，英文按词数——300 个英文字符只有 50 个词，不能算"中等"
    # insufficient 只在"连句长都算不出来"时才给（<60 字 / <30 词），
    # 否则一段 150 字的文字会拿到一份空报告，那不是谨慎，是没用。
    if zh:
        band = ("insufficient" if unit < 60 else "low" if unit < 300
                else "medium" if unit < 1000 else "high")
    else:
        band = ("insufficient" if unit < 30 else "low" if unit < 100
                else "medium" if unit < 250 else "high")
    r["reliability"] = {"level": band, "unit_count": unit}

    sents = split_sentences(text, zh)
    paras = split_paragraphs(text, zh)
    s_len = [len(RE_ZH.findall(s)) if zh else len(RE_WORD.findall(s)) for s in sents]
    p_len = [n for _, n in paras]

    # --- 1. 句长波动（burstiness）
    ss = stats(s_len)
    SHORT_MAX, LONG_MIN = (10, 45) if zh else (8, 30)
    short_ratio = round(100.0 * sum(1 for x in s_len if x <= SHORT_MAX) / max(1, len(s_len)), 1)
    long_ratio = round(100.0 * sum(1 for x in s_len if x >= LONG_MIN) / max(1, len(s_len)), 1)
    adj = [abs(s_len[i] - s_len[i - 1]) for i in range(1, len(s_len))]
    sentence = {
        "count": ss["n"], "mean": ss["mean"], "sd": ss["sd"], "cv": ss["cv"],
        "min": ss["min"], "max": ss["max"],
        "short_ratio_pct": short_ratio, "long_ratio_pct": long_ratio,
        "short_max": SHORT_MAX, "long_min": LONG_MIN,
        "mean_adjacent_jump": round(sum(adj) / len(adj), 1) if adj else 0.0,
    }

    # --- 2. 段落长度（"段段等长"）
    ps = stats(p_len)
    paragraph = {"count": ps["n"], "mean": ps["mean"], "cv": ps["cv"],
                 "min": ps["min"], "max": ps["max"]}

    # --- 3. 词汇多样性
    toks = char_bigrams(text)
    content = [t for t in toks if t not in STOP_ZH and t not in STOP_EN and len(t) > 1]
    tf = Counter(content)
    hapax = sum(1 for w, c in tf.items() if c == 1)
    vocabulary = {
        "tokens": len(toks), "types": len(set(toks)),
        "ttr": round(len(set(toks)) / max(1, len(toks)), 3),
        "content_types": len(tf),
        "hapax_ratio": round(hapax / max(1, len(tf)), 3),
        "top_repeated": [[w, c] for w, c in tf.most_common(6) if c >= 3],
    }

    # --- 4. n-gram 重复
    grams = Counter()
    for i in range(len(content) - 2):
        grams["·".join(content[i:i + 3])] += 1
    repetition = {"top_ngrams": [[g, c] for g, c in grams.most_common(5) if c >= 3]}

    # --- 5. 格式痕迹（数字空格是中文特有痕迹；英文里数字前后空格是正常排版）
    digit_space = {"count": 0, "examples": []}
    if zh:
        digit_space = {"count": len(RE_DIGIT_SPACE.findall(text)),
                       "examples": locate_regex(RE_DIGIT_SPACE.pattern, text)}
    enums, enum_total = {}, 0
    for pat, name in (ENUM_PATTERNS_ZH if zh else ENUM_PATTERNS_EN):
        cnt = sum(1 for line in text.split("\n") if re.search(pat, line))
        if cnt:
            enums[name] = {"count": cnt, "examples": locate_regex(pat, text)}
            enum_total += cnt
    starts = []
    for p, _ in paras:
        head = p[:4] if zh else p[:24].lower()
        pool = CONNECT_START_ZH if zh else CONNECT_START_EN
        for c in pool:
            if head.startswith(c):
                starts.append(c)
                break
    fmt = {"digit_space": digit_space, "enum_total": enum_total, "enum_kinds": enums,
           "connector_ratio_pct": round(100.0 * len(starts) / max(1, len(paras)), 1),
           "connector_hits": starts}

    # --- 6. 修辞
    if zh:
        _stripped = text
        for _w in SIMILE_EXCLUDE_ZH:
            _stripped = _stripped.replace(_w, "")
        similes = len(RE_SIMILE_ZH.findall(_stripped))
        tricolon, notjust, emdash = 0, 0, len(re.findall(r"——|—", text))
    else:
        similes = len(RE_SIMILE_EN.findall(text))
        tricolon = len(RE_TRICOLON.findall(text))
        notjust = len(RE_NOT_JUST.findall(text)) + len(RE_NOT_X_ITS_Y.findall(text))
        emdash = len(re.findall(r"—|–", text))
    rhetoric = {"simile_count": similes,
                "simile_per_1k": round(1000.0 * similes / max(1, n_chars), 1),
                "tricolon": tricolon, "not_just_x": notjust,
                "emdash_per_1k": round(1000.0 * emdash / max(1, n_chars), 1)}

    # --- 7. 词汇层（套话 / 英文 AI 词）
    if zh:
        g_hits = [w for w in GRANDIOSE if w in text]
        en_hits, pseudo = [], []
    else:
        g_hits = []
        low = text.lower()
        en_hits = [w for w in EN_TELLS if re.search(r"\b" + re.escape(w) + r"\b", low)]
        pseudo = [w for w in EN_PSEUDO if re.search(r"\b" + w + r"\b", low)]
    lexical = {"grandiose": {"hits": g_hits, "count": len(g_hits)},
               "en_tells": {"hits": en_hits, "count": len(en_hits)},
               "en_pseudo": {"hits": pseudo, "count": len(pseudo)}}

    # --- 8. 人味正面标记
    coll = [w for w in (COLLOQUIAL_ZH if zh else COLLOQUIAL_EN)
            if (w in text if zh else w in text.lower())]
    hedges = [w for w in (HEDGE_ZH if zh else HEDGE_EN)
              if (w in text if zh else w in text.lower())]
    tail = sum(1 for s in sents if RE_TAIL_PARTICLE.search(s)) if zh else 0
    if zh:
        first_person = len(re.findall(r"(?<![其])我(?!们)", text)) + len(re.findall(r"我们", text))
    else:
        first_person = len(re.findall(r"\bI\b|\b(?:we|We|my|My|our|Our)\b", text))
    human = {
        "colloquial_count": len(coll), "colloquial_hits": coll[:8],
        "tail_particle": tail,
        "hedge_count": len(hedges), "hedge_hits": hedges[:6],
        "first_person": first_person,
        "questions": len(re.findall(r"[？?]", text)),
        "dash": emdash,
        "paren": len(re.findall(r"[（(]", text)),
        "numbers": len(re.findall(r"\d+(?:\.\d+)?%?", text)),
        "digit_density_pct": round(100.0 * len(re.findall(r"\d", text)) / max(1, n_chars), 1),
    }

    r["metrics"] = {"sentence": sentence, "paragraph": paragraph, "vocabulary": vocabulary,
                    "repetition": repetition, "format": fmt, "rhetoric": rhetoric,
                    "lexical": lexical, "human": human}
    r["findings"] = build_findings(r, prof, zh, text)

    # 文本太短时：句长、词汇、n-gram 统计都是噪声，但"有几个分点"是可数的，
    # 所以保留机械类（blocker + format.*），丢掉统计类。
    if band == "insufficient":
        r["findings"] = [f for f in r["findings"]
                         if f["severity"] == "blocker" or f["id"].startswith("format.")]

    counts = Counter(f["severity"] for f in r["findings"])
    r["summary"] = {"blockers": counts.get("blocker", 0), "majors": counts.get("major", 0),
                    "minors": counts.get("minor", 0), "total": len(r["findings"])}
    return r


def build_findings(r, prof, zh, text):
    """按严重度生成待办。顺序即优先级，同级按插入顺序。"""
    m = r["metrics"]
    s, p, v = m["sentence"], m["paragraph"], m["vocabulary"]
    fmt, rh, lx, h = m["format"], m["rhetoric"], m["lexical"], m["human"]
    f = []

    # ---- blocker：机械痕迹，检测方一抓一个准，与文风无关
    if zh and fmt["digit_space"]["count"] > 0:
        f.append(F("format.digit_space", "blocker", [],
                   "数字两侧有空格",
                   f"命中 {fmt['digit_space']['count']} 处。这是 Markdown 渲染习惯的残留，"
                   f"人手写中文不会这样。逐处删掉，不要用正则全替换（会把英文缩写也吃掉）。",
                   "space around digits",
                   f"{fmt['digit_space']['count']} hit(s). A Markdown-rendering artifact; "
                   f"nobody typing Chinese inserts these. Fix each one by hand.",
                   fmt["digit_space"]["examples"]))

    # ---- major：结构信号，检测器真正在称的东西
    if s["cv"] < prof["cv"] - 0.10:
        f.append(F("sentence.cv", "major", ["M7"],
                   "句长过于均匀",
                   f"CV={s['cv']}，体裁目标 ≥{prof['cv']}。每 3–4 句插一个极短句"
                   f"（{'≤10 字' if zh else '≤8 词'}），或在长句后直接断成两截。",
                   "sentence lengths too uniform",
                   f"CV={s['cv']}, target >= {prof['cv']} for this genre. Drop a very short "
                   f"sentence every 3-4 lines, or cut one long sentence in half.",
                   []))
    elif s["cv"] < prof["cv"]:
        f.append(F("sentence.cv", "minor", ["M7"],
                   "句长略平",
                   f"CV={s['cv']}，体裁目标 ≥{prof['cv']}。还差一点落差。",
                   "sentence lengths slightly flat",
                   f"CV={s['cv']}, target >= {prof['cv']}. Close, but the rhythm is still even.",
                   []))

    if s["count"] >= 6 and s["short_ratio_pct"] < prof["short"] / 2:
        f.append(F("sentence.short", "major", ["M7"],
                   "缺少短句",
                   f"极短句仅占 {s['short_ratio_pct']}%，目标 ≥{prof['short']}%。"
                   f"整篇没有喘气的地方——这是最容易被识别的节奏特征。",
                   "no short sentences",
                   f"Only {s['short_ratio_pct']}% of sentences are very short; target "
                   f">= {prof['short']}%. Nothing breathes.",
                   []))
    elif s["count"] >= 6 and s["short_ratio_pct"] < prof["short"]:
        f.append(F("sentence.short", "minor", ["M7"],
                   "短句偏少",
                   f"极短句占 {s['short_ratio_pct']}%，目标 ≥{prof['short']}%。",
                   "few short sentences",
                   f"{s['short_ratio_pct']}% very short; target >= {prof['short']}%.",
                   []))

    if p["count"] >= 3 and p["cv"] < prof["pcv"] - 0.10:
        f.append(F("paragraph.cv", "major", ["M1", "M3"],
                   "段落等长",
                   f"段落长度 CV={p['cv']}，目标 ≥{prof['pcv']}。长短段交替，"
                   f"允许某段只有一句话。",
                   "paragraphs all the same length",
                   f"Paragraph-length CV={p['cv']}, target >= {prof['pcv']}. Alternate long and "
                   f"short; let one paragraph be a single sentence.",
                   []))
    elif p["count"] >= 3 and p["cv"] < prof["pcv"]:
        f.append(F("paragraph.cv", "minor", ["M3"],
                   "段落长度偏齐",
                   f"段落长度 CV={p['cv']}，目标 ≥{prof['pcv']}。",
                   "paragraph lengths slightly even",
                   f"Paragraph-length CV={p['cv']}, target >= {prof['pcv']}.",
                   []))

    if not zh and lx["en_tells"]["count"] >= 3:
        f.append(F("lexical.en_tells", "major", ["M13", "M14"],
                   "英文 AI 高频词",
                   f"命中 {lx['en_tells']['count']} 个：{lx['en_tells']['hits'][:6]}。"
                   f"这些词本身没错，成串出现才是指纹。换成具体名词或直接删。",
                   "English AI vocabulary cluster",
                   f"{lx['en_tells']['count']} hits: {lx['en_tells']['hits'][:6]}. The words are "
                   f"fine; the cluster is the fingerprint. Swap for something specific.",
                   locate_words(lx["en_tells"]["hits"], text)))

    if not zh and rh["tricolon"] >= 2:
        f.append(F("rhetoric.tricolon", "major", ["M8"],
                   "三项并列",
                   f"{rh['tricolon']} 处 X, Y, and Z 结构。三件套是英文最强的 AI 指纹之一："
                   f"砍成一个，或让最后一项变形（更具体、更短、或直接省略）。",
                   "tricolon stacking",
                   f"{rh['tricolon']} instances of X, Y, and Z. One of the strongest English "
                   f"tells. Keep two items, or make the third one specific.",
                   []))

    if not zh and rh["not_just_x"] >= 2:
        f.append(F("rhetoric.not_just", "major", ["M5", "M2"],
                   "「不只是 X，而是 Y」句式",
                   f"{rh['not_just_x']} 处。这是 2024–2026 年最泛滥的模型句式，"
                   f"检测器已专门建特征。改成一个直接断言。",
                   "'not just X, but Y' construction",
                   f"{rh['not_just_x']} instances. The most overused model cadence of 2024-2026; "
                   f"detectors model it directly. Replace with a plain claim.",
                   []))

    if not prof["enum_ok"] and fmt["enum_total"] >= 3:
        f.append(F("format.enumeration", "major", ["M5"],
                   "机械分点",
                   f"枚举标记 {fmt['enum_total']} 处（{list(fmt['enum_kinds'])}）。"
                   f"这个体裁里分点是模型习惯，不是规范。改成因果、让步、转折串联。",
                   "mechanical enumeration",
                   f"{fmt['enum_total']} markers ({list(fmt['enum_kinds'])}). In this genre a list "
                   f"is a model habit, not a requirement. Chain them with because/but/instead.",
                   [ex for k in fmt["enum_kinds"].values() for ex in k["examples"]][:3]))

    if zh and lx["grandiose"]["count"] >= 2:
        f.append(F("lexical.grandiose", "major", ["M2"],
                   "主题升华",
                   f"空转大词 {lx['grandiose']['count']} 个：{lx['grandiose']['hits'][:5]}。"
                   f"删掉拔高，让结论停在具体层面。",
                   "uplift vocabulary",
                   f"{lx['grandiose']['count']} empty grand words: {lx['grandiose']['hits'][:5]}. "
                   f"Delete the elevation; end on something concrete.",
                   locate_words(lx["grandiose"]["hits"], text)))

    if fmt["connector_ratio_pct"] >= prof["connect"]:
        f.append(F("format.connectors", "major" if fmt["connector_ratio_pct"] >= prof["connect"] + 15
                   else "minor", ["M11"],
                   "段首连接词依赖",
                   f"{fmt['connector_ratio_pct']}% 的段落以 {fmt['connector_hits'][:4]} 开头。"
                   f"删掉它们，靠内容衔接——两段之间本来就有关系，不需要每次都报幕。",
                   "connector-dependent paragraph openings",
                   f"{fmt['connector_ratio_pct']}% of paragraphs open with "
                   f"{fmt['connector_hits'][:4]}. Delete them; the content already connects.",
                   []))

    # ---- minor：打磨项
    if not zh and rh["emdash_per_1k"] > 5:
        f.append(F("rhetoric.emdash", "minor", ["M7", "M8"],
                   "破折号过密",
                   f"{rh['emdash_per_1k']}/千字符。破折号是模型的万能连接件，用多了就成指纹。"
                   f"一半改成句号。",
                   "em-dash density",
                   f"{rh['emdash_per_1k']} per 1k chars. The em dash is the model's universal "
                   f"joint; at this density it is a tell. Turn half of them into full stops.",
                   []))

    if not zh and lx["en_pseudo"]["count"] >= 3:
        f.append(F("lexical.en_pseudo", "minor", ["M12"],
                   "「伪人味」副词",
                   f"{lx['en_pseudo']['hits'][:4]} 被当成加人味的捷径，现在本身已是新的机器味。"
                   f"删掉，靠事实而不是副词表达诚恳。",
                   "manufactured-candour adverbs",
                   f"{lx['en_pseudo']['hits'][:4]} are used as a shortcut to sounding human and "
                   f"have become a tell themselves. Cut them; let facts carry the candour.",
                   []))

    if v["top_repeated"]:
        top = v["top_repeated"][0]
        if top[1] >= 5:
            f.append(F("vocabulary.repeat", "minor", ["M12", "M10"],
                       "同词高频复用",
                       f"「{top[0]}」出现 {top[1]} 次。代词化、省略、换叙述视角。",
                       "one word repeated",
                       f"'{top[0]}' appears {top[1]} times. Pronominalise, elide, change the "
                       f"vantage point.",
                       []))

    if m["repetition"]["top_ngrams"]:
        f.append(F("repetition.ngram", "minor", ["M3"],
                   "三词组重复",
                   f"{m['repetition']['top_ngrams'][:3]}。同一意思只写一遍。",
                   "repeated trigrams",
                   f"{m['repetition']['top_ngrams'][:3]}. Say it once.",
                   []))

    if v["content_types"] >= 40 and v["hapax_ratio"] < 0.55:
        f.append(F("vocabulary.hapax", "minor", ["M12"],
                   "用词过于均衡",
                   f"仅出现一次的词占 {v['hapax_ratio']}，目标 ≥0.70。人写作有偏科："
                   f"几个爱用的词反复用，其余随手取。",
                   "vocabulary too evenly distributed",
                   f"Hapax ratio {v['hapax_ratio']}, target >= 0.70. People are lopsided: a few "
                   f"favourite words recur, everything else is picked at random.",
                   []))

    if rh["simile_per_1k"] >= 4:
        f.append(F("rhetoric.simile", "minor", ["M8", "M13"],
                   "比喻连排",
                   f"比喻密度 {rh['simile_per_1k']}/千字。三个并列砍成一个，或让最后一个变形。",
                   "simile pile-up",
                   f"{rh['simile_per_1k']} per 1k chars. Keep one of three, or deform the last.",
                   []))

    if prof["colloquial"] > 0 and h["colloquial_count"] == 0 and h["tail_particle"] == 0:
        f.append(F("human.colloquial", "minor", ["M9"],
                   "零口语痕迹",
                   "全文没有一个口语词，也没有一句以「了/吧/呢/啊」收尾。"
                   "这个体裁可以少，但一个都没有就是机器味。",
                   "zero colloquial traces",
                   "No colloquial marker, and not one sentence ends on a soft particle. "
                   "This genre needs few, but zero is a machine signature.",
                   []))

    # 阈值按语言换单位：中文看字数，英文看词数。500 个英文字符只有 90 个词，
    # 用同一套数字要求它"必须有一句自问"是不合理的。
    long_500 = r["chars"] > 500 if zh else r["reliability"]["unit_count"] > 100
    long_600 = r["chars"] > 600 if zh else r["reliability"]["unit_count"] > 120

    if prof["hedge"] > 0 and h["hedge_count"] == 0 and long_500:
        f.append(F("human.hedge", "minor", ["M4"],
                   "没有留余地",
                   "全篇零模糊限定（大概/可能/不一定/很难说）。人对自己不确定的东西会承认不确定，"
                   "模型倾向于给出干净利落的断言。",
                   "no hedging at all",
                   "Not one hedge. People admit uncertainty about things they are unsure of; "
                   "models prefer clean assertions.",
                   []))

    if h["questions"] == 0 and long_600:
        f.append(F("human.questions", "minor", ["M9"],
                   "没有疑问",
                   "全篇没有一句自问。人会对自己发问，模型不会。",
                   "no questions",
                   "Not a single question, not even to itself. People ask; models assert.",
                   []))

    f.sort(key=lambda x: SEV_RANK[x["severity"]])   # 稳定排序：同级保持插入顺序
    return f


# ================================================================ 渲染

def render_text(r, ui="zh", max_flags=8):
    t = TXT[ui]
    zh = r["lang"] == "zh"
    m = r["metrics"] if "metrics" in r else None
    L = []
    A = L.append
    A(t["header"].format(label=r["label"], chars=r["chars"], lang=r["lang"],
                         genre=GENRES[r["genre"]][ui]))
    A("")
    rel = t["rel"][r["reliability"]["level"]].format(n=r["reliability"]["unit_count"])
    A(f"{t['reliability']}  {rel}")
    if m is None or r["reliability"]["level"] == "insufficient":
        # 文本太短：句长与词汇统计都是噪声，只留机械类问题
        if r["findings"]:
            A("")
            A(t["findings"])
            for i, fd in enumerate(r["findings"][:max_flags], 1):
                A(f"{i}. [{t['sev_' + fd['severity']]}] {fd['title_' + ui]}：{fd['detail_' + ui]}")
                for ev in fd["evidence"][:3]:
                    A(f"      {ev}")
        A("")
        A(t["note"])
        return "\n".join(L)

    s, p, v = m["sentence"], m["paragraph"], m["vocabulary"]
    unit = t["unit_char"] if zh else t["unit_word"]
    A(f"{t['sentence']}  {s['count']} sentences  mean {s['mean']}  sd {s['sd']}  "
      f"CV {s['cv']}  range {s['min']}-{s['max']}")
    A(f"            short(<={s['short_max']} {unit}) {s['short_ratio_pct']}%   "
      f"long(>={s['long_min']} {unit}) {s['long_ratio_pct']}%   "
      f"adjacent jump {s['mean_adjacent_jump']}")
    A(f"{t['paragraph']}  {p['count']}  mean {p['mean']}  CV {p['cv']}  {p['min']}-{p['max']}")
    A(f"{t['vocabulary']}  TTR {v['ttr']}  hapax {v['hapax_ratio']}")
    if v["top_repeated"]:
        A(f"            top repeated {v['top_repeated']}")
    if m["repetition"]["top_ngrams"]:
        A(f"{t['repetition']}  {m['repetition']['top_ngrams']}")
    fmt, rh, lx, h = m["format"], m["rhetoric"], m["lexical"], m["human"]
    A(f"{t['format']}  digit-space {fmt['digit_space']['count']}  "
      f"enum {fmt['enum_total']}  grandiose {lx['grandiose']['count']}  "
      f"connectors {fmt['connector_ratio_pct']}%")
    A(f"{t['rhetoric']}  simile {rh['simile_count']} ({rh['simile_per_1k']}/1k)  "
      f"tricolon {rh['tricolon']}  not-just {rh['not_just_x']}  em-dash {rh['emdash_per_1k']}/1k")
    A(f"{t['human']}  colloquial {h['colloquial_count']}  tail {h['tail_particle']}  "
      f"hedge {h['hedge_count']}  first-person {h['first_person']}  questions {h['questions']}")
    if lx["en_tells"]["count"] or lx["en_pseudo"]["count"]:
        A(f"{t['english']}  {lx['en_tells']['hits']}  pseudo {lx['en_pseudo']['hits']}")
    A("")

    shown = r["findings"][:max_flags]
    if shown:
        A(t["findings"])
        for i, fd in enumerate(shown, 1):
            sev = t["sev_" + fd["severity"]]
            A(f"{i}. [{sev}] {fd['title_' + ui]}：{fd['detail_' + ui]}")
            for ev in fd["evidence"][:3]:
                A(f"      {ev}")
            if fd["moves"]:
                A(f"      -> {', '.join(fd['moves'])}")
        rest = len(r["findings"]) - len(shown)
        if rest > 0:
            A(t["more"].format(n=rest))
    else:
        A(t["clean"])
    A("")
    A(t["note"])
    return "\n".join(L)


def render_md(results, ui="zh", max_flags=8):
    t = TXT[ui]
    zh = ui == "zh"
    head = ["指标", "数值", "目标"] if zh else ["metric", "value", "target"]
    lab = (["句长 CV", "短句占比", "段落 CV", "hapax 比", "数字空格", "枚举标记"] if zh
           else ["sentence CV", "short sentences", "paragraph CV", "hapax ratio",
                 "digit-space artifacts", "enumeration markers"])
    L = []
    for r in results:
        L.append(f"## {r['label']}")
        L.append("")
        L.append(f"`{r['chars']}` {t['unit_char']} · `{r['lang']}` · "
                 f"`{GENRES[r['genre']][ui]}` · reliability: **{r['reliability']['level']}**")
        L.append("")
        m = r.get("metrics")
        if not m:
            L.append(f"> {t['rel'][r['reliability']['level']].format(n=r['reliability']['unit_count'])}")
            L.append("")
            continue
        s, p, v = m["sentence"], m["paragraph"], m["vocabulary"]
        L.append(f"| {head[0]} | {head[1]} | {head[2]} |")
        L.append("|---|---|---|")
        L.append(f"| {lab[0]} | {s['cv']} | >= {GENRES[r['genre']]['cv']} |")
        L.append(f"| {lab[1]} | {s['short_ratio_pct']}% | >= {GENRES[r['genre']]['short']}% |")
        L.append(f"| {lab[2]} | {p['cv']} | >= {GENRES[r['genre']]['pcv']} |")
        L.append(f"| {lab[3]} | {v['hapax_ratio']} | >= 0.70 |")
        L.append(f"| {lab[4]} | {m['format']['digit_space']['count']} | 0 |")
        L.append(f"| {lab[5]} | {m['format']['enum_total']} | "
                 f"{'allowed' if GENRES[r['genre']]['enum_ok'] else '0-2'} |")
        L.append("")
        if r["findings"]:
            L.append(f"**{t['findings']}**")
            L.append("")
            for fd in r["findings"][:max_flags]:
                L.append(f"- `{t['sev_' + fd['severity']]}` **{fd['title_' + ui]}** — "
                         f"{fd['detail_' + ui]}")
                for ev in fd["evidence"][:2]:
                    L.append(f"  - `{ev}`")
                if fd["moves"]:
                    L.append(f"  - moves: {', '.join(fd['moves'])}")
            L.append("")
        else:
            L.append(f"> {t['clean']}")
            L.append("")
    L.append(f"_{t['note']}_")
    return "\n".join(L)


def _get(d, path):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _enough(r, path):
    """样本量不够的指标不参与对比——145 个词的 hapax 比只是噪声，
    把它算进"退步"会让对比结论变成假的。"""
    if path.startswith("sentence."):
        return (_get(r, "metrics.sentence.count") or 0) >= 6
    if path == "paragraph.cv":
        return (_get(r, "metrics.paragraph.count") or 0) >= 3
    if path == "vocabulary.hapax_ratio":
        # 60 个 content type 上算 hapax 比，波动比信号大一个量级
        return (_get(r, "metrics.vocabulary.content_types") or 0) >= 120
    return True


COMPARE_METRICS = [
    # (path, direction, names, epsilon) — 小于 epsilon 的差值算持平：
    # hapax 从 0.935 掉到 0.929 不是"退步"，是抽样噪声，把它算成退步等于制造假结论。
    ("sentence.cv", "up", {"zh": "句长 CV", "en": "sentence CV"}, 0.02),
    ("sentence.short_ratio_pct", "up", {"zh": "短句占比 %", "en": "short sentences %"}, 1.0),
    ("paragraph.cv", "up", {"zh": "段落 CV", "en": "paragraph CV"}, 0.02),
    ("vocabulary.hapax_ratio", "up", {"zh": "hapax 比", "en": "hapax ratio"}, 0.02),
    ("format.digit_space.count", "down", {"zh": "数字空格", "en": "digit-space hits"}, 0),
    ("format.enum_total", "down", {"zh": "枚举标记", "en": "enumeration markers"}, 0),
    ("format.connector_ratio_pct", "down", {"zh": "段首连接词 %", "en": "connector openings %"}, 1.0),
    ("lexical.grandiose.count", "down", {"zh": "空转大词", "en": "grandiose words"}, 0),
    ("lexical.en_tells.count", "down", {"zh": "英文套词", "en": "English tells"}, 0),
    ("rhetoric.tricolon", "down", {"zh": "三项并列", "en": "tricolons"}, 0),
    ("rhetoric.simile_per_1k", "down", {"zh": "比喻/千字", "en": "similes per 1k"}, 0.5),
]


def _disp_w(s):
    """终端显示宽度：中文占两格，str.ljust 按字符数补空格会把表格排歪。"""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in str(s))


def _pad(s, width, align="left"):
    s = str(s)
    gap = max(0, width - _disp_w(s))
    return (" " * gap + s) if align == "right" else (s + " " * gap)


def render_compare(base, target, ui="zh"):
    t = TXT[ui]
    L = [t["compare_title"].format(base=base["label"], target=target["label"]), ""]
    L.append(_pad("", 24) + _pad("before", 10, "right") + _pad("after", 10, "right")
             + _pad("delta", 10, "right"))
    good = bad = flat = 0
    for path, direction, names, eps in COMPARE_METRICS:
        b, a = _get(base, "metrics." + path), _get(target, "metrics." + path)
        if b is None or a is None or not _enough(base, path) or not _enough(target, path):
            continue
        d = round(a - b, 3)
        if abs(d) <= eps:
            verdict, flat = t["same"], flat + 1
        elif (d > 0) == (direction == "up"):
            verdict, good = t["better"], good + 1
        else:
            verdict, bad = t["worse"], bad + 1
        L.append(_pad(names[ui], 24) + _pad(b, 10, "right") + _pad(a, 10, "right")
                 + _pad(f"{d:+}", 10, "right") + "  " + verdict)
    L.append("")
    L.append(t["compare_sum"].format(n=good + bad + flat, good=good, bad=bad, flat=flat))
    L.append(t["compare_verdict_good"] if bad == 0 else t["compare_verdict_bad"])
    return "\n".join(L)


# ================================================================ CLI

def read_inputs(files):
    jobs = []
    for fp in files:
        if fp == "-":
            jobs.append(("<stdin>", sys.stdin.read()))
            continue
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                jobs.append((fp, fh.read()))
        except OSError as e:
            print(f"error: cannot read {fp}: {e.strerror or e}", file=sys.stderr)
            sys.exit(1)
        except UnicodeDecodeError:
            print(f"error: {fp} is not valid UTF-8", file=sys.stderr)
            sys.exit(1)
    return jobs


def build_parser():
    ap = argparse.ArgumentParser(
        prog="humanity_check.py",
        description="Heuristic humanity self-check for AI-written text. Not a detector.",
        epilog="Use - to read stdin. No network, no dependencies, no score.")
    ap.add_argument("files", nargs="*", help="text files (.md/.txt), or - for stdin")
    ap.add_argument("--text", help="inline text instead of a file")
    ap.add_argument("--genre", default="general", choices=sorted(GENRES),
                    help="threshold profile (default: general)")
    ap.add_argument("--lang", default="auto", choices=["auto", "zh", "en"],
                    help="language of the text (default: auto-detect)")
    ap.add_argument("--ui-lang", default=None, choices=["zh", "en"],
                    help="language of the report (default: follow text language)")
    ap.add_argument("--compare", metavar="BASE",
                    help="compare every input against BASE and print a delta table")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--md", action="store_true", help="Markdown report")
    ap.add_argument("--max-flags", type=int, default=8, help="max findings per file (default: 8)")
    ap.add_argument("--fail-on", default="none", choices=["none", "blocker", "major"],
                    help="exit 2 if any finding reaches this severity (for CI)")
    ap.add_argument("--list-genres", action="store_true", help="print genre profiles and exit")
    ap.add_argument("--version", action="version", version=f"humanity_check.py {__version__}")
    return ap


def print_genres():
    print(f"{'genre':<10}{'CV':>6}{'short%':>8}{'paraCV':>8}{'enum ok':>9}{'connector%':>12}")
    for k, v in GENRES.items():
        print(f"{k:<10}{v['cv']:>6}{v['short']:>8}{v['pcv']:>8}"
              f"{str(v['enum_ok']):>9}{v['connect']:>12}")


def main(argv=None):
    init_stdio()
    ap = build_parser()
    args = ap.parse_args(argv)

    if args.list_genres:
        print_genres()
        return 0

    jobs = []
    if args.text is not None:          # 用 is not None：--text "" 也是一个有效输入
        jobs.append(("<inline>", args.text))
    jobs += read_inputs(args.files)

    if not jobs:
        ap.print_help()
        print()
        print(TXT["zh"]["usage_hint"])
        return 1

    results = [analyze(t, n, args.genre, args.lang) for n, t in jobs]

    # 英文文本默认出英文报告；--ui-lang 可覆盖
    ui = args.ui_lang or results[0]["lang"]

    payload = None
    if args.json:
        payload = {"schema_version": SCHEMA_VERSION,
                   "generator": {"name": "humanity_check.py", "version": __version__},
                   "results": [_strip_private(r, ui, args.max_flags) for r in results]}

    base = None
    if args.compare:
        if args.compare == "-":
            base_text = sys.stdin.read()
        else:
            try:
                with open(args.compare, "r", encoding="utf-8") as fh:
                    base_text = fh.read()
            except OSError as e:
                print(f"error: cannot read baseline {args.compare}: {e.strerror or e}",
                      file=sys.stderr)
                return 1
        base = analyze(base_text, args.compare, args.genre, args.lang)
        if payload is not None:
            payload["comparison"] = {
                "base": args.compare,
                "rows": _compare_rows(base, results),
            }

    if payload is not None:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if base is not None:
            for r in results:
                print(render_compare(base, r, ui))
                print()
        if args.md:
            print(render_md(results, ui, args.max_flags))
        elif base is None:
            for r in results:
                print(render_text(r, ui, args.max_flags))
                print()

    # CI 退出码
    if args.fail_on != "none":
        threshold = 0 if args.fail_on == "blocker" else 1
        if any(any(SEV_RANK[f["severity"]] <= threshold for f in r["findings"]) for r in results):
            return 2
    return 0


def _strip_private(r, ui, max_flags):
    """JSON 里只放可消费的字段，去掉原文与另一语言的文案。"""
    out = {k: v for k, v in r.items() if not k.startswith("_")}
    out["findings"] = [{
        "id": f["id"], "severity": f["severity"], "moves": f["moves"],
        "title": f["title_" + ui], "detail": f["detail_" + ui], "evidence": f["evidence"],
    } for f in r["findings"][:max_flags]]
    out["findings_total"] = r["summary"]["total"]
    # 深拷贝一层，别把 note 写回原始结果（同一进程内还会再渲染一次）
    out["reliability"] = dict(r["reliability"])
    out["reliability"]["note"] = TXT[ui]["rel"][r["reliability"]["level"]].format(
        n=r["reliability"]["unit_count"])
    return out


def _compare_rows(base, results):
    rows = []
    for path, direction, names, eps in COMPARE_METRICS:
        b = _get(base, "metrics." + path)
        if b is None:
            continue
        for r in results:
            a = _get(r, "metrics." + path)
            if a is None or not _enough(base, path) or not _enough(r, path):
                continue
            d = round(a - b, 3)
            verdict = ("flat" if abs(d) <= eps
                       else "better" if (d > 0) == (direction == "up") else "worse")
            rows.append({"metric": path, "base": b, "target": a, "delta": d,
                         "direction": direction, "verdict": verdict, "label": r["label"]})
    return rows


if __name__ == "__main__":
    sys.exit(main())
