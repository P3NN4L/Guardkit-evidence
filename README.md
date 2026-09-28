# GuardKit Evidence — MAIB7050 Group Project

> MAIB7050 · Business Data Management for AI · Direction E (Risk Compliance and Escalation)
> **GuardKit Evidence** — an evidence-grounded screening data product for suspicious payment messages in Hong Kong.

一个可查验（working & checkable）的数据产品原型：**一条可疑支付消息 → 打分 → 判决卡（分数/命中规则/官方依据原文）→ 升级人工复核**。

## 30 秒跑通

```bash
python3 src/build_db.py      # 建 SQLite 库（8 张业务表 + FTS5 虚表）+ 灌数（data/ 数据包 + 种子）
python3 src/run_demo.py      # 全量消息打分落库 → 演示判决卡（CLI）+ demo/verdict_cards.html
python3 tests/test_parity.py # 一致性守门（本机有 public-v7 仓时强校验，否则跳过）
sqlite3 guardkit_evidence.sqlite < docs/queries.sql   # 代表性业务 SQL（可追溯输出/评估交叉表）
open demo/verdict_cards.html # 浏览器看产品形态（生成产物，重跑 run_demo.py 即刷新）
```

仅需 Python 3 标准库（sqlite3，含 FTS5），无第三方依赖。

## 仓库结构

| 路径 | 内容 |
|---|---|
| `src/build_db.py` | 建库灌数：institutions / rules / rule_patterns / messages / verdicts / verdict_evidence / evidence_documents / evidence_passages + evidence_fts（FTS5 检索虚表）；含 PII 扫描与硬门槛自检 |
| `src/run_demo.py` | 核心路径：全量打分 → 白名单压档（保留原始分）→ FTS5/BM25 证据检索 → 判决+证据连接落库 → 演示判决卡（CLI + HTML） |
| `src/textproc.py` | 共享文本处理：规范化 / bigram / FTS token 串 / PII 扫描（索引侧与查询侧同一实现） |
| `src/seed_evidence.json` | 证据种子：真实官方页面逐字引用（警务处《商業電郵騙案》2026-01-16、HKMA《Beware of Fraudsters!》），带原文链接+抓取日期+内容 hash |
| `data/` | GP 数据包：25 份真实证据文档 + 标注消息池（来源/标注政策见 `DATA-HANDOFF.md`；消息取数规格见 `data/MESSAGES-SPEC.md`） |
| `engine/scorer.py` | guard-kit v7 评分组件的 **pinned 快照**（只读依赖，本仓不修改） |
| `models/radar.json` | v7 现役权重（= 公开 npm 包 `@p3nn4l/guard-kit@7.0.0` 的模型文件） |
| `tests/test_parity.py` | 快照 ↔ v7 训练侧评分器逐位一致守门 |
| `docs/queries.sql` | 代表性业务 SQL：判决↔证据溯源、expected-vs-observed 交叉表、白名单压档审计等 |
| `docs/proposal.md` | 提交用提案（Moodle 1 页正文版） |
| `docs/match.md` | 作业要求 ↔ 资产逐条对照表 |
| `docs/plan.md` | 执行计划（里程碑/工作包/分工/风险/提交前 checklist） |
| `demo/verdict_cards.html` | 三张演示判决卡（**生成产物**，每次 `run_demo.py` 重新生成；非手写交付物） |
| `EXTERNAL-REVIEW-2026-09-29.md` | 外部独立复核报告（内部工作文档；若纳入提交包须按 §2.11 申报） |

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

- **包内规模**：本提交包内证据文档 **27 份**（≥20 ✅）、标注消息 **89 条**（≥50 ✅）——其中 86 条来自 `data/messages.jsonl`（全部真实文本，`synthetic_derived=0`，来源卷与标注政策见 `DATA-HANDOFF.md`），3 条为演示/盲测卷样例；重建后以 `build_db.py` 输出为准。
- 打分引擎是确定性 n-gram 模型（无生成式组件）：老骗术近乎满分，2025 新骗术存在召回缺口（v7 全卷基线 `recall 84.2%`），将作为已知局限写入评估。
- 检索层为 FTS5 + BM25（CJK 字符 bigram 索引，排序/过滤在 SQL 内完成）；embedding 是否「justified value」按 `docs/plan.md` WP3 做对比评估后如实报告。
- **PII 处理**：证据段落摄取时经扫描脱敏（个人邮箱/电话/证件号；公司客服热线与公共角色邮箱按治理口径保留原文），命中数记录在 `evidence_documents.pii_redactions`；消息只计数不改动（`messages.pii_hits`，文本须逐字保留供打分）。证据文档 license 备注已随数据包补录（25/27，余 2 份 seed 待从页面页脚补）。
- 本仓不存储任何真实用户消息；消息样本为演示撰写或团队盲测卷内容（来源标注于 `messages.source`）。
- 先期工作申报：评分引擎、语料与评测基线由组员 Zhanjian Li 在课程开始前开发（公开仓 P3NN4L/guard-kit-code），本仓以 pinned 依赖消费，不属于本课程被评估的贡献。
