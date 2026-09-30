# -*- coding: utf-8 -*-
"""GuardKit Evidence——建库（课程仓版）。
运行：python3 src/build_db.py  → 仓根 guardkit_evidence.sqlite

数据源（全部带来源标注）：
- data/institutions.json         机构注册表（GP 数据包，见 data/DATA-HANDOFF.md）
- data/evidence_documents.jsonl  证据文档（公开网页逐字全文 + URL + 抓取时间）
- data/messages.jsonl            标注消息池（取数规格见 data/MESSAGES-SPEC.md）
- src/seed_evidence.json         逐字引用种子（警务处/HKMA，带 content hash）
- 内嵌 3 条演示消息              判决卡演示用（来源各自标注）
- engine/scorer.py               pinned 引擎：白名单正则投影成 rule_patterns 数据表

全部 SQL 使用参数绑定；schema 变更只发生在本文件。
"""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows GBK 控制台兼容（✅/❌ 否则崩溃）；Jupyter 的 OutStream 无此方法，跳过

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
DATA = ROOT / "data"

import textproc  # noqa: E402  共享文本处理（与 run_demo 检索侧同一实现）
from engine import scorer  # noqa: E402  pinned 只读快照，见模块头

DB = ROOT / "guardkit_evidence.sqlite"
MODEL = scorer.load_model(ROOT / "models" / "radar.json")
ENGINE_VERSION = "v%s (pinned snapshot @7.0.0)" % MODEL["version"]

