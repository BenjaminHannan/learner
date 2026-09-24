#!/usr/bin/env python3
"""338 runner: chatpanel338 on arms P (330a + 334 + 333 + 338), B (the same without 338) and
T (the plain MiniCPM5-1B twin). Marks: artifacts/claude-chat338-20260924/PASSMARKS.md.
New file only; never prints panel text.

Each conversation gets a fresh agent; its turns are sent in order (no sleeps, no restarts).
Output: <out>/arm_<A>.jsonl, one row per turn {item_id, turn_i, kind, reply, ms, events,
chat338 (P only: stats delta)}; with --score: summary.json plus blind-judge packets
  judge_pair_T.jsonl / judge_pair_B.jsonl  per conversation, P and the other arm shuffled
                                           (fixed seed; keys in judge_key_T.json / judge_key_B.json)
  judge_turns_P.jsonl                      per conversation, P's replies, for the per-turn
                                           "natural and helpful" and invented-fact judges
  grammar_P.jsonl                          P's distinct replies, for the two grammar graders

Usage (combined main + builder-outbox tree, BensPC):
  python -B scripts/claude_chat338_run.py --panel DIR --arm B --model <lis-301 dir> --gen-model <MiniCPM5-1B dir> --out DIR
  python -B scripts/claude_chat338_run.py --panel DIR --arm P --model <lis-301 dir> --gen-model <same> --out DIR
  python -B scripts/claude_chat338_run.py --panel DIR --arm T --gen-model <same> --out DIR
  python -B scripts/claude_chat338_run.py --panel DIR --score DIR
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import statistics
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def build_B(state_dir, args):
    import claude_e2e330_arms as A
    return A.build_330a_cre(state_dir, args)


_G338: dict = {}


def build_P(state_dir, args):
    import claude_chat338_agent as C
    import claude_e2e330_arms as A
    loop = A.build_330a_cre(state_dir, args)
    if args.gen_model not in _G338:
        _G338[args.gen_model] = C.Gen338(share=A._gen(args.gen_model))
    C.install_chat338(loop, _G338[args.gen_model])
    return loop


def run(a):
    import claude_e2e336_run as R
    items = load(Path(a.panel) / "items.jsonl")
    rows = []
    for it in items:
        tmp = tempfile.mkdtemp(prefix=f"chat338-{a.arm}-")
        try:
            if a.arm == "T":
                import claude_e2e336_twin as TW
                agent = TW.Twin336(tmp, a.gen_model)
            else:
                agent = (build_P if a.arm == "P" else build_B)(tmp, a)
            for i, t in enumerate(it["turns"]):
                s0 = dict(getattr(agent, "chat338_stats", {}) or {})
                reply, ms, new = R.one(agent, t["text"])
                row = {"item_id": it["item_id"], "turn_i": i, "kind": t["kind"], "reply": reply,
                       "ms": round(ms, 1), "events": len(new)}
                if a.arm == "P":
                    s1 = agent.chat338_stats
                    row["chat338"] = {k: s1[k] - s0.get(k, 0) for k in s1 if s1[k] - s0.get(k, 0)}
                rows.append(row)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print(f"[338/{a.arm}] {it['item_id']}", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"arm_{a.arm}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                            encoding="utf-8")


def _vmatch(text, value):
    v = str(value).strip().lower()
    return bool(v) and re.search(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])", text.lower()) is not None


def score(a):
    import claude_chat338_agent as C
    import claude_e2e336_score as S
    items = {it["item_id"]: it for it in load(Path(a.panel) / "items.jsonl")}
    d = Path(a.score)
    arms = {x: load(d / f"arm_{x}.jsonl") for x in ("P", "B", "T") if (d / f"arm_{x}.jsonl").exists()}
    summ = {"conversations": len(items)}
    for x, rows in arms.items():
        n = len(rows)
        gave = sum(1 for r in rows if C.gave_up(r["reply"]))
        known = [r for r in rows if r["kind"] == "ask_known"]
        unknown = [r for r in rows if r["kind"] == "ask_unknown"]
        ms = [r["ms"] for r in rows]
        summ[x] = {
            "turns": n,
            "P338.2_gave_up_or_canned_turns": gave,
            "events_on_non_teach_turns": sum(r["events"] for r in rows if r["kind"] != "teach"),
            "ask_known_right": sum(1 for r in known
                                   if _vmatch(r["reply"], items[r["item_id"]]["turns"][r["turn_i"]]["gold"])),
            "ask_known": len(known),
            "ask_unknown_dont_know": sum(1 for r in unknown if S.has(r["reply"].lower(), S.ABSTAIN_MARKERS)),
            "ask_unknown": len(unknown),
            "distinct_replies": len({r["reply"] for r in rows}),
            "most_common_reply_count": max(
                [sum(1 for q in rows if q["reply"] == r["reply"]) for r in rows] or [0]),
            "ms_median": round(statistics.median(ms), 1) if ms else None,
            "ms_p90": round(sorted(ms)[int(0.9 * (len(ms) - 1))], 1) if ms else None,
        }
        if x == "P":
            tot: dict = {}
            for r in rows:
                for k, v in r.get("chat338", {}).items():
                    tot[k] = tot.get(k, 0) + v
            summ["P"]["chat338"] = tot

    def convo(x, iid):
        return [{"user": items[iid]["turns"][r["turn_i"]]["text"], "assistant": r["reply"]}
                for r in arms[x] if r["item_id"] == iid]

    if "P" in arms:
        for other in ("T", "B"):
            if other not in arms:
                continue
            rng = random.Random(338)
            packets, key = [], {}
            for iid in sorted(items):
                pair = [("P", convo("P", iid)), (other, convo(other, iid))]
                rng.shuffle(pair)
                key[iid] = [pair[0][0], pair[1][0]]
                packets.append({"item_id": iid, "conversation_1": pair[0][1], "conversation_2": pair[1][1]})
            (d / f"judge_pair_{other}.jsonl").write_text(
                "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in packets), encoding="utf-8")
            (d / f"judge_key_{other}.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
        (d / "judge_turns_P.jsonl").write_text("".join(
            json.dumps({"item_id": iid, "conversation": convo("P", iid)}, ensure_ascii=False) + "\n"
            for iid in sorted(items)), encoding="utf-8")
        (d / "grammar_P.jsonl").write_text("".join(
            json.dumps({"reply": x}, ensure_ascii=False) + "\n"
            for x in sorted({r["reply"] for r in arms["P"] if r["reply"]})), encoding="utf-8")
    (d / "summary.json").write_text(json.dumps(summ, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(summ, sort_keys=True))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--arm", choices=["P", "B", "T"])
    ap.add_argument("--model", default="", help="lis-301 reader dir (arms P and B)")
    ap.add_argument("--gen-model", default="", help="base MiniCPM5-1B dir")
    ap.add_argument("--mouth-model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--score", default="")
    a = ap.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")      # never download mid-run
    if a.score:
        score(a)
        return
    if not a.gen_model or (a.arm in ("P", "B") and not a.model):
        raise SystemExit("338: --gen-model (all arms) and --model (arms P, B) are required")
    if a.arm in ("P", "B"):
        try:                                           # 292t's self-question router needs MiniLM on disk
            import fable_self122 as S122
            S122.route122("what is your name?")
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f"MISSING-CACHE: the self122 MiniLM router did not load ({exc!r}). Nothing was run.")
    run(a)


if __name__ == "__main__":
    main()
