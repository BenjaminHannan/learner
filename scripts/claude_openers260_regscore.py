#!/usr/bin/env python3
"""Exp 260 scorer for the registered marks M2-M6 (M1 = claude_openers260_score.py panel).

  regscore <run_dir> <predicted_moves260.json> [out.json]

Bases are 138m's saved registered outputs (artifacts/claude-merge138m-20260922/run,
artifacts/claude-verify-20260922/138m); M6 latency uses a 138m arm run in the
same session by scripts/claude_260_runall.sh. Timing fields are never compared.
Helpers (_walk, _ghost, fixed_texts, _rt143_verdict) are imported read-only
from scripts/claude_138m_score.py.
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, "scripts")
import claude_138m_score as C  # noqa: E402 (read-only helpers)
import claude_openers260_rowdiff as RD  # noqa: E402

M_RUN = Path("artifacts/claude-merge138m-20260922/run")
VM = Path("artifacts/claude-verify-20260922/138m")
BENCH = ("bench132_4hop", "edit200", "new_121_4hop", "old_s2fresh_4hop")
PROBES = ("p3-dialogs", "p3c-restart2", "p3d-ghost", "v-dialogs", "v-supp")


def jl(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def moved(a, b):
    ua, ub = RD.units(RD.load(a)), RD.units(RD.load(b))
    return sorted(k for k in set(ua) | set(ub) if ua.get(k) != ub.get(k)), \
        len(ua), len(ub)


def m2(run, pred):
    pairs = {
        "rt136": (run / "sd136/rt136-rows.json", M_RUN / "sd136/rt136-rows.json"),
        "rt143_nogate": (run / "rt143nogate-n.json", M_RUN / "rt143nogate-m.json"),
        "sessions152": (run / "sd/sessions152-rows.json",
                        M_RUN / "sd/sessions152-rows.json"),
    }
    for b in BENCH:
        pairs[f"bench:{b}"] = (run / f"sd/bench-{b}-rows.jsonl",
                               M_RUN / f"sd/bench-{b}-rows.jsonl")
    want = pred["m2"]["moves"]
    wrows = pred["m2"].get("rows", {})
    res, ok = {}, True
    for name, (a, b) in pairs.items():
        mv, na, nb = moved(a, b)
        w = sorted(want.get(name, []))
        good = mv == w and na == nb and na > 0
        # each predicted moved row must be exactly the predicted row
        rows_bad = []
        if name in wrows:
            new = RD.load(a)
            new = {r["id"]: r for r in (new if isinstance(new, list)
                                        else new.get("rows", []))}
            for rid, fields in wrows[name].items():
                if any(new.get(rid, {}).get(k) != v for k, v in
                       fields.items()):
                    rows_bad.append(rid)
        good = good and not rows_bad
        res[name] = {"units": [na, nb], "moved": mv, "rows_bad": rows_bad,
                     "pass": good}
        ok &= good
    # suitediff labels vs the sealed bases equal 138m's own labels
    lab = {}
    for name, a, b in (
            ("rt136", run / "sd136/rt136-diff.json", M_RUN / "sd136/rt136-diff.json"),
            ("sessions152", run / "sd/sessions152-diff.json", None),
            ("bench", run / "sd/bench-diff.json", None)):
        da = jl(a)
        mine = [(m["id"], m["class"]) for m in da["moves"]]
        if b is None:
            good = da["n_moves"] == 0
            lab[name] = {"n_moves": da["n_moves"], "pass": good}
        else:
            db = jl(b)
            extra = [tuple(x) for x in
                     pred["m2"].get("label_moves", {}).get(name, [])]
            theirs = sorted([(m["id"], m["class"]) for m in db["moves"]]
                            + extra)
            mine = sorted(mine)
            good = mine == theirs
            lab[name] = {"n_moves": [da["n_moves"], db["n_moves"]],
                         "same_labels_as_138m": good, "pass": good}
        ok &= good
    res["labels"] = lab
    # rt143 verdict flips under rt143's own rule
    import fable_redteam143_run as R
    markers = jl(R.CASES_PATH)["abstain_markers"]
    base = {r["id"]: r for r in jl(M_RUN / "rt143nogate-m.json")}
    new = {r["id"]: r for r in jl(run / "rt143nogate-n.json")}
    flips = [i for i in base if C._rt143_verdict(base[i], markers)
             != C._rt143_verdict(new.get(i, {}), markers)]
    res["rt143_verdict_flips"] = flips
    ok &= not flips
    res["pass"] = ok
    return res


def m3(run, pred):
    diffs = []
    C._walk(jl(M_RUN / "smoke-m.json"), jl(run / "smoke-n.json"), "", diffs)
    allowed = set(pred["m3"]["allowed_fields"])
    bad = [d for d in diffs if d not in allowed]
    return {"differing_fields": diffs, "bad": bad, "pass": not bad}


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


def m4(run, pred):
    res, ok = {}, True
    p = pred["m4"]
    for name, base, new in (("probes", VM / "rows-138m.json", run / "vp-n.json"),
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
                     "new_writes": new_writes, "new_writes_unpredicted": nw_bad,
                     "pass": good}
        ok &= good
    res["pass"] = ok
    return res


def m5(run, pred):
    fixed = C.fixed_texts()
    want = pred["m5"]["reply_changes"]
    changes, bad, dup_fail, counts = {}, [], [], {}
    for p in PROBES:
        a = jl(M_RUN / "probe" / f"m-{p}.json")["rows"]
        b = jl(run / "probe" / f"n-{p}.json")["rows"]
        counts[p] = [len(a), len(b), sum(len(r["audits"]) for r in b)]
        for x, y in zip(a, b):
            for i, (ta, tb) in enumerate(zip(x["turns"], y["turns"])):
                if ta["reply"] != tb["reply"]:
                    changes[f"{p}:d{x['dialog']:02d}:t{i:02d}"] = {
                        "turn": tb["turn"], "m": tb["reply"],
                        "stored_end": y["stored"]}
                if ta["events"] != tb["events"] or ta["turn"] != tb["turn"]:
                    bad.append([p, y["dialog"], i])
            if len(x["turns"]) != len(y["turns"]) or sorted(
                    map(tuple, x["stored"])) != sorted(map(tuple, y["stored"])):
                bad.append([p, y["dialog"], "stored/len"])
            if not y.get("dup_ok_all", False):
                dup_fail.append([p, y["dialog"]])
    unpred = sorted(k for k in changes if k not in want)
    missing = sorted(k for k in want if k not in changes)
    ghosts = sorted(k for k, v in changes.items() if C._ghost(v, fixed))
    n_ok = all(c[0] == c[1] > 0 and c[2] > 0 for c in counts.values())
    ok = n_ok and not (unpred or missing or ghosts or bad or dup_fail)
    return {"counts": counts, "reply_changes": sorted(changes),
            "unpredicted": unpred, "predicted_not_seen": missing,
            "ghost_answers": ghosts, "bad_writes": bad,
            "failed_duplicate_checks": dup_fail, "pass": ok}


def m6(run, pred):
    lm, ln = [], []
    for i in (1, 2, 3):
        lm += jl(run / f"lat-m-{i}.json")["times_ms"]
        ln += jl(run / f"lat-n-{i}.json")["times_ms"]
    mm, mn = statistics.median(lm), statistics.median(ln)
    return {"median_138m_ms": round(mm, 3), "median_260_ms": round(mn, 3),
            "delta_ms": round(mn - mm, 3), "n": [len(lm), len(ln)],
            "pass": mn - mm <= pred["m6"]["max_delta_ms"]}


def main(argv):
    run, pred = Path(argv[1]), jl(argv[2])
    out = {}
    for name, fn in (("M2", m2), ("M3", m3), ("M4", m4), ("M5", m5),
                     ("M6", m6)):
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
