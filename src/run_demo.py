# -*- coding: utf-8 -*-
"""GuardKit Evidence——核心路径演示（课程仓版）。
贴消息 → v7 评分快照打分落库 → 证据检索 → 判决卡（CLI + HTML）→ 升级案件。

引擎来源：本仓 engine/scorer.py 是 guard-kit v7 评分组件的逐字 pinned 快照
（权重 models/radar.json = 公开包 @p3nn4l/guard-kit@7.0.0 的模型文件）。
一致性由 tests/test_parity.py 对拍 v7 训练侧评分器验证。

运行：python3 src/run_demo.py
输出：CLI 判决卡 + demo/verdict_cards.html（浏览器打开）
"""
import html
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from engine import scorer  # noqa: E402  pinned 快照（见模块头）

DB = ROOT / "guardkit_evidence.sqlite"
MODEL = scorer.load_model(ROOT / "models" / "radar.json")
SCORE = scorer.make_scorer(MODEL)
RAW_MID, RAW_HIGH = scorer.RAW_MID, scorer.RAW_HIGH
MODEL_VERSION = "radar v%s (pinned snapshot @7.0.0)" % MODEL["version"]

TYPE_LABELS = {"pay_first": "先转账后兑现", "impersonation": "冒充身份", "bait": "兼职/投资诱饵"}
BAND_LABEL = {"high": ("高危", "立即停止付款流程，按下方建议核实或升级"),
              "medium": ("可疑", "先不要转账；按下方建议核实后再决定"),
              "low": ("未识别风险", "仍建议按付款审批流程办事")}

# 检索用的关键词旁路（正式版为 SQLite FTS + embedding 对比，见 docs/plan.md WP3）
KEYWORDS = {
    "business_email_compromise": ["收款", "戶口", "账户", "账戶", "轉賬", "转账", "過數", "匯款",
                                   "供應商", "供应商", "換", "更換", "新", "審計", "审计", "尾數",
                                   "付款", "今日", "即刻", "盡快", "尽快", "核實", "核实"],
    "phishing_smishing": ["連結", "链接", "link", "登入", "login", "app", "hotline", "驗證",
                           "验证", "otp", "密碼", "密码", "sms", "銀行", "银行"],
}


def norm(t: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", t.lower())


def bigrams(t: str) -> set:
    t = norm(t)
    return {t[i:i + 2] for i in range(len(t) - 1)} if len(t) > 1 else {t}


def retrieve_evidence(conn, text: str, top_k: int = 2):
    """关键词 + 字符 bigram 重叠的混合检索（demo 级；正式版做 FTS/embedding 对比评估）。"""
    qb = bigrams(text)
    sql = "SELECT p.doc_id, p.passage, d.category, d.title, d.publisher, d.source_url, d.accessed_at FROM evidence_passages p JOIN evidence_documents d ON d.doc_id = p.doc_id"
    rows = conn.execute(sql).fetchall()
    scored = []
    for doc_id, passage, cat, title, publisher, url, acc in rows:
        kw = sum(1 for k in KEYWORDS.get(cat, []) if k in passage and k in text)
        overlap = len(qb & bigrams(passage)) / max(1, len(qb))
        score = kw * 2.0 + overlap * 8.0
        if score > 0:
            scored.append({"doc_id": doc_id, "passage": passage, "title": title,
                           "publisher": publisher, "url": url, "accessed_at": acc,
                           "score": round(score, 2)})
    scored.sort(key=lambda x: -x["score"])
    return scored[:top_k]


def whitelist_rule_of(t: str):
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


def save_verdict(conn, msg_id, p_raw, p_cal, band, top_type, wl):
    sql = "INSERT INTO verdicts (id, message_id, score, p_cal, band, top_type, whitelist_rule, model_version, created_at) VALUES (?,?,?,?,?,?,?,?,?)"
    conn.execute(sql, ("V-" + msg_id, msg_id, p_raw, p_cal, band, top_type, wl, MODEL_VERSION, datetime.now().isoformat(timespec="seconds")))
    conn.commit()


def cli_card(msg, p_raw, p_cal, band, top_type, wl, hits):
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
        print("官方依据（可溯源）：")
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


def html_card(msg, p_raw, p_cal, band, top_type, wl, hits):
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
    if "困难案例" in msg[5]:
        note = ('<div class="sec note">※ 本条为团队盲测卷中的已知困难案例（对话类误报）：引擎会误报，'
                '但工作流把结论交给人工而非自动拦截——这正是「triage → human review」设计的安全垫。</div>')
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
    msgs = conn.execute("SELECT id, text, lang, channel, received_at, source FROM messages ORDER BY id").fetchall()
    page = ['<html><head><meta charset="utf-8"><title>GuardKit Evidence · 判决卡原型</title><style>%s</style></head><body>' % CARD_CSS]
    page.append('<h2 style="max-width:640px;margin:8px auto 4px">GuardKit Evidence — 判决卡原型</h2>')
    page.append('<p style="max-width:640px;margin:0 auto 20px;font-size:13px;color:#667">'
                '三条演示消息：① 冒充供应商换账户（高危→升级人工）② 银行账单通知（机构白名单→放行）'
                '③ 假借钱测警觉性对话（已知困难案例→人工复核兜底）。证据全部来自真实官方页面，可点击溯源。</p>')
    n_saved = 0
    for msg in msgs:
        s = SCORE(msg[1])
        p_raw, p_cal, probs = s[3], s[2], (s[1] or {})
        top_type = max(((c, p) for c, p in probs.items() if c != "normal"), key=lambda x: x[1], default=(None, 0))[0]
        band = band_of(p_cal, p_raw)
        t = scorer.norm_text(msg[1])
        wl = whitelist_rule_of(t)
        if wl:  # 白名单压档与引擎同规则：压到可疑档以下
            p_raw = min(p_raw, MODEL["bands"]["mid"] - 0.01)
            p_cal = min(p_cal, MODEL["bands"]["mid"] - 0.01)
            band = band_of(p_cal, p_raw)
        hits = [] if wl else retrieve_evidence(conn, msg[1])
        save_verdict(conn, msg[0], p_raw, p_cal, band, top_type, wl)
        n_saved += 1
        cli_card(msg, p_raw, p_cal, band, top_type, wl, hits)
        page.append(html_card(msg, p_raw, p_cal, band, top_type, wl, hits))
    page.append('<p class="ftr">引擎：%s ｜ 评分快照与 guard-kit v7 训练侧逐位一致（tests/test_parity.py）｜ '
                '证据段落为官方页面逐字引用，附原文链接与抓取日期 ｜ 演示数据：MSG-001 为演示撰写，'
                'MSG-002/003 来自团队盲测卷（真实标注）。本原型不自动拦截任何消息，最终判断永远由人做出。</p>' % MODEL_VERSION)
    page.append('</body></html>')
    out = ROOT / "demo" / "verdict_cards.html"
    out.write_text("".join(page), encoding="utf-8")
    conn.close()
    print("\nHTML 判决卡 -> %s（浏览器打开）" % out.relative_to(ROOT))
    print("已落库判决 %d 条" % n_saved)


if __name__ == "__main__":
    main()
