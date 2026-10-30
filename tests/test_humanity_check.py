#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for humanity_check.py.

Run:  python -m unittest discover -s tests -v

The script is loaded by path on purpose: it is shipped as a single file that
users copy into a host, so there is no package to import.
"""

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "human-voice" / "scripts" / "humanity_check.py"
EXAMPLES = ROOT / "examples"

_spec = importlib.util.spec_from_file_location("humanity_check", SCRIPT)
hc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hc)


def read(name):
    return (EXAMPLES / name).read_text(encoding="utf-8")


def run_cli(*args, stdin=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, encoding="utf-8", input=stdin,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


# ---------------------------------------------------------------- unit level

class TestSplitting(unittest.TestCase):
    def test_semicolon_is_not_a_sentence_end(self):
        # 分号切句会把长句剁碎、把 CV 算低，从而漏掉最主要的信号
        sents = hc.split_sentences("这是一个很长的句子，中间有分号；后面还有内容。第二句。", zh=True)
        self.assertEqual(len(sents), 2)

    def test_single_newline_does_not_split(self):
        # 硬折行的文本不能被算成两倍句数
        sents = hc.split_sentences("第一行写着半句话\n第二行接着写完。", zh=True)
        self.assertEqual(len(sents), 1)

    def test_blank_line_splits(self):
        sents = hc.split_sentences("第一段结束。\n\n第二段开始。", zh=True)
        self.assertEqual(len(sents), 2)

    def test_english_abbreviation_survives(self):
        text = "We tested e.g. two tools, and et al. was cited. Then we stopped."
        sents = hc.split_sentences(text, zh=False)
        self.assertEqual(len(sents), 2)

    def test_decimal_is_not_a_sentence_end(self):
        sents = hc.split_sentences("The score was 0.31 on average. That is low.", zh=False)
        self.assertEqual(len(sents), 2)


class TestLanguageDetection(unittest.TestCase):
    def test_chinese(self):
        self.assertEqual(hc.resolve_lang("这是一段中文，没有英文单词。"), "zh")

    def test_english(self):
        self.assertEqual(hc.resolve_lang("This is plainly an English sentence."), "en")

    def test_forced_language_wins(self):
        self.assertEqual(hc.resolve_lang("这是一段中文。", "en"), "en")


class TestSimileFalsePositives(unittest.TestCase):
    def test_image_words_are_not_similes(self):
        # 图像 / 像素 / 成像 / 肖像 里的「像」不是比喻
        text = "图像分辨率、像素密度、成像质量、肖像权，这四个概念经常被混用。"
        r = hc.analyze(text)
        self.assertEqual(r["metrics"]["rhetoric"]["simile_count"], 0)

    def test_actual_simile_counts(self):
        r = hc.analyze("这件事像一块石头压在胸口，让人喘不过气。")
        self.assertEqual(r["metrics"]["rhetoric"]["simile_count"], 1)


class TestFormatTraces(unittest.TestCase):
    def test_digit_space_is_a_blocker_with_a_line_number(self):
        text = "第一段有 12 处空格。\n第二段没有。"
        r = hc.analyze(text)
        blockers = [f for f in r["findings"] if f["severity"] == "blocker"]
        self.assertEqual(len(blockers), 1)
        self.assertTrue(blockers[0]["evidence"])
        self.assertIn("L1", blockers[0]["evidence"][0])

    def test_english_digit_spacing_is_not_flagged(self):
        r = hc.analyze("The study covered 12 cases and 3 sites over 5 years of work.")
        self.assertEqual(r["metrics"]["format"]["digit_space"]["count"], 0)


class TestEnglishTells(unittest.TestCase):
    def test_vocabulary_cluster(self):
        r = hc.analyze(read("en-before.md"))
        self.assertGreaterEqual(r["metrics"]["lexical"]["en_tells"]["count"], 3)
        ids = [f["id"] for f in r["findings"]]
        self.assertIn("lexical.en_tells", ids)

    def test_tricolon(self):
        r = hc.analyze(read("en-before.md"))
        self.assertGreaterEqual(r["metrics"]["rhetoric"]["tricolon"], 2)
        self.assertIn("rhetoric.tricolon", [f["id"] for f in r["findings"]])

    def test_not_just_x(self):
        r = hc.analyze("It is not just a tool, but a whole new way of working. "
                       "It's not a feature. It's a philosophy.")
        self.assertGreaterEqual(r["metrics"]["rhetoric"]["not_just_x"], 2)

    def test_stopwords_do_not_top_the_repeat_list(self):
        r = hc.analyze("The cat and the dog and the bird and the fish and the horse ran.")
        words = [w for w, _ in r["metrics"]["vocabulary"]["top_repeated"]]
        self.assertNotIn("and", words)
        self.assertNotIn("the", words)


class TestGenreProfiles(unittest.TestCase):
    ENUM_TEXT = (
        "第一、先看协作边界。\n"
        "- 明确谁在什么时候可以打断谁\n"
        "- 明确哪些决定必须同步\n"
        "首先，要建立清晰的沟通规范；其次，要提供必要的技术支持。\n"
    )

    def test_enumeration_is_exempt_in_a_report(self):
        essay = hc.analyze(self.ENUM_TEXT, genre="essay")
        report = hc.analyze(self.ENUM_TEXT, genre="report")
        self.assertIn("format.enumeration", [f["id"] for f in essay["findings"]])
        self.assertNotIn("format.enumeration", [f["id"] for f in report["findings"]])

    def test_academic_does_not_ask_for_colloquialism(self):
        text = "本研究采用混合方法，样本量为 412 份问卷。结果显示，变量之间存在显著相关。" * 4
        r = hc.analyze(text, genre="academic")
        self.assertNotIn("human.colloquial", [f["id"] for f in r["findings"]])

    def test_unknown_genre_falls_back_to_general(self):
        r = hc.analyze("随便一段话，用来确认未知体裁不会崩。", genre="nope")
        self.assertEqual(r["genre"], "general")


class TestSeverityAndReliability(unittest.TestCase):
    def test_blockers_sort_first(self):
        # 在正常的 AI 稿后面加一处数字空格，制造一个阻断项
        text = read("zh-before.md") + "\n\n这一段故意留了 12 处空格，用来制造阻断项。\n"
        r = hc.analyze(text)
        sevs = [f["severity"] for f in r["findings"]]
        self.assertEqual(sevs[0], "blocker")
        self.assertEqual(sevs, sorted(sevs, key=lambda s: hc.SEV_RANK[s]))

    def test_tiny_text_keeps_only_blockers(self):
        r = hc.analyze("好。")
        self.assertEqual(r["reliability"]["level"], "insufficient")
        self.assertTrue(all(f["severity"] == "blocker" for f in r["findings"]))

    def test_english_reliability_is_measured_in_words(self):
        # 300 个英文字符只有约 50 个词，不能报"中等"
        text = "word " * 50
        r = hc.analyze(text.strip() + ".")
        self.assertEqual(r["reliability"]["unit_count"], 50)
        self.assertIn(r["reliability"]["level"], ("low", "insufficient"))

    def test_long_chinese_is_high_reliability(self):
        r = hc.analyze("这是一句用于测试可信度的中文句子，长度足够。" * 60)
        self.assertEqual(r["reliability"]["level"], "high")


class TestComparison(unittest.TestCase):
    def test_rows_mark_direction(self):
        base = hc.analyze(read("zh-before.md"))
        target = hc.analyze(read("zh-after.md"))
        rows = hc._compare_rows(base, [target])
        by_metric = {r["metric"]: r for r in rows}
        self.assertEqual(by_metric["sentence.cv"]["verdict"], "better")
        self.assertEqual(by_metric["format.connector_ratio_pct"]["verdict"], "better")
        self.assertEqual(by_metric["format.digit_space.count"]["verdict"], "flat")

    def test_noisy_metrics_are_skipped(self):
        # 58 个 content type 上的 hapax 比不参与对比
        base = hc.analyze(read("en-before.md"))
        target = hc.analyze(read("en-after.md"))
        metrics = [r["metric"] for r in hc._compare_rows(base, [target])]
        self.assertNotIn("vocabulary.hapax_ratio", metrics)

    def test_small_delta_is_flat_not_worse(self):
        base = hc.analyze(read("zh-before.md"))
        target = hc.analyze(read("zh-before.md"))
        rows = hc._compare_rows(base, [target])
        self.assertTrue(all(r["verdict"] == "flat" for r in rows))


# ---------------------------------------------------------------- CLI level

class TestCli(unittest.TestCase):
    def test_version(self):
        out = run_cli("--version")
        self.assertEqual(out.returncode, 0)
        self.assertIn(hc.__version__, out.stdout)

    def test_json_envelope(self):
        out = run_cli(str(EXAMPLES / "zh-before.md"), "--json")
        self.assertEqual(out.returncode, 0)
        data = json.loads(out.stdout)
        self.assertEqual(data["schema_version"], hc.SCHEMA_VERSION)
        self.assertEqual(data["generator"]["version"], hc.__version__)
        r = data["results"][0]
        for key in ("label", "lang", "genre", "metrics", "findings", "summary"):
            self.assertIn(key, r)

    def test_json_findings_are_localized(self):
        zh = json.loads(run_cli(str(EXAMPLES / "zh-before.md"), "--json").stdout)
        en = json.loads(run_cli(str(EXAMPLES / "zh-before.md"), "--json",
                                "--ui-lang", "en").stdout)
        zh_title = zh["results"][0]["findings"][0]["title"]
        en_title = en["results"][0]["findings"][0]["title"]
        self.assertNotEqual(zh_title, en_title)
        self.assertIn("title", en["results"][0]["findings"][0])
        self.assertNotIn("title_zh", en["results"][0]["findings"][0])

    def test_ui_language_defaults_to_text_language(self):
        out = run_cli(str(EXAMPLES / "en-before.md"))
        self.assertIn("[sentence length]", out.stdout)

    def test_ui_language_can_be_forced(self):
        out = run_cli(str(EXAMPLES / "en-before.md"), "--ui-lang", "zh")
        self.assertIn("[句长波动]", out.stdout)

    def test_compare_table(self):
        out = run_cli(str(EXAMPLES / "zh-after.md"), "--compare", str(EXAMPLES / "zh-before.md"))
        self.assertEqual(out.returncode, 0)
        self.assertIn("句长 CV", out.stdout)
        self.assertIn("改善", out.stdout)

    def test_compare_json(self):
        out = run_cli(str(EXAMPLES / "zh-after.md"), "--compare", str(EXAMPLES / "zh-before.md"),
                      "--json")
        data = json.loads(out.stdout)
        self.assertIn("comparison", data)
        self.assertTrue(data["comparison"]["rows"])

    def test_fail_on_major_sets_exit_code(self):
        bad = run_cli(str(EXAMPLES / "zh-before.md"), "--fail-on", "major")
        good = run_cli(str(EXAMPLES / "zh-after.md"), "--fail-on", "major")
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(good.returncode, 0)

    def test_markdown_output(self):
        zh = run_cli(str(EXAMPLES / "zh-before.md"), "--md")
        en = run_cli(str(EXAMPLES / "en-before.md"), "--md")
        self.assertIn("| 指标 | 数值 | 目标 |", zh.stdout)
        self.assertIn("| metric | value | target |", en.stdout)
        self.assertIn("## ", zh.stdout)

    def test_stdin(self):
        out = run_cli("-", stdin="这是一段通过标准输入传入的中文文本，用来确认管道可用。")
        self.assertEqual(out.returncode, 0)
        self.assertIn("<stdin>", out.stdout)

    def test_empty_inline_text_is_still_a_job(self):
        out = run_cli("--text", "")
        self.assertEqual(out.returncode, 0)
        self.assertIn("<inline>", out.stdout)

    def test_no_input_prints_help(self):
        out = run_cli()
        self.assertEqual(out.returncode, 1)
        self.assertIn("usage", out.stdout.lower())

    def test_missing_file_is_a_clean_error(self):
        out = run_cli("does-not-exist.md")
        self.assertEqual(out.returncode, 1)
        self.assertIn("cannot read", out.stderr)
        self.assertNotIn("Traceback", out.stderr)

    def test_list_genres(self):
        out = run_cli("--list-genres")
        self.assertIn("academic", out.stdout)
        self.assertIn("novel", out.stdout)

    def test_max_flags_truncates(self):
        out = run_cli(str(EXAMPLES / "en-before.md"), "--max-flags", "2", "--json")
        data = json.loads(out.stdout)
        self.assertEqual(len(data["results"][0]["findings"]), 2)
        self.assertGreater(data["results"][0]["findings_total"], 2)

    def test_text_output_has_no_score_claim(self):
        out = run_cli(str(EXAMPLES / "zh-before.md"))
        self.assertNotIn("AI 率", out.stdout)
        self.assertIn("不是检测器", out.stdout)


if __name__ == "__main__":
    unittest.main()
