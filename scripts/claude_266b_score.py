#!/usr/bin/env python3
"""Exp 266b scorer for marks M2..M4 (M1 has the blind panels' sealed scorers).
Reads only row files; runs nothing. Mirrors scripts/claude_266_score.py
one-for-one, with the 266b agent/config/paths and the 266b chain finder
for the M3 ghost check (so multi-word lifts are not flagged as ghosts).

Run dir layout (all produced by scripts/claude_266b_runall.sh):
  sd/                 fable_suitediff218 on 266b vs 266's saved rows
                      (--base-dir artifacts/claude-chain266-20260923/run/sd)
  sd136/              fable_suitediff218 --only rt136 vs 138j's sealed rows
                      (labels; same method as 266) -- the scorer also
                      compares every row directly with 266's saved
                      run/sd136/rt136-rows.json
  rt143nogate-n.json  claude_138l_rt143nogate.py on 266b (base: 266's saved
                      run/rt143nogate-n.json)
  probe/n-<file>.json claude_merge138k_probe.py on 266b (138j p3-dialogs,
                      p3c-restart2, p3d-ghost; 138k v-dialogs, v-supp;
                      base: 266's run/probe/n-<file>.json)
  probe266b.json      run_probes.py on 266b over 138m/probes.json
                      (base: 266's run/probe266.json)
  probe266b-supp.json run_probes.py on 266b over 138m/probes-supp.json
                      (base: 266's run/probe266-supp.json)
  lat-{m,n}-{1,2,3}.json  claude_merge138k_latency.py, alternating processes
                      (m = 266 arm, n = 266b arm)

usage: claude_266b_score.py <run_dir> <predicted_moves266b.json> <out.json>
       claude_266b_score.py --predict <pilot_run_dir> <pred.json>
           (builds the m2/m3 sections of pred.json from a pilot run dir)
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
N_RUN = ROOT / "artifacts/claude-chain266-20260923/run"
M_PRED = ROOT / "artifacts/claude-merge138m-20260922/predicted_moves138m.json"
M138 = ROOT / "artifacts/claude-verify-20260922/138m"
BENCH_FILES = ("bench132_4hop", "edit200", "new_121_4hop", "old_s2fresh_4hop")
SUITES = ("rt136", "sessions152", "bench", "marks123")
PROBES = ("p3-dialogs", "p3c-restart2", "p3d-ghost", "v-dialogs", "v-supp")
BAD_CLASSES = ("new WRONG", "new WRONG-WRITE", "new junk write", "lost OK")


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def jsonl_raw(p: Path) -> dict:
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out[json.loads(line)["id"]] = line
    return out


def jsonl(p: Path) -> dict:
    return {k: json.loads(v) for k, v in jsonl_raw(p).items()}


def _sd_dirs(run: Path) -> dict:
    return {"rt136": run / "sd136", "sessions152": run / "sd",
            "bench": run / "sd", "marks123": run / "sd"}


def _exc() -> dict:
    return jl(M_PRED)["exceptions_222_inherited_from_138l"]


def m2(run: Path, pred: dict) -> dict:
    res: dict = {}
    ok_all = True
    dirs = _sd_dirs(run)
    skipped = [s for s in SUITES if not (dirs[s] / f"{s}-diff.json").exists()]
    res["suites_skipped"] = skipped
    if skipped:
        res["pass"] = False
        return res
    exc = _exc()
    for suite in SUITES:
        d = jl(dirs[suite] / f"{suite}-diff.json")
        got = {(m["id"], m["class"]) for m in d["moves"]}
        want = {(m["id"], m["class"]) for m in pred["m2"][suite]}
        unpred = sorted(got - want)
        missing = sorted(want - got)
        ex = set(exc.get(suite, []))
        bad_new = sorted(m["id"] for m in d["moves"]
                         if m["class"] in BAD_CLASSES
                         and m["id"] not in ex)
        ok = not unpred and not missing and not bad_new
        res[suite] = {"n_moves": len(got),
                      "class_counts": d.get("class_counts"),
                      "unpredicted": unpred, "predicted_not_seen": missing,
                      "new_bad_outside_222_exceptions": bad_new, "pass": ok}
        ok_all &= ok
    keys = ("reply", "stored", "verdict")
    lr = jsonl(N_RUN / "sd136" / "rt136-rows.json")
    mr = jsonl(run / "sd136" / "rt136-rows.json")
    moved = sorted(i for i in lr if any(lr[i][k] != mr[i][k] for k in keys))
    res["rt136_direct_vs_266_rows"] = {
        "moved": moved, "n": len(mr),
        "pass": moved == pred["m2"]["rt136_direct_vs_266"]
        and len(lr) == len(mr)}
    ok_all &= res["rt136_direct_vs_266_rows"]["pass"]

    def same(a, b):
        return ({k: v for k, v in a.items() if k != "seconds"}
                == {k: v for k, v in b.items() if k != "seconds"})
    a = jsonl(N_RUN / "sd136" / "rt136-rows.json")
    b = jsonl(run / "sd136" / "rt136-rows.json")
    rt136_same = [i for i in exc["rt136"] if same(a[i], b[i])]
    a = jsonl(N_RUN / "sd" / "bench-edit200-rows.jsonl")
    b = jsonl(run / "sd" / "bench-edit200-rows.jsonl")
    bench_same = [i for i in exc["bench"] if same(a[i], b[i])]
    mk = "marks123/bench-rows-fable_edit_200.jsonl"
    a = jsonl(N_RUN / "sd" / mk)
    b = jsonl(run / "sd" / mk)
    pre = "bench-fable_edit_200:"
    marks_same = [i for i in exc["marks123"]
                  if same(a[i[len(pre):]], b[i[len(pre):]])]
    n_exc = len(exc["rt136"]) + len(exc["bench"]) + len(exc["marks123"])
    n_same = len(rt136_same) + len(bench_same) + len(marks_same)
    res["exceptions_identical_to_266_rows"] = {
        "rt136": f"{len(rt136_same)}/{len(exc['rt136'])}",
        "bench": f"{len(bench_same)}/{len(exc['bench'])}",
        "marks123": f"{len(marks_same)}/{len(exc['marks123'])}",
        "total": f"{n_same}/{n_exc}", "pass": n_same == n_exc == 63}
    ok_all &= res["exceptions_identical_to_266_rows"]["pass"]
    import fable_redteam143_run as R
    markers = jl(R.CASES_PATH)["abstain_markers"]
    base = {r["id"]: r for r in jl(N_RUN / "rt143nogate-n.json")}
    new = {r["id"]: r for r in jl(run / "rt143nogate-n.json")}
    moves = []
    for cid, r in base.items():
        f = [k for k in ("teach_replies", "triples", "reply")
             if r[k] != new[cid][k]]
        if f:
            moves.append({"id": cid, "fields": f, "base_reply": r["reply"],
                          "new_reply": new[cid]["reply"]})
    want = {m["id"]: m for m in pred["m2"]["rt143_nogate"]}
    rt_bad = [m["id"] for m in moves if m["id"] not in want
              or m["fields"] != want[m["id"]]["fields"]
              or m["new_reply"] != want[m["id"]]["new_reply"]]
    rt_missing = sorted(set(want) - {m["id"] for m in moves})

    def verdict(row):
        low = row["reply"].lower()
        abst = any(m.lower() in low for m in markers)
        exp = row["expected"]
        if exp == "abstain":
            return "OK" if abst else "WRONG-ANSWER"
        if R.norm(R.extract_answer(row["reply"])) == R.norm(exp) \
                and R.norm(exp):
            return "OK"
        return "MISSED" if abst else "WRONG-ANSWER"
    vflips = [{"id": i, "m": verdict(base[i]), "n": verdict(new[i])}
              for i in base if verdict(base[i]) != verdict(new[i])]
    ok = not rt_bad and not rt_missing and not vflips
    res["rt143_nogate"] = {"n_moves": len(moves), "unpredicted": rt_bad,
                           "predicted_not_seen": rt_missing,
                           "verdict_flips": vflips, "pass": ok}
    ok_all &= ok
    res["pass"] = bool(ok_all)
    return res


def _probe_changes(run: Path) -> tuple[list[dict], list[str]]:
    """Reply changes 266b vs 266's M6 probe rows + failed dup audits."""
    changes, dup_fails = [], []
    for b in PROBES:
        m_rows = jl(N_RUN / "probe" / f"n-{b}.json")["rows"]
        n_rows = jl(run / "probe" / f"n-{b}.json")["rows"]
        for md, nd in zip(m_rows, n_rows):
            for i, (mt, nt) in enumerate(zip(md["turns"], nd["turns"])):
                if mt["reply"] != nt["reply"] or mt["events"] != nt["events"]:
                    changes.append({"file": b, "dialog": md["dialog"],
                                    "turn": i, "q": mt["turn"],
                                    "m": mt["reply"], "n": nt["reply"],
                                    "m_events": mt["events"],
                                    "n_events": nt["events"]})
            for tag, dd in (("m", md), ("n", nd)):
                for a in dd.get("audits", []):
                    dup = [list(t) for t in a.get("dup_fast", [])] \
                        or [list(t) for t in a.get("dup_ids", [])]
                    fast = sorted(map(str, a.get("fast", [])))
                    truth = sorted(map(str, a.get("truth", [])))
                    if dup or fast != truth or not a.get("dup_ok", True):
                        dup_fails.append(f"{tag}-{b}#{dd['dialog']}"
                                         f"@{a.get('where')}")
    return changes, dup_fails


