#!/usr/bin/env python3
"""Exp 189b W1/W2/W3 driver -- widened repeat grammar + frozen regression.

W1 (sealed `cases189b.json`, >= 36 turns, fresh in-process loops):
  base loop189 and loop189b stepped in lockstep on the same turns.
  - kind=noprev (repeat with no previous reply): 189b must reply the one
    fixed line NO_PREV189B, events unchanged.
  - kind=repeat (>= 18 new phrasings): 189b must reply its own previous
    NON-REPEAT reply byte-identical, events unchanged (triples + facts +
    events.jsonl lines identical before/after: a repeated "Saved:" never
    writes twice).
  - kind=trap/base (>= 12 Say/repeat traps + teaches/asks): 189b reply
    byte-identical to loop189 reply AND stored triples identical AND
    events identical AND facts identical.
W2 (189's sealed `cases189.json`, 38 turns): loop189 vs loop189b in
  lockstep, every turn byte-identical (reply + triples + facts +
  events) -- the 8 loop189 shapes are a subset of the 189b grammar.
W3 (frozen suites with loop189b vs SEALED loop138g rows AND loop189
  rows): redteam136, cases150, f1, cases139b, redteam143, sessions152
  (0 moves predicted); bench121 4 splits via the base driver's scorer
  (0 new wrong predicted); marks123 via stock
  `scripts/fable_marks123_all.py` compared per-case vs sealed marks138g
  and vs marks189 after scrubbing volatile metadata (0 moves predicted).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed; heavy suites
one at a time):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix189b_sayagain.py --only w1|w2|junk|rt143|sessions|bench|marks123|all
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138g_agent as L138G  # noqa: E402 (frozen base, read-only)
import fable_loop189_agent as L189  # noqa: E402 (parent agent, read-only)
import fable_loop189b_agent as L189B  # noqa: E402 (agent under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-sayagain189b-20260922"
ART189 = ROOT / "artifacts" / "fable-sayagain189-20260922"
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


def _lockstep(cases: list[dict], tag: str) -> dict:
    out_rows: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="w-base-") as tb, \
            tempfile.TemporaryDirectory(prefix="w-189b-") as t9b:
        cb = copy.deepcopy(L189.DEFAULT_CONFIG189)
        cb["state_dir"] = tb
        cb["sleep_threshold"] = 100000
        base = L189.build_agent189(cb)
        c9 = copy.deepcopy(L189B.DEFAULT_CONFIG189B)
        c9["state_dir"] = t9b
        c9["sleep_threshold"] = 100000
        agent = L189B.build_agent189b(c9)
        prev_nonrepeat: str | None = None
        for row in cases:
            turn, kind = row["turn"], row["kind"]
            rb = " ".join(base.turn(turn)).strip()
            s9 = _snap(agent, Path(t9b))
            r9 = " ".join(agent.turn(turn)).strip()
            eb, e9 = _snap(base, Path(tb)), _snap(agent, Path(t9b))
            if kind == "noprev":
                ok = (r9 == L189B.NO_PREV189B and e9 == s9)
                # noprev: fixed line; 189b wrote nothing itself
                note = "fixed-line" if ok else f"got {r9!r}"
            elif kind == "repeat":
                want = prev_nonrepeat if prev_nonrepeat is not None \
                    else L189B.NO_PREV189B
                # echo of 189b's own previous non-repeat reply, 0 writes
                ok = (r9 == want and e9 == s9)
                note = "verbatim-echo" if ok else (
                    f"want {want!r} got {r9!r} wrote={e9 != s9}")
            else:  # trap / base turns: byte-identical to loop189
                ok = (r9 == rb and e9["triples"] == eb["triples"]
                      and e9["events"] == eb["events"]
                      and e9["facts"] == eb["facts"])
                note = "identical" if ok else (
                    f"base {rb!r} vs189b {r9!r} "
                    f"triples={e9['triples'] != eb['triples']} "
                    f"facts={e9['facts'] != eb['facts']} "
                    f"events={e9['events'] != eb['events']}")
            if kind not in ("noprev", "repeat"):
                prev_nonrepeat = r9
            out_rows.append({"id": row["id"], "kind": kind, "turn": turn,
                             "reply189b": r9, "reply189": rb,
                             "verdict": "OK" if ok else "FAIL",
                             "note": note})
    (ART / f"{tag}-sayagain189b.json").write_text(
        json.dumps(out_rows, indent=1, ensure_ascii=False), encoding="utf-8")
    by_kind: dict = {}
    for r in out_rows:
        by_kind.setdefault(r["kind"], [0, 0])
        by_kind[r["kind"]][1] += 1
        by_kind[r["kind"]][0] += (r["verdict"] == "OK")
    rep = {"suite": tag, "n": len(out_rows),
           "ok": sum(1 for r in out_rows if r["verdict"] == "OK"),
           "by_kind": {k: f"{a}/{b}" for k, (a, b) in by_kind.items()},
           "fails": [r for r in out_rows if r["verdict"] != "OK"]}
    print(f"{tag}: {rep['ok']}/{rep['n']} {rep['by_kind']}", flush=True)
    for r in rep["fails"]:
        print(f"  {tag}FAIL {r['id']} {r['turn']!r}: {r['note']}",
              flush=True)
    return rep


def run_w1() -> dict:
    cases = json.loads((ART / "cases189b.json").read_text(encoding="utf-8"))
    assert len(cases) >= 36, f"sealed W1 case file has {len(cases)} < 36"
    nrep = sum(1 for c in cases if c["kind"] == "repeat")
    ntra = sum(1 for c in cases if c["kind"] == "trap")
    assert nrep >= 18, f"only {nrep} repeat turns < 18"
    assert ntra >= 12, f"only {ntra} trap turns < 12"
    return _lockstep(cases, "w1")


def run_w2() -> dict:
    cases = json.loads((ART189 / "cases189.json").read_text(encoding="utf-8"))
    assert len(cases) == 38, f"189 R1 case file has {len(cases)} != 38"
    rows = _lockstep(
        [{"id": r["id"], "kind": ("trap" if r["kind"] in ("trap", "base")
                                  else "w2lock"), "turn": r["turn"]}
         for r in cases], "w2raw")
    # W2 bar: every turn byte-identical to loop189 (reply+store+events).
    # _lockstep marks non-trap/base kinds by echo rules; re-score here
    # strictly: reply189b == reply189 AND snapshots equal is already what
    # trap/base rows check; for repeat/noprev rows of cases189 the old
    # shapes are inside the 189b grammar so both echo identically --
    # check the raw rows directly.
    bad = [r for r in rows["fails"]]
    rep = {"suite": "w2", "n": rows["n"],
           "ok": rows["n"] - len(bad),
           "by_kind": rows["by_kind"],
           "fails": bad}
    print(f"W2 (189 R1 rerun, 189b vs 189): "
          f"{rep['ok']}/{rep['n']}", flush=True)
    return rep


def build189b(extra: dict) -> object:
    cfg = copy.deepcopy(L189B.DEFAULT_CONFIG189B)
    cfg.update(extra)
    return L189B.build_agent189b(cfg)


def new_daemon189b(root: Path):
    cfg = copy.deepcopy(L189B.DEFAULT_CONFIG189B)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L189B.Loop189bDaemon(root, cfg=cfg, idle_seconds=3600.0)


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False,
                                        sort_keys=True) for r in rows)
                    + "\n", encoding="utf-8")


def _sealed_rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in
            path.read_text(encoding="utf-8").splitlines() if l.strip()]


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
            moves.append({"id": r["id"], "base": b.get("verdict"),
                          "loop189b": r.get("verdict"),
                          "reply_base": str(b.get("reply", ""))[:120],
                          "reply189b": str(r.get("reply", ""))[:120]})
            if r.get("verdict") in ("WRONG-WRITE", "WRONG-ANSWER",
                                    "WRONG", "WRONG-REPLY"):
                new_wrong += 1
    return moves, new_wrong


def run_junk() -> dict:
    import fable_fix139b_probe as P139b  # noqa: E402 (judge, read-only)
    import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
    import fable_fix150_probe as P150  # noqa: E402 (judge, read-only)
    out: dict = {}
    ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"
    ART150 = ROOT / "artifacts" / "fable-fix150-20260922"
    ART139B = ROOT / "artifacts" / "fable-fix139b-20260922"
    ART144 = ROOT / "artifacts" / "fable-fix144-20260922"
    # redteam136
    R136.new_daemon139b = new_daemon189b  # type: ignore[method-assign]
    cases = json.loads((ART136 / "cases136.json").read_text(
        encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = ART / "work-rt136"
    workroot.mkdir(parents=True, exist_ok=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    _write_rows(ART / "redteam136-loop189b.json", rows)
    for refname, refpath in (
            ("138g", ART138G / "redteam136-loop138g.json"),
            ("189", ART189 / "redteam136-loop189.json")):
        moves, new_wrong = _moves(rows, _sealed_rows(refpath))
        out[f"redteam136_vs_{refname}"] = {
            "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves": moves, "new_wrong": new_wrong}
        print(f"junk redteam136 vs {refname}: n={len(rows)} "
              f"{out[f'redteam136_vs_{refname}']['counter']} "
              f"moves={len(moves)} new_wrong={new_wrong}", flush=True)
    # cases150
    cases150 = json.loads((ART150 / "cases150.json").read_text(
        encoding="utf-8"))
    rows150 = [P150.run_case(row, build189b) for row in cases150]
    _write_rows(ART / "probe150-loop189b.json", rows150)
    for refname, refpath in (
            ("138g", ART138G / "probe150-loop138g.json"),
            ("189", ART189 / "probe150-loop189.json")):
        base150 = {r["id"]: r for r in _sealed_rows(refpath)}
        m150 = [{"id": r["id"]} for r in rows150 if r["id"] in base150 and (
            r["verdict"] != base150[r["id"]]["verdict"]
            or r["reply"] != base150[r["id"]]["reply"])]
        out[f"cases150_vs_{refname}"] = {"n": len(rows150), "moves": m150}
        print(f"junk cases150 vs {refname}: n={len(rows150)} "
              f"moves={len(m150)}", flush=True)
    # f1
    casesf1 = json.loads((ART144 / "f1-cases.json").read_text(
        encoding="utf-8"))["cases"]
    rowsf1 = []
    for row in casesf1:
        t0 = time.time()
        with tempfile.TemporaryDirectory(prefix=row["id"] + "_") as tmp:
            try:
                loop = build189b({"state_dir": tmp,
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
    _write_rows(ART / "f1-loop189b.json", rowsf1)
    for refname, refpath in (("138g", ART138G / "f1-loop138g.json"),
                             ("189", ART189 / "f1-loop189.json")):
        b1 = {r["id"]: r for r in _sealed_rows(refpath)}
        m1 = [{"id": r["id"]} for r in rowsf1 if r["id"] in b1 and
              b1[r["id"]]["verdict"] != r["verdict"]]
        out[f"f1_vs_{refname}"] = {"n": len(rowsf1), "moves": m1}
        print(f"junk f1 vs {refname}: n={len(rowsf1)} moves={len(m1)}",
              flush=True)
    # cases139b
    casesb = json.loads((ART139B / "cases139b.json").read_text(
        encoding="utf-8"))
    cases139 = json.loads(
        (ROOT / "artifacts" / "fable-fix139-20260922" / "cases139.json"
         ).read_text(encoding="utf-8"))
    if isinstance(cases139, dict):
        cases139 = cases139.get("cases", cases139)
    rowsb = [P139b.run_case(row, build189b)
             for row in list(cases139) + list(casesb)]
    _write_rows(ART / "probe139b-loop189b.json", rowsb)
    for refname, refpath in (
            ("138g", ART138G / "probe139b-loop138g.json"),
            ("189", ART189 / "probe139b-loop189.json")):
        bb = {r["id"]: r for r in _sealed_rows(refpath)}
        mb = [{"id": r["id"]} for r in rowsb if r["id"] in bb and
              (bb[r["id"]]["verdict"] != r["verdict"]
               or str(bb[r["id"]].get("reply", ""))
               != str(r.get("reply", "")))]
        out[f"cases139b_vs_{refname}"] = {"n": len(rowsb), "moves": mb}
        print(f"junk cases139b vs {refname}: n={len(rowsb)} "
              f"moves={len(mb)}", flush=True)
    (ART / "junk189b-summary.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    return out


def run_rt143() -> dict:
    import fable_redteam143_run as R143  # noqa: E402 (judge, read-only)
    R143.Loop132Daemon = L189B.Loop189bDaemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L189B.DEFAULT_CONFIG189B)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / "scratch143-loop189b"
    rows: list[dict] = []
    for case in suite["cases"]:
        rec = R143.run_case(case, scratch / case["id"], markers)
        rows.append(rec)
    (ART / "redteam143-loop189b.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    out: dict = {}
    for refname, refpath in (
            ("138g", ART138G / "redteam143-loop138g.json"),
            ("189", ART189 / "redteam143-loop189.json")):
        base = json.loads(refpath.read_text(encoding="utf-8"))
        base_rows = base["rows"] if isinstance(base, dict) else base
        moves, _ = _moves(rows, base_rows)
        out[f"vs_{refname}"] = {
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves": moves}
        print(f"rt143 vs {refname}: {out[f'vs_{refname}']['counter']} "
              f"moves={len(moves)}", flush=True)
    (ART / "redteam143-compare.json").write_text(
        json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    return out


def run_sessions() -> dict:
    import shutil as _sh
    import fable_session152_run as S152R  # noqa: E402 (judge, read-only)
    sessions_out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = ART / "work-sessions-loop189b" / s["id"]
        if root.exists():
            _sh.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(L189B.DEFAULT_CONFIG189B)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L189B.Loop189bDaemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    (ART / "sessions152-loop189b.json").write_text(
        json.dumps(sessions_out, indent=1, ensure_ascii=False),
        encoding="utf-8")
    out: dict = {}
    for refname, refpath in (
            ("138g", ART138G / "sessions152-loop138g.json"),
            ("189", ART189 / "sessions152-loop189.json")):
        out138 = json.loads(refpath.read_text(encoding="utf-8"))
        moves, new_wrong, new_writes = [], 0, []
        for sid, turns in sessions_out.items():
            for t, b in zip(turns, out138.get(sid, [])):
                if t["verdict"] != b["verdict"] or str(
                        t["reply"]).strip() != str(b["reply"]).strip():
                    moves.append({"session": sid, "n": t["n"],
                                  f"{refname}": b["verdict"],
                                  "loop189b": t["verdict"]})
                    if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                        new_wrong += 1
                bw = (b.get("fact_writes") or b.get("writes") or [])
                tw = (t.get("fact_writes") or t.get("writes") or [])
                if tw and tw != bw:
                    new_writes.append({"session": sid, "n": t["n"]})
        out[f"vs_{refname}"] = {"moves": moves, "new_wrong": new_wrong,
                                "new_writes": new_writes}
        print(f"sessions vs {refname}: moves={len(moves)} "
              f"new_wrong={new_wrong} new_writes={len(new_writes)}",
              flush=True)
    (ART / "sessions152-compare.json").write_text(
        json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    return out


def run_bench(only: str = "all") -> dict:
    import fable_bench121_run as B  # noqa: E402 (scorer, read-only)
    B.Loop121Daemon = L189B.Loop189bDaemon
    cfg = copy.deepcopy(L189B.DEFAULT_CONFIG189B)
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
    workroot = ART / "scratch-bench121-loop189b"
    if workroot.exists():
        _sh.rmtree(workroot)
    workroot.mkdir(parents=True)
    summary: dict = {"agent": "loop189b", "splits": {}}
    for stag, path, sealed_name in splits:
        items = [json.loads(line) for line in
                 Path(str(path)).read_text(encoding="utf-8").splitlines()
                 if line.strip()]
        rows = [B.run_item(it, workroot / stag, copy.deepcopy(cfg))
                for it in items]
        (ART / f"fable_bench121_loop189b_{stag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        for refname, refdir, pat in (
                ("138g", ART138G, sealed_name),
                ("189", ART189,
                 f"fable_bench121_loop189_{stag}_rows.jsonl")):
            base_rows_l = [json.loads(line) for line in
                           (refdir / pat).read_text(
                               encoding="utf-8").splitlines() if line.strip()]
            s_by_id = {r["id"]: r for r in base_rows_l}
            moves, new_wrong = [], 0
            for r in rows:
                s = s_by_id.get(r["id"])
                if s is None:
                    continue
                if r["verdict"] != s["verdict"]:
                    moves.append({"id": r["id"], refname: s["verdict"],
                                  "loop189b": r["verdict"]})
                    if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                        new_wrong += 1
            summary["splits"].setdefault(stag, {})[f"vs_{refname}"] = {
                "n": len(rows),
                "cell": {"correct": sum(1 for r in rows
                                        if r["verdict"] == "correct"),
                         "abstain": sum(1 for r in rows
                                        if r["verdict"] == "abstain"),
                         "wrong": sum(1 for r in rows
                                      if r["verdict"] == "wrong")},
                "moves": moves, "new_wrong": new_wrong}
            print(f"{stag} vs {refname}: "
                  f"{summary['splits'][stag][f'vs_{refname}']['cell']} "
                  f"new_wrong={new_wrong} moves={len(moves)}", flush=True)
    (ART / "fable_bench121_summary_loop189b.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    return summary


_VOLATILE_KEYS = {"seconds", "elapsed", "wall", "duration", "timestamp",
                  "date", "run_id", "pid", "out", "stdout", "stderr"}


def _scrub(obj):
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items()
                if k not in _VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    if isinstance(obj, str):
        s = obj
        s = re.sub(r"fable_loop189b_agent\.py", "AGENT.py", s)
        s = re.sub(r"fable_loop189_agent\.py", "AGENT.py", s)
        s = re.sub(r"fable_loop138g_agent\.py", "AGENT.py", s)
        s = re.sub(r"fable-sayagain189b-20260922", "ART", s)
        s = re.sub(r"fable-sayagain189-20260922", "ART", s)
        s = re.sub(r"fable-agent138g-20260922", "ART", s)
        s = re.sub(r"marks189b", "MARKS", s)
        s = re.sub(r"marks189(?!b)", "MARKS", s)
        s = re.sub(r"marks138g", "MARKS", s)
        return s
    return obj


def _drop_statuses(obj):
    # Daemon-log-derived `statuses` are timing-volatile (log-flush race at
    # daemon kill; observed once in pilot as [] vs ['OK'] with
    # byte-identical replies and verdicts, 0/3 on rerun). Compared
    # separately, never counted as moves.
    if isinstance(obj, dict):
        return {k: _drop_statuses(v) for k, v in obj.items()
                if k != "statuses"}
    if isinstance(obj, list):
        return [_drop_statuses(v) for v in obj]
    return obj


def _norm_number(s: str) -> str:
    # Sleep-row SKIP reason names the agent file (predicted metadata diff,
    # already scrubbed to AGENT.py) and 189's sealed row carries a stray
    # trailing "(" truncation artifact; strip trailing whitespace/parens.
    return re.sub(r"[\s()]+$", "", s)


def run_marks123() -> dict:
    import subprocess as _sp
    cfg_src = ART / "loop189b-config.json"
    out = ART / "marks189b"
    cmd = (f"export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; "
           f"uv run --offline --no-project --python 3.12 "
           f"--with torch --with numpy python -B "
           f"scripts/fable_marks123_all.py --agent "
           f"scripts/fable_loop189b_agent.py --config {cfg_src} "
           f"--out {out}")
    t0 = time.time()
    r = _sp.run(cmd, shell=True, capture_output=True, text=True,
                cwd=str(ROOT), timeout=1500)
    secs = round(time.time() - t0, 1)
    (ART / "marks123-loop189b-stdout.txt").write_text(
        r.stdout[-20000:] + "\n---STDERR---\n" + r.stderr[-8000:],
        encoding="utf-8")
    rep = {"suite": "marks123", "rc": r.returncode, "seconds": secs,
           "out": str(out)}
    print(f"marks123: rc={r.returncode} {secs}s", flush=True)
    rep["compare"] = {}
    rep["volatile_statuses_only"] = {}
    for refname, refdir in (("138g", ART138G / "marks138g"),
                            ("189", ART189 / "marks189")):
        diffs: list = []
        voldiffs: list = []
        for p in sorted(refdir.glob("*-report.json")):
            ob = out / p.name
            if not ob.exists():
                diffs.append({"report": p.name, "note": "missing-side"})
                continue
            bj = _scrub(json.loads(p.read_text(encoding="utf-8")))
            oj = _scrub(json.loads(ob.read_text(encoding="utf-8")))
            if _drop_statuses(bj) != _drop_statuses(oj):
                diffs.append({"report": p.name, "note": "differs"})
            elif bj != oj:
                voldiffs.append({"report": p.name,
                                 "note": "statuses-only (volatile log)"})
        for p in ("fable_marks123_summary.json",):
            nb, ob = refdir / p, out / p
            if nb.exists() and ob.exists():
                bj = _scrub(json.loads(nb.read_text(encoding="utf-8")))
                oj = _scrub(json.loads(ob.read_text(encoding="utf-8")))
                # suite statuses must match exactly; numbers match after
                # agent-name scrub + trailing artifact strip; seconds drop
                bt = [(t.get("suite"), t.get("status"),
                       _norm_number(str(t.get("number", ""))))
                      for t in bj.get("table", [])]
                ot = [(t.get("suite"), t.get("status"),
                       _norm_number(str(t.get("number", ""))))
                      for t in oj.get("table", [])]
                if bt != ot:
                    diffs.append({"report": p, "note": "table-differs"})
                if bj.get("suites") != oj.get("suites"):
                    diffs.append({"report": p, "note": "suites-differs"})
            else:
                diffs.append({"report": p, "note": "missing-side"})
        rep["compare"][f"vs_{refname}"] = diffs
        rep["volatile_statuses_only"][f"vs_{refname}"] = voldiffs
        for m in diffs:
            print(f"  MARKSDIFF vs {refname} {m}", flush=True)
        for m in voldiffs:
            print(f"  MARKSVOLATILE vs {refname} {m}", flush=True)
    (ART / "marks123-compare.json").write_text(
        json.dumps(rep, indent=1, sort_keys=True), encoding="utf-8")
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 189b W1/W2/W3 driver")
    ap.add_argument("--only", default="all",
                    help="comma list of w1,w2,junk,rt143,sessions,bench,"
                         "marks123 or all")
    ap.add_argument("--bench-only", default="all")
    args = ap.parse_args(argv)
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc = 0
    want = args.only.split(",")
    if "all" in want or "w1" in want:
        rep = run_w1()
        if rep["ok"] != rep["n"]:
            rc = 1
    if "all" in want or "w2" in want:
        rep = run_w2()
        if rep["ok"] != rep["n"]:
            rc = 1
    if "all" in want or "junk" in want:
        rep = run_junk()
        for k, v in rep.items():
            mv = v.get("moves", [])
            if mv or v.get("new_wrong", 0):
                print(f"  JUNKMOVE {k}: {mv}", flush=True)
                rc = 1
    if "all" in want or "rt143" in want:
        rep = run_rt143()
        for k, v in rep.items():
            if v["moves"]:
                rc = 1
    if "all" in want or "sessions" in want:
        rep = run_sessions()
        for k, v in rep.items():
            if v["moves"] or v["new_writes"]:
                rc = 1
    if "all" in want or "bench" in want:
        rep = run_bench(args.bench_only)
        for stag, cell in rep["splits"].items():
            for ref, c in cell.items():
                if c["moves"] or c["new_wrong"]:
                    rc = 1
    if "all" in want or "marks123" in want:
        rep = run_marks123()
        # NOTE: the stock runner exits nonzero whenever the inherited
        # overall is FAIL (p3-l5z1, p4, rt81 FAIL exactly as sealed for
        # loop138g/loop189); the mark is per-case identity + identical
        # suite statuses, i.e. rep["compare"] only.
        for ref, diffs in rep["compare"].items():
            if diffs:
                rc = 1
    print(f"fix189b done in {round(time.time() - t0, 1)}s rc={rc}",
          flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
