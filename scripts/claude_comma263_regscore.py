#!/usr/bin/env python3
"""Exp 263 scorer for the registered marks M2-M4 + verifier probes.

  regscore <run_dir> <predicted_moves263.json> [out.json]

M2: openpanel260 panel.jsonl run once on 263; every 260 figure (from 260's
    sealed run/panel-score260.json) equal or better, 0 new junk, control
    16/16 byte-identical to the writer's base138m.jsonl.
M3: frozen suites (rt136, rt143_nogate, sessions152, bench x4) run with the
    same commands/bases as 260's runall; every moved unit vs 260's saved
    rows must be exactly the predicted list (0 everywhere), suitediff move
    labels equal to 260's, 0 rt143 verdict flips vs 260.
M4: latency medians (260 vs 263, same session): median263 - median260 <= 3ms.
PROBES: 138m verifier probes on 263 vs 138m's saved rows: changed rows
    exactly the predicted list (260's 7 rows), stored changes exactly B15
    and D10, 0 unpredicted new writes.
Helpers are imported read-only from scripts/claude_138m_score.py,
scripts/claude_openers260_rowdiff.py and scripts/claude_openers260_score.py.
Only ids, counts and flags are printed (never panel item text).
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, "scripts")
import claude_138m_score as C  # noqa: E402 (read-only helpers)
import claude_openers260_rowdiff as RD  # noqa: E402 (read-only)
import claude_openers260_score as S260  # noqa: E402 (read-only)
import fable_redteam143_run as R143  # noqa: E402 (read-only)

M_RUN = Path("artifacts/claude-openers260-20260922/run")
N_RUN = Path("artifacts/claude-merge138m-20260922/run")
VM = Path("artifacts/claude-verify-20260922/138m")
PANEL260 = Path("artifacts/claude-openpanel260-20260922")
BENCH = ("bench132_4hop", "edit200", "new_121_4hop", "old_s2fresh_4hop")
PROBES = ("p3-dialogs", "p3c-restart2", "p3d-ghost", "v-dialogs", "v-supp")


def jl(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def jll(p):
    t = Path(p).read_text(encoding="utf-8")
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return [json.loads(x) for x in t.splitlines() if x.strip()]


def moved_units(a, b):
    ua, ub = RD.units(RD.load(a)), RD.units(RD.load(b))
    return sorted(k for k in set(ua) | set(ub) if ua.get(k) != ub.get(k))


def m2(run, pred):
    rows263 = jll(run / "openpanel263.jsonl")
    items, base, out = S260.score_panel(str(PANEL260), rows263,
                                        jll(M_RUN / "panel-260.jsonl"))
    got263 = {r["id"]: r for r in out["260"]}
    ref = jl(M_RUN / "panel-score260.json")
    ref263 = {r["id"]: r for r in ref["rows"]["260"]}
    fam_n, fam_260 = S260.tally(out["260"]), S260.tally(
        [ref263[i] for i in ref263])
    fams, ok = {}, True
    for f in fam_n:
        fams[f] = {"263": list(fam_n[f]), "260": list(fam_260[f])}
        if fam_n[f][0] < fam_260[f][0]:
            ok = False
    worse = sorted(i for i in got263 if ref263[i]["right"]
                   and not got263[i]["right"])
    junk_n = sorted(r["id"] for r in out["260"] if r["junk"])
    junk_260 = sorted(r["id"] for r in ref["rows"]["260"] if r["junk"])
    new_junk = sorted(set(junk_n) - set(junk_260))
    ctrl_ident = sum(1 for r in out["260"] if r["family"] == "control"
                     and r["identical"])
    ctrl_right = fam_n["control"][0]
    good = ok and not worse and not new_junk and ctrl_ident == 16 \
        and ctrl_right == 16
    return {"families": fams, "worse_than_260": worse,
            "junk_263": junk_n, "new_junk": new_junk,
            "control_identical": ctrl_ident, "pass": bool(good)}


def m3(run, pred):
    pairs = {
        "rt136": (run / "sd136/rt136-rows.json",
                  M_RUN / "sd136/rt136-rows.json"),
        "rt143_nogate": (run / "rt143nogate-n.json",
                         M_RUN / "rt143nogate-n.json"),
        "sessions152": (run / "sd/sessions152-rows.json",
                        M_RUN / "sd/sessions152-rows.json"),
    }
    for b in BENCH:
        pairs[f"bench:{b}"] = (run / f"sd/bench-{b}-rows.jsonl",
                               M_RUN / f"sd/bench-{b}-rows.jsonl")
    want = pred["m3"]["moves"]
    res, ok = {}, True
    for name, (a, b) in pairs.items():
        mv = moved_units(a, b)
        ua = RD.units(RD.load(a))
        good = mv == sorted(want.get(name, [])) and len(ua) > 0
        res[name] = {"moved": mv, "pass": good}
        ok &= good
    # suitediff move labels equal to 260's
    lab, lok = {}, True
    for name, a, b in (
            ("rt136", run / "sd136/rt136-diff.json",
             M_RUN / "sd136/rt136-diff.json"),
            ("sessions152", run / "sd/sessions152-diff.json",
             M_RUN / "sd/sessions152-diff.json"),
            ("bench", run / "sd/bench-diff.json",
             M_RUN / "sd/bench-diff.json")):
        ma = sorted((m["id"], m["class"]) for m in jl(a)["moves"])
        mb = sorted((m["id"], m["class"]) for m in jl(b)["moves"])
        good = ma == mb
        lab[name] = {"moves_263": ma, "moves_260": mb, "pass": good}
        lok &= good
    ok &= lok
    res["labels"] = lab
    # rt143 verdict flips 263 vs 260 under rt143's own rule
    markers = jl(R143.CASES_PATH)["abstain_markers"]
    base = {r["id"]: r for r in jl(M_RUN / "rt143nogate-n.json")}
    new = {r["id"]: r for r in jl(run / "rt143nogate-n.json")}
    flips = [i for i in base if C._rt143_verdict(base[i], markers)
             != C._rt143_verdict(new.get(i, {}), markers)]
    res["rt143_verdict_flips_vs_260"] = flips
    ok &= not flips
    res["pass"] = bool(ok)
    return res


def m4(run, pred):
    l0, l1 = [], []
    for i in (1, 2, 3):
        l0 += jl(run / f"lat-260-{i}.json")["times_ms"]
        l1 += jl(run / f"lat-263-{i}.json")["times_ms"]
    m0, m1 = statistics.median(l0), statistics.median(l1)
    return {"median_260_ms": round(m0, 3), "median_263_ms": round(m1, 3),
            "delta_ms": round(m1 - m0, 3), "n": [len(l0), len(l1)],
            "pass": bool(m1 - m0 <= pred["m4"]["max_delta_ms"])}


def _probe_diff(base_rows, new_rows):
    a = {x["id"]: x for x in base_rows}
    b = {x["id"]: x for x in new_rows}
    rows, stored = {}, {}
    for i in a:
        for k, (ra, rb) in enumerate(zip(a[i]["rows"], b[i]["rows"])):
            if ra != rb:
                rows[f"{i}:t{k}"] = {"turn": rb["turn"], "reply": rb["reply"],
                                     "ev": rb["ev"], "triples": rb["triples"],
                                     "reply_138m": ra["reply"],
                                     "ev_138m": ra["ev"]}
        if len(a[i]["rows"]) != len(b[i]["rows"]):
            rows[f"{i}:len"] = {"n": [len(a[i]["rows"]), len(b[i]["rows"])]}
        if a[i]["stored"] != b[i]["stored"]:
            stored[i] = b[i]["stored"]
    return rows, stored, sorted(set(a) ^ set(b))


def probes(run, pred):
    res, ok = {}, True
    p = pred["probes"]
    for name, base, new in (("probes", VM / "rows-138m.json",
                             run / "vp-n.json"),
                            ("probes_supp", VM / "supp-rows-138m.json",
                             run / "vs-n.json")):
        rows, stored, idset = _probe_diff(jl(base), jl(new))
        want = p[name]["rows"]
        unpred = sorted(k for k in rows if k not in want)
        wrong = sorted(k for k in rows if k in want and any(
            rows[k][f] != want[k][f] for f in ("turn", "reply", "ev",
                                               "triples")))
        missing = sorted(k for k in want if k not in rows)
        wst = p[name]["stored"]
        st_bad = sorted(i for i in set(stored) | set(wst)
                        if stored.get(i) != (wst.get(i) or {}).get("stored"))
        new_writes = sorted(k for k, v in rows.items()
                            if v.get("ev", 0) > v.get("ev_138m", 0))
        nw_bad = [k for k in new_writes if k not in p["allowed_new_writes"]]
        good = not (unpred or wrong or missing or st_bad or idset or nw_bad)
        res[name] = {"changed_rows": sorted(rows), "unpredicted": unpred,
                     "predicted_wrong": wrong, "predicted_not_seen": missing,
                     "stored_bad": st_bad, "id_mismatch": idset,
                     "new_writes": new_writes,
                     "new_writes_unpredicted": nw_bad, "pass": good}
        ok &= good
    res["pass"] = ok
    return res


def main(argv):
    run, pred = Path(argv[1]), jl(argv[2])
    only = argv[4] if len(argv) > 4 else None
    out = {}
    for name, fn in (("M2", m2), ("M3", m3), ("M4", m4), ("PROBES", probes)):
        if only is not None and name != only:
            continue
        try:
            out[name] = fn(run, pred)
        except Exception as e:  # noqa: BLE001
            out[name] = {"error": f"{type(e).__name__}: {e}", "pass": False}
        print(name, "PASS" if out[name]["pass"] else "FAIL",
              json.dumps(out[name], default=str)[:1500])
    if len(argv) > 3:
        Path(argv[3]).write_text(json.dumps(out, indent=1, default=str),
                                 encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
