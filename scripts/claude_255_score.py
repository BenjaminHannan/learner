#!/usr/bin/env python3
"""Exp 255 scorer for M2, M4, M5, M6, M7 (M1 and M3 are graded by others).

Run dir layout (scripts/claude_255_runall.sh):
  sd255/                 suitediff218 rows, 255 vs base138m-rows
  rt143nogate-255.json   verifier-method rt143 rows on 255
  vp/{m,255}-{probes,probes-supp}.json   verifier probes, same session
  smoke-255.json         sleep smoke on 255
  probe/{m,255}-<p>.json restart / verifier dialogs, same session
  lat-{m,255}-{1,2,3}.json  latency, alternating processes

Every changed reply must be EXACTLY the 138m reply with each fixed line
passed through claude_fix255_text.rewrite255 ("explained"); anything else
is unexplained. M4 labels are mechanical, fixed before the run: an
explained change is labelled "same meaning (template <id>)"; an
unexplained change is labelled "worse (unexplained)". (The director may
re-label; this scorer never grades wording.)

usage: claude_255_score.py <run_dir> <predicted_moves255.json> <out.json>
       claude_255_score.py --predict <run_dir> <out_pred.json>
"""
import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import claude_fix255_text as T  # noqa: E402

BASE138M = ROOT / "artifacts" / "claude-merge138m-20260922" / "run"
BASE_ROWS = ROOT / "artifacts" / "claude-fixedtext255-20260922" / \
    "base138m-rows"
VP = ("probes", "probes-supp")
PROBES = ("p3-dialogs", "p3c-restart2", "p3d-ghost", "v-dialogs", "v-supp")


