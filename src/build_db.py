# -*- coding: utf-8 -*-
"""GuardKit Evidence——建库（课程仓版）。
运行：python3 src/build_db.py  → 仓根 guardkit_evidence.sqlite
"""
import hashlib
import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DB = ROOT / "guardkit_evidence.sqlite"

SCHEMA = """
DROP TABLE IF EXISTS verdicts;
DROP TABLE IF EXISTS evidence_passages;
DROP TABLE IF EXISTS evidence_documents;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS rules;
DROP TABLE IF EXISTS institutions;

CREATE TABLE institutions (
  id TEXT PRIMARY KEY,            -- 机构标识
  name TEXT NOT NULL,             -- 名称
  type TEXT NOT NULL,             -- regulator | police | bank
  whitelist_flag INTEGER NOT NULL DEFAULT 0,  -- 官方域名白名单覆盖
  source_url TEXT
);

CREATE TABLE rules (
  id TEXT PRIMARY KEY,            -- 规则族标识
  family TEXT NOT NULL,           -- notice | domain | institutional（三重白名单族）
  description TEXT NOT NULL,
  pattern_summary TEXT NOT NULL,  -- 模式说明（正式版放可审计的正则清单）
  weight REAL NOT NULL,           -- 证据权重（演示用固定值）
  institution_id TEXT REFERENCES institutions(id)  -- 可空：notice 族不对应单一机构
);

CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  text TEXT NOT NULL,
  lang TEXT,                      -- zh-HK | en | mixed
  channel TEXT,                   -- sms | whatsapp | email
  received_at TEXT,
  source TEXT NOT NULL            -- demo-written | blind-set（真实来源标注）
);

CREATE TABLE verdicts (
  id TEXT PRIMARY KEY,
  message_id TEXT NOT NULL REFERENCES messages(id),
  score REAL NOT NULL,            -- pRaw
  p_cal REAL NOT NULL,            -- pCal（校准分）
  band TEXT NOT NULL,             -- high | medium | low（双条件档位）
  top_type TEXT,                  -- 骗术大类 best-guess
  whitelist_rule TEXT,            -- notice | domain | institutional | NULL
  model_version TEXT NOT NULL,    -- 引擎版本（血缘）
  created_at TEXT NOT NULL,
  reviewed_by TEXT,               -- 人工复核（升级后填写）
  reviewed_at TEXT
);

CREATE TABLE evidence_documents (
  doc_id TEXT PRIMARY KEY,
  institution_id TEXT NOT NULL REFERENCES institutions(id),
  title TEXT NOT NULL,
  publisher TEXT,
  published_date TEXT,
  source_url TEXT NOT NULL,       -- 溯源：原文链接
  accessed_at TEXT NOT NULL,      -- 溯源：抓取日期
  lang TEXT,
  category TEXT,
  content_hash TEXT               -- 溯源：内容指纹（快照校验用）
);

CREATE TABLE evidence_passages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id TEXT NOT NULL REFERENCES evidence_documents(doc_id),
  passage TEXT NOT NULL,          -- 逐字段落（preserved source evidence）
  seq INTEGER NOT NULL
);
"""

INSTITUTIONS = [
    ("HKMA", "香港金融管理局 Hong Kong Monetary Authority", "regulator", 0, "https://www.hkma.gov.hk"),
    ("HKPF", "香港警務處（反詐騙協調中心）", "police", 0, "https://www.police.gov.hk/ppp_sc/adcc/"),
    ("HSBC", "滙豐銀行 HSBC", "bank", 1, "https://www.hsbc.com.hk"),
    ("HASE", "恆生銀行 Hang Seng Bank", "bank", 1, "https://www.hangseng.com"),
    ("BOCHK", "中國銀行(香港) BOCHK", "bank", 1, "https://www.bochk.com"),
]

RULES = [
    ("R-NOTICE", "notice", "官方反诈提示白名单：反诈主题词×官方建议词同时出现 → 压到可疑档以下",
     "反詐/防騙/騙案… × 熱線/掛斷/切勿/核實…", 0.9, None),
    ("R-DOMAIN", "domain", "官方域名白名单：含官方银行域名且无可疑 URL 记号 → 机构通知",
     "gov.hk / hsbc.com.hk / hangseng.com / bochk.com …（且无 .top/.xyz/… 记号）", 0.9, "HSBC"),
    ("R-INSTITUTIONAL", "institutional", "机构通知白名单 v4：机构通知主题×官方渠道指引×无可疑 URL（三重条件）",
     "賬單/按揭/學費/勞工處/警務處… × 如需查詢請致電8位熱線/網上理財/App內… × 无可疑 URL", 0.8, "HASE"),
]

MESSAGES = [
    ("MSG-001", "May你好，我係恆達五金阿強。我哋公司換咗收款戶口，上個月嗰批貨尾數HK$85,000請今日內轉去新戶口123-456-789，舊戶口因審計已停用，有疑問回覆呢個號碼。",
     "zh-HK", "whatsapp", "2026-09-29 14:02", "demo-written"),
    ("MSG-002", "【恆生銀行】您的信用卡賬單已於今日發出，本期應繳金額HK$3,256，繳款截止日期為下月5號。你可透過恆生Mobile App或網上理財查閱詳細賬單。",
     "zh-HK", "sms", "2026-09-29 09:15", "blind-set:blind-n200:N200-N07"),
    ("MSG-003", "哥，我手機壞咗用阿明部機搵你，我急用二萬週轉，你幫我過落呢個戶口先。咁啱咁大額？我打你平時個號碼先。哦……打咗啦。你聽到真係你先話我知……其實係我，測試下你警覺性。",
     "zh-HK", "whatsapp", "2026-09-29 20:41", "blind-set:blind-v12:W12-N16（已知困难案例：对话类）"),
]


def main():
    seed = json.loads((HERE / "seed_evidence.json").read_text(encoding="utf-8"))
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO institutions VALUES (?,?,?,?,?)", INSTITUTIONS)
    conn.executemany("INSERT INTO rules VALUES (?,?,?,?,?,?)", RULES)
    conn.executemany("INSERT INTO messages VALUES (?,?,?,?,?,?)", MESSAGES)
    for doc in seed["documents"]:
        h = hashlib.sha256("".join(doc["passages"]).encode()).hexdigest()[:16]
        conn.execute(
            "INSERT INTO evidence_documents VALUES (?,?,?,?,?,?,?,?,?,?)",
            (doc["doc_id"], doc["institution_id"], doc["title"], doc["publisher"],
             doc["published_date"], doc["source_url"], doc["accessed_at"],
             doc["lang"], doc["category"], h))
        for i, p in enumerate(doc["passages"], 1):
            conn.execute("INSERT INTO evidence_passages (doc_id, passage, seq) VALUES (?,?,?)",
                         (doc["doc_id"], p, i))
    conn.commit()
    n_inst = conn.execute("SELECT COUNT(*) FROM institutions").fetchone()[0]
    n_rules = conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0]
    n_msgs = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    n_docs = conn.execute("SELECT COUNT(*) FROM evidence_documents").fetchone()[0]
    n_pass = conn.execute("SELECT COUNT(*) FROM evidence_passages").fetchone()[0]
    conn.close()
    print("OK -> %s | institutions=%d rules=%d messages=%d evidence_documents=%d evidence_passages=%d"
          % (DB.name, n_inst, n_rules, n_msgs, n_docs, n_pass))


if __name__ == "__main__":
    main()
