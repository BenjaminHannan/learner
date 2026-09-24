#!/usr/bin/env python3
"""333 runner: creativepanel333 on arms P (292t + creative333), B (292t), T (plain twin).
Marks: artifacts/claude-cre333-20260924/PASSMARKS.md. New file only; never prints panel text.

Each item gets a fresh agent: every turn in `turns` is sent, then `last` is sent and scored.
Output: <out>/arm_<A>.jsonl rows {item_id, kind, reply, last_events, stored_triples, ms,
cre333 (P only: stats delta)} and, with --score, summary.json plus the blind-judge packets
judge_creative.jsonl (arms P and T shuffled per item with a fixed seed; the key is in judge_key.json).

Usage (combined main + builder-outbox tree, like lis-313):
  python -B scripts/claude_cre333_run.py --panel DIR --arm P --gen-model <base MiniCPM5-1B dir> --out DIR
  python -B scripts/claude_cre333_run.py --panel DIR --arm B --out DIR
  python -B scripts/claude_cre333_run.py --panel DIR --arm T --gen-model <same dir> --out DIR
  python -B scripts/claude_cre333_run.py --panel DIR --score DIR
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def run(a):
    import claude_e2e336_run as R
    items = load(Path(a.panel) / "items.jsonl")
    gen = None
    if a.arm == "P":
        import claude_cre333_agent as C
        gen = C.Gen333(a.gen_model)
    rows = []
    for it in items:
        tmp = tempfile.mkdtemp(prefix=f"cre333-{a.arm}-")
        try:
            if a.arm == "T":
                import claude_e2e336_twin as TW
                agent = TW.Twin336(tmp, a.gen_model)
            else:
                agent = R.build_292t(tmp, a)
                if a.arm == "P":
                    C.install_creative333(agent, gen)
            for t in it["turns"]:
                agent.turn(t)
            s0 = dict(getattr(agent, "cre333_stats", {}) or {})
            reply, ms, new = R.one(agent, it["last"])
            row = {"item_id": it["item_id"], "kind": it["kind"], "reply": reply, "ms": round(ms, 1),
                   "last_events": len(new), "stored_triples": R.triples(agent)}
            if a.arm == "P":
                s1 = agent.cre333_stats
                row["cre333"] = {k: s1[k] - s0.get(k, 0) for k in s1 if s1[k] - s0.get(k, 0)}
            rows.append(row)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print(f"[333/{a.arm}] {it['item_id']}", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"arm_{a.arm}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                            encoding="utf-8")


def score(a):
    items = {it["item_id"]: it for it in load(Path(a.panel) / "items.jsonl")}
    d = Path(a.score)
    P = {r["item_id"]: r for r in load(d / "arm_P.jsonl")}
    B = {r["item_id"]: r for r in load(d / "arm_B.jsonl")}
    T = {r["item_id"]: r for r in load(d / "arm_T.jsonl")}
    cre = [i for i, it in items.items() if it["kind"] == "creative"]
    ctl = [i for i, it in items.items() if it["kind"] != "creative"]
    summ = {
        "creative_items": len(cre), "control_items": len(ctl),
        "P333.1_creative_events_P": sum(P[i]["last_events"] for i in cre),
        "P333.2_controls_equal_B": sum(1 for i in ctl if P[i]["reply"] == B[i]["reply"]
                                       and P[i]["stored_triples"] == B[i]["stored_triples"]),
        "P_creative_routed": sum(1 for i in cre if P[i].get("cre333", {}).get("creative_turns")),
        "P_controls_routed": sum(1 for i in ctl if P[i].get("cre333", {}).get("creative_turns")),
        "P_fallbacks": sum(P[i].get("cre333", {}).get("fallbacks", 0) for i in cre),
        "P_ms_creative_median": sorted(P[i]["ms"] for i in cre)[len(cre) // 2] if cre else None,
    }
    rng = random.Random(333)
    packets, key = [], {}
    for i in sorted(cre):
        pair = [("P", P[i]["reply"]), ("T", T[i]["reply"])]
        rng.shuffle(pair)
        key[i] = [pair[0][0], pair[1][0]]
        it = items[i]
        packets.append({"item_id": i, "chat": it["turns"], "request": it["last"],
                        "about_untaught_person": it.get("about_untaught_person"),
                        "reply_1": pair[0][1], "reply_2": pair[1][1]})
    (d / "judge_creative.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in packets),
                                            encoding="utf-8")
    (d / "judge_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    (d / "summary.json").write_text(json.dumps(summ, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(summ, sort_keys=True))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--arm", choices=["P", "B", "T"])
    ap.add_argument("--gen-model", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--score", default="")
    a = ap.parse_args()
    import os
    os.environ.setdefault("HF_HUB_OFFLINE", "1")      # never download mid-run
    if not a.score and a.arm in ("P", "B"):
        try:                                           # 292t's self-question router needs MiniLM on disk
            import fable_self122 as S122
            S122.route122("what is your name?")
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f"MISSING-CACHE: the self122 MiniLM router did not load ({exc!r}). Nothing was run.")
    if a.score:
        score(a)
    else:
        if a.arm in ("P", "T") and not a.gen_model:
            raise SystemExit("333: --gen-model is required for arms P and T")
        a.model = a.gen_model
        run(a)


if __name__ == "__main__":
    main()
