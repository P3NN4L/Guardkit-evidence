# GuardKit Evidence — MAIB7050 Group Project

> MAIB7050 · Business Data Management for AI · Direction E (Risk Compliance and Escalation)
> **GuardKit Evidence** — an evidence-grounded screening data product for suspicious payment messages in Hong Kong.

一个可查验（working & checkable）的数据产品原型：**一条可疑支付消息 → 打分 → 判决卡（分数/命中规则/官方依据原文）→ 升级人工复核**。

## 30 秒跑通

```bash
python3 src/build_db.py      # 建 SQLite 库（8 张业务表 + FTS5 虚表）+ 灌数（data/ 数据包 + 种子）
python3 src/run_demo.py      # 全量消息打分落库 → 演示判决卡（CLI）+ demo/verdict_cards.html
python3 tests/test_parity.py # 一致性守门：包内快照向量必过（PASS 5/5）+ 本机有 public-v7 仓时另做训练侧强校验
sqlite3 guardkit_evidence.sqlite < docs/queries.sql   # 代表性业务 SQL（可追溯输出/评估交叉表）
open demo/verdict_cards.html # 浏览器看产品形态（生成产物，重跑 run_demo.py 即刷新）
```

仅需 Python 3 标准库（sqlite3，含 FTS5），无第三方依赖。

**偏好 notebook？** `GuardKit_Evidence.ipynb` 是四条命令的**分步等价物**（§1.6 允许的交付形态）：建库 → 打分原理 → 检索 → 判决卡（内嵌 HTML）→ 业务 SQL → 评估交叉表 → 复现性守门，叙述与输出已全部内嵌，jupyter/colab 打开即读。

> **唯一产品数据库：`guardkit_evidence.sqlite`**（由 `src/build_db.py` 从 `data/*.jsonl` + 种子重建）。
> `data/guardkit_course.db` 是数据包交付时的三表快照，**不是**产品库——判分请以上述库为准。

## 仓库结构

```text
GP/
├── README.md                  ← 本文件（跑通步骤 + 数据字典要点 + 诚实声明）
├── GuardKit_Evidence.ipynb    ← 课程交付 notebook（四条命令的分步等价物，输出已内嵌）
├── guardkit_evidence.sqlite   ← 唯一产品数据库（由 build_db.py 重建）
├── src/                       ← 源代码
│   ├── build_db.py            建库灌数（8 表 + FTS5；PII 扫描 + 硬门槛自检）
│   ├── run_demo.py            全量打分 → 白名单 → 检索 → 判决+证据落库 → 判决卡
│   ├── textproc.py            共享文本处理（bigram / FTS token / PII 扫描）
│   └── seed_evidence.json     证据种子（警务处 + HKMA 逐字引用，带 hash）
├── engine/ + models/          ← 打分引擎（pinned 依赖 @7.0.0，只读不修改）
├── data/                      ← 数据包与登记
│   ├── messages.jsonl         105 条真实标注消息（100 数据包 + 5 爬取 BEC）
│   ├── evidence_documents.jsonl  25 份证据文档（全文 + 溯源 + license）
│   ├── source-register.csv    来源登记表（§2.4 交付物）
│   ├── institutions.json      机构注册表
│   ├── DATA-HANDOFF.md        数据包交接说明（来源/标注政策/真实性核查）
│   ├── MESSAGES-SPEC.md       消息取数规格
│   └── guardkit_course.db     交付时的三表快照（非产品库，仅存档）
├── docs/                      ← 全部项目文档
│   ├── proposal.md            提交用提案（Moodle 1 页版）
│   ├── match.md               作业要求 ↔ 资产逐条对照
│   ├── plan.md                执行计划（里程碑/分工/checklist）
│   ├── design.md              ERD + 架构/血缘视图（§2.4 设计产物）
│   ├── data-dictionary.md     数据字典（§1.6/§2.4 交付物）
│   ├── compliance-matrix.md   Guideline 原文逐条合规对照
│   ├── queries.sql            六组代表性业务 SQL
│   ├── walkthrough.md         答辩走讲（开场/动线/数字表/Q&A）
│   ├── theory-primer.md       原理揉碎版（每个概念讲为什么）
│   ├── pitch-to-team.md       组员说服材料（评分对分 + 疑虑拆解）
│   └── pitch-and-defense.md / study-guide.md   组员学习与答辩手册
│   └── assets/                erd.png / lineage.png（设计图渲染版）
├── external-reviews/          ← 三份外部 AI 独立复核（2026-09-29）
│   ├── EXTERNAL-REVIEW-2026-09-29.md      初轮复核（发现 schema 断层等 7 项）
│   ├── ACTION-ITEMS-2026-09-29.md         收尾行动项（ERD/两库合一/评估集）
│   └── FINAL-CHECK-2026-09-29.md          端到端复现验证（确定性实测）
├── tests/
│   └── test_parity.py         一致性守门（快照向量 PASS 5/5 + 可选训练侧对拍）
│   └── fixtures/              快照完整性向量
├── evaluation/                17 卷基线 + 164 条误报归因（评估节素材）
└── demo/
    └── verdict_cards.html     三张演示判决卡（生成产物，重跑即刷新）
```

## 新组员上手：按这个顺序读（第一天就能完成）