SCHEMA = """
DROP TABLE IF EXISTS verdict_evidence;
DROP TABLE IF EXISTS verdicts;
DROP TABLE IF EXISTS evidence_fts;
DROP TABLE IF EXISTS evidence_passages;
DROP TABLE IF EXISTS evidence_documents;
DROP TABLE IF EXISTS rule_patterns;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS rules;
DROP TABLE IF EXISTS institutions;

CREATE TABLE institutions (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL,              -- regulator | police | government | bank
  whitelist_flag INTEGER NOT NULL DEFAULT 0,     -- 1=官方域名命中引擎 OFFICIAL_DOMAIN 白名单（R-DOMAIN 生效对象）
  evidence_authority INTEGER NOT NULL DEFAULT 0, -- 1=官方证据来源机构（监管/警务/政府）
  domains TEXT,                    -- JSON 数组：已知官方域名
  source_url TEXT
);

CREATE TABLE rules (
  id TEXT PRIMARY KEY,            -- 规则族标识
  family TEXT NOT NULL,           -- notice | domain | institutional（三重白名单族）
  description TEXT NOT NULL,
  pattern_summary TEXT NOT NULL,  -- 人读摘要；可审计正则见 rule_patterns 表
  weight REAL NOT NULL,           -- 证据权重（演示用固定值）
  institution_id TEXT REFERENCES institutions(id)  -- 可空：notice 族不对应单一机构
);

-- 规则即数据：由 pinned 引擎（engine/scorer.py）在建库时投影生成，可审计、可版本化，
-- 与实际执行的引擎不会漂移；禁止手工编辑本表内容。
CREATE TABLE rule_patterns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rule_id TEXT NOT NULL REFERENCES rules(id),
  pattern_name TEXT NOT NULL,     -- 引擎侧常量名（溯源到 engine/scorer.py）
  pattern TEXT NOT NULL,          -- 正则原文
  guard TEXT NOT NULL,            -- positive=命中才放行 | negative=命中即否决白名单
  version TEXT NOT NULL           -- 生成时的 pinned 引擎版本
);

CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  text TEXT NOT NULL,
  lang TEXT,                      -- zh-HK | zh | en | mixed
  channel TEXT,                   -- sms | whatsapp | email | NULL
  received_at TEXT,
  source TEXT NOT NULL,           -- 溯源 <set>:<id>（约定见 README 数据字典）
  note TEXT,
  label TEXT,                     -- 期望标签 scam | normal（评估对照用）
  synthetic_derived INTEGER NOT NULL DEFAULT 0,  -- 1=含 LLM 生成成分（AI 申报用）
  generation TEXT,                -- 生成方式：real | llm_rewrite_v3_blind | human_written_demo …
  pii_hits INTEGER NOT NULL DEFAULT 0  -- PII 扫描疑似命中数（只计数，文本保持逐字）
);

CREATE TABLE verdicts (
  id TEXT PRIMARY KEY,
  message_id TEXT NOT NULL REFERENCES messages(id),
  score REAL NOT NULL,            -- 生效 pRaw（白名单压档后）
  p_cal REAL NOT NULL,            -- 生效 pCal（校准分）
  band TEXT NOT NULL,             -- high | medium | low（双条件档位）
  top_type TEXT,                  -- 骗术大类 best-guess
  whitelist_rule TEXT,            -- 命中家族名 notice | domain | institutional（人读）
  verdict_rule_id TEXT REFERENCES rules(id),  -- 命中规则行（SQL 可查"哪个规则介入过哪个判决"）
  score_raw_before_rule REAL,     -- 规则介入前引擎原始 pRaw（NULL=无规则介入）——审计链保留
  model_id TEXT NOT NULL,         -- 引擎标识（血缘，便于按版本统计）
  model_version TEXT NOT NULL,    -- 引擎版本全称
  created_at TEXT NOT NULL,
  reviewed_by TEXT,               -- 人工复核（升级后填写）
  reviewed_at TEXT
);

CREATE TABLE evidence_documents (
  doc_id TEXT PRIMARY KEY,
  institution_id TEXT NOT NULL REFERENCES institutions(id),
  title TEXT NOT NULL,
  publisher TEXT,
  published_date TEXT,            -- 页面/通告日期（gov_press 行源 schema 以此为主溯源）
  source_url TEXT NOT NULL,       -- 溯源：原文链接
  accessed_at TEXT NOT NULL,      -- 溯源：抓取日期；harvested_at 缺失时回落记录 content_date（数据字典有注）
  lang TEXT,
  category TEXT,                  -- 检索用语义类别
  evidence_class TEXT,            -- 采集侧来源类别（GP 数据包 taxonomy）
  content_hash TEXT,              -- 溯源：内容指纹（快照校验用）
  license TEXT,                   -- license 备注（WP2 扩库时从页面页脚补录）
  pii_scan TEXT NOT NULL DEFAULT 'clean',  -- clean | redacted（摄取管线 PII 扫描结果）
  pii_redactions INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE evidence_passages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id TEXT NOT NULL REFERENCES evidence_documents(doc_id),
  passage TEXT NOT NULL,          -- 逐字段落（preserved source evidence；PII 命中处已脱敏）
  seq INTEGER NOT NULL
);

-- 检索索引：CJK 无空格分词，按字符 bigram 切开（unicode61），BM25 排序。
-- passage 列存的是索引用 token 串，原文在 evidence_passages.passage。
CREATE VIRTUAL TABLE evidence_fts USING fts5(passage, doc_id UNINDEXED, tokenize='unicode61');

-- P0 修复：判决 ↔ 证据段落 的 schema 级连接（Element 6 可追溯输出的落库保证）
CREATE TABLE verdict_evidence (
  verdict_id TEXT NOT NULL REFERENCES verdicts(id),
  passage_id INTEGER NOT NULL REFERENCES evidence_passages(id),
  rank INTEGER NOT NULL,          -- 依据强度序（1 = 最强）
  retrieval_method TEXT NOT NULL, -- fts5-bm25-bigram
  score REAL,                     -- 检索相关度（-bm25，越大越相关）
  PRIMARY KEY (verdict_id, passage_id)
);
"""

