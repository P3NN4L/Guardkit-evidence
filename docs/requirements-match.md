# MAIB7050 作业要求 ↔ 资产 对照表（完工版 · 2026-09-29）

> 用途：给组员和教授答疑用——说明「作业每一条要求，我们拿什么对上」。
> 配套文件：`docs/proposal.md`（提案）、`docs/plan.md`（执行计划）、`docs/requirements-compliance.md`（Guideline 原文逐条对照）。
> 路径约定：凡 `public-v7/...` 开头的路径都指**外部先期仓** guard-kit-code（Zhanjian Li 课程前开发，
> 见 proposal 第 4 节申报），**不在本提交包内**；本仓对应物在第六节逐条标注。
> 状态标记：✅ 已完成并验证 · 🟡 部分完成（余量明确）。
> 本表已从「立项规划版」更新为「完工版」——早期版本里大量 🔴 的条目均已完成，状态以本版为准。

---

## 一、选题方向（guidelines §1.3）

课程给 A-G 七个方向选一个：

| 方向 | 内容 |
|---|---|
| A | 客户与服务智能（投诉/客服对话） |
| B | 产品与质量智能（评论/维修/预警） |
| C | 客户 360 与挽留 |
| D | 运营与案件排序 |
| **E** | **风险合规与升级：交易/事件 + 政策/报告 →「基于证据的分流产品，把案件转人工复核」** |
| F | 组织知识与政策检索 |
| G | 自拟（要求不减） |

**我们选 E**。E 的官方示例句 "an evidence-based triage product that routes cases for human review" 与本项目形态（可疑支付消息 → 打分/提醒/升级人工，全程带证据）几乎逐字吻合。唯一需要论证的偏差：官方示例偏银行场景，我们把主用户定为中小企业财务人员（银行已有成套反诈体系、无采纳故事；SME 是商务骗案重灾区且无工具可用），银行作为复核方+证据源保留在故事里。

## 二、七要素逐条对应（guidelines §1.2，所有项目的公共模型）

| # | 文档要求回答的问题 | 我们拿什么对上 | 状态 |
|---|---|---|---|
| 1 | 谁用？什么决策/工作流？什么动作？ | 双角色已写进提案 §1（SME 财务=分流、银行反诈=复核）；动作=放行/核实/升级；永不自动拦截 | ✅ |
| 2 | 哪些结构化+文本文档源？什么局限？ | **包内**：105 条真实标注消息 + 25 份证据文档（`data/`，来源/标注政策见 DATA-HANDOFF）。**先期**：语料 13,677 条与盲测卷在申报的外部仓（不入包，边界已申报）。局限如实写：真实文本占比、2025 新骗术召回缺口 | ✅ |
| 3 | 哪些稳定实体放关系库？ | SQLite **8 张业务表 + FTS5 虚表**已建成并灌数（外键含 verdicts→rules、verdict_evidence→verdicts×evidence_passages）；数据字典 `docs/data-dictionary.md` | ✅ |
| 4 | 哪些记录用 JSON/文档建模？ | 证据层 JSONL 已建成：逐字段落+元数据（URL/日期/hash/license/类别/PII 状态） | ✅ |
| 5 | 用户怎么检索证据？ | FTS5 + BM25（bigram 索引）+ 文档级聚合已落地，`retrieval_method` 字段落库；embedding 经论证无正当增量（`docs/design.md` §4） | ✅ |
| 6 | 输出怎么展示依据？ | 判决卡已建成：分数→命中规则→官方段落原文+链接+抓取日期；**判决↔依据由 `verdict_evidence` 外键保证**（142 行） | ✅ |
| 7 | 质量/隐私/血缘/失败案例/局限怎么评？ | 治理字段（PII 管线/审计链/复核字段）已建；评估池 108 条带真值+交叉表；**60 例评估集成稿待做** | 🟡 |

## 三、数据硬指标对应（§1.5）

