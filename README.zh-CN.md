# ai-patina

[English](README.md) · **简体中文**

[![CI](https://github.com/Rain13Sad/ai-patina/actions/workflows/ci.yml/badge.svg)](https://github.com/Rain13Sad/ai-patina/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](docs/cli.md)

> 一个给 AI 代理用的技能：把机器写的文本改成有人味的样子，AI 生成率随之下降——那是副产品。

*Patina* 是铜绿，是被手反复摩挲之后才长出来的那层东西。名字就是这个意思：有包浆的文字，是过了某人的手——他的具体经历、他的立场、他决定不说的那些话。

---

## 这是什么

一个面向 AI 代理的技能（WorkBuddy、Claude 系技能宿主，或任何能读 `SKILL.md` 的代理），用来把 AI 生成的文本改写成像是人写的。

它建立在一个前提上：**检测器不读语义，它测可预测性。** 所以修法不是"把词换成更花哨的"，而是**离开模型最可能走的那条路**——而人本来就在路外，因为人有具体经历、有真实立场、有决定不说的东西。

## 这不是什么

装之前先读这段。

| 不做 | 原因 |
|---|---|
| 清除水印、元数据、隐形字符 | 《人工智能生成合成内容标识办法》与 GB 45438-2025 明文禁止；欧盟《AI 法案》第 50 条同类义务 |
| 伪造文档结构、修订记录、写作过程证据 | 无法事后补造，而且这是唯一一层改写碰不到的 |
| 代写论文、作业、评审意见并当作原创提交 | 不在范围内 |
| 承诺分数 | "96% AI" 的意思是*这段文本带有很强的 AI 特征*，不是*96% 由 AI 写成*。分数随分段、长度、上下文漂移，不可复现 |

**它做的是**：提升文本质量、校准个人文风、还原被磨平的个人表达、准备误判申诉材料。

如果有人说"帮我把 AI 率降到 15% 以下好交论文"，技能的第一反应是说明这个数字是概率分类结果而非证据——Turnitin 宣称文档级假阳性 <1%，独立测试中部分样本可达 50%；OpenAI 自家分类器准确率 26%，已下线。然后给出两条诚实路径：改文本质量，以及留好过程材料。

---

## 四句话说清原理

1. 模型最可预测的地方，恰好是人最不会写的地方：句长均匀、用词均衡、面面俱到、论证无摩擦、结尾必然升华。
2. 所以杠杆在结构，不在措辞。换同义词只动表层，监督分类器看的是整体指纹。
3. **不要让模型"把这段改得像人写的"。** 输出的仍是模型分布里的样本。有实证：AI 率 62%，要求"改得像人写的"，改完 94%。
4. 真正有效的是**边写边做的重写**：换骨架、砍三成、加反例、放进一个具体的人。

---

## 安装

```bash
git clone https://github.com/Rain13Sad/ai-patina.git
cp -r ai-patina/skills/human-voice ~/.workbuddy-ai/skills/    # WorkBuddy
# cp -r ai-patina/skills/human-voice ~/.claude/skills/        # Claude 系宿主
```

只给单个项目用，就放到项目的 `.workbuddy-ai/skills/` 或 `.claude/skills/` 下。

零依赖。自查脚本只用 Python 3 标准库，而且这条守得住——CI 里有一项检查，一旦出现第三方 import 就失败。

## 使用

直接说就行。触发词：

- 去 AI 味 / 写得像人 / 降低 AI 率 / 加人味 / 别这么机械
- remove the AI smell / make this sound human / humanize this / doesn't read like ChatGPT

也可以直接跑脚本：

```bash
python skills/human-voice/scripts/humanity_check.py draft.md --genre essay
python skills/human-voice/scripts/humanity_check.py draft.md --compare draft.before.md
python skills/human-voice/scripts/humanity_check.py draft.md --json --md
cat draft.md | python skills/human-voice/scripts/humanity_check.py -
```

一段典型的 AI 稿，`--genre essay` 下长这样：

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

每条待办后面直接挂着对应的改写动作编号（M1–M14），代理不用回头翻文档就知道下一步做什么。

改完再跟原稿比，而不是人肉看两份报告：

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

脚本中英双语：英文稿默认出英文报告，中文稿出中文报告，`--ui-lang` 可以强制覆盖。它**刻意不输出"AI 率"**——那个数字你改一下分段就会变，给出来只是假精度。

完整参数与 JSON 契约见 [`docs/cli.md`](docs/cli.md)。

## 工作流

| 阶段 | 做什么 |
|---|---|
| **S0** | 定体裁、读者、"人"的浓度。这一步错了，后面全错 |
| **S1** | 诊断：带上 `--genre` 跑自查，做五维审计，查事实——虚构引用改不回来 |
| **S2** | 结构重写，占总工作量七成。先换骨架；骨架不换，改多少词都白费 |
| **S3** | 句级节奏手术。目标不是句子更花哨，是读起来有呼吸 |
| **S4** | 机械痕迹清扫。不需要判断力，但漏一项就白干 |
| **S5** | 验收：`--compare` 对原稿、出声读、倒着读 |

**顺序有纪律**：S4 必须在 S2/S3 之后；S5 之后不允许再"整体润色一遍"——会把刚做的手术全部抹平。

## 14 个动作

| # | 动作 | 治什么 |
|---|---|---|
| A1 | 换骨架 | 定义→背景→意义的开场 |
| A2 | 删升华 | 结尾强行拔高 |
| A3 | 砍三成 | 用面面俱到代替立场 |
| A4 | 加反例 | 自我印证的论证 |
| A5 | 换论证关系 | 没有真实关系的第一第二第三 |
| A6 | 注入不可替换的细节 | "很多企业""显著提升" |
| B7 | 长短手术 | 句长均匀 |
| B8 | 拆排比 | 三项并列、比喻连排 |
| B9 | 插入语与自我修正 | 一路顺滑 |
| B10 | 换视角 | 只换同义词、指纹原样保留 |
| B11 | 去连接词依赖 | 段首的"此外/然而" |
| C12 | 建立个人偏科 | 用词过于均衡 |
| C13 | 降形容词密度 | "非常重要""显著地" |
| C14 | 术语精度 | 抽象词堆叠 |

带反例正例的全文：[`rewrite-moves.md`](skills/human-voice/references/rewrite-moves.md)（中文）· [`en-writing-guide.md`](skills/human-voice/references/en-writing-guide.md)（英文）。

## 仓库结构

```
ai-patina/
├── README.md · README.zh-CN.md
├── CHANGELOG.md · LICENSE · Makefile
├── .github/workflows/ci.yml          # 测试、JSON 契约、仅标准库检查
├── docs/
│   ├── cli.md                        # 参数、退出码、JSON schema
│   ├── roadmap.md                    # v1.1 为什么长这样
│   └── ai-text-detection-landscape.md
├── examples/                         # 中英各一组改前/改后样本
├── tests/test_humanity_check.py      # 42 个用例，标准库 unittest
└── skills/human-voice/
    ├── SKILL.md                      # 技能主体：边界、审计、工作流
    ├── references/
    │   ├── cli.md                    # 四条命令覆盖全部工作流
    │   ├── rewrite-moves.md          # 14 个动作，中文示例
    │   ├── en-writing-guide.md       # 同一套方法，英文示例 + 英文痕迹
    │   ├── traces-checklist.md       # S4 清扫 + 正式文体豁免表
    │   ├── voice-profile.md          # 六维声音提取，8 种原型
    │   ├── detector-model.md         # 检测原理，改到什么程度够
    │   └── before-after.md           # 三个完整改写案例
    └── scripts/humanity_check.py     # 自查脚本，仅标准库，不给分数
```

## 开发

```bash
make test        # python -m unittest discover -s tests -v
make compare     # 中文样本的差值表
make compare-en  # 英文样本
make blockers    # 退出码 2，CI 契约
```

阈值只有一个地方改：`humanity_check.py` 顶部的 `GENRES` 表。改一个数字，finding、对比行、测试会一起变。

设计取舍与刻意没做的事：[`docs/roadmap.md`](docs/roadmap.md)。

## 设计原则

- **是工艺，不是规避。** 降 AI 率是文本变好之后发生的事，不是反过来。
- **不给分数。** 脚本报可解释的指标，拒绝产出一个假装是测量结果的数字。
- **人味随体裁变化。** 学术文本的人味是判断锋利、可证伪，不是口语。把论文写成公众号是另一种失败。技能里有体裁表，也有正式文体的豁免表——公文的分点、论文的"综上所述"是规范要求，清了反而是破坏。
- **脚本对事实没有判断力。** 虚构引用是最强的 AI 信号，任何改写都救不了，所以查事实是独立且不可跳过的一步。
- **边界写在技能里，不只写在 README 里。** 代理运行时读得到。

## 背景

这份技能来自一次对 AI 文本检测实际原理的调研——统计特征、零样本概率方法、监督分类器、水印、元数据标识——以及证据显示哪些反制手段真的站得住。短版：改写胜过换词，结构胜过措辞，而过程证据是唯一一层谁也补不出来的东西。

见 [`docs/ai-text-detection-landscape.md`](docs/ai-text-detection-landscape.md)。

> 检测器是筛子、是罗盘，不是判决。这句话对两边都成立：分数不该成为处分依据，通过检测也不代表作品站得住。

## 许可

MIT，见 [LICENSE](LICENSE)。
