#!/usr/bin/env python3
"""Exp 189 R1/R2 driver -- say-again repeats + frozen-suite regression.

R1 (sealed `cases189.json`, >= 30 turns, fresh in-process loops):
  base loop138g and loop189 stepped in lockstep on the same turns.
  - kind=noprev (repeat with no previous reply): 189 must reply the one
    fixed line NO_PREV189, events unchanged.
  - kind=repeat: 189 must reply its own previous NON-REPEAT reply
    byte-identical (== base's previous reply on non-repeat turns),
    events unchanged (triples + facts + events.jsonl lines identical
    before/after: a repeated "Saved:" never writes twice).
  - kind=trap/base (teaches, asks, Say-X pretend traps, hearsay/hypo,
    self): 189 reply byte-identical to loop138g reply AND stored
    triples identical AND events identical.
R2 (frozen suites vs the base agent): redteam136, cases150, f1,
  cases139b, redteam143, sessions152 via the 138g suites-driver logic
  with loop189, compared per-case against the SEALED loop138g rows
  (0 moves predicted); bench121 4 splits via the base driver's scorer
  (0 new wrong predicted); marks123 via stock
  `scripts/fable_marks123_all.py` compared per-case vs sealed marks138g
  (0 moves predicted).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed; heavy suites
one at a time):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix189_sayagain.py --only r1|junk|rt143|sessions|bench|marks123|all
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138g_agent as L138G  # noqa: E402 (base agent, read-only)
import fable_loop189_agent as L189  # noqa: E402 (agent under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-sayagain189-20260922"
ART138G = ROOT / "artifacts" / "fable-agent138g-20260922"


def _snap(loop, state_dir: Path) -> dict:
    triples = [list(t) for t in L90.notebook_triples(loop.nb)]
    facts = len(set(loop.nb.facts))
    ev = state_dir / "events.jsonl"
    lines = 0
    if ev.exists():
        with open(ev, "rb") as fh:
            lines = sum(1 for _ in fh)
    return {"triples": triples, "facts": facts, "events": lines}


def run_r1() -> dict:
    cases = json.loads((ART / "cases189.json").read_text(encoding="utf-8"))
    assert len(cases) >= 30, f"sealed R1 case file has {len(cases)} < 30"
    out_rows: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="r1-base-") as tb, \
            tempfile.TemporaryDirectory(prefix="r1-189-") as t189:
        cb = copy.deepcopy(L138G.DEFAULT_CONFIG138G)
        cb["state_dir"] = tb
        cb["sleep_threshold"] = 100000
        base = L138G.build_agent138g(cb)
        c9 = copy.deepcopy(L189.DEFAULT_CONFIG189)
        c9["state_dir"] = t189
        c9["sleep_threshold"] = 100000
        agent = L189.build_agent189(c9)
        prev_nonrepeat: str | None = None
        for row in cases:
            turn, kind = row["turn"], row["kind"]
            sb, s9 = _snap(base, Path(tb)), _snap(agent, Path(t189))
            rb = " ".join(base.turn(turn)).strip()
            r9 = " ".join(agent.turn(turn)).strip()
            s9_after = _snap(agent, Path(t189))
            eb, e9 = _snap(base, Path(tb)), s9_after
            if kind == "noprev":
                ok = (r9 == L189.NO_PREV189 and s9_after == s9)
                note = "fixed-line" if ok else f"got {r9!r}"
            elif kind == "repeat":
                want = prev_nonrepeat if prev_nonrepeat is not None \
                    else L189.NO_PREV189
                ok = (r9 == want and s9_after == s9)
                note = "verbatim-echo" if ok else (
                    f"want {want!r} got {r9!r} snap={s9_after != s9}")
            else:  # trap / base turns: byte-identical to loop138g
                ok = (r9 == rb and e9["triples"] == eb["triples"]
                      and e9["events"] == eb["events"]
                      and e9["facts"] == eb["facts"])
                note = "identical" if ok else (
                    f"base {rb!r} vs189 {r9!r} "
                    f"triples={e9['triples'] != eb['triples']}")
            if kind not in ("noprev", "repeat"):
                prev_nonrepeat = r9
            out_rows.append({"id": row["id"], "kind": kind, "turn": turn,
                             "reply189": r9, "reply138g": rb,
                             "verdict": "OK" if ok else "FAIL",
                             "note": note})
    (ART / "r1-sayagain189.json").write_text(
        json.dumps(out_rows, indent=1, ensure_ascii=False), encoding="utf-8")
    by_kind: dict = {}
    for r in out_rows:
        by_kind.setdefault(r["kind"], [0, 0])
        by_kind[r["kind"]][1] += 1
        by_kind[r["kind"]][0] += (r["verdict"] == "OK")
    rep = {"suite": "r1", "n": len(out_rows),
           "ok": sum(1 for r in out_rows if r["verdict"] == "OK"),
           "by_kind": {k: f"{a}/{b}" for k, (a, b) in by_kind.items()},
           "fails": [r for r in out_rows if r["verdict"] != "OK"]}
    print(f"R1: {rep['ok']}/{rep['n']} {rep['by_kind']}", flush=True)
    for r in rep["fails"]:
        print(f"  R1FAIL {r['id']} {r['turn']!r}: {r['note']}", flush=True)
    return rep


def build189(extra: dict) -> object:
    cfg = copy.deepcopy(L189.DEFAULT_CONFIG189)
    cfg.update(extra)
    return L189.build_agent189(cfg)


def new_daemon189(root: Path):
    cfg = copy.deepcopy(L189.DEFAULT_CONFIG189)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L189.Loop189Daemon(root, cfg=cfg, idle_seconds=3600.0)


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False,
                                        sort_keys=True) for r in rows)
                    + "\n", encoding="utf-8")


def _sealed_rows(name: str) -> list[dict]:
    return [json.loads(l) for l in
            (ART138G / name).read_text(encoding="utf-8").splitlines()
            if l.strip()]


def _moves(rows: list[dict], base: list[dict]) -> tuple[list, int]:
    b_by_id = {r["id"]: r for r in base}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if (r.get("verdict") != b.get("verdict")
                or str(r.get("reply", "")).strip()
                != str(b.get("reply", "")).strip()):
            moves.append({"id": r["id"], "loop138g": b.get("verdict"),
                          "loop189": r.get("verdict"),
                          "reply138g": str(b.get("reply", ""))[:120],
                          "reply189": str(r.get("reply", ""))[:120]})
            if r.get("verdict") in ("WRONG-WRITE", "WRONG-ANSWER",
                                    "WRONG", "WRONG-REPLY"):
                new_wrong += 1
    return moves, new_wrong


def run_junk() -> dict:
    import fable_fix139b_probe as P139b  # noqa: E402 (judge, read-only)
    import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
    import fable_fix150_probe as P150  # noqa: E402 (judge, read-only)
    import fable_loop138g_agent as _G  # noqa: E402 (sealed rows exist)
    _ = _G
    out: dict = {}
    ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"
    ART150 = ROOT / "artifacts" / "fable-fix150-20260922"
    ART139B = ROOT / "artifacts" / "fable-fix139b-20260922"
    ART144 = ROOT / "artifacts" / "fable-fix144-20260922"
    # redteam136
    R136.new_daemon139b = new_daemon189  # type: ignore[method-assign]
    cases = json.loads((ART136 / "cases136.json").read_text(
        encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = ART / "work-rt136"
    workroot.mkdir(parents=True, exist_ok=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    _write_rows(ART / "redteam136-loop189.json", rows)
    moves, new_wrong = _moves(rows, _sealed_rows("redteam136-loop138g.json"))
    out["redteam136"] = {"n": len(rows),
                         "counter": dict(Counter(r["verdict"]
                                                 for r in rows)),
                         "moves_vs_138g": moves,
                         "new_wrong_vs_138g": new_wrong}
    print(f"junk redteam136: n={len(rows)} "
          f"{out['redteam136']['counter']} moves={len(moves)} "
          f"new_wrong={new_wrong}", flush=True)
    # cases150
    cases150 = json.loads((ART150 / "cases150.json").read_text(
        encoding="utf-8"))
    rows150 = [P150.run_case(row, build189) for row in cases150]
    _write_rows(ART / "probe150-loop189.json", rows150)
    base150 = {r["id"]: r for r in _sealed_rows("probe150-loop138g.json")}
    m150 = [{"id": r["id"]} for r in rows150 if r["id"] in base150 and (
        r["verdict"] != base150[r["id"]]["verdict"]
        or r["reply"] != base150[r["id"]]["reply"])]
    out["cases150"] = {"n": len(rows150), "moves_vs_138g": m150}
    print(f"junk cases150: n={len(rows150)} moves={len(m150)}", flush=True)
    # f1
    casesf1 = json.loads((ART144 / "f1-cases.json").read_text(
        encoding="utf-8"))["cases"]
    rowsf1 = []
    for row in casesf1:
        t0 = time.time()
        with tempfile.TemporaryDirectory(prefix=row["id"] + "_") as tmp:
            try:
                loop = build189({"state_dir": tmp,
                                 "sleep_threshold": 100000})
                reply = " ".join(loop.turn(row["text"]))
                stored = [list(t) for t in L90.notebook_triples(loop.nb)]
            except Exception as exc:  # noqa: BLE001
                rowsf1.append({"id": row["id"], "kind": row["kind"],
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
        rowsf1.append(rep)
    _write_rows(ART / "f1-loop189.json", rowsf1)
    b1 = {r["id"]: r for r in _sealed_rows("f1-loop138g.json")}
    m1 = [{"id": r["id"]} for r in rowsf1 if r["id"] in b1 and
          b1[r["id"]]["verdict"] != r["verdict"]]
    out["f1"] = {"n": len(rowsf1), "moves_vs_138g": m1}
    print(f"junk f1: n={len(rowsf1)} moves={len(m1)}", flush=True)
    # cases139b
    casesb = json.loads((ART139B / "cases139b.json").read_text(
        encoding="utf-8"))
    cases139 = json.loads(
        (ROOT / "artifacts" / "fable-fix139-20260922" / "cases139.json"
         ).read_text(encoding="utf-8"))
    if isinstance(cases139, dict):
        cases139 = cases139.get("cases", cases139)
    rowsb = [P139b.run_case(row, build189)
             for row in list(cases139) + list(casesb)]
    _write_rows(ART / "probe139b-loop189.json", rowsb)
    bb = {r["id"]: r for r in _sealed_rows("probe139b-loop138g.json")}
    mb = [{"id": r["id"]} for r in rowsb if r["id"] in bb and
          (bb[r["id"]]["verdict"] != r["verdict"]
           or str(bb[r["id"]].get("reply", "")) != str(r.get("reply", "")))]
    out["cases139b"] = {"n": len(rowsb), "moves_vs_138g": mb}
    print(f"junk cases139b: n={len(rowsb)} moves={len(mb)}", flush=True)
    (ART / "junk189-summary.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    return out


def run_rt143() -> dict:
    import fable_redteam143_run as R143  # noqa: E402 (judge, read-only)
    R143.Loop132Daemon = L189.Loop189Daemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L189.DEFAULT_CONFIG189)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / "scratch143-loop189"
    rows: list[dict] = []
    for case in suite["cases"]:
        rec = R143.run_case(case, scratch / case["id"], markers)
        rows.append(rec)
    (ART / "redteam143-loop189.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    base = json.loads(
        (ART138G / "redteam143-loop138g.json").read_text(encoding="utf-8"))
    moves, _ = _moves(rows, base["rows"])
    rep = {"suite": "rt143",
           "counter": dict(Counter(r["verdict"] for r in rows)),
           "moves_vs_138g": moves}
    print(f"rt143: {rep['counter']} moves={len(moves)}", flush=True)
    for m in moves:
        print(f"  MOVE {m}", flush=True)
    (ART / "redteam143-compare.json").write_text(
        json.dumps(rep, indent=1, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    return rep


def run_sessions() -> dict:
    import shutil as _sh
    import fable_session152_run as S152R  # noqa: E402 (judge, read-only)
    sessions_out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = ART / "work-sessions-loop189" / s["id"]
        if root.exists():
            _sh.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(L189.DEFAULT_CONFIG189)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L189.Loop189Daemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    (ART / "sessions152-loop189.json").write_text(
        json.dumps(sessions_out, indent=1, ensure_ascii=False),
        encoding="utf-8")
    out138g = json.loads(
        (ART138G / "sessions152-loop138g.json").read_text(encoding="utf-8"))
    moves, new_wrong, new_writes = [], 0, []
    for sid, turns in sessions_out.items():
        for t, b in zip(turns, out138g.get(sid, [])):
            if t["verdict"] != b["verdict"] or str(t["reply"]).strip() != str(
                    b["reply"]).strip():
                moves.append({"session": sid, "n": t["n"],
                              "loop138g": b["verdict"],
                              "loop189": t["verdict"]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
            bw = (b.get("fact_writes") or b.get("writes") or [])
            tw = (t.get("fact_writes") or t.get("writes") or [])
            if tw and tw != bw:
                new_writes.append({"session": sid, "n": t["n"]})
    rep = {"suite": "sessions", "moves_vs_138g": moves,
           "new_wrong_vs_138g": new_wrong, "new_writes": new_writes}
    print(f"sessions: moves={len(moves)} new_wrong={new_wrong} "
          f"new_writes={len(new_writes)}", flush=True)
    (ART / "sessions152-compare.json").write_text(
        json.dumps(rep, indent=1, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    return rep


def run_bench(only: str = "all") -> dict:
    import fable_bench121_run as B  # noqa: E402 (scorer, read-only)
    B.Loop121Daemon = L189.Loop189Daemon
    cfg = copy.deepcopy(L189.DEFAULT_CONFIG189)
    cfg["sleep_threshold"] = 100000
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
    import shutil as _sh
    workroot = ART / "scratch-bench121-loop189"
    if workroot.exists():
        _sh.rmtree(workroot)
    workroot.mkdir(parents=True)
    summary: dict = {"agent": "loop189", "splits": {}}
    for stag, path, sealed_name in splits:
        items = [json.loads(line) for line in
                 Path(str(path)).read_text(encoding="utf-8").splitlines()
                 if line.strip()]
        rows = [B.run_item(it, workroot / stag, copy.deepcopy(cfg))
                for it in items]
        (ART / f"fable_bench121_loop189_{stag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
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
                              "loop189": r["verdict"]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
        summary["splits"][stag] = {
            "n": len(rows),
            "cell": {"correct": sum(1 for r in rows
                                    if r["verdict"] == "correct"),
                     "abstain": sum(1 for r in rows
                                    if r["verdict"] == "abstain"),
                     "wrong": sum(1 for r in rows
                                   if r["verdict"] == "wrong")},
            "moves_vs_138g": moves, "new_wrong_vs_138g": new_wrong}
        print(f"{stag}: {summary['splits'][stag]['cell']} "
              f"new_wrong={new_wrong} moves={len(moves)}", flush=True)
    (ART / "fable_bench121_summary_loop189.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    return summary


def run_marks123() -> dict:
    import subprocess as _sp
    cfg_src = ART / "loop189-config.json"
    out = ART / "marks189"
    cmd = (f"export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; "
           f"uv run --offline --no-project --python 3.12 "
           f"--with torch --with numpy python -B "
           f"scripts/fable_marks123_all.py --agent "
           f"scripts/fable_loop189_agent.py --config {cfg_src} "
           f"--out {out}")
    t0 = time.time()
    r = _sp.run(cmd, shell=True, capture_output=True, text=True,
                cwd=str(ROOT), timeout=1500)
    secs = round(time.time() - t0, 1)
    (ART / "marks123-loop189-stdout.txt").write_text(
        r.stdout[-20000:] + "\n---STDERR---\n" + r.stderr[-8000:],
        encoding="utf-8")
    rep = {"suite": "marks123", "rc": r.returncode, "seconds": secs,
           "out": str(out)}
    print(f"marks123: rc={r.returncode} {secs}s", flush=True)
    # per-case compare of the summary + suite reports vs sealed marks138g
    base_dir = ART138G / "marks138g"
    moves: list = []
    for name in ("fable_marks123_summary.json", "p2-report.json",
                 "p3-report.json", "p4-report.json", "rt110-report.json",
                 "q1-report.json", "rt81-report.json"):
        nb, ob = base_dir / name, out / name
        if nb.exists() and ob.exists():
            try:
                bj = json.loads(nb.read_text(encoding="utf-8"))
                oj = json.loads(ob.read_text(encoding="utf-8"))
                if bj != oj:
                    moves.append({"report": name, "note": "differs"})
            except Exception as exc:  # noqa: BLE001
                moves.append({"report": name, "note": repr(exc)[:120]})
        else:
            moves.append({"report": name, "note": "missing-side"})
    rep["report_diffs_vs_138g"] = moves
    for m in moves:
        print(f"  MARKSDIFF {m}", flush=True)
    (ART / "marks123-compare.json").write_text(
        json.dumps(rep, indent=1, sort_keys=True), encoding="utf-8")
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 189 R1/R2 driver")
    ap.add_argument("--only", default="all",
                    help="comma list of r1,junk,rt143,sessions,bench,"
                         "marks123 or all")
    ap.add_argument("--bench-only", default="all")
    args = ap.parse_args(argv)
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc = 0
    want = args.only.split(",")
    if "all" in want or "r1" in want:
        rep = run_r1()
        if rep["ok"] != rep["n"]:
            rc = 1
    if "all" in want or "junk" in want:
        rep = run_junk()
        for k, v in rep.items():
            mv = v.get("moves_vs_138g", [])
            if mv or v.get("new_wrong_vs_138g", 0):
                print(f"  JUNKMOVE {k}: {mv}", flush=True)
                rc = 1
    if "all" in want or "rt143" in want:
        rep = run_rt143()
        if rep["moves_vs_138g"]:
            rc = 1
    if "all" in want or "sessions" in want:
        rep = run_sessions()
        if rep["moves_vs_138g"] or rep["new_writes"]:
            rc = 1
    if "all" in want or "bench" in want:
        rep = run_bench(args.bench_only)
        for stag, cell in rep["splits"].items():
            if cell["moves_vs_138g"] or cell["new_wrong_vs_138g"]:
                rc = 1
    if "all" in want or "marks123" in want:
        rep = run_marks123()
        if rep["rc"] != 0 or rep["report_diffs_vs_138g"]:
            rc = 1
    print(f"fix189 done in {round(time.time() - t0, 1)}s rc={rc}",
          flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
