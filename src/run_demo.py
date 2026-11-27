# -*- coding: utf-8 -*-
"""GuardKit Evidence——核心路径演示。
全量消息打分落库 → FTS5 证据检索 → 判决落库（含证据连接）→ 演示判决卡（CLI + HTML）。

引擎来源：本仓 engine/scorer.py 是 guard-kit v7 评分组件的逐字 pinned 快照
（权重 models/radar.json = 公开包 @p3nn4l/guard-kit@7.0.0 的模型文件）。
一致性由 tests/test_parity.py 对拍 v7 训练侧评分器验证。

检索：SQLite FTS5 + BM25（CJK 按字符 bigram 索引，unicode61；元数据过滤见 docs/queries.sql）。
落库：每条判决写 verdicts（含压档前原始分、命中规则外键）；
      非白名单判决的证据命中写 verdict_evidence（可 SQL 溯源）。

运行：python3 src/run_demo.py
输出：CLI 演示判决卡（MSG- 前缀 3 条）+ demo/verdict_cards.html（生成产物，重跑即刷新）
"""
import html
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows GBK 控制台兼容；Jupyter 的 OutStream 无此方法，跳过

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import textproc  # noqa: E402  与 build_db 索引侧共用的实现
from engine import scorer  # noqa: E402  pinned 快照（见模块头）

DB = ROOT / "guardkit_evidence.sqlite"
MODEL = scorer.load_model(ROOT / "models" / "radar.json")
SCORE = scorer.make_scorer(MODEL)
RAW_MID, RAW_HIGH = scorer.RAW_MID, scorer.RAW_HIGH
MODEL_ID = "radar"
MODEL_VERSION = "radar v%s (pinned snapshot @7.0.0)" % MODEL["version"]
RETRIEVAL_METHOD = "fts5-bm25-docagg"

TYPE_LABELS = {"pay_first": "先转账后兑现", "impersonation": "冒充身份", "bait": "兼职/投资诱饵"}
BAND_LABEL = {"high": ("高危", "立即停止付款流程，按下方建议核实或升级"),
              "medium": ("可疑", "先不要转账；按下方建议核实后再决定"),
              "low": ("未识别风险", "仍建议按付款审批流程办事")}

FAMILY_TO_RULE_ID = {"notice": "R-NOTICE", "domain": "R-DOMAIN", "institutional": "R-INSTITUTIONAL"}


def whitelist_rule_of(t: str):
    """与 pinned 引擎内部同规则（scorer.score 的白名单段）；返回家族名或 None。"""
    if scorer.NOTICE_TOPIC.search(t) and scorer.NOTICE_ADVICE.search(t):
        return "notice"
    if scorer.OFFICIAL_DOMAIN.search(t) and not scorer.BAD_URL_TOKEN.search(t):
        return "domain"
    if scorer.INSTITUTIONAL_TOPIC.search(t) and scorer.SAFE_CHANNEL.search(t) and not scorer.BAD_URL_TOKEN.search(t):
        return "institutional"
    return None


def band_of(p_cal: float, p_raw: float) -> str:
    if p_cal >= MODEL["bands"]["high"] and p_raw >= RAW_HIGH:
        return "high"
    if p_cal >= MODEL["bands"]["mid"] and p_raw >= RAW_MID:
        return "medium"
    return "low"