def _vprobe_changes(run: Path) -> tuple[list[dict], int, int]:
    """Reply changes 266b vs 266's verifier rows (probes + supp)."""
    changes = []
    n_dlgs = 0
    n_restart_audits = 0
    for stem, base in (("probe266b", N_RUN / "probe266.json"),
                       ("probe266b-supp", N_RUN / "probe266-supp.json")):
        m_rows = jl(base)
        n_rows = jl(run / f"{stem}.json")
        assert len(m_rows) == len(n_rows), (stem, len(m_rows), len(n_rows))
        for md, nd in zip(m_rows, n_rows):
            assert md["id"] == nd["id"], (stem, md["id"], nd["id"])
            n_dlgs += 1
            for i, (mr, nr) in enumerate(zip(md["rows"], nd["rows"])):
                if mr.get("restart") or nr.get("restart"):
                    n_restart_audits += 1
                    if mr.get("triples") != nr.get("triples"):
                        changes.append({"file": stem, "dialog": md["id"],
                                        "turn": i, "q": "__RESTART__",
                                        "m": str(mr.get("triples")),
                                        "n": str(nr.get("triples"))})
                    continue
                if mr["reply"] != nr["reply"] or mr["ev"] != nr["ev"] \
                        or mr.get("stored") != nr.get("stored") \
                        or mr.get("triples") != nr.get("triples"):
                    changes.append({"file": stem, "dialog": md["id"],
                                    "turn": i, "q": mr["turn"],
                                    "m": mr["reply"], "n": nr["reply"]})
    return changes, n_dlgs, n_restart_audits