| 要求 | 对应 | 状态 |
|---|---|---|
| ≥3 个可 SQL 分析的关联实体 | 8 张业务表 + FTS 虚表，外键链完整（`PRAGMA foreign_key_check` 零违规） | ✅ |
| ≥50 条短文本 或 20 份文档 | **包内即达标：108 条消息 + 27 份文档**（全真实、逐条溯源），不依赖外部语料 | ✅ |
| 结构化×非结构化逻辑关联 | `verdict_evidence` 桥表：84 条判决 SQL 可溯源到具体官方段落 | ✅ |
| 来源合规（来源/许可/访问日期记录；LLM 生成数据明确标注） | URL+日期+hash 全有；license 25/27（余 2 份 seed 待补页脚）；`synthetic_derived`/`generation` 字段隔离标注（当前全 0=全真实） | ✅ |

## 四、最低实现能力对应（§1.6，七项缺一不可）

| 能力 | 文档要求 | 我们拿什么对上 | 状态 |
|---|---|---|---|
| 关系数据管理 | schema+键+关系+数据字典+代表性 SQL | schema+外键 ✅、`docs/data-dictionary.md` ✅、`docs/queries.sql` 六组业务 SQL ✅ | ✅ |
| 文档/文本管理 | JSON 结构+元数据+保留源证据+成文的准备决策 | JSONL 证据层 ✅；准备决策见 DATA-HANDOFF 与 build_db 注释（采集门控/PII 口径/hash） | ✅ |
| 检索 | 能跑的关键词/元数据/语义/混合 | FTS5+BM25+文档聚合，运行于 108 判决（142 条依据连接） | ✅ |
| 有据输出 | 结果标明依据记录/段落（证据强制） | 判决卡引用官方段落原文+URL+日期；verdict_evidence 落库 | ✅ |
| 集成与血缘 | 源→转换→存储→查询 + 版本/运行说明可复现 | README 四条命令 + 血缘图（design.md）+ **确定性重建实测（8 表逻辑逐行一致）** + parity 守门 | ✅ |
| 治理 | 真实的所有权/访问/隐私/人工复核决策 | PII 扫描脱敏管线（字段级计数）、白名单审计链（原始分留档）、永不自动拦截、复核字段 | ✅ |
| 评估 | 代表性+困难用例、expected vs observed | 交叉表现成（scam 召回 40/43）+ 漏报/误报逐条归因 + 困难案例（W12-N16 对话类等）；**60 例成稿待做** | 🟡 |

**marker 查验路径**（§1.6 硬要求：至少一条完整路径可亲手跑通）：
`python3 src/build_db.py` → `python3 src/run_demo.py` → 判决卡显示分数/档位/命中规则 → 依据展示官方段落原文+URL+抓取日期（verdict_evidence 可 SQL 溯源）→ 高危升级人工。
或打开 `GuardKit_Evidence.ipynb` 分步走同一路径（输出已内嵌）。外部复核（reviews/FINAL-CHECK）已按此路径完整复现一次。

## 五、交付物与评分对应（§2.8/§2.9）

| 交付物/评分项 | 分值 | 现状 |
|---|---|---|
| 业务问题与产品边界 | 10 | 双角色+双错成本已论证；补统计数字占位符即可 |
| 数据源质量与治理 | 10 | 来源登记+license+PII 管线+生成标注全齐 |
| 数据架构与建模 | 15 | 8 表+FTS5 已建成，ERD/血缘图已出（design.md） |
| 实现与集成 | 15 | 端到端四条命令跑通；确定性重建已实测 |
| 检索、证据与评估 | 15 | 检索+证据链已落地；评估交叉表现成；60 例成稿待做 |
| 报告 | 10 | 素材全齐（design/queries/walkthrough/复现表），**本体待写** |
| 展示答辩 | 10 | 判决卡 live demo + walkthrough 动线；slides/录屏待做 |
| 个人反思 | 15 | 各人自办 |

## 六、现成弹药清单（报告/演示直接引用）

> `public-v7/...` = 外部先期仓 guard-kit-code（不在提交包）；其余为本仓路径。