# ---- 机构注册表：本仓 5 家 + GP 数据包 5 家（HSBC 重复合并）----
# whitelist_flag 语义以引擎 OFFICIAL_DOMAIN 正则为准（gov.hk / hsbc.com.hk / hangseng.com /
# bochk.com 等），HKMA/HKPF 的 gov.hk 域名亦命中 → 1（修正旧值 0 的语义含混，见外部复核 P3-2）。
INSTITUTIONS_OURS = [
    ("HKMA", "香港金融管理局 Hong Kong Monetary Authority", "regulator", 1, 1,
     ["www.hkma.gov.hk"], "https://www.hkma.gov.hk"),
    ("HKPF", "香港警務處（反詐騙協調中心）", "police", 1, 1,
     ["www.police.gov.hk"], "https://www.police.gov.hk/ppp_sc/adcc/"),
    ("HSBC", "滙豐銀行 HSBC", "bank", 1, 0,
     ["www.hsbc.com.hk"], "https://www.hsbc.com.hk"),
    ("HASE", "恆生銀行 Hang Seng Bank", "bank", 1, 0,
     ["www.hangseng.com"], "https://www.hangseng.com"),
    ("BOCHK", "中國銀行(香港) BOCHK", "bank", 1, 0,
     ["www.bochk.com"], "https://www.bochk.com"),
]

# GP 数据包机构名 → 本仓 TEXT id（HSBC 与本仓行合并，domains 并入）
PKG_NAME_TO_ID = {
    "Chiyu Bank": "CHIYU",
    "HKCPF CyberDefender": "HKCPF",
    "HKSAR Government": "HKGOV",
    "HSBC": "HSBC",
    "SHACOM Bank": "SHACOM",
}
INSTITUTIONS_PKG = {
    "CHIYU": ("Chiyu Bank 集友銀行", "bank", 0, 0,
              ["www.chiyubank.com"], "https://www.chiyubank.com"),
    "HKCPF": ("香港警務處 CyberDefender 防騙資料庫", "police", 0, 1,
              ["cyberdefender.hk"], "https://cyberdefender.hk"),
    "HKGOV": ("香港特別行政區政府（新聞公報）", "government", 1, 1,
              ["info.gov.hk"], "https://www.info.gov.hk"),
    "SHACOM": ("上海商業銀行 SHACOM Bank", "bank", 0, 0,
               ["www.shacombank.com.hk", "www1.shacombank.com.hk"], "https://www.shacombank.com.hk"),
}

RULES = [
    ("R-NOTICE", "notice", "官方反诈提示白名单：反诈主题词×官方建议词同时出现 → 压到可疑档以下",
     "反詐/防騙/騙案… × 熱線/掛斷/切勿/核實…", 0.9, None),
    ("R-DOMAIN", "domain", "官方域名白名单：含官方银行域名且无可疑 URL 记号 → 机构通知",
     "gov.hk / hsbc.com.hk / hangseng.com / bochk.com …（且无 .top/.xyz/… 记号）", 0.9, "HSBC"),
    ("R-INSTITUTIONAL", "institutional", "机构通知白名单 v4：机构通知主题×官方渠道指引×无可疑 URL（三重条件）",
     "賬單/按揭/學費/勞工處/警務處… × 如需查詢請致電8位熱線/網上理財/App內… × 无可疑 URL", 0.8, "HASE"),
]

# 白名单正则 → rule_patterns 投影（pattern 取自 pinned 引擎，guard 说明其在三重条件里的角色）
PATTERN_FAMILIES = [
    ("R-NOTICE", [("NOTICE_TOPIC", "positive"), ("NOTICE_ADVICE", "positive")]),
    ("R-DOMAIN", [("OFFICIAL_DOMAIN", "positive"), ("BAD_URL_TOKEN", "negative")]),
    ("R-INSTITUTIONAL", [("INSTITUTIONAL_TOPIC", "positive"), ("SAFE_CHANNEL", "positive"),
                         ("BAD_URL_TOKEN", "negative")]),
]

