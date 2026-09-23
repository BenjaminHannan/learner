#!/usr/bin/env python3
"""Merge 291 scorer for the registered marks. New file only; piece scorers
are used via their sealed CLIs (never edited); shared helpers from
claude_138m_score / claude_138p_score are imported read-only.

  claude_291_score.py m1 <m1dev_dir> <pred> [out.json]
  claude_291_score.py m2m6 <run_dir> <pred> [out.json]
  claude_291_score.py m7 <m7_tmpdir> <pred> [out.json]
  claude_291_score.py m8 <m8_tmpdir> <pred> [out.json]

m1 checks the dev/case parts (the 720 part is judged by claude_291_m1.py):
  B1 260 devcases: own (260) re-run identical to 260's pilot rows
      (artifacts/claude-openers260-20260922/pilot/dev-rows260.json, every
      field except per-turn sec); 291 identical to own on all 109
      (138p-vs-own moves reported, expected 0).
  C1 dev252b: 252c re-run identical to 252c's registered rows
      (artifacts/claude-merge252c-20260922/run/dev252b-252c.jsonl, every
      field except ms_per_turn); 291 identical to the 252c re-run on all 56.
  C2 dev258/dev259: 252c re-run identical to registered rows; 291 identical
      except the predicted ids, each with its exact record (pred m1c);
      0 false replies and the known junk ids only (d258-037, v259-008).
m2m6 checks vs 138nb's saved rows (timing fields never compared):
  M2 suites: (id, class) move sets equal pred m2 lists; rt136 labels equal
      pred list; direct 291-vs-fresh-138nb row compare moved == pred list;
      no new WRONG / lost OK / WRONG-WRITE / junk except pred-justified ids;
      rt143 0 moved, 0 verdict flips.
  M3 smoke fields differ only in the allowed set.
  M4 bench x3 byte-identical (4 files).
  M5 latency median(291)-median(138nb) <= pred max (+5 ms).
  M6 restart: reply changes exactly pred (exact replies), 0 ghosts, 0 failed
      duplicate checks, 0 bad writes, audits ok. Verifier probes: 291 rows
      vs 138nb rows with exactly the pred moves (ids only in the tally).
m7 tallies the five regression panels from the sealed scorers' outputs
(fidelity first; VOID if not 100%). Output holds ids, families and counts
only -- never item text or replies.
m8 tallies corrpanel291 (arms 138nb, 138p, 291) from its sealed scorer.
"""
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, "scripts")
import claude_138m_score as C  # noqa: E402 (read-only helpers)

NB_RUN = Path("artifacts/claude-merge138nb-20260923/run")
N_RUN = Path("artifacts/claude-merge138n-20260922/run")
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
    new = _dev260_rows(mdir / "dev260-291.json")
    refp = _dev260_rows(mdir / "dev260-p.json")
    fid = sorted(i for i in ref if own.get(i) != ref.get(i))
    wantb = pred.get("m1b", {}).get("dev260", {})
    mv, wrongb, missingb = [], [], []
    for i in own:
        if new.get(i) == own.get(i):
            if i in wantb:
                missingb.append(i)
            continue
        if i not in wantb:
            mv.append(i)
        elif new.get(i) != wantb[i]:
            wrongb.append(i)
    mvp = sorted(i for i in own if refp.get(i) != own.get(i))
    good = (not fid and not mv and not wrongb and not missingb and not mvp
            and sorted(own) == sorted(ref) == sorted(new) == sorted(refp))
    out["parts"]["dev260"] = {"n": len(ref), "fidelity_bad": fid,
                              "moved_291": mv, "predicted_wrong": wrongb,
                              "predicted_not_seen": missingb,
                              "moved_138p": mvp, "pass": good}
    out["pass"] &= good
    # C1: dev252b
    reg = {r["id"]: r for r in jll(D252C / "run/dev252b-252c.jsonl")}
    ownc = {r["id"]: r for r in jll(mdir / "dev252b-252c.jsonl")}
    newc = {r["id"]: r for r in jll(mdir / "dev252b-291.jsonl")}
    fid = sorted(i for i in reg if {k: v for k, v in ownc.get(i, {}).items()
                                    if k != "ms_per_turn"} !=
                 {k: v for k, v in reg[i].items() if k != "ms_per_turn"})
    wantb = pred.get("m1b", {}).get("dev252b", {})
    mv, wrongb, missingb = [], [], []
    for i in reg:
        a = {k: v for k, v in ownc.get(i, {}).items() if k != "ms_per_turn"}
        b = {k: v for k, v in newc.get(i, {}).items() if k != "ms_per_turn"}
        if a == b:
            if i in wantb:
                missingb.append(i)
            continue
        if i not in wantb:
            mv.append(i)
        elif b != wantb[i]:
            wrongb.append(i)
    good = (not fid and not mv and not wrongb and not missingb
            and sorted(ownc) == sorted(reg) == sorted(newc))
    out["parts"]["dev252b"] = {"n": len(reg), "fidelity_bad": fid,
                               "moved_291": mv, "predicted_wrong": wrongb,
                               "predicted_not_seen": missingb, "pass": good}
    out["pass"] &= good
    # C2: dev258 + dev259 (predicted exceptions)
    for dev, n in (("dev258", 79), ("dev259", 66)):
        regf = {"dev258": "dev258-252c.jsonl",
                "dev259": "dev259-252c.jsonl"}[dev]
        reg = {r["id"]: r for r in jll(D252C / f"run/{regf}")}
        ownc = {r["id"]: r for r in jll(mdir / f"{dev}-252c.jsonl")}
        newc = {r["id"]: r for r in jll(mdir / f"{dev}-291.jsonl")}
        fid = sorted(i for i in reg if
                     {k: v for k, v in ownc.get(i, {}).items()
                      if k != "ms_per_turn"} !=
                     {k: v for k, v in reg[i].items() if k != "ms_per_turn"})
        want = pred["m1c"][dev]
        unpred, wrong, missing = [], [], []
        for i in reg:
            a = {k: v for k, v in ownc[i].items() if k != "ms_per_turn"}
            b = {k: v for k, v in newc[i].items() if k != "ms_per_turn"}
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
                and sorted(newc) == sorted(reg))
        out["parts"][dev] = {"n": len(reg), "fidelity_bad": fid,
                             "unpredicted": unpred, "predicted_wrong": wrong,
                             "predicted_not_seen": missing, "pass": good}
        out["pass"] &= good
    return out


