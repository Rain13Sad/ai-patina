#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
humanity_check.py — 文本"人味"自查器

用途：改写前后各跑一次，用可量化的表层指标定位 AI 痕迹。
性质：启发式自查，**不是检测器**。它测的是文档里那几个公开可解释的特征
      （句长波动、词汇多样性、n-gram 重复、格式痕迹、套话密度），
      不产生"AI 率"这种数字，因为那个数字本身不稳定、不可复现。

用法：
    python humanity_check.py draft.md
    python humanity_check.py draft.md --json
    python humanity_check.py --text "要检查的一段话"
    python humanity_check.py a.md b.md          # 多文件对比

仅依赖标准库。
"""

import sys
import re
import json
import math
import argparse
from collections import Counter

# ---------------------------------------------------------------- 词表

# 中文虚词/高频功能词，用于过滤"高频实词"统计
STOP_ZH = set("""
的 了 是 在 和 与 也 就 都 而 及 或 被 把 让 使 对 从 到 为 以 于 之 其 这 那 有 我 你 他 她 它 我们 你们 他们
不 没 很 更 最 会 能 要 可以 一个 一些 这个 那个 这些 那些 上 下 中 里 外 后 前 时 个 们 过 着 地 得 等 但 却
如 若 则 即 又 再 还 已 曾 将 应 该 可 需 须 并 且 因 由 此 所 者 也 呢 吗 吧 啊 嘛 呀
""".split())

# 主题升华 / 空转大词：AI 中文最典型的"结尾拔高"标记
GRANDIOSE = """
折射 彰显 凝聚 赋能 闭环 抓手 生态位 底色 注脚 篇章 光芒 光辉 本质 深刻变革 新时代
新篇章 温度 力量 价值坐标 精神内核 生动实践 时代答卷 行稳致远 久久为功 提质增效
深度融合 全方位 多维度 立体化 系统性重塑 格局 势能 护城河 想象力 坐标系
""".split()

# 分点 / 机械枚举标记
ENUM_PATTERNS = [
    (r"第[一二三四五六七八九十]+[、，,．.]", "第一、第二式"),
    (r"(?m)^\s*[①②③④⑤⑥⑦⑧⑨⑩]", "圈号列表"),
    (r"(?m)^\s*\d+[、.．)）]\s*\S", "阿拉伯数字列表"),
    (r"(?m)^\s*[-*+]\s+\S", "无序列表"),
    (r"首先[，,].{0,80}?其次[，,]", "首先/其次"),
    (r"一方面.{0,120}?另一方面", "一方面/另一方面"),
]

# 段首连接词依赖：AI 极爱用这些开头起段
CONNECT_START = "此外 然而 因此 同时 总之 综上 值得注意的是 更重要的是 与此同时 另一方面 由此可见 总的来说 总而言之 需要指出的是".split()
CONNECT_START_EN = ["furthermore", "moreover", "additionally", "however", "therefore",
                    "consequently", "in addition", "ultimately", "overall", "notably"]

# 口语 / 人味正面标记
COLLOQUIAL = """
其实 说白了 老实说 说实话 反正 挺 蛮 说不清 我觉得 我猜 结果 后来 也就是说 换句话说
问题是 奇怪的是 意外的是 干脆 顺手 得了吧 谁知道 我印象里 我记得 折腾 靠谱 不像话
而已 干嘛 啥 咋 呗 算了 顶多 无非 压根 说白了就是 话又说回来 说白了 谁知道呢
""".split()

# 模糊限定语：人写作会留余地，模型倾向于给确定断言
HEDGE = """
大概 可能 估计 差不多 某种意义上 至少 不太 好像 似乎 说不定 很难说 不一定 大体上
""".split()

# 英文 AI 高频词（英文场景用）
EN_TELLS = """
delve tapestry landscape realm navigate leverage robust seamless holistic paradigm
underscore pivotal intricate multifaceted nuanced testament foster showcase
furthermore moreover additionally consequently ultimately
""".split()

# 标点与句式
# 注意：中文分号「；」是分句符，不是句末符。按它切会把长句剁碎、把 CV 算低，
# 从而漏掉"句长过于均匀"这个最主要的信号。只按真正的句末符与换行切。
RE_SENT_SPLIT = re.compile(r"[。！？!?…]+|\n+")
# 英文句号要单独处理，且不能在小数点处断开（0.31 不能被切成两句）
RE_SENT_SPLIT_EN = re.compile(r"(?<!\d)[.!?]+(?!\d)|\n+")
RE_ZH = re.compile(r"[\u4e00-\u9fff]")
RE_DIGIT_SPACE = re.compile(r"[\u4e00-\u9fff][ \t]+\d[\d.,%]*|\d[\d.,%]*[ \t]+[\u4e00-\u9fff]")
RE_ASCII_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
RE_TAIL_PARTICLE = re.compile(r"[了吧呢啊嘛呗啦哦呀]\s*[。！？!?]?$")


# ---------------------------------------------------------------- 工具

def is_zh(s):
    return len(RE_ZH.findall(s)) > len(RE_ASCII_WORD.findall(s))


def strip_markup(text):
    """去掉标题行、表格行、代码块，避免它们污染句长统计。"""
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


def split_sentences(text, zh=True):
    parts = (RE_SENT_SPLIT if zh else RE_SENT_SPLIT_EN).split(strip_markup(text))
    out = []
    for p in parts:
        p = p.strip()
        p = re.sub(r"^[#>\-\*\s]+", "", p)      # 去掉 markdown 标记
        # 阈值放到 2：像"是新人。"这种 3 字短句正是人类节奏的核心证据，不能被过滤
        if len(RE_ZH.findall(p)) + len(RE_ASCII_WORD.findall(p)) >= 2:
            out.append(p)
    return out


def split_paragraphs(text):
    out = []
    for block in re.split(r"\n\s*\n", text):
        b = block.strip()
        if not b or b.startswith("|") or b.startswith("```"):
            continue
        b = re.sub(r"^[#>\-\*\s]+", "", b)
        if len(b) >= 10:
            out.append(b)
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
    toks += [w.lower() for w in RE_ASCII_WORD.findall(text)]
    return toks


def stats(nums):
    if not nums:
        return {"n": 0, "mean": 0.0, "sd": 0.0, "cv": 0.0, "min": 0, "max": 0}
    n = len(nums)
    m = sum(nums) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in nums) / n) if n > 1 else 0.0
    return {"n": n, "mean": round(m, 1), "sd": round(sd, 1),
            "cv": round(sd / m, 2) if m else 0.0,
            "min": min(nums), "max": max(nums)}


def level(value, weak, strong, reverse=False):
    """reverse=True 表示数值越大越像人（如句长 CV）。"""
    if reverse:
        return "OK" if value >= strong else ("偏弱" if value >= weak else "明显")
    return "OK" if value <= strong else ("偏弱" if value <= weak else "明显")


def find_examples(pattern, text, limit=3):
    hits = [m.group(0) for m in re.finditer(pattern, text)]
    return hits[:limit], len(hits)


# ---------------------------------------------------------------- 主分析

def analyze(text, label="<text>"):
    zh = is_zh(text)
    r = {"label": label, "lang": "zh" if zh else "en", "chars": len(text)}

    # 极短文本：所有指标都无意义，直接短路，避免输出一堆假警报
    if len(RE_ZH.findall(text)) + len(RE_ASCII_WORD.findall(text)) < 20:
        r["reliability"] = "不适用 —— 有效词数少于 20，任何指标都没有意义"
        r["_flags"] = []
        r["_too_short"] = True
        return r

    sents = split_sentences(text, zh)
    paras = split_paragraphs(text)
    s_len = [len(RE_ZH.findall(s)) if zh else len(RE_ASCII_WORD.findall(s)) for s in sents]
    p_len = [len(p) for p in paras]

    # --- 1. 句长波动（对应 burstiness）
    ss = stats(s_len)
    # 中文以"字"计，英文以"词"计，短句/长句的门槛因此不同
    SHORT_MAX, LONG_MIN = (10, 45) if zh else (8, 30)
    short_ratio = round(100.0 * sum(1 for x in s_len if x <= SHORT_MAX) / max(1, len(s_len)), 1)
    long_ratio = round(100.0 * sum(1 for x in s_len if x >= LONG_MIN) / max(1, len(s_len)), 1)
    adj = [abs(s_len[i] - s_len[i - 1]) for i in range(1, len(s_len))]
    r["sentence"] = {
        "count": ss["n"], "mean_len": ss["mean"], "sd": ss["sd"], "cv": ss["cv"],
        "min": ss["min"], "max": ss["max"],
        "short_ratio_pct": short_ratio, "long_ratio_pct": long_ratio,
        "short_max": SHORT_MAX, "long_min": LONG_MIN,
        "mean_adjacent_jump": round(sum(adj) / len(adj), 1) if adj else 0.0,
    }
    r["sentence"]["cv_status"] = level(ss["cv"], 0.35, 0.45, reverse=True)
    r["sentence"]["short_status"] = level(short_ratio, 8, 15, reverse=True)

    # --- 2. 段落长度（对应"段段等长"）
    ps = stats(p_len)
    r["paragraph"] = {"count": ps["n"], "mean_len": ps["mean"], "cv": ps["cv"],
                      "min": ps["min"], "max": ps["max"]}
    r["paragraph"]["status"] = (level(ps["cv"], 0.30, 0.42, reverse=True)
                                if ps["n"] >= 3 else "样本不足")

    # --- 3. 词汇多样性
    toks = char_bigrams(text)
    content = [t for t in toks if t not in STOP_ZH and len(t) > 1]
    tf = Counter(content)
    hapax = sum(1 for w, c in tf.items() if c == 1)
    r["vocabulary"] = {
        "tokens": len(toks), "types": len(set(toks)),
        "ttr": round(len(set(toks)) / max(1, len(toks)), 3),
        "content_types": len(tf),
        "hapax_ratio": round(hapax / max(1, len(tf)), 3),
        "top_repeated": [[w, c] for w, c in tf.most_common(6) if c >= 3],
    }
    r["vocabulary"]["hapax_status"] = (level(r["vocabulary"]["hapax_ratio"], 0.55, 0.70, reverse=True)
                                       if len(tf) >= 40 else "样本不足")

    # --- 4. n-gram 重复（对应"相同词语复用 / 语义冗余循环"）
    grams = Counter()
    for i in range(len(content) - 2):
        grams["·".join(content[i:i + 3])] += 1
    r["ngram"] = {"repeated_3gram": [[g, c] for g, c in grams.most_common(5) if c >= 3]}

    # --- 5. 格式痕迹（数字空格是中文特有痕迹；英文里数字前后空格是正常排版）
    fmt = {}
    if zh:
        hits, n = find_examples(RE_DIGIT_SPACE.pattern, text)
        fmt["digit_space"] = {"count": n, "examples": hits}
    else:
        fmt["digit_space"] = {"count": 0, "examples": []}
    enums = {}
    for pat, name in ENUM_PATTERNS:
        h, cnt = find_examples(pat, text)
        if cnt:
            enums[name] = {"count": cnt, "examples": h}
    fmt["enumeration"] = enums
    fmt["enum_total"] = sum(v["count"] for v in enums.values())

    # --- 6. 套话密度（中文词表）
    g_hits = [w for w in GRANDIOSE if w in text] if zh else []
    r["grandiose"] = {"hits": g_hits, "count": len(g_hits)}

    # --- 7. 段首连接词依赖
    starts = []
    if zh:
        for p in paras:
            head = p[:4]
            for c in CONNECT_START:
                if head.startswith(c):
                    starts.append(c)
                    break
    else:
        for p in paras:
            head = p[:24].lower()
            for c in CONNECT_START_EN:
                if head.startswith(c):
                    starts.append(c)
                    break
    r["connector_starts"] = {"count": len(starts),
                             "ratio_pct": round(100.0 * len(starts) / max(1, len(paras)), 1),
                             "hits": starts}

    # --- 8. 排比 / 比喻连排
    similes = len(re.findall(r"(像|如同|仿佛|好似|宛如)", text)) if zh else \
        len(re.findall(r"\b(like|as if|as though)\b", text, re.I))
    r["simile"] = {"count": similes,
                   "per_1000_chars": round(1000.0 * similes / max(1, len(text)), 1)}

    # --- 9. 人味正面标记
    coll = [w for w in COLLOQUIAL if w in text] if zh else []
    hedges = [w for w in HEDGE if w in text] if zh else \
        [w for w in ["maybe", "perhaps", "probably", "roughly", "not sure", "I think"]
         if w in text.lower()]
    tail = sum(1 for s in sents if RE_TAIL_PARTICLE.search(s)) if zh else 0
    r["human_markers"] = {
        "colloquial_hits": coll[:8],
        "colloquial_count": len(coll),
        "tail_particle": tail,
        "hedge_hits": hedges[:6],
        "hedge_count": len(hedges),
        "first_person": (len(re.findall(r"(?<![其])我(?!们)", text)) + len(re.findall(r"我们", text)))
        if zh else len(re.findall(r"\b(I|we|my|our)\b", text)),
        "questions": len(re.findall(r"[？?]", text)),
        "dash": len(re.findall(r"——|—", text)) if zh else len(re.findall(r"—|--", text)),
        "paren": len(re.findall(r"[（(]", text)),
        "numbers": len(re.findall(r"\d+(?:\.\d+)?%?", text)),
        "digit_density_pct": round(100.0 * len(re.findall(r"\d", text)) / max(1, len(text)), 1),
    }

    # --- 10. 英文 AI 高频词
    if not zh:
        low = text.lower()
        en_hits = [w for w in EN_TELLS if re.search(r"\b" + w + r"\b", low)]
        r["en_tells"] = en_hits

    r["format"] = fmt
    n_chars = len(text)
    if n_chars < 300:
        r["reliability"] = "低 —— 文本过短，任何统计指标（包括真实检测器）都不可靠，只做参考"
    elif n_chars < 1000:
        r["reliability"] = "中 —— 可看出趋势，但阈值判断会抖"
    else:
        r["reliability"] = "较高 —— 长度已超过主流检测器的最低要求（约 300–1000 字）"
    r["_flags"] = build_flags(r)
    return r


def build_flags(r):
    """按优先级生成待办，最多 6 条。中文专属项在英文文本上不检查。"""
    zh = r["lang"] == "zh"
    f = []
    s = r["sentence"]
    if s["cv_status"] != "OK":
        f.append(("句长过于均匀", f"CV={s['cv']}（人类常 >0.45）。每 3–4 句插一个极短句"
                                  f"（中文 ≤10 字 / 英文 ≤8 词），或在长句后直接断句成两截。"))
    if s["short_ratio_pct"] < 8 and s["count"] >= 6:
        f.append(("缺少短句", f"极短句仅占 {s['short_ratio_pct']}%。整篇没有「喘气的地方」，"
                             f"这是最容易被识别的节奏特征。"))
    if r["paragraph"]["status"] not in ("OK", "样本不足"):
        f.append(("段落等长", f"段落长度 CV={r['paragraph']['cv']}。长短段交替，"
                             f"允许某段只有一句话。"))
    if zh and r["format"]["digit_space"]["count"] > 0:
        f.append(("数字两侧有空格", f"命中 {r['format']['digit_space']['count']} 处，"
                                   f"例：{r['format']['digit_space']['examples'][:2]}。"
                                   f"这是 Markdown 渲染习惯的残留，人手写中文不会这样，务必清掉。"))
    if r["format"]["enum_total"] >= 3:
        f.append(("机械分点", f"枚举标记 {r['format']['enum_total']} 处（{list(r['format']['enumeration'])}）。"
                             f"改成因果、让步、转折串联。"))
    if zh and r["grandiose"]["count"] >= 2:
        f.append(("主题升华", f"空转大词：{r['grandiose']['hits'][:5]}。删掉拔高，让结论停在具体层面。"))
    if r["connector_starts"]["ratio_pct"] >= 30:
        f.append(("段首连接词依赖", f"{r['connector_starts']['ratio_pct']}% 的段落以"
                                   f"{r['connector_starts']['hits'][:4]} 开头。删掉它们，靠内容衔接。"))
    if r["vocabulary"]["top_repeated"]:
        top = r["vocabulary"]["top_repeated"][0]
        if top[1] >= 5:
            f.append(("同词高频复用", f"「{top[0]}」出现 {top[1]} 次。代词化、省略、换叙述视角。"))
    if r["ngram"]["repeated_3gram"]:
        f.append(("三词组重复", f"{r['ngram']['repeated_3gram'][:3]}。同一意思只写一遍。"))
    if r["vocabulary"]["hapax_status"] not in ("OK", "样本不足"):
        f.append(("用词过于均衡", f"仅出现一次的词占 {r['vocabulary']['hapax_ratio']}。"
                                 f"人写作有「偏科」：几个爱用的词反复用，其余随手取。"))
    if r["simile"]["per_1000_chars"] >= 4:
        f.append(("比喻连排", f"比喻密度 {r['simile']['per_1000_chars']}/千字。"
                             f"三个并列砍成一个，或让最后一个变形。"))
    if zh and r["human_markers"]["colloquial_count"] == 0 and r["human_markers"]["tail_particle"] == 0:
        f.append(("零口语痕迹", "全文没有一个口语词，也没有一句以「了/吧/呢/啊」收尾。"
                               "正式文体可以少，但一个都没有就是机器味。"))
    if r["human_markers"]["hedge_count"] == 0 and r["chars"] > 500:
        f.append(("没有留余地", "全篇零模糊限定（大概/可能/不一定/很难说）。人对自己不确定的东西会承认不确定，"
                               "模型倾向于给出干净利落的断言。"))
    if r["human_markers"]["questions"] == 0 and r["chars"] > 600:
        f.append(("没有疑问", "全篇没有一句自问。人会对自己发问，模型不会。"))
    return f[:6]


# ---------------------------------------------------------------- 输出

def render(r):
    L = []
    A = L.append
    A(f"═══ {r['label']}  ({r['chars']} 字符, {r['lang']}) ═══")
    A("")
    if r.get("_too_short"):
        A(f"[跳过] {r['reliability']}")
        return "\n".join(L)
    s, p, v = r["sentence"], r["paragraph"], r["vocabulary"]
    A(f"[句长波动]  {s['count']} 句  均 {s['mean_len']}  标准差 {s['sd']}  CV {s['cv']}  "
      f"区间 {s['min']}–{s['max']}   → {s['cv_status']}")
    unit = "字" if r["lang"] == "zh" else "词"
    A(f"            短句(≤{s['short_max']}{unit}) {s['short_ratio_pct']}%  [{s['short_status']}]   "
      f"长句(≥{s['long_min']}{unit}) {s['long_ratio_pct']}%   相邻句落差 {s['mean_adjacent_jump']}")
    A(f"[段落]      {p['count']} 段  均 {p['mean_len']} 字  CV {p['cv']}  "
      f"{p['min']}–{p['max']} → {p['status']}")
    A(f"[词汇]      TTR {v['ttr']}   hapax(仅一次) {v['hapax_ratio']} [{v['hapax_status']}]")
    if v["top_repeated"]:
        A(f"            高频实词 {v['top_repeated']}")
    if r["ngram"]["repeated_3gram"]:
        A(f"[3-gram]    {r['ngram']['repeated_3gram']}")
    A(f"[格式痕迹]  数字空格 {r['format']['digit_space']['count']}   "
      f"枚举 {r['format']['enum_total']}   升华词 {r['grandiose']['count']} "
      f"{r['grandiose']['hits'][:4]}")
    A(f"            段首连接词 {r['connector_starts']['ratio_pct']}% "
      f"{r['connector_starts']['hits'][:4]}")
    A(f"[比喻]      {r['simile']['count']} 处 ({r['simile']['per_1000_chars']}/千字)")
    h = r["human_markers"]
    A(f"[人味标记]  口语 {h['colloquial_count']} {h['colloquial_hits'][:5]}   "
      f"句末语气词 {h['tail_particle']}   模糊限定 {h['hedge_count']} {h['hedge_hits'][:4]}")
    A(f"            第一人称 {h['first_person']}   疑问 {h['questions']}   "
      f"数字 {h['numbers']}（密度 {h['digit_density_pct']}%）   "
      f"破折号 {h['dash']}   括号 {h['paren']}")
    if r.get("en_tells"):
        A(f"[英文套词]  {r['en_tells']}")
    A(f"[可信度]    {r['reliability']}")
    A("")
    if r["_flags"]:
        A("── 待办（按优先级）──")
        for i, (title, why) in enumerate(r["_flags"], 1):
            A(f"{i}. {title}：{why}")
    else:
        A("── 表层指标全部通过。下一步只能靠人工判断：事实、判断力、有没有人真的想过。──")
    A("")
    A("注：以上是启发式自查，不是检测器分数。检测器把文本切段判定，"
      "分数随分段、长度、上下文漂移，不可复现。")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="文本人味自查（启发式）")
    ap.add_argument("files", nargs="*", help="待检查的文本文件（.md/.txt）")
    ap.add_argument("--text", help="直接传入文本")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    jobs = []
    if args.text:
        jobs.append(("<inline>", args.text))
    for fp in args.files:
        with open(fp, "r", encoding="utf-8") as fh:
            jobs.append((fp, fh.read()))
    if not jobs:
        ap.print_help()
        return 1

    results = [analyze(t, n) for n, t in jobs]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(render(r))
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
