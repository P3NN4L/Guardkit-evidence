-- GuardKit Evidence · 代表性业务 SQL（对照课程 §1.6 "representative SQL queries that answer business questions"）
-- 运行：sqlite3 guardkit_evidence.sqlite < docs/queries.sql
-- 全部语句只读；判定口径见 README 数据字典。

-- ── Q1 · 业务问题：被升级人工复核的高危案件，各自的官方依据是什么？（Element 6 可追溯输出）
SELECT v.id AS case_id, m.source, v.score, v.p_cal,
       ve.rank AS evidence_rank, p.passage,
       d.title, d.source_url, d.accessed_at
FROM verdicts v
JOIN messages m ON m.id = v.message_id
JOIN verdict_evidence ve ON ve.verdict_id = v.id
JOIN evidence_passages p ON p.id = ve.passage_id
JOIN evidence_documents d ON d.doc_id = p.doc_id
WHERE v.band = 'high'
ORDER BY v.id, ve.rank;

-- ── Q2 · 业务问题：引擎判得准不准？期望标签 × 判决档位交叉表（expected vs observed，评估节素材）
-- 高危/可疑=拦截方向，未识别=放行方向；normal 却判高危/可疑 = 误报候选，scam 却未识别 = 漏报候选。
SELECT m.label AS expected,
       CASE WHEN v.band IN ('high','medium') THEN 'flagged' ELSE 'released' END AS observed,
       COUNT(*) AS n
FROM verdicts v
JOIN messages m ON m.id = v.message_id
WHERE m.label IS NOT NULL
GROUP BY 1, 2 ORDER BY 1, 2;

-- 漏报明细（真 scam 却被放行）——评估节的失败案例清单
SELECT v.id, m.lang, m.source, v.score, v.band
FROM verdicts v JOIN messages m ON m.id = v.message_id
WHERE m.label = 'scam' AND v.band = 'low'
ORDER BY v.score DESC;

-- ── Q3 · 业务问题：白名单把分数压了多少？（审计链：压档前 vs 生效分，P2-2 修复的产出）
SELECT v.id, v.whitelist_rule, r.family AS rule_family,
       v.score_raw_before_rule AS engine_raw,
       v.score AS effective_raw,
       ROUND(v.score_raw_before_rule - v.score, 4) AS suppressed
FROM verdicts v
LEFT JOIN rules r ON r.id = v.verdict_rule_id
WHERE v.score_raw_before_rule IS NOT NULL
ORDER BY suppressed DESC;

-- ── Q4 · 业务问题：哪条白名单规则介入了多少判决？用的什么正则（规则即数据，可版本化）
SELECT r.id, r.description, rp.version, rp.pattern_name, rp.guard, COUNT(v.id) AS verdicts
FROM rules r
LEFT JOIN rule_patterns rp ON rp.rule_id = r.id
LEFT JOIN verdicts v ON v.verdict_rule_id = r.id
GROUP BY r.id, rp.pattern_name, rp.guard, rp.version
ORDER BY r.id, verdicts DESC;

-- ── Q5 · 业务问题：各机构的证据覆盖如何？（证据库建设进度，WP2）
SELECT i.name, i.type, i.evidence_authority,
       COUNT(DISTINCT d.doc_id) AS docs,
       COUNT(p.id) AS passages
FROM institutions i
LEFT JOIN evidence_documents d ON d.institution_id = i.id
LEFT JOIN evidence_passages p ON p.doc_id = d.doc_id
GROUP BY i.id ORDER BY docs DESC, i.id;

-- ── Q6 · 检索示例：带元数据过滤的 FTS5 检索（换账户类消息 → 只要监管/警务机构的中文依据）
SELECT p.doc_id, d.title, d.lang, bm25(evidence_fts) AS rel
FROM evidence_fts f
JOIN evidence_passages p ON p.id = f.rowid
JOIN evidence_documents d ON d.doc_id = p.doc_id
JOIN institutions i ON i.id = d.institution_id
WHERE evidence_fts MATCH ?
  AND i.evidence_authority = 1
ORDER BY rel LIMIT 5;
-- 绑定参数示例（sqlite3 CLI）：SELECT … MATCH ? … 时传
--   .parameter init  .parameter set @q "換 收款 戶口 戶口"  -- 由应用层 textproc.fts_tokens 生成
