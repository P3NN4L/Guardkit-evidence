# MAIB7050 Group Project Proposal (v2 — one-page main body, per §2.2 field list)

> 中文备注：正文按 Moodle 一页限制写（~620 词，TNR 12pt/1.2 倍行距约一页）。
> [方括号] 是占位符：诈骗统计数字从你们 evidence pipeline 抓的官方页面里取，保证可引用。
> Declarations 在附加页（§2.6 允许），不算正文。

---

**Direction:** E. Risk Compliance and Escalation
**Provisional title:** GuardKit Evidence — an evidence-grounded screening data product for suspicious payment messages in Hong Kong
**Group:** [GroupID] · Members: [names] · Contact: [name]

**1. User, decision, action — and why it is worth addressing**
- **Users (two roles, matching the triage-then-review workflow):** front line — accounts-payable / finance staff at an SME who receive payment-related SMS/WhatsApp instructions ("supplier changed bank account", "this invoice is due today") and must decide whether to pay, hold, or verify; back line — bank fraud-review analysts who work the escalated queue and need each case to arrive with evidence, not just a score.
- **Decision and action:** release / hold-and-verify / escalate to a human fraud-review queue with supporting evidence attached. The product never auto-blocks; every "scam" verdict reaches a person.
- **Why worth addressing:** Hong Kong recorded [N] deception cases with HK$[X] in losses in [year], with commercial fraud (impersonating suppliers/executives) among the fastest-growing categories ([HKFPD/HKMA source — cite from evidence store]). SME finance staff currently triage such messages from memory or ad-hoc search: a wrong "safe" means direct loss, a wrong "hold" means a late payment. The product makes the first pass consistent and auditable — each verdict arrives with its score, the rule that fired, and the official advisory passage that justifies it, cutting lookup time and creating a reviewable record. (The scoring engine also ships in a consumer app; this project deliberately frames the same engine as a B2B triage workflow.)
- **Visible limitations:** scores are probabilistic; zh-HK/en/Cantonese coverage is uneven; evidence pages lag live fraud patterns. Success is defined on a documented 60-case evaluation set (recall, evidence coverage, retrieval quality), not on interface polish.

**2. Data sources (and why they are suitable)**
- **Evidence layer (semi-structured):** HKMA fraud alerts, bank fraud-alert pages, HK government press releases → JSON with source URL, access date, license note, content hash (~200 curated documents). Suitable because verdicts must cite official advisories, not model output.
- **Screening corpus (unstructured text):** labelled scam advisories and normal messages (gov notices, forum language) plus clearly labelled synthetic rows (~1,000 curated; of which [X]% real, [Y]% template-generated, [Z]% LLM-generated). Suitable because the screening component needs realistic bilingual short texts. Every row carries a generation label in the data dictionary (`real` with source dataset / `template` with generator script / `llm` with model name and prompt family); synthetic rows supplement real data, never dominate, and are never cited as evidence.
- **Structured layer:** institution registry, rule table, verdict log — ≥3 related SQL entities (§3).
- **Key data-management decisions:** group-wise held-out split (75/25, template-grouped so test phrasings are unseen); SHA-256-locked test sets; nothing deleted — superseded evidence versions are kept.

**3. Architecture: relational core + flexible evidence layer**
SQLite/PostgreSQL core: `institutions`, `rules` (pattern, weight), `messages`, `verdicts` (score, band, model_version, `whitelist_rule` enum notice|domain|institutional, nullable institution FK, reviewed_by/at), `evidence_documents` (institution FK, published_date, source_url, content_hash, accessed_at). Evidence documents keep raw passages and provenance in JSON; each verdict links to its matched passages — the traceable output path required by Element 6.

**4. Prior work vs project work (declared)**
**Prior work (Zhanjian Li, before the course):** GuardKit v7 scoring engine (public repo, released npm package), harvesting pipeline with provenance and dedup gates, labelling/quarantine conventions. The engine is used strictly as the scoring component, pinned to one released version, and is not modified in this project.
**To be built (the assessed work):** (1) relational schema, data dictionary, representative business SQL (Element 3); (2) evidence retrieval — metadata filters first, semantic search where justified (Element 5); (3) verdict card: score → band → matched rule → official passages with source URL and date (Element 6); (4) 60-case evaluation set including difficult bilingual and whitelist-conflict cases, expected vs observed, failure analysis (Element 7); (5) governance write-up: access tiers, privacy (no real customer messages stored — public/synthetic samples only), human-review workflow, model/version lineage (Element 7).

**5. Course connection**
Data product framing; relational vs document modelling trade-offs; metadata and lineage; retrieval design (SQL / metadata / semantic / hybrid) and when embeddings add justified value; evidence-grounded output vs unsupported answers; governance (ownership, access, privacy, human-in-the-loop); evaluation with labelled cases.

**6. Scope, responsibilities, risks**
**In:** working prototype (notebook or lightweight app), ~1,000-message corpus, ~200-document evidence store, schema + SQL, retrieval path, verdict cards, 60-case evaluation, governance doc. **Out:** production deployment, mobile integration, real-time streams, retraining.
**Workstreams:** A — verdict card, prototype, live demo [Member]; B — schema, data dictionary, SQL [Member]; C — evidence store, JSON layer, retrieval [Member]; D — evaluation set, failure analysis, governance, report integration [Member]. All members review the full product weekly; a contribution record is kept from day one.
**Main risks:** source pages change → snapshot with access date and hash; uneven language coverage → bilingual difficult-case set; engine version drift → pinned dependency, engine changes out of scope.

---

## Additional pages (declarations only — §2.6)

**Prior work declaration.** The GuardKit v7 scoring engine, its message corpus, the harvesting pipeline and the evaluation harness were developed by team member Zhanjian Li before this course (public repository `guard-kit-code`, released npm package `@p3nn4l/guard-kit`, cited in Works Cited). They are used as a pinned dependency and are not part of the assessed contribution.

**AI use declaration.** Proposal and report drafting were assisted by a large-language-model coding agent ([tool/model]); all outputs were checked and revised by the team. Implementation assistance may be used for schema SQL, the retrieval prototype and evaluation scripts; all code was executed and verified by the team, and the marker can reproduce the full path from the submitted package. The scoring engine itself is prior work by a team member; this project only consumes it as a dependency, and the scoring path contains no generative component. No AI-generated data, citations, labels or evaluation judgements are submitted as independently observed; synthetic corpus rows are labelled as such.

**Generated data declaration.** Part of the screening corpus is machine-generated to supplement real data: template-generated rows follow reviewable generator scripts, and [Z]% of rows were generated with [model] using documented prompt families. Every row is labelled with its generation method and model in the data dictionary, and samples were manually reviewed before inclusion. Generated rows supplement — and never replace — real data: the evidence layer consists of real official advisories, and the evaluation set consists of real messages and team-authored cases (any generated case, if included, is labelled and its expected label verified by the team). Generation scripts and prompt families are included in the supporting package for verification.

**Data compliance.** Only public web pages are collected; terms of use are respected; source URL and access date are recorded for every document; no personal data is collected or stored.
