#!/usr/bin/env python3
"""rt-02d: chat route to the slept puzzle skill (month-end line, 2026-09-26; fix A agreed with Fix sleep). New file only.

Marks: artifacts/claude-rt02d-20260926/PASSMARKS-rt02d.md (registered before this code). Written on DEV wordings only;
the TEST panel artifacts/claude-panel-rt02d-20260926 is never opened here except by run --task puzzles/negatives.

What: when a user turn is a number puzzle (a target and the 3-4 numbers to use), the turn goes to the 1B's puzzle
prompt with the rule-keeper (claude_blurt2.Solver.generate on the agent's own shared 1B, the doorway the sleep nights
train): one greedy answer, then up to N_TRIES sampled answers at T 1.5 (the nights' TEST setting), each checked with
the exact checker (claude_blurt1.check). The reply gives the first checked expression; if none checks, it says it
could not find one and never states an unchecked answer. Every other turn goes to the agent unchanged.

  build_rt02d      = claude_e2e02c.build_02c + route (the adapter as installed by 0.2c)
  build_rt02d_off  = the same, with every LoRA scale at 0 during the route's call only (B1off, the plain 1B)

The route wraps the finished agent's turn (outermost), so build_02c stays untouched. A routed turn is not seen by
the agent's inner layers (reader, turn log, delivered history); report-only limitation.

  python -B scripts/claude_rt02d.py --selftest                    (no model; parser on dev wordings + negatives)
  python -B scripts/claude_twinb_wrap.py scripts/claude_rt02d.py run --task puzzles|negatives|general|chatdev \
      --arm claude_e2e02c:build_02c|claude_rt02d:build_rt02d|claude_rt02d:build_rt02d_off --name B0|B1|B1off \
      --model READER319 --gen-model BASE --out OUT [--panel-dir PD]
  python -B scripts/claude_rt02d.py score --out OUT --score SCOREDIR
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

N_TRIES = 20              # sampled answers after a failed greedy one (the nights' TEST uses 20 guesses)
TEMP = 1.5                # the nights' guess temperature (claude_dl1_nights.TEMP)
SEED_BASE = 402_026       # per-puzzle sampling seed = SEED_BASE + a hash of (nums, target): same for B1 and B1off
TURN_SEED = 402_027       # per-turn torch seed set by the runner before every turn, the same in every arm

_INT = re.compile(r"(?<![\d.])\d+(?!\d|\.\d)")
_TARGET = re.compile(
    r"(?:make|makes|making|get|gets|getting|reach|reaches|equal|equals|equalling|equaling|=|hit|hits|total|totals|"
    r"totalling|totaling|sum to|sums to|come out to|comes out to|come out as|end up with|end up at|end up as|"
    r"arrive at|land on|produce|produces|give|gives|giving|result in|results in|become|becomes|turn into|into|"
    r"has to be|have to be|must be|should be|needs to be|need to be|answer is|target is|target of|goal is|->|→)"
    r"\s+(?:to\s+|at\s+|as\s+|exactly\s+|up\s+with\s+|a\s+total\s+of\s+|the\s+number\s+)?(\d+)(?!\d|\.\d)", re.I)
_OPS = re.compile(r"[+*/×÷]|\b(?:add|adding|addition|plus|subtract|subtracting|subtraction|minus|multipl\w*|divid\w*|"
                  r"division|times|arithmetic|operations?|operators?|puzzle|brackets?|parenthes[ie]s|each number|"
                  r"each of (?:the|these|those)|exactly once|only once|each once|once each|combine|combining)\b", re.I)
_LIST = re.compile(r"\d+(?:\s*,\s*|\s+and\s+|\s+|\s*;\s*)\d+(?:\s*,\s*|\s*,?\s+and\s+|\s+|\s*;\s*)\d+")
_ASK = re.compile(r"\?|\b(?:can you|could you|can u|could u|please|pls|plz|help|how (?:can|do|would)|find|solve|show me|figure|work out|help me)\b", re.I)


def parse_puzzle(text: str):
    """{'nums': sorted list, 'target': int} if the turn asks for a number puzzle, else None (rules; dev-tuned)."""
    t = text.replace("−", "-")
    ints = [(m.start(), int(m.group(0))) for m in _INT.finditer(t)]
    if not 4 <= len(ints) <= 5:
        return None
    tm = list(_TARGET.finditer(t))
    if not tm:
        return None
    tgt_pos, target = tm[-1].start(1), int(tm[-1].group(1))
    nums = [v for pos, v in ints if pos != tgt_pos]
    if len(nums) not in (3, 4) or len(nums) != len(ints) - 1:
        return None
    if not all(1 <= v <= 13 for v in nums) or not 1 <= target <= 100:
        return None
    if not (_OPS.search(t) or (_LIST.search(t) and _ASK.search(t))):
        return None
    return {"nums": sorted(nums), "target": target}


def _seed(p) -> int:
    h = hashlib.sha256(json.dumps([p["nums"], p["target"]]).encode()).hexdigest()
    return SEED_BASE + int(h[:8], 16) % 100_000


def solve_route(one_b, p, lora_off: bool = False) -> dict:
    """Greedy, then up to N_TRIES sampled answers, each checked; the first checked one wins."""
    import claude_blurt1 as B1
    import claude_sleep02c as SL
    s = SL.solver_shim(one_b)
    mods = SL.lora_mods(one_b.model)
    saved = [x.scale for x in mods]
    if lora_off:
        for x in mods:
            x.scale = 0.0
    try:
        g = s.generate(p, 1, None)[0]
        if B1.check(g, p["nums"], p["target"]):
            return {"expr": g.split("=")[0].strip(), "how": "greedy", "tries": 1}
        s.torch.manual_seed(_seed(p))
        for i, t in enumerate(s.generate(p, N_TRIES, TEMP)):
            if B1.check(t, p["nums"], p["target"]):
                return {"expr": t.split("=")[0].strip(), "how": "sampled", "tries": 2 + i}
        return {"expr": "", "how": "none", "tries": 1 + N_TRIES}
    finally:
        for x, sc in zip(mods, saved):
            x.scale = sc


def reply_for(p, res) -> str:
    if res["expr"]:
        return f"Here's one way that works: {res['expr']} = {p['target']}."
    ns = ", ".join(str(n) for n in p["nums"][:-1]) + " and " + str(p["nums"][-1])
    return f"I tried, but I couldn't find a way to make {p['target']} from {ns} that I could check."


def install_rt02d(loop, one_b, lora_off: bool = False) -> None:
    inner = loop.turn
    loop.rt02d_stats = {"routed": 0, "solved": 0}
    loop.rt02d_last = None

    def turn_rt02d(text: str) -> list[str]:
        p = parse_puzzle(text or "")
        if p is None:
            loop.rt02d_last = None
            return inner(text)
        res = solve_route(one_b, p, lora_off)
        loop.rt02d_stats["routed"] += 1
        loop.rt02d_stats["solved"] += int(bool(res["expr"]))
        loop.rt02d_last = {"parsed": p, **res}
        return [reply_for(p, res)]

    turn_rt02d.__name__ = "turn_rt02d"
    loop.turn = turn_rt02d


def _build(state_dir, args, lora_off):
    import claude_e2e02c as E02C
    import claude_e2e330_arms as A
    loop = E02C.build_02c(state_dir, args)
    install_rt02d(loop, A._GEN[args.gen_model], lora_off)
    loop.layers330c = list(getattr(loop, "layers330c", []) or []) + ["rt02d" + ("off" if lora_off else "")]
    return loop


def build_rt02d(state_dir, args):
    return _build(state_dir, args, False)


def build_rt02d_off(state_dir, args):
    return _build(state_dir, args, True)


# ------------------------------------------------------------------ runner
def _load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def _determinism():
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    import torch
    torch.use_deterministic_algorithms(True, warn_only=True)
    return torch


def _conversations(a) -> list[tuple[str, list[str]]]:
    """[(conv_id, [user texts])] for the task; every conversation starts with a fresh agent."""
    if a.task == "puzzles":
        return [(r["id"], [r["text"]]) for r in _load(Path(a.panel_dir) / "chat_puzzles.jsonl")]
    if a.task == "negatives":
        return [(r["id"], [r["text"]]) for r in _load(Path(a.panel_dir) / "negatives.jsonl")]
    if a.task == "general":
        import claude_dl1_nights as D1
        return [(f"gen-{i:03d}", [it["q"]]) for i, it in enumerate(D1.harm_panel())]
    if a.task == "chatdev":
        items = _load(Path(a.panel_dir or "artifacts/claude-panel382-dev-20260925/chat") / "items.jsonl")
        return [(it["item_id"], [t["text"] for t in it["turns"]]) for it in items]
    if a.task == "dev":
        return [(f"dev-{i:03d}", [t]) for i, (t, _) in enumerate(dev_cases())]
    raise SystemExit(f"unknown task {a.task}")


def run(a) -> None:
    torch = _determinism()
    mod, fn = a.arm.split(":")
    build = getattr(importlib.import_module(mod), fn)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{a.task}_{a.name}.jsonl"
    if path.exists():
        raise SystemExit(f"rt02d: {path} exists (each run is launched once)")
    rows = []
    for cid, texts in _conversations(a):
        tmp = tempfile.mkdtemp(prefix=f"rt02d-{a.name}-")
        try:
            agent = build(tmp, a)
            for ti, text in enumerate(texts):
                torch.manual_seed(TURN_SEED + ti)
                t0 = time.time()
                parts = agent.turn(text)
                ms = (time.time() - t0) * 1000
                last = getattr(agent, "rt02d_last", None)
                rows.append({"id": cid, "turn_i": ti, "reply": " ".join(x for x in (parts or []) if x),
                             "routed": last is not None, "route": last, "ms": round(ms, 1)})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"task": a.task, "name": a.name, "rows": len(rows),
                      "routed": sum(r["routed"] for r in rows)}), flush=True)


# ------------------------------------------------------------------ score (counts only; never prints panel text)
def score(a) -> None:
    import claude_blurt1 as B1
    import claude_panel382_run as P
    out = Path(a.out)
    truth = {r["id"]: r for r in _load(Path(a.panel_dir) / "chat_puzzles.jsonl")}

    def rows(task, name):
        f = out / f"{task}_{name}.jsonl"
        return _load(f) if f.exists() else None

    solved = {}
    for name in ("B0", "B1", "B1off"):
        r = rows("puzzles", name)
        if r is not None:
            solved[name] = sum(int(P.puzzle_solved(x["reply"], truth[x["id"]]["nums"], truth[x["id"]]["target"]))
                               for x in r)
    b1 = rows("puzzles", "B1") or []
    by_wording = {}
    for x in b1:
        w = truth[x["id"]]["wording_id"]
        d = by_wording.setdefault(w, {"n": 0, "routed": 0, "solved": 0})
        d["n"] += 1
        d["routed"] += int(x["routed"])
        d["solved"] += int(P.puzzle_solved(x["reply"], truth[x["id"]]["nums"], truth[x["id"]]["target"]))
    dishonest = 0
    for x in b1:
        if x["routed"] and x["route"] and x["route"].get("expr"):
            tr = truth[x["id"]]
            if not B1.check(x["route"]["expr"], tr["nums"], tr["target"]):
                dishonest += 1
    neg = rows("negatives", "B1")
    fires_neg = sum(int(x["routed"]) for x in neg) if neg is not None else None
    r4 = {}
    for task in ("general", "chatdev"):
        b0, b1t = rows(task, "B0"), rows(task, "B1")
        if b0 is None or b1t is None:
            r4[task] = None
            continue
        k0 = {(x["id"], x["turn_i"]): x["reply"] for x in b0}
        diff = sum(1 for x in b1t if not x["routed"] and k0.get((x["id"], x["turn_i"])) != x["reply"])
        r4[task] = {"turns": len(b1t), "fired": sum(int(x["routed"]) for x in b1t), "differ_unrouted": diff}
    res = {"solved": solved, "fires_negatives": fires_neg, "no_harm": r4, "dishonest": dishonest,
           "by_wording": by_wording,
           "ms_routed_median": _median([x["ms"] for x in b1 if x["routed"]]),
           "how": {h: sum(1 for x in b1 if x["route"] and x["route"].get("how") == h)
                   for h in ("greedy", "sampled", "none")}}
    s0, s1, s1o = solved.get("B0"), solved.get("B1"), solved.get("B1off")
    g, c = r4.get("general"), r4.get("chatdev")
    res["marks"] = {
        "R1": None if s1 is None or s0 is None else (s1 >= 8 and s1 - s0 >= 6),
        "R2": None if s1 is None or s1o is None else (s1 - s1o >= 4),
        "R3": None if fires_neg is None else fires_neg <= 2,
        "R4": None if g is None or c is None else (g["fired"] <= 3 and g["differ_unrouted"] == 0
                                                   and c["differ_unrouted"] == 0),
        "R5": dishonest == 0 if b1 else None}
    res["pass"] = all(v is True for v in res["marks"].values())
    sd = Path(a.score)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "rt02d_score.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({"solved": solved, "marks": res["marks"], "pass": res["pass"]}))


def _median(v):
    v = sorted(v)
    return None if not v else (v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2)


# ------------------------------------------------------------------ dev cases (written by me; never the TEST panel)
DEV_WORDINGS = [
    "Can you solve this number puzzle? Use each of the numbers {L} exactly once, with + - * / and brackets, to make "
    "{T}. Give the expression.",                                                     # 0.2c's CHAT_ASK
    "Quick one: how do I get {T} out of {L}? Each number once.",
    "Using {L}, make {T} with add, subtract, multiply or divide.",
    "I'm stuck on a math puzzle - the numbers are {L} and the answer has to be {T}. Help?",
    "{L} -> {T}, using + - * / only, every number exactly once. What's the expression?",
    "hey can u make {T} from {L}",
    "My teacher gave us {L}. We have to combine them to equal {T}. How?",
    "Find an expression with {L} (each once) that equals {T}.",
]
DEV_NEGATIVES = [
    "I have 3 kids aged 4, 7 and 9.",
    "The meeting moved from 2 to 3 on Friday the 12th.",
    "Can you make dinner for 6 people? I have 2 chickens and 4 potatoes.",
    "I ran 5 miles on Monday, 3 on Tuesday and 8 today, trying to get to 20 this week.",
    "We scored 12 points in the first half and 9 in the second, final score 21 to 18.",
    "What is 7 times 8?",
    "My flight is at 6:45 and lands at 9:10.",
    "Buy 2 apples, 3 pears and 5 bananas for the party at 7.",
    "Room 12 has 4 beds and room 3 has 2.",
    "I need 3 more signatures to reach 10.",
    "It's 72 degrees and the pool opens at 11.",
    "What is the capital of France? Reply with the city name only.",
    "Rina is 13, her brother is 9 and her cousin is 11; together they are 33.",
    "Can you remind me to call Tomas at 4 about the 2 tickets for the 8 pm show?",
    "The recipe needs 2 eggs, 3 cups of flour and 1 cup of sugar to make 12 muffins.",
]


def dev_cases() -> list[tuple[str, dict | None]]:
    import claude_blurt2 as B2
    ps = B2.puzzles(4880, 40)                       # dev seed; never used by 0.2c (4701-4703, 4790, 4795) or TEST 4797
    out = []
    for i, p in enumerate(ps):
        order = list(p["nums"])
        if i % 2:
            order = order[::-1]
        L = ", ".join(str(n) for n in order[:-1]) + " and " + str(order[-1])
        w = DEV_WORDINGS[i % len(DEV_WORDINGS)]
        out.append((w.format(L=L, T=p["target"]), {"nums": sorted(p["nums"]), "target": p["target"]}))
    out += [(t, None) for t in DEV_NEGATIVES]
    return out


def selftest() -> None:
    ok = bad = 0
    for text, want in dev_cases():
        got = parse_puzzle(text)
        if got == want:
            ok += 1
        else:
            bad += 1
            print("MISMATCH", want, got, "|", text)
    assert parse_puzzle("") is None
    p = {"nums": [1, 3, 4, 6], "target": 24}
    assert reply_for(p, {"expr": "6/(1-3/4)"}).endswith("6/(1-3/4) = 24.")
    assert "couldn't" in reply_for(p, {"expr": ""})
    print(f"rt02d selftest {ok}/{ok + bad} dev cases")
    if bad:
        raise SystemExit(1)


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        selftest()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "score"])
    ap.add_argument("--task", default="")
    ap.add_argument("--arm", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--model", default="", help="reader dir")
    ap.add_argument("--gen-model", default="", help="base MiniCPM5-1B dir")
    ap.add_argument("--mouth-model", default="")
    ap.add_argument("--panel-dir", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--score", default="")
    a = ap.parse_args()
    run(a) if a.cmd == "run" else score(a)


if __name__ == "__main__":
    main()
