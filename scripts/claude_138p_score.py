#!/usr/bin/env python3
"""Merge 138p scorer for the registered marks (M1 in the L1 judge + here;
M2-M6 here; M7 here). New file only; piece scorers are imported read-only.

  claude_138p_score.py m1 <m1dev_dir> <pred> [out.json]
  claude_138p_score.py m2m6 <run_dir> <pred> [out.json]
  claude_138p_score.py m7 <m7_dir> <pred> [out.json]

m1 checks the dev/case parts (the L1-A part is judged by claude_138p_l1.py):
  B1 260 devcases: own (260) re-run identical to 260's pilot rows
      (artifacts/claude-openers260-20260922/pilot/dev-rows260.json, every
      field except per-turn sec); 138p identical to own on all 109.
  C1 dev252b: 252c re-run identical to 252c's registered rows
      (artifacts/claude-merge252c-20260922/run/dev252b-252c.jsonl, every
      field except ms_per_turn); 138p identical to the 252c re-run on all 56.
  C2 dev258/dev259: 252c re-run identical to registered rows; 138p identical
      except the predicted abstain-wording ids, each with its exact record
      (pred m1c); 0 false replies and the known junk ids only (d258-037,
      v259-008, both junk in the own arms too).
m2m6 checks vs 138m's saved rows (timing fields never compared):
  M2 suites: (id, class) move sets equal pred m2 lists; rt136 labels equal
      138m's + C122 (260 exemption); direct 138p-vs-138m row compare moved ==
      [C071,C072,C073,C075,C076,C079,C122]; 63 inherited 222 rows identical;
      rt143 0 moved, 0 verdict flips.
  M3 smoke fields differ only in the allowed set.
  M4 bench x3 byte-identical (4 files).
  M5 latency delta <= pred max (+5 ms).
  M6 restart: reply changes exactly pred (exact replies), 0 ghosts (a changed
      reply that asserts a triple absent from the end store), 0 failed
      duplicate checks, 0 bad writes (events + end store equal), audits ok.
      verifier probes: 138p rows byte-identical to 260's registered
      vp-n.json/vs-n.json; m arm reproduces VM rows-138m.json (no-timing).
m7 (blind panels; ids and counts only, never item text):
  openpanel260: 260 re-run identical to registered panel-260.jsonl (except
      sec); 138m re-run identical to writer base138m.jsonl; 138p scored with
      the same scorer: bars per pred m7 (vs registered arm + 138m numbers).
  corrtail258/corrpanel252: 252c re-run identical to registered rows (except
      ms); 138p scored with the same scorer (m1/m4 rule): bars per pred m7.
"""
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, "scripts")
import claude_138m_score as C  # noqa: E402 (read-only helpers)
import claude_openers260_rowdiff as RD  # noqa: E402 (read-only helpers)

M_RUN = Path("artifacts/claude-merge138m-20260922/run")
VM = Path("artifacts/claude-verify-20260922/138m")
D260 = Path("artifacts/claude-openers260-20260922")
D252C = Path("artifacts/claude-merge252c-20260922")
P260 = Path("artifacts/claude-openpanel260-20260922")
PTAIL = Path("artifacts/claude-corrtail258-20260922")
PPAN = Path("artifacts/claude-corrpanel252-20260922")
BENCH = ("bench132_4hop", "edit200", "new_121_4hop", "old_s2fresh_4hop")
PROBES = ("p3-dialogs", "p3c-restart2", "p3d-ghost", "v-dialogs", "v-supp")


