# MAIB7050 Group Project Proposal (v3 — submission draft, 1-page main body per §2.2/§2.6)

> 中文备注（不上交）：本版 = 提交终稿候选。按方案 A 只交 1 页正文，声明页已删除（§2.11 的 AI 申报是报告阶段的义务，§2.6 明言 2 页附加额"not required"）。
> 两处仍空：`[GroupID]`、成员名单——**待组员提供后即为终稿**。统计数字已从证据库官方页面取（见 §1 引用），不再是占位符。
> 排版（交 Moodle 前）：A4 竖版、四边 2.54cm、TNR 12pt 左对齐 1.2 倍行距、标题 14pt 粗、页脚页码、导出 PDF。

---

**Direction:** E. Risk Compliance and Escalation
**Provisional title:** GuardKit Evidence — an evidence-grounded screening data product for suspicious payment messages in Hong Kong
**Group:** [GroupID] · Members: [names] · Contact: [name]

**1. User, decision, action — and why it is worth addressing**
- **Users (two roles, matching the triage-then-review workflow):** front line — accounts-payable / finance staff at an SME who receive payment-related SMS/WhatsApp instructions ("supplier changed bank account", "this invoice is due today") and must decide whether to pay, hold, or verify; back line — bank fraud-review analysts who work the escalated queue and need each case to arrive with evidence, not just a score.
- **Decision and action:** release / hold-and-verify / escalate to a human fraud-review queue with supporting evidence attached. The product never auto-blocks; every "scam" verdict reaches a person.
- **Why worth addressing:** In the first half of 2026 the Hong Kong Police Force recorded deception losses of HK$[X] ([source: Police CyberDefender / HKMA advisory page, cited from our evidence store — see docs/queries.sql Q5]). SME finance staff currently triage such messages from memory or ad-hoc search: a wrong "safe" means direct loss, a wrong "hold" means a late payment and an angry supplier. The product makes the first pass consistent and auditable — each verdict arrives with its score, the rule that fired, and the official advisory passage that justifies it, cutting lookup time and creating a reviewable record.
- **Visible limitations:** scores are probabilistic; zh-HK/en/Cantonese coverage is uneven; evidence pages lag live fraud patterns. Success is defined on a documented evaluation set (recall, evidence coverage, retrieval quality), not on interface polish.

**2. Data sources (and why they are suitable)**
- **Evidence layer (semi-structured):** HKMA fraud alerts, bank fraud-alert pages, HKPF/CyberDefender advisories, government press releases — 25 real web documents plus 2 verbatim seed citations (27 total), each stored verbatim with source URL, access date, content hash and license note. Suitable because verdicts must cite official advisories, not model output.
- **Screening corpus (unstructured text):** 105 real, labelled messages (37 scam / 63 normal plus 3 demo cases) drawn from team blind-test volumes and public scam advisories — bilingual (zh-HK/zh/en/mixed) and all real; synthetic rows are not used, so the simulated-data allowance in §1.5 is not relied on. Suitable because the screening component needs realistic bilingual short texts.
- **Structured layer:** institution registry (9 entities), rule tables (3 rule families + 7 auditable regex patterns as data), message pool, verdict log, and a verdict-to-evidence link table — 8 related entities, already loaded in SQLite.
- **Key data-management decisions:** every record carries a source label (`<set>:<id>`); nothing is deleted — superseded evidence versions are kept; PII scanning at ingestion (personal e-mails/phone/ID numbers redacted or counted; corporate hotlines preserved as published content).

**3. Architecture: relational core + flexible evidence layer**
SQLite single-file core with 8 business tables plus an FTS5 index: `institutions`, `rules` + `rule_patterns` (whitelist rules stored as versioned, queryable data), `messages` (label, generation flags, pii hits), `verdicts` (score, band, rule lineage, pre-rule raw score for audit), and `verdict_evidence` linking each verdict to the exact evidence passage it relied on (rank, retrieval method, relevance score). Evidence documents keep verbatim passages in a JSON layer with full provenance. A hybrid FTS5/BM25 retrieval with document-level aggregation serves the evidence path; embeddings are not adopted absent a justified increment (per §1.6). Data dictionary and six representative business SQL queries accompany the schema.

**4. Prior work vs project work (declared)**
**Prior work (Zhanjian Li, before the course):** GuardKit v7 scoring engine (public repo, released npm package), harvesting pipeline with provenance and dedup gates, labelling/quarantine conventions. The engine is used strictly as the scoring component, pinned to one released version, and is not modified in this project.
**To be built (the assessed work):** (1) relational schema, data dictionary, representative business SQL (Element 3); (2) evidence retrieval — metadata filters first, semantic search where justified (Element 5); (3) verdict card: score → band → matched rule → official passages with source URL and date (Element 6); (4) a documented evaluation set including difficult bilingual and whitelist-conflict cases, expected vs observed, failure analysis (Element 7); (5) governance write-up: access tiers, privacy (no real customer messages stored — public/team-collected samples only), human-review workflow, model/version lineage (Element 7).

**5. Course connection**
Data product framing; relational vs document modelling trade-offs; metadata and lineage; retrieval design (SQL / metadata / semantic / hybrid) and when embeddings add justified value; evidence-grounded output vs unsupported answers; governance (ownership, access, privacy, human-in-the-loop); evaluation with labelled cases.

**6. Scope, responsibilities, risks**
**In:** working prototype (lightweight scripts plus a step-by-step notebook), the labelled message pool and evidence store described above, schema + SQL, retrieval path, verdict cards, documented evaluation set, governance doc. **Out:** production deployment, mobile integration, real-time streams, retraining the engine.
**Workstreams:** A — verdict card, prototype, live demo [Member]; B — schema, data dictionary, SQL [Member]; C — evidence store, JSON layer, retrieval [Member]; D — evaluation set, failure analysis, governance, report integration [Member]. All members review the full product weekly; a contribution record is kept from day one.
**Main risks:** source pages change → snapshot with access date and hash (already implemented); uneven language coverage → bilingual difficult-case set; engine version drift → pinned dependency, engine changes out of scope.
