# MAIB7050 Group Project Proposal (v3 — submission draft, 1-page main body per §2.2/§2.6)

> 中文备注（不上交）：本版 = 提交终稿候选。按方案 A 只交 1 页正文，声明页已删除（§2.11 的 AI 申报是报告阶段的义务，§2.6 明言 2 页附加额"not required"）。
> 两处仍空：`[GroupID]`、成员名单——**待组员提供后即为终稿**。统计数字已取自官方公报（2024 年 44,480 宗 / 91.5 亿港元，info.gov.hk 2025-02-11），MLA 条目随报告 Works Cited 一并给出。
> 排版（交 Moodle 前）：A4 竖版、四边 2.54cm、TNR 12pt 左对齐 1.2 倍行距、标题 14pt 粗、页脚页码、导出 PDF。

---

**Direction:** E. Risk Compliance and Escalation
**Provisional title:** GuardKit Evidence — an evidence-grounded screening data product for suspicious payment messages in Hong Kong
**Group:** [GroupID] · Members: [names] · Contact: [name]

**1. User, decision, action — and why it is worth addressing**
- **Users (two roles):** front line — SME accounts-payable staff who receive payment instructions via SMS/WhatsApp ("supplier changed bank account") and must decide whether to pay, hold, or verify; back line — bank fraud-review analysts who need escalated cases to arrive with evidence, not just a score.
- **Decision and action:** release / hold-and-verify / escalate to a human fraud-review queue with supporting evidence attached. The product never auto-blocks; every "scam" verdict reaches a person.
- **Why worth addressing:** Deception is Hong Kong's largest crime category — 44,480 cases in 2024 (up 11.7% year-on-year), losses of HK$9.15 billion, 46.9% of all recorded crime (HKSAR Government press release, 11 Feb 2025); commercial impersonation (fake suppliers instructing payment to new accounts) is a documented fast-growing modus operandi (Police CyberDefender). SME finance staff triage such messages from memory: a wrong "safe" means direct loss; a wrong "hold" means a late payment. The product makes the first pass consistent and auditable — each verdict carries its score, the rule that fired, and the official passage that justifies it.
- **Visible limitations:** probabilistic scores; uneven zh-HK/en coverage; evidence pages lag live fraud patterns. Success is defined on a documented evaluation set, not interface polish.

**2. Data sources (and why they are suitable)**
- **Evidence layer:** 27 official documents (HKMA alerts, bank fraud-alert pages, HKPF/CyberDefender advisories), each stored verbatim with source URL, access date, content hash and license note — verdicts must cite official advisories, not model output.
- **Screening corpus:** 105 real, labelled messages (37 scam / 63 normal + 3 demo) from team blind-test volumes and public advisories, bilingual (zh-HK/zh/en/mixed); no synthetic rows are used. Suitable because screening needs realistic bilingual short texts.
- **Structured layer:** 8 related SQLite entities — institutions, rules (+ 7 regex patterns as data), messages, verdicts, and a verdict-to-evidence link table.
- **Key decisions:** every record carries a source label; nothing is deleted (superseded evidence versions kept); PII scanning at ingestion (personal data redacted or counted).

**3. Architecture: relational core + flexible evidence layer**
A SQLite single-file core holds 8 business tables plus an FTS5 index: `institutions`; `rules` + `rule_patterns` (whitelist rules as versioned, queryable data); `messages`; `verdicts` (score, band, rule lineage, pre-rule raw score for audit); and `verdict_evidence`, linking each verdict to the exact passage it relied on. Verbatim passages live in a JSON layer with full provenance. Hybrid FTS5/BM25 retrieval with document-level aggregation serves the evidence path; embeddings are not adopted absent a justified increment. A data dictionary and six representative business SQL queries accompany the schema.

**4. Prior work vs project work (declared)**
**Prior work (Zhanjian Li, before the course):** GuardKit v7 scoring engine (public repo, released npm package) and its harvesting/labelling pipeline. The engine is a pinned, unmodified scoring component.
**To be built (the assessed work):** (1) relational schema, data dictionary, business SQL (Element 3); (2) evidence retrieval (Element 5); (3) verdict card — score → band → rule → official passage with source URL and date (Element 6); (4) documented evaluation set with difficult cases, expected vs observed, failure analysis (Element 7); (5) governance write-up — privacy, human-review workflow, version lineage (Element 7).

**5. Course connection**
Relational vs document modelling; metadata and lineage; retrieval design (SQL / metadata / semantic / hybrid) and when embeddings add justified value; evidence-grounded output vs unsupported answers; governance (privacy, human-in-the-loop); evaluation with labelled cases.

**6. Scope, responsibilities, risks**
**In:** working prototype (scripts + step-by-step notebook), the labelled pool and evidence store above, schema + SQL, retrieval path, verdict cards, evaluation set, governance doc. **Out:** production deployment, mobile integration, real-time streams, engine retraining.
**Workstreams:** A — verdict card, prototype, live demo [Member]; B — schema, data dictionary, SQL [Member]; C — evidence store, JSON layer, retrieval [Member]; D — evaluation set, failure analysis, governance, report integration [Member]. All members review the full product weekly; a contribution record is kept from day one.
**Main risks:** source pages change → snapshots with access date and hash (already implemented); uneven language coverage → bilingual difficult-case set; engine drift → pinned dependency.