def retrieve_evidence(conn, text: str, top_k: int = 2):
    """FTS5/BM25 两阶段检索：
    ① SQL 完成 MATCH + bm25 排序（top 30 候选段落）；
    ② 证据以「整份通告」为单位竞争——advisory 被拆成多段后，单段短文本在
       bm25 下会输给样板话术密集的短通告，按文档聚合候选段得分修复该偏差。
    （SQLite 限制 bm25 不可进入聚合函数，故②的分组在应用层完成；
    应用层只做候选分组，无任何手调加权——权重全部来自标准 BM25。）"""
    q = textproc.fts_query(text)
    if not q:
        return []
    cands = conn.execute("SELECT d.doc_id, d.title, d.publisher, d.source_url, d.accessed_at, p.id, p.passage, bm25(evidence_fts) AS rel FROM evidence_fts f JOIN evidence_passages p ON p.id = f.rowid JOIN evidence_documents d ON d.doc_id = p.doc_id WHERE evidence_fts MATCH ? ORDER BY rel LIMIT 30", (q,)).fetchall()
    if not cands:
        return []
    docscore = {}
    for doc_id, _title, _pub, _url, _acc, _pid, _psg, rel in cands:
        docscore[doc_id] = docscore.get(doc_id, 0.0) - rel
    best = max(docscore, key=docscore.get)
    out = []
    for doc_id, title, publisher, url, accessed_at, pid, passage, rel in cands:
        if doc_id != best:
            continue
        out.append({"passage_id": pid, "passage": passage, "title": title,
                    "publisher": publisher, "url": url, "accessed_at": accessed_at,
                    "score": round(-rel, 4), "method": RETRIEVAL_METHOD})
        if len(out) >= top_k:
            break
    return out


SUSPICION_HINTS = [
    ("更換收款", "要求更改收款账户"), ("換咗收款戶口", "要求更改收款账户"), ("新戶口", "指定转入新银行账户"), ("新賬戶", "指定转入新银行账户"),
    ("過落呢個戶口", "指定转入陌生账户"), ("今日內", "制造限期压力（今日内/即将截止）"),
    ("即刻", "催促即时行动"), ("回覆呢個號碼", "引导脱离原有渠道联系"), ("審計已停用", "以审计/停用为由切断原有渠道"),
    ("急用", "制造紧急用钱场景"), ("手機壞咗", "以设备故障解释换号/换渠道"),
]


def suspicion_points(text: str, top_type):
    pts = [label for pat, label in SUSPICION_HINTS if pat in text]
    if top_type:
        pts.insert(0, "引擎判别大类：%s" % TYPE_LABELS.get(top_type, top_type))
    return pts[:4]


