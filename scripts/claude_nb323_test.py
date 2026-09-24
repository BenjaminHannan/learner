#!/usr/bin/env python3
"""Exp nb-323 tests: durable hash-chained turn log (M1-M5).

  m1 <panel> <config> <rec274run> <rec274probes> <rec274score> <rec292>
     <rec280b> <rec281> <rec282b> <rec292probes> <rec280bprobes>
     <rec281probes> <rec282bprobes> <workdir> <outdir> <out.json>
    Run the 292t/273 panel exactly as 274 ran it (same runner
    scripts/claude_join292t_run.py, same config, same panel; 323 in the
    274 slot; the four comparison arms reused from 274's verified
    run274, byte-identical reruns already proven 4/4 in 274 M3), score
    once with the same scorer scripts/claude_join292t_score.py against
    274's recorded score, and byte-compare every 323 turn (reply,
    writes, store) plus probes against recorded 274. Bar: scores
    identical to 274 (90/90, 0 overlaps, 0 wrong); replies and stores
    byte-identical on every turn.
  m2 <out.json>
    20 seeded dev dialogs (invented names, 30 turns each: teaches,
    questions, small talk). Each dialog: 2 kill-free restarts (rebuild
    on the same state_dir) and 2 forced sleeps (small sleep_threshold,
    reported). Bar: exactly one BEGIN and one END per turn, in order,
    full text/reply matching turn(): 600/600; 0 lost.
  m3 <statedir> <out.json>
    30 SIGKILLs at random moments while turns run (loop mode, fresh
    subprocess per iteration on one shared state_dir). Bar: 0 returned
    replies missing an END, 0 duplicate ENDs, 0 failed opens, every
    interrupted turn listed.
  m3child <statedir> <progress> <start> <count>
    (helper) run turns, fsyncing each returned reply with its turn_id.
  m4 <out.json>
    20 copies of a finished log, one byte changed at a random offset
    in each, outside the final line. Bar: 20/20 caught on open.
  m5 <out.json>
    Cost, report only: per-turn append overhead (median/max ms) and
    open time of a 10,000-turn log.
  merge <m1> <m2> <m3> <m4> <m5> <out.json>
    Combine into the final results.json shape.

All names and turn texts are invented. The sealed panel is never read
item by item (counts and ids only). Test dirs live under /tmp/nb323/.
"""

from __future__ import annotations

import copy
import gc
import json
import os
import random
import shutil
import signal
import statistics
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

NB323 = "/tmp/nb323"

# Invented pools (fiction only).
_M2_NAMES = ["Zara", "Milo", "Kessa", "Ruan", "Ilsa", "Tobin", "Wren",
             "Calix", "Odessa", "Perrin", "Sable", "Tilda", "Vesper",
             "Bran", "Cleo", "Dario", "Elif", "Fintan", "Greta", "Hadil",
             "Juno", "Kaito", "Lena", "Marisol", "Nico", "Opal", "Petra",
             "Quill", "Rosa", "Sven"]
_M2_RELS = ["city", "color", "teacher", "friend", "doctor", "book"]
_M2_VALS = ["Quiln", "Bluefen", "Marlow", "Tess", "Amberline", "Corvo",
            "Duskley", "Elmira"]
_M2_SMALL = ["Hello.", "Thanks!", "Bye.", "How are you?", "Good morning.",
             "See you soon.", "Nice to meet you.", "Have a good day."]

M2_THRESHOLD = 6


def m2_turns(seed: int, n: int = 30) -> list[str]:
    out = []
    for i in range(n):
        name = _M2_NAMES[(seed * 7 + i * 3) % len(_M2_NAMES)]
        rel = _M2_RELS[(seed + i * 5) % len(_M2_RELS)]
        val = _M2_VALS[(seed * 3 + i * 11) % len(_M2_VALS)]
        if i % 3 == 0:
            out.append(f"{name}'s {rel} is {val}.")
        elif i % 3 == 1:
            out.append(f"What is {name}'s {rel}?")
        else:
            out.append(_M2_SMALL[(seed + i) % len(_M2_SMALL)])
    return out


