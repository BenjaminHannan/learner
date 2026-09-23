#!/usr/bin/env python3
"""Merge 138nb -- scorer for marks M2-M5 (M2's judge is in
scripts/claude_138nb_m2.py). Reads only row files; runs nothing.

Run dir layout (all produced by scripts/claude_138nb_runall.sh):
  m2-judge.json             M2 (nb vs n on 138n's 720 dev/case files)
  sd/                 fable_suitediff218 on 138nb vs 138n's saved rows
                      (--base-dir artifacts/claude-merge138n-20260922/run/sd)
  sd136/              fable_suitediff218 --only rt136 vs 138j's sealed rows
                      (as 138n did); the scorer also compares every row
                      directly with 138n's saved run/sd136/rt136-rows.json
  rt143nogate-nb.json claude_138l_rt143nogate.py on 138nb (base: 138n's
                      saved run/rt143nogate-n.json)
  smoke-nb.json       fable_sleepsmoke206.py (base: 138n's saved smoke-n.json)
  bench{1,2,3}/       fable_suitediff218 --only bench, three back-to-back runs
  lat-{n,nb}-{1,2,3}.json claude_merge138k_latency.py, alternating processes
  probe/{n,nb}-<file>.json claude_merge138k_probe.py (138n fresh vs 138nb) on
                      138n's M6 files (138j p3-dialogs, p3c-restart2,
                      p3d-ghost; 138k v-dialogs, v-supp) + the 138m verifier
                      probes (v138m-probes-dialogs, v138m-probes-supp-dialogs)

M3 bar: the (id, class) move set of every suite equals the predicted list
exactly, each predicted new reply matches, and no new WRONG / WRONG-WRITE /
junk write / lost OK. rt136 is also compared row-by-row with 138n's saved
rows. Probes bar: 0 ghost answers, 0 failed duplicate checks, events +
final stored triples equal to 138n's except predicted changes, every reply
change predicted exactly.
M5 bar: median(138nb) - median(138n) <= +2 ms.

usage: claude_138nb_score.py <run_dir> <predicted_moves138nb.json> <out.json>
       claude_138nb_score.py --predict <pilot_run_dir> <pred.json>
           (writes the m3 sections into pred.json from a pilot run dir)
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
N_RUN = ROOT / "artifacts/claude-merge138n-20260922/run"
BENCH_FILES = ("bench132_4hop", "edit200", "new_121_4hop", "old_s2fresh_4hop")
SUITES = ("rt136", "sessions152", "bench", "marks123")
PROBES = ("p3-dialogs", "p3c-restart2", "p3d-ghost", "v-dialogs", "v-supp",
          "v138m-probes-dialogs", "v138m-probes-supp-dialogs")
OLD_PROBES = PROBES[:5]
NAME_PREFIXES = ("Yes. Your name is ", "Your name is ", "No. Your name is ")
BAD_CLASSES = ("new WRONG", "new WRONG-WRITE", "new junk write", "lost OK")


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def jsonl(p: Path) -> dict:
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def fixed_texts() -> set[str]:
    """Replies that state no notebook fact (224 sentences, 234 fixed reply,
    227c identity sheet / name-check / rename, plus the 138nb label)."""
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
    base = {r["id"]: r for r in jl(N_RUN / "rt143nogate-n.json")}
    new = {r["id"]: r for r in jl(run / "rt143nogate-nb.json")}
    moves = []
    for cid, r in base.items():
        f = [k for k in ("teach_replies", "triples", "reply")
             if r[k] != new[cid][k]]
        if f:
            moves.append({"id": cid, "fields": f, "base_reply": r["reply"],
                          "new_reply": new[cid]["reply"],
                          "base_triples": r["triples"],
                          "new_triples": new[cid]["triples"],
                          "new_teach": new[cid]["teach_replies"]})
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
    a = jsonl(N_RUN / "sd136" / "rt136-rows.json")
    b = jsonl(run / "sd136" / "rt136-rows.json")
    return sorted(i for i in a if any(a[i][k] != b[i][k] for k in keys))


def m2(run: Path) -> dict:
    j = jl(run / "m2-judge.json")
    n_cases = sum(v["n"] for v in j["pieces"].values())
    n_moved = sum(v["moved"] for v in j["pieces"].values())
    return {"n_cases": n_cases, "n_moved_vs_n": n_moved,
            "judge_counts": j["counts"], "pass": bool(j["pass"])}


def m3(run: Path, pred: dict) -> dict:
    res: dict = {}
    ok_all = True
    dirs = _sd_dirs(run)
    skipped = [s for s in SUITES if not (dirs[s] / f"{s}-diff.json").exists()]
    res["suites_skipped"] = skipped
    if skipped:
        res["pass"] = False
        return res
    for suite in SUITES:
        d = jl(dirs[suite] / f"{suite}-diff.json")
        got = {(m["id"], m["class"]) for m in d["moves"]}
        pm = pred["m3"][suite]
        want = {(m["id"], m["class"]) for m in pm}
        unpred = sorted(got - want)
        missing = sorted(want - got)
        preply = {(m["id"], m["class"]): m.get("new_reply") for m in pm}
        wrong = sorted(m["id"] for m in d["moves"]
                       if (m["id"], m["class"]) in preply
                       and preply[(m["id"], m["class"])]
                       != m.get("new_reply"))
        ex = set(pred["m3"].get("allowed_bad", {}).get(suite, {}))
        bad_new = sorted(m["id"] for m in d["moves"]
                         if m["class"] in BAD_CLASSES and m["id"] not in ex)
        ok = not unpred and not missing and not wrong and not bad_new
        res[suite] = {"n_moves": len(got),
                      "class_counts": d.get("class_counts"),
                      "unpredicted": unpred, "predicted_not_seen": missing,
                      "predicted_reply_wrong": wrong,
                      "new_bad": bad_new, "pass": ok}
        ok_all &= ok
    moved = _rt136_direct(run)
    n_b = len(jsonl(N_RUN / "sd136" / "rt136-rows.json"))
    n_n = len(jsonl(run / "sd136" / "rt136-rows.json"))
    res["rt136_direct_vs_138n_rows"] = {
        "moved": moved, "n": n_n,
        "pass": moved == pred["m3"]["rt136_direct_vs_138n"] and n_b == n_n}
    ok_all &= res["rt136_direct_vs_138n_rows"]["pass"]
    import fable_redteam143_run as R
    markers = jl(R.CASES_PATH)["abstain_markers"]
    moves = _rt143_moves(run)
    want = {m["id"]: m for m in pred["m3"]["rt143_nogate"]}
    rt_bad = [m["id"] for m in moves if m["id"] not in want
              or m["fields"] != want[m["id"]]["fields"]
              or m["new_reply"] != want[m["id"]]["new_reply"]
              or m["new_triples"] != want[m["id"]]["new_triples"]]
    rt_missing = sorted(set(want) - {m["id"] for m in moves})
    base = {r["id"]: r for r in jl(N_RUN / "rt143nogate-n.json")}
    new = {r["id"]: r for r in jl(run / "rt143nogate-nb.json")}
    vflips = [{"id": i, "n": _rt143_verdict(base[i], markers),
               "nb": _rt143_verdict(new[i], markers)} for i in base
              if _rt143_verdict(base[i], markers)
              != _rt143_verdict(new[i], markers)]
    want_flips = pred["m3"].get("rt143_verdict_flips", [])
    rt_ok = (not rt_bad and not rt_missing and len(new) == len(base)
             and vflips == want_flips
             and not [f for f in vflips if f["nb"] == "WRONG-ANSWER"])
    res["rt143_nogate"] = {"n": len(base), "n_moves": len(moves),
                           "bad": rt_bad, "predicted_not_seen": rt_missing,
                           "verdict_flips": vflips, "pass": rt_ok}
    ok_all &= rt_ok
    pr = m3probes(run, pred)
    res["probes"] = pr
    ok_all &= pr["pass"]
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


def m4(run: Path) -> dict:
    diffs = []
    _walk(jl(N_RUN / "smoke-n.json"), jl(run / "smoke-nb.json"), "", diffs)
    allowed = {".agent", ".config", ".label", ".seconds", ".root", ".report"}
    bad = [d for d in diffs if d not in allowed]
    same = []
    for f in BENCH_FILES:
        blobs = [(run / f"bench{i}" / f"bench-{f}-rows.jsonl").read_bytes()
                 for i in (1, 2, 3)]
        same.append(f if blobs[0] == blobs[1] == blobs[2] else None)
    n = sum(1 for x in same if x)
    ok = (not bad) and n == 4
    return {"differing_fields": diffs, "bad": bad,
            "identical_files": f"{n}/4", "pass": ok}


def m5(run: Path) -> dict:
    ln_, lnb = [], []
    for i in (1, 2, 3):
        ln_ += jl(run / f"lat-n-{i}.json")["times_ms"]
        lnb += jl(run / f"lat-nb-{i}.json")["times_ms"]
    mn, mnb = statistics.median(ln_), statistics.median(lnb)
    return {"median_n_ms": round(mn, 3), "median_nb_ms": round(mnb, 3),
            "delta_ms": round(mnb - mn, 3), "n_n": len(ln_),
            "n_nb": len(lnb), "pass": mnb - mn <= 2.0}


def _probe_changes(run: Path):
    changes, writes, dup_fail, counts = {}, {}, [], {}
    for p in PROBES:
        a = jl(run / "probe" / f"n-{p}.json")["rows"]
        b = jl(run / "probe" / f"nb-{p}.json")["rows"]
        counts[p] = {"dialogs_n": len(a), "dialogs_nb": len(b),
                     "audits_nb": sum(len(r["audits"]) for r in b)}
        for x, y in zip(a, b):
            dk = f"{p}:d{x['dialog']:02d}"
            for i, (ta, tb) in enumerate(zip(x["turns"], y["turns"])):
                if ta["reply"] != tb["reply"]:
                    changes[f"{dk}:t{i:02d}"] = {
                        "turn": tb["turn"], "n": ta["reply"],
                        "nb": tb["reply"], "stored_end": y["stored"]}
                if ta["events"] != tb["events"] or ta["turn"] != tb["turn"]:
                    writes[f"{dk}:t{i:02d}"] = {
                        "turn": tb["turn"], "events_n": ta["events"],
                        "events_nb": tb["events"]}
            if len(x["turns"]) != len(y["turns"]):
                writes[f"{dk}:turn_count"] = [len(x["turns"]),
                                              len(y["turns"])]
            if sorted(map(tuple, x["stored"])) != sorted(map(tuple,
                                                            y["stored"])):
                writes[f"{dk}:stored"] = {"n": sorted(x["stored"]),
                                          "nb": sorted(y["stored"])}
            if not y.get("dup_ok_all", False):
                dup_fail.append(dk)
    return changes, writes, dup_fail, counts


def _n_vs_saved(run: Path) -> list[str]:
    """Fresh 138n rows vs 138n's own saved M6 rows (the old five files):
    the base arm reproduces its registered run."""
    bad = []
    for p in OLD_PROBES:
        a = jl(N_RUN / "probe" / f"n-{p}.json")["rows"]
        b = jl(run / "probe" / f"n-{p}.json")["rows"]
        if len(a) != len(b):
            bad.append(f"{p}:count")
            continue
        for x, y in zip(a, b):
            if x["turns"] != y["turns"] or x["stored"] != y["stored"]:
                bad.append(f"{p}:d{x['dialog']:02d}")
    return bad


def _ghost(ch: dict, fixed: set[str]) -> bool:
    """A changed reply that states something not in the notebook.

    Every answer sentence ("S's R is V.", possibly several joined by
    spaces, or "Your R is V.") must name a value (or subject) from the
    final stored triples of that dialog; anything else (clarify /
    no-save / abstain / fixed text) must name no new value.
    """
    import claude_fix138nb_label as LB
    import re
    r = ch["nb"]
    base = r[:-len(LB.LABEL138NB)].rstrip() if r.endswith(LB.LABEL138NB) \
        else r
    if base in fixed or r in fixed:
        return False
    for pre in NAME_PREFIXES:
        if base.startswith(pre):
            name = base[len(pre):].rstrip(".")
            users = {t[2] for t in ch["stored_end"]
                     if t[0] == "USER" and t[1] == "name"}
            return name not in users
    vals = {str(t[2]) for t in ch["stored_end"]} | \
           {str(t[0]) for t in ch["stored_end"]}
    sents = [s.strip() for s in base.split(". ") if s.strip()]
    if not sents:
        return False
    any_answer = False
    for s in sents:
        s = s.rstrip(".")
        m = re.match(r"^(.+?)'s? (.+?) is (.+?)$", s)
        if m and not s.startswith(("Saved:", "Updated:", "I ")):
            any_answer = True
            if m.group(3) not in vals:
                return True
    if any_answer:
        return False
    return False


def m3probes(run: Path, pred: dict) -> dict:
    changes, writes, dup_fail, counts = _probe_changes(run)
    fixed = fixed_texts()
    want = pred["m3"]["probes"]["reply_changes"]
    unpred = sorted(k for k in changes if k not in want)
    wrong = sorted(k for k in changes
                   if k in want and changes[k]["nb"] != want[k]["nb"])
    missing = sorted(k for k in want if k not in changes)
    ghosts = sorted(k for k, v in changes.items() if _ghost(v, fixed))
    wwant = pred["m3"]["probes"].get("write_changes", {})
    bad_writes = sorted(k for k in writes
                        if k not in wwant or writes[k] != wwant[k]["got"])
    w_missing = sorted(k for k in wwant if k not in writes)
    n_saved_bad = _n_vs_saved(run)
    n_ok = all(c["dialogs_n"] == c["dialogs_nb"] > 0 and c["audits_nb"] > 0
               for c in counts.values())
    ok = (n_ok and not unpred and not wrong and not missing and not ghosts
          and not bad_writes and not w_missing and not dup_fail
          and not n_saved_bad)
    return {"counts": counts, "reply_changes": len(changes),
            "write_changes": len(writes),
            "unpredicted": unpred, "predicted_wrong": wrong,
            "predicted_not_seen": missing, "ghost_answers": ghosts,
            "bad_writes": bad_writes, "write_changes_not_seen": w_missing,
            "failed_duplicate_checks": dup_fail,
            "fresh_138n_vs_saved_138n_rows": n_saved_bad, "pass": ok}


def predict(run: Path, pred_path: Path) -> int:
    """Write the raw m2/m3 sections from a PILOT run dir (every move by id,
    with its exact new record)."""
    pred = jl(pred_path) if pred_path.exists() else {}
    m2j = jl(run / "m2-judge.json")
    m2p: dict = {}
    for piece, v in m2j["pieces"].items():
        m2p[piece] = {}
        for mv in v["moves"]:
            cid = mv["id"].split("/", 1)[1]
            nb = {r["id"]: r for r in jl(run / "m2" / f"{piece}-nb.json")}
            m2p[piece][cid] = {"expect_nb": {"replies": nb[cid]["replies"],
                                             "active": nb[cid]["active"],
                                             "all": nb[cid]["all"]},
                               "n_replies": mv["n_replies"],
                               "nb_replies": mv["nb_replies"]}
    pred["m2"] = m2p
    dirs = _sd_dirs(run)
    m3p: dict = {}
    for suite in SUITES:
        d = jl(dirs[suite] / f"{suite}-diff.json")
        m3p[suite] = [{"id": m["id"], "class": m["class"],
                       "base_reply": m.get("base_reply"),
                       "new_reply": m.get("new_reply"),
                       "detail": m.get("detail")} for m in d["moves"]]
    m3p["rt136_direct_vs_138n"] = _rt136_direct(run)
    m3p["rt143_nogate"] = _rt143_moves(run)
    import fable_redteam143_run as R
    markers = jl(R.CASES_PATH)["abstain_markers"]
    base = {r["id"]: r for r in jl(N_RUN / "rt143nogate-n.json")}
    new = {r["id"]: r for r in jl(run / "rt143nogate-nb.json")}
    m3p["rt143_verdict_flips"] = [
        {"id": i, "n": _rt143_verdict(base[i], markers),
         "nb": _rt143_verdict(new[i], markers)} for i in base
        if _rt143_verdict(base[i], markers) != _rt143_verdict(new[i],
                                                              markers)]
    changes, writes, _df, _c = _probe_changes(run)
    m3p["probes"] = {"reply_changes": {k: {"turn": v["turn"], "n": v["n"],
                                           "nb": v["nb"]}
                                       for k, v in changes.items()},
                     "write_changes": {k: {"got": v} for k, v in writes.items()}}
    pred["m3"] = m3p
    pred_path.write_text(json.dumps(pred, indent=1, ensure_ascii=False),
                         encoding="utf-8")
    print(json.dumps({s: len(v) for s, v in m3p.items()
                      if isinstance(v, list)}),
          "probes changes", len(changes), "writes", len(writes))
    return 0


def main() -> int:
    if sys.argv[1] == "--predict":
        return predict(Path(sys.argv[2]), Path(sys.argv[3]))
    run, pred_p, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    pred = jl(pred_p)
    marks = {"M2": m2(run), "M3": m3(run, pred), "M4": m4(run),
             "M5": m5(run)}
    for k, v in marks.items():
        print(k, "PASS" if v["pass"] else "FAIL",
              json.dumps({x: y for x, y in v.items() if x != "pass"},
                         ensure_ascii=False)[:1500], flush=True)
    out.write_text(json.dumps(marks, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    return 0 if all(v["pass"] for v in marks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
