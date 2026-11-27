# Data Dictionary · 数据字典

> 真相来源（source of truth）：schema 定义在 `src/build_db.py`，本字典由 `guardkit_evidence.sqlite` 的 PRAGMA 实测生成。
> 口径日期：2026-09-29。行数：institutions 9 · rules 3 · rule_patterns 7 · messages 108 · verdicts 108 · verdict_evidence 142 · evidence_documents 27 · evidence_passages 34。

## 值域与约定（全库通用）

| 约定 | 取值 | 说明 |
|---|---|---|
| 档位 `band` | high / medium / low | 双条件判档：`p_cal` 与 `p_raw` 同时过线才算高/可疑，否则 low |
| 期望标签 `label` | scam / normal | 人工真值（盲测卷标注），评估对照用；演示消息亦标注 |
| 来源标注 `source` | `<集合>:<ID>` | 例 `blind-set:blind-n200:N200-N07`、`v3-mixed:v3scam_mixed_20`、`public-nazario:pub-nz-2024-bec-01`、`demo:written:MSG-001` |
| 生成方式 `generation` | real / llm_rewrite_v3_blind / human_written_demo | 配合 `synthetic_derived`（1=含 LLM 成分）；当前库内 105 条消息全部 real |
| PII 状态 `pii_scan` | clean / redacted | 证据段落摄取时扫描（个人邮箱/电话/证件号脱敏；公司热线与公共角色邮箱按治理口径保留） |
| 检索方法 `retrieval_method` | fts5-bm25-docagg | FTS5+BM25（bigram 索引）+ 文档级聚合 |
| 语言 `lang` | zh-HK / zh / en / mixed | 粤语 / 普通话 / 英文 / 混合 |
| 档位阈值 | bands.mid / bands.high；RAW_MID 0.455 / RAW_HIGH 0.505 | 来自 pinned 模型文件 `models/radar.json` 与引擎常量 |

## institutions（机构注册表，9 行）— 主键 `id`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | TEXT PK | 机构标识（HKMA/HKPF/HSBC/HASE/BOCHK/CHIYU/HKCPF/HKGOV/SHACOM） |
| name | TEXT | 展示名 |
| type | TEXT | regulator / police / government / bank |
| whitelist_flag | INTEGER | 1=官方域名命中引擎 OFFICIAL_DOMAIN 白名单（R-DOMAIN 生效对象） |
| evidence_authority | INTEGER | 1=官方证据来源机构（监管/警务/政府） |
| domains | TEXT | JSON 数组：已知官方域名 |
| source_url | TEXT | 机构官网（可点开验证） |

## rules（白名单规则族，3 行）— 主键 `id`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | TEXT PK | R-NOTICE / R-DOMAIN / R-INSTITUTIONAL |
| family | TEXT | notice / domain / institutional |
| description | TEXT | 人话解释（三重条件语义） |
| pattern_summary | TEXT | 模式摘要；可审计正则见 rule_patterns |
| weight | REAL | 证据权重（演示固定值） |
| institution_id | TEXT FK→institutions.id，可空 | 归属机构（notice 族不对应单一机构） |

## rule_patterns（规则正则数据，7 行）— 主键 `id`

| 字段 | 类型 | 说明 |
|---|---|---|
| rule_id | TEXT FK→rules.id | 所属规则族 |
| pattern_name | TEXT | 引擎侧常量名（溯源 engine/scorer.py） |
| pattern | TEXT | 正则原文（由 pinned 快照投影生成，禁手改） |
| guard | TEXT | positive=命中才放行 / negative=命中即否决白名单 |
| version | TEXT | 生成时的 pinned 引擎版本 |

## messages（消息池，108 行）— 主键 `id`

