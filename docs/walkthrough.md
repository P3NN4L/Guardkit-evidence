# 答辩走讲 · Walkthrough & Cheat Sheet（内部答辩准备文档）

> 用途：每人答辩/写报告前过一遍。数字全部有出处（`evaluation/`、`data/DATA-HANDOFF.md`、`docs/queries.sql` 实查），不许手编。
> 最后同步：2026-09-29（108 条消息 / 27 份文档口径）。

---

## 0. 三十秒开场（背下来）

> 香港中小企业财务每天收到各种付款消息，搞错一单就是真金白银的损失。我们做了**证据型分流产品**：可疑支付消息进来 → 引擎打分 → 出一张「判决卡」（分数 + 命中规则 + **官方原文依据**）→ 高危升级人工复核。**永不自动拦截，最终判断永远由人做。**
>
> 课程方向 E 的官方示例句是 "an evidence-based triage product that routes cases for human review"——我们与它逐字吻合。唯一论证过的偏差：主用户从银行改成中小企业财务（银行有成套反诈体系、无采纳故事；SME 是商业骗案重灾区且无工具可用），银行保留为复核方 + 证据源。

---

## 1. 数据怎么流（四步 × 四个文件）

```
① 建库  python3 src/build_db.py
   三路数据 → 一个 SQLite（8 张业务表 + 1 张 FTS5 虚表）
   · 证据侧：27 份真实官方文档（警务处/HKMA/银行防骗页/政府公报）
     每份带 source_url + accessed_at + content_hash + license
     → evidence_documents / evidence_passages
   · 消息侧：108 条标注消息（105 真实 + 3 演示），带来源/期望标签/生成标注
     → messages
   · 规则侧：白名单正则从 pinned 引擎投影成数据表 → rules / rule_patterns

② 打分  python3 src/run_demo.py
   v7 pinned 引擎（先期工作，只读）打分 → 三重白名单（全部命中才放行）
   → 白名单压档时原始分留在 verdicts.score_raw_before_rule（审计链）

③ 检索  FTS5 + BM25（bigram 索引 + 文档级聚合）
   命中写进 verdict_evidence —— schema 的桥：判决侧 ↔ 证据侧
   每条判决可用 SQL 查出「依据是哪段原文」

④ 出卡  判决卡 = 分数档位 + 命中规则 + 官方原文引用（链接 + 日期）
   → demo/verdict_cards.html（三张演示卡）
```

---

## 2. 五个设计决策（每个都有「为什么」）

### 2.1 为什么永不自动拦截？
引擎有已知盲区（2025 新骗术召回缺口 84.2%）。误拦正常付款代价极高 → 设计为 triage-then-review：高危升级人工，结论由人下。**判决卡③故意演示一个引擎误报案例**（假借钱测警觉性对话），主动展示安全垫。

### 2.2 为什么判决连到「段落」而不是「文档」？
可追溯要落到最小证据单元。判分人一条 SQL（`queries.sql` Q1）即可查出：V-MSG-001 的依据是警务处《商業電郵騙案》原文「供應商聲稱更換付款賬戶，必須先聯絡對方已知舊有聯絡方式確認」。这由 `verdict_evidence` 表在 **schema 层**保证，不是应用层假装——proposal 第 3 节承诺的正是这条链。

### 2.3 为什么白名单要留压档前的原始分？
白名单是治理取舍（宁可放行低可疑度的机构通知）。留原始分才能回答「白名单救了多少条、压了多少分」——Q3 一条 SQL 出审计统计。当前 12 条白名单放行全部留档。

### 2.4 为什么 FTS5 不用 embedding？
课程原话：embeddings "when they add justified value"。本用例 = 官方通告短段落 + 精确术语命中（「供應商」「收款戶口」「熱線」）→ 关键词检索可解释、可复现、零依赖。**如实写「本用例下 embedding 无正当增量」是符合课程要求的正当结论。** 另外 `verdict_evidence.retrieval_method` 字段让检索方法可查询、可对比、可演进。

### 2.5 为什么 12 条判决没有证据？
全部是粤语日常闲聊（约去海边/看戏，分数 0.01–0.10）。benign 消息不该硬凑官方引用——检索无结果时**如实显示**。这是 "unsupported outputs" 的反面，是治理设计点。

---

## 3. 必记数字表

