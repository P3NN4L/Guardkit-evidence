# -*- coding: utf-8 -*-
"""构建 60 例评估集（常规 30 + 困难 30）。
产出：evaluation/60cases.csv（用例清单 + 期望 + 观测 + 是否命中）、evaluation/60cases-summary.txt（构成统计）。
抽取是确定性的（按 msg_id 排序轮转填充），重跑结果不变；期望标签取自 messages.label 真值，观测取自 verdicts。
运行：python3 evaluation/build_60cases.py（任意目录均可）
"""
import csv
import io
import sqlite3
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT_CASES = ROOT / "evaluation" / "60cases.csv"
OUT_SUM = ROOT / "evaluation" / "60cases-summary.txt"
DB = ROOT / "guardkit_evidence.sqlite"

HARD_QUOTA = 30
NORM_QUOTA = 30
HARD_ORDER = ["困难-漏报", "困难-误报", "困难-已知困难案例", "困难-分布外BEC"]


def classify(label, band, note, src, flagged):
    """给每条消息定候选池标签（决定它进哪个池）。"""
    hard_note = bool(note and ("困难" in note or "误报" in note))
    if label == "scam" and band == "low":
        return "困难-漏报"                    # 真骗局被放行（引擎盲区实证）
    if label == "normal" and flagged:
        return "困难-误报"                    # 正常被拦下（误报大类实证）
    if hard_note:
        return "困难-已知困难案例"             # 盲测卷标注的已知困难案例
    if src.startswith("public-nazario"):
        return "困难-分布外BEC"                # 爬取的真实英文长邮件（分布外）
    if label == "scam":
        return "常规-scam"
    return "常规-normal"


def main():
    if not DB.exists():
        print("未找到 guardkit_evidence.sqlite —— 请先运行 python3 src/build_db.py")
        sys.exit(2)
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT m.id, m.lang, m.label, v.band, m.note, m.source, m.synthetic_derived FROM messages m JOIN verdicts v ON v.message_id = m.id WHERE m.label IS NOT NULL ORDER BY m.id").fetchall()

    pools = {}
    meta = {}
    excluded_demo = 0
    for mid, lang, label, band, note, src, syn in rows:
        if src.startswith("demo") or syn:
            excluded_demo += 1   # 评估集必须全真实：演示消息（demo:* 前缀）与生成成分消息（synthetic_derived=1）一律不入池
            continue
        flagged = 1 if band in ("high", "medium") else 0
        cat = classify(label, band, note or "", src, flagged)
        pools.setdefault(cat, []).append(mid)
        meta[mid] = (lang, label, band, note or "", src)

    used = set()
    hard_pick = []
    for cat in HARD_ORDER:
        for mid in sorted(pools.get(cat, [])):
            if len(hard_pick) >= HARD_QUOTA:
                break
            if mid not in used:
                hard_pick.append((cat, mid))
                used.add(mid)
    fills = sorted(pools.get("常规-scam", []))
    fi = 0
    while len(hard_pick) < HARD_QUOTA and fi < len(fills):
        mid = fills[fi]
        fi += 1
        if mid not in used:
            hard_pick.append(("困难-补位(常规scam)", mid))
            used.add(mid)

    norm_pick = []
    for cat, quota in (("常规-scam", 15), ("常规-normal", 15)):
        taken = 0
        for mid in sorted(pools.get(cat, [])):
            if taken >= quota or len(norm_pick) >= NORM_QUOTA:
                break
            if mid not in used:
                norm_pick.append((cat, mid))
                used.add(mid)
                taken += 1
    rest = sorted(pools.get("常规-normal", []))
    ri = 0
    while len(norm_pick) < NORM_QUOTA and ri < len(rest):
        mid = rest[ri]
        ri += 1
        if mid not in used:
            norm_pick.append(("常规-normal", mid))
            used.add(mid)

    out = []
    n = 0
    for stratum, picked in (("常规", norm_pick), ("困难", hard_pick)):
        for cat_actual, mid in picked:
            n += 1
            lang, label, band, note, src = meta[mid]
            observed = "flagged" if band in ("high", "medium") else "released"
            expected_action = "flagged" if label == "scam" else "released"
            match = "Y" if observed == expected_action else "N"
            ev = conn.execute("SELECT COUNT(*) FROM verdict_evidence ve JOIN verdicts v ON v.id = ve.verdict_id WHERE v.message_id = ?", (mid,)).fetchone()[0]
            out.append({
                "case_id": "C%02d" % n, "stratum": stratum, "category": cat_actual,
                "msg_id": mid, "lang": lang, "expected_label": label,
                "observed_band": band, "observed_action": observed,
                "expected_vs_observed": match, "evidence_linked": ev,
                "note": note, "source": src,
            })
    conn.close()

    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)
    OUT_CASES.write_text(buf.getvalue(), encoding="utf-8-sig")

    total = len(out)
    scam_n = sum(1 for r in out if r["expected_label"] == "scam")
    scam_hit = sum(1 for r in out if r["expected_label"] == "scam" and r["observed_action"] == "flagged")
    norm_rel = sum(1 for r in out if r["expected_label"] == "normal" and r["observed_action"] == "released")
    match_n = sum(1 for r in out if r["expected_vs_observed"] == "Y")
    hard_cats = sorted({r["category"] for r in out if r["stratum"] == "困难"})
    hard_stat = ", ".join("%s=%d" % (cat, sum(1 for r in out if r["category"] == cat)) for cat in hard_cats)
    langs = {}
    for r in out:
        langs[r["lang"]] = langs.get(r["lang"], 0) + 1
    lang_stat = ", ".join("%s=%d" % (k, v) for k, v in sorted(langs.items()))

    lines = [
        "60 例评估集构成（expected vs observed）",
        "总数=%d（常规 %d + 困难 %d）；全部来自真实消息池（演示消息已排除 %d 条）" % (total, NORM_QUOTA, HARD_QUOTA, excluded_demo),
        "expected=scam: %d 例，observed flagged %d（召回 %d/%d）" % (scam_n, scam_hit, scam_hit, scam_n),
        "expected=normal: %d 例，observed released %d" % (total - scam_n, norm_rel),
        "整体命中率 %d/%d" % (match_n, total),
        "困难构成：" + hard_stat,
        "语言构成：" + lang_stat,
        "（确定性抽取：重跑本脚本结果不变；期望=人工真值，观测=当前 pinned 引擎判决）",
    ]
    OUT_SUM.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("")
    print("OK -> %s + %s" % (OUT_CASES.as_posix(), OUT_SUM.as_posix()))


if __name__ == "__main__":
    main()
