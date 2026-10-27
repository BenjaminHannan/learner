#!/usr/bin/env python3
"""0.2d DEV health gate D0 (Month-end; marks fixed in design/v3/30-modes/02d-gates-ADDENDUM-26.md). New file only.

D0 runs scripts/claude_e2e02d.py on readable DEV data only, never a TEST-ONLY panel or bank:
  chats  the 336 DEV bank artifacts/claude-e2e331-dev-20260924 (10 lives, 194 turns; no number squares in it)
  grids  a DEV grid bank made here from 358b3's panel generator with DEV seed 47201 (n 4 per size 5, 6, 7; its
         lookalike share), one single-turn chat per item. 47201 is not a TEST seed (row A 47311, demo 47399,
         358b2 35900-35999, rival smoke 36000) and no generator seed overlaps theirs (seed x 100 + size).
Marks (integer counts, ADDENDUM-26):
  D0.1  every user turn gets a non-empty reply
  D0.2  0 crashes or tracebacks (runner exit codes and the run logs)
  D0.3  at least 1 fact saved in every DEV chat that teaches one
  D0.4  the W input is used on every turn that has an earlier user turn; turns that used the store's top-k are reported
  D0.5  the reasoner is called on every grid turn; calls and grids read are reported
  D0.6  one night of sleep completes without error (the H-B recipe's own sleep run; counted there, not here)

  python -B scripts/claude_e2e02d_d0.py make-grid --out DIR
  E2E02D_LOG_DIR=LOGS/chat python -B scripts/claude_e2e336_run.py --bank artifacts/claude-e2e331-dev-20260924 \\
      --arm claude_e2e02d:build_02d --name D0chat --model LIS320 --gen-model BASE --out OUT
  E2E02D_LOG_DIR=LOGS/grid python -B scripts/claude_e2e336_run.py --bank DIR --arm claude_e2e02d:build_02d \\
      --name D0grid --model LIS320 --gen-model BASE --out OUT
  python -B scripts/claude_e2e02d_d0.py count --chat-bank B --grid-bank DIR --out OUT --logs LOGS \\
      --run-logs RUN1.log,RUN2.log
  python -B scripts/claude_e2e02d_d0.py selftest
count prints one JSON line of counts and D0.1-D0.5 PASS/FAIL; it never prints chat text.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

GRID_SEED = 47201
GRID_N = 4
GRID_SIZES = (5, 6, 7)
TEACH_KINDS = {"teach", "correct"}


def load(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def make_grid(out: Path) -> dict:
    import claude_rsn358b3_panel as P
    panel, answers = P.make_panel(GRID_SEED, GRID_N, list(GRID_SIZES))
    out.mkdir(parents=True, exist_ok=True)
    turns = [{"life_id": f"d0grid-{p['id']}", "day": 1, "turn_index": 0, "user_text": p["message"], "kind": "grid",
              "ask_type": None, "facts": [], "gold": None, "creative_seed_facts": []} for p in panel]
    (out / "turns.jsonl").write_text("".join(json.dumps(t) + "\n" for t in turns), encoding="utf-8")
    (out / "truth.jsonl").write_text("", encoding="utf-8")
    (out / "answers.jsonl").write_text("".join(json.dumps(a) + "\n" for a in answers), encoding="utf-8")
    return {"grid_items": len(turns), "broken": sum(a["kind"] == "broken" for a in answers)}


def life_of(log_name: str) -> str:
    """<logs>/e2e336-<life>-<mkdtemp suffix>.jsonl -> <life>"""
    stem = Path(log_name).stem
    return stem[len("e2e336-"):].rsplit("-", 1)[0]


def logs_by_life(d: Path) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for p in sorted(Path(d).glob("e2e336-*.jsonl")):
        out.setdefault(life_of(p.name), []).extend(load(p))
    return out


def count(chat_bank, grid_bank, arm_chat, arm_grid, logs_chat, logs_grid, run_logs) -> dict:
    res = {}
    rows = [r for r in load(arm_chat) + load(arm_grid) if r["kind"] == "user"]
    res["user_turns"] = len(rows)
    res["empty_replies"] = sum(1 for r in rows if not str(r["reply"]).strip())
    tb = [r for p in run_logs for r in [Path(p).read_text(encoding="utf-8", errors="replace")]]
    res["tracebacks"] = sum(t.count("Traceback (most recent call last)") for t in tb)
    turns = load(Path(chat_bank) / "turns.jsonl")
    want = {t["life_id"] for t in turns}
    grid_turns = load(Path(grid_bank) / "turns.jsonl")
    res["chat_lives_run"] = len({r["life_id"] for r in load(arm_chat)} & want)
    res["grid_items_run"] = len({r["life_id"] for r in load(arm_grid)})
    teaching = {t["life_id"] for t in turns if t["kind"] in TEACH_KINDS}
    saved = {r["life_id"] for r in load(arm_chat) if r.get("stored_triples")}
    res["teaching_chats"] = len(teaching)
    res["teaching_chats_with_a_save"] = len(teaching & saved)
    lc = logs_by_life(logs_chat)
    lg = logs_by_life(logs_grid)
    every = [r for v in list(lc.values()) + list(lg.values()) for r in v]
    res["logged_turns"] = len(every)
    firsts = [v[0] for v in list(lc.values()) + list(lg.values()) if v]
    later = [r for v in list(lc.values()) + list(lg.values()) for r in v[1:]]
    res["w_used_on_later_turns"] = sum(1 for r in later if r["w"] != "none" and r["w_rows"] > 0)
    res["later_turns"] = len(later)
    res["w_top_k_turns"] = sum(1 for r in every if r["w"] == "top_k")
    res["first_turns"] = len(firsts)
    gl = [r for v in lg.values() for r in v]
    res["grid_turns_logged"] = len(gl)
    res["grids_read"] = sum(1 for r in gl if r["grid"])
    res["reasoner_calls"] = sum(1 for r in gl if r["reasoner_called"])
    res["reasoner_calls_on_chat_turns"] = sum(1 for v in lc.values() for r in v if r["reasoner_called"])
    res["solved_checked"] = sum(1 for r in gl if r["solved"])
    res["hit_max"] = sum(1 for r in every if r.get("hit_max"))
    n_grid = len(grid_turns)
    res["D0.1"] = "PASS" if res["empty_replies"] == 0 and res["user_turns"] == len(turns) + n_grid else "FAIL"
    res["D0.2"] = "PASS" if res["tracebacks"] == 0 and res["logged_turns"] == len(turns) + n_grid else "FAIL"
    res["D0.3"] = "PASS" if res["teaching_chats_with_a_save"] == res["teaching_chats"] else "FAIL"
    res["D0.4"] = "PASS" if res["w_used_on_later_turns"] == res["later_turns"] else "FAIL"
    res["D0.5"] = "PASS" if res["reasoner_calls"] == res["grids_read"] == res["grid_turns_logged"] == n_grid else "FAIL"
    res["D0.6"] = "counted in the H-B recipe's sleep run"
    return res


def selftest() -> None:
    import tempfile
    ok = {}
    ok["life id from log name"] = life_of("e2e336-e2e-dev-01-ab_c9x.jsonl") == "e2e-dev-01"
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        g = make_grid(d / "grid")
        ok["grid bank: 12 items, one turn each"] = g["grid_items"] == 12 and len(load(d / "grid/turns.jsonl")) == 12
        import claude_puzzle_reader as P
        read = sum(P.read_latin(t["user_text"]) is not None for t in load(d / "grid/turns.jsonl"))
        ok["read_latin reads every DEV grid"] = read == 12
        cb = d / "chat"
        cb.mkdir()
        turns = [{"life_id": "L1", "day": 1, "turn_index": 0, "kind": "teach"},
                 {"life_id": "L1", "day": 1, "turn_index": 1, "kind": "ask"}]
        (cb / "turns.jsonl").write_text("".join(json.dumps(t) + "\n" for t in turns))
        ac = d / "arm_c.jsonl"
        ac.write_text("".join(json.dumps(r) + "\n" for r in [
            {"life_id": "L1", "turn_index": 0, "kind": "user", "reply": "hi", "stored_triples": [["USER", "job", "x"]]},
            {"life_id": "L1", "turn_index": 1, "kind": "user", "reply": "x", "stored_triples": [["USER", "job", "x"]]}]))
        ag = d / "arm_g.jsonl"
        ag.write_text("".join(json.dumps({"life_id": t["life_id"], "turn_index": 0, "kind": "user", "reply": "sq",
                                          "stored_triples": []}) + "\n" for t in load(d / "grid/turns.jsonl")))
        lc, lgd = d / "lc", d / "lg"
        lc.mkdir()
        lgd.mkdir()
        base = {"w": "none", "w_rows": 0, "grid": False, "reasoner_called": False, "solved": False, "hit_max": 0}
        (lc / "e2e336-L1-abc.jsonl").write_text(json.dumps(base) + "\n" + json.dumps(dict(base, w="whole", w_rows=1))
                                               + "\n")
        for t in load(d / "grid/turns.jsonl"):
            (lgd / f"e2e336-{t['life_id']}-q1.jsonl").write_text(json.dumps(dict(base, grid=True, reasoner_called=True))
                                                                 + "\n")
        rl = d / "run.log"
        rl.write_text("[336/D0chat] L1 turns=2\n")
        r = count(cb, d / "grid", ac, ag, lc, lgd, [rl])
        ok["all D0 marks pass on a clean fake run"] = all(r[k] == "PASS" for k in ("D0.1", "D0.2", "D0.3", "D0.4",
                                                                                  "D0.5"))
        rl.write_text("Traceback (most recent call last):\n")
        ok["a traceback fails D0.2"] = count(cb, d / "grid", ac, ag, lc, lgd, [rl])["D0.2"] == "FAIL"
    for name, v in ok.items():
        print(("PASS " if v else "FAIL ") + name)
    print("E2E02D-D0-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    if not all(ok.values()):
        raise SystemExit(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("make-grid", "count", "selftest"))
    ap.add_argument("--out")
    ap.add_argument("--chat-bank", default="artifacts/claude-e2e331-dev-20260924")
    ap.add_argument("--grid-bank")
    ap.add_argument("--logs", help="dir holding chat/ and grid/ (the E2E02D_LOG_DIR of each run)")
    ap.add_argument("--run-logs", default="", help="comma-separated stdout+stderr logs of the two runs")
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    if a.cmd == "make-grid":
        print(json.dumps(make_grid(Path(a.out))))
        return
    out = Path(a.out)
    print(json.dumps(count(a.chat_bank, a.grid_bank, out / "arm_D0chat.jsonl", out / "arm_D0grid.jsonl",
                           Path(a.logs) / "chat", Path(a.logs) / "grid", [x for x in a.run_logs.split(",") if x])))


if __name__ == "__main__":
    main()