def jl(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def jll(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8")
            .splitlines() if l.strip()]


# ------------------------------------------------------------- m1 (devs)
def _dev260_rows(p):
    return {r["id"]: {"rows": [{k: v for k, v in t.items() if k != "sec"}
                               for t in r["rows"]], "stored": r["stored"]}
            for r in jl(p)}


def m1(mdir, pred):
    mdir, out = Path(mdir), {"parts": {}, "pass": True}
    # B1: 260 devcases
    ref = _dev260_rows(D260 / "pilot/dev-rows260.json")
    own = _dev260_rows(mdir / "dev260-own.json")
    p = _dev260_rows(mdir / "dev260-p.json")
    fid = sorted(i for i in ref if own.get(i) != ref.get(i))
    mv = sorted(i for i in own if p.get(i) != own.get(i))
    good = not fid and not mv and sorted(own) == sorted(ref) == sorted(p)
    out["parts"]["dev260"] = {"n": len(ref), "fidelity_bad": fid,
                              "p_vs_own": mv, "pass": good}
    out["pass"] &= good
    # C1: dev252b
    reg = {r["id"]: r for r in jll(D252C / "run/dev252b-252c.jsonl")}
    ownc = {r["id"]: r for r in jll(mdir / "dev252b-252c.jsonl")}
    pc = {r["id"]: r for r in jll(mdir / "dev252b-p.jsonl")}
    fid = sorted(i for i in reg if {k: v for k, v in ownc.get(i, {}).items()
                                    if k != "ms_per_turn"} !=
                 {k: v for k, v in reg[i].items() if k != "ms_per_turn"})
    mv = sorted(i for i in reg if {k: v for k, v in pc.get(i, {}).items()
                                   if k != "ms_per_turn"} !=
                {k: v for k, v in ownc.get(i, {}).items()
                 if k != "ms_per_turn"})
    good = not fid and not mv and sorted(ownc) == sorted(reg) == sorted(pc)
    out["parts"]["dev252b"] = {"n": len(reg), "fidelity_bad": fid,
                               "p_vs_own": mv, "pass": good}
    out["pass"] &= good
    # C2: dev258 + dev259 (predicted abstain-wording exceptions)
    for dev, n in (("dev258", 79), ("dev259", 66)):
        regf = {"dev258": "dev258-252c.jsonl",
                "dev259": "dev259-252c.jsonl"}[dev]
        reg = {r["id"]: r for r in jll(D252C / f"run/{regf}")}
        ownc = {r["id"]: r for r in jll(mdir / f"{dev}-252c.jsonl")}
        pc = {r["id"]: r for r in jll(mdir / f"{dev}-p.jsonl")}
        fid = sorted(i for i in reg if
                     {k: v for k, v in ownc.get(i, {}).items()
                      if k != "ms_per_turn"} !=
                     {k: v for k, v in reg[i].items() if k != "ms_per_turn"})
        want = pred["m1c"][dev]
        unpred, wrong, missing = [], [], []
        for i in reg:
            a = {k: v for k, v in ownc[i].items() if k != "ms_per_turn"}
            b = {k: v for k, v in pc[i].items() if k != "ms_per_turn"}
            if a == b:
                if i in want:
                    missing.append(i)
                continue
            if i not in want:
                unpred.append(i)
            elif b != want[i]:
                wrong.append(i)
        good = (not fid and not unpred and not wrong and not missing
                and len(reg) == n and sorted(ownc) == sorted(reg)
                and sorted(pc) == sorted(reg))
        out["parts"][dev] = {"n": len(reg), "fidelity_bad": fid,
                             "unpredicted": unpred, "predicted_wrong": wrong,
                             "predicted_not_seen": missing, "pass": good}
        out["pass"] &= good
    return out


# ------------------------------------------------------------- m2m6
def _units(a, b):
    ua, ub = RD.units(RD.load(a)), RD.units(RD.load(b))
    return (sorted(k for k in set(ua) | set(ub) if ua.get(k) != ub.get(k)),
            len(ua), len(ub))


def m2m6(run, pred):
    run, out = Path(run), {}
    ok = True
    # M2 suites: (id, class) move sets from the suitediff diff files must
    # equal the predicted lists exactly (brief: "the (id, class) move set
    # equals your predicted list")
    pairs = {"rt143_nogate": (run / "rt143nogate-p.json",
                              M_RUN / "rt143nogate-m.json")}
    for b in BENCH:
        pairs[f"bench:{b}"] = (run / f"sd/bench-{b}-rows.jsonl",
                               M_RUN / f"sd/bench-{b}-rows.jsonl")
    r2, ok2 = {}, True
    for name, (a, b) in pairs.items():
        mv, na, nb = _units(a, b)
        w = sorted(pred["m2"]["moves"].get(name, []))
        good = mv == w and na == nb and na > 0
        r2[name] = {"units": [na, nb], "moved": mv, "pass": good}
        ok2 &= good
    for name, dfile in (("sessions152", run / "sd/sessions152-diff.json"),
                        ("bench", run / "sd/bench-diff.json")):
        da = jl(dfile)
        mine = sorted((m["id"], m["class"]) for m in da["moves"])
        want = sorted(tuple(x) for x in pred["m2"]["moves"].get(name, []))
        good = mine == want
        r2[name] = {"n_moves": da["n_moves"], "moves": mine, "pass": good}
        ok2 &= good
    # rt136 labels vs 138m's + C122 exemption
    da, db = jl(run / "sd136/rt136-diff.json"), jl(M_RUN / "sd136/rt136-diff.json")
    mine = sorted((m["id"], m["class"]) for m in da["moves"])
    extra = [tuple(x) for x in pred["m2"].get("label_moves", {}).get("rt136", [])]
    theirs = sorted([(m["id"], m["class"]) for m in db["moves"]] + extra)
    good = mine == theirs
    r2["rt136_labels"] = {"n_moves": [da["n_moves"], db["n_moves"]],
                          "pass": good}
    ok2 &= good
    # rt136 direct rows vs 138m saved rows
    base = {r["id"]: r for r in
            RD.load(M_RUN / "sd136/rt136-rows.json")}
    new = {r["id"]: r for r in RD.load(run / "sd136/rt136-rows.json")}
    moved, exc_bad, c122_bad = [], [], []
    exc = pred["m2"]["rt136_exceptions"]
    want_moved = sorted(pred["m2"].get("rt136_direct", []))
    c122 = pred["m2"]["rows"]["rt136"]["C122"]
    for i in base:
        a = {k: v for k, v in base[i].items() if k not in ("seconds", "sec")}
        b = {k: v for k, v in new.get(i, {}).items()
             if k not in ("seconds", "sec")}
        if a != b:
            moved.append(i)
        if i in exc and a != b:
            exc_bad.append(i)
    for k, v in c122.items():
        if new.get("C122", {}).get(k) != v:
            c122_bad.append(k)
    good = sorted(moved) == want_moved and not exc_bad and not c122_bad
    r2["rt136_direct"] = {"moved": sorted(moved), "exceptions_bad": exc_bad,
                          "c122_bad": c122_bad, "pass": good}
    ok2 &= good
    # exceptions identical is covered above (exc_bad); labels no-new-bad:
    bad_classes = [m for m in da["moves"] if m["class"] in
                   ("new WRONG", "lost OK") or
                   (m["class"] in ("new WRONG-WRITE", "new junk write")
                    and m["id"] not in exc + ["C122"])]
    good = not bad_classes
    r2["rt136_no_new_bad"] = {"bad": [(m["id"], m["class"])
                                      for m in bad_classes], "pass": good}
    ok2 &= good
    # rt143 verdict flips
    import fable_redteam143_run as R
    markers = jl(R.CASES_PATH)["abstain_markers"]
    base143 = {r["id"]: r for r in jl(M_RUN / "rt143nogate-m.json")}
    new143 = {r["id"]: r for r in jl(run / "rt143nogate-p.json")}
    flips = [i for i in base143 if C._rt143_verdict(base143[i], markers)
             != C._rt143_verdict(new143.get(i, {}), markers)]
    good = not flips
    r2["rt143_verdict_flips"] = flips
    r2["pass"] = ok2 and good
    out["M2"] = r2
    ok &= r2["pass"]
    # M3 smoke
    diffs = []
    C._walk(jl(M_RUN / "smoke-m.json"), jl(run / "smoke-p.json"), "", diffs)
    allowed = set(pred["m3"]["allowed_fields"])
    bad = [d for d in diffs if d not in allowed]
    out["M3"] = {"differing_fields": diffs, "bad": bad, "pass": not bad}
    ok &= out["M3"]["pass"]
    # M4 bench x3 byte-identical
    files = [f"bench-{b}-rows.jsonl" for b in BENCH]
    bad = []
    for f in files:
        blobs = [(run / f"bench{i}/{f}").read_bytes() for i in (1, 2, 3)]
        if not (blobs[0] == blobs[1] == blobs[2]):
            bad.append(f)
    out["M4"] = {"files": files, "differing": bad, "pass": not bad}
    ok &= out["M4"]["pass"]
    # M5 latency
    lm, lp = [], []
    for i in (1, 2, 3):
        lm += jl(run / f"lat-m-{i}.json")["times_ms"]
        lp += jl(run / f"lat-p-{i}.json")["times_ms"]
    mm, mp = statistics.median(lm), statistics.median(lp)
    good = mp - mm <= pred["m5"]["max_delta_ms"]
    out["M5"] = {"median_138m_ms": round(mm, 3),
                 "median_138p_ms": round(mp, 3),
                 "delta_ms": round(mp - mm, 3), "n": [len(lm), len(lp)],
                 "pass": good}
    ok &= good
    # M6 restart probes
    fixed = C.fixed_texts()
    want = pred["m6"]["reply_changes"]
    changes, badw, dup, counts = {}, [], [], {}
    for p in PROBES:
        a = jl(M_RUN / "probe" / f"m-{p}.json")["rows"]
        b = jl(run / "probe" / f"p-{p}.json")["rows"]
        counts[p] = [len(a), len(b), sum(len(r["audits"]) for r in b)]
        for x, y in zip(a, b):
            for i, (ta, tb) in enumerate(zip(x["turns"], y["turns"])):
                if ta["reply"] != tb["reply"]:
                    changes[f"{p}:d{x['dialog']:02d}:t{i:02d}"] = {
                        "turn": tb["turn"], "m": tb["reply"],
                        "stored_end": y["stored"]}
                if ta["events"] != tb["events"] or ta["turn"] != tb["turn"]:
                    badw.append([p, y["dialog"], i])
            if len(x["turns"]) != len(y["turns"]) or sorted(
                    map(tuple, x["stored"])) != sorted(map(tuple, y["stored"])):
                badw.append([p, y["dialog"], "stored/len"])
            if not y.get("dup_ok_all", False):
                dup.append([p, y["dialog"]])
    unpred = sorted(k for k in changes if k not in want)
    wrong = sorted(k for k in changes if k in want and
                   changes[k]["m"] != want[k]["m"])
    missing = sorted(k for k in want if k not in changes)
    ghosts = sorted(k for k, v in changes.items()
                    if _ghost138p(v, fixed))
    n_ok = all(c[0] == c[1] > 0 and c[2] > 0 for c in counts.values())
    good = n_ok and not (unpred or wrong or missing or ghosts or badw or dup)
    out["M6restart"] = {"counts": counts, "reply_changes": sorted(changes),
                        "unpredicted": unpred, "predicted_wrong": wrong,
                        "predicted_not_seen": missing,
                        "ghost_answers": ghosts, "bad_writes": badw,
                        "failed_duplicate_checks": dup, "pass": good}
    ok &= good
    # M6 verifier probes: 138p rows byte-identical to 260's registered rows
    v6, ok6 = {}, True
    for name, b260, newp in (
            ("probes", D260 / "run/vp-n.json", run / "vp-p.json"),
            ("supp", D260 / "run/vs-n.json", run / "vs-p.json")):
        same = jl(b260) == jl(newp)
        v6[name] = {"identical_to_260": same, "pass": same}
        ok6 &= same
    # m arm reproduces VM base (timing-insensitive: drop sec-like fields)
    def _notime(x):
        if isinstance(x, dict):
            return {k: _notime(v) for k, v in x.items()
                    if k not in ("sec", "seconds", "ms")}
        if isinstance(x, list):
            return [_notime(v) for v in x]
        return x
    for name, basef, newf in (
            ("probes", VM / "rows-138m.json", run / "vp-m.json"),
            ("supp", VM / "supp-rows-138m.json", run / "vs-m.json")):
        same = _notime(jl(basef)) == _notime(jl(newf))
        v6[name + "_m_fidelity"] = {"m_matches_base": same, "pass": same}
        ok6 &= same
    out["M6probes"] = v6
    out["M6probes"]["pass"] = ok6
    ok &= ok6
    out["pass"] = ok
    return out


ASSERT_RE = re.compile(r"(\b[\w][\w ]*?)'s ([\w][\w ]*?) is ([\w][\w ]*?)[.\n]")


def _ghost138p(ch, fixed) -> bool:
    """A changed reply that asserts a triple absent from the end store."""
    r = ch["m"]
    if r in fixed:
        return False
    # quoted how-to-say examples ("say it like \"Kim's boss is Lee.\"")
    # are templates, not assertions about the notebook
    r = re.sub(r'say it like ".*?"', "", r)
    for pre in ("Yes. Your name is ", "Your name is ", "No. Your name is "):
        if r.startswith(pre):
            users = {t[2] for t in ch["stored_end"]
                     if t[0] == "USER" and t[1] == "name"}
            return r[len(pre):].rstrip(".") not in users
    end = {(s.lower(), rl.lower(), v.lower())
           for s, rl, v in ch["stored_end"]}
    for m in ASSERT_RE.finditer(r):
        if (m.group(1).lower(), m.group(2).lower(), m.group(3).lower()) \
                not in end:
            return True
    for tag in ("Saved:", "Updated:"):
        if tag in r:
            return True
    return False


# ------------------------------------------------------------- m7
def _strip_ms(r):
    return {k: v for k, v in r.items() if k != "ms_per_turn"}


def m7(mdir, pred):
    mdir, out = Path(mdir), {}
    ok = True
    p7 = pred["m7"]
    # ---- openpanel260: fidelity (rerun score == registered score) + bars
    reg_score = jl(D260 / "run/panel-score260.json")
    rerun_score = jl(mdir / "score-260.json")
    new_score = jl(mdir / "score-138p260.json")
    o = {"fidelity_score_equal": rerun_score == reg_score,
         "n_rows": [len(reg_score["rows"]["260"]),
                    len(rerun_score["rows"]["260"])]}
    good = o["fidelity_score_equal"]
    out["openpanel260_fidelity"] = o
    ok &= good
    # bars vs registered arm (260): no item right on 260 wrong on 138p,
    # 0 junk, 0 question writes, controls identical; totals reported
    r260 = {r["id"]: r for r in reg_score["rows"]["260"]}
    r138p = {r["id"]: r for r in new_score["rows"]["260"]}
    r2w = sorted(i for i in r260 if r260[i]["right"] and not r138p[i]["right"])
    junk = sum(len(r138p[i]["junk"]) for i in r138p)
    qw = sum(1 for i in r138p if r138p[i]["question_write"])
    ctrl = [i for i in r138p
            if r138p[i]["family"] == "control"]
    ctrl_bad = [i for i in ctrl if not r138p[i]["identical"]]
    tot = [sum(1 for i in r if r["right"]) for r in
           (r260.values(), r138p.values())]
    marks_pass = all(m[1] for m in new_score["marks"])
    good = (not r2w and junk == 0 and qw == 0 and not ctrl_bad
            and marks_pass and tot == p7["openpanel260"]["totals"])
    out["openpanel260"] = {"right_totals_260_138p": tot,
                           "right_to_wrong": r2w, "junk": junk,
                           "question_writes": qw,
                           "control_not_identical": ctrl_bad,
                           "marks_pass": marks_pass, "pass": good}
    ok &= good
    # ---- corrtail258 + corrpanel252: fidelity (rerun rows == registered
    # rows except ms; rerun score == registered score) + bars
    for name, regrows, rerows, regscore, rerscore, newscore, predn in (
            ("corrtail258", D252C / "run/corrtail258-252c.jsonl",
             mdir / "corrtail258-252c.jsonl",
             D252C / "run/m1-check.txt", mdir / "score-tail252c.json",
             mdir / "score-tail138p.json", "corrtail258"),
            ("corrpanel252", D252C / "run/corrpanel252-252c.jsonl",
             mdir / "corrpanel252-252c.jsonl",
             D252C / "run/m4-check.txt", mdir / "score-panel252c.json",
             mdir / "score-panel138p.json", "corrpanel252")):
        reg = jll(regrows)
        rer = jll(rerows)
        row_bad = [a["id"] for a, b in zip(reg, rer)
                   if _strip_ms(a) != _strip_ms(b)] \
            if len(reg) == len(rer) else ["len", len(reg), len(rer)]
        # registered score files are the scorer's printed JSON plus a
        # trailing "scorer exit N" line
        lines = Path(regscore).read_text(encoding="utf-8").splitlines()
        regj = json.loads("\n".join(
            lines[: next(i for i, l in enumerate(lines)
                         if l.strip().startswith("scorer exit"))])
            if any(l.strip().startswith("scorer exit") for l in lines)
            else "\n".join(lines))
        rerj = jl(rerscore)
        newj = jl(newscore)
        oo = {"n": len(reg), "row_diffs": row_bad,
              "score_equal": rerj == regj,
              "pass_fidelity": (not row_bad) and rerj == regj}
        ok &= oo["pass_fidelity"]
        if predn == "corrtail258":
            r2 = {i: v for i, v in
                  rerj["per_item_right"].items()}
            n2 = {i: v for i, v in
                  newj["per_item_right"].items()}
            # per_item_right: [family, 252b, 258, 259, mine]
            r2w = sorted(i for i in r2 if r2[i][4] and not n2[i][4])
            tot = [rerj["totals"]["252c"]["right"],
                   newj["totals"]["252c"]["right"]]
            bars = newj["bars"]
            good = (not r2w and newj["M1_pass"]
                    and tot == p7["corrtail258"]["totals"]
                    and newj["moved_vs_252b"] == p7["corrtail258"]["moved"])
            oo.update({"right_totals_252c_138p": tot, "right_to_wrong": r2w,
                       "bars": bars, "pass": good and oo["pass_fidelity"]})
            # question writes: no question turn changes the store
            qw = [r["id"] for r in jll(mdir / "corrtail258-138p.jsonl")
                  if r["turn"].rstrip().endswith("?")
                  and (r["stored_after_turn"] != r["stored_after_setup"])]
            oo["question_writes"] = qw
            oo["pass"] = oo["pass"] and not qw
        else:
            tot = [rerj.get("moved_vs_252b"), newj.get("moved_vs_252b")]
            good = (newj["M4_pass"]
                    and newj["moved_vs_252b"] == p7["corrpanel252"]["moved"]
                    and newj.get("c252_022_class") == "both")
            oo.update({"moved_252c": tot[0], "moved_138p": tot[1],
                       "M4_pass": newj["M4_pass"],
                       "pass": good and oo["pass_fidelity"]})
        out[name] = oo
        ok &= oo["pass"]
    out["pass"] = ok
    return out


def main(argv):
    mode, args = argv[1], argv[2:]
    if mode == "m1":
        mdir, pred = Path(args[0]), jl(args[1])
        out = m1(mdir, pred)
    elif mode == "m2m6":
        run, pred = Path(args[0]), jl(args[1])
        out = m2m6(run, pred)
    elif mode == "m7":
        mdir, pred = Path(args[0]), jl(args[1])
        out = m7(mdir, pred)
    else:
        raise ValueError(mode)
    print(json.dumps(out, indent=1, default=str)[:4000])
    if len(args) > 2:
        Path(args[2]).write_text(json.dumps(out, indent=1, default=str),
                                 encoding="utf-8")
    return 0 if out.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