# ---- 3 条演示消息（判决卡演示用；来源/标签/生成方式如实标注）----
MESSAGES_DEMO = [
    ("MSG-001", "May你好，我係恆達五金阿強。我哋公司換咗收款戶口，上個月嗰批貨尾數HK$85,000請今日內轉去新戶口123-456-789，舊戶口因審計已停用，有疑問回覆呢個號碼。",
     "zh-HK", "whatsapp", "2026-09-29 14:02", "demo:written:MSG-001",
     "演示撰写（非真实消息）", "scam", 0, "human_written_demo"),
    ("MSG-002", "【恆生銀行】您的信用卡賬單已於今日發出，本期應繳金額HK$3,256，繳款截止日期為下月5號。你可透過恆生Mobile App或網上理財查閱詳細賬單。",
     "zh-HK", "sms", "2026-09-29 09:15", "blind-set:blind-n200:N200-N07",
     None, "normal", 0, "real"),
    ("MSG-003", "哥，我手機壞咗用阿明部機搵你，我急用二萬週轉，你幫我過落呢個戶口先。咁啱咁大額？我打你平時個號碼先。哦……打咗啦。你聽到真係你先話我知……其實係我，測試下你警覺性。",
     "zh-HK", "whatsapp", "2026-09-29 20:41", "blind-set:blind-v12:W12-N16",
     "已知困难案例：对话类（引擎误报 → 人工复核兜底）", "normal", 0, "real"),
]


