# 外部复核 · MAIB7050GP（2026-09-29）

> ⚠️ **提交前须知**：本文档由外部 AI 复核生成。若它被纳入提交包，**必须在 AI use declaration 中申报**（课程 §2.11 要求写明工具/模型、用途、影响范围，以及团队如何核查与修订）。建议路径：作为内部工作文档保留在仓内、不进 Moodle 提交包；若纳入，则补申报。
>
> 复核方：外部独立复核。基于仓库**实际产物**（`guardkit_evidence.sqlite` 下载后逐表 dump、`src/run_demo.py` 与 `src/build_db.py` 源码、`engine/scorer.py`、`docs/*`），不采信文档自述。
> 复核未修改任何代码。
> 方法：下载 `guardkit_evidence.sqlite` → `PRAGMA table_info` / `PRAGMA foreign_key_list` / 逐表取样 → 与课程要求（`MAIB7050_Group_Project_Guidelines.pdf`）逐条对照。

---

## 摘要

| 等级 | 项 | 影响 |
|---|---|---|
| 🔴 P0 | `verdicts` 与 `evidence_passages` 在 schema 里**没有任何链接** | 直接违反课程核心要求「Integration」+「traceable evidence is compulsory」 |
| 🔴 P0 | 提交包内 `evidence_documents` 仅 **2 份**、`messages` 仅 **3 条** | 两条硬门槛（≥20 文档 / ≥50 短文本）**在包内都不达标** |
| 🟠 P1 | 检索层未使用 SQL 能力，且无对比评估 | 「Retrieval, evidence, evaluation」15 分 |
| 🟠 P1 | `docs/match.md` 引用的路径在本仓全部不存在 | 判分人顺手一点就是死链 |
| 🟠 P1 | PII 处理无实作（声明有，流程无） | 数据合规章节答不实 |
| 🟡 P2 | `rules` 表 3 行散文，真正的正则藏在代码里 | 关系核心的说服力被削弱 |
| 🟡 P2 | 白名单压档覆盖了引擎原始分 | 审计链断裂 |
| 🟡 P2 | `demo/verdict_cards.html` 是生成产物却入库 | 会过期 |
| 🟢 P3 | 若干命名/字段一致性问题 | 细节分 |

**先说做得好、不要动的部分（见第九节）**：Direction E 定位、双角色设计、"永不自动拦截"、先期工作/AI 使用/生成数据三段声明、检索无结果时如实显示的兜底文案、第三条判决卡主动展示已知误报。这些是加分项，复核**不建议改动**。

---

## P0-1 · `verdicts` 与 `evidence_passages` 在 schema 里没有链接

### 证据

`proposal.md` 第 3 节原文：

> Evidence documents keep raw passages and provenance in JSON; **each verdict links to its matched passages** — the traceable output path required by Element 6.

实际 schema（`guardkit_evidence.sqlite` 实测）：

```
evidence_documents.institution_id → institutions.id
evidence_passages.doc_id         → evidence_documents.doc_id
rules.institution_id             → institutions.id
verdicts.message_id              → messages.id
```

**外键图是两段互不相连的**：

```
institutions ─→ evidence_documents ─→ evidence_passages        （证据侧）
messages     ─→ verdicts                                        （判决侧）
```

两段之间**没有任何外键**。

`src/run_demo.py` 的 `save_verdict()` 实际写入的字段：

```python
sql = "INSERT INTO verdicts (id, message_id, score, p_cal, band, top_type,
       whitelist_rule, model_version, created_at) VALUES (?,?,?,?,?,?,?,?,?)"
```

**没有 evidence 相关字段。** `retrieve_evidence()` 返回的 `hits` 只被传给 `cli_card()` 和 `html_card()` 用于渲染，**从不落库**。

### 为什么这是最严重的问题

1. **直接违反课程的硬性核心要求。** 课程 §1.5：
   > **Integration:** A clear, logic-driven connection between structured and unstructured data.

   §1.6：
   > **Evidence-grounded output:** Results identify the supporting record, document or passage and relevant metadata.
   > **traceable evidence is compulsory.**

   现在这条链路只活在**应用层的一次运行里**。判分人问「用 SQL 查出具支持判决 `V-MSG-001` 的官方段落」——**答不上来**。

2. **可追溯性不可持久。** `demo/verdict_cards.html` 每次 `run_demo.py` 重新生成；数据库里的 `verdicts` 行不携带任何依据。二次查询、审计、回归都无法重建「当时为什么这么判」。