def save_verdict(conn, msg_id, p_raw, p_cal, band, top_type, wl, rule_id, raw_before, hits):
    """判决落库：生效分 + 压档前原始分 + 规则外键 + 证据连接（幂等，可重跑）。"""
    vid = "V-" + msg_id
    conn.execute("DELETE FROM verdict_evidence WHERE verdict_id = ?", (vid,))
    conn.execute("INSERT OR REPLACE INTO verdicts (id, message_id, score, p_cal, band, top_type, whitelist_rule, verdict_rule_id, score_raw_before_rule, model_id, model_version, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (vid, msg_id, p_raw, p_cal, band, top_type, wl, rule_id, raw_before, MODEL_ID, MODEL_VERSION, datetime.now().isoformat(timespec="seconds")))
    for rank, h in enumerate(hits, 1):
        conn.execute("INSERT INTO verdict_evidence (verdict_id, passage_id, rank, retrieval_method, score) VALUES (?,?,?,?,?)", (vid, h["passage_id"], rank, h["method"], h["score"]))
    conn.commit()


def cli_card(msg, p_cal, band, top_type, wl, hits):
    label, action = BAND_LABEL[band]
    line = "─" * 62
    print(line)
    print("判决卡 %s  [%s]" % (msg[0], msg[4]))
    print(line)
    print("消息：%s…" % msg[1][:46])
    print("来源：%s | 渠道：%s" % (msg[5], msg[3]))
    bar = "█" * int(p_cal * 20)
    print("风险分：%-4.2f/1.00 %s" % (p_cal, bar))
    print("档位：%s   引擎：%s" % (label, MODEL_VERSION))
    if wl:
        print("白名单：命中 %s 规则（三重条件，已压档）" % wl)
    pts = suspicion_points(msg[1], top_type)
    if pts:
        print("为什么：")
        for p in pts:
            print("  · " + p)
    if hits:
        print("官方依据（可溯源，已落库 verdict_evidence）：")
        for h in hits:
            print("  「%s…」" % h["passage"][:44])
            print("    —— %s《%s》 溯源：%s（抓取 %s）" % (h["publisher"], h["title"][:18], h["url"], h["accessed_at"]))
    print("建议动作：%s" % action)
    if band == "high":
        print("          升级：案件 V-%s 已生成（附本卡），转人工复核" % msg[0])
    print(line)


CARD_CSS = """
body{font-family:-apple-system,'PingFang TC','Microsoft JhengHei',sans-serif;background:#f0f2f5;margin:0;padding:24px;}
.card{max-width:640px;margin:0 auto 24px;background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.08);}
.head{padding:14px 20px;color:#fff;display:flex;justify-content:space-between;align-items:center;}
.band-high{background:#c0392b}.band-medium{background:#d48806}.band-low{background:#1e7e34}
.body{padding:18px 20px;}
.score{font-size:34px;font-weight:700;}
.meta{color:#667;font-size:12px;margin:2px 0 12px;}
.sec{margin:12px 0;font-size:14px;line-height:1.55;}
.sec h4{margin:0 0 6px;font-size:13px;color:#556;}
.quote{border-left:3px solid #cbd3dd;background:#f8fafc;padding:8px 12px;margin:8px 0;font-size:13px;color:#334;}
.src{font-size:12px;color:#778;margin-top:4px;}
.src a{color:#2a6bc9;}
.action{border:1px dashed #b9c2cf;border-radius:10px;padding:10px 14px;font-size:14px;background:#fbfcfe;}
.note{font-size:12px;color:#889;}
.ftr{max-width:640px;margin:0 auto;font-size:11px;color:#99a;line-height:1.6;}
"""


def html_card(msg, p_cal, band, top_type, wl, hits):
    label, action = BAND_LABEL[band]
    pts = suspicion_points(msg[1], top_type)
    ev = ""
    for h in hits:
        tpl = '<div class="quote">「%s」<div class="src">—— %s《%s》· <a href="%s" target="_blank">原文链接</a> · 抓取于 %s</div></div>'
        ev += tpl % (html.escape(h["passage"]), html.escape(h["publisher"]), html.escape(h["title"]), html.escape(h["url"]), h["accessed_at"])
    if not ev:
        ev = '<div class="note">本次未检索到足够相关的官方段落（检索无结果时如实显示，不硬凑依据）。</div>'
    wl_html = ('<div class="sec"><h4>白名单</h4>命中 <b>%s</b> 规则（主题×官方渠道×无可疑链接 三重条件），分数已按规则压档。</div>' % wl) if wl else ""
    why = "".join('<div>· %s</div>' % html.escape(p) for p in pts) or '<div class="note">未命中典型话术特征。</div>'
    note = ""
    if msg[6] and "困难案例" in msg[6]:
        note = ('<div class="sec note">※ %s：引擎会误报，'
                '但工作流把结论交给人工而非自动拦截——这正是「triage → human review」设计的安全垫。</div>' % html.escape(msg[6]))
    tpl = """
<div class="card">
  <div class="head band-%s"><div><b>判决卡 %s</b> · %s · %s</div><div style="font-size:20px;font-weight:700">%s</div></div>
  <div class="body">
    <div class="score">%.2f <span style="font-size:13px;color:#99a">/ 1.00 风险分（校准）</span></div>
    <div class="meta">消息来源：%s ｜ 渠道：%s ｜ 引擎：%s</div>
    <div class="sec"><h4>消息原文</h4>%s</div>
    <div class="sec"><h4>为什么可疑</h4>%s</div>
    %s
    <div class="sec"><h4>官方依据（可溯源）</h4>%s</div>
    <div class="action"><b>建议动作：</b>%s%s</div>
    %s
  </div>
</div>"""
    return tpl % (band, msg[0], msg[3], msg[4], label, p_cal, html.escape(msg[5]), msg[3], MODEL_VERSION,
                  html.escape(msg[1]), why, wl_html, ev, html.escape(action),
                  (" 升级：案件 V-%s 已生成（附本卡），转人工复核。" % msg[0]) if band == "high" else "", note)


def main():
    conn = sqlite3.connect(DB)
    msgs = conn.execute("SELECT id, text, lang, channel, received_at, source, note FROM messages ORDER BY id").fetchall()
    stats = {"high": 0, "medium": 0, "low": 0, "wl": 0, "evidence": 0}
    demo_rows = []  # (msg, p_cal, band, top_type, wl, hits)
    for msg in msgs:
        s = SCORE(msg[1])
        p_raw, p_cal, probs = s[3], s[2], (s[1] or {})
        top_type = max(((c, p) for c, p in probs.items() if c != "normal"), key=lambda x: x[1], default=(None, 0))[0]
        band = band_of(p_cal, p_raw)
        t = scorer.norm_text(msg[1])
        wl = whitelist_rule_of(t)
        rule_id = FAMILY_TO_RULE_ID.get(wl)
        raw_before = p_raw if wl else None  # 规则介入前的引擎原始分（审计链）
        if wl:  # 白名单压档与 pinned 引擎同规则：压到可疑档以下
            p_raw = min(p_raw, MODEL["bands"]["mid"] - 0.01)
            p_cal = min(p_cal, MODEL["bands"]["mid"] - 0.01)
            band = band_of(p_cal, p_raw)
        hits = [] if wl else retrieve_evidence(conn, msg[1])
        save_verdict(conn, msg[0], p_raw, p_cal, band, top_type, wl, rule_id, raw_before, hits)
        stats[band] += 1
        stats["wl"] += 1 if wl else 0
        stats["evidence"] += len(hits)
        if msg[0].startswith("MSG-"):
            demo_rows.append((msg, p_cal, band, top_type, wl, hits))

    n = len(msgs)
    print("已落库判决 %d 条：高危 %d / 可疑 %d / 未识别 %d；白名单放行 %d 条；"
          "证据连接 %d 条（verdict_evidence）" %
          (n, stats["high"], stats["medium"], stats["low"], stats["wl"], stats["evidence"]))

    page = ['<html><head><meta charset="utf-8"><title>GuardKit Evidence · 判决卡原型</title><style>%s</style></head><body>' % CARD_CSS]
    page.append('<h2 style="max-width:640px;margin:8px auto 4px">GuardKit Evidence — 判决卡原型</h2>')
    page.append('<p style="max-width:640px;margin:0 auto 8px;font-size:13px;color:#667">'
                '本库全量 %d 条消息已打分落库：高危 %d · 可疑 %d · 未识别 %d · 白名单放行 %d；'
                '判决与证据连接可在 SQLite 复查（docs/queries.sql）。'
                '以下展示 3 张演示判决卡：① 冒充供应商换账户（高危→升级人工）'
                '② 银行账单通知（机构白名单→放行）③ 假借钱测警觉性对话（已知困难案例→人工复核兜底）。'
                '证据全部来自真实官方页面，可点击溯源。</p>' %
                (n, stats["high"], stats["medium"], stats["low"], stats["wl"]))
    for msg, p_cal, band, top_type, wl, hits in demo_rows:
        print()
        cli_card(msg, p_cal, band, top_type, wl, hits)
        page.append(html_card(msg, p_cal, band, top_type, wl, hits))
    page.append('<p class="ftr">引擎：%s ｜ 评分快照与 guard-kit v7 训练侧逐位一致（tests/test_parity.py）｜ '
                '证据段落为官方页面逐字引用，附原文链接与抓取日期 ｜ 演示数据：MSG-001 为演示撰写，'
                'MSG-002/003 来自团队盲测卷（真实标注）。本原型不自动拦截任何消息，最终判断永远由人做出。</p>' % MODEL_VERSION)
    page.append('</body></html>')
    out = ROOT / "demo" / "verdict_cards.html"
    out.write_text("".join(page), encoding="utf-8")
    conn.close()
    print("\nHTML 判决卡 -> %s（浏览器打开；生成产物，重跑本脚本即刷新）" % out.relative_to(ROOT))


if __name__ == "__main__":
    main()
