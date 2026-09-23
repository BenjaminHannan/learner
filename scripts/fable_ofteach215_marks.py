#!/usr/bin/env python3
"""Experiment 215 -- marks driver: P1/P2 panels + frozen suites + bench + reversal210 loop arm (Muse).

Panels:
  P1 cases215-p1.json (40 teach+ask sets): teach "X is the R of Y.", then
  "Who/What is Y's R?" and "Who/What is the R of Y?" must answer X; the
  stored taught triple must be exactly (Y, R, X); 0 junk "R of" relations.
  P2 cases215-p2.json (25 traps): reply AND stored FACT/RELATION/ENTITY
  events byte-identical between loop215 and loop138i.

Frozen (loop215 ONLY, diffed vs sealed loop138i rows, read-only):
  redteam136, redteam143, sessions152, bench-v3 4x200.
Reversal: loop215 arm over the 70 exp-210 items (same scorer/checker as
scripts/fable_reversal210_run.py); bar: junk "R of" saves 26 -> 0, every
item reported.

Run (Mac CPU, offline; ONE suite at a time):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_ofteach215_marks.py --only <p1|p2|rt136|rt143|sessions|bench|reversal> --out <dir>
Pilot use: --out <scratch dir>. Registered use (only AFTER the seal):
--out artifacts/fable-ofteach215-20260922/<suite>.
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

import fable_loop138i_agent as L138  # noqa: E402 (base arm, read-only)
import fable_loop215_agent as L215  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-ofteach215-20260922"
ART138I = ROOT / "artifacts" / "fable-agent138i-20260922"

WRONGish = ("WRONG-WRITE", "WRONG-ANSWER", "WRONG", "WRONG-REPLY", "BUG",
            "wrong")


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False),
                    encoding="utf-8")


def fresh215(root: Path):
    cfg = copy.deepcopy(L215.DEFAULT_CONFIG215)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L215.Loop215Daemon(root, cfg=cfg, idle_seconds=3600.0)


def fresh138(root: Path):
    cfg = copy.deepcopy(L138.DEFAULT_CONFIG138I)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L138.Loop138iDaemon(root, cfg=cfg, idle_seconds=3600.0)


def daemon_turn(daemon, text: str) -> str:
    n = daemon_turn.n = getattr(daemon_turn, "n", 0) + 1
    name = f"t{n:04d}.txt"
    (daemon.root / "inbox" / name).write_text(str(text) + "\n",
                                             encoding="utf-8")
    daemon.process_file(daemon.root / "inbox" / name)
    return (daemon.root / "outbox" / name).read_text(
        encoding="utf-8").strip()


def stored_events(daemon) -> dict:
    ev = daemon.root / "notebook" / "events.jsonl"
    facts, rels, ents = [], [], []
    if ev.exists():
        names: dict[str, str] = {}
        for line in ev.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("kind") == "ENTITY":
                names[str(d.get("entity_id"))] = str(d.get("name", ""))
                ents.append([str(d.get("entity_id")),
                             str(d.get("name", ""))])
            elif d.get("kind") == "RELATION":
                rels.append(str(d.get("relation", "")))
            elif d.get("kind") == "FACT":
                val = d.get("value")
                obj = ""
                if isinstance(val, dict):
                    obj = str(val.get("entity_id") or val.get("entity")
                              or val.get("value") or val.get("name")
                              or val.get("literal") or "")
                    if obj in names:
                        obj = names[obj]
                else:
                    obj = str(val or "")
                facts.append([names.get(str(d.get("subject")), "?"),
                              str(d.get("relation", "")),
                              obj if obj not in names else names[obj],
                              str(d.get("source", ""))])
    return {"facts": facts, "relations": rels, "entities": ents}


def run_p1(out: Path) -> dict:
    t0 = time.time()
    cases = json.loads((ART / "cases215-p1.json").read_text(
        encoding="utf-8"))["cases"]
    workroot = Path(tempfile.mkdtemp(prefix="o215-p1-"))
    rows = []
    for c in cases:
        root = workroot / c["id"]
        root.mkdir(parents=True)
        daemon = fresh215(root)
        r_teach = daemon_turn(daemon, c["teach"])
        r_poss = daemon_turn(daemon, c["ask_poss"])
        r_of = daemon_turn(daemon, c["ask_of"])
        st = stored_events(daemon)
        taught = [f for f in st["facts"] if f[3] == "taught"]
        triple_ok = ([c["y"], c["rel"], c["x"]] in
                     [[f[0], f[1], f[2]] for f in taught])
        junk = [r for r in st["relations"]
                if "_of" in r or " of" in r or r.endswith("_of")]
        ans_poss = c["x"] in r_poss
        ans_of = c["x"] in r_of
        ok = (r_teach.startswith("Saved:") and ans_poss and ans_of
              and triple_ok and not junk)
        rows.append({"id": c["id"], "ok": ok, "teach_reply": r_teach,
                     "poss_reply": r_poss, "of_reply": r_of,
                     "triple_ok": triple_ok, "taught": taught,
                     "junk_relations": junk})
        print(f"  {c['id']} {'OK' if ok else 'FAIL'} teach={r_teach[:60]!r} "
              f"poss={r_poss[:60]!r} of={r_of[:60]!r}", flush=True)
    shutil.rmtree(workroot, ignore_errors=True)
    rep = {"suite": "p1", "n": len(rows),
           "ok": sum(1 for r in rows if r["ok"]),
           "fail": [r["id"] for r in rows if not r["ok"]],
           "junk_total": sum(len(r["junk_relations"]) for r in rows),
           "seconds": round(time.time() - t0, 1)}
    write_json(out / "p1-rows.json", rows)
    write_json(out / "p1-report.json", rep)
    print(f"p1: {rep['ok']}/{rep['n']} ok junk={rep['junk_total']} "
          f"fail={rep['fail']}", flush=True)
    return rep


def run_p2(out: Path) -> dict:
    t0 = time.time()
    traps = json.loads((ART / "cases215-p2.json").read_text(
        encoding="utf-8"))["traps"]
    workroot = Path(tempfile.mkdtemp(prefix="o215-p2-"))
    rows = []
    for t in traps:
        r215_dir = workroot / ("215-" + t["id"])
        r138_dir = workroot / ("138-" + t["id"])
        r215_dir.mkdir(parents=True)
        r138_dir.mkdir(parents=True)
        d215, d138 = fresh215(r215_dir), fresh138(r138_dir)
        reply215 = daemon_turn(d215, t["text"])
        reply138 = daemon_turn(d138, t["text"])
        st215, st138 = stored_events(d215), stored_events(d138)
        same = (reply215 == reply138 and st215 == st138)
        rows.append({"id": t["id"], "same": same, "text": t["text"],
                     "reply215": reply215, "reply138": reply138,
                     "stored215": st215, "stored138": st138})
        print(f"  {t['id']} {'SAME' if same else 'DIFF'}", flush=True)
        if not same:
            print(f"    215: {reply215[:120]!r}", flush=True)
            print(f"    138: {reply138[:120]!r}", flush=True)
    shutil.rmtree(workroot, ignore_errors=True)
    rep = {"suite": "p2", "n": len(rows),
           "same": sum(1 for r in rows if r["same"]),
           "diff": [r["id"] for r in rows if not r["same"]],
           "seconds": round(time.time() - t0, 1)}
    write_json(out / "p2-rows.json", rows)
    write_json(out / "p2-report.json", rep)
    print(f"p2: {rep['same']}/{rep['n']} identical diff={rep['diff']}",
          flush=True)
    return rep


def run_rt136(out: Path) -> dict:
    import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
    t0 = time.time()
    R136.new_daemon139b = fresh215  # type: ignore[method-assign]
    cases = json.loads((ROOT / "artifacts" / "fable-redteam136-20260922"
                        / "cases136.json").read_text(encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = Path(tempfile.mkdtemp(prefix="o215-rt136-"))
    rows = [R136.run_case139b(row, workroot) for row in cases]
    write_json(out / "redteam136-loop215.json", rows)
    base = [json.loads(line) for line in
            (ART138I / "g2frozen" / "redteam136-loop138i.json").read_text(
                encoding="utf-8").splitlines() if line.strip()]
    b_by_id = {r["id"]: r for r in base}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            moves.append({"id": r["id"], "what": "missing-base"})
            continue
        if (r["verdict"] != b["verdict"]
                or str(r.get("reply", "")).strip()
                != str(b.get("reply", "")).strip()
                or r.get("stored") != b.get("stored")):
            moves.append({"id": r["id"], "loop138i": b["verdict"],
                          "loop215": r["verdict"],
                          "reply138i": str(b.get("reply", ""))[:140],
                          "reply215": str(r.get("reply", ""))[:140],
                          "stored138i": b.get("stored"),
                          "stored215": r.get("stored")})
            if b["verdict"] not in WRONGish and r["verdict"] in WRONGish:
                new_wrong += 1
    shutil.rmtree(workroot, ignore_errors=True)
    rep = {"suite": "redteam136", "n": len(rows),
           "counter": dict(Counter(r["verdict"] for r in rows)),
           "moves": moves, "new_wrong": new_wrong,
           "seconds": round(time.time() - t0, 1)}
    write_json(out / "rt136-report.json", rep)
    print(f"rt136: {rep['counter']} moves={len(moves)} "
          f"new_wrong={new_wrong}", flush=True)
    for m in moves[:20]:
        print(f"  MOVE {m}", flush=True)
    return rep


def run_rt143(out: Path) -> dict:
    import fable_redteam143_run as R143  # noqa: E402 (judge, read-only)
    t0 = time.time()
    R143.Loop132Daemon = L215.Loop215Daemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L215.DEFAULT_CONFIG215)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = Path(tempfile.mkdtemp(prefix="o215-rt143-"))
    rows = [R143.run_case(c, scratch / c["id"], markers)
            for c in suite["cases"]]
    write_json(out / "redteam143-loop215.json", {"rows": rows})
    base = json.loads((ART138I / "g2frozen" / "redteam143-loop138i.json")
                      .read_text(encoding="utf-8"))
    b_by_id = {r["id"]: r for r in base["rows"]}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            moves.append({"id": r["id"], "what": "missing-base"})
            continue
        if (r["verdict"] != b["verdict"]
                or str(r.get("reply", "")).strip()
                != str(b.get("reply", "")).strip()):
            moves.append({"id": r["id"], "loop138i": b["verdict"],
                          "loop215": r["verdict"],
                          "reply138i": str(b.get("reply", ""))[:140],
                          "reply215": str(r.get("reply", ""))[:140]})
            if b["verdict"] not in WRONGish and r["verdict"] in WRONGish:
                new_wrong += 1
    shutil.rmtree(scratch, ignore_errors=True)
    rep = {"suite": "redteam143", "n": len(rows),
           "counter": dict(Counter(r["verdict"] for r in rows)),
           "moves": moves, "new_wrong": new_wrong,
           "seconds": round(time.time() - t0, 1)}
    write_json(out / "rt143-report.json", rep)
    print(f"rt143: {rep['counter']} moves={len(moves)} "
          f"new_wrong={new_wrong}", flush=True)
    for m in moves[:20]:
        print(f"  MOVE {m}", flush=True)
    return rep


def run_sessions(out: Path) -> dict:
    import fable_session152_run as S152R  # noqa: E402 (judge, read-only)
    t0 = time.time()
    sessions_out: dict = {}
    workroot = Path(tempfile.mkdtemp(prefix="o215-s152-"))
    for s in S152R.S152.SESSIONS:
        root = workroot / s["id"]
        root.mkdir(parents=True)
        daemon = fresh215(root)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    write_json(out / "sessions152-loop215.json", sessions_out)
    out138i = json.loads((ART138I / "g2frozen" / "sessions152-loop138i.json")
                         .read_text(encoding="utf-8"))
    moves, new_wrong, new_writes = [], 0, []
    counts138i: Counter = Counter()
    counts215: Counter = Counter()
    for sid, turns in sessions_out.items():
        for t, b in zip(turns, out138i.get(sid, [])):
            counts138i[b["verdict"]] += 1
            counts215[t["verdict"]] += 1
            if (t["verdict"] != b["verdict"]
                    or str(t.get("reply", "")).strip()
                    != str(b.get("reply", "")).strip()):
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop138i": b["verdict"],
                              "loop215": t["verdict"],
                              "reply138i": str(b["reply"]).strip()[:120],
                              "reply215": str(t["reply"]).strip()[:120],
                              "why": t["why"][:160]})
                if (t["verdict"] == "WRONG"
                        and b["verdict"] != "WRONG"):
                    new_wrong += 1
            bw = (b.get("fact_writes") or b.get("writes") or [])
            tw = (t.get("fact_writes") or t.get("writes") or [])
            if tw and tw != bw:
                new_writes.append({"session": sid, "n": t["n"],
                                   "loop138i_writes": bw,
                                   "loop215_writes": tw})
    shutil.rmtree(workroot, ignore_errors=True)
    rep = {"suite": "sessions", "loop138i": dict(counts138i),
           "loop215": dict(counts215), "moves": moves,
           "new_wrong": new_wrong, "new_writes": new_writes,
           "seconds": round(time.time() - t0, 1)}
    write_json(out / "sessions-report.json", rep)
    print(f"sessions: {dict(counts215)} moves={len(moves)} "
          f"new_wrong={new_wrong} new_writes={len(new_writes)}", flush=True)
    for m in moves[:20]:
        print(f"  MOVE {m}", flush=True)
    for w in new_writes[:20]:
        print(f"  WRITE {w}", flush=True)
    return rep


def run_bench(out: Path, only: str = "all") -> dict:
    import fable_bench121_run as B  # noqa: E402 (scorer, read-only)
    import fable_fix172b_benchv3 as V3  # noqa: E402 (v3 driver, read-only)
    t0 = time.time()
    splits = (
        ("new_121_4hop", B.DATA_NEW,
         "fable_benchv3_loop138i_new_121_4hop_rows.jsonl"),
        ("old_s2fresh_4hop", B.DATA_OLD,
         "fable_benchv3_loop138i_old_s2fresh_4hop_rows.jsonl"),
        ("edit200", str(ROOT / "data" / "open" / "bench65"
                        / "fable_edit_200.jsonl"),
         "fable_benchv3_loop138i_edit200_rows.jsonl"),
        ("bench132_4hop", str(ROOT / "data" / "open" / "bench132"
                              / "fable_edit132_4hop.jsonl"),
         "fable_benchv3_loop138i_bench132_4hop_rows.jsonl"),
    )
    if only != "all":
        splits = [s for s in splits if s[0] in only.split(",")]
    workroot = Path(tempfile.mkdtemp(prefix="o215-bench-"))
    summary: dict = {"seconds": 0.0, "arm": "loop215", "proto": "v3",
                     "splits": {}}
    for stag, path, sealed_name in splits:
        items = [json.loads(line) for line in
                 Path(str(path)).read_text(
                     encoding="utf-8").splitlines() if line.strip()]
        cfg = copy.deepcopy(L215.DEFAULT_CONFIG215)
        cfg["sleep_threshold"] = 100000
        rows = [V3.run_item_v3(it, workroot / stag, copy.deepcopy(cfg),
                               L215.Loop215Daemon, "v3") for it in items]
        (out / f"fable_benchv3_loop215_{stag}_rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                       for r in rows) + "\n", encoding="utf-8")
        cell = {"n": len(rows),
                "correct": sum(1 for r in rows if r["verdict"] == "correct"),
                "abstain": sum(1 for r in rows if r["verdict"] == "abstain"),
                "wrong": sum(1 for r in rows if r["verdict"] == "wrong"),
                "confirms": sum(r["confirms"] for r in rows)}
        base_rows_l = [json.loads(line) for line in
                       (ART138I / "g1bench" / sealed_name).read_text(
                           encoding="utf-8").splitlines() if line.strip()]
        s_by_id = {r["id"]: r for r in base_rows_l}
        moves, new_wrong = [], 0
        for r in rows:
            s = s_by_id.get(r["id"])
            if s is None:
                continue
            if r["verdict"] != s["verdict"]:
                moves.append({"id": r["id"], "loop138i": s["verdict"],
                              "loop215": r["verdict"],
                              "reply138i": str(s.get("reply", ""))[:120],
                              "reply215": str(r.get("reply", ""))[:120]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
        summary["splits"][stag] = {"loop215": cell,
                                   "moves_vs_138i": moves,
                                   "new_wrong_vs_138i": new_wrong}
        print(f"v3 {stag}: loop215 {cell} new_wrong={new_wrong} "
              f"moves={len(moves)}", flush=True)
        for m in moves[:16]:
            print(f"  MOVE {m}", flush=True)
    shutil.rmtree(workroot, ignore_errors=True)
    summary["seconds"] = round(time.time() - t0, 1)
    write_json(out / "bench-report.json", summary)
    return summary


def run_reversal(out: Path) -> dict:
    import fable_reversal210_run as R210  # noqa: E402 (scorer, read-only)
    t0 = time.time()
    items = [json.loads(l) for l in
             (ROOT / "data" / "open" / "reversal210"
              / "fable_reversal210.jsonl").read_text(
                 encoding="utf-8").splitlines() if l.strip()]
    workroot = Path(tempfile.mkdtemp(prefix="o215-rev-"))
    rows = []
    for it in items:
        ddir = workroot / "loop215" / it["id"]
        if ddir.exists():
            shutil.rmtree(ddir)
        ddir.mkdir(parents=True)
        daemon = L215.Loop215Daemon(
            str(ddir), cfg=dict(copy.deepcopy(L215.DEFAULT_CONFIG215)))
        teach_replies: list[str] = []
        n_reject = 0
        n = 0
        for t in it["taught"]:
            n += 1
            name = f"t{n:03d}.txt"
            (ddir / "inbox" / name).write_text(
                str(t["sentence_en"]) + "\n", encoding="utf-8")
            daemon.process_file(ddir / "inbox" / name)
            reply = (ddir / "outbox" / name).read_text(
                encoding="utf-8").strip()
            teach_replies.append(reply)
            n_reject += 0 if R210.teach_accepted(reply) else 1
        n += 1
        qname = f"t{n:03d}.txt"
        (ddir / "inbox" / qname).write_text(str(it["question"]) + "\n",
                                           encoding="utf-8")
        daemon.process_file(ddir / "inbox" / qname)
        reply = (ddir / "outbox" / qname).read_text(
            encoding="utf-8").strip()
        golds = [str(g) for g in list(it.get("gold", []))
                 + list(it.get("gold_aliases", []))]
        verdict, exact, contains = R210.classify_v2(reply, golds)
        triples = R210.stored_triples(ddir)
        taught = it["taught"][0]
        inv = [t for t in triples
               if R210.norm(t[0]) == R210.norm(str(taught["object"]))
               and R210.norm(t[2]) == R210.norm(str(taught["subject"]))]
        junk = [t for t in triples
                if "_of" in str(t[1]) or " of" in str(t[1])]
        rows.append({"id": it["id"], "type": str(it.get("type", "?")),
                     "taught_dir": str(it.get("taught_dir", "?")),
                     "asked": str(it.get("asked", "?")),
                     "verdict": verdict, "exact": bool(exact),
                     "contains_gold": bool(contains),
                     "extracted": R210.extract_answer(reply),
                     "n_teach": len(teach_replies),
                     "n_teach_reject": n_reject,
                     "teach_replies": teach_replies,
                     "stored_triples": triples,
                     "n_inverse_stored": len(inv),
                     "junk_of": junk,
                     "reply": reply})
    (out / "fable_reversal210_loop215_rows.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in rows) + "\n", encoding="utf-8")
    table = R210.summarize(rows)
    rep = {"suite": "reversal210-loop215", "n": len(rows), "table": table,
           "teach_rejects": sum(r["n_teach_reject"] for r in rows),
           "items_with_inverse_stored": sum(
               1 for r in rows if r["n_inverse_stored"]),
           "items_with_junk_of": sum(1 for r in rows if r["junk_of"]),
           "coverage_all_reported": (
               sorted(r["id"] for r in rows)
               == sorted(it["id"] for it in items)),
           "seconds": round(time.time() - t0, 1)}
    shutil.rmtree(workroot, ignore_errors=True)
    write_json(out / "reversal-report.json", rep)
    print(json.dumps(rep, indent=1)[:2000], flush=True)
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 215 marks")
    ap.add_argument("--only", default="p1",
                    choices=["p1", "p2", "rt136", "rt143", "sessions",
                             "bench", "reversal"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--bench-only", default="all")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fn = {"p1": run_p1, "p2": run_p2, "rt136": run_rt136,
          "rt143": run_rt143, "sessions": run_sessions,
          "reversal": run_reversal}[args.only] \
        if args.only != "bench" else lambda o: run_bench(o, args.bench_only)
    rep = fn(out)
    print(json.dumps({args.only: "done",
                      "seconds": rep.get("seconds")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