3. **文档与实现落差。** proposal 明写了这条链接，代码没做——这类落差在判分时最伤，因为判分人会拿 proposal 逐条对代码。

### 修法

加一张连接表（**这是复核认为性价比最高的一处修改**）：

```sql
CREATE TABLE verdict_evidence (
  verdict_id       TEXT    NOT NULL REFERENCES verdicts(id),
  passage_id       INTEGER NOT NULL REFERENCES evidence_passages(id),
  rank             INTEGER NOT NULL,   -- 第几条依据（1 = 最强）
  retrieval_method TEXT,               -- keyword | bigram | fts | semantic
  score            REAL,               -- 检索得分
  PRIMARY KEY (verdict_id, passage_id)
);
```

并让 `save_verdict()` 接收 `hits` 一并落库。

**顺带解决一个连带问题**：`verdicts.whitelist_rule` 存的是字符串枚举（`notice|domain|institutional`），而 `rules` 表已有主键 `id`。应改为：

```sql
verdict_rule_id TEXT REFERENCES rules(id)   -- 替代 whitelist_rule 字符串
```

这样「哪个规则介入过哪个判决」也能用 SQL 查出来。

**收益**：这条改完之后，Element 3（关系核心）和 Element 6（可追溯输出）从「应用层假装」变成「schema 保证」，并且可以给出这样一条代表性 SQL（课程明确要求 "representative SQL queries that answer business questions"）：

```sql
-- 业务问题：本周被升级人工的案件，各自的依据是什么？
SELECT v.id, m.text, v.band, v.score,
       p.passage, d.title, d.source_url, d.accessed_at
FROM verdicts v
JOIN messages m           ON m.id = v.message_id
JOIN verdict_evidence ve  ON ve.verdict_id = v.id
JOIN evidence_passages p  ON p.id = ve.passage_id
JOIN evidence_documents d ON d.doc_id = p.doc_id
WHERE v.band = 'high'
ORDER BY v.created_at DESC, ve.rank;
```

---

## P0-2 · 提交包内的两条硬门槛都不达标

### 证据

实测行数：

| 表 | 行数 |
|---|---|
| `institutions` | 5 |
| `rules` | 3 |
| `messages` | **3** |
| `verdicts` | 3 |
| `evidence_documents` | **2** |
| `evidence_passages` | 9 |

课程 §1.5 核心要求原文：

> • **Structured Data:** At least 3 related entities suitable for SQL analysis.
> • **Unstructured/Semi-structured Data:** At least **50 short-text records** or **20 substantive documents**.
> • Integration: A clear, logic-driven connection between structured and unstructured data.

### 问题

`guard-kit-code` 里的 13,677 条语料和 ~165 份 HKMA PDF **不在这个仓库里**，判分人只看提交包（§2.4「The marker must be able to follow at least one complete path」，§2.8 交付物清单）。

所以在**当前提交包内**：
- 文档路线：2 份 < 20 ❌
- 短文本路线：3 条 < 50 ❌

**两条路都不达标。**

### 修法（按优先级）

1. **`evidence_documents` 扩到 ≥20 份**（`docs/plan.md` WP2 已列为待做，这是必须做完的）。来源现成：HKMA 警示、各银行防骗页、警务处《警声》、政府新闻署通告。每份按现有 `seed_evidence.json` 的 schema，保留 `source_url` / `accessed_at` / `content_hash`。
2. **`messages` 扩到 ≥60 条**（同时满足 proposal 承诺的 60 例评估集）。来源：团队已有的盲测卷（`blind-n200/n400/v10/v11/v12`、`v3-blind-scam-*`），以及公开短讯样本。**注意 `source` 字段要如实区分 `blind-set:*` / `demo-written` / `public:*`。**
3. 在 README 里明确写出「本包内 X 份文档、Y 条短文本」，让判分人一眼对上门槛。

> 提示：这两条做完后，「Integration」那条也能顺势成立——因为 `verdict_evidence`（P0-1）刚好把两层连起来。

---

## P1-1 · 检索层没有用 SQL，也没有对比评估

### 证据

`src/run_demo.py`：

```python
def retrieve_evidence(conn, text: str, top_k: int = 2):
    qb = bigrams(text)
    sql = "SELECT p.doc_id, p.passage, ... FROM evidence_passages p JOIN evidence_documents d ON d.doc_id = p.doc_id"
    rows = conn.execute(sql).fetchall()          # ← 全表捞出
    for doc_id, passage, cat, title, ... in rows:
        kw = sum(1 for k in KEYWORDS.get(cat, []) if k in passage and k in text)
        overlap = len(qb & bigrams(passage)) / max(1, len(qb))
        score = kw * 2.0 + overlap * 8.0          # ← 权重无出处
```