| 材料 | 位置 |
|---|---|
| 17 卷统一评测基线 | **本仓** `evaluation/baseline-v7-public-allsets.json`（外部源：`public-v7/training/baseline/result-v7-public-allsets.json`） |
| 本地回归门（召回下降即 fail） | 外部仓 `public-v7/training/baseline/eval_v7_allsets_local.py`（本仓由 `tests/test_parity.py` 承担快照一致性守门） |
| 164 个误报全量归因（对话类/广告类/单一类） | **本仓** `evaluation/fp-attribution.md` + `.json`（外部工具：`public-v7/training/baseline/dump_fps.py`） |
| 白名单三重条件设计取舍 | **本仓** `engine/scorer.py`（v7 pinned 快照，注释即 `public-v7/src/radar.ts` 对应物）+ `V7-HANDOFF.md §十`（外部仓） |
| 校准诚实度（ECE+可靠性表） | 外部仓 `public-v7/training/artifacts/metrics.json`（数字已进本仓文档，引用时注明外部源） |
| Python↔TS 一致性守门（110 条 parity） | **本仓** `tests/test_parity.py`（外部对侧：`public-v7/training/verify/verify-ml.ts`） |
| 六端黄金向量自检 | 外部仓 `public-v7/spec/golden-vectors.json` + dart/swift/kotlin/miniprogram tests |
| 打分引擎（npm 包） | `@p3nn4l/guard-kit@7.0.0`（guard-kit-code 公开仓；本仓以 `engine/scorer.py` + `models/radar.json` pinned 快照消费） |
| 代表性业务 SQL | **本仓** `docs/queries.sql` |
| 数据包交接说明 | **本仓** `data/DATA-HANDOFF.md`（证据文档 + 消息池溯源与标注政策） |
| ERD/血缘/合规矩阵/数据字典/来源登记 | **本仓** `docs/design.md` · `docs/requirements-compliance.md` · `docs/data-dictionary.md` · `data/source-register.csv` |
| 课程交付 notebook | **本仓** `GuardKit_Evidence.ipynb`（全流程分步演示，输出内嵌） |
| 三份外部独立复核 | **本仓** `external-reviews/`（初轮复核 7 项 → 行动项 → 端到端复现验证） |

## 七、工作量状态（原「缺口清单」完工对照）

**已完成（原清单 1–4 项全部落地）**：
1. ✅ SQLite 库 + 数据字典 + 灌数（8 表 + FTS5，108 消息/27 文档）
2. ✅ 证据库：25 份真实文档带完整溯源 + 来源登记表 + 5 条爬取 BEC 补充（目标 200 份为愿景值，课程门槛 20 已达标）
3. ✅ 检索层：FTS5+BM25+文档聚合（embedding 经论证不采用，design.md §4）
4. ✅ verdict card + demo：判决卡三张 + HTML + notebook 全流程

**剩余（= 提交前最后一段路）**：
5. 🟡 60 例评估集成稿（池子现成）+ 治理文档成稿 + **报告英文 10 页**（素材全齐）
6. 🔴 Slides + demo 兜底视频 + 各人反思 + 提案占位符填实（GroupID/成员/统计/AI 工具名）

## 八、诚实备注（答辩前自己先知道）

- 抓取管线与证据成果的位置已确认：本仓 `data/` 即其导出子集（见 DATA-HANDOFF）；全量成果仍在私有仓，边界已在 proposal §4 申报。
- 引擎基线数字对应已发布的 `@7.0.0`；本地有一个未发版的误报优化（白名单 v4，误报 -24%），课程项目默认 pin @7.0.0；若要用新版本需先走发版流程（见 plan 的决策清单）。
- 打分引擎是 n-gram 确定性模型：老骗术近乎满分（n 系卷召回 100%），2025 新骗术有召回缺口（cd2025 84.2%）——这个局限要**主动写进评估节**，是被文档明确奖励的「recognition of limitations」。
- 复现口径（答辩被追问时用）：**确定性重建 = 逻辑内容逐行一致（8 表全量、含 142 条证据连接）+ 文件大小一致（204,800 B）**；字节级差异仅来自判决时间戳与 SQLite 页头计数器——不要说"逐字节一致"。