# ------------------------------------------------------------- m2m6
def _strip_turn_text(ch):
    """Drop turn text from a change record (ids and counts only)."""
    return {k: v for k, v in ch.items() if k != "turn"}


def m2m6(run, pred):
    import claude_openers260_rowdiff as RD
    run, out = Path(run), {}
    ok = True
    # M2 suites: (id, class) move sets from the suitediff diff files must
    # equal the predicted lists exactly (base: 138nb's saved rows)
    pairs = {"rt143_nogate": (run / "rt143nogate-291.json",
                              run / "rt143nogate-nb.json")}
    for b in BENCH:
        pairs[f"bench:{b}"] = (run / f"sd/bench-{b}-rows.jsonl",
                               NB_RUN / f"sd/bench-{b}-rows.jsonl")
    r2, ok2 = {}, True
    for name, (a, b) in pairs.items():
        ua, ub = RD.units(RD.load(a)), RD.units(RD.load(b))
        mv = sorted(k for k in set(ua) | set(ub) if ua.get(k) != ub.get(k))
        na, nb = len(ua), len(ub)
        w = sorted(pred["m2"]["moves"].get(name, []))
        good = mv == w and na == nb and na > 0
        r2[name] = {"units": [na, nb], "moved": mv, "pass": good}
        ok2 &= good
    for name, dfile in (("sessions152", run / "sd/sessions152-diff.json"),
                        ("bench", run / "sd/bench-diff.json"),
                        ("marks123", run / "sd/marks123-diff.json")):
        da = jl(dfile)
        mine = sorted((m["id"], m["class"]) for m in da["moves"])
        want = sorted(tuple(x) for x in pred["m2"]["moves"].get(name, []))
        good = mine == want
        r2[name] = {"n_moves": da["n_moves"], "moves": mine, "pass": good}
        ok2 &= good
    # rt136 labels vs 138j's sealed rows; the scorer also compares every
    # row directly with fresh 138nb rows from the same session.
    da = jl(run / "sd136/rt136-diff.json")
    mine = sorted((m["id"], m["class"]) for m in da["moves"])
    want = sorted(tuple(x) for x in pred["m2"].get("label_moves", [])
                  or pred["m2"]["moves"].get("rt136", []))
    good = mine == want
    r2["rt136_labels"] = {"n_moves": da["n_moves"], "pass": good}
    ok2 &= good
    # rt136 direct rows 291 vs fresh 138nb rows (seconds never compared)
    base = {r["id"]: r for r in RD.load(run / "sd136-nb/rt136-rows.json")}
    new = {r["id"]: r for r in RD.load(run / "sd136/rt136-rows.json")}
    moved, exc_bad = [], []
    exc = pred["m2"].get("rt136_exceptions", [])
    want_moved = sorted(pred["m2"].get("rt136_direct", []))
    for i in base:
        a = {k: v for k, v in base[i].items() if k not in ("seconds", "sec")}
        b = {k: v for k, v in new.get(i, {}).items()
             if k not in ("seconds", "sec")}
        if a != b:
            moved.append(i)
        if i in exc and a != b:
            exc_bad.append(i)
    good = sorted(moved) == want_moved and not exc_bad
    r2["rt136_direct"] = {"moved": sorted(moved), "exceptions_bad": exc_bad,
                          "pass": good}
    ok2 &= good
    # labels no-new-bad (C122 = 260's registered stated-fact exemption,
    # same justification as 138p; inherited 222 rows listed in pred)
    exc = pred["m2"].get("rt136_exceptions", [])
    just = pred["m2"].get("rt136_justified", ["C122"])
    bad_classes = [m for m in da["moves"] if m["class"] in
                   ("new WRONG", "lost OK") or
                   (m["class"] in ("new WRONG-WRITE", "new junk write")
                    and m["id"] not in exc + just)]
    good = not bad_classes
    r2["rt136_no_new_bad"] = {"bad": [(m["id"], m["class"])
                                      for m in bad_classes], "pass": good}
    ok2 &= good
    # rt143 verdict flips (291 vs fresh 138nb)
    import fable_redteam143_run as R
    markers = jl(R.CASES_PATH)["abstain_markers"]
    base143 = {r["id"]: r for r in jl(run / "rt143nogate-nb.json")}
    new143 = {r["id"]: r for r in jl(run / "rt143nogate-291.json")}
    flips = [i for i in base143 if C._rt143_verdict(base143[i], markers)
             != C._rt143_verdict(new143.get(i, {}), markers)]
    moved143 = sorted(i for i in base143 if base143[i] != new143.get(i))
    good = not flips and not moved143
    r2["rt143_verdict_flips"] = flips
    r2["rt143_moved"] = moved143
    r2["pass"] = ok2 and good
    out["M2"] = r2
    ok &= r2["pass"]
    # M3 smoke (base: 138n's saved smoke; 291 differs only in the allowed
    # identity fields)
    diffs = []
    C._walk(jl(N_RUN / "smoke-n.json"), jl(run / "smoke-291.json"), "",
            diffs)
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
    lnb, lp = [], []
    for i in (1, 2, 3):
        lnb += jl(run / f"lat-nb-{i}.json")["times_ms"]
        lp += jl(run / f"lat-291-{i}.json")["times_ms"]
    mnb, mp = statistics.median(lnb), statistics.median(lp)
    good = mp - mnb <= pred["m5"]["max_delta_ms"]
    out["M5"] = {"median_138nb_ms": round(mnb, 3),
                 "median_291_ms": round(mp, 3),
                 "delta_ms": round(mp - mnb, 3), "n": [len(lnb), len(lp)],
                 "pass": good}
    ok &= good
    # M6 restart probes (138nb vs 291)
    fixed = C.fixed_texts()
    want = pred["m6"]["reply_changes"]
    changes, badw, dup, counts = {}, [], [], {}
    for p in PROBES:
        a = jl(run / "probe" / f"nb-{p}.json")["rows"]
        b = jl(run / "probe" / f"291-{p}.json")["rows"]
        counts[p] = [len(a), len(b), sum(len(r["audits"]) for r in b)]
        for x, y in zip(a, b):
            for i, (ta, tb) in enumerate(zip(x["turns"], y["turns"])):
                if ta["reply"] != tb["reply"]:
                    changes[f"{p}:d{x['dialog']:02d}:t{i:02d}"] = {
                        "nb": ta["reply"], "new": tb["reply"],
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
                   changes[k]["new"] != want[k]["new"])
    missing = sorted(k for k in want if k not in changes)
    ghosts = sorted(k for k, v in changes.items()
                    if _ghost291(v, fixed))
    n_ok = all(c[0] == c[1] > 0 and c[2] > 0 for c in counts.values())
    good = n_ok and not (unpred or wrong or missing or ghosts or badw or dup)
    out["M6restart"] = {"counts": counts,
                        "reply_changes": sorted(changes),
                        "unpredicted": unpred, "predicted_wrong": wrong,
                        "predicted_not_seen": missing,
                        "ghost_answers": ghosts, "bad_writes": badw,
                        "failed_duplicate_checks": dup, "pass": good}
    ok &= good
    # M6 verifier probes (138nb vs 291, timing-insensitive)
    def _notime(x):
        if isinstance(x, dict):
            return {k: _notime(v) for k, v in x.items()
                    if k not in ("sec", "seconds", "ms")}
        if isinstance(x, list):
            return [_notime(v) for v in x]
        return x
    v6, ok6 = {}, True
    for name in ("probes", "supp"):
        a = _notime(jl(run / f"vp-nb-{name}.json"))
        b = _notime(jl(run / f"vp-291-{name}.json"))
        mv = _vprobes_moves(a, b)
        wantv = sorted(pred["m6"].get(f"verifier_{name}", []))
        goodv = sorted(mv) == wantv
        v6[name] = {"n": [len(a) if isinstance(a, list) else 1,
                          len(b) if isinstance(b, list) else 1],
                    "moves": sorted(mv), "pass": goodv}
        ok6 &= goodv
    out["M6probes"] = v6
    out["M6probes"]["pass"] = ok6
    ok &= ok6
    out["pass"] = ok
    return out