def load_jsonl(path: Path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def merge_institutions(pkg_institutions):
    """本仓 5 行 + 数据包（HSBC 合并，domains 并入）。"""
    rows = {r[0]: list(r) for r in INSTITUTIONS_OURS}
    for inst in pkg_institutions:
        iid = PKG_NAME_TO_ID.get(inst.get("name"))
        if iid is None:
            raise SystemExit(f"data/institutions.json 出现未知机构名：{inst.get('name')!r}（PKG_NAME_TO_ID 需要补充）")
        if iid == "HSBC":
            known = set(rows["HSBC"][5])
            rows["HSBC"][5] = json.dumps(sorted(known | set(inst.get("domains", []))), ensure_ascii=False)
            continue
        name, typ, wl, auth, domains, url = INSTITUTIONS_PKG[iid]
        rows[iid] = [iid, name, typ, wl, auth, json.dumps(domains, ensure_ascii=False), url]
    for row in rows.values():
        if isinstance(row[5], list):
            row[5] = json.dumps(row[5], ensure_ascii=False)
    return [rows[k] for k in sorted(rows)]


def load_messages():
    """数据包消息 + 演示消息；来源约定 <set>:<id>；PII 只计数不改动。"""
    out = []
    for m in load_jsonl(DATA / "messages.jsonl"):
        mid = m["msg_id"]
        if mid.startswith("MSG-"):
            raise SystemExit(f"msg_id {mid!r} 使用了演示保留前缀 MSG-（见 data/MESSAGES-SPEC.md）")
        out.append((mid, m["text"], m.get("lang"), m.get("channel"), m.get("received_at"),
                    "%s:%s" % (m["volume"], mid), m.get("note"), m.get("label"),
                    1 if m.get("synthetic_derived") else 0, m.get("kind", "real")))
    out.extend(MESSAGES_DEMO)
    ids = [r[0] for r in out]
    if len(ids) != len(set(ids)):
        from collections import Counter
        dup = [k for k, v in Counter(ids).items() if v > 1]
        raise SystemExit(f"messages 主键重复：{dup[:5]}")
    return out


def load_evidence_docs():
    """seed（2 份逐字引用）+ 数据包（25 份真实抓取）→ (doc 行, passages)；证据段落过 PII 脱敏。"""
    docs, passages = [], []
    seed = json.loads((HERE / "seed_evidence.json").read_text(encoding="utf-8"))
    for doc in seed["documents"]:
        text_hash = hashlib.sha256("".join(doc["passages"]).encode()).hexdigest()[:16]
        docs.append((doc["doc_id"], doc["institution_id"], doc["title"], doc.get("publisher"),
                     doc.get("published_date"), doc["source_url"], doc["accessed_at"],
                     doc.get("lang"), doc.get("category"), doc.get("evidence_class"),
                     text_hash, doc.get("license"), "clean", 0))
        for i, p in enumerate(doc["passages"], 1):
            passages.append((doc["doc_id"], p, i))

    for doc in load_jsonl(DATA / "evidence_documents.jsonl"):
        iid = PKG_NAME_TO_ID.get(doc["institution"])
        if iid is None:
            raise SystemExit(f"evidence_documents 出现未知机构名：{doc['institution']!r}")
        harvested = (doc.get("harvested_at") or "")[:10]
        accessed = harvested or doc.get("content_date")  # gov_press 行按源 schema 回落 content_date
        text = doc["text"]
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        redacted, n_red = textproc.pii_redact(text)
        docs.append((doc["doc_id"], iid, doc["title"], doc["institution"], doc.get("content_date"),
                     doc["url"], accessed, doc.get("lang"), doc.get("category"),
                     doc.get("evidence_class"), text_hash, doc.get("license_note") or doc.get("license"),
                     "redacted" if n_red else "clean", n_red))
        passages.append((doc["doc_id"], redacted, 1))
    return docs, passages


def main():
    pkg_institutions = json.loads((DATA / "institutions.json").read_text(encoding="utf-8"))
    institutions = merge_institutions(pkg_institutions)
    messages = load_messages()
    docs, passages = load_evidence_docs()

    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO institutions (id, name, type, whitelist_flag, evidence_authority, domains, source_url) VALUES (?,?,?,?,?,?,?)",
                     institutions)
    conn.executemany("INSERT INTO rules (id, family, description, pattern_summary, weight, institution_id) VALUES (?,?,?,?,?,?)",
                     RULES)
    conn.executemany("INSERT INTO rule_patterns (rule_id, pattern_name, pattern, guard, version) VALUES (?,?,?,?,?)",
                     [(rid, name, getattr(scorer, name).pattern, guard, ENGINE_VERSION)
                      for rid, patterns in PATTERN_FAMILIES for name, guard in patterns])
    conn.executemany("INSERT INTO messages (id, text, lang, channel, received_at, source, note, label, synthetic_derived, generation, pii_hits) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     [row + (textproc.pii_scan_count(row[1]),) for row in messages])
    conn.executemany("INSERT INTO evidence_documents (doc_id, institution_id, title, publisher, published_date, source_url, accessed_at, lang, category, evidence_class, content_hash, license, pii_scan, pii_redactions) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     docs)
    conn.executemany("INSERT INTO evidence_passages (doc_id, passage, seq) VALUES (?,?,?)", passages)

    fts_rows = []
    for pid, p, did in conn.execute("SELECT id, passage, doc_id FROM evidence_passages"):
        fts_rows.append((pid, textproc.fts_tokens(p), did))
    conn.executemany("INSERT INTO evidence_fts (rowid, passage, doc_id) VALUES (?,?,?)", fts_rows)
    conn.commit()

    n_inst = conn.execute("SELECT COUNT(*) FROM institutions").fetchone()[0]
    n_rules = conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0]
    n_pat = conn.execute("SELECT COUNT(*) FROM rule_patterns").fetchone()[0]
    n_msgs = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    n_docs = conn.execute("SELECT COUNT(*) FROM evidence_documents").fetchone()[0]
    n_pass = conn.execute("SELECT COUNT(*) FROM evidence_passages").fetchone()[0]
    n_pii_msg = conn.execute("SELECT COALESCE(SUM(pii_hits), 0) FROM messages").fetchone()[0]
    n_pii_doc = conn.execute("SELECT COALESCE(SUM(pii_redactions), 0) FROM evidence_documents").fetchone()[0]
    conn.close()

    print("OK -> %s" % DB.name)
    print("  institutions=%d rules=%d rule_patterns=%d" % (n_inst, n_rules, n_pat))
    print("  messages=%d（含 3 条演示）evidence_documents=%d evidence_passages=%d"
          % (n_msgs, n_docs, n_pass))
    print("  PII 扫描：证据段落脱敏 %d 处；消息疑似命中 %d 处（只计数，文本逐字保留）" % (n_pii_doc, n_pii_msg))
    print("  硬门槛：文档 ≥20 %s（%d 份）；短文本 ≥50 %s（%d 条）"
          % ("✅" if n_docs >= 20 else "❌", n_docs, "✅" if n_msgs >= 50 else "❌", n_msgs))


if __name__ == "__main__":
    main()