def _cfg323(state_dir: Path, sleep_threshold: int):
    import claude_nb323_turnlog as T323
    cfg = copy.deepcopy(T323.DEFAULT_CONFIG323)
    cfg["state_dir"] = str(state_dir)
    cfg["sleep_threshold"] = int(sleep_threshold)
    return cfg


# ------------------------------------------------------------------ M1

def run_m1(panel: str, config: str, rec274run: str, rec274probes: str,
           rec274score: str, rec292: str, rec280b: str, rec281: str,
           rec282b: str, rec292probes: str, rec280bprobes: str,
           rec281probes: str, rec282bprobes: str, workdir: str,
           outdir: str) -> dict:
    import claude_join292t_run as R292T  # noqa: E402 (same runner)
    import claude_join292t_score as S  # noqa: E402 (same scorer)
    import claude_openers260_run as R260  # noqa: E402 (same driver)
    t0 = time.perf_counter()
    agent = str(SCRIPTS / "claude_nb323_turnlog.py")
    work = Path(workdir)
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    outd = Path(outdir)
    outd.mkdir(parents=True, exist_ok=True)
    r = R260.Runner(agent, config, str(work / "p323"))
    dialogs = R292T.load_panel_dialogs(panel)
    n_turns = sum(len(d["turns"]) for d in dialogs)
    new323 = str(outd / "panel-323.json")
    new323probes = str(outd / "probes-323.json")
    rows = R292T.run_panel_dialogs(r, dialogs)
    Path(new323).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    probes = R292T.run_probes(r)
    Path(new323probes).write_text(json.dumps(probes, indent=1),
                                  encoding="utf-8")
    del r
    gc.collect()
    score_path = str(outd / "panel-score323.json")
    rc = S.panel_main([panel, rec292, rec280b, rec281, rec282b, new323,
                       rec292probes, rec280bprobes, rec281probes,
                       rec282bprobes, new323probes, score_path])
    new_score = json.loads(Path(score_path).read_text(encoding="utf-8"))
    rec_score = json.loads(Path(rec274score).read_text(encoding="utf-8"))
    fields = ["n_dialogs", "n_turns", "by_cat", "agree", "overlaps",
              "qwrite292t", "smalltalk_writes292t",
              "store_diffs_292t_vs_292", "old_sheet_hits_292t",
              "mech_owners", "verdict"]
    field_match = {f: (new_score.get(f) == rec_score.get(f)) for f in fields}
    rows323 = {row["id"]: row for row in rows}
    rows274 = {row["id"]: row for row in json.loads(
        Path(rec274run).read_text(encoding="utf-8"))}
    per_same, per_n, ids_ok, stored_same, stored_n = 0, 0, True, 0, 0
    for did in sorted(set(rows323) & set(rows274)):
        a, b = rows323[did], rows274[did]
        if len(a.get("rows", [])) != len(b.get("rows", [])):
            ids_ok = False
            continue
        for ra, rb in zip(a["rows"], b["rows"]):
            per_n += 1
            if (ra.get("reply") == rb.get("reply")
                    and ra.get("ev") == rb.get("ev")
                    and ra.get("triples") == rb.get("triples")):
                per_same += 1
        stored_n += 1
        if a.get("stored") == b.get("stored"):
            stored_same += 1
    probes323 = json.loads(Path(new323probes).read_text(encoding="utf-8"))
    probes274 = json.loads(Path(rec274probes).read_text(encoding="utf-8"))
    probes_same = (probes323 == probes274)
    agree = new_score.get("agree", {})
    m1 = {
        "n_dialogs": len(dialogs), "n_turns": n_turns,
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
        "mech_owners": new_score.get("mech_owners"),
        "all_score_fields_identical": bool(all(field_match.values())),
        "field_match": field_match,
        "per_turn_323_vs_recorded_274": f"{per_same}/{per_n}",
        "per_turn_ids_ok": bool(ids_ok),
        "stored_identical": f"{stored_same}/{stored_n}",
        "probes_identical": bool(probes_same),
        "elapsed_s": round(time.perf_counter() - t0, 1),
        "verdict": ("PASS" if all(field_match.values())
                    and per_same == per_n and per_n == 90
                    and ids_ok and stored_same == stored_n
                    and probes_same else "FAIL"),
    }
    return {"m1": m1,
            "verdict": "PASS" if m1["verdict"] == "PASS" else "FAIL"}


