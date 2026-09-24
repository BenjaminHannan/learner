#!/usr/bin/env python3
"""Exp 274 tests: reply-before-sleep (M1), sleep still runs (M2),
deaf meter (M4), panel no-change compare (M3).

  m124 <out.json>
    20 seeded cases x 2 arms (274 vs 273). Sleep forced due
    (sleep_threshold 5 + 5 prefilled experience rows, sleep_due()
    verified True); both arms carry the same slow stub sleeper
    (0.25 s per sleep tick, never accepts, writes nothing) standing in
    for a heavy consolidation sleep.
    M1: turn() returns the reply with zero sleep ticks run
    (counters["sleeps"] still 0, inbox drained). Bar 274 20/20; 273
    reported (expect 0/20: its turn() drains the sleep inside
    run_until_idle before returning).
    M2: on the same loops right after the turn, step up to 30 ticks;
    the due sleep must run within the next 3 idle ticks. Bar 274 20/20.
    M4: agent deaf meter (loop.deaf_log274) on the 274 arm vs wall
    clock around turn() on the 273 arm. Bar: 274 max < 273 max and
    274 median <= 2 s. Both arms reported.
  m3 <panel.jsonl> <new274run> <new274probes> <new292run> <new280brun>
     <new281run> <new282brun> <new292probes> <new280bprobes>
     <new281probes> <new282bprobes> <rec273run> <rec273score>
     <rec292run> <rec280brun> <rec281run> <rec282brun> <scoredir> <out.json>
    Score the new runs once with the 292t scorer (274 in the 292t
    slot), compare every score field to the recorded 273 score, compare
    per-turn 274 vs recorded 273, and check the four comparison reruns
    byte-identical to the recorded ones. Bar: identical everywhere
    (agree 90/90, 0 overlaps, 0 wrong); any change = FAIL.
  merge <m124.json> <m3.json> <out.json>
    Combine into the final results.json shape.

All names/values are invented. No sealed panel is read item by item
(counts and ids only). Usage examples:
  python -B scripts/claude_loop274_test.py m124 /tmp/m124.json
"""

from __future__ import annotations

import copy
import json
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_loop273_agent as A273  # noqa: E402 (comparison arm)
import claude_loop274_agent as A274  # noqa: E402 (under test)
import claude_loop292t_agent as A292T  # noqa: E402 (shared config shape)

N_CASES = 20
THRESHOLD = 5
PREFILL = 5
SLOW_S = 0.5
M2_WITHIN = 3
M2_CAP = 30
M4_MEDIAN_BAR_S = 2.0

# Invented message parts (same pool shape as the 273 test; fiction only).
_NAMES = ["Zara", "Milo", "Kessa", "Ruan", "Ilsa", "Tobin", "Wren",
          "Calix", "Odessa", "Perrin", "Sable", "Tilda", "Vesper",
          "Bran", "Cleo", "Dario", "Elif", "Fintan", "Greta", "Hadil"]
_RELS = ["city", "color", "boss", "teacher", "friend"]
_VALS = ["Quiln", "Bluefen", "Marlow", "Tess", "Amberline"]


def msg_for(seed: int) -> str:
    name = _NAMES[seed % len(_NAMES)]
    rel = _RELS[(seed * 3) % len(_RELS)]
    val = _VALS[(seed * 7) % len(_VALS)]
    if seed % 4 == 3:
        return f"What is {name}'s {rel}?"
    return f"{name}'s {rel} is {val}."


class SlowSleeper:
    """Test-only heavy-sleep stand-in: slow, accepts nothing, writes nothing."""

    def __init__(self) -> None:
        self.requests: list[int] = []

    def sleep(self, experience: list[dict], notebook) -> dict:
        time.sleep(SLOW_S)
        self.requests.append(len(experience))
        return {"accepted": False, "reason": "274 test slow stub",
                "log_size": len(experience)}


def _cfg274(root: Path) -> dict:
    cfg = copy.deepcopy(A292T.DEFAULT_CONFIG292T)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = THRESHOLD
    return cfg


