# MAIB7050 作业要求 ↔ v7 资产 对照表

> 用途：给组员和教授答疑用——说明「作业每一条要求，我们拿什么对上」。
> 配套文件：`docs/proposal.md`（提案）、`docs/plan.md`（执行计划）。
> 路径约定：凡 `public-v7/...` 开头的路径都指**外部先期仓** guard-kit-code（Zhanjian Li 课程前开发，
> 见 proposal 第 4 节申报），**不在本提交包内**；本仓对应物在第六节逐条标注。
> 状态标记：✅ 现成 / 🟡 半现成（整理即可）/ 🔴 需新做（课程项目的工作量所在）。

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

| # | 文档要求回答的问题 | v7/仓库已有 | 项目要做的 | 状态 |
|---|---|---|---|---|
| 1 | 谁用？什么决策/工作流？什么动作？ | 产品双档设计（可疑=提醒、高危=强预警、永不自动拦截） | 写清双角色：SME 财务（分流）、银行反诈（复核） | ✅ |
| 2 | 哪些结构化+文本文档源？什么局限？ | 语料 13,677 条（真实+合成，`training/artifacts/corpus.jsonl`）、盲测卷 3,600+ 行、17 卷评测基线 | 精选 ~1,000 条入池；整理 ~200 份官方文档证据库 | 🟡 |
| 3 | 哪些稳定实体放关系库？ | 概念全有：机构（白名单域名 9 家银行）、规则（三层白名单正则）、消息、判决（评测结果） | SQLite 建 8 张业务表 + FTS 检索虚表 + 数据字典 | 🔴 |
| 4 | 哪些记录用 JSON/文档建模？ | provenance 惯例（URL+日期+hash+排重守卫）是已申报的先期工作 | 官方文档原文段落+元数据整理成 JSON 证据层 | 🟡 |
| 5 | 用户怎么检索证据？ | ——（仓库无检索层） | metadata 过滤基线 + 语义检索对比 | 🔴 |
| 6 | 输出怎么展示依据？ | `mlScore`/`mlBandLabel` 输出分数+档位+大类；白名单命中是最接近"依据"的现有物（`src/radar.ts`） | verdict card：分数→命中规则→官方段落原文+链接 | 🔴 |
| 7 | 质量/隐私/血缘/失败案例/局限怎么评？ | 17 卷统一基线（`training/baseline/result-v7-public-allsets.json`）、164 个 FP 归因（`training/baseline/dump_fps.py`）、校准诚实度 ECE（`training/artifacts/metrics.json`）、合成标注+隔离池纪律、回归门（`eval_v7_allsets_local.py`） | 编制 60 例评估集；写治理节（访问分级/人工复核流程） | 🟡 |

## 三、数据硬指标对应（§1.5）

| 要求 | 对应 | 状态 |
|---|---|---|
| ≥3 个可 SQL 分析的关联实体 | 8 张业务表（institutions/rules/rule_patterns/messages/verdicts/verdict_evidence/evidence_documents/evidence_passages）+ evidence_fts 虚表，外键含 verdicts→rules、verdict_evidence→verdicts×evidence_passages | 🔴 建表 |
| ≥50 条短文本 或 20 份文档 | 短文本 13k+（远超）；文档侧依赖先期抓取成果 | ✅ |
| 结构化×非结构化逻辑关联 | 关联键现成：白名单命中域名→机构表→该机构官方文档；topType→骗术大类→对应官方解读 | 🟡 接线 |
| 来源合规（来源/许可/访问日期记录；LLM 生成数据只作补充且明确标注） | synthetic 标签+隔离池惯例现成；LLM 行需补「模型名+prompt 家族」字段 | 🟡 |

## 四、最低实现能力对应（§1.6，七项缺一不可）

