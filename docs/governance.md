# Governance · 治理文档

> 每个机制都落到字段/流程/可跑 SQL，不写与本项目无关的泛泛伦理声明。
> 九要素索引：Ownership→§1 · Privacy→§2 · Human review→§3 · Lineage→§4 · Quality→§5 · Access→§6 · Constraints/Unresolved risks→§7 · Inappropriate uses→§3+§8 · 变更方法论→§8。

## 1. 所有权与角色（Ownership）

| 层 | 谁负责 | 载体 |
|---|---|---|
| 数据产品层（库/检索/判决/评估/治理） | 全组 | `src/`、`docs/`、`evaluation/` |
| 评分引擎 | Zhanjian Li 的先期工作（GuardKit 项目）——本仓库以 **pinned 依赖**消费，代码不修改 | `engine/scorer.py` + `models/radar.json` + `tests/test_parity.py` 守门 |
| 证据数据 | 数据侧交付（`data/DATA-HANDOFF.md` 溯源）+ 代码侧摄取管线 | `data/source-register.csv`（doc_id→institution→source_url→license 逐行可查）；原文不随公开仓库分发 |

SQL 复核：`docs/queries.sql` **Q5** 各机构证据覆盖（`institutions × evidence_documents × evidence_passages` 一条 SQL 出全部归属计数）。

## 2. 隐私与 PII（Privacy）

**机制而非声明**——摄取管线（`src/textproc.py` 三种 PII 模式与 `pii_redact`；`src/build_db.py` 证据脱敏 / 消息计数）在入库时自动执行：

| 对象 | 处理 | 落库字段 |
|---|---|---|
| 个人邮箱 / 香港身份证号 / 个人电话（852 前缀、4+4、上下文词三形态） | 证据段落：脱敏（保留前 2 字符+***）；消息：只计数不改动（打分需逐字原文） | `evidence_documents.pii_scan / pii_redactions`；`messages.pii_hits` |
| 公司客服热线 / 公共角色邮箱（info@ 等） | **保留原文**——官方通告的正式内容（建议动作就是拨打），脱敏反而破坏"逐字引用" | 同上（治理口径白名单：`src/textproc.py`） |
| 真实用户消息 | 不存储——消息池全部来自团队盲测卷、公开通告与公开语料（Nazario honeypot），逐条带来源标注 | `messages.source`（`<集合>:<ID>`） |

当前实测（SQL 可复算）：`SELECT COALESCE(SUM(pii_redactions),0) FROM evidence_documents;` → **0**（27 份证据本批内容干净）；`SELECT COALESCE(SUM(pii_hits),0) FROM messages;` → **2**（消息侧疑似命中只计数、文本逐字保留）。

公开仓库层面的处理：消息原文与证据全文都不入库到公开仓库——消息原文含公开语料里的第三方个人信息，证据全文归发布机构版权所有。公开仓库只保留来源登记（`data/source-register.csv`）与说明文档。

## 3. 人工复核与自动化边界（Human-in-the-loop / Inappropriate uses）

- **永不自动拦截**：产品的最高风险动作是"升级人工"，不存在自动阻断/代付/撤回路径。依据：误拦真付款与漏放骗局的代价不对称，机器初筛 + 人做最终决定（triage-then-review）。**不当使用边界同源**：本产品禁止用于自动风控决策；营销/广告语料不得借白名单机制"洗白"（见 §8 三道关第①关）。
- **升级路径**：判决 band=high → 案件转人工复核队列，复核人/时间留痕（`verdicts.reviewed_by / reviewed_at`，当前为空=演示库未走真实复核）。
- **明知误报的展示**：判决卡③（MSG-003 假借钱对话）主动演示已知误报→人工兜底；评估集失败案例全部保留并归因（`evaluation/60cases.csv` + `evaluation/fp-attribution.md`），不做选择性隐藏。

## 4. 可审计性（Auditability / Lineage）

