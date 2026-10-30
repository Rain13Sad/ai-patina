# 脚本速查 / Script recipes

`scripts/humanity_check.py` 是单文件、仅标准库、不联网。`python scripts/humanity_check.py --help` 是参数的唯一权威来源；本页只给该跑什么。

## 四条命令，覆盖全部工作流

```bash
# S1 诊断：先定体裁，阈值跟着体裁走
python scripts/humanity_check.py draft.md --genre essay

# S2/S3 改完，S5 验收：直接看差值，不要人肉比两份报告
python scripts/humanity_check.py draft.md --compare draft.before.md

# 英文稿：报告语言自动跟随正文，不用额外参数
python scripts/humanity_check.py draft.en.md --genre essay

# 要贴进对话或 PR 的表格
python scripts/humanity_check.py draft.md --md
```

`--compare` 是主操作。改一轮跑一次，只看"退步"那几行。

## 体裁

| `--genre` | 用在 | 特别之处 |
|---|---|---|
| `general` | 不确定时 | 默认，最严 |
| `academic` | 论文、技术文档 | 不要求口语；分点、段首连接词豁免 |
| `essay` | 评论、公众号 | 要求短句与落差 |
| `copy` | 商业文案 | 短句阈值最高，最忌排比 |
| `novel` | 小说 | 段落落差要求最高 |
| `report` | 报告、公文 | 分点豁免，但要求事实密度 |

体裁选错，后面全错：`--genre academic` 跑一篇公众号，会漏掉它真正的问题。

## 退出码

`0` 正常 / `1` 用法或 IO 错误 / `2` 触到 `--fail-on` 的严重度。

CI 里只用 `--fail-on blocker`。blocker 是机械事实（数字空格），major 是判断，判断不该卡构建。

## 严重度

- `blocker` —— 机械痕迹，与文风无关，必须清零。
- `major` —— 检测器真正在称的结构信号（句长 CV、英文套词簇、三项并列、分点）。
- `minor` —— 打磨项。

`findings[].moves` 直接给出对应的改写动作编号（M1–M14），不用再翻 `rewrite-moves.md` 找。

## 两条纪律

1. **它不给"AI 率"。** 要分数就去看检测器，别看这个脚本；这个脚本的作用是告诉你改哪里。
2. **文本短于 60 字（英文 30 词）时只报机械问题。** 句长统计在这个长度上是噪声，报了也是假精度。