| 能力 | 文档要求 | v7 对应 | 状态 |
|---|---|---|---|
| 关系数据管理 | schema+键+关系+数据字典+代表性 SQL | 表内容现成（规则表可从 `src/radar.ts` 白名单直接生成） | 🔴 |
| 文档/文本管理 | JSON 结构+元数据+保留源证据 | 抓取管线与去重守门是先期工作 | 🟡 |
| 检索 | 能跑的关键词/元数据/语义/混合 | 无 | 🔴 |
| 有据输出 | 结果标明依据记录/段落（证据强制，LLM 答案可选） | 分数输出现成，证据引用待接 | 🔴 |
| 集成与血缘 | 源→转换→存储→查询全链路可复现 | 现成全套：parity.json → golden-vectors → sync-weights → verify-ml → 基线回归，`scripts/sync-weights.py` + `training/verify/verify-ml.ts` | ✅ |
| 治理 | 真实的所有权/访问/隐私/人工复核决策 | 双档不自动拦截、融合层人工兜底、盲卷只读纪律、ECE 校准表；引擎无生成式组件（干净） | 🟡 |
| 评估 | 代表性+困难用例、expected vs observed | 17 卷基线 + FP 三类归因 + 红线测试方法；困难案例现成（如盲卷 W12-N16「假借钱测警觉性」、对话类/广告类 FP、白名单冲突案例） | 🟡 |

**marker 查验路径**（§1.6 硬要求：至少一条完整路径可亲手跑通）：
贴入一条可疑短信 → `mlScore` 打分落库 → 判决卡显示分数/档位/命中规则 → 点击依据展示官方文档原文段落+URL+抓取日期 → 升级动作生成带证据的案件记录。demo 用本地 npm 包跑，另录兜底视频。

## 五、交付物与评分对应（§2.8/§2.9）

| 交付物/评分项 | 分值 | 我们的底子 |
|---|---|---|
| 业务问题与产品边界 | 10 | 双角色+双错成本论证已写进提案 v2；补统计数字即可 |
| 数据源质量与治理 | 10 | provenance 惯例+合成标注+隔离池现成，等于白捡 |
| 数据架构与建模 | 15 | 表设计新做，但实体/关系/字段全部有真实来源可讲 |
| 实现与集成 | 15 | 引擎接入半天；库+判决管线 1-2 周 |
| 检索、证据与评估 | 15 | 检索新做；评估材料现成度全场最高（基线+归因+校准） |
| 报告 | 10 | 基线表格/归因/取舍论证可直接进报告 |
| 展示答辩 | 10 | 现场调 `mlScore`+多轮对话检测是强 demo；答辩预设问题（证据冲突怎么办/检索失败怎么办）有真实答案（三重条件+BAD_URL 守卫+人工兜底） |
| 个人反思 | 15 | 每人自己写，分工从第一天记贡献记录 |

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
| 数据包交接说明 | **本仓** `DATA-HANDOFF.md`（25 份证据文档 + 消息池溯源与标注政策） |

## 七、缺口清单（= 项目全部工作量）

1. 🔴 SQLite 库 + 数据字典 + 灌数（~2-3 天）
2. 🔴 证据库 200 份整理 + 来源登记（~1 周，体力活可两人分担；先确认先期抓取成果在哪）
3. 🔴 检索层（metadata 基线 + 语义对比，~4-5 天）
4. 🔴 verdict card + demo（~3 天）
5. 🟡 60 例评估集编制 + 治理文档 + 报告（~1 周，素材大半现成）

## 八、诚实备注（答辩前自己先知道）

- 抓取管线与 ~5,000 fragments 证据成果是**申报的先期工作，不在 public-v7 仓里**——立项前要确认它的位置和可用性。
- 引擎基线数字对应已发布的 `@7.0.0`；本地有一个未发版的误报优化（白名单 v4，误报 -24%），课程项目默认 pin @7.0.0；若要用新版本需先走发版流程（见 plan 的决策清单）。
- 打分引擎是 n-gram 确定性模型：老骗术近乎满分（n 系卷召回 100%），2025 新骗术有召回缺口（cd2025 84.2%）——这个局限要**主动写进评估节**，是被文档明确奖励的「recognition of limitations」。
