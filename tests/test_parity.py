# -*- coding: utf-8 -*-
"""一致性守门（两级）：
1) 快照完整性（包内可跑，必过）：tests/fixtures/snapshot-vectors.json 记录 pinned 快照
   在固定输入上的期望输出——engine/ 或 models/ 任何改动都会在此失败。
2) 训练侧逐位对拍（强校验，可选）：本机存在 public-v7 仓时，另对 v7 evolve.py 对拍。

运行：python3 tests/test_parity.py   →  PASS: N/N snapshot vectors match
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows GBK 控制台兼容；Jupyter 的 OutStream 无此方法，跳过

from engine import scorer  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "snapshot-vectors.json"
V7 = ROOT.parent / "public-v7"
TOL = 1e-9


def check_vectors(model, vectors, tag):
    mine = scorer.make_scorer(model)
    bad = 0
    for e in vectors:
        pred, _probs, p_cal, p_raw = mine(e["text"])
        if (abs(p_cal - e["p_cal"]) > TOL or abs(p_raw - e["p_raw"]) > TOL
                or pred != e["pred"]):
            bad += 1
            print("MISMATCH [%s] %s: got (%s, %r, %r) want (%s, %r, %r)"
                  % (tag, e["id"], pred, p_cal, p_raw, e["pred"], e["p_cal"], e["p_raw"]))
    return bad


def main():
    model = scorer.load_model(ROOT / "models" / "radar.json")

    # 1) 快照完整性（包内自包含）
    if not FIXTURES.exists():
        print("FAIL: 缺少 fixtures（%s）——仓库不完整" % FIXTURES.name)
        sys.exit(1)
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    n = len(fixtures["vectors"])
    bad = check_vectors(model, fixtures["vectors"], "snapshot")
    if bad:
        print("FAIL: %d/%d snapshot vectors mismatch —— engine/ 或 models/ 相对 fixtures 已被改动" % (bad, n))
        sys.exit(1)
    print("PASS: %d/%d snapshot vectors match（pinned 快照完整性）" % (n - bad, n))

    # 2) 训练侧强校验（仅当本机有 public-v7 仓）
    if not V7.exists():
        print("NOTE: 未找到 public-v7 仓（%s），跳过训练侧逐位对拍（包内快照守门已通过）" % V7)
        return
    sys.path.insert(0, str(V7 / "training"))
    import evolve  # noqa: E402
    theirs = evolve.make_scorer(json.loads((V7 / "models" / "radar.json").read_text(encoding="utf-8")))

    conn = sqlite3.connect(ROOT / "guardkit_evidence.sqlite")
    texts = {mid: text for mid, text in conn.execute("SELECT id, text FROM messages")}
    for p in sorted((V7 / "training").glob("blind-v*.jsonl"))[:4]:
        for r in evolve.load_jsonl(p)[:6]:
            texts[p.stem + ":" + r.get("id", "?")] = r["text"]
    conn.close()

    v7_bad = 0
    for key, text in texts.items():
        a, b = scorer.make_scorer(model)(text), theirs(text)
        if abs(a[2] - b[2]) > TOL or abs(a[3] - b[3]) > TOL or a[0] != b[0]:
            v7_bad += 1
            print("MISMATCH [v7] %s: mine=%s theirs=%s" % (key, a[2:4], b[2:4]))
    print("v7 training-side: checked %d texts, mismatches=%d" % (len(texts), v7_bad))
    sys.exit(1 if v7_bad else 0)


if __name__ == "__main__":
    main()
