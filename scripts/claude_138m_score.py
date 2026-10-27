#!/usr/bin/env python3
"""Merge 138m -- scorer for marks M2..M6 (M1 has its own judge in
scripts/claude_138m_l1.py). Reads only row files; runs nothing.

Run dir layout (all produced by scripts/claude_138m_runall.sh):
  sd/                 fable_suitediff218 on 138m vs 138l's saved rows
                      (--base-dir artifacts/claude-merge138l-20260922/run/sd)
  sd136/              fable_suitediff218 --only rt136 vs 138j's sealed rows
                      (labels; same method as 138l) -- the scorer also
                      compares every row directly with 138l's saved
                      run/sd136/rt136-rows.json
  rt143nogate-m.json  claude_138l_rt143nogate.py on 138m (base: 138l's saved
                      run/rt143nogate-l.json)
  smoke-{l,m}.json    fable_sleepsmoke206.py
  bench{1,2,3}/       fable_suitediff218 --only bench, three back-to-back runs
  lat-{l,m}-{1,2,3}.json  claude_merge138k_latency.py, alternating processes
  probe/{l,m}-<file>.json claude_merge138k_probe.py on the verifier dialogs
                      (138j p3-dialogs, p3c-restart2, p3d-ghost; 138k
                      v-dialogs, v-supp)

usage: claude_138m_score.py <run_dir> <predicted_moves138m.json> <out.json>
       claude_138m_score.py --predict <pilot_run_dir> <pred.json>
           (adds the m2/m6 sections to pred.json from a pilot run dir)
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
L_RUN = ROOT / "artifacts/claude-merge138l-20260922/run"
L_PRED = ROOT / "artifacts/claude-merge138l-20260922/predicted_moves138l.json"
BENCH_FILES = ("bench132_4hop", "edit200", "new_121_4hop", "old_s2fresh_4hop")
SUITES = ("rt136", "sessions152", "bench", "marks123")
PROBES = ("p3-dialogs", "p3c-restart2", "p3d-ghost", "v-dialogs", "v-supp")
NAME_PREFIXES = ("Yes. Your name is ", "Your name is ", "No. Your name is ")


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


def fixed_texts() -> set[str]:
    """Replies that state no notebook fact (224 sentences, 234 fixed reply,
    227c identity sheet / name-check / rename)."""
    import claude_identity227c as C
    import claude_loop234_agent as A234
    import fable_decline224 as DEC
    s = set(DEC.NEW_SENTENCES224.values())
    s |= {A234.FIXED_234, A234.GREET_PREFIX_234 + A234.FIXED_234}
    s |= set(C.SHEET_227C.values())
    s |= {C.NAMECHECK_YES, C.NAMECHECK_NO, C.RENAME_REPLY}
    return s


def _sd_dirs(run: Path) -> dict:
    return {"rt136": run / "sd136", "sessions152": run / "sd",
            "bench": run / "sd", "marks123": run / "sd"}


def _rt143_moves(run: Path) -> list[dict]:
    base = {r["id"]: r for r in jl(L_RUN / "rt143nogate-l.json")}
    new = {r["id"]: r for r in jl(run / "rt143nogate-m.json")}
    moves = []
    for cid, r in base.items():
        f = [k for k in ("teach_replies", "triples", "reply")
             if r[k] != new[cid][k]]
        if f:
            moves.append({"id": cid, "fields": f, "base_reply": r["reply"],
                          "new_reply": new[cid]["reply"]})
    return moves


def _rt143_verdict(row: dict, markers) -> str:
    import fable_redteam143_run as R
    low = row["reply"].lower()
    abst = any(m.lower() in low for m in markers)
    exp = row["expected"]
    if exp == "abstain":
        return "OK" if abst else "WRONG-ANSWER"
    if R.norm(R.extract_answer(row["reply"])) == R.norm(exp) and R.norm(exp):
        return "OK"
    return "MISSED" if abst else "WRONG-ANSWER"


def _rt136_direct(run: Path) -> list[str]:
    keys = ("reply", "stored", "verdict")
    lr = jsonl(L_RUN / "sd136" / "rt136-rows.json")
    mr = jsonl(run / "sd136" / "rt136-rows.json")
    return sorted(i for i in lr if any(lr[i][k] != mr[i][k] for k in keys))


def m1(run: Path) -> dict:
    """Roll-up of claude_138m_l1.py judge (m vs line head, every move
    predicted by id) and sealed (own arm reproduces each piece's sealed
    rows, i.e. the driver runs each piece faithfully)."""
    j = jl(run / "l1-judge.json")
    sd = jl(run / "l1-sealed.json")
    n_sealed = sum(v["n_sealed"] for v in sd.values())
    unmatched = {k: v["unmatched"] for k, v in sd.items() if v["unmatched"]}
    n_cases = sum(v["n"] for v in j["pieces"].values())
    n_moved = sum(v["moved"] for v in j["pieces"].values())
    ok = j["pass"] and not unmatched
    return {"n_cases": n_cases, "n_moved_vs_head": n_moved,
            "judge_counts": j["counts"],
            "own_arm_sealed_rows_reproduced":
                f"{n_sealed - sum(map(len, unmatched.values()))}/{n_sealed}",
            "unmatched": unmatched, "pass": ok}


def m2(run: Path, pred: dict) -> dict:
    res: dict = {}
    ok_all = True
    dirs = _sd_dirs(run)
    skipped = [s for s in SUITES if not (dirs[s] / f"{s}-diff.json").exists()]
    res["suites_skipped"] = skipped
    if skipped:
        res["pass"] = False
        return res
    exc = jl(L_PRED)["L2_literal_bar_exceptions"]
    for suite in SUITES:
        d = jl(dirs[suite] / f"{suite}-diff.json")
        got = {(m["id"], m["class"]) for m in d["moves"]}
        want = {(m["id"], m["class"]) for m in pred["m2"][suite]}
        unpred = sorted(got - want)
        missing = sorted(want - got)
        ex = set(exc.get(suite, []))
        bad_new = sorted(m["id"] for m in d["moves"]
                         if m["class"] in ("new WRONG", "new WRONG-WRITE",
                                           "new junk write", "lost OK")
                         and m["id"] not in ex)
        ok = not unpred and not missing and not bad_new
        res[suite] = {"n_moves": len(got),
                      "class_counts": d.get("class_counts"),
                      "unpredicted": unpred, "predicted_not_seen": missing,
                      "new_bad_outside_222_exceptions": bad_new, "pass": ok}
        ok_all &= ok
    # rt136 direct row check against 138l's saved rows
    moved = _rt136_direct(run)
    n_l = len(jsonl(L_RUN / "sd136" / "rt136-rows.json"))
    n_m = len(jsonl(run / "sd136" / "rt136-rows.json"))
    res["rt136_direct_vs_138l_rows"] = {
        "moved": moved, "n": n_m,
        "pass": moved == pred["m2"]["rt136_direct_vs_138l"] and n_l == n_m}
    ok_all &= res["rt136_direct_vs_138l_rows"]["pass"]
    # the 63 declared 222 exception rows: identical to 138l's rows, every
    # field except the wall-clock "seconds" timing field (bench and marks123
    # rows carry no timing field, so those are compared whole)
    def same(a, b):
        return ({k: v for k, v in a.items() if k != "seconds"}
                == {k: v for k, v in b.items() if k != "seconds"})
    a = jsonl(L_RUN / "sd136" / "rt136-rows.json")
    b = jsonl(run / "sd136" / "rt136-rows.json")
    rt136_same = [i for i in exc["rt136"] if same(a[i], b[i])]
    a = jsonl(L_RUN / "sd" / "bench-edit200-rows.jsonl")
    b = jsonl(run / "sd" / "bench-edit200-rows.jsonl")
    bench_same = [i for i in exc["bench"] if same(a[i], b[i])]
    mk = "marks123/bench-rows-fable_edit_200.jsonl"
    a = jsonl(L_RUN / "sd" / mk)
    b = jsonl(run / "sd" / mk)
    pre = "bench-fable_edit_200:"
    marks_same = [i for i in exc["marks123"]
                  if same(a[i[len(pre):]], b[i[len(pre):]])]
    n_exc = len(exc["rt136"]) + len(exc["bench"]) + len(exc["marks123"])
    n_same = len(rt136_same) + len(bench_same) + len(marks_same)
    res["exceptions_identical_to_138l_rows"] = {
        "rt136": f"{len(rt136_same)}/{len(exc['rt136'])}",
        "bench": f"{len(bench_same)}/{len(exc['bench'])}",
        "marks123": f"{len(marks_same)}/{len(exc['marks123'])}",
        "total": f"{n_same}/{n_exc}", "pass": n_same == n_exc == 63}
    ok_all &= res["exceptions_identical_to_138l_rows"]["pass"]
    # rt143 no-gate vs 138l's saved rows + verdicts under rt143's own rule
    import fable_redteam143_run as R
    markers = jl(R.CASES_PATH)["abstain_markers"]
    moves = _rt143_moves(run)
    want = {m["id"]: m for m in pred["m2"]["rt143_nogate"]}
    rt_bad = [m["id"] for m in moves if m["id"] not in want
              or m["fields"] != want[m["id"]]["fields"]
              or m["new_reply"] != want[m["id"]]["new_reply"]]
    rt_missing = sorted(set(want) - {m["id"] for m in moves})
    base = {r["id"]: r for r in jl(L_RUN / "rt143nogate-l.json")}
    new = {r["id"]: r for r in jl(run / "rt143nogate-m.json")}
    vflips = [{"id": i, "l": _rt143_verdict(base[i], markers),
               "m": _rt143_verdict(new[i], markers)} for i in base
              if _rt143_verdict(base[i], markers)
              != _rt143_verdict(new[i], markers)]
    rt_ok = (not rt_bad and not rt_missing and len(new) == len(base)
             and not vflips)
    res["rt143_nogate"] = {"n": len(base), "n_moves": len(moves),
                           "bad": rt_bad, "predicted_not_seen": rt_missing,
                           "verdict_flips": vflips, "pass": rt_ok}
    ok_all &= rt_ok
    res["pass"] = ok_all
    return res


def _walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            _walk(a.get(k), b.get(k), f"{path}.{k}", out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            _walk(x, y, f"{path}[{i}]", out)
    elif a != b:
        out.append(path)


def m3(run: Path, pred: dict) -> dict:
    diffs = []
    _walk(jl(run / "smoke-l.json"), jl(run / "smoke-m.json"), "", diffs)
    allowed = {".agent", ".config", ".label", ".seconds", ".root", ".report"}
    allowed |= set(pred.get("m3_allowed_fields", []))
    bad = [d for d in diffs if d not in allowed]
    return {"differing_fields": diffs, "bad": bad, "pass": not bad}


def m4(run: Path) -> dict:
    same = []
    for f in BENCH_FILES:
        blobs = [(run / f"bench{i}" / f"bench-{f}-rows.jsonl").read_bytes()
                 for i in (1, 2, 3)]
        same.append(f if blobs[0] == blobs[1] == blobs[2] else None)
    n = sum(1 for x in same if x)
    return {"identical_files": f"{n}/4", "pass": n == 4}


def m5(run: Path) -> dict:
    ll, lm = [], []
    for i in (1, 2, 3):
        ll += jl(run / f"lat-l-{i}.json")["times_ms"]
        lm += jl(run / f"lat-m-{i}.json")["times_ms"]
    ml, mm = statistics.median(ll), statistics.median(lm)
    return {"median_l_ms": round(ml, 3), "median_m_ms": round(mm, 3),
            "delta_ms": round(mm - ml, 3), "n_l": len(ll), "n_m": len(lm),
            "pass": mm - ml <= 5.0}


def _probe_changes(run: Path) -> tuple[dict, list, list, dict]:
    changes, bad_writes, dup_fail, counts = {}, [], [], {}
    for p in PROBES:
        a = jl(run / "probe" / f"l-{p}.json")["rows"]
        b = jl(run / "probe" / f"m-{p}.json")["rows"]
        counts[p] = {"dialogs_l": len(a), "dialogs_m": len(b),
                     "audits_m": sum(len(r["audits"]) for r in b)}
        for x, y in zip(a, b):
            for i, (ta, tb) in enumerate(zip(x["turns"], y["turns"])):
                if ta["reply"] != tb["reply"]:
                    changes[f"{p}:d{x['dialog']:02d}:t{i:02d}"] = {
                        "turn": tb["turn"], "l": ta["reply"],
                        "m": tb["reply"], "stored_end": y["stored"]}
                if ta["events"] != tb["events"] or ta["turn"] != tb["turn"]:
                    bad_writes.append({"probe": p, "dialog": y["dialog"],
                                       "turn": i, "events_l": ta["events"],
                                       "events_m": tb["events"]})
            if len(x["turns"]) != len(y["turns"]):
                bad_writes.append({"probe": p, "dialog": y["dialog"],
                                   "turn_count": [len(x["turns"]),
                                                  len(y["turns"])]})
            if sorted(map(tuple, x["stored"])) != sorted(map(tuple,
                                                            y["stored"])):
                bad_writes.append({"probe": p, "dialog": y["dialog"],
                                   "stored_l": x["stored"],
                                   "stored_m": y["stored"]})
            if not y.get("dup_ok_all", False):
                dup_fail.append({"probe": p, "dialog": y["dialog"]})
    return changes, bad_writes, dup_fail, counts


def _ghost(ch: dict, fixed: set[str]) -> bool:
    """A changed reply that states something not in the notebook."""
    r = ch["m"]
    if r in fixed:
        return False
    for pre in NAME_PREFIXES:
        if r.startswith(pre):
            name = r[len(pre):].rstrip(".")
            users = {t[2] for t in ch["stored_end"]
                     if t[0] == "USER" and t[1] == "name"}
            return name not in users
    return True


def m6(run: Path, pred: dict) -> dict:
    changes, bad_writes, dup_fail, counts = _probe_changes(run)
    fixed = fixed_texts()
    want = pred["m6"]["reply_changes"]
    unpred = sorted(k for k in changes if k not in want)
    wrong = sorted(k for k in changes
                   if k in want and changes[k]["m"] != want[k]["m"])
    missing = sorted(k for k in want if k not in changes)
    ghosts = sorted(k for k, v in changes.items() if _ghost(v, fixed))
    n_ok = all(c["dialogs_l"] == c["dialogs_m"] > 0 and c["audits_m"] > 0
               for c in counts.values())
    ok = (n_ok and not unpred and not wrong and not missing and not ghosts
          and not bad_writes and not dup_fail)
    return {"counts": counts, "reply_changes": len(changes),
            "unpredicted": unpred, "predicted_wrong": wrong,
            "predicted_not_seen": missing, "ghost_answers": ghosts,
            "bad_writes": bad_writes, "failed_duplicate_checks": dup_fail,
            "pass": ok}


def predict(run: Path, pred_path: Path) -> int:
    """Add m2/m6 sections from a PILOT run dir (every move by id)."""
    pred = jl(pred_path) if pred_path.exists() else {}
    dirs = _sd_dirs(run)
    m2p: dict = {}
    for suite in SUITES:
        d = jl(dirs[suite] / f"{suite}-diff.json")
        m2p[suite] = [{"id": m["id"], "class": m["class"],
                       "reason": _m2_reason(suite, m)} for m in d["moves"]]
    m2p["rt136_direct_vs_138l"] = _rt136_direct(run)
    m2p["rt143_nogate"] = [dict(m, reason="224 glue -> Q2 (reply only)")
                           for m in _rt143_moves(run)]
    pred["m2"] = m2p
    changes, _bw, _df, _c = _probe_changes(run)
    import fable_decline224 as DEC
    s224 = set(DEC.NEW_SENTENCES224.values())
    fixed = fixed_texts()
    def why(v):
        if v["m"] in s224:
            return "224/224c: glued decline -> one sentence (still a decline)"
        if v["m"] in fixed:
            return "227/227b/227c identity sheet wins over 187/138l self route"
        return "name line (219/230c) answer from a stored USER name"
    pred["m6"] = {"reply_changes": {k: {"turn": v["turn"], "l": v["l"],
                                        "m": v["m"], "reason": why(v)}
                                    for k, v in changes.items()}}
    pred_path.write_text(json.dumps(pred, indent=1, ensure_ascii=False),
                         encoding="utf-8")
    print(json.dumps({s: len(v) for s, v in m2p.items()}),
          "m6 changes", len(changes))
    return 0


def _m2_reason(suite: str, m: dict) -> str:
    import fable_decline224 as DEC
    exc = jl(L_PRED)["L2_literal_bar_exceptions"]
    if m["id"] in exc.get(suite, []):
        return "222 inherited exception (label vs 138j; unchanged from 138l)"
    nr = str(m.get("new_reply", "")).strip()
    if nr in set(DEC.NEW_SENTENCES224.values()):
        return "224/224c: glued decline -> one sentence (verdict unchanged)"
    return "see pilot row"


def main() -> int:
    if sys.argv[1] == "--predict":
        return predict(Path(sys.argv[2]), Path(sys.argv[3]))
    run, pred_p, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    pred = jl(pred_p)
    marks = {"M1": m1(run), "M2": m2(run, pred), "M3": m3(run, pred), "M4": m4(run),
             "M5": m5(run), "M6": m6(run, pred)}
    for k, v in marks.items():
        print(k, "PASS" if v["pass"] else "FAIL",
              json.dumps({x: y for x, y in v.items() if x != "pass"})[:1200],
              flush=True)
    out.write_text(json.dumps(marks, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    return 0 if all(v["pass"] for v in marks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