三个问题：

1. **SQL 只做了一次全表 JOIN**，所有过滤与排序都在 Python 里。课程 §1.6 要求 "a **justified combination**"，§2.3 要求 "appropriate SQL"。判分人看到「查出全表再在 Python 里 for 循环」会直接扣实现分。
2. **`kw * 2.0 + overlap * 8.0` 两个权重没有依据**，也没有敏感性分析。课程 §1.6 明确要 "any comparison used to justify the final design"。
3. **proposal 第 4 节承诺的 "metadata filters first, semantic search where justified" 在代码里都不存在**。文档与实现的第二处落差。

### 修法

1. **FTS5 是 Python 标准库 `sqlite3` 自带的**，不需要新依赖：

```sql
CREATE VIRTUAL TABLE evidence_fts USING fts5(
  passage, doc_id UNINDEXED, tokenize='unicode61'
);
```
   BM25 排序是白拿的，权重来源变成可引用的标准算法，而不是手调常数。

2. **元数据过滤推进 SQL `WHERE`**：

```sql
SELECT p.* FROM evidence_passages p
JOIN evidence_documents d ON d.doc_id = p.doc_id
WHERE (? IS NULL OR d.category = ?)
  AND (? IS NULL OR d.lang = ?)
ORDER BY bm25(evidence_fts) LIMIT ?;
```

3. **做三方对比并写进报告**（这就是「Retrieval, evidence, and evaluation」15 分的素材）：

| 方案 | 说明 | 待测指标 |
|---|---|---|
| metadata-only | 纯 SQL 过滤，无文本相关性 | 依据命中率 |
| FTS5 / BM25 | 关键词 | P@1 / P@2、MRR |
| 语义（可选） | embedding 余弦 | 同上 + 「embeddings 是否带来 justified value」的论证 |

   **第三行是否做取决于对比结果**——课程原文 "Semantic retrieval should use embeddings **when they add justified value**"。如果 FTS5 已经够用，**如实报告「不需要 embedding」反而是加分项**。

4. 把 `docs/plan.md` WP3 的「关键词+bigram → 正式版 FTS/embedding 对比」在代码里落实，别只留在计划里。

---

## P1-2 · `docs/match.md` 引用的路径在本仓全部不存在

### 证据

`docs/match.md` 第六节「现成弹药清单」列的位置：

| 文档里写的路径 | 本仓实际 |
|---|---|
| `public-v7/training/baseline/result-v7-public-allsets.json` | `evaluation/baseline-v7-public-allsets.json` |
| `public-v7/training/baseline/eval_v7_allsets_local.py` | 不存在 |
| `public-v7/training/baseline/dump_fps.py` | 不存在 |
| `public-v7/src/radar.ts` | `engine/scorer.py` |
| `public-v7/training/artifacts/metrics.json` | 不存在 |
| `public-v7/training/verify/verify-ml.ts` | `tests/test_parity.py` |

另外 `match.md` §二 写「SQLite 建 **5** 张表」，实际 DB 有 **6** 张业务表（5 + `evidence_passages`）。

### 修法

1. 把路径全部改成本仓真实路径；
2. 或者明确标注 `docs/match.md` 是**内部规划稿**（引用的是外部 `guard-kit-code` 仓），在文件头写清，避免判分人当场点死链；
3. 表数量改为 6，或统一口径说明「5 张实体表 + 1 张段落从表」。

> 这类问题本身不重，但它是**判分人最容易顺手验证的一项**，一次死链会连带影响他对其他文档的信任。

---

## P1-3 · PII 处理：声明有，实作无

### 现状

`docs/proposal.md` 的 Data compliance 段：

> Only public web pages are collected; terms of use are respected; source URL and access date are recorded for every document; **no personal data is collected or stored.**

`README.md`：

> 本仓不存储任何真实用户消息。

这两句在当前 3 条 message 范围内成立。**但 WP2 要扩到 ~200 份文档，来源正是银行防骗页** —— 而这类页面的页脚普遍带真实职员联系方式。

复核在兄弟仓 `versionV8-database/v2/harvest/` 的同源数据里实测到：

```
電郵：teresa.lok@shacombank.com.hk
電話：(852)28415302傳真：(852)25268320
```

