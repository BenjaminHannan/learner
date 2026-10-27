#!/usr/bin/env python3
"""ch-403 runner, scorer and marks (everyday-chat thread, 2026-09-26). New file only; never prints panel text.

Marks: artifacts/claude-ch403-20260926/PASSMARKS.md (sealed before the registered run).

run     one arm over a chat panel in the 382 format (items.jsonl or part*.jsonl). Each conversation gets a fresh agent
        (claude_panel382_run.make_agent); its turns go in order. Before EVERY turn the torch, numpy and python RNGs
        are seeded with TURN_SEED + a hash of (item_id, turn_i), the same in every arm, so X and X403 give the same
        reply on every turn until the change first acts (the 1B's chat samples are the only randomness).
        Row: {item_id, turn_i, kind, reply, ms, events, line, c403, c338}; line = the reply's class (pretend, honest,
        think_split, clarify, answer); c403/c338 = this turn's change in loop.chat403_stats / loop.chat338_stats.
          python -B scripts/claude_twinb_wrap.py scripts/claude_ch403_run.py run --panel-dir PD --arm A --name N \
              --model READER319 --gen-model BASE --out OUT
        A = claude_e2e02c:build_02c (X) | claude_ch403_agent:build_403 (X403) | twin (T, plain 1B, greedy).
score   counts per arm (M1, M3, M5 inputs and report-only counts) and the blind judge packets:
          pair_a  X403 vs X, only conversations whose transcripts differ (identical ones are ties by script)
          pair_b  X403 vs T, all conversations          pair_c  X vs T, all conversations (report only)
        order shuffled per conversation (seeds 4031, 4032, 4033); packets in files of 15 conversations; keys apart.
          python -B scripts/claude_ch403_run.py score --panel-dir PD --out OUT
marks   applies the keys to the judges' files and prints every mark against its bar.
          python -B scripts/claude_ch403_run.py marks --panel-dir PD --out OUT --judged JDIR
selftest  CPU only, no model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import shutil
import statistics
import sys
import tempfile
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

TURN_SEED = 403_000
EVERYDAY = ("smalltalk", "advice", "explain", "feelings", "followup", "think")
MEMORY = ("ask_known", "ask_unknown")
THINK_SPLIT = "I'm not sure. I worked it out a few times and got different answers."
PACKET = 15


def load_panel(pd: Path) -> list[dict]:
    files = sorted(pd.glob("part*.jsonl")) or [pd / "items.jsonl"]
    rows = []
    for f in files:
        rows += [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
    return sorted(rows, key=lambda r: r["item_id"])


def load(p: Path) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def line_class(reply: str) -> str:
    import claude_ch403_agent as N
    import claude_chat338_agent as C38
    import claude_vary330c as V
    r = reply.strip()
    if r == N.HYPO_REPLY:
        return "pretend"
    if r in V.HONEST_VARIANTS:
        return "honest"
    if r == THINK_SPLIT:
        return "think_split"
    if C38.gave_up(r):
        return "clarify"
    return "answer"


def turn_seed(item_id: str, ti: int) -> int:
    return TURN_SEED + int(hashlib.sha256(f"{item_id}|{ti}".encode()).hexdigest()[:8], 16)


def seed_all(s: int) -> None:
    random.seed(s)
    try:
        import numpy as np
        np.random.seed(s % (2 ** 32))
    except ImportError:
        pass
    try:
        import torch
        torch.manual_seed(s)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(s)
    except ImportError:
        pass


def _delta(a: dict | None, b: dict | None) -> dict:
    a, b = a or {}, b or {}
    return {k: b[k] - a.get(k, 0) for k in b if isinstance(b[k], int) and b[k] - a.get(k, 0)}


def run(a) -> None:
    import claude_e2e336_run as R
    import claude_panel382_run as P
    items = load_panel(Path(a.panel_dir))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"chat_{a.name}.jsonl"
    done = {json.loads(x)["item_id"] for x in path.read_text(encoding="utf-8").splitlines() if x.strip()} \
        if path.exists() else set()
    for it in items:
        if it["item_id"] in done:
            continue
        tmp = tempfile.mkdtemp(prefix=f"ch403-{a.name}-")
        rows = []
        try:
            agent = P.make_agent(a, tmp)
            for ti, t in enumerate(it["turns"]):
                c0 = dict(getattr(agent, "chat403_stats", {}) or {})
                s0 = dict(getattr(agent, "chat338_stats", {}) or {})
                seed_all(turn_seed(it["item_id"], ti))
                reply, ms, new = R.one(agent, t["text"])
                rows.append({"item_id": it["item_id"], "turn_i": ti, "kind": t["kind"], "reply": reply,
                             "ms": round(ms, 1), "events": len(new), "line": line_class(reply),
                             "c403": _delta(c0, getattr(agent, "chat403_stats", None)),
                             "c338": _delta(s0, getattr(agent, "chat338_stats", None))})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        with open(path, "a", encoding="utf-8") as fh:            # one conversation at a time: a crash keeps the rest
            fh.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        print(f"[ch403/{a.name}] {it['item_id']} turns={len(rows)} "
              f"lines={dict(Counter(r['line'] for r in rows))}", flush=True)


# ------------------------------------------------------------------ scoring
def arm_counts(rows: list[dict], items: dict) -> dict:
    import claude_e2e336_score as S
    import claude_panel382_run as P

    def turn(r):
        return items[r["item_id"]]["turns"][r["turn_i"]]
    ev = [r for r in rows if r["kind"] in EVERYDAY]
    known = [r for r in rows if r["kind"] == "ask_known"]
    unknown = [r for r in rows if r["kind"] == "ask_unknown"]
    think_num = [r for r in rows if r["kind"] == "think" and turn(r).get("gold_number") is not None]
    words = {k: statistics.median([len(r["reply"].split()) for r in rows if r["kind"] == k] or [0])
             for k in EVERYDAY}
    c403 = Counter()
    for r in rows:
        c403.update(r.get("c403") or {})
    return {
        "turns": len(rows),
        "stock_everyday": sum(1 for r in ev if r["line"] in ("pretend", "honest")),     # M1
        "lines_everyday": dict(Counter(r["line"] for r in ev)),
        "lines_memory": dict(Counter(r["line"] for r in rows if r["kind"] in MEMORY)),
        "ask_known": len(known), "ask_known_right": sum(P._vmatch(r["reply"], turn(r)["gold"]) for r in known),
        "ask_unknown": len(unknown),
        "ask_unknown_dont_know": sum(S.has(r["reply"].lower(), S.ABSTAIN_MARKERS) for r in unknown),
        "events_on_non_teach": sum(r["events"] for r in rows if r["kind"] != "teach"),
        "think_numeric": len(think_num),
        "think_numeric_right": sum(P._num_in(r["reply"], turn(r)["gold_number"]) for r in think_num),
        "median_words": words,
        "most_common_reply_count": max(Counter(r["reply"] for r in rows).values() or [0]),
        "ms_median": round(statistics.median([r["ms"] for r in rows]), 1) if rows else None,
        "c403": dict(c403),
    }


def convo(rows: list[dict], items: dict, iid: str) -> list[dict]:
    return [{"user": items[iid]["turns"][r["turn_i"]]["text"], "assistant": r["reply"]}
            for r in sorted((r for r in rows if r["item_id"] == iid), key=lambda r: r["turn_i"])]


def packets(first: str, other: str, arms: dict, items: dict, seed: int, only_diff: bool):
    rng = random.Random(seed)
    pk, key, same = [], {}, []
    for iid in sorted(items):
        c1, c2 = convo(arms[first], items, iid), convo(arms[other], items, iid)
        if only_diff and c1 == c2:
            same.append(iid)
            continue
        pair = [(first, c1), (other, c2)]
        rng.shuffle(pair)
        key[iid] = [pair[0][0], pair[1][0]]
        pk.append({"item_id": iid, "conversation_1": pair[0][1], "conversation_2": pair[1][1]})
    return pk, key, same


def first_diff_where(a_rows, b_rows, iid) -> str:
    """For a conversation that differs: did the first differing turn carry a ch-403 action (report only)?"""
    ar = sorted((r for r in a_rows if r["item_id"] == iid), key=lambda r: r["turn_i"])
    br = sorted((r for r in b_rows if r["item_id"] == iid), key=lambda r: r["turn_i"])
    for x, y in zip(ar, br):
        if x["reply"] != y["reply"]:
            return "change_acted" if (x.get("c403") or y.get("c403")) else "elsewhere"
    return "none"


def score(a) -> None:
    items = {it["item_id"]: it for it in load_panel(Path(a.panel_dir))}
    d = Path(a.out)
    arms = {x: load(d / f"chat_{x}.jsonl") for x in ("X403", "X", "T") if (d / f"chat_{x}.jsonl").exists()}
    summ = {"items": len(items), "turns": sum(len(it["turns"]) for it in items.values())}
    for x, rows in arms.items():
        summ[x] = arm_counts(rows, items)
    jd = d / "judge"
    jd.mkdir(exist_ok=True)
    for tag, other, seed, only_diff in (("a", "X", 4031, True), ("b", "T", 4032, False), ("c", "T", 4033, False)):
        first = "X" if tag == "c" else "X403"
        if first not in arms or other not in arms:
            continue
        pk, key, same = packets(first, other, arms, items, seed, only_diff)
        for i in range(0, len(pk), PACKET):
            (jd / f"pair_{tag}{i // PACKET + 1}.jsonl").write_text(
                "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pk[i:i + PACKET]), encoding="utf-8")
        (d / f"key_{tag}.json").write_text(json.dumps({"key": key, "identical": same}, indent=1), encoding="utf-8")
        summ[f"pair_{tag}"] = {"judged": len(pk), "identical": len(same),
                               "files": math.ceil(len(pk) / PACKET)}
        if tag == "a":
            summ["pair_a"]["first_difference"] = dict(Counter(first_diff_where(arms["X403"], arms["X"], iid)
                                                              for iid in key))
    (d / "summary.json").write_text(json.dumps(summ, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(summ, sort_keys=True))


# ------------------------------------------------------------------ marks
def judged(jdir: Path, tag: str, key: dict) -> dict:
    """{arm: wins, 'tie': n, 'madeup': {arm: n}, 'missing': [...]} from the judges' files for one pair set."""
    got = {}
    for f in sorted(jdir.glob(f"pair_{tag}*.out.jsonl")):
        for r in load(f):
            got[r["item_id"]] = r
    res = Counter()
    made = Counter()
    for iid, order in key["key"].items():
        r = got.get(iid)
        if r is None:
            res["missing"] += 1
            continue
        w = str(r.get("winner"))
        res[order[int(w) - 1] if w in ("1", "2") else "tie"] += 1
        made[order[0]] += int(r.get("madeup_1") or 0)
        made[order[1]] += int(r.get("madeup_2") or 0)
    res["tie"] += len(key.get("identical", []))
    return {"result": dict(res), "madeup": dict(made)}