ASSERT_RE = re.compile(r"(\b[\w][\w ]*?)'s ([\w][\w ]*?) is ([\w][\w ]*?)[.\n]")


def _ghost291(ch, fixed) -> bool:
    """A changed reply that asserts a triple absent from the end store."""
    r = ch["new"]
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


def _vprobes_moves(a, b):
    """Ids of verifier-probe entries whose timing-stripped record differs."""
    la = a if isinstance(a, list) else a.get("rows", a)
    lb = b if isinstance(b, list) else b.get("rows", b)
    if not isinstance(la, list) or not isinstance(lb, list):
        return ["SHAPE"] if a != b else []
    mv = []
    for i, (x, y) in enumerate(zip(la, lb)):
        if x != y:
            mv.append(str(x.get("id", x.get("dialog", i))))
    if len(la) != len(lb):
        mv.append("LEN")
    return mv


# ------------------------------------------------------------- m7
def _strip_ms(r):
    return {k: v for k, v in r.items() if k != "ms_per_turn"}


def _ids_counts(rows):
    """Ids, families and counts only (never item text or replies)."""
    return [{"id": r["id"], "family": r.get("family"),
             "right": bool(r.get("right")), "wrong": bool(r.get("wrong"))}
            for r in rows]


LABEL291 = " (worked out backwards)"
Q2_NEW = ("didn't understand that question", "well enough to save it")
GLUE_OLD = ("do not know that from what you taught me",
            "cannot predict", "have no record of it")