| 步骤 | 读/做什么 | 时间 | 读完你能 |
|---|---|---|---|
| **0. 先跑一遍** | 上面「30 秒跑通」四条命令（或直接开 `GuardKit_Evidence.ipynb` 看内嵌输出） | 10 分钟 | 有体感：消息进、判决卡出、依据可点 |
| **1. 它在干什么** | `docs/study-guide.md`（四节课：场景 → 数据组织 → 证据检索 → 怎么讲） | 40 分钟 | 用大白话讲清项目；每课末尾有检查问题 |
| **2. 为什么这样设计** | `docs/theory-primer.md`（每个概念揉碎：是什么/为什么/怎么做的/答辩一句话） | 40 分钟 | 被追问一层也不慌 |
| **3. 看结构** | `docs/design.md` 两张图（ERD + 血缘）→ `docs/queries.sql` 逐条跑 | 20 分钟 | 指着图讲数据流；SQL 每条回答什么业务问题 |
| **4. 答辩怎么走** | `docs/walkthrough.md`（30 秒开场 / 演示动线 / 必记数字 / 预设 Q&A） | 20 分钟 | 背下开场白和 7 个必记数字 |
| **按需** | 说服别人：`docs/pitch-to-team.md` + `docs/pitch-and-defense.md`；要求对照：`docs/match.md` + `docs/compliance-matrix.md`；分工与待办：`docs/plan.md`；数据从哪来：`data/DATA-HANDOFF.md`；外部复核说了什么：`external-reviews/` | 按需 | 各自场景够用 |

**给每个人的底线要求**（§2.1 原文："all members must understand the full data product and be ready to explain it"）：
① 会跑四条命令并解释输出；② 能讲 §0 的三十秒开场；③ theory-primer 九节里自己工作包相关的那几节能答"为什么"。
写报告/反思所需的背景全在上面路径里，不需要读代码——`src/*.py` 是已固化的实现，懂到"每个脚本一句话干什么"即可（notebook 注释里都写了）。

## 数据字典（要点）

- **来源标注 `messages.source`**：约定 `<set>:<id>`（如 `blind-set:blind-n200:N200-N07`、`v3-mixed:v3scam_mixed_20`、`demo:written:MSG-001`）。
- **生成标签**：`messages.synthetic_derived`（1=含 LLM 生成成分）+ `messages.generation`（real / llm_rewrite_v3_blind / human_written_demo…）——对应课程 AI/生成数据申报。
- **机构双标志**：`institutions.whitelist_flag`=官方域名命中引擎 R-DOMAIN 白名单（HKMA/HKPF/HKGOV 及发件银行=1）；`evidence_authority`=官方证据来源机构（监管/警务/政府=1）。
- **审计链**：`verdicts.score_raw_before_rule` 保留白名单压档前的引擎原始分（NULL=无规则介入）；`verdict_rule_id` 外键到 `rules.id`，可用 SQL 查「哪条规则介入过哪个判决」。
- **可追溯输出**：`verdict_evidence` 把每个判决与其依据段落（`evidence_passages.id`）+ 检索方法/得分落库——Element 6 由 schema 保证，`docs/queries.sql` Q1 可复现。
- **accessed_at 注**：gov_press 类文档源 schema 以 content_date 为主溯源（harvested_at 为空），此时 `accessed_at` 回落记录 content_date。

## 三张判决卡演示的三个设计点

1. **MSG-001 冒充供应商换账户 → 高危 → 升级人工**：证据精确命中警务处原文「供應商聲稱更換付款賬戶，必須先聯絡對方已知舊有聯絡方式確認」——判决与依据均落库（verdict_evidence），输出可溯源（Element 6）。
2. **MSG-002 银行账单通知（真实盲测卷样本）→ 命中机构通知白名单 → 放行**：三重条件（主题×官方渠道×无可疑链接）压档，压档前原始分留档——明确的数据治理取舍（Element 7）。
3. **MSG-003 假借钱对话（已知困难案例，引擎误报）→ 高危 → 人工复核**：引擎有已知盲区，但工作流把结论交给人而非自动拦截——「triage → human review」的安全垫，评估将如实报告。

## 边界（诚实声明）

- **包内规模**：本提交包内证据文档 **27 份**（≥20 ✅）、标注消息 **108 条**（≥50 ✅）——其中 105 条来自 `data/messages.jsonl`（**全部真实文本**，`synthetic_derived=0`：数据包 100 条 + 爬取真实 BEC 邮件 5 条（`public-nazario`，带溯源），构成见 `data/DATA-HANDOFF.md`），3 条为演示/盲测卷样例；重建后以 `build_db.py` 输出为准。
- 打分引擎是确定性 n-gram 模型（无生成式组件）：老骗术近乎满分，2025 新骗术存在召回缺口（v7 全卷基线 `recall 84.2%`），将作为已知局限写入评估。
- 检索层为 FTS5 + BM25（CJK 字符 bigram 索引，排序/过滤在 SQL 内完成）；embedding 是否「justified value」按 `docs/plan.md` WP3 做对比评估后如实报告。
- **PII 处理**：证据段落摄取时经扫描脱敏（个人邮箱/电话/证件号；公司客服热线与公共角色邮箱按治理口径保留原文），命中数记录在 `evidence_documents.pii_redactions`；消息只计数不改动（`messages.pii_hits`，文本须逐字保留供打分）。证据文档 license 备注已随数据包补录（25/27，余 2 份 seed 待从页面页脚补）。
- 本仓不存储任何真实用户消息；消息样本为演示撰写或团队盲测卷内容（来源标注于 `messages.source`）。
- 先期工作申报：评分引擎、语料与评测基线由组员 Zhanjian Li 在课程开始前开发（公开仓 P3NN4L/guard-kit-code），本仓以 pinned 依赖消费，不属于本课程被评估的贡献。