| 数字 | 含义 | 出处 |
|---|---|---|
| **27 份 / 108 条** | 证据文档 / 标注消息（硬门槛 ≥20 / ≥50 双达标） | `build_db.py` 输出 |
| **84 + 12 + 12 = 108** | 判决三分账：证据落库 / 白名单放行 / 如实无检索 | `verdict_evidence` 实查 |
| **scam 召回 40/43；normal 放行 53/65** | expected-vs-observed 交叉表；漏报 3、误报 12 | `queries.sql` Q2 |
| **204,800 bytes 逐字节一致** | 独立复现：重建库 = 提交库（确定性） | FINAL-CHECK §4.3 |
| **164 → 124** | 白名单 v4 相对 @7.0.0 发布版的误报差 | `evaluation/fp-attribution.md` |
| **recall 84.2%** | 引擎 2025 新骗术卷召回缺口（主动写进评估） | 17 卷基线 |
| **9 家机构 / 7 条正则** | institutions 注册表 / rule_patterns 规则数据 | schema 实查 |

---

## 4. 演示动线（15 分钟 demo 的 5 分钟核心）

1. `python3 src/build_db.py` —— 指着末尾两行硬门槛 ✅（判分人最想看的信心句）
2. `python3 src/run_demo.py` —— **重点讲 MSG-001 卡**：冒充供应商换账户 → 高危 0.99 → 官方依据命中警务处原文（链接可点）→ 升级人工
3. MSG-002 卡：银行账单通知 → 白名单三重条件放行 → 「原始分已留档」一句带过审计链
4. MSG-003 卡：假借钱对话 → 引擎误报 → 工作流交人工兜底 → 「永不自动拦截」落点
5. `open demo/verdict_cards.html` + `sqlite3 ... < docs/queries.sql` —— 展示 Q1 一条 SQL 溯源判决依据

---

## 5. 预设问题 Q&A（课程 §2.10 列过的问题）

**Q：这个结果从哪来的（where did a result come from）？**
从 pinned 引擎（`engine/scorer.py` + `models/radar.json` @7.0.0，逐字快照，parity 守门）→ `verdicts` 落库；依据从证据库 FTS5 检索 → `verdict_evidence` 落库。全链字段可查（`model_id` / `retrieval_method` / `rank`）。

**Q：为什么这个字段这样设计（why a field was chosen）？**
举 `score_raw_before_rule`：白名单是治理取舍，覆盖分数会断审计链，所以生效分与原始分并存。同理 `label` / `synthetic_derived` / `generation` / `pii_hits` 把数据合规做成字段级证据，对应 §1.5 合成数据标注要求。

**Q：检索失败怎么办（what happens when retrieval fails）？**
判决卡如实显示「未检索到足够相关的官方段落（不硬凑依据）」。当前 12 条 benign 消息即此路径，全部 label=normal、分数 ≤0.10——不是缺陷，是不制造 unsupported output。

**Q：引擎是谁做的？算不算你们的工作？**
先期工作（组员 Zhanjian Li 课程前开发，公开仓 + npm 包，proposal 第 4 节已申报）。课程评估的是**数据产品层**：库、检索、判决卡、评估、治理。引擎以 pinned 依赖消费，快照不许改。

**Q：证据会不会过期/失效？**
来源页面变更风险 → 快照 + `content_hash` + `accessed_at` 三件套（proposal 风险节既定对策）。

**Q：怎么处理个人数据（PII）？**
摄取管线内置扫描（`src/textproc.py`）：个人邮箱/电话/证件号命中即脱敏并计数（`pii_redactions`）；公司客服热线与公共角色邮箱是公开通告的正式内容，按治理口径保留原文；消息只计数不改动（`pii_hits`），文本须逐字保留供打分。

---

## 6. 局限（诚实 = 加分，全部有文件佐证）

- 引擎是确定性 n-gram 模型：老骗术近乎满分，2025 新骗术召回缺口 84.2%（`evaluation/baseline-v7-public-allsets.json`）
- 长文本英文 BEC 覆盖不均：当前 3 条漏报中 2 条属此类（1 条爬取的真实 BEC 伪付款确认 + 1 条盲测卷英文冒充教务处）
- 证据页面滞后于实时骗术
- 数据构成如实声明：全部 105 条消息真实（`synthetic_derived=0`）、来源可溯（`data/DATA-HANDOFF.md`）

---

## 7. 待办（答辩前）

- [ ] 报告 10 页正文（素材齐：design.md 两图 / queries.sql / 复现表 / 归因分析）
- [ ] 60 例评估集（从 108 条抽 30 常规 + 30 困难；Q2/Q3 即评估表骨架）
- [ ] 提案三处占位符：组员名单、诈骗统计 [N]/[X]（从证据层官方页取）、AI 工具名
- [ ] `reviews/` 下三份外部复核文档若纳入提交包 → AI 使用声明必须申报（§2.11）
- [ ] `data/guardkit_course.db` 处置（删或改名，见 ACTION-ITEMS §3）
