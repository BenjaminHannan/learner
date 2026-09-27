"""rv-393 counter (thought-memory thread). Written before any real result, from PLAN.md's sealed marks; tried on smoke/.

Reads the run folder only (measure-*, noharm-*, train-*, info-*). Recounts every mark from the rows files and checks the
recount against the summaries. Prints one JSON report and the verdict. Standard library only; no torch.
usage: python3 count.py <run dir> [--nets-sha <NETS-358i2.sha256.txt>] [--out report.json]
"""
import argparse
import bisect
import json
import random
from collections import defaultdict
from pathlib import Path

MARK_SET, REPORT_SET = "pp-grids7", "p-grids7"
ARMS = ["orig", "pencil", "clean"]
TESTS = ["grids6", "grids7", "sums6"]
MIN_WRONG = 30                      # "a net counts" = at least 30 wrong marks judged in its PENCIL arm
WRONG_MIN, RIGHT_MAX, BEAT_CLEAN = 0.60, 0.10, 0.20
AUC_MARGIN, HARM_FLOOR = 0.05, -5
WRONG_FLOOR = 0.30                  # PROVED WRONG clause 1
STEPS = 3000
BOOT, BOOT_SEED = 1000, 0


def auc(pos, neg):
    """P(a dead state's value > a live state's), ties count half (as claude_rv391_critic.auc, unrounded)."""
    if not pos or not neg:
        return None
    ns = sorted(neg)
    tot = 0.0
    for x in pos:
        lo, hi = bisect.bisect_left(ns, x), bisect.bisect_right(ns, x)
        tot += lo + 0.5 * (hi - lo)
    return tot / (len(pos) * len(ns))


def rate(x, n):
    return None if not n else x / n


def mean(xs):
    xs = [x for x in xs if x is not None]
    return None if not xs else sum(xs) / len(xs)


def r4(x):
    return None if x is None else round(x, 4)


def recount(rows, name):
    st = [r for r in rows if r["row"] == "state" and r["set"] == name]
    mk = [r for r in rows if r["row"] == "mark" and r["set"] == name]
    wj, rj = [m for m in mk if not m["right"]], [m for m in mk if m["right"]]
    dead, live = [s for s in st if s["dead"]], [s for s in st if not s["dead"]]
    return {"states": len(st), "dead": len(dead),
            "auc": auc([s["score"] for s in dead], [s["score"] for s in live]),
            "auc_count_only": auc([float(s["k"]) for s in dead], [float(s["k"]) for s in live]),
            "wrong_judged": len(wj), "wrong_over": sum(m["over"] for m in wj),
            "wrong_over_rate": rate(sum(m["over"] for m in wj), len(wj)),
            "right_judged": len(rj), "right_over": sum(m["over"] for m in rj),
            "right_over_rate": rate(sum(m["over"] for m in rj), len(rj)),
            "puzzles_with_states": len({s["item"] for s in st})}


def agree(mine, theirs, problems, where):
    for k in ["states", "dead", "wrong_judged", "wrong_over", "right_judged", "right_over"]:
        if mine[k] != theirs[k]:
            problems.append(f"{where} {k}: rows give {mine[k]}, summary says {theirs[k]}")
    for k in ["auc", "auc_count_only", "wrong_over_rate", "right_over_rate"]:
        a, b = mine[k], theirs[k]
        if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-4):
            problems.append(f"{where} {k}: rows give {a}, summary says {b}")