ABSTAIN = ("don't know", "didn\u2019t understand", "didn't understand",
           "couldn't", "i couldn", "i do not know")


def _is_q2wording(base_text: str, new_text: str) -> bool:
    """Honest-abstain rewording: the old glued long decline becomes 224's
    Q2 (unparsed '?') or 138m's save-failure (statements)."""
    b, n = base_text.lower(), new_text.lower()
    return (any(m in n for m in Q2_NEW)
            and any(m in b for m in GLUE_OLD))


def _stored_names(stored) -> set:
    names = set()
    try:
        items = stored if isinstance(stored, list) else []
        for t in items:
            if isinstance(t, (list, tuple)) and len(t) >= 3:
                for w in (str(t[0]), str(t[2])):
                    wl = w.strip().lower()
                    if len(wl) >= 3 and wl not in ("you", "user"):
                        names.add(wl)
    except Exception:  # noqa: BLE001
        pass
    return names


def _is_tablelabel(base_text: str, new_text: str, base_stored=None,
                   new_stored=None) -> bool:
    """138nb's table/label behaviour: exact label append, or an abstain
    that becomes an answer naming a taught subject with stores equal."""
    if LABEL291 in new_text and new_text.replace(LABEL291, "") == base_text:
        return True
    b, n = base_text.lower(), new_text.lower()
    if not any(m in b for m in ABSTAIN):
        return False
    if LABEL291 in new_text:
        return True
    if base_stored is None or new_stored is None:
        return False
    if base_stored != new_stored:
        return False
    names = _stored_names(base_stored)
    return any(nm in n and nm not in b for nm in names)


def _classify_move(base_text: str, new_text: str, base_stored=None,
                   new_stored=None) -> str:
    if new_text == base_text:
        if base_stored != new_stored:
            return "store-only"
        return "identical"
    if _is_q2wording(base_text, new_text):
        return "q2-wording"
    if _is_tablelabel(base_text, new_text, base_stored, new_stored):
        return "table-label"
    return "unclassified"


def _row_texts(r: dict) -> str:
    parts = []
    for k in ("turn_reply", "followup_reply", "question_reply"):
        v = r.get(k)
        if isinstance(v, str):
            parts.append(v)
    ex = r.get("extra_replies")
    if isinstance(ex, list):
        parts.extend(str(x) for x in ex)
    sr = r.get("setup_replies")
    if isinstance(sr, list):
        parts.extend(str(x) for x in sr)
    return "\n".join(parts)