def _build_pair(seed: int):
    d274 = Path(tempfile.mkdtemp(prefix=f"m274_s{seed}_"))
    d273 = Path(tempfile.mkdtemp(prefix="m273_s%d_" % seed))
    l274 = A274.build_agent274(_cfg274(d274))
    l273 = A273.build_agent273(_cfg274(d273))
    l274.sleeper = SlowSleeper()
    l273.sleeper = SlowSleeper()
    return (l274, l273), (d274, d273)


def _force_sleep_due(loop, n: int) -> None:
    for _ in range(n):
        loop.experience.append({"tick": 0, "kind": "turn",
                                "text": "setup", "statuses": []})


def _cleanup(dirs) -> None:
    for d in dirs:
        shutil.rmtree(d, ignore_errors=True)


def run_m124() -> dict:
    rows = []
    for seed in range(N_CASES):
        (l274, l273), dirs = _build_pair(seed)
        try:
            _force_sleep_due(l274, PREFILL)
            _force_sleep_due(l273, PREFILL)
            pre274, pre273 = bool(l274.sleep_due()), bool(l273.sleep_due())
            m = msg_for(seed)
            # --- 274 arm: agent deaf meter is the measurement under test.
            t0 = time.perf_counter()
            said274 = l274.turn(m)
            wall274 = time.perf_counter() - t0
            meter274 = float(l274.deaf_log274[-1]["deaf_s"]) if \
                l274.deaf_log274 else -1.0
            sleeps274 = int(l274.counters.get("sleeps", 0))
            drained274 = (list(l274.inbox) == [])
            # --- 273 arm: wall clock (273 has no meter).
            t0 = time.perf_counter()
            said273 = l273.turn(m)
            wall273 = time.perf_counter() - t0
            sleeps273 = int(l273.counters.get("sleeps", 0))
            pass274 = bool(pre274 and sleeps274 == 0 and drained274
                           and isinstance(said274, list))
            pass273 = bool(pre273 and sleeps273 == 0)
            # --- M2 on the same loops: step until the first SLEEP tick.
            tick274, tick273 = None, None
            for k in range(1, M2_CAP + 1):
                ev = l274.step()
                if ev.get("mode") == "SLEEP":
                    tick274 = k
                    break
            for k in range(1, M2_CAP + 1):
                ev = l273.step()
                if ev.get("mode") == "SLEEP":
                    tick273 = k
                    break
            m2_274 = tick274 is not None and tick274 <= M2_WITHIN
            rows.append({
                "seed": seed,
                "sleep_due_274": pre274, "sleep_due_273": pre273,
                "m1_pass274": pass274, "m1_pass273": pass273,
                "sleeps_after_turn_274": sleeps274,
                "sleeps_after_turn_273": sleeps273,
                "inbox_drained_274": drained274,
                "reply_match_274_vs_273": list(said274) == list(said273),
                "n_meter_rows_274": len(l274.deaf_log274),
                "meter274_s": round(meter274, 5),
                "wall274_s": round(wall274, 5),
                "wall273_s": round(wall273, 5),
                "m2_tick_to_sleep_274": tick274,
                "m2_tick_to_sleep_273": tick273,
                "m2_pass274": bool(m2_274),
            })
        finally:
            _cleanup(dirs)
    m1_274 = sum(1 for r in rows if r["m1_pass274"])
    m1_273 = sum(1 for r in rows if r["m1_pass273"])
    m2_274 = sum(1 for r in rows if r["m2_pass274"])
    pre = sum(1 for r in rows if r["sleep_due_274"] and r["sleep_due_273"])
    match = sum(1 for r in rows if r["reply_match_274_vs_273"])
    meter = [r["meter274_s"] for r in rows]
    wall3 = [r["wall273_s"] for r in rows]
    med274, max274 = float(statistics.median(meter)), float(max(meter))
    med273, max273 = float(statistics.median(wall3)), float(max(wall3))
    m1 = {"n": N_CASES, "precondition_sleep_due_both": pre,
          "reply_before_sleep_274": m1_274,
          "reply_before_sleep_273": m1_273,
          "reply_match_274_vs_273": match, "rows": rows,
          "verdict": "PASS" if m1_274 == N_CASES else "FAIL"}
    m2 = {"n": N_CASES, "sleep_within_3_ticks_274": m2_274,
          "within_ticks": M2_WITHIN,
          "verdict": "PASS" if m2_274 == N_CASES else "FAIL"}
    m4 = {"n": N_CASES, "meter274_median_s": round(med274, 5),
          "meter274_max_s": round(max274, 5),
          "wall273_median_s": round(med273, 5),
          "wall273_max_s": round(max273, 5),
          "verdict": ("PASS" if max274 < max273
                       and med274 <= M4_MEDIAN_BAR_S else "FAIL")}
    verdict = ("PASS" if m1["verdict"] == "PASS"
               and m2["verdict"] == "PASS"
               and m4["verdict"] == "PASS" else "FAIL")
    return {"m1": m1, "m2": m2, "m4": m4, "verdict": verdict}