def _has_chain(turn: str) -> bool:
    import claude_fix266b_detector as F266B
    try:
        return F266B.find_chain266b(turn) is not None
    except Exception:
        return False


def _taught_values(turns: list[str], upto: int) -> list[str]:
    vals = []
    for t in turns[:upto]:
        s = " ".join(str(t).split())
        if s.endswith("?"):
            continue
        low = s.lower()
        for lead in ("actually, ", "actually ", "no, ", "no "):
            if low.startswith(lead):
                s = s[len(lead):]
                break
        if " is " in s:
            v = s.split(" is ", 1)[1].rstrip(".").strip()
            if v:
                vals.append(v)
    return vals


def m3(run: Path, pred: dict) -> dict:
    p_changes, dup_fails = _probe_changes(run)
    v_changes, n_dlgs, n_audits = _vprobe_changes(run)
    all_changes = ([{**c, "src": "m6"} for c in p_changes]
                   + [{**c, "src": "vprobe"} for c in v_changes])
    want = {(c["src"], c["file"], c["dialog"], c["turn"]): c
            for c in pred["m3"]["reply_changes"]}
    got = {(c["src"], c["file"], c["dialog"], c["turn"]): c
           for c in all_changes}
    unpred = sorted(set(got) - set(want))
    missing = sorted(set(want) - set(got))
    wrong = sorted(k for k in set(got) & set(want)
                   if got[k]["n"] != want[k]["n"])
    ghosts = []
    for k, c in got.items():
        q = c.get("q", "")
        if q == "__RESTART__":
            ghosts.append(k)
            continue
        if not _has_chain(q):
            ghosts.append(k)
            continue
        n = c["n"]
        nl = n.lower()
        if "don't know" in nl or "do not know" in nl \
                or "didn't understand" in nl \
                or "not someone i can look up" in nl:
            continue
        ghosts.append(k)
    write_changes = [k for k, c in got.items()
                     if c.get("m_events", 0) != c.get("n_events", 0)]
    ok = (not unpred and not missing and not wrong and not ghosts
          and not dup_fails and not write_changes)
    return {"n_dialogs": n_dlgs + len(PROBES),
            "n_restart_audits": n_audits,
            "n_reply_changes": len(all_changes),
            "reply_changes": all_changes,
            "unpredicted": unpred, "predicted_not_seen": missing,
            "predicted_but_different": wrong, "ghost_answers": ghosts,
            "failed_duplicate_checks": dup_fails,
            "write_changes": write_changes, "pass": bool(ok)}