# ------------------------------------------------------------------ M2

def run_m2() -> dict:
    import claude_nb323_turnlog as T323
    base = Path(NB323) / "m2"
    if base.exists():
        shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    turn_ok, turn_n = 0, 0
    sleeps_forced, restarts = 0, 0
    dialogs_ok = 0
    for seed in range(20):
        d = base / f"d{seed:02d}"
        d.mkdir(parents=True)
        cfg = _cfg323(d, M2_THRESHOLD)
        turns = m2_turns(seed)
        sent: list[str] = []
        got: list[str] = []
        loop = T323.build_agent323(cfg)
        for i, text in enumerate(turns):
            if i in (10, 20):
                del loop
                gc.collect()
                loop = T323.build_agent323(cfg)
                restarts += 1
            said = loop.turn(text)
            sent.append(text)
            got.append(list(said))
            if i == 19:
                before = int(loop.counters.get("sleeps", 0))
                loop.run_until_idle()
                if int(loop.counters.get("sleeps", 0)) > before:
                    sleeps_forced += 1
        before = int(loop.counters.get("sleeps", 0))
        loop.run_until_idle()
        if int(loop.counters.get("sleeps", 0)) > before:
            sleeps_forced += 1
        del loop
        gc.collect()
        rep = T323.read_turns(d / "turns323.jsonl")
        recs = rep["records"]
        begins = [r for r in recs if r.get("kind") == "BEGIN"]
        ends = {int(r["turn_id"]): r for r in recs
                if r.get("kind") == "END"}
        ok = (len(begins) == 30 and len(ends) == 30
              and not rep["interrupted"] and not rep["torn"])
        if ok:
            for k in range(30):
                tid = k + 1
                b = begins[k]
                e = ends.get(tid)
                if (b.get("turn_id") == tid and b.get("text") == sent[k]
                        and e is not None
                        and e.get("reply") == got[k]
                        and recs[2 * k].get("kind") == "BEGIN"
                        and recs[2 * k + 1].get("kind") == "END"):
                    turn_ok += 1
                turn_n += 1
            if turn_ok == (seed + 1) * 30:
                dialogs_ok += 1
        else:
            turn_n += 30
    m2 = {"n_dialogs": 20, "turns_per_dialog": 30,
          "sleep_threshold": M2_THRESHOLD,
          "restarts": restarts, "sleeps_forced": sleeps_forced,
          "turns_exact_begin_end_in_order": f"{turn_ok}/{turn_n}",
          "dialogs_fully_ok": f"{dialogs_ok}/20",
          "verdict": ("PASS" if turn_ok == 600 and turn_n == 600
                       and sleeps_forced == 40 and restarts == 40
                       else "FAIL")}
    return {"m2": m2,
            "verdict": "PASS" if m2["verdict"] == "PASS" else "FAIL"}


# ------------------------------------------------------------------ M3

M3_TURNS = [
    "Milo's teacher is Tess.", "What is Milo's teacher?",
    "Hello.", "Kessa's city is Elmira.", "What is Kessa's city?",
    "Thanks!", "Ruan's friend is Corvo.", "What is Ruan's friend?",
    "How are you?", "Ilsa's book is Duskley.", "What is Ilsa's book?",
    "Bye.", "Tobin's color is Bluefen.", "What is Tobin's color?",
    "Good morning.", "Wren's doctor is Marlow.", "What is Wren's doctor?",
    "See you soon.", "Calix's city is Quiln.", "What is Calix's city?",
    "Nice to meet you.", "Odessa's friend is Tess.",
    "What is Odessa's friend?", "Have a good day.",
    "Perrin's teacher is Elmira.", "What is Perrin's teacher?",
    "Hello.", "Sable's book is Corvo.", "What is Sable's book?",
    "Thanks!", "Tilda's color is Amberline.", "What is Tilda's color?",
    "Bye.", "Vesper's doctor is Marlow.", "What is Vesper's doctor?",
    "How are you?", "Bran's city is Duskley.", "What is Bran's city?",
    "Good morning.", "Cleo's friend is Quiln.", "What is Cleo's friend?",
    "See you soon.", "Dario's teacher is Tess.",
    "What is Dario's teacher?", "Have a good day.",
    "Elif's book is Elmira.", "What is Elif's book?", "Hello.",
]