def bootstrap(pencil_rows):
    """puzzle-level bootstrap of mean(auc) - mean(count-only auc) over the nets, resampling each net's puzzles that
    have states (as critic/verify/extra.py). A resample where some net's AUC is undefined is dropped and counted."""
    rng = random.Random(BOOT_SEED)
    by = {}
    for n, rows in pencil_rows.items():
        d = defaultdict(list)
        for r in rows:
            if r["row"] == "state" and r["set"] == MARK_SET:
                d[r["item"]].append(r)
        by[n] = d
    diffs, dropped = [], 0
    for _ in range(BOOT):
        a_s, k_s, bad = [], [], False
        for n, d in by.items():
            keys = list(d)
            samp = [rng.choice(keys) for _ in keys] if keys else []
            rr = [r for key in samp for r in d[key]]
            p, q = [r for r in rr if r["dead"]], [r for r in rr if not r["dead"]]
            a, k = auc([r["score"] for r in p], [r["score"] for r in q]), auc([r["k"] for r in p], [r["k"] for r in q])
            if a is None or k is None:
                bad = True
                break
            a_s.append(a); k_s.append(k)
        if bad:
            dropped += 1
            continue
        diffs.append(sum(a_s) / len(a_s) - sum(k_s) / len(k_s))
    diffs.sort()
    if not diffs:
        return {"resamples": 0, "dropped": dropped}
    q = lambda f: round(diffs[min(len(diffs) - 1, int(f * len(diffs)))], 4)
    return {"resamples": len(diffs), "dropped": dropped, "p2.5": q(0.025), "p50": q(0.5), "p97.5": q(0.975),
            "share_above_0": round(sum(x > 0 for x in diffs) / len(diffs), 3),
            "share_at_least_margin": round(sum(x >= AUC_MARGIN for x in diffs) / len(diffs), 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--nets-sha", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    run = Path(a.run)
    problems, notes = [], []
    tags = sorted({p.name.split("-")[-1].split(".")[0] for p in run.glob("measure-pencil-s*.json")})
    nets_sha = {}
    if a.nets_sha:
        for line in Path(a.nets_sha).read_text().splitlines():
            h, f = line.split()
            nets_sha["s" + f.split("/")[0].split("-s")[-1]] = h
    rep = {"nets": tags, "per_net": {}, "validity": {}, "noharm": {}, "problems": problems, "notes": notes}
    rows_by = {arm: {} for arm in ARMS}
    for t in tags:
        info = json.loads((run / f"info-{t}.json").read_text())
        pn = {"sha256": info["sha256"], "gpu": info.get("gpu"), "torch": info.get("torch"), "trace": info.get("trace")}
        if nets_sha:
            pn["sha_matches_nets_file"] = nets_sha.get(t) == info["sha256"]
            if not pn["sha_matches_nets_file"]:
                problems.append(f"{t}: net sha256 {info['sha256']} is not the {t} line of the nets file")
        for arm in ["pencil", "clean"]:
            f = run / f"train-{arm}-{t}.json"
            if not f.exists():
                problems.append(f"{t}: {f.name} missing")
                continue
            tr = json.loads(f.read_text())
            rep["validity"][f"{arm}-{t}"] = {k: tr.get(k) for k in
                                             ["steps", "steps_block_nograd", "autocast_cache_off", "torch", "device",
                                              "minutes", "trace_states"]}
            log = run / f"trainlog-{arm}-{t}.jsonl"
            if log.exists():
                last = json.loads(log.read_text().splitlines()[-1])
                rep["validity"][f"{arm}-{t}"]["trainlog_last"] = last
                if last.get("steps_block_nograd") != tr.get("steps_block_nograd"):
                    problems.append(f"{t} {arm}: trainlog's last steps_block_nograd differs from train json")
        for arm in ARMS:
            f = run / f"measure-{arm}-{t}.json"
            if not f.exists():
                problems.append(f"{t}: {f.name} missing")
                continue
            summ = json.loads(f.read_text())
            rows = [json.loads(l) for l in (run / f"measure-{arm}-{t}.rows.jsonl").read_text().splitlines()]
            rows_by[arm][t] = rows
            for name in [MARK_SET, REPORT_SET]:
                mine = recount(rows, name)
                agree(mine, summ["sets"][name], problems, f"{t} {arm} {name}")
                for k in ["n", "day_right", "unfinished", "pencil_solved", "unjudged"]:
                    mine[k] = summ["sets"][name][k]
                pn[f"{arm}/{name}"] = {k: r4(v) if isinstance(v, float) else v for k, v in mine.items()}
        nh = run / f"noharm-{t}.json"
        if nh.exists():
            rep["noharm"][t] = json.loads(nh.read_text())
        else:
            problems.append(f"{t}: noharm-{t}.json missing")
        rep["per_net"][t] = pn

    # VALID: steps_block_nograd = 0 in all 8 fine-tunes (and each ran the sealed 3,000 steps)
    fts = rep["validity"]
    valid = len(fts) == 2 * len(tags) and all(v["steps_block_nograd"] == 0 for v in fts.values())
    for k, v in fts.items():
        if v["steps"] != STEPS:
            problems.append(f"{k}: ran {v['steps']} steps, not the sealed {STEPS}")
    if len(tags) < 4:
        notes.append(f"only {len(tags)} nets have results; the marks read 'of the 4 nets', so a missing net is a miss")

    P = lambda t, arm, name=MARK_SET: rep["per_net"][t].get(f"{arm}/{name}")
    # clause 1, per net
    c1 = {}
    for t in tags:
        pe, cl = P(t, "pencil"), P(t, "clean")
        counts = pe is not None and pe["wrong_judged"] >= MIN_WRONG
        row = {"counts": counts, "pencil_wrong_judged": pe and pe["wrong_judged"]}
        if counts:
            pw, pr = pe["wrong_over_rate"], pe["right_over_rate"]
            cw = cl and cl["wrong_over_rate"]
            row.update(pencil_wrong_rate=pw, pencil_right_rate=pr, clean_wrong_rate=cw,
                       wrong_ok=pw >= WRONG_MIN, right_ok=(pr is not None and pr <= RIGHT_MAX),
                       beats_clean=(cw is not None and pw - cw >= BEAT_CLEAN),
                       below_floor=pw < WRONG_FLOOR, not_above_clean=(cw is not None and pw <= cw))
            if cw is None:
                notes.append(f"{t}: CLEAN judged no wrong marks, so 'beats CLEAN by 20 points' is undefined; "
                             "counted as not met for WORKS and as not firing for PROVED WRONG (not fixed in PLAN.md)")
            row["meets_all"] = row["wrong_ok"] and row["right_ok"] and row["beats_clean"]
        c1[t] = row
    need = 3
    n_meet = sum(1 for r in c1.values() if r.get("meets_all"))
    clause1 = n_meet >= need
    # clause 2: mean per-net AUC (pencil) vs mean per-net count-only AUC (pencil), both on the pencil arm's states
    aucs = [P(t, "pencil")["auc"] for t in tags if P(t, "pencil")]
    kaucs = [P(t, "pencil")["auc_count_only"] for t in tags if P(t, "pencil")]
    if any(x is None for x in aucs + kaucs):
        notes.append("some net's AUC is undefined (no dead or no live states); the means use the nets that have one")
    m_auc, m_k = mean(aucs), mean(kaucs)
    margin = None if m_auc is None or m_k is None else m_auc - m_k
    clause2 = margin is not None and margin >= AUC_MARGIN
    works = valid and clause1 and clause2
    # NO HARM
    harm = {}
    for test in TESTS:
        d = [rep["noharm"][t]["pencil"][test] - rep["noharm"][t]["orig"][test] for t in tags if t in rep["noharm"]]
        dc = [rep["noharm"][t]["clean"][test] - rep["noharm"][t]["orig"][test] for t in tags if t in rep["noharm"]]
        harm[test] = {"pencil_minus_orig_per_net": d, "mean": r4(mean(d)), "ok": mean(d) is not None and mean(d) >= HARM_FLOOR,
                      "clean_minus_orig_per_net_report_only": dc}
    no_harm = all(h["ok"] for h in harm.values())
    # PROVED WRONG (any), among the counted nets
    counted = [r for r in c1.values() if r["counts"]]
    pw1 = sum(1 for r in counted if r["below_floor"]) >= need
    pw2 = sum(1 for r in counted if r["not_above_clean"]) >= need
    pw3 = margin is not None and margin <= 0
    proved_wrong = valid and (pw1 or pw2 or pw3)
    if not valid:
        verdict = "NOT VALID (rerun)"
    elif works and not no_harm:
        verdict = "WORKS BUT HARMS"
    elif works:
        verdict = "WORKS"
    elif proved_wrong:
        verdict = "PROVED WRONG"
    else:
        verdict = "NO CLEAR RESULT"
    # report-only: does ORIG or CLEAN meet clause 1's first two thresholds in >= 3 nets?
    ro = {}
    for arm in ["orig", "clean"]:
        hits = []
        for t in tags:
            x = P(t, arm)
            if x and x["wrong_judged"] >= MIN_WRONG and x["wrong_over_rate"] >= WRONG_MIN and \
                    x["right_over_rate"] is not None and x["right_over_rate"] <= RIGHT_MAX:
                hits.append(t)
        ro[arm] = {"nets_meeting_first_two": hits, "in_3_or_more": len(hits) >= need}
    # pooled count-only AUC on the pencil arm's states, and the bootstrap
    pooled_rows = [r for t in tags for r in rows_by["pencil"].get(t, []) if r["row"] == "state" and r["set"] == MARK_SET]
    pooled_k = auc([r["k"] for r in pooled_rows if r["dead"]], [r["k"] for r in pooled_rows if not r["dead"]])
    rep["marks"] = {
        "valid": valid, "clause1_per_net": c1, "clause1_nets_meeting": n_meet, "clause1": clause1,
        "pencil_mean_auc": r4(m_auc), "pencil_mean_count_only_auc": r4(m_k), "margin": r4(margin), "clause2": clause2,
        "works": works, "noharm": harm, "no_harm": no_harm,
        "proved_wrong_clauses": {"under_30pct_in_3_counted": pw1, "not_above_clean_in_3_counted": pw2,
                                 "auc_not_above_count": pw3},
        "verdict": verdict}
    rep["three_readings"] = {"per_net_mean_margin": r4(margin), "bootstrap": bootstrap(rows_by["pencil"]),
                             "pooled_count_only_auc": r4(pooled_k),
                             "mean_auc_minus_pooled_count_only": r4(None if m_auc is None or pooled_k is None
                                                                    else m_auc - pooled_k)}
    rep["report_only"] = {"orig_or_clean_meet_first_two": ro}
    txt = json.dumps(rep, indent=1)
    if a.out:
        Path(a.out).write_text(txt + "\n")
    print(txt)
    print("VERDICT:", verdict, "| problems:", len(problems))


if __name__ == "__main__":
    main()