这是**真实个人的工作邮箱**（上海商业银行职员），来自银行警示页页脚。

### 为什么必须处理

课程 §1.5 明确要求组织数据必须 "remove or protect confidential and personal information"；§2.4 提交清单写 "Do not submit ... unnecessary personal information"。而且判分时几乎必问「你们怎么处理个人数据」——现在没有可展示的流程。

### 修法

在证据摄取环节加一步显式扫描 + 脱敏，并把方法写进治理章节：

1. 正则扫描 `邮箱 / 电话 / 传真 / 身份证号 / 姓名`；
2. 命中即脱敏（`teresa.lok@***`、`(852)2***302`）或整段丢弃；
3. **记录脱敏日志**（命中数、处理方式），作为治理证据；
4. 在 `evidence_documents` 加一个 `pii_scan` 字段记录结果，让合规检查可被 SQL 查询。

> 这一条做好了是**加分项**——多数学生项目只会写一句泛泛的伦理声明，而课程的评分描述明确说 "Do not add generic ethics statements unrelated to the actual project."

---

## P2-1 · `rules` 应该是数据，不是代码

### 现状

`rules` 表 3 行，`pattern_summary` 是散文：

| id | family | pattern_summary |
|---|---|---|
| R-NOTICE | notice | `反詐/防騙/騙案… × 熱線/掛斷/切勿/核實…` |
| R-DOMAIN | domain | `gov.hk / hsbc.com.hk / hangseng.com / bochk.com …（且无 .top/.xyz/… 记号）` |
| R-INSTITUTIONAL | institutional | （同类散文） |

真正的正则定义在 `engine/scorer.py` 的 `NOTICE_TOPIC` / `NOTICE_ADVICE` / `OFFICIAL_DOMAIN` / `BAD_URL_TOKEN` / `SAFE_CHANNEL`。

### 问题

课程要求 Element 3 是 "Which **stable entities, relationships and rules** should be managed in a relational structure?"——**规则本身就是被点名的要素**。而你的规则是代码常量，不是可查询的数据。

`build_db.py` 的注释也自认「正式版放可审计的正则清单」。

### 修法

把规则族拆成可版本化的数据：

```sql
-- rules 保留族定义
-- 新增规则条目表
CREATE TABLE rule_patterns (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  rule_id      TEXT NOT NULL REFERENCES rules(id),
  pattern      TEXT NOT NULL,   -- 可审计的正则原文
  pattern_type TEXT NOT NULL,   -- regex | domain_list | keyword
  version      TEXT NOT NULL,
  effective_from TEXT
);
```

**收益（报告里可以直接这么讲）**：「规则作为数据管理，支持版本化与回溯——当白名单调整导致误报率变化时，可以精确定位是哪一条规则在哪个版本引入的。」

这句话在校准/误报归因那一节（`evaluation/fp-attribution.md`）里有现成的数据支撑，**是这个项目独有的、别的组讲不出来的故事**。

---

## P2-2 · 白名单压档覆盖了引擎原始分

### 证据

`src/run_demo.py`：

```python
if wl:  # 白名单压档与引擎同规则：压到可疑档以下
    p_raw = min(p_raw, MODEL["bands"]["mid"] - 0.01)
    p_cal = min(p_cal, MODEL["bands"]["mid"] - 0.01)
```

结果：`MSG-002` 的 `verdicts.score` = `p_cal` = **0.34**（= 0.35 − 0.01）。

### 问题

**引擎原本说了什么，被覆盖掉了。** 审计和答辩时都会需要回答「规则介入前，模型给这条消息打了几分」——现在查不到。而这不是理论问题：`evaluation/fp-attribution.md` 里记录的「白名单误放」正是这类取舍的实证，报告里要讲这个 trade-off，就需要原始分做对照。

### 修法

`verdicts` 表增加：

```sql
score_raw_before_rule  REAL,   -- 规则介入前的引擎原始分
```

保留 `score` / `p_cal` 为「生效分」。这样一条 SQL 就能出「白名单把多少条压了多少分」的统计。

---

## P2-3 · `demo/verdict_cards.html` 是生成产物却入库

`README.md` 把它列为交付物，但它是 `run_demo.py` 每次运行重写的。入库会导致：

- 与 DB 不同步（DB 更新了、HTML 还是旧的）；
- 判分人打开看到的可能不是当前代码的输出。

**修法**：要么 `.gitignore` 掉、在 README 写「运行 `run_demo.py` 生成」；要么在 README 标注它是**某次运行的快照**（附 `created_at`）。前者更干净。