def run_m3child(statedir: str, progress: str, start: int, count: int) -> int:
    import claude_nb323_turnlog as T323
    cfg = _cfg323(Path(statedir), 100000)
    loop = T323.build_agent323(cfg)
    with open(progress, "a", encoding="utf-8") as out:
        for j in range(count):
            text = M3_TURNS[(start + j) % len(M3_TURNS)]
            said = loop.turn(text)
            tid = int(loop.turnlog323.last_turn_id)
            out.write(json.dumps({"k": start + j, "turn_id": tid,
                                  "reply": list(said)},
                                 ensure_ascii=False) + "\n")
            out.flush()
            os.fsync(out.fileno())
    return 0


def run_m3(statedir: str) -> dict:
    import claude_nb323_turnlog as T323
    rng = random.Random(323031)
    base = Path(statedir)
    if base.exists():
        shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    prog = base.parent / "progress.jsonl"
    if prog.exists():
        prog.unlink()
    prog.write_text("", encoding="utf-8")
    logpath = base / "turns323.jsonl"
    opens_ok, failed_opens, torn_repairs = 0, 0, 0
    early_kills, midrun_kills = 0, 0
    for it in range(30):
        resume = sum(1 for _ in prog.read_text(
            encoding="utf-8").splitlines() if _.strip())
        cmd = [sys.executable, "-B", str(SCRIPTS / "claude_nb323_test.py"),
               "m3child", str(base), str(prog), str(resume), "400"]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        try:
            if it % 6 == 5:
                time.sleep(rng.uniform(0.05, 0.4))
                early_kills += 1
            else:
                deadline = time.time() + 25.0
                while time.time() < deadline:
                    n = sum(1 for _ in prog.read_text(
                        encoding="utf-8").splitlines() if _.strip())
                    if n > resume:
                        break
                    time.sleep(0.02)
                time.sleep(rng.uniform(0.02, 0.5))
                midrun_kills += 1
        finally:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            proc.wait()
        try:
            log = T323.TurnLog323(logpath)
            opens_ok += 1
            if log.torn_tail:
                log.repair_torn_tail()
                torn_repairs += 1
        except T323.TurnLog323Corrupt:
            failed_opens += 1
    log = T323.TurnLog323(logpath)
    if log.torn_tail:
        log.repair_torn_tail()
        torn_repairs += 1
    rep = T323.read_turns(logpath)
    ends: dict[int, list] = {}
    for r in rep["records"]:
        if r.get("kind") == "END":
            ends.setdefault(int(r["turn_id"]), []).append(r)
    dup_ends = sum(len(v) - 1 for v in ends.values() if len(v) > 1)
    prog_rows = [json.loads(x) for x in prog.read_text(
        encoding="utf-8").splitlines() if x.strip()]
    missing, mismatched = 0, 0
    for row in prog_rows:
        cand = ends.get(int(row["turn_id"]))
        if not cand:
            missing += 1
        elif cand[0].get("reply") != list(row["reply"]):
            mismatched += 1
    m3 = {"sigkills": 30, "early_kills": early_kills,
          "midrun_kills": midrun_kills,
          "progress_rows": len(prog_rows),
          "returned_missing_end": missing,
          "reply_mismatches": mismatched,
          "duplicate_ends": dup_ends,
          "failed_opens": failed_opens,
          "opens_ok": opens_ok,
          "torn_repairs": torn_repairs,
          "interrupted_turns": len(rep["interrupted"]),
          "verdict": ("PASS" if missing == 0 and mismatched == 0
                       and dup_ends == 0 and failed_opens == 0
                       else "FAIL")}
    return {"m3": m3,
            "verdict": "PASS" if m3["verdict"] == "PASS" else "FAIL"}