def m4(run: Path) -> dict:
    mt, nt = [], []
    for i in (1, 2, 3):
        mt += jl(run / f"lat-m-{i}.json")["times_ms"]
        nt += jl(run / f"lat-n-{i}.json")["times_ms"]
    med_m, med_n = statistics.median(mt), statistics.median(nt)
    return {"n_turns_each": len(mt), "median_266_ms": med_m,
            "median_266b_ms": med_n, "added_ms": med_n - med_m,
            "pass": (med_n - med_m) <= 5.0}


def score(run: Path, pred: dict) -> dict:
    out = {"m2": m2(run, pred), "m3": m3(run, pred), "m4": m4(run)}
    out["pass"] = out["m2"]["pass"] and out["m3"]["pass"] \
        and out["m4"]["pass"]
    return out


def predict(run: Path) -> dict:
    """Build m2/m3 prediction sections from a pilot run dir (reviewed by
    hand before sealing: every entry must be a multi-word chain lift)."""
    pred: dict = {"m2": {}, "m3": {}}
    dirs = _sd_dirs(run)
    for suite in SUITES:
        d = jl(dirs[suite] / f"{suite}-diff.json")
        pred["m2"][suite] = [{"id": m["id"], "class": m["class"]}
                             for m in d["moves"]]
    keys = ("reply", "stored", "verdict")
    lr = jsonl(N_RUN / "sd136" / "rt136-rows.json")
    mr = jsonl(run / "sd136" / "rt136-rows.json")
    pred["m2"]["rt136_direct_vs_266"] = sorted(
        i for i in lr if any(lr[i][k] != mr[i][k] for k in keys))
    base = {r["id"]: r for r in jl(N_RUN / "rt143nogate-n.json")}
    new = {r["id"]: r for r in jl(run / "rt143nogate-n.json")}
    moves = []
    for cid, r in base.items():
        f = [k for k in ("teach_replies", "triples", "reply")
             if r[k] != new[cid][k]]
        if f:
            moves.append({"id": cid, "fields": f, "base_reply": r["reply"],
                          "new_reply": new[cid]["reply"]})
    pred["m2"]["rt143_nogate"] = moves
    p_changes, _ = _probe_changes(run)
    v_changes, _, _ = _vprobe_changes(run)
    pred["m3"] = {"reply_changes": [
        {"src": "m6", "file": c["file"], "dialog": c["dialog"],
         "turn": c["turn"], "q": c["q"], "m": c["m"], "n": c["n"]}
        for c in p_changes] + [
        {"src": "vprobe", "file": c["file"], "dialog": c["dialog"],
         "turn": c["turn"], "q": c["q"], "m": c["m"], "n": c["n"]}
        for c in v_changes]}
    return pred


def main(argv=None) -> int:
    if len(argv or []) >= 1 and argv[0] == "--predict":
        _, pilot, out = argv
        Path(out).write_text(
            json.dumps(predict(Path(pilot)), indent=1), encoding="utf-8")
        print(f"Wrote {out}")
        return 0
    run, pred_path, out_path = (Path(argv[0]), Path(argv[1]), Path(argv[2]))
    pred = json.loads(pred_path.read_text(encoding="utf-8"))
    res = score(run, pred)
    Path(out_path).write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k in ("m2", "m3", "m4"):
        print(f"{k}: pass={res[k]['pass']}")
    print(f"OVERALL pass={res['pass']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