| 机制 | 字段/文件 | 回答的问题 |
|---|---|---|
| 白名单压档审计链 | `verdicts.score_raw_before_rule` + `verdict_rule_id` | "规则介入前引擎原始分多少？哪条规则介入？"（`docs/queries.sql` **Q3/Q4**） |
| 判决↔证据连接 | `verdict_evidence`（rank/method/score，外键） | "这个判决的依据是哪段原文？"（**Q1** 一条 SQL 溯源） |
| 证据快照 | `source_url + accessed_at + content_hash`（sha256 前 16 位，由 `src/build_db.py` 生成）+ `license` | "证据从哪来、抓取时内容是否被改过？" |
| 引擎血缘 | `model_id + model_version`（pinned @7.0.0）+ parity 快照向量（`tests/fixtures/snapshot-vectors.json`，容差 1e-9） | "这个判决用的哪个引擎版本？引擎被改过吗？"（PASS 5/5 守门） |
| 数据生成标注 | `messages.synthetic_derived / generation` | "哪些数据是生成的？"（当前全部 real=0） |

## 5. 数据质量与保留（Quality & Retention）

- **不删除**：被取代的证据版本保留（superseded 保留策略）；演示消息（demo:*）不删除但**从评估集排除**（`evaluation/build_60cases.py` 代码级保证，确定性抽取重跑结果不变）。
- **规模自检**：`src/build_db.py` 末尾打印证据文档与消息数量（当前 27 文档 / 108 消息）；`SELECT COUNT(*)` 两句即可复算。
- **确定性可复现**：同样输入 → 重建库 8 表逻辑逐行一致、大小一致（字节差异仅判决时间戳）——经独立的端到端复现验证。
- **检索失败处置**：无足够相关依据时如实显示"未检索到"，不硬凑（108 判决三分账：84 证据 + 12 规则放行 + 12 如实无检索）。

## 6. 访问与仓库卫生（Access & repository hygiene）

- 单文件本地 SQLite，无网络服务层暴露；证据原文的版权归发布机构，使用范围见 `data/source-register.csv` 的 license 注记。
- 仓库不含凭据/私钥；消息原文与证据全文因隐私与版权原因不随公开仓库分发（见 README 的 Data 一节）。

## 7. 已知局限与未解风险（Constraints / Unresolved risks · 如实申报）

- 引擎 n-gram 确定性模型：2025 新骗术召回缺口（CyberDefender 2025 卷 recall 84.2%，17 卷合并 229/240）；对话类/广告类误报历史归因见 `evaluation/fp-attribution.md`（残差 124 = promo-ad 76 + other-noise 37 + dialogue 11，三类均为架构边界而非 bug）。
- **gov-news 暴露面（评估新发现）**：`gov-news-2026` 卷 4 条 normal 消息被判 high/medium（`evaluation/60cases.csv` 含该 4 例），且该卷不在 fp-attribution 17 盲测卷归因范围内——是否纳入机构通知白名单治理待过 §8 三道关后裁定，暂不改动。
- 证据页面天然滞后于实时骗术；gov_press 类 5 份以 content_date 为主溯源（源 schema 特性，已在数据字典注明）。
- **版权**：27 份证据文档的版权都归发布机构（HKMA Copyright Notice、HKPF Copyright Notice 等各自的版权声明），`data/source-register.csv` 的 license 列逐份记录；因此公开仓库不再分发证据原文，只保留来源链接与抓取日期。
- 演示库未接入真实复核流（reviewed_by 为空）——生产化时的接口已预留。

## 8. 白名单变更治理（变更方法论）

任何白名单扩展必须同时过三道关（`evaluation/fp-attribution.md` §五）：

1. **误放行红线**：17 卷 scam + 约 3,800 行 scam 语料零新增命中（曾以此否决「寄到」分支——它会放进冒充警务处骗局）；
2. **全卷回归**：17 卷召回逐卷与基线（`evaluation/baseline-v7-public-allsets.json`）比对，任何一卷召回下降 = 拒收；
3. **Python↔TS parity**：评分快照与训练侧 ≤1e-6（`tests/test_parity.py`）。
