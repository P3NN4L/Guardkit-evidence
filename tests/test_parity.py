# -*- coding: utf-8 -*-
"""一致性守门：仓内 pinned 快照（engine/scorer.py + models/radar.json）
↔ guard-kit v7 训练侧评分器（public-v7/training/evolve.py）逐位一致。

v7 仓存在时强校验；不存在（marker/CI 环境）时跳过并提示——仓自身可独立运行。
运行：python3 tests/test_parity.py
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import scorer  # noqa: E402

V7 = ROOT.parent / "public-v7"


def main():
    model = scorer.load_model(ROOT / "models" / "radar.json")
    mine = scorer.make_scorer(model)

    texts = {}
    if not V7.exists():
        print("SKIP: 未找到 public-v7 仓（%s），仓内快照自包含可独立运行" % V7)
        return
    sys.path.insert(0, str(V7 / "training"))
    import evolve  # noqa: E402
    theirs = evolve.make_scorer(json.loads((V7 / "models" / "radar.json").read_text(encoding="utf-8")))

    conn = sqlite3.connect(ROOT / "guardkit_evidence.sqlite")
    for mid, text in conn.execute("SELECT id, text FROM messages"):
        texts[mid] = text
    for p in sorted((V7 / "training").glob("blind-v*.jsonl"))[:4]:
        for r in evolve.load_jsonl(p)[:6]:
            texts[p.stem + ":" + r.get("id", "?")] = r["text"]
    conn.close()

    bad = 0
    for key, text in texts.items():
        a, b = mine(text), theirs(text)
        if abs(a[2] - b[2]) > 1e-9 or abs(a[3] - b[3]) > 1e-9 or a[0] != b[0]:
            bad += 1
            print("MISMATCH %s: mine=%s theirs=%s" % (key, a[2:4], b[2:4]))
    print("checked %d texts, mismatches=%d" % (len(texts), bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
