#!/usr/bin/env python3
"""Exp 138j G-suites driver -- G1 bench-v3, G2 frozen suites, G3 director
pairs, G4 index identity (mirrors scripts/fable_fix138i_suites.py parts,
read-only, with the builder/daemon pointed at loop138j and compared
per-case against loop138i's sealed outputs).

G1: bench121 4 splits (v3 protocol, confirming user) vs 138i's sealed
  v3 rows: 0 new wrong vs loop138i.
G2: redteam136, redteam143, sessions152 per-case identical to loop138i
  outputs except predicted moves; 0 new WRONG / WRONG-WRITE / junk
  writes. marks123 runs via the stock CLI (see PASSMARKS) and is
  compared per-case to marks138i.
G3: nine director pairs (a)-(i), fresh loop each; replies must equal
  the frozen exact replies in cases138j-g3.json (taken from the owning
  piece's agent live pre-seal; composed pairs name their pieces).
G4: S2-fresh 1000 turns with the 170 index on vs off (off arm runs with
  FABLE138J_INDEX=off in a SUBPROCESS): every reply + facts-sha
  identical.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed; pilots use
--out outside artifacts/; heavy suites one at a time):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138j_suites.py --only <g3|g4|rt136|rt143|sessions|benchv3> \\
    --out <dir>
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138j_agent as L138J  # noqa: E402 (agent under test)
import fable_loop90_agent as L90  # noqa: E402 (triples, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-agent138j-20260922"
ART138I = ROOT / "artifacts" / "fable-agent138i-20260922"
OUTDIR = ART

WRONGish = ("WRONG-WRITE", "WRONG-ANSWER", "WRONG", "WRONG-REPLY", "BUG",
            "wrong")


def fresh138j():
    d = tempfile.mkdtemp(prefix="g-138j-")
    cfg = copy.deepcopy(L138J.DEFAULT_CONFIG138J)
    cfg["state_dir"] = d
    cfg["sleep_threshold"] = 100000
    return L138J.build_agent138j(cfg)


def triples(loop) -> list:
    return [list(t) for t in L90.notebook_triples(loop.nb)]


# ------------------------------------------------------------------ G3
G3_PAIRS = [
    ("G3a", ["Oda's boss is Kim.", "Kim's city is Lagos.",
             "what is odas boss's city?"],
     "COMPOSED-180b-193-base-two-hop"),
    ("G3b", ["Kim's boss is Sam.", "No, Kim's boss is Lee."],
     "fable_loop192_agent"),
    ("G3c", ["Omar speaks Urdu.", "No, Omar's language is Farsi.",
             "What is Omar's language?"],
     "COMPOSED-167d-verb-154g-replace"),
    ("G3d", ["Omar speaks Urdu.", "Omar speaks Hindi.",
             "Omar's language is not Hindi."],
     "COMPOSED-167d-verb-154e-multi-154f-negate"),
    ("G3e", ["Kim's boss is Lee.", "Kim works at Acme.",
             "Tell me about Kim."],
     "COMPOSED-167d-verb-164b-about"),
    ("G3f", ["Kim's boss is Lee.", "Who is Kim's boss?", "Come again?"],
     "COMPOSED-base-ask-189b-repeat"),
    ("G3g", ["Kim's city is Lima.", "Who lives in Lima?"],
     "COMPOSED-base-teach-190-reverse"),
    ("G3h", ["My name is Juno.", "Tell me about me."],
     "COMPOSED-173b-name-164b-about-me"),
    ("G3i", ["What are you?", "The weather was nice yesterday."],
     "COMPOSED-187b-self-188-statefall"),
]


def mkbase(modname: str):
    mod = __import__(modname)
    cfg = next(copy.deepcopy(getattr(mod, a)) for a in dir(mod)
               if a.startswith("DEFAULT_CONFIG"))
    builder = next(getattr(mod, a) for a in dir(mod)
                   if a.startswith("build_agent"))

    def build():
        d = tempfile.mkdtemp(prefix="g3own-")
        c = dict(cfg)
        c["state_dir"] = d
        c["sleep_threshold"] = 100000
        return builder(c)

    return build


def run_g3() -> dict:
    frozen = json.loads((ART / "cases138j-g3.json").read_text(
        encoding="utf-8"))
    f_by_id = {c["id"]: c for c in frozen["cases"]}
    rows = []
    for pid, turns, owner in G3_PAIRS:
        loop = fresh138j()
        replies = [" ".join(loop.turn(t)) for t in turns]
        stored = sorted(triples(loop))
        if owner.startswith("COMPOSED"):
            own_replies, own_stored = None, None
        else:
            own = mkbase(owner)()
            own_replies = [" ".join(own.turn(t)) for t in turns]
            own_stored = sorted(triples(own))
        want = f_by_id[pid]
        ok = (replies == want["replies"]
              and stored == sorted(want["stored"]))
        rows.append({"id": pid, "turns": turns, "replies138j": replies,
                     "stored138j": stored, "owner": owner,
                     "replies_own": own_replies, "stored_own": own_stored,
                     "frozen_exact": ok})
        print(f"G3 {pid} ({owner}): {'EXACT' if ok else 'MOVED'}",
              flush=True)
        for t, r in zip(turns, replies):
            print(f"    {t!r} => {r!r}", flush=True)
        print(f"    stored={stored}", flush=True)
    return {"suite": "g3-director", "n": len(rows), "rows": rows}


# ------------------------------------------------------------------ G4
def run_g4() -> dict:
    cases = json.loads((ROOT / "artifacts" / "fable-speed170-20260922"
                        / "cases-s2-fresh.json").read_text(encoding="utf-8"))
    turns = cases["turns"]
    env = dict(os.environ)
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    helper = ("import sys,copy,json,tempfile,hashlib;"
              "sys.path.insert(0,'scripts');"
              "import fable_loop138j_agent as M,fable_loop90_agent as L90;"
              "d=tempfile.mkdtemp();"
              "cfg=copy.deepcopy(M.DEFAULT_CONFIG138J);"
              "cfg['state_dir']=d;cfg['sleep_threshold']=100000;"
              "L=M.build_agent138j(cfg);"
              "turns=json.load(open(sys.argv[1]))['turns'];"
              "reps=[' '.join(L.turn(t)) for t in turns];"
              "facts=hashlib.sha256('\\n'.join(sorted(' '.join(map(str,t)) for t in L90.notebook_triples(L.nb))).encode()).hexdigest();"
              "json.dump({'replies':reps,'facts_sha':facts,'events':len(L.nb.events)},open(sys.argv[2],'w'))")
    tmp = Path(tempfile.mkdtemp(prefix="g4-138j-"))
    casepath = tmp / "cases.json"
    casepath.write_text(json.dumps(cases), encoding="utf-8")
    outs = {}
    for tag, extra in (("on", {}), ("off", {"FABLE138J_INDEX": "off"})):
        e = dict(env)
        e.update(extra)
        op = tmp / f"out-{tag}.json"
        t0 = time.time()
        subprocess.run(
            [sys.executable, "-B", "-c", helper, str(casepath), str(op)],
            check=True, env=e, cwd=str(ROOT),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        outs[tag] = {"payload": json.loads(op.read_text(encoding="utf-8")),
                     "seconds": round(time.time() - t0, 1)}
    on, off = outs["on"]["payload"], outs["off"]["payload"]
    ndiff = sum(1 for a, b in zip(on["replies"], off["replies"]) if a != b)
    identical = (ndiff == 0 and on["facts_sha"] == off["facts_sha"]
                 and on["events"] == off["events"])
    print(f"G4 s2-fresh n={len(turns)} reply_diffs={ndiff} "
          f"facts_equal={on['facts_sha'] == off['facts_sha']} "
          f"events={on['events']}/{off['events']} "
          f"sec_on={outs['on']['seconds']} sec_off={outs['off']['seconds']}",
          flush=True)
    return {"suite": "g4-index", "n": len(turns), "reply_diffs": ndiff,
            "facts_sha_on": on["facts_sha"],
            "facts_sha_off": off["facts_sha"],
            "events_on": on["events"], "events_off": off["events"],
            "identical": identical,
            "seconds_on": outs["on"]["seconds"],
            "seconds_off": outs["off"]["seconds"]}


# ------------------------------------------------------------------ G2
def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False,
                                          sort_keys=True) for r in rows)
                    + "\n", encoding="utf-8")


def run_rt136() -> dict:
    import fable_fix139b_redteam136 as R136  # noqa: E402 (judge, read-only)
    cfg = copy.deepcopy(L138J.DEFAULT_CONFIG138J)
    cfg["sleep_threshold"] = 100000

    def new_daemon138j(root: Path):
        c = dict(cfg)
        c["state_dir"] = str(root)
        return L138J.Loop138jDaemon(root, cfg=c, idle_seconds=3600.0)

    R136.new_daemon139b = new_daemon138j  # type: ignore[method-assign]
    cases = json.loads((ROOT / "artifacts" / "fable-redteam136-20260922"
                        / "cases136.json").read_text(encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", cases)
    workroot = OUTDIR / "work-rt136"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    rows = [R136.run_case139b(row, workroot) for row in cases]
    write_rows(OUTDIR / "redteam136-loop138j.json", rows)
    base = [json.loads(line) for line in
            (ART138I / "g2frozen" / "redteam136-loop138i.json").read_text(
                encoding="utf-8").splitlines() if line.strip()]
    b_by_id = {r["id"]: r for r in base}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if (r["verdict"] != b["verdict"]
                or str(r.get("reply", "")).strip()
                != str(b.get("reply", "")).strip()
                or r.get("stored") != b.get("stored")):
            moves.append({"id": r["id"], "loop138i": b["verdict"],
                          "loop138j": r["verdict"],
                          "reply138i": str(b.get("reply", ""))[:140],
                          "reply138j": str(r.get("reply", ""))[:140]})
            if b["verdict"] not in WRONGish and r["verdict"] in WRONGish:
                new_wrong += 1
    print(f"rt136: {dict(Counter(r['verdict'] for r in rows))} "
          f"moves={len(moves)} new_wrong={new_wrong}", flush=True)
    for m in moves[:20]:
        print(f"  MOVE {m}", flush=True)
    return {"suite": "redteam136", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_138i": moves, "new_wrong_vs_138i": new_wrong}


def run_rt143() -> dict:
    import fable_redteam143_run as R143  # noqa: E402 (judge, read-only)
    R143.Loop132Daemon = L138J.Loop138jDaemon  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(  # type: ignore[method-assign]
        L138J.DEFAULT_CONFIG138J)
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = OUTDIR / "scratch143-loop138j"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    rows = [R143.run_case(case, scratch / case["id"], markers)
            for case in suite["cases"]]
    (OUTDIR / "redteam143-loop138j.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    base = json.loads((ART138I / "g2frozen" / "redteam143-loop138i.json").read_text(
        encoding="utf-8"))
    b_by_id = {r["id"]: r for r in base["rows"]}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if (r["verdict"] != b["verdict"]
                or str(r.get("reply", "")).strip()
                != str(b.get("reply", "")).strip()):
            moves.append({"id": r["id"], "loop138i": b["verdict"],
                          "loop138j": r["verdict"],
                          "reply138i": str(b.get("reply", ""))[:140],
                          "reply138j": str(r.get("reply", ""))[:140]})
            if b["verdict"] not in WRONGish and r["verdict"] in WRONGish:
                new_wrong += 1
    print(f"rt143: {dict(Counter(r['verdict'] for r in rows))} "
          f"moves={len(moves)} new_wrong={new_wrong}", flush=True)
    for m in moves[:20]:
        print(f"  MOVE {m}", flush=True)
    return {"suite": "rt143", "n": len(rows),
            "counter": dict(Counter(r["verdict"] for r in rows)),
            "moves_vs_138i": moves, "new_wrong_vs_138i": new_wrong}


def run_sessions() -> dict:
    import fable_session152_run as S152R  # noqa: E402 (judge, read-only)
    sessions_out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = OUTDIR / "work-sessions-loop138j" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(L138J.DEFAULT_CONFIG138J)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L138J.Loop138jDaemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    (OUTDIR / "sessions152-loop138j.json").write_text(
        json.dumps(sessions_out, indent=1, ensure_ascii=False),
        encoding="utf-8")
    out138i = json.loads((ART138I / "g2frozen" / "sessions152-loop138i.json").read_text(
        encoding="utf-8"))
    moves, new_wrong, new_writes = [], 0, []
    counts138i: Counter = Counter()
    counts138j: Counter = Counter()
    for sid, turns in sessions_out.items():
        for t, b in zip(turns, out138i.get(sid, [])):
            counts138i[b["verdict"]] += 1
            counts138j[t["verdict"]] += 1
            if (t["verdict"] != b["verdict"]
                    or str(t.get("reply", "")).strip()
                    != str(b.get("reply", "")).strip()):
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop138i": b["verdict"],
                              "loop138j": t["verdict"],
                              "reply138i": str(b["reply"]).strip()[:120],
                              "reply138j": str(t["reply"]).strip()[:120],
                              "why": t["why"][:160]})
                if (t["verdict"] == "WRONG"
                        and b["verdict"] != "WRONG"):
                    new_wrong += 1
            bw = (b.get("fact_writes") or b.get("writes") or [])
            tw = (t.get("fact_writes") or t.get("writes") or [])
            if tw and tw != bw:
                new_writes.append({"session": sid, "n": t["n"],
                                   "loop138i_writes": bw,
                                   "loop138j_writes": tw})
    print(f"sessions: {dict(counts138j)} moves={len(moves)} "
          f"new_wrong={new_wrong} new_writes={len(new_writes)}", flush=True)
    for m in moves[:20]:
        print(f"  MOVE {m}", flush=True)
    for w in new_writes[:20]:
        print(f"  WRITE {w}", flush=True)
    return {"suite": "sessions", "loop138i": dict(counts138i),
            "loop138j": dict(counts138j), "moves_vs_138i": moves,
            "new_wrong_vs_138i": new_wrong, "new_writes": new_writes}


# ---------------------------------------------------------------- G1 v3
def run_benchv3(only: str = "all") -> dict:
    """Bench under protocol v3 (confirming user) with the loop138j arm;
    verdicts compared vs loop138i's sealed v3 rows: 0 new wrong."""
    import fable_bench121_run as B  # noqa: E402 (scorer, read-only)
    import fable_fix172b_benchv3 as V3  # noqa: E402 (v3 driver, read-only)
    daemon_cls, cfg0 = L138J.Loop138jDaemon, L138J.DEFAULT_CONFIG138J
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
    want = only.split(",")
    if want != ["all"]:
        splits = [s for s in splits if s[0] in want]
    workroot = OUTDIR / "scratch-benchv3-loop138j"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    summary: dict = {"seconds": 0.0, "arm": "loop138j", "proto": "v3",
                     "splits": {}}
    for stag, path, sealed_name in splits:
        items = [json.loads(line) for line in
                 Path(str(path)).read_text(
                     encoding="utf-8").splitlines() if line.strip()]
        cfg = copy.deepcopy(cfg0)
        cfg["sleep_threshold"] = 100000
        rows = [V3.run_item_v3(it, workroot / stag, copy.deepcopy(cfg),
                               daemon_cls, "v3") for it in items]
        (OUTDIR / f"fable_benchv3_loop138j_{stag}_rows.jsonl").write_text(
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
                              "loop138j": r["verdict"],
                              "reply138i": str(s.get("reply", ""))[:120],
                              "reply138j": str(r.get("reply", ""))[:120]})
                if s["verdict"] != "wrong" and r["verdict"] == "wrong":
                    new_wrong += 1
        summary["splits"][stag] = {"loop138j": cell,
                                   "moves_vs_138i": moves,
                                   "new_wrong_vs_138i": new_wrong}
        print(f"v3 {stag}: loop138j {cell} new_wrong={new_wrong} "
              f"moves={len(moves)}", flush=True)
        for m in moves[:16]:
            print(f"  MOVE {m}", flush=True)
    return summary