def marks(a) -> None:
    d = Path(a.out)
    s = json.loads((d / "summary.json").read_text(encoding="utf-8"))
    jdir = Path(a.judged)
    x3, x = s["X403"], s["X"]
    ka = json.loads((d / "key_a.json").read_text(encoding="utf-8"))
    ja = judged(jdir, "a", ka)
    jb = judged(jdir, "b", json.loads((d / "key_b.json").read_text(encoding="utf-8")))
    jc = judged(jdir, "c", json.loads((d / "key_c.json").read_text(encoding="utf-8"))) \
        if (d / "key_c.json").exists() else None
    wa, la = ja["result"].get("X403", 0), ja["result"].get("X", 0)
    m = {}
    m["M1"] = ("INCONCLUSIVE" if x["stock_everyday"] < 8 else
               "PASS" if x3["stock_everyday"] <= x["stock_everyday"] // 4 else "FAIL",
               f"stock lines on everyday turns X403 {x3['stock_everyday']} vs X {x['stock_everyday']} "
               f"(bar X403 <= {x['stock_everyday'] // 4}; X < 8 = INCONCLUSIVE)")
    m["M2"] = ("INCONCLUSIVE" if len(ka["key"]) < 12 else "PASS" if wa - la >= 6 else "FAIL",
               f"blind pairs on the {len(ka['key'])} differing conversations: X403 won {wa}, X won {la}, "
               f"ties {ja['result'].get('tie', 0) - len(ka['identical'])} (+{len(ka['identical'])} identical); "
               f"bar X403 - X >= +6; fewer than 12 differing = INCONCLUSIVE")
    m["M3"] = ("PASS" if x3["ask_unknown_dont_know"] >= x["ask_unknown_dont_know"] - 1
               and x3["ask_known_right"] >= x["ask_known_right"] - 1 else "FAIL",
               f"never-told don't-know X403 {x3['ask_unknown_dont_know']} vs X {x['ask_unknown_dont_know']} of "
               f"{x['ask_unknown']}; told-and-asked right X403 {x3['ask_known_right']} vs X {x['ask_known_right']} "
               f"of {x['ask_known']}; bar each >= X - 1")
    ma3, ma = ja["madeup"].get("X403", 0), ja["madeup"].get("X", 0)
    m["M4"] = ("PASS" if ma3 <= ma else "FAIL",
               f"judged replies stating or assuming something about the user they never said, in the differing "
               f"pairs: X403 {ma3} vs X {ma}; bar X403 <= X")
    m["M5"] = ("PASS" if x3["events_on_non_teach"] <= x["events_on_non_teach"] else "FAIL",
               f"notebook events on non-teach turns X403 {x3['events_on_non_teach']} vs X {x['events_on_non_teach']}")
    verdict = "PASS" if all(v[0] == "PASS" for v in m.values()) else \
        "INCONCLUSIVE" if any(v[0] == "INCONCLUSIVE" for v in m.values()) and \
        not any(v[0] == "FAIL" for v in m.values()) else "FAIL"
    wb = jb["result"].get("X403", 0)
    c1 = ("PASS" if wb >= 40 else "FAIL",
          f"X403 vs T: X403 won {wb}, T won {jb['result'].get('T', 0)}, ties {jb['result'].get('tie', 0)}, "
          f"missing {jb['result'].get('missing', 0)}; bar X403 won >= 40 of 60")
    out = {"ch403": verdict, "marks": m, "C1": c1,
           "report": {"X_vs_T": jc, "made_up_X403_vs_T": jb["madeup"], "missing_a": ja["result"].get("missing", 0)}}
    (d / "marks.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


# ------------------------------------------------------------------ selftest
def selftest() -> None:
    import claude_ch403_agent as N
    assert line_class(N.HYPO_REPLY) == "pretend" and line_class(THINK_SPLIT) == "think_split"
    assert line_class("Honestly, I don't know. I don't think that's come up yet.") == "honest"
    assert line_class("Rainbows form when light bends.") == "answer"
    assert turn_seed("a", 1) == turn_seed("a", 1) != turn_seed("a", 2)
    items = {"c1": {"item_id": "c1", "turns": [{"text": "hi", "kind": "smalltalk", "gold": None, "gold_number": None},
                                                {"text": "what if?", "kind": "followup", "gold": None,
                                                 "gold_number": None}]},
             "c2": {"item_id": "c2", "turns": [{"text": "yo", "kind": "smalltalk", "gold": None, "gold_number": None}]}}
    base = [{"item_id": "c1", "turn_i": 0, "reply": "Hey!", "line": "answer", "c403": {}},
            {"item_id": "c1", "turn_i": 1, "reply": N.HYPO_REPLY, "line": "pretend", "c403": {}},
            {"item_id": "c2", "turn_i": 0, "reply": "Hi.", "line": "answer", "c403": {}}]
    new = [dict(base[0]), dict(base[1], reply="Then try again later.", line="answer",
                                   c403={"pretend_handed": 1, "pretend_replaced": 1}), dict(base[2])]
    pk, key, same = packets("X403", "X", {"X403": new, "X": base}, items, 4031, True)
    assert [p["item_id"] for p in pk] == ["c1"] and same == ["c2"] and sorted(key["c1"]) == ["X", "X403"]
    assert first_diff_where(new, base, "c1") == "change_acted"
    with tempfile.TemporaryDirectory() as t:
        jd = Path(t)
        w = "1" if key["c1"][0] == "X403" else "2"
        (jd / "pair_a1.out.jsonl").write_text(json.dumps({"item_id": "c1", "winner": w, "madeup_1": 0,
                                                          "madeup_2": 1}) + "\n", encoding="utf-8")
        r = judged(jd, "a", {"key": key, "identical": same})
        assert r["result"] == {"X403": 1, "tie": 1}, r
    print("ch-403 run selftest: 6/6 OK")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "score", "marks", "selftest"])
    ap.add_argument("--panel-dir", default="")
    ap.add_argument("--arm", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--model", default="", help="reader dir (agent arms)")
    ap.add_argument("--gen-model", default="", help="base MiniCPM5-1B dir")
    ap.add_argument("--mouth-model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--judged", default="")
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    elif a.cmd == "run":
        import os
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        if not (a.arm and a.name and a.out and a.gen_model and a.panel_dir):
            raise SystemExit("ch403: run needs --panel-dir, --arm, --name, --out and --gen-model")
        run(a)
    elif a.cmd == "score":
        score(a)
    else:
        marks(a)


if __name__ == "__main__":
    main()
