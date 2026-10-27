#!/usr/bin/env python3
"""rt-02e: rt-02d's chat route, minus messages that already state a worked sum (Plain-English puzzles thread,
2026-09-26). New file only. Marks: artifacts/claude-rt02e-20260926/PASSMARKS-rt02e.md (sealed with this code BEFORE
rt-02d's result exists).

Why (practice data only, report): on 40 lookalike messages a blind agent wrote (artifacts/claude-rt02e-20260926/
practice), rt-02d's parser fired on 3, and all 3 already state a worked sum: a check question ("is <sum> equal to
<n>?") or a solution the user found alone ("I got <sum> = <n>"). The user is not asking for an expression there.
rt-02d's R3 allows at most 2 fires in 100.

One change: the route fires only when rt-02d's parse_puzzle fires AND the message does not state a worked sum
(states_sum below: two or more numbers joined by arithmetic operators, then "=", "equals", "equal to", "is",
"makes", "gives", "gets" or "comes to" and a number). Nothing else changes: same parser, same solver, same tries,
seeds, reply wording and arms.

How it is measured (no new GPU run): the route's firing is a pure function of the message text, and on a turn the
route does not fire the agent's reply is the inner build_02c reply, which rt-02d's run records as B0 for the same
conversation on the same machine (rt-02d's dev gate and R4 check exactly that identity). So on rt-02d's own blind
panel:
  B1e reply = B1 reply where rt-02e fires, else B0 reply     (B1off_e likewise from B1off and B0)
  fires on negatives / general items / chat dev turns = rt-02e's firing rule applied to their text.
Valid only if rt-02d's dev gate passed and its R4 found 0 differing unrouted replies on both no-harm sets.

  python -B scripts/claude_rt02e.py --selftest
  python -B scripts/claude_rt02e.py score --out artifacts/claude-rt02d-20260926/run \
      --panel-dir artifacts/claude-panel-rt02d-20260926 --rt02d-score artifacts/claude-rt02d-20260926/score/rt02d_score.json \
      --score artifacts/claude-rt02e-20260926/score
Counts only; never prints panel text.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_NUM = r"\(*\s*\d+\s*\)*"
_OP = r"(?:[+\-*/×÷xX−]|plus|minus|times|multiplied\s+by|divided\s+by|over)"
_CLAIM = re.compile(r"(?<![\d.])" + _NUM + r"(?:\s*" + _OP + r"\s*" + _NUM + r")+\s*"
                    r"(?:=|equals?(?:\s+to)?|is|makes|gives|gets|comes\s+to)\s*\d+", re.I)


def states_sum(text: str) -> bool:
    """True if the message already states a worked sum: numbers joined by operators, then a result."""
    return bool(_CLAIM.search((text or "").replace("−", "-")))


def fires(text: str):
    import claude_rt02d as RT
    p = RT.parse_puzzle(text or "")
    if p is None or states_sum(text):
        return None
    return p


def build_rt02e(state_dir, args):
    """Live arm for joining into the build later (the registered score is the replay below)."""
    import claude_e2e02c as E02C
    import claude_e2e330_arms as A
    loop = E02C.build_02c(state_dir, args)
    _install(loop, A._GEN[args.gen_model], False)
    loop.layers330c = list(getattr(loop, "layers330c", []) or []) + ["rt02e"]
    return loop


def _install(loop, one_b, lora_off):
    import claude_rt02d as RT
    inner = loop.turn
    loop.rt02d_stats = {"routed": 0, "solved": 0}
    loop.rt02d_last = None

    def turn_rt02e(text: str) -> list[str]:
        p = fires(text)
        if p is None:
            loop.rt02d_last = None
            return inner(text)
        res = RT.solve_route(one_b, p, lora_off)
        loop.rt02d_stats["routed"] += 1
        loop.rt02d_stats["solved"] += int(bool(res["expr"]))
        loop.rt02d_last = {"parsed": p, **res}
        return [RT.reply_for(p, res)]

    turn_rt02e.__name__ = "turn_rt02e"
    loop.turn = turn_rt02e


# ------------------------------------------------------------------ replay score (counts only)
def _load(p: Path):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else None


def score(a) -> None:
    import claude_dl1_nights as D1
    import claude_panel382_run as P
    import claude_rt02d as RT
    out, pd = Path(a.out), Path(a.panel_dir)
    truth = {r["id"]: r for r in _load(pd / "chat_puzzles.jsonl")}
    runs = {n: {r["id"]: r for r in (_load(out / f"puzzles_{n}.jsonl") or [])} for n in ("B0", "B1", "B1off")}
    off = json.loads(Path(a.rt02d_score).read_text()) if a.rt02d_score else {}
    res: dict = {}
    # validity: rt-02d's identity of unrouted replies with B0 on this machine
    nh = off.get("no_harm") or {}
    valid = all(nh.get(t) and nh[t]["differ_unrouted"] == 0 for t in ("general", "chatdev"))
    res["valid_identity"] = valid
    fire_e = {i: fires(t["text"]) is not None for i, t in truth.items()}
    fire_d = {i: RT.parse_puzzle(t["text"]) is not None for i, t in truth.items()}
    res["puzzles_fired_rt02d"] = sum(fire_d.values())
    res["puzzles_fired_rt02e"] = sum(fire_e.values())
    res["subset_ok"] = all(fire_d[i] for i in truth if fire_e[i])
    solved = {}
    for arm, src in (("B1e", "B1"), ("B1off_e", "B1off")):
        if not runs[src] or not runs["B0"]:
            continue
        n = 0
        for i, t in truth.items():
            row = runs[src][i] if fire_e[i] else runs["B0"][i]
            n += int(P.puzzle_solved(row["reply"], t["nums"], t["target"]))
        solved[arm] = n
    for arm in ("B0", "B1", "B1off"):
        if runs[arm]:
            solved[arm] = sum(int(P.puzzle_solved(r["reply"], truth[i]["nums"], truth[i]["target"]))
                              for i, r in runs[arm].items())
    res["solved"] = solved
    negs = _load(pd / "negatives.jsonl")
    res["fires_negatives_rt02e"] = sum(fires(r["text"]) is not None for r in negs)
    res["fires_negatives_rt02d"] = sum(RT.parse_puzzle(r["text"]) is not None for r in negs)
    gen = [it["q"] for it in D1.harm_panel()]
    res["fires_general_rt02e"] = sum(fires(q) is not None for q in gen)
    chat = _load(Path("artifacts/claude-panel382-dev-20260925/chat/items.jsonl")) or []
    res["fires_chatdev_rt02e"] = sum(fires(t["text"]) is not None for it in chat for t in it["turns"])
    b1 = runs["B1"]
    res["dishonest"] = off.get("dishonest")
    s = solved
    res["marks"] = {
        "E1": res["fires_negatives_rt02e"] <= 2,
        "E2": None if "B1e" not in s else (s["B1e"] >= 8 and s["B1e"] - s.get("B0", 0) >= 6 and s["B1e"] >= s["B1"] - 2),
        "E3": None if "B1e" not in s or "B1off_e" not in s else (s["B1e"] - s["B1off_e"] >= 4),
        "E4": valid and res["subset_ok"] and res["fires_general_rt02e"] <= 3,
        "E5": None if res["dishonest"] is None or not b1 else res["dishonest"] == 0}
    res["pass"] = all(v is True for v in res["marks"].values())
    sd = Path(a.score)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "rt02e_score.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("solved", "fires_negatives_rt02e", "fires_negatives_rt02d", "marks", "pass")}))


# ------------------------------------------------------------------ selftest (dev + practice data only)
def selftest() -> None:
    import claude_blurt2 as B2
    import claude_dl1_nights as D1
    import claude_rt02d as RT
    ok = 0
    for text, want in RT.dev_cases():                          # 40 dev puzzles + 15 dev negatives
        got = fires(text)
        assert got == want, (want, got, text)
        ok += 1
    prac = json.loads((SCRIPTS.parent / "artifacts/claude-rt02e-20260926/practice/wordings_practice.json").read_text())
    ps = B2.puzzles(4881, 3 * len(prac["puzzle_templates"]))   # practice seed; not 0.2c (4701-4703, 4790, 4795) or TEST 4797
    fmts = [lambda o: ", ".join(map(str, o[:-1])) + " and " + str(o[-1]), lambda o: " ".join(map(str, o)),
            lambda o: ", ".join(map(str, o))]
    lost = kept = 0
    for wi, t in enumerate(prac["puzzle_templates"]):
        for k in range(3):
            p = ps[3 * wi + k]
            o = list(p["nums"])[::-1] if k % 2 else list(p["nums"])
            text = t.replace("{L}", fmts[k](o)).replace("{T}", str(p["target"]))
            d, e = RT.parse_puzzle(text), fires(text)
            kept += int(d is not None and e == d)
            lost += int(d is not None and e is None)
    neg_d = sum(RT.parse_puzzle(n) is not None for n in prac["negatives"])
    neg_e = sum(fires(n) is not None for n in prac["negatives"])
    gen = sum(fires(it["q"]) is not None for it in D1.harm_panel())
    assert lost == 0 and neg_e <= neg_d and gen == 0, (lost, neg_d, neg_e, gen)
    for s in ["Is 8 times 12 equal to 96?", "I got (8 - 3) * 2 + 4 = 14 today!", "is 7 + 6 * 2 equal to 26",
              "3 x 4 is 12", "(13-1)*2 = 24 right?"]:
        assert states_sum(s), s
    for s in ["Use 3, 4, 5 and 6 to make 24.", "3 5 7 8 -> 24, each once", "Make 24 from 1, 3, 4 and 6 with + - * /."]:
        assert not states_sum(s), s
    print(f"rt02e selftest: dev {ok}/55 unchanged; practice puzzles kept {kept}, lost {lost}; "
          f"practice negatives fired {neg_d} -> {neg_e} of {len(prac['negatives'])}; general items fired {gen}/300")


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        selftest()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["score"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--panel-dir", required=True)
    ap.add_argument("--rt02d-score", required=True)
    ap.add_argument("--score", required=True)
    score(ap.parse_args())


if __name__ == "__main__":
    main()
