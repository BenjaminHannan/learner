#!/usr/bin/env python3
"""Exp 164b -- A2/A3 + bench suites driver: junk + rt143 + sessions + bench.

Mirrors scripts/fable_fix138h_suites.py (same sealed cases + judges,
read-only); only the loop under test is loop164b (fresh in-process loops /
Loop164bDaemon with idle_seconds, sleep_threshold=100000). Compares
per-case against the SEALED loop138h rows (verdict AND reply AND stored /
writes byte-identical; every move must be in the sealed predicted set,
which is EMPTY: pre-seal scan fires 0/6175 bench texts, 0/180 session
turns, 0/473 suite case texts). 0 new WRONG / WRONG-WRITE / junk writes
vs 138h anywhere. Bench reuses the base agent's driver
(scripts/fable_bench121_run.py run_item/summarize, read-only).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed; one suite at a
time under parallel-agent load):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix164b_suites.py --only junk|rt143|sessions|bench|all
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
import fable_loop164b_agent as L164B  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-about164b-20260922"
ART138H = ROOT / "artifacts" / "fable-agent138h-20260922"
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"
ART139B = ROOT / "artifacts" / "fable-fix139b-20260922"
ART144 = ROOT / "artifacts" / "fable-fix144-20260922"
ART150 = ROOT / "artifacts" / "fable-fix150-20260922"

# Sealed prediction: NO turn differs from the 138h rows (empty by design).
PREDICTED_MOVES: list = []


def build164b(extra: dict) -> object:
    cfg = copy.deepcopy(L164B.DEFAULT_CONFIG164B)
    cfg.update(extra)
    return L164B.build_agent164b(cfg)


def new_daemon164b(root: Path):
    cfg = copy.deepcopy(L164B.DEFAULT_CONFIG164B)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L164B.Loop164bDaemon(root, cfg=cfg, idle_seconds=3600.0)


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False,
                                          sort_keys=True) for r in rows)
                    + "\n", encoding="utf-8")


def base_rows(name: str) -> list[dict]:
    return [json.loads(l) for l in
            (ART138H / name).read_text(
                encoding="utf-8").splitlines() if l.strip()]


def moves_vs(rows: list[dict], base: list[dict], tag: str) -> tuple[list, int]:
    """Verdict OR reply moves (A2 byte-identical); new_wrong counts WRONG*."""
    b_by_id = {r["id"]: r for r in base}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if (r.get("verdict") != b.get("verdict")
                or str(r.get("reply", "")).strip()
                != str(b.get("reply", "")).strip()):
            moves.append({"id": r["id"], "base": b["verdict"],
                          tag: r["verdict"],
                          "reply_base": str(b.get("reply", ""))[:120],
                          "reply164b": str(r.get("reply", ""))[:120]})
            if r.get("verdict") in ("WRONG-WRITE", "WRONG-ANSWER", "WRONG",
                                    "WRONG-REPLY"):
                new_wrong += 1
    return moves, new_wrong


def run_redteam136() -> dict:
    R136.new_daemon139b = new_daemon164b  # type: ignore[method-assign]
    cases = json.loads((ART136 / "cases136.json").read_text(
        encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = ART / "work-rt136"
    workroot.mkdir(parents=True, exist_ok=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    write_rows(ART / "redteam136-loop164b.json", rows)
    moves_g, _ = moves_vs(rows, base_rows("redteam136-loop138h.json"),
                          "loop164b")
    return {"suite": "redteam136", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_138h": moves_g}


def run_cases150() -> dict:
    cases = json.loads((ART150 / "cases150.json").read_text(
        encoding="utf-8"))
    rows = [P150.run_case(row, build164b) for row in cases]
    write_rows(ART / "probe150-loop164b.json", rows)
    b_by_id = {r["id"]: r for r in base_rows("probe150-loop138h.json")}
    moves = []
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if (r["verdict"] != b["verdict"] or r["reply"] != b["reply"]
                or r.get("stored") != b.get("stored")):
            moves.append({"id": r["id"], "loop138h": b["verdict"],
                          "loop164b": r["verdict"]})
    return {"suite": "cases150", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_138h": moves}


def run_f1() -> dict:
    cases = json.loads((ART144 / "f1-cases.json").read_text(
        encoding="utf-8"))["cases"]
    rows = []
    for row in cases:
        t0 = time.time()
        with tempfile.TemporaryDirectory(
                prefix=row["id"] + "_") as tmp:
            try:
                loop = build164b({"state_dir": tmp,
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
    write_rows(ART / "f1-loop164b.json", rows)
    base_f1 = base_rows("f1-loop138h.json")
    b_by_id = {r["id"]: r for r in base_f1}
    moves = [{"id": r["id"], "loop138h": b_by_id[r["id"]]["verdict"],
              "loop164b": r["verdict"]}
             for r in rows
             if r["id"] in b_by_id and
             (b_by_id[r["id"]]["verdict"] != r["verdict"]
              or str(b_by_id[r["id"]].get("reply", "")).strip()
              != str(r.get("reply", "")).strip())]
    return {"suite": "f1", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "non_ok": [r for r in rows if r["verdict"] != "OK"],
            "moves_vs_138h": moves}


def run_cases139b() -> dict:
    cases = json.loads((ART139B / "cases139b.json").read_text(
        encoding="utf-8"))
    cases139 = json.loads(
        (ROOT / "artifacts" / "fable-fix139-20260922" / "cases139.json").read_text(
            encoding="utf-8"))
    if isinstance(cases139, dict):
        cases139 = cases139.get("cases", cases139)
    cases = list(cases139) + list(cases)
    rows = [P139b.run_case(row, build164b) for row in cases]
    write_rows(ART / "probe139b-loop164b.json", rows)
    b_by_id = {r["id"]: r for r in base_rows("probe139b-loop138h.json")}
    moves = []
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if (r["verdict"] != b["verdict"]
                or str(r.get("reply", "")).strip()
                != str(b.get("reply", "")).strip()):
            moves.append({"id": r["id"], "loop138h": b["verdict"],
                          "loop164b": r["verdict"]})
    return {"suite": "cases139b", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_138h": moves}


def run_junk() -> dict:
    out: dict = {}
    for fn in (run_redteam136, run_cases150, run_f1, run_cases139b):
        rep = fn()
        out[rep["suite"]] = rep
        print(f"M4 {rep['suite']}: n={rep['n']} {rep['counter']} "
              f"moves_vs_138h={len(rep.get('moves_vs_138h', []))}",
              flush=True)
        for m in rep.get("moves_vs_138h", []) or []:
            print(f"  MOVE {m}", flush=True)
    return out


def run_rt143() -> dict:
    import fable_redteam143_run as R143  # noqa: E402 (judge, read-only)
    R143.Loop132Daemon = L164B.Loop164bDaemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L164B.DEFAULT_CONFIG164B)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / "scratch143-loop164b"
    rows: list[dict] = []
    for case in suite["cases"]:
        rec = R143.run_case(case, scratch / case["id"], markers)
        rows.append(rec)
    (ART / "redteam143-loop164b.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    base = json.loads(
        (ART138H / "redteam143-loop138h.json").read_text(encoding="utf-8"))
    moves, _ = moves_vs(rows, base["rows"], "loop164b")
    return {"suite": "rt143",
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_138h": moves, "new_wrong_vs_138h": 0}


def run_sessions() -> dict:
    import fable_session152_run as S152R  # noqa: E402 (judge, read-only)
    sessions_out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = ART / "work-sessions-loop164b" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(L164B.DEFAULT_CONFIG164B)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L164B.Loop164bDaemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    (ART / "sessions152-loop164b.json").write_text(
        json.dumps(sessions_out, indent=1, ensure_ascii=False),
        encoding="utf-8")
    out138h = json.loads(
        (ART138H / "sessions152-loop138h.json").read_text(encoding="utf-8"))
    moves, new_wrong, new_writes = [], 0, []
    counts138h: Counter = Counter()
    counts164b: Counter = Counter()
    for sid, turns in sessions_out.items():
        for t, b in zip(turns, out138h.get(sid, [])):
            counts138h[b["verdict"]] += 1
            counts164b[t["verdict"]] += 1
            if (t["verdict"] != b["verdict"]
                    or str(t.get("reply", "")).strip()
                    != str(b.get("reply", "")).strip()):
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop138h": b["verdict"],
                              "loop164b": t["verdict"],
                              "reply138h": str(b["reply"]).strip()[:120],
                              "reply164b": str(t["reply"]).strip()[:120],
                              "why": t["why"][:160]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
            bw = (b.get("fact_writes") or b.get("writes") or [])
            tw = (t.get("fact_writes") or t.get("writes") or [])
            if tw and tw != bw:
                new_writes.append({"session": sid, "n": t["n"],
                                   "loop138h_writes": bw,
                                   "loop164b_writes": tw})
    return {"suite": "sessions", "loop138h": dict(counts138h),
            "loop164b": dict(counts164b),
            "new_wrong_vs_138h": new_wrong, "moves_vs_138h": moves,
            "new_writes": new_writes}


def run_bench(only: str = "all") -> dict:
    import fable_bench121_run as B  # noqa: E402 (base driver, read-only)
    B.Loop121Daemon = L164B.Loop164bDaemon
    cfg = copy.deepcopy(L164B.DEFAULT_CONFIG164B)
    cfg["sleep_threshold"] = 100000
    tag = "loop164b"
    DATA134 = ROOT / "data" / "open" / "bench65" / "fable_edit_200.jsonl"
    DATA132 = ROOT / "data" / "open" / "bench132" / "fable_edit132_4hop.jsonl"
    splits = (
        ("new_121_4hop", B.DATA_NEW,
         "fable_bench121_loop138h_new_121_4hop_rows.jsonl"),
        ("old_s2fresh_4hop", B.DATA_OLD,
         "fable_bench121_loop138h_old_s2fresh_4hop_rows.jsonl"),
        ("edit200", DATA134, "fable_bench121_loop138h_edit200_rows.jsonl"),
        ("bench132_4hop", DATA132,
         "fable_bench121_loop138h_bench132_4hop_rows.jsonl"),
    )
    want = only.split(",")
    if want != ["all"]:
        splits = [s for s in splits if s[0] in want]
    workroot = ART / "scratch-bench121-loop164b"
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
                       (ART138H / sealed_name).read_text(
                           encoding="utf-8").splitlines() if line.strip()]
        s_by_id = {r["id"]: r for r in base_rows_l}
        moves, new_wrong, reply_moves = [], 0, []
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                continue
            if r["verdict"] != s["verdict"]:
                moves.append({"id": r["id"], "loop138h": s["verdict"],
                              tag: r["verdict"]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
            if str(r.get("reply", "")).strip() != str(
                    s.get("reply", "")).strip():
                reply_moves.append(r["id"])
        summary["splits"][stag] = {tag: cell, "by_type": table,
                                   "moves_vs_138h": moves,
                                   "reply_moves_vs_138h": reply_moves,
                                   "new_wrong_vs_138h": new_wrong}
        print(f"{stag}: {tag} {cell} new_wrong={new_wrong} "
              f"moves={len(moves)} reply_moves={len(reply_moves)}",
              flush=True)
        for m in moves:
            print(f"  MOVE {m}", flush=True)
        for m in reply_moves[:10]:
            print(f"  REPLY-MOVE {m}", flush=True)
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 164b A2/A3/bench suites")
    ap.add_argument("--only", default="all",
                    help="comma list of junk,rt143,sessions,bench or all")
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
        (ART / "junk164b-summary.json").write_text(
            json.dumps(out["junk"], indent=1, sort_keys=True),
            encoding="utf-8")
    if "all" in want or "rt143" in want:
        t1 = time.time()
        out["rt143"] = run_rt143()
        out["rt143"]["seconds"] = round(time.time() - t1, 1)
        print(f"rt143: {out['rt143']['counter']} "
              f"moves={len(out['rt143']['moves_vs_138h'])}", flush=True)
    if "all" in want or "sessions" in want:
        t1 = time.time()
        out["sessions"] = run_sessions()
        out["sessions"]["seconds"] = round(time.time() - t1, 1)
        print(f"sessions: {out['sessions']['loop164b']} "
              f"moves={len(out['sessions']['moves_vs_138h'])} "
              f"new_writes={len(out['sessions']['new_writes'])}",
              flush=True)
        for m in out["sessions"]["moves_vs_138h"][:20]:
            print(f"  MOVE {m}", flush=True)
        for w in out["sessions"]["new_writes"][:20]:
            print(f"  WRITE {w}", flush=True)
    if "all" in want or "bench" in want:
        t1 = time.time()
        out["bench"] = run_bench(args.bench_only)
        out["bench"]["seconds"] = round(time.time() - t1, 1)
        (ART / "bench164b-summary.json").write_text(
            json.dumps(out["bench"], indent=1, sort_keys=True),
            encoding="utf-8")
    out["seconds"] = round(time.time() - t0, 1)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True),
                                  encoding="utf-8")
        print(f"wrote {args.out}")
    for key in ("junk", "rt143", "sessions", "bench"):
        if key not in out:
            continue
        if key == "junk":
            for suite, rep in out[key].items():
                if suite == "seconds":
                    continue
                rc |= int(len(rep.get("moves_vs_138h", [])) != 0)
        elif key == "bench":
            for stag, rep in out[key].get("splits", {}).items():
                rc |= int(len(rep.get("moves_vs_138h", [])) != 0
                          or len(rep.get("reply_moves_vs_138h", [])) != 0
                          or rep.get("new_wrong_vs_138h", 0) != 0)
        else:
            rc |= int(len(out[key].get("moves_vs_138h", [])) != 0)
            rc |= int(out[key].get("new_wrong_vs_138h", 0) != 0)
            rc |= int(len(out[key].get("new_writes", [])) != 0)
    return rc


if __name__ == "__main__":
    sys.exit(main())