def main(argv=None) -> int:
    global OUTDIR
    ap = argparse.ArgumentParser(description="Exp 138j G suites")
    ap.add_argument("--only", default="g3",
                    help="comma list of g3,g4,rt136,rt143,sessions,benchv3")
    ap.add_argument("--bench-only", default="all")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    if args.out:
        OUTDIR = Path(args.out)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc = 0
    out: dict = {}
    for name in args.only.split(","):
        t1 = time.time()
        if name == "g3":
            out["g3"] = run_g3()
            if any(not r["frozen_exact"] for r in out["g3"]["rows"]):
                rc = 1
        elif name == "g4":
            out["g4"] = run_g4()
            if not out["g4"]["identical"]:
                rc = 1
        elif name == "rt136":
            out["rt136"] = run_rt136()
            if out["rt136"]["new_wrong_vs_138i"]:
                rc = 1
        elif name == "rt143":
            out["rt143"] = run_rt143()
            if out["rt143"]["new_wrong_vs_138i"]:
                rc = 1
        elif name == "sessions":
            out["sessions"] = run_sessions()
            if out["sessions"]["new_wrong_vs_138i"]:
                rc = 1
        elif name == "benchv3":
            out["benchv3"] = run_benchv3(args.bench_only)
            if any(s["new_wrong_vs_138i"]
                   for s in out["benchv3"]["splits"].values()):
                rc = 1
        else:
            print(f"unknown suite {name}", flush=True)
            rc = 1
        print(f"done {name} in {round(time.time() - t1, 1)}s", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    (OUTDIR / "suites138j-summary.json").write_text(
        json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    print(f"wrote {OUTDIR / 'suites138j-summary.json'} "
          f"seconds={out['seconds']}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