def _row_stored(r: dict):
    out = []
    for k in ("stored_after_setup", "stored_after_turn",
              "stored_after_followup"):
        v = r.get(k)
        if isinstance(v, list):
            out.extend([list(x) if isinstance(x, list) else x for x in v])
    return out


def m7(tdir, pred):
    tdir, out = Path(tdir), {}
    ok = True
    p7 = pred.get("m7", {})
    # ---- openpanel260
    reg_score = jl(D260 / "run/panel-score260.json")
    rerun_score = jl(tdir / "score-260.json")
    new_score = jl(tdir / "score-291-260.json")
    o = {"fidelity_score_equal": rerun_score == reg_score,
         "n_rows": [len(reg_score["rows"]["260"]),
                    len(rerun_score["rows"]["260"])]}
    good = o["fidelity_score_equal"]
    out["openpanel260_fidelity"] = o
    ok &= good
    r260 = {r["id"]: r for r in reg_score["rows"]["260"]}
    r291 = {r["id"]: r for r in new_score["rows"]["260"]}
    r2w = sorted(i for i in r260 if r260[i]["right"] and not r291[i]["right"])
    junk = sum(len(r291[i].get("junk", [])) for i in r291)
    qw = sum(1 for i in r291 if r291[i].get("question_write"))
    ctrl = [i for i in r291 if r291[i].get("family") == "control"]
    ctrl_bad = [i for i in ctrl if not r291[i].get("identical")]
    tot = [sum(1 for r in r260.values() if r["right"]),
           sum(1 for r in r291.values() if r["right"])]
    marks_pass = all(bool(m[1]) for m in new_score["marks"])
    # reply-level moves come from the rows files (the score rows carry
    # verdicts, not reply text): any stripped-row difference counts, and
    # every move must classify as q2-wording or table-label (anything
    # else, including a store-only change, fails).
    rrows = {r["id"]: r for r in jll(tdir / "open-260.jsonl")}
    nrows = {r["id"]: r for r in jll(tdir / "open-291.jsonl")}
    moves, classes, badclass = [], {}, []
    for i in rrows:
        c = _classify_move(_row_texts(rrows[i]), _row_texts(nrows.get(i, {})),
                           _row_stored(rrows[i]),
                           _row_stored(nrows.get(i, {})))
        if c != "identical":
            moves.append(i)
            classes[i] = c
            if c not in ("q2-wording", "table-label"):
                badclass.append(i)
    moves = sorted(moves)
    good = (not r2w and junk == 0 and qw == 0 and not ctrl_bad
            and marks_pass and not badclass)
    out["openpanel260"] = {"right_totals_260_291": tot,
                           "right_to_wrong": r2w, "junk": junk,
                           "question_writes": qw,
                           "control_not_identical": ctrl_bad,
                           "marks_pass": marks_pass,
                           "moves_291_vs_260": moves,
                           "move_classes": classes,
                           "unclassified_moves": sorted(badclass),
                           "pass": good}
    ok &= good
    # ---- corrtail258 + corrpanel252
    for name, regrows, rerows, regscore, rerscore, newscore, predn in (
            ("corrtail258", D252C / "run/corrtail258-252c.jsonl",
             tdir / "corrtail258-252c.jsonl",
             D252C / "run/m1-check.txt", tdir / "score-tail252c.json",
             tdir / "score-tail291.json", "corrtail258"),
            ("corrpanel252", D252C / "run/corrpanel252-252c.jsonl",
             tdir / "corrpanel252-252c.jsonl",
             D252C / "run/m4-check.txt", tdir / "score-panel252c.json",
             tdir / "score-panel291.json", "corrpanel252")):
        reg = jll(regrows)
        rer = jll(rerows)
        row_bad = [a["id"] for a, b in zip(reg, rer)
                   if _strip_ms(a) != _strip_ms(b)] \
            if len(reg) == len(rer) else ["len", len(reg), len(rer)]
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
            r2 = {i: v for i, v in rerj["per_item_right"].items()}
            n2 = {i: v for i, v in newj["per_item_right"].items()}
            # per_item_right: [family, 252b, 258, 259, mine]
            r2w = sorted(i for i in r2 if r2[i][4] and not n2[i][4])
            tot = [rerj["totals"]["252c"]["right"],
                   newj["totals"]["252c"]["right"]]
            # reply-level moves come from the rows files (reply-only
            # swaps keep every verdict True but change the text); every
            # move must classify (the t258-049 keep shape is q2-wording:
            # stores identical, reply-only).
            rrows = {r["id"]: r for r in jll(tdir / "corrtail258-252c.jsonl")}
            nrows = {r["id"]: r for r in jll(tdir / "corrtail258-291.jsonl")}
            moves, classes, badclass = [], {}, []
            for i in rrows:
                c = _classify_move(_row_texts(rrows[i]),
                                   _row_texts(nrows.get(i, {})),
                                   _row_stored(rrows[i]),
                                   _row_stored(nrows.get(i, {})))
                if c != "identical":
                    moves.append(i)
                    classes[i] = c
                    if c not in ("q2-wording", "table-label"):
                        badclass.append(i)
            moves = sorted(moves)
            # strict store-safety bars from the sealed scorer (M counts
            # 291 as "252c"): 0 false claims, 0 junk, 0 new wrong values.
            fc = list(newj.get("false_claims_252c", []))
            jk = list(newj.get("junk_252c", []))
            wv = list(newj.get("wrong_value_new_252c", []))
            good = (not fc and not jk and not wv and not badclass)
            oo.update({"right_totals_252c_291": tot, "right_to_wrong": r2w,
                       "false_claims": fc, "junk": jk,
                       "new_wrong_values": wv,
                       "moves_291_vs_252c": moves, "move_classes": classes,
                       "unclassified_moves": sorted(badclass),
                       "M1_pass_info": newj.get("M1_pass"),
                       "pass": good and oo["pass_fidelity"]})
            # question writes: no question turn changes the store (turn
            # texts joined mechanically from the panel items file by id;
            # no item is read, tuned on, or quoted).
            items = {it["id"]: it for it in
                     jll(PTAIL / "panel.jsonl")}
            qw = [r["id"] for r in jll(tdir / "corrtail258-291.jsonl")
                  if str(items[r["id"]]["turn"]).rstrip().endswith("?")
                  and (r["stored_after_turn"] != r["stored_after_setup"])]
            oo["question_writes"] = qw
            oo["pass"] = oo["pass"] and not qw
        else:
            tot = [rerj.get("moved_vs_252b"), newj.get("moved_vs_252b")]
            rrows = {r["id"]: r for r in jll(tdir / "corrpanel252-252c.jsonl")}
            nrows = {r["id"]: r for r in jll(tdir / "corrpanel252-291.jsonl")}
            moves, classes, badclass = [], {}, []
            for i in rrows:
                c = _classify_move(_row_texts(rrows[i]),
                                   _row_texts(nrows.get(i, {})),
                                   _row_stored(rrows[i]),
                                   _row_stored(nrows.get(i, {})))
                if c != "identical":
                    moves.append(i)
                    classes[i] = c
                    if c not in ("q2-wording", "table-label"):
                        badclass.append(i)
            moves = sorted(moves)
            # strict store-safety bars from the sealed scorer: the one
            # real correction works (c252-022 both), 0 new wrong values,
            # 0 new junk, 0 false replies.
            wv = list(newj.get("new_wrong_values", []))
            jk = list(newj.get("new_junk_writes", []))
            fr = list(newj.get("false_replies_252c", []))
            good = (newj.get("c252_022_class") == "both"
                    and not wv and not jk and not fr and not badclass)
            oo.update({"moved_252c": tot[0], "moved_291": tot[1],
                       "M4_pass_info": newj.get("M4_pass"),
                       "c252_022_class": newj.get("c252_022_class"),
                       "new_wrong_values": wv, "new_junk_writes": jk,
                       "false_replies": fr,
                       "moves_291_vs_252c": moves, "move_classes": classes,
                       "unclassified_moves": sorted(badclass),
                       "pass": good and oo["pass_fidelity"]})
        out[name] = oo
        ok &= oo["pass"]
    # ---- invpanel138nb (sealed panel scorer; fidelity: 138n arm == base)
    base = {r["id"]: r for r in jll(tdir / "inv-base.jsonl")}
    arm_n = {r["id"]: r for r in jll(tdir / "inv-138n.jsonl")}
    fid_bad = sorted(i for i in base
                     if arm_n.get(i, {}).get("question_reply")
                     != base[i].get("question_reply")
                     or arm_n.get(i, {}).get("setup_replies")
                     != base[i].get("setup_replies")
                     or arm_n.get(i, {}).get("question_wrote")
                     != base[i].get("question_wrote"))
    out["invpanel138nb_fidelity"] = {"n": len(base),
                                     "reply_diffs": fid_bad,
                                     "pass": not fid_bad}
    ok &= out["invpanel138nb_fidelity"]["pass"]
    for arm, key in (("138nb", "inv-138nb"), ("138p", "inv-138p"),
                     ("291", "inv-291")):
        per = jl(tdir / f"score-{key}.json")
        rows = per if isinstance(per, list) else per.get("per_item", per)
        right = sorted(r["id"] for r in rows if r.get("right"))
        wrong = sorted(r["id"] for r in rows if r.get("wrong"))
        fams = {}
        for r in rows:
            fams.setdefault(r.get("family"), [0, 0])
            fams[r.get("family")][1] += 1
            fams[r.get("family")][0] += int(bool(r.get("right")))
        out[f"invpanel138nb_{arm}"] = {"right_n": len(right),
                                       "wrong_n": len(wrong),
                                       "wrong_ids": wrong,
                                       "families": fams}
    rn = {r["id"]: r for r in
          (jl(tdir / "score-inv-138nb.json")
           if isinstance(jl(tdir / "score-inv-138nb.json"), list)
           else jl(tdir / "score-inv-138nb.json").get("per_item", []))}
    r9 = {r["id"]: r for r in
          (jl(tdir / "score-inv-291.json")
           if isinstance(jl(tdir / "score-inv-291.json"), list)
           else jl(tdir / "score-inv-291.json").get("per_item", []))}
    r2w = sorted(i for i in rn if rn[i].get("right") and not r9[i].get("right"))
    new_wrong = sorted(i for i in r9 if r9[i].get("wrong")
                       and not rn.get(i, {}).get("wrong"))
    # moves from the rows files (question_reply text), classified. The
    # stored fields carry the known D1 artefact on every arm equally, so
    # classification here is reply-shape only.
    brows = {r["id"]: r for r in jll(tdir / "inv-138nb.jsonl")}
    crows = {r["id"]: r for r in jll(tdir / "inv-291.jsonl")}
    moves, classes, badclass = [], {}, []
    for i in brows:
        c = _classify_move(str(brows[i].get("question_reply", "")),
                           str(crows.get(i, {}).get("question_reply", "")))
        if c != "identical":
            moves.append(i)
            classes[i] = c
            if c not in ("q2-wording", "table-label"):
                badclass.append(i)
    moves = sorted(moves)
    # question writes: teach_control items are statement turns that write
    # by design; only any other family counts.
    qw = sorted(i for i in r9 if r9[i].get("question_wrote")
                and r9[i].get("family") != "teach_control")
    good = (not r2w and not new_wrong and not qw and not badclass
            and r9 and len(r9) == len(rn) == 70)
    out["invpanel138nb"] = {"right_to_wrong": r2w, "new_wrong": new_wrong,
                            "moves_291_vs_138nb": moves,
                            "move_classes": classes,
                            "unclassified_moves": sorted(badclass),
                            "question_writes": qw, "pass": good}
    ok &= good
    # ---- tablepanel221 (registered panelmap scorer; fidelity: the
    # 138n/138nb pair reproduces 138nb's registered M6 relationship)
    regm6 = jl(NB_RUN / "m6/m6-compare.json")
    nn, nb = {}, {}
    for r in jll(tdir / "t221-n/rows.jsonl"):
        nn[f"{r['id']}#{r['turn_index']}"] = r
    for r in jll(tdir / "t221-nb/rows.jsonl"):
        nb[f"{r['id']}#{r['turn_index']}"] = r
    ids = sorted(nn)
    fid = {"n": len(ids),
           "right_nb": sum(1 for i in ids if nb[i]["correct221"]),
           "gained": sorted(i for i in ids if nb[i]["correct221"]
                            and not nn[i]["correct221"]),
           "lost": sorted(i for i in ids if nn[i]["correct221"]
                          and not nb[i]["correct221"]),
           "wrong_nb": sorted(i for i in ids if nb[i]["wrong_value221"])}
    fid["pass"] = (fid["right_nb"] == regm6["right"]["138nb"]
                   and fid["gained"] == regm6["gained_right_ids"]
                   and not fid["lost"] and not fid["wrong_nb"])
    out["tablepanel221_fidelity"] = fid
    ok &= fid["pass"]
    n9 = {f"{r['id']}#{r['turn_index']}": r
          for r in jll(tdir / "t221-291/rows.jsonl")}
    r2w = sorted(i for i in ids if nb[i]["correct221"]
                 and not n9[i]["correct221"])
    new_wrong = sorted(i for i in ids if n9[i]["wrong_value221"]
                       and not nb[i]["wrong_value221"])
    moves = sorted(i for i in ids if (nb[i]["correct221"],
                                      nb[i]["wrong_value221"])
                   != (n9[i]["correct221"], n9[i]["wrong_value221"]))
    # every verdict move must classify on the reply text (panelmap rows
    # carry reply221 + stage221).
    classes, badclass = {}, []
    for i in moves:
        c = _classify_move(str(nb[i].get("reply221", "")),
                           str(n9[i].get("reply221", "")))
        classes[i] = c
        if c not in ("q2-wording", "table-label"):
            badclass.append(i)
    qw = sorted({str(t.get("id")) for t in jll(tdir / "t221-291/turns.jsonl")
                 if str(t.get("text", "")).strip().endswith("?")
                 and t.get("wrote221")})
    good = (not r2w and not new_wrong and not qw and not badclass)
    out["tablepanel221"] = {"right_to_wrong": r2w, "new_wrong": new_wrong,
                            "moves_291_vs_138nb": moves,
                            "move_classes": classes,
                            "unclassified_moves": sorted(badclass),
                            "question_writes": qw, "pass": good}
    ok &= good
    out["pass"] = ok
    return out