def _run_rows(path: str) -> dict:
    return {r["id"]: r for r in json.loads(Path(path).read_text(
        encoding="utf-8"))}


def run_m3(panel: str, new274: str, new274probes: str, new292: str,
           new280b: str, new281: str, new282b: str, new292probes: str,
           new280bprobes: str, new281probes: str, new282bprobes: str,
           rec273: str, recscore: str, rec292: str, rec280b: str,
           rec281: str, rec282b: str, scoredir: str) -> dict:
    import claude_join292t_score as S  # noqa: E402 (read-only scorer)
    score_path = str(Path(scoredir) / "panel-score274.json")
    rc = S.panel_main([panel, new292, new280b, new281, new282b, new274,
                       new292probes, new280bprobes, new281probes,
                       new282bprobes, new274probes, score_path])
    new_score = json.loads(Path(score_path).read_text(encoding="utf-8"))
    rec_score = json.loads(Path(recscore).read_text(encoding="utf-8"))
    # Score fields that must be identical (counts/ids only).
    fields = ["n_dialogs", "n_turns", "by_cat", "agree", "overlaps",
              "qwrite292t", "smalltalk_writes292t",
              "store_diffs_292t_vs_292", "old_sheet_hits_292t",
              "mech_owners", "verdict"]
    field_match = {f: (new_score.get(f) == rec_score.get(f)) for f in fields}
    # Per-turn 274 vs recorded 273 (reply, writes, store; counts only).
    rows274, rows273 = _run_rows(new274), _run_rows(rec273)
    same_ids = sorted(set(rows274) & set(rows273))
    per_turn_same, per_turn_n, per_turn_ids_ok = 0, 0, True
    for did in same_ids:
        a, b = rows274[did], rows273[did]
        if len(a.get("rows", [])) != len(b.get("rows", [])):
            per_turn_ids_ok = False
            continue
        for i, (ra, rb) in enumerate(zip(a["rows"], b["rows"])):
            per_turn_n += 1
            if (ra.get("reply") == rb.get("reply")
                    and ra.get("ev") == rb.get("ev")
                    and ra.get("triples") == rb.get("triples")):
                per_turn_same += 1
    # Comparison-arm reruns byte-identical to recorded (harness check).
    arm_match = {}
    for tag, newp, recp in (("292", new292, rec292),
                            ("280b", new280b, rec280b),
                            ("281", new281, rec281),
                            ("282b", new282b, rec282b)):
        new_txt = Path(newp).read_text(encoding="utf-8")
        rec_txt = Path(recp).read_text(encoding="utf-8")
        arm_match[tag] = (new_txt == rec_txt)
    agree = new_score.get("agree", {})
    m3 = {
        "score274_path": score_path,
        "scorer_rc": rc,
        "agree": f"{agree.get('n')}/{agree.get('denom')}",
        "overlaps": len(new_score.get("overlaps", [])),
        "moved_turns": len(agree.get("moved_ids", [])),
        "old_sheet_hits": len(new_score.get("old_sheet_hits_292t", [])),
        "question_writes": len(new_score.get("qwrite292t", [])),
        "smalltalk_writes": len(
            new_score.get("smalltalk_writes292t", [])),
        "store_diffs": len(
            new_score.get("store_diffs_292t_vs_292", [])),
        "by_cat_identical": bool(field_match.get("by_cat")),
        "mech_owners": new_score.get("mech_owners"),
        "mech_owners_identical": bool(field_match.get("mech_owners")),
        "verdict_field": new_score.get("verdict"),
        "all_score_fields_identical": bool(all(field_match.values())),
        "field_match": field_match,
        "per_turn_274_vs_recorded_273": f"{per_turn_same}/{per_turn_n}",
        "per_turn_ids_ok": bool(per_turn_ids_ok),
        "comparison_reruns_identical": arm_match,
        "verdict": ("PASS" if all(field_match.values())
                    and per_turn_same == per_turn_n and per_turn_n > 0
                    and per_turn_ids_ok else "FAIL"),
    }
    return {"m3": m3,
            "verdict": "PASS" if m3["verdict"] == "PASS" else "FAIL"}