# ------------------------------------------------------------------ M4

def run_m4() -> dict:
    import claude_nb323_turnlog as T323
    rng = random.Random(32304)
    base = Path(NB323) / "m4"
    if base.exists():
        shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    d = base / "finished"
    d.mkdir(parents=True)
    loop = T323.build_agent323(_cfg323(d, 100000))
    for i, text in enumerate(m2_turns(7)):
        loop.turn(text)
    del loop
    gc.collect()
    src = (d / "turns323.jsonl").read_bytes()
    n_lines = len(src.split(b"\n")) - 1
    caught = 0
    for c in range(20):
        work = base / f"copy{c:02d}"
        work.mkdir(parents=True)
        p = work / "turns323.jsonl"
        blob = bytearray(src)
        lines = bytes(blob).split(b"\n")
        assert lines[-1] == b""
        body = lines[:-1]
        li = rng.randrange(len(body) - 1)  # outside the final line
        line = body[li]
        pos = rng.randrange(len(line))
        old = line[pos]
        new = rng.randrange(256)
        while new == old or new == 10:
            new = rng.randrange(256)
        off = sum(len(body[k]) + 1 for k in range(li)) + pos
        blob[off] = new
        p.write_bytes(bytes(blob))
        try:
            T323.TurnLog323(p)
        except T323.TurnLog323Corrupt:
            caught += 1
    m4 = {"copies": 20, "log_lines": n_lines, "caught": caught,
          "verdict": "PASS" if caught == 20 else "FAIL"}
    return {"m4": m4,
            "verdict": "PASS" if m4["verdict"] == "PASS" else "FAIL"}


# ------------------------------------------------------------------ M5

def run_m5() -> dict:
    import claude_nb323_turnlog as T323
    base = Path(NB323) / "m5"
    if base.exists():
        shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    bench = T323.TurnLog323(base / "bench.jsonl")
    sample_records = [{"kind": "write", "line": "teach Zara city = Quiln",
                       "text": "Saved: Zara's city is Quiln.",
                       "wrote": True, "pending": False}]
    pair_ms: list[float] = []
    for i in range(300):
        t0 = time.perf_counter()
        tid = bench.append_begin(f"Bench person's city is Quiln {i}.")
        bench.append_end(tid, [f"Saved: bench person's city is Quiln {i}."],
                         sample_records, "bench73", 0.91, ["F00001"],
                         {"E0001": "Bench Person"}, i + 1, i * 2,
                         i * 2 + 1, "LISTENING", 0.004)
        pair_ms.append((time.perf_counter() - t0) * 1000.0)
    big = base / "big.jsonl"
    if big.exists():
        big.unlink()
    gen = T323.TurnLog323(big)
    for i in range(10000):
        tid = gen.append_begin(f"Bench turn number {i} with some text.")
        gen.append_end(tid, ["Saved: bench fact."], sample_records,
                       "bench73", 0.5, [], {}, i + 1, i, i,
                       "LISTENING", 0.001)
    del gen
    gc.collect()
    t0 = time.perf_counter()
    opened = T323.TurnLog323(big)
    open_s = time.perf_counter() - t0
    assert opened.n_lines == 20000
    m5 = {"append_pairs": len(pair_ms),
          "per_turn_overhead_median_ms": round(
              float(statistics.median(pair_ms)), 3),
          "per_turn_overhead_max_ms": round(float(max(pair_ms)), 3),
          "open_10000_turns_s": round(open_s, 3),
          "open_10000_turns_lines": opened.n_lines}
    return {"m5": m5, "verdict": "report"}