---

## P3 · 小问题清单

| # | 位置 | 问题 |
|---|---|---|
| 1 | `src/seed_evidence.json` | `_comment` 里写 `access_date`，实际字段是 `accessed_at` |
| 2 | `institutions.whitelist_flag` | HKMA / HKPF（regulator / police）为 0，语义不明——是指「银行域名白名单」还是「官方来源」？建议改名或加注释 |
| 3 | `messages.source` | 取值格式不统一：`demo-written` vs `blind-set:blind-n200:N200-N07`。建议规范成 `<type>:<set>:<id>` 并在数据字典里定义 |
| 4 | `verdicts.model_version` | 存的是自由文本 `"radar v7 (pinned snapshot @7.0.0)"`。血缘建议拆成 `model_id` + `model_version` 两个字段，便于按版本统计 |
| 5 | `evidence_documents` | 缺 `license` 字段，而 proposal 承诺记录 license note |
| 6 | `docs/plan.md` / `proposal.md` | 多处 `[占位符]`（诈骗统计数字、成员姓名、GroupID）——提交前必须填实，且数字要从 evidence store 里可引用的官方页面取 |

---

## 九、做得好的部分（**复核建议不要改动**）

写在这里，避免后续修改时误伤：

| 项 | 为什么好 |
|---|---|
| **Direction E 定位** | 与课程示例句 "an evidence-based triage product that routes cases for human review" 几乎逐字吻合，且论证了用户从银行改为 SME 财务的理由 |
| **双角色设计** | 前线（SME 财务）+ 后台（银行复核），对应 "triage-then-review" 的完整工作流，比单角色更有业务说服力 |
| **"永不自动拦截"** | 这是治理章节最有力的设计主张，也是第三条判决卡的价值所在 |
| **三段声明**（先期工作 / AI 使用 / 生成数据） | 极其规范。课程序言明确要求这些，且多数学生项目会在这里翻车。**保持不动** |
| **检索无结果的兜底文案** | `run_demo.py` 里「本次未检索到足够相关的官方段落（检索无结果时如实显示，不硬凑依据）」——直接对应评分描述里的 "unsupported outputs" 反面 |
| **第三条判决卡主动展示已知误报** | 对应 "strong evaluation of difficult cases" 与 "recognition of limitations"，是被明确奖励的行为 |
| **`tests/test_parity.py`** | Python 快照 ↔ 训练侧逐位一致守门，血缘证据的硬材料 |
| **README 的边界声明** | 主动写「2025 新骗术存在召回缺口（v7 全卷基线 recall 84.2%）」——诚实 |
| **证据种子是逐字引用 + URL + 抓取日期 + content hash** | 这正是 "preserved source evidence" 的教科书做法，扩到 200 份即可 |

---

## 十、优先级总表

| 顺序 | 动作 | 成本 | 影响评分项 |
|---|---|---|---|
| 1 | 加 `verdict_evidence` 表 + `save_verdict()` 落库 | 半天 | 架构 15 + 检索证据 15 |
| 2 | `evidence_documents` 扩到 ≥20 份 | 3–5 天 | **硬门槛** + 数据源 10 |
| 3 | `messages` 扩到 ≥60 条（兼作评估集） | 2–3 天 | **硬门槛** + 评估 15 |
| 4 | 检索改 FTS5 + SQL 元数据过滤 + 三方对比 | 3–4 天 | 实现 15 + 检索证据 15 |
| 5 | 修 `docs/match.md` 路径与表数 | 30 分钟 | 报告 10（避免死链） |
| 6 | PII 扫描 + 脱敏 + 日志 | 1 天 | 数据治理 10 |
| 7 | `rules` → `rule_patterns` 数据化 | 1 天 | 架构 15 |
| 8 | `score_raw_before_rule` 字段 | 1 小时 | 评估 15 |
| 9 | `demo/*.html` 处理（gitignore 或标注快照） | 15 分钟 | 报告 10 |
| 10 | P3 小问题批量清理 | 2 小时 | 细节分 |

---

*本复核只包含分析与建议，未修改任何代码。所有 schema 与行数结论可用下列方式复现：*

```bash
python3 -c "
import sqlite3
c = sqlite3.connect('guardkit_evidence.sqlite')
for t, in c.execute(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\"):
    print(t, c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0])
print([r for r in c.execute('PRAGMA foreign_key_list(verdicts)')])
"
```