# ------------------------------------------------------------- m8
def m8(tdir, pred):
    tdir, out = Path(tdir), {}
    ok = True
    p8 = pred["m8"]
    arms = {}
    for arm in ("138nb", "138p", "291"):
        per = jl(tdir / f"score-corrpanel291-{arm}.json")
        rows = per if isinstance(per, list) else per.get("per_item", per)
        arms[arm] = {r["id"]: r for r in rows}
    ids = sorted(arms["138nb"])
    good_ids = ids and ids == sorted(arms["138p"]) == sorted(arms["291"])
    out["n"] = len(ids)
    ok &= bool(good_ids)
    rn, rp, r9 = arms["138nb"], arms["138p"], arms["291"]
    r2w_p = sorted(i for i in ids if rp[i].get("right")
                   and not r9[i].get("right"))
    r2w_n = sorted(i for i in ids if rn[i].get("right")
                   and not r9[i].get("right"))
    wrong = sorted(i for i in ids if r9[i].get("wrong"))
    qw = sorted(i for i in ids if r9[i].get("question_wrote"))
    fams = {}
    for r in r9.values():
        fams.setdefault(r.get("family"), [0, 0])
        fams[r.get("family")][1] += 1
        fams[r.get("family")][0] += int(bool(r.get("right")))
    cause_fams = p8.get("cause_families") or sorted(
        {r.get("family") for r in rp.values()} - {"control"})
    cause_n = {f: sum(1 for r in rp.values()
                      if r.get("family") == f and r.get("right"))
               for f in cause_fams}
    cause_9 = {f: sum(1 for r in r9.values()
                      if r.get("family") == f and r.get("right"))
               for f in cause_fams}
    cause_ok = all(cause_9[f] >= cause_n[f] for f in cause_fams)
    ctrl = sorted(i for i in ids if r9[i].get("family") == "control")
    # byte-identity vs 138nb: full-row compare (timing keys excluded) when
    # no reply-text field is present, else the reply-text compare.
    def _ctrl_key(r):
        if isinstance(r.get("question_reply"), str):
            return {"question_reply": r["question_reply"]}
        return {k: v for k, v in r.items()
                if k not in ("ms_per_turn", "ms", "sec", "seconds")}
    ctrl_bad = sorted(i for i in ctrl
                      if _ctrl_key(r9[i]) != _ctrl_key(rn[i]))
    good = (not r2w_p and not r2w_n and not wrong and not qw and cause_ok
            and not ctrl_bad and len(ids) == p8.get("n", len(ids)))
    out["m8"] = {"right_to_wrong_vs_138p": r2w_p,
                 "right_to_wrong_vs_138nb": r2w_n,
                 "wrong_ids": wrong, "question_writes": qw,
                 "families_291": fams,
                 "cause_right_138p": cause_n, "cause_right_291": cause_9,
                 "control_not_identical_to_138nb": ctrl_bad,
                 "pass": good}
    ok &= good
    out["pass"] = ok
    return out


def main(argv) -> int:
    mode, args = argv[1], argv[2:]
    if mode == "m1":
        out = m1(args[0], jl(args[1]))
    elif mode == "m2m6":
        out = m2m6(args[0], jl(args[1]))
    elif mode == "m7":
        out = m7(args[0], jl(args[1]))
    elif mode == "m8":
        out = m8(args[0], jl(args[1]))
    else:
        raise SystemExit("mode must be m1, m2m6, m7 or m8")
    text = json.dumps(out, indent=1)
    if len(args) > 2:
        Path(args[2]).write_text(text, encoding="utf-8")
    print(text)
    return 0 if out.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