| 字段 | 类型 | 说明 |
|---|---|---|
| text | TEXT | 消息原文逐字（打分输入，PII 只计数不改动） |
| lang / channel / received_at | TEXT | 语言 / sms·whatsapp·email / 时间（缺失为 NULL） |
| source | TEXT NOT NULL | 溯源 `<集合>:<ID>`（约定见上） |
| note | TEXT | 困难案例等备注 |
| label | TEXT | scam / normal（评估真值） |
| synthetic_derived | INTEGER | 1=含 LLM 生成成分（AI 申报用；当前全部 0） |
| generation | TEXT | 生成方式标签 |
| pii_hits | INTEGER | PII 疑似命中数（只计数） |

## verdicts（判决，108 行）— 主键 `id`（=`V-`+消息ID）

| 字段 | 类型 | 说明 |
|---|---|---|
| message_id | TEXT FK→messages.id | 1:1 |
| score / p_cal | REAL | 生效 pRaw / 校准分（白名单压档后） |
| band | TEXT NOT NULL | high / medium / low |
| top_type | TEXT | 骗术大类 best-guess（impersonation / pay_first / bait） |
| whitelist_rule | TEXT | 命中家族名（人读） |
| verdict_rule_id | TEXT FK→rules.id，可空 | 命中规则行（SQL 可查"哪条规则介入过哪个判决"） |
| score_raw_before_rule | REAL，可空 | 规则介入前原始 pRaw（NULL=无规则介入）——审计链 |
| model_id / model_version | TEXT | 引擎血缘（radar / v7 pinned snapshot @7.0.0） |
| created_at | TEXT | 判决时间 |
| reviewed_by / reviewed_at | TEXT，可空 | 人工复核（升级后填写） |

## verdict_evidence（判决↔证据连接，142 行）— 复合主键

| 字段 | 类型 | 说明 |
|---|---|---|
| verdict_id | TEXT FK→verdicts.id | 判决 |
| passage_id | INTEGER FK→evidence_passages.id | 被引用段落 |
| rank | INTEGER | 依据强度序（1=最强） |
| retrieval_method | TEXT | fts5-bm25-docagg |
| score | REAL | 检索相关度（-bm25，越大越相关） |

> **判决依据三分账**：108 判决 = 84 有证据落库 + 12 白名单放行（依据是规则，见 verdict_rule_id）+ 12 如实无检索（benign 闲聊，不硬凑依据）。

## evidence_documents（证据文档，27 行）— 主键 `doc_id`

| 字段 | 类型 | 说明 |
|---|---|---|
| institution_id | TEXT FK→institutions.id | 发布方 |
| title / publisher / published_date | TEXT | 页面信息（gov_press 行源 schema 以 content_date 为主溯源） |
| source_url | TEXT NOT NULL | 溯源：原文链接 |
| accessed_at | TEXT NOT NULL | 溯源：抓取日期；harvested_at 缺失时回落记录 content_date |
| lang / category / evidence_class | TEXT | 语言 / 检索语义类别 / 采集侧类别 |
| content_hash | TEXT | SHA-256 指纹（快照校验） |
| license | TEXT | 许可备注（数据包 license_note 与 seed license 映射；27/27 全有值） |
| pii_scan / pii_redactions | TEXT / INTEGER | PII 扫描结果与脱敏数 |

## evidence_passages（证据段落，34 行）— 主键 `id`

| 字段 | 类型 | 说明 |
|---|---|---|
| doc_id | TEXT FK→evidence_documents.doc_id | 所属文档 |
| passage | TEXT NOT NULL | 逐字原文（preserved source evidence；PII 按治理口径处理） |
| seq | INTEGER | 段序（1 起） |

## evidence_fts（FTS5 检索虚表，34 行）

`passage`（bigram token 串，非原文）+ `doc_id`（UNINDEXED）；`rowid` = `evidence_passages.id`；排序用内置 `bm25()`。

## 代表性业务 SQL

见 `docs/queries.sql`（判决溯源 Q1、评估交叉表 Q2、压档审计 Q3、规则数据 Q4、机构覆盖 Q5、过滤检索 Q6）。