def main(argv) -> int:
    mode = argv[1] if len(argv) > 1 else ""
    if mode == "m1":
        (panel, config, rec274run, rec274probes, rec274score, rec292,
         rec280b, rec281, rec282b, rec292probes, rec280bprobes,
         rec281probes, rec282bprobes, workdir, outdir,
         out_path) = argv[2:18]
        res = run_m1(panel, config, rec274run, rec274probes, rec274score,
                     rec292, rec280b, rec281, rec282b, rec292probes,
                     rec280bprobes, rec281probes, rec282bprobes, workdir,
                     outdir)
        Path(out_path).write_text(json.dumps(res, indent=1),
                                  encoding="utf-8")
        print(f"M1 agree {res['m1']['agree']} overlaps "
              f"{res['m1']['overlaps']} moved {res['m1']['moved_turns']} "
              f"oldhits {res['m1']['old_sheet_hits']} per-turn "
              f"{res['m1']['per_turn_323_vs_recorded_274']} stored "
              f"{res['m1']['stored_identical']} probes "
              f"{res['m1']['probes_identical']} fields-identical "
              f"{res['m1']['all_score_fields_identical']} "
              f"-> {res['m1']['verdict']}")
        return 0 if res["verdict"] == "PASS" else 1
    if mode == "m2":
        out_path = argv[2]
        res = run_m2()
        Path(out_path).write_text(json.dumps(res, indent=1),
                                  encoding="utf-8")
        print(f"M2 exact {res['m2']['turns_exact_begin_end_in_order']} "
              f"dialogs {res['m2']['dialogs_fully_ok']} restarts "
              f"{res['m2']['restarts']} sleeps {res['m2']['sleeps_forced']} "
              f"threshold {res['m2']['sleep_threshold']} "
              f"-> {res['m2']['verdict']}")
        return 0 if res["verdict"] == "PASS" else 1
    if mode == "m3":
        statedir, out_path = argv[2:4]
        res = run_m3(statedir)
        Path(out_path).write_text(json.dumps(res, indent=1),
                                  encoding="utf-8")
        print(f"M3 kills {res['m3']['sigkills']} progress "
              f"{res['m3']['progress_rows']} missing-end "
              f"{res['m3']['returned_missing_end']} dups "
              f"{res['m3']['duplicate_ends']} failed-opens "
              f"{res['m3']['failed_opens']} interrupted "
              f"{res['m3']['interrupted_turns']} "
              f"-> {res['m3']['verdict']}")
        return 0 if res["verdict"] == "PASS" else 1
    if mode == "m3child":
        statedir, progress, start, count = argv[2:6]
        return run_m3child(statedir, progress, int(start), int(count))
    if mode == "m4":
        out_path = argv[2]
        res = run_m4()
        Path(out_path).write_text(json.dumps(res, indent=1),
                                  encoding="utf-8")
        print(f"M4 caught {res['m4']['caught']}/{res['m4']['copies']} "
              f"-> {res['m4']['verdict']}")
        return 0 if res["verdict"] == "PASS" else 1
    if mode == "m5":
        out_path = argv[2]
        res = run_m5()
        Path(out_path).write_text(json.dumps(res, indent=1),
                                  encoding="utf-8")
        print(f"M5 overhead median/max "
              f"{res['m5']['per_turn_overhead_median_ms']}/"
              f"{res['m5']['per_turn_overhead_max_ms']} ms; open 10k "
              f"{res['m5']['open_10000_turns_s']} s "
              f"({res['m5']['open_10000_turns_lines']} lines)")
        return 0
    if mode == "merge":
        paths = argv[2:7]
        out_path = argv[7]
        parts = [json.loads(Path(p).read_text(encoding="utf-8"))
                 for p in paths]
        res = {"m1": parts[0]["m1"], "m2": parts[1]["m2"],
               "m3": parts[2]["m3"], "m4": parts[3]["m4"],
               "m5": parts[4]["m5"],
               "verdict": ("PASS" if all(p["verdict"] == "PASS"
                                         for p in parts[:4]) else "FAIL")}
        Path(out_path).write_text(json.dumps(res, indent=1),
                                  encoding="utf-8")
        print("VERDICT:", res["verdict"])
        return 0 if res["verdict"] == "PASS" else 1
    raise SystemExit("mode must be m1|m2|m3|m3child|m4|m5|merge")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
