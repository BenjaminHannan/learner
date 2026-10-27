#!/usr/bin/env python3
"""Exp 138h M4/G1/G3-suites driver -- junk + rt143 + sessions + bench + director probes.

Mirrors scripts/fable_fix138g_suites.py (same sealed cases + judges,
read-only); only the loop under test is loop138h (fresh in-process loops
/ Loop138hDaemon with idle_seconds, sleep_threshold=100000). Compares
per-case against the SEALED loop138g rows (move check; every move must be
in the sealed predicted set) AND against the sealed loop138b rows
(0-new-wrong absolutes + the 7 M4 cases). G3 director probes: the 5 sealed
layer-B1 pairs (teach then ask, fresh loop each) with sealed expected
replies. Outputs into artifacts/fable-agent138h-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed; one suite at a
time under parallel-agent load):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138h_suites.py --only junk|rt143|sessions|bench|g3|all
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix139b_probe as P139b  # noqa: E402 (judge, read-only)
import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
import fable_fix150_probe as P150  # noqa: E402 (judge, read-only)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)
import fable_loop138h_agent as L138H  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-agent138h-20260922"
ART138G = ROOT / "artifacts" / "fable-agent138g-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"
ART139B = ROOT / "artifacts" / "fable-fix139b-20260922"
ART144 = ROOT / "artifacts" / "fable-fix144-20260922"
ART150 = ROOT / "artifacts" / "fable-fix150-20260922"

SEVEN = {"redteam136": ["C124", "C127", "C129", "C142"],
         "cases139b": ["C10", "C21"]}

CLARIFY138G = ("I do not know that from what you taught me. "
               "I have no record of it, so I will not guess. "
               "I didn't understand that, I don't know \u2014 could "
               "you say it another way?")


def build138h(extra: dict) -> object:
    cfg = copy.deepcopy(L138H.DEFAULT_CONFIG138H)
    cfg.update(extra)
    return L138H.build_agent138h(cfg)


def new_daemon138h(root: Path):
    cfg = copy.deepcopy(L138H.DEFAULT_CONFIG138H)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L138H.Loop138hDaemon(root, cfg=cfg, idle_seconds=3600.0)


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False,
                                          sort_keys=True) for r in rows)
                    + "\n", encoding="utf-8")


def base_rows(which: str, name: str) -> list[dict]:
    root = ART138G if which == "138g" else ART138B
    return [json.loads(l) for l in
            (root / name).read_text(
                encoding="utf-8").splitlines() if l.strip()]


def check_seven(suite: str, rows: list[dict]) -> dict:
    r_by_id = {r["id"]: r for r in rows}
    b_by_id = {r["id"]: r for r in base_rows(
        "138b", "redteam136-loop138b.json" if suite == "redteam136"
        else "probe139b-loop138b.json")}
    out = {}
    for cid in SEVEN[suite]:
        r = r_by_id.get(cid, {})
        b = b_by_id.get(cid, {})
        out[cid] = {"verdict138h": r.get("verdict"),
                    "verdict138b": b.get("verdict"),
                    "identical": (r.get("verdict") == b.get("verdict")
                                  and str(r.get("reply", "")).strip()
                                  == str(b.get("reply", "")).strip()
                                  and r.get("stored", "n/a")
                                  == b.get("stored", "n/a"))}
    return out


def moves_vs(rows: list[dict], base: list[dict], tag: str) -> tuple[list, int]:
    b_by_id = {r["id"]: r for r in base}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "base": b["verdict"],
                          tag: r["verdict"],
                          "reply_base": str(b.get("reply", ""))[:120],
                          "reply138h": str(r.get("reply", ""))[:120]})
            if r["verdict"] in ("WRONG-WRITE", "WRONG-ANSWER", "WRONG",
                                "WRONG-REPLY"):
                new_wrong += 1
    return moves, new_wrong


def run_redteam136() -> dict:
    R136.new_daemon139b = new_daemon138h  # type: ignore[method-assign]
    cases = json.loads((ART136 / "cases136.json").read_text(
        encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = ART / "work-rt136"
    workroot.mkdir(parents=True, exist_ok=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    write_rows(ART / "redteam136-loop138h.json", rows)
    moves_g, _ = moves_vs(rows, base_rows("138g", "redteam136-loop138g.json"),
                          "loop138h")
    _, new_wrong_b = moves_vs(rows, base_rows("138b",
                                              "redteam136-loop138b.json"),
                              "loop138h")
    return {"suite": "redteam136", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_138g": moves_g,
            "new_wrong_vs_138b": new_wrong_b,
            "seven": check_seven("redteam136", rows)}


def run_cases150() -> dict:
    cases = json.loads((ART150 / "cases150.json").read_text(
        encoding="utf-8"))
    rows = [P150.run_case(row, build138h) for row in cases]
    write_rows(ART / "probe150-loop138h.json", rows)
    b_by_id = {r["id"]: r for r in base_rows(
        "138g", "probe150-loop138g.json")}
    moves = []
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"] or r["reply"] != b["reply"]:
            moves.append({"id": r["id"], "loop138g": b["verdict"],
                          "loop138h": r["verdict"]})
    return {"suite": "cases150", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_138g": moves}


def run_f1() -> dict:
    cases = json.loads((ART144 / "f1-cases.json").read_text(
        encoding="utf-8"))["cases"]
    rows = []
    for row in cases:
        t0 = time.time()
        with tempfile.TemporaryDirectory(
                prefix=row["id"] + "_") as tmp:
            try:
                loop = build138h({"state_dir": tmp,
                                  "sleep_threshold": 100000})
                reply = " ".join(loop.turn(row["text"]))
                stored = [list(t) for t in L90.notebook_triples(loop.nb)]
            except Exception as exc:  # noqa: BLE001
                rows.append({"id": row["id"], "kind": row["kind"],
                             "verdict": "HARNESS-ERROR",
                             "reply": repr(exc)[:120], "stored": []})
                continue
        rep = {"id": row["id"], "kind": row["kind"], "text": row["text"],
               "stored": stored, "reply": reply.strip()[:160],
               "seconds": round(time.time() - t0, 3)}
        if row["kind"] == "must-write":
            want = [list(row["expect"])]
            rep["expect"] = row["expect"]
            if stored == want and reply.strip().startswith("Saved:"):
                rep["verdict"] = "OK"
            elif not stored:
                rep["verdict"] = "MISSED"
            else:
                rep["verdict"] = "WRONG-WRITE"
        else:
            if not stored and not reply.strip().startswith("Saved:"):
                rep["verdict"] = "OK"
            else:
                rep["verdict"] = "WRONG-WRITE"
        rows.append(rep)
    write_rows(ART / "f1-loop138h.json", rows)
    base_f1 = base_rows("138g", "f1-loop138g.json")
    b_by_id = {r["id"]: r for r in base_f1}
    moves = [{"id": r["id"], "loop138g": b_by_id[r["id"]]["verdict"],
              "loop138h": r["verdict"]}
             for r in rows
             if r["id"] in b_by_id and
             b_by_id[r["id"]]["verdict"] != r["verdict"]]
    return {"suite": "f1", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "non_ok": [r for r in rows if r["verdict"] != "OK"],
            "moves_vs_138g": moves}


def run_cases139b() -> dict:
    cases = json.loads((ART139B / "cases139b.json").read_text(
        encoding="utf-8"))
    cases139 = json.loads(
        (ROOT / "artifacts" / "fable-fix139-20260922" / "cases139.json").read_text(
            encoding="utf-8"))
    if isinstance(cases139, dict):
        cases139 = cases139.get("cases", cases139)
    cases = list(cases139) + list(cases)
    rows = [P139b.run_case(row, build138h) for row in cases]
    write_rows(ART / "probe139b-loop138h.json", rows)
    b_by_id = {r["id"]: r for r in base_rows(
        "138g", "probe139b-loop138g.json")}
    moves = []
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "loop138g": b["verdict"],
                          "loop138h": r["verdict"]})
    return {"suite": "cases139b", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_138g": moves,
            "seven": check_seven("cases139b", rows)}


def run_junk() -> dict:
    out: dict = {}
    for fn in (run_redteam136, run_cases150, run_f1, run_cases139b):
        rep = fn()
        out[rep["suite"]] = rep
        print(f"M4 {rep['suite']}: n={rep['n']} {rep['counter']} "
              f"moves_vs_138g={len(rep.get('moves_vs_138g', []))}",
              flush=True)
        for m in rep.get("moves_vs_138g", []) or []:
            print(f"  MOVE {m}", flush=True)
        for cid, s in rep.get("seven", {}).items():
            print(f"  SEVEN {cid}: 138h={s['verdict138h']} "
                  f"138b={s['verdict138b']} identical={s['identical']}",
                  flush=True)
    return out


def run_rt143() -> dict:
    import fable_redteam143_run as R143  # noqa: E402 (judge, read-only)
    R143.Loop132Daemon = L138H.Loop138hDaemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L138H.DEFAULT_CONFIG138H)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / "scratch143-loop138h"
    rows: list[dict] = []
    for case in suite["cases"]:
        rec = R143.run_case(case, scratch / case["id"], markers)
        rows.append(rec)
    (ART / "redteam143-loop138h.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    base = json.loads(
        (ART138G / "redteam143-loop138g.json").read_text(encoding="utf-8"))
    b_by_id = {r["id"]: r for r in base["rows"]}
    moves, _ = moves_vs(rows, base["rows"], "loop138h")
    base_b = json.loads(
        (ART138B / "redteam143-loop138b.json").read_text(encoding="utf-8"))
    _, new_wrong_b = moves_vs(rows, base_b["rows"], "loop138h")
    m3 = next((r for r in rows if r["id"] == "M3"), {})
    b3 = b_by_id.get("M3", {})
    m3_vs_138g = (m3.get("verdict") == b3.get("verdict")
                  and str(m3.get("reply", "")).strip()
                  == str(b3.get("reply", "")).strip())
    return {"suite": "rt143",
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_138g": moves, "new_wrong_vs_138b": new_wrong_b,
            "M3_vs_138g_identical": m3_vs_138g,
            "M3_138h": {k: m3.get(k) for k in ("verdict", "reply")}}


def run_sessions() -> dict:
    import fable_session152_run as S152R  # noqa: E402 (judge, read-only)
    sessions_out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = ART / "work-sessions-loop138h" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(L138H.DEFAULT_CONFIG138H)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L138H.Loop138hDaemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    (ART / "sessions152-loop138h.json").write_text(
        json.dumps(sessions_out, indent=1, ensure_ascii=False),
        encoding="utf-8")
    out138g = json.loads(
        (ART138G / "sessions152-loop138g.json").read_text(encoding="utf-8"))
    moves, new_wrong, new_writes = [], 0, []
    counts138g: Counter = Counter()
    counts138h: Counter = Counter()
    for sid, turns in sessions_out.items():
        for t, b in zip(turns, out138g.get(sid, [])):
            counts138g[b["verdict"]] += 1
            counts138h[t["verdict"]] += 1
            if t["verdict"] != b["verdict"]:
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop138g": b["verdict"],
                              "loop138h": t["verdict"],
                              "reply138g": str(b["reply"]).strip()[:120],
                              "reply138h": str(t["reply"]).strip()[:120],
                              "why": t["why"][:160]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
            bw = (b.get("fact_writes") or b.get("writes") or [])
            tw = (t.get("fact_writes") or t.get("writes") or [])
            if tw and tw != bw:
                new_writes.append({"session": sid, "n": t["n"],
                                   "loop138g_writes": bw,
                                   "loop138h_writes": tw})
    return {"suite": "sessions", "loop138g": dict(counts138g),
            "loop138h": dict(counts138h),
            "new_wrong_vs_138g": new_wrong, "moves_vs_138g": moves,
            "new_writes": new_writes}


def run_bench(only: str = "all") -> dict:
    import fable_bench121_run as B  # noqa: E402 (scorer, read-only)
    B.Loop121Daemon = L138H.Loop138hDaemon
    cfg = copy.deepcopy(L138H.DEFAULT_CONFIG138H)
    cfg["sleep_threshold"] = 100000
    tag = "loop138h"
    DATA134 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
    DATA132 = ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl"
    splits = (
        ("new_121_4hop", B.DATA_NEW,
         "fable_bench121_loop138g_new_121_4hop_rows.jsonl"),
        ("old_s2fresh_4hop", B.DATA_OLD,
         "fable_bench121_loop138g_old_s2fresh_4hop_rows.jsonl"),
        ("edit200", DATA134, "fable_bench121_loop138g_edit200_rows.jsonl"),
        ("bench132_4hop", DATA132,
         "fable_bench121_loop138g_bench132_4hop_rows.jsonl"),
    )
    want = only.split(",")
    if want != ["all"]:
        splits = [s for s in splits if s[0] in want]
    workroot = ART / "scratch-bench121-loop138h"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    summary: dict = {"seconds": 0.0, "scorer": "v2", "agent": tag,
                     "splits": {}}
    for stag, path, sealed_name in splits:
        items = [json.loads(line) for line in
                 Path(str(path)).read_text(
                     encoding="utf-8").splitlines() if line.strip()]
        rows = [B.run_item(it, workroot / stag, copy.deepcopy(cfg))
                for it in items]
        (ART / f"fable_bench121_{tag}_{stag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        table = B.summarize(rows)
        cell = {"n": len(rows),
                "correct": sum(1 for r in rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in rows if r["verdict"] == "wrong")}
        base_rows_l = [json.loads(line) for line in
                       (ART138G / sealed_name).read_text(
                           encoding="utf-8").splitlines() if line.strip()]
        s_by_id = {r["id"]: r for r in base_rows_l}
        moves, new_wrong = [], 0
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                continue
            if r["verdict"] != s["verdict"]:
                moves.append({"id": r["id"], "loop138g": s["verdict"],
                              tag: r["verdict"]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
        summary["splits"][stag] = {tag: cell, "by_type": table,
                                   "moves_vs_138g": moves,
                                   "new_wrong_vs_138g": new_wrong}
        print(f"{stag}: {tag} {cell} new_wrong={new_wrong} "
              f"moves={len(moves)}", flush=True)
        for m in moves:
            print(f"  MOVE {m}", flush=True)
    return summary


G3_PAIRS = [
    {"id": "G3h-1a", "turn": "The Beatles' drummer is Ringo.",
     "expect_reply": CLARIFY138G, "expect_triples": []},
    {"id": "G3h-1b", "turn": "Who is the Beatles' drummer?",
     "expect_reply": CLARIFY138G, "expect_triples": []},
    {"id": "G3h-2a", "turn": "Tom's boss is Lee.",
     "expect_reply": "Saved: Tom's boss is Lee.",
     "expect_triples": [["Tom", "boss", "Lee"]]},
    {"id": "G3h-2b", "turn": "who is toms boss",
     "expect_reply": "tom's boss is Lee.",
     "expect_triples": [["Tom", "boss", "Lee"]]},
    {"id": "G3h-3a", "turn": "My sister is Ada.",
     "expect_reply": "Saved: your sister is Ada.",
     "expect_triples": [["USER", "sister", "Ada"]]},
    {"id": "G3h-3b", "turn": "Who is my sister?",
     "expect_reply": "Your sister is Ada.",
     "expect_triples": [["USER", "sister", "Ada"]]},
    {"id": "G3h-4a", "turn": "My name is Juno.",
     "expect_reply": "You never told me your name, so I do not know it.",
     "expect_triples": []},
    {"id": "G3h-4b", "turn": "What is my name?",
     "expect_reply": "I don't know your name yet.",
     "expect_triples": []},
    {"id": "G3h-5a", "turn": "Kwame lives in Accra.",
     "expect_reply": "Saved: Kwame's city is Accra.",
     "expect_triples": [["Kwame", "city", "Accra"]]},
    {"id": "G3h-5b", "turn": "Where does Kwame live?",
     "expect_reply": "Kwame's city is Accra.",
     "expect_triples": [["Kwame", "city", "Accra"]]},
]

G3H_PAIRS = [("G3h-1", "The Beatles' drummer is Ringo.",
              "Who is the Beatles' drummer?"),
             ("G3h-2", "Tom's boss is Lee.", "who is toms boss"),
             ("G3h-3", "My sister is Ada.", "Who is my sister?"),
             ("G3h-4", "My name is Juno.", "What is my name?"),
             ("G3h-5", "Kwame lives in Accra.", "Where does Kwame live?")]


def run_g3() -> dict:
    rows = []
    by_id = {c["id"]: c for c in G3_PAIRS}
    for pid, teach, ask in G3H_PAIRS:
        with tempfile.TemporaryDirectory(
                prefix="g3-138h-") as tmp:
            loop = build138h({"state_dir": tmp,
                              "sleep_threshold": 100000})
            for cid, turn in ((pid + "a", teach), (pid + "b", ask)):
                case = by_id[cid]
                reply = " ".join(loop.turn(turn)).strip()
                stored = [list(t) for t in L90.notebook_triples(loop.nb)]
                ok = (reply == case["expect_reply"]
                      and stored == case["expect_triples"])
                rows.append({"id": cid, "turn": turn,
                             "reply": reply, "stored": stored,
                             "expect_reply": case["expect_reply"],
                             "expect_triples": case["expect_triples"],
                             "verdict": "OK" if ok else "FAIL"})
    (ART / "g3-138h-probes.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"suite": "g3-director", "n": len(rows),
            "ok": sum(1 for r in rows if r["verdict"] == "OK"),
            "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 138h M4/G1/G3 suites")
    ap.add_argument("--only", default="all",
                    help="comma list of junk,rt143,sessions,bench,g3 or all")
    ap.add_argument("--bench-only", default="all")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc = 0
    want = args.only.split(",")
    out: dict = {}
    if "all" in want or "junk" in want:
        t1 = time.time()
        out["junk"] = run_junk()
        out["junk"]["seconds"] = round(time.time() - t1, 1)
        (ART / "junk138h-summary.json").write_text(
            json.dumps(out["junk"], indent=1, sort_keys=True),
            encoding="utf-8")
    if "all" in want or "rt143" in want:
        t1 = time.time()
        out["rt143"] = run_rt143()
        out["rt143"]["seconds"] = round(time.time() - t1, 1)
        print(f"M4 rt143: {out['rt143']['counter']} "
              f"moves={len(out['rt143']['moves_vs_138g'])} "
              f"new_wrong_vs_138b={out['rt143']['new_wrong_vs_138b']}",
              flush=True)
    if "all" in want or "sessions" in want:
        t1 = time.time()
        out["sessions"] = run_sessions()
        out["sessions"]["seconds"] = round(time.time() - t1, 1)
        print(f"M4 sessions: {out['sessions']['loop138h']} "
              f"moves={len(out['sessions']['moves_vs_138g'])} "
              f"new_writes={len(out['sessions']['new_writes'])}",
              flush=True)
        for m in out["sessions"]["moves_vs_138g"][:20]:
            print(f"  MOVE {m}", flush=True)
        for w in out["sessions"]["new_writes"][:20]:
            print(f"  WRITE {w}", flush=True)
    if "all" in want or "bench" in want:
        t1 = time.time()
        out["bench"] = run_bench(args.bench_only)
        out["bench"]["seconds"] = round(time.time() - t1, 1)
        (ART / "bench138h-summary.json").write_text(
            json.dumps(out["bench"], indent=1, sort_keys=True),
            encoding="utf-8")
    if "all" in want or "g3" in want:
        t1 = time.time()
        out["g3"] = run_g3()
        out["g3"]["seconds"] = round(time.time() - t1, 1)
        print(f"G3: ok={out['g3']['ok']}/{out['g3']['n']}", flush=True)
        for r in out["g3"]["rows"]:
            if r["verdict"] != "OK":
                print(f"  G3FAIL {r['id']}: got={r['reply'][:120]!r} "
                      f"want={r['expect_reply'][:120]!r}", flush=True)
                rc = 1
    out["seconds"] = round(time.time() - t0, 1)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True),
                                  encoding="utf-8")
        print(f"wrote {args.out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