def jl(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def explained(old, new):
    if not isinstance(old, str) or not isinstance(new, str):
        return None
    out, tids = [], []
    for line in old.split("\n"):
        n, t = T.rewrite255(line)
        out.append(n)
        if t:
            tids.append(t)
    if "\n".join(out) == new and tids:
        return tids
    return None


# ------------------------------------------------------------------- M2
def m2(run: Path, pred: dict, pred_path: str) -> dict:
    out = run / "m2-check.json"
    r1 = subprocess.run([sys.executable, "-B",
                         str(ROOT / "scripts" / "claude_255_m2check.py"),
                         str(BASE_ROWS), str(run / "sd255"), str(out),
                         "--pred", pred_path],
                        capture_output=True, text=True)
    out2 = run / "m2-nogate-check.json"
    r2 = subprocess.run([sys.executable, "-B",
                         str(ROOT / "scripts" / "claude_255_m2check.py"),
                         "--nogate", str(BASE138M / "rt143nogate-m.json"),
                         str(run / "rt143nogate-255.json"), str(out2)],
                        capture_output=True, text=True)
    a, b = jl(out), jl(out2)
    ng_ids = sorted(m["id"] for m in b["moves"])
    ng_ok = ng_ids == sorted(pred["m2_nogate"])
    summ = jl(run / "sd255" / "SUITEDIFF218-SUMMARY.json")
    return {"suitediff_summary": summ["summary_lines"], "gate": summ["gate"],
            "skipped": summ.get("skipped"),
            "counts": a["counts"], "reply_only_moves": a["n_moves"],
            "unexplained": a["n_unexplained"],
            "matches_prediction": a.get("matches_prediction"),
            "missing_predicted": a.get("missing_predicted"),
            "unpredicted": a.get("unpredicted"),
            "nogate_moves": b["n_moves"], "nogate_unexplained":
                b["n_unexplained"], "nogate_matches_prediction": ng_ok,
            "stdout": r1.stdout.strip().splitlines()[-2:] +
                      r2.stdout.strip().splitlines()[-1:],
            "pass": (r1.returncode == 0 and r2.returncode == 0 and ng_ok
                     and summ["gate"] == "GATE: clean" and not summ.get("skipped")
                     and len(summ["suites"]) == 4
                     and a.get("matches_prediction") is True)}


# ------------------------------------------------------------------- M4
def vp_changes(run: Path):
    changes, store = {}, []
    for p in VP:
        a, b = jl(run / "vp" / f"m-{p}.json"), jl(run / "vp" / f"255-{p}.json")
        if [x["id"] for x in a] != [y["id"] for y in b]:
            store.append({"probe": p, "problem": "dialog ids differ"})
        for x, y in zip(a, b):
            if x["stored"] != y["stored"]:
                store.append({"probe": p, "id": x["id"], "stored_m":
                              x["stored"], "stored_255": y["stored"]})
            k = 0
            for tx, ty in zip(x["rows"], y["rows"]):
                if tx.get("restart"):
                    continue
                if (tx.get("triples") != ty.get("triples")
                        or tx.get("ev") != ty.get("ev")):
                    store.append({"probe": p, "id": x["id"], "turn": k})
                if tx.get("reply") != ty.get("reply"):
                    tids = explained(tx.get("reply"), ty.get("reply"))
                    changes[f"{p}:{x['id']}:t{k:02d}"] = {
                        "turn": tx.get("turn"), "m": tx.get("reply"),
                        "255": ty.get("reply"), "templates": tids or [],
                        "label": (f"same meaning (template "
                                  f"{', '.join(tids)})" if tids else
                                  "worse (unexplained)")}
                k += 1
    return changes, store


def m4(run: Path, pred: dict) -> dict:
    changes, store = vp_changes(run)
    flagged = set(pred.get("m4_flagged", []))
    for k, v in changes.items():
        if k in flagged and v["templates"]:
            v["label"] = ("flagged: possibly worse on meaning, director "
                          "rules (template " + ", ".join(v["templates"]) +
                          ")")
    worse = sorted(k for k, v in changes.items() if v["label"].startswith(
        "worse"))
    want = set(pred["m4"])
    unpred = sorted(set(changes) - want)
    missing = sorted(want - set(changes))
    labels = {}
    for v in changes.values():
        labels[v["label"].split(" (")[0]] = labels.get(
            v["label"].split(" (")[0], 0) + 1
    return {"changed_replies": len(changes), "labels": labels,
            "flagged": sorted(k for k in changes if k in flagged),
            "worse": worse, "store_changes": store, "unpredicted": unpred,
            "predicted_not_seen": missing, "changes": changes,
            "pass": not worse and not store and not unpred and not missing}


# ------------------------------------------------------------------- M5
def _walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            _walk(a.get(k), b.get(k), f"{path}.{k}", out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            _walk(x, y, f"{path}[{i}]", out)
    elif a != b:
        out.append(path)


def m5(run: Path) -> dict:
    diffs = []
    _walk(jl(BASE138M / "smoke-m.json"), jl(run / "smoke-255.json"), "",
          diffs)
    allowed = {".agent", ".config", ".label", ".seconds", ".root", ".report"}
    bad = [d for d in diffs if d not in allowed]
    return {"differing_fields": diffs, "bad": bad, "pass": not bad}


# ------------------------------------------------------------------- M6
def probe_changes(run: Path, base_prefix: str, base_dir: Path):
    changes, bad, dup_fail, counts = {}, [], [], {}
    for p in PROBES:
        a = jl(base_dir / f"{base_prefix}-{p}.json")["rows"]
        b = jl(run / "probe" / f"255-{p}.json")["rows"]
        counts[p] = {"dialogs_m": len(a), "dialogs_255": len(b),
                     "audits_255": sum(len(r["audits"]) for r in b)}
        for x, y in zip(a, b):
            for i, (ta, tb) in enumerate(zip(x["turns"], y["turns"])):
                if ta["reply"] != tb["reply"]:
                    tids = explained(ta["reply"], tb["reply"])
                    changes[f"{p}:d{x['dialog']:02d}:t{i:02d}"] = {
                        "turn": tb["turn"], "m": ta["reply"],
                        "255": tb["reply"], "templates": tids or [],
                        "ghost": tids is None}
                if ta["events"] != tb["events"] or ta["turn"] != tb["turn"]:
                    bad.append({"probe": p, "dialog": y["dialog"], "turn": i})
            if len(x["turns"]) != len(y["turns"]):
                bad.append({"probe": p, "dialog": y["dialog"],
                            "turn_count": [len(x["turns"]), len(y["turns"])]})
            if sorted(map(tuple, x["stored"])) != sorted(
                    map(tuple, y["stored"])):
                bad.append({"probe": p, "dialog": y["dialog"],
                            "stored_m": x["stored"], "stored_255":
                                y["stored"]})
            if not y.get("dup_ok_all", False):
                dup_fail.append({"probe": p, "dialog": y["dialog"]})
        if len(a) != len(b):
            bad.append({"probe": p, "dialog_count": [len(a), len(b)]})
    return changes, bad, dup_fail, counts


def m6(run: Path, pred: dict) -> dict:
    res = {}
    ok = True
    for label, prefix, bdir in (("vs_138m_saved", "m", BASE138M / "probe"),
                                ("vs_138m_same_session", "m",
                                 run / "probe")):
        changes, bad, dup_fail, counts = probe_changes(run, prefix, bdir)
        want = pred["m6"]
        unpred = sorted(k for k in changes if k not in want)
        wrong = sorted(k for k in changes if k in want
                       and changes[k]["255"] != want[k])
        missing = sorted(k for k in want if k not in changes)
        ghosts = sorted(k for k, v in changes.items() if v["ghost"])
        n_ok = all(c["dialogs_m"] == c["dialogs_255"] > 0
                   and c["audits_255"] > 0 for c in counts.values())
        p = (n_ok and not unpred and not wrong and not missing and not ghosts
             and not bad and not dup_fail)
        ok = ok and p
        res[label] = {"counts": counts, "reply_changes": len(changes),
                      "unpredicted": unpred, "predicted_wrong": wrong,
                      "predicted_not_seen": missing, "ghost_answers": ghosts,
                      "bad_writes": bad, "failed_duplicate_checks": dup_fail,
                      "changes": changes, "pass": p}
    res["pass"] = ok
    return res


# ------------------------------------------------------------------- M7
def m7(run: Path) -> dict:
    lm, ln = [], []
    for i in (1, 2, 3):
        lm += jl(run / f"lat-m-{i}.json")["times_ms"]
        ln += jl(run / f"lat-255-{i}.json")["times_ms"]
    mm, mn = statistics.median(lm), statistics.median(ln)
    return {"median_138m_ms": round(mm, 3), "median_255_ms": round(mn, 3),
            "delta_ms": round(mn - mm, 3), "n_138m": len(lm),
            "n_255": len(ln), "pass": mn - mm <= 2.0}


def predict(run: Path, out: Path) -> int:
    changes4, _ = vp_changes(run)
    changes6, _, _, _ = probe_changes(run, "m", run / "probe")
    ng = jl(run / "m2-nogate-check.json") if (
        run / "m2-nogate-check.json").exists() else None
    m2c = jl(run / "m2-check.json") if (run / "m2-check.json").exists() \
        else None
    pred = {"moves": sorted(f"{m['suite']}/{m['id']}" for m in m2c["moves"])
            if m2c else [],
            "m4": sorted(changes4),
            "m6": {k: v["255"] for k, v in sorted(changes6.items())},
            "m2_nogate": sorted(m["id"] for m in ng["moves"]) if ng else []}
    out.write_text(json.dumps(pred, indent=1, ensure_ascii=False))
    print(f"m2={len(pred['moves'])} m4={len(pred['m4'])} m6={len(pred['m6'])} "
          f"m2_nogate={len(pred['m2_nogate'])} -> {out}")
    return 0


def main(argv) -> int:
    if argv[0] == "--predict":
        return predict(Path(argv[1]), Path(argv[2]))
    run, pred, out = Path(argv[0]), jl(argv[1]), Path(argv[2])
    res = {"M2": m2(run, pred, argv[1]), "M4": m4(run, pred), "M5": m5(run),
           "M6": m6(run, pred), "M7": m7(run)}
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    for k, v in res.items():
        brief = {kk: vv for kk, vv in v.items()
                 if kk not in ("changes", "counts", "vs_138m_saved",
                               "vs_138m_same_session")}
        print(k, "PASS" if v["pass"] else "FAIL",
              json.dumps(brief, ensure_ascii=False)[:900])
        for sub in ("vs_138m_saved", "vs_138m_same_session"):
            if sub in v:
                s = {kk: vv for kk, vv in v[sub].items()
                     if kk not in ("changes", "counts")}
                print("  ", sub, json.dumps(s)[:600])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