def main(argv) -> int:
    mode = argv[1] if len(argv) > 1 else "m124"
    if mode == "m124":
        out_path = argv[2] if len(argv) > 2 else None
        res = run_m124()
        m1, m2, m4 = res["m1"], res["m2"], res["m4"]
        print(f"M1 274 reply-before-sleep {m1['reply_before_sleep_274']}/"
              f"{m1['n']} (273 {m1['reply_before_sleep_273']}/{m1['n']}, "
              f"reply-match {m1['reply_match_274_vs_273']}/{m1['n']}) "
              f"-> {m1['verdict']}")
        print(f"M2 274 sleep-within-{m2['within_ticks']} "
              f"{m2['sleep_within_3_ticks_274']}/{m2['n']} -> {m2['verdict']}")
        print(f"M4 meter274 median/max {m4['meter274_median_s']}/"
              f"{m4['meter274_max_s']}s vs wall273 median/max "
              f"{m4['wall273_median_s']}/{m4['wall273_max_s']}s "
              f"-> {m4['verdict']}")
        print("VERDICT:", res["verdict"])
        if out_path:
            Path(out_path).write_text(json.dumps(res, indent=1),
                                      encoding="utf-8")
            print(f"wrote {out_path}")
        return 0 if res["verdict"] == "PASS" else 1
    if mode == "m3":
        (panel, new274, new274probes, new292, new280b, new281, new282b,
         new292probes, new280bprobes, new281probes, new282bprobes, rec273,
         recscore, rec292, rec280b, rec281, rec282b, scoredir,
         out_path) = argv[2:21]
        res = run_m3(panel, new274, new274probes, new292, new280b, new281,
                     new282b, new292probes, new280bprobes, new281probes,
                     new282bprobes, rec273, recscore, rec292, rec280b,
                     rec281, rec282b, scoredir)
        m3 = res["m3"]
        print(f"M3 agree {m3['agree']} overlaps {m3['overlaps']} moved "
              f"{m3['moved_turns']} oldhits {m3['old_sheet_hits']} "
              f"per-turn {m3['per_turn_274_vs_recorded_273']} "
              f"fields-identical {m3['all_score_fields_identical']} "
              f"-> {m3['verdict']}")
        print("VERDICT:", res["verdict"])
        Path(out_path).write_text(json.dumps(res, indent=1),
                                  encoding="utf-8")
        print(f"wrote {out_path}")
        return 0 if res["verdict"] == "PASS" else 1
    if mode == "merge":
        m124p, m3p, out_path = argv[2:5]
        m124 = json.loads(Path(m124p).read_text(encoding="utf-8"))
        m3 = json.loads(Path(m3p).read_text(encoding="utf-8"))
        res = {"m1": m124["m1"], "m2": m124["m2"], "m4": m124["m4"],
               "m3": m3["m3"],
               "verdict": ("PASS" if m124["verdict"] == "PASS"
                           and m3["verdict"] == "PASS" else "FAIL")}
        Path(out_path).write_text(json.dumps(res, indent=1),
                                  encoding="utf-8")
        print("VERDICT:", res["verdict"])
        print(f"wrote {out_path}")
        return 0 if res["verdict"] == "PASS" else 1
    raise SystemExit("mode must be m124|m3|merge")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
