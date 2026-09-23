#!/usr/bin/env python3
"""nb-321 unit tests T1-T5 (BUILD task only; scale comparison is nb-321-run).

Usage:
  python -B scripts/claude_nb321_test.py all [--root /tmp/nb321]
  python -B scripts/claude_nb321_test.py t1|t2|t3|t4|t5 [--root /tmp/nb321]
  python -B scripts/claude_nb321_test.py crashchild --dir D --ack A --n N --seed S

All test notebooks live under the root (default /tmp/nb321), never in the repo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C
from claude_nb321_store import open_compact

FUNCT = ["city", "color", "captain", "anthem"]
MULTI = ["friend", "song", "tool"]
RELS = FUNCT + MULTI

_FIRST = ["Tal", "Bren", "Cor", "Dal", "Fen", "Gal", "Har", "Jel", "Kel",
          "Lor", "Mal", "Nel", "Pel", "Ral", "Sel", "Tor", "Vel", "Wen"]
_LAST = ["voick", "alen", "orath", "enow", "isey", "aldis", "ethan", "ormer"]
_LITS = ["Brelmar", "Torholm", "Salway", "Kelford", "Marmere", "Fenbank",
         "Galfield", "Harwick", "Delstead", "Normoor", "Peldale", "Rilbrook"]
_OPENERS = ["Actually, ", "No wait, ", "Sorry, ", "Let me fix that: ",
            "Correction: ", "Hmm, actually ", "I misspoke, ", "To be exact, ",
            "Scratch that, ", "Rather, "]
_TPLS = [
    "{s}'s {r} is {v}.",
    "{s} calls {r} {v}.",
    "We recorded that {s} keeps {v} as {r}.",
    "{s} told me this morning: {r} is {v}.",
    "Note: {s} has {v} for {r}.",
    "{s} now lists {v} under {r}.",
    "Confirming {s}: the {r} is {v}.",
    "{s} mentioned the {r} {v} yesterday.",
    "For {s}, put down {v} as the {r}.",
    "Word is {s}'s {r} became {v}.",
    "{s} says {v} whenever {r} comes up.",
    "Filed: {s} | {r} | {v}.",
]


def raw_for(rng, subj, rel, val, correction=False):
    t = rng.choice(_TPLS).format(s=subj, r=rel, v=val)
    if correction:
        t = rng.choice(_OPENERS) + t
    return t


def res_key(r):
    return (r.status, json.dumps(r.detail, sort_keys=True, ensure_ascii=False, default=str))


# ---------------------------------------------------------------- T1
def t1():
    rows = C.run_suite(open_compact)
    npass = sum(1 for _, ok, _ in rows if ok)
    fails = [(n, note) for n, ok, note in rows if not ok]
    return {"n": len(rows), "pass": npass, "fails": fails}


# ---------------------------------------------------------------- T2
def build_names(rng, count):
    names, seen = [], set()
    while len(names) < count:
        name = f"{rng.choice(_FIRST)}{rng.choice(['vo','a','or','en'])} {rng.choice(_LAST)}"
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def run_seed(seed, root):
    rng = random.Random(32100 + seed)
    names = build_names(rng, 60)
    da = Path(tempfile.mkdtemp(prefix=f"nb321-t2-{seed}-a-", dir=str(root)))
    db = Path(tempfile.mkdtemp(prefix=f"nb321-t2-{seed}-b-", dir=str(root)))
    na, nb = C.Notebook(str(da)), open_compact(str(db))
    diffs = []
    n_diffs = 0

    def both(label, fn_a, fn_b):
        nonlocal n_diffs
        ra, rb = fn_a(), fn_b()
        if res_key(ra) != res_key(rb):
            n_diffs += 1
            if len(diffs) < 50:
                diffs.append({"op": label, "a": [ra.status, ra.detail],
                              "b": [rb.status, rb.detail]})
        return ra, rb

    eids = []
    for i, name in enumerate(names):
        ra, rb = both(f"ent-{i}",
                      lambda: na.new_entity(f"s{seed}-ent-{i}", name),
                      lambda: nb.new_entity(f"s{seed}-ent-{i}", name))
        if ra.status == "SAVED":
            assert rb.status == "SAVED"
            if ra.detail["entity_id"] != rb.detail["entity_id"]:
                n_diffs += 1
                diffs.append({"op": f"ent-{i}-id", "a": ra.detail, "b": rb.detail})
            eids.append(ra.detail["entity_id"])
    for j, rel in enumerate(RELS):
        both(f"rel-{rel}",
             lambda: na.declare_relation(f"s{seed}-rel-{j}", rel, rel in FUNCT),
             lambda: nb.declare_relation(f"s{seed}-rel-{j}", rel, rel in FUNCT))
    both(f"rule-R1", lambda: na.approve_rule(f"s{seed}-rule", "ben", "R1", "x"),
         lambda: nb.approve_rule(f"s{seed}-rule", "ben", "R1", "x"))

    taught = {}   # fact_id -> (subj_idx, rel, text, is_ent)
    func_live = {}  # (subj_idx, rel) -> fact_id (active taught, functional only)
    active_all = []  # active fact_ids (taught only, for forgets)
    proposed = []  # proposed fact_ids available to promote
    seen_event_ids = []
    touched = set()

    def val_for(subj_idx):
        if rng.random() < 0.5:
            o = rng.randrange(len(eids))
            if o == subj_idx:
                o = (o + 1) % len(eids)
            return {"entity": eids[o]}, names[o], True, o
        lit = rng.choice(_LITS)
        return {"literal": lit}, lit, False, None

    for i in range(5000):
        eid = f"s{seed}-op{i:05d}"
        u = rng.random()
        if u < 0.46:  # teach
            s = rng.randrange(len(eids))
            rel = rng.choice(RELS)
            if rel in FUNCT and (s, rel) in func_live:
                continue
            v, text, is_ent, oe = val_for(s)
            raw = raw_for(rng, names[s], rel, text)
            ra, rb = both(eid,
                          lambda: na.assert_fact(eid, "listening", "taught", eids[s], rel, dict(v), raw=raw),
                          lambda: nb.assert_fact(eid, "listening", "taught", eids[s], rel, dict(v), raw=raw))
            seen_event_ids.append(eid)
            if ra.status == "SAVED" and res_key(ra) == res_key(rb):
                taught[ra.detail["fact_id"]] = (s, rel, text, is_ent)
                active_all.append(ra.detail["fact_id"])
                if rel in FUNCT:
                    func_live[(s, rel)] = ra.detail["fact_id"]
                touched.add((s, rel))
        elif u < 0.58:  # correction
            if not func_live:
                continue
            key = rng.choice(sorted(func_live))
            s, rel = key
            old = taught[func_live[key]]
            v, text, is_ent, oe = val_for(s)
            raw = raw_for(rng, names[s], rel, text, correction=True)
            ceid = eid
            ra, rb = both(ceid,
                          lambda: na.assert_fact(ceid, "listening", "taught", eids[s], rel, dict(v), correction=True, raw=raw),
                          lambda: nb.assert_fact(ceid, "listening", "taught", eids[s], rel, dict(v), correction=True, raw=raw))
            seen_event_ids.append(ceid)
            if ra.status == "SAVED" and res_key(ra) == res_key(rb):
                if func_live.get(key) in active_all:
                    active_all.remove(func_live[key])
                taught[ra.detail["fact_id"]] = (s, rel, text, is_ent)
                active_all.append(ra.detail["fact_id"])
                func_live[key] = ra.detail["fact_id"]
                touched.add((s, rel))
        elif u < 0.66:  # forget (+ bad retracts)
            if rng.random() < 0.8 and active_all:
                fid = rng.choice(active_all)
                ra, rb = both(eid,
                              lambda: na.retract(eid, "listening", fid, "forget it"),
                              lambda: nb.retract(eid, "listening", fid, "forget it"))
                seen_event_ids.append(eid)
                if ra.status == "SAVED" and res_key(ra) == res_key(rb):
                    active_all.remove(fid)
                    for k, v in list(func_live.items()):
                        if v == fid:
                            del func_live[k]
            elif rng.random() < 0.5:
                both(eid, lambda: na.retract(eid, "listening", "F99999", "x"),
                     lambda: nb.retract(eid, "listening", "F99999", "x"))
                seen_event_ids.append(eid)
            else:
                if not active_all:
                    continue
                fid = rng.choice(active_all)
                both(eid, lambda: na.retract(eid, "sleep", fid, "tidy"),
                     lambda: nb.retract(eid, "sleep", fid, "tidy"))
                seen_event_ids.append(eid)
        elif u < 0.74:  # alias (+ bad alias)
            s = rng.randrange(len(eids))
            if rng.random() < 0.85:
                alias = f"{names[s].split()[0]} K"
                both(eid, lambda: na.add_alias(eid, eids[s], alias),
                     lambda: nb.add_alias(eid, eids[s], alias))
                seen_event_ids.append(eid)
            else:
                both(eid, lambda: na.add_alias(eid, "E9999", "Zed"),
                     lambda: nb.add_alias(eid, "E9999", "Zed"))
                seen_event_ids.append(eid)
        elif u < 0.80:  # propose + promote
            s = rng.randrange(len(eids))
            rel = rng.choice(RELS)
            v, text, is_ent, oe = val_for(s)
            peid = eid + "-p"
            ra, rb = both(peid,
                          lambda: na.assert_fact(peid, "creative", "proposed", eids[s], rel, dict(v)),
                          lambda: nb.assert_fact(peid, "creative", "proposed", eids[s], rel, dict(v), ))
            seen_event_ids.append(peid)
            if ra.status == "SAVED" and res_key(ra) == res_key(rb):
                proposed.append(ra.detail["fact_id"])
            if proposed and rng.random() < 0.7:
                fid = proposed.pop(0)
                if rng.random() < 0.85:
                    ra, rb = both(eid,
                                  lambda: na.promote(eid, "ben", fid),
                                  lambda: nb.promote(eid, "ben", fid))
                    seen_event_ids.append(eid)
                    if ra.status == "SAVED" and res_key(ra) == res_key(rb):
                        taught[ra.detail["fact_id"]] = (s, rel, text, is_ent)
                        active_all.append(ra.detail["fact_id"])
                        touched.add((s, rel))
                else:
                    both(eid, lambda: na.promote(eid, "thinking", fid),
                         lambda: nb.promote(eid, "thinking", fid))
                    seen_event_ids.append(eid)
                    proposed.append(fid)
        elif u < 0.86:  # conflict attempt
            if not func_live:
                continue
            key = rng.choice(sorted(func_live))
            s, rel = key
            v, text, is_ent, oe = val_for(s)
            both(eid,
                 lambda: na.assert_fact(eid, "listening", "taught", eids[s], rel, dict(v), raw="x"),
                 lambda: nb.assert_fact(eid, "listening", "taught", eids[s], rel, dict(v), raw="x"))
            seen_event_ids.append(eid)
        elif u < 0.92:  # duplicate event id
            if not seen_event_ids:
                continue
            dup = rng.choice(seen_event_ids)
            s = rng.randrange(len(eids))
            both(f"dup-{i}",
                 lambda: na.assert_fact(dup, "listening", "taught", eids[s], "song", {"literal": "X"}),
                 lambda: nb.assert_fact(dup, "listening", "taught", eids[s], "song", {"literal": "X"}))
        elif u < 0.97:  # inferred
            if not active_all:
                continue
            dep = rng.choice(active_all)
            s = rng.randrange(len(eids))
            if rng.random() < 0.8:
                both(eid,
                     lambda: na.assert_fact(eid, "thinking", "inferred", eids[s], "song", {"literal": "Y"}, rule_id="R1", deps=(dep,)),
                     lambda: nb.assert_fact(eid, "thinking", "inferred", eids[s], "song", {"literal": "Y"}, rule_id="R1", deps=(dep,)))
            else:
                both(eid,
                     lambda: na.assert_fact(eid, "thinking", "inferred", eids[s], "song", {"literal": "Y"}, rule_id="NOPE", deps=(dep,)),
                     lambda: nb.assert_fact(eid, "thinking", "inferred", eids[s], "song", {"literal": "Y"}, rule_id="NOPE", deps=(dep,)))
            seen_event_ids.append(eid)
        else:  # invalid writes
            s = rng.randrange(len(eids))
            if rng.random() < 0.5:
                both(eid,
                     lambda: na.assert_fact(eid, "thinking", "taught", eids[s], "song", {"literal": "Z"}),
                     lambda: nb.assert_fact(eid, "thinking", "taught", eids[s], "song", {"literal": "Z"}))
            else:
                both(eid,
                     lambda: na.assert_fact(eid, "listening", "taught", "E9999", "song", {"literal": "Z"}),
                     lambda: nb.assert_fact(eid, "listening", "taught", "E9999", "song", {"literal": "Z"}))
            seen_event_ids.append(eid)

    # end asks on every touched (subject, relation)
    ask_diffs = []
    n_ask = 0
    for (s, rel) in sorted(touched):
        ra = na.ask(names[s], [rel])
        rb = nb.ask(names[s], [rel])
        n_ask += 1
        if res_key(ra) != res_key(rb):
            if len(ask_diffs) < 20:
                ask_diffs.append({"ask": [names[s], [rel]], "a": [ra.status, ra.detail],
                                  "b": [rb.status, rb.detail]})
    # export comparison
    exp = db / "export.jsonl"
    nb.export_events(str(exp))
    ha = hashlib.sha256((da / "events.jsonl").read_bytes()).hexdigest()
    hb = hashlib.sha256(exp.read_bytes()).hexdigest()
    out = {"seed": seed, "result_diffs": n_diffs, "diff_rows": diffs,
           "n_ask": n_ask, "ask_diffs": ask_diffs,
           "export_equal": ha == hb, "sha_a": ha, "sha_b": hb,
           "bytes_a": (da / "events.jsonl").stat().st_size,
           "bytes_b": exp.stat().st_size}
    na = None
    nb.close()
    return out


def t2(root):
    return [run_seed(s, root) for s in (0, 1, 2)]


# ---------------------------------------------------------------- T3
def crashchild(args):
    rng = random.Random(args.seed)
    nb = open_compact(args.dir)
    nb.declare_relation(f"crash-rel-{args.seed}", "pal", False)
    eids = []
    for i in range(20):
        r = nb.new_entity(f"crash-{args.seed}-e{i}", f"Crashper{args.seed} Son{i}")
        eids.append(r.detail["entity_id"])
    ack = open(args.ack, "a", encoding="utf-8")
    for i in range(args.n):
        eid = eids[i % len(eids)]
        ev = f"crash-{args.seed}-{i:05d}"
        r = nb.assert_fact(ev, "listening", "taught", eid, "pal",
                           {"literal": f"Town{i}"}, raw=f"crash note {i} filed")
        if r.status == "SAVED":
            ack.write(ev + "\n")
            ack.flush()
            os.fsync(ack.fileno())
    ack.close()
    return 0


def t3(root):
    rng = random.Random(32103)
    work = Path(root) / "t3"
    work.mkdir(parents=True, exist_ok=True)
    lost = dups = failed = torn = 0
    details = []
    for j in range(20):
        d = work / f"crash-{j:02d}"
        if d.exists():
            shutil.rmtree(d)
        ack = work / f"ack-{j:02d}.txt"
        if ack.exists():
            ack.unlink()
        proc = subprocess.Popen(
            [sys.executable, "-B", __file__, "crashchild",
             "--dir", str(d), "--ack", str(ack), "--n", "2000",
             "--seed", str(32103 + j)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        waited = 0.0
        while waited < 120.0:
            if proc.poll() is not None:
                break
            if ack.exists() and ack.stat().st_size > 0:
                break
            time.sleep(0.02)
            waited += 0.02
        time.sleep(rng.uniform(0.05, 1.5))
        killed = True
        if proc.poll() is None:
            proc.send_signal(signal.SIGKILL)
            proc.wait()
        else:
            killed = False
        acked = ack.read_text(encoding="utf-8").split() if ack.exists() else []
        try:
            nb = open_compact(str(d))
            opened = True
        except Exception as exc:  # noqa: BLE001
            failed += 1
            details.append({"child": j, "killed": killed,
                            "failed_open": type(exc).__name__})
            continue
        if getattr(nb, "torn_tail", False):
            torn += 1
            nb.repair_torn_tail()
            nb = open_compact(str(d))
        present = set(nb.event_ids)
        miss = [e for e in acked if e not in present]
        lost += len(miss)
        seen = set()
        nd = 0
        for e in nb.event_ids:
            if e in seen:
                nd += 1
            seen.add(e)
        dups += nd
        details.append({"child": j, "killed": killed, "acked": len(acked),
                        "lost": len(miss), "dup": nd})
    return {"children": 20, "acked_lost": lost, "duplicates": dups,
            "failed_opens": failed, "torn_tails": torn, "details": details}


# ---------------------------------------------------------------- T4
def t4(root):
    rng = random.Random(32104)
    d = Path(root) / "t4build"
    if d.exists():
        shutil.rmtree(d)
    nb = open_compact(str(d))
    nb.declare_relation("t4-rel-city", "city", True)
    eids = []
    for i in range(30):
        r = nb.new_entity(f"t4-e{i}", f"T4per{i} Vonoick")
        eids.append(r.detail["entity_id"])
    for i in range(300):
        nb.assert_fact(f"t4-{i:05d}", "listening", "taught", eids[i % 30], "city",
                       {"literal": f"City{i}"}, raw=f"T4per{i} Vonoick's city is City{i}.")
    nb.close()
    nb = open_compact(str(d))  # clean reopen syncs the sidecar
    t0 = time.perf_counter()
    rep = nb.verify_all()
    verify_s = time.perf_counter() - t0
    nb.close()
    db = d / "store.db"
    size = db.stat().st_size
    caught_open = caught_verify = 0
    missed = []
    for k in range(10):
        c = Path(root) / f"t4tamper-{k:02d}"
        if c.exists():
            shutil.rmtree(c)
        shutil.copytree(d, c)
        off = rng.randrange(size)
        with open(c / "store.db", "r+b") as fh:
            fh.seek(off)
            b = fh.read(1)
            fh.seek(off)
            fh.write(bytes([(b[0] + 1) % 256]))
            fh.flush()
            os.fsync(fh.fileno())
        try:
            tam = open_compact(str(c))
        except Exception:  # noqa: BLE001 open caught it
            caught_open += 1
            continue
        try:
            tam.verify_all()
            missed.append({"copy": k, "offset": off})
        except Exception:  # noqa: BLE001 verify caught it
            caught_verify += 1
        finally:
            try:
                tam.close()
            except Exception:  # noqa: BLE001
                pass
    blocked = 0
    con = sqlite3.connect(str(db))
    try:
        con.execute("UPDATE events SET kind=1 WHERE n=1")
    except Exception:  # noqa: BLE001 trigger blocks
        blocked += 1
    try:
        con.execute("DELETE FROM events WHERE n=1")
    except Exception:  # noqa: BLE001 trigger blocks
        blocked += 1
    con.close()
    return {"tamper_copies": 10, "caught_open": caught_open,
            "caught_verify": caught_verify, "missed": missed,
            "blocked": blocked, "verify_s": verify_s,
            "verify_n": rep["n_events"]}


# ---------------------------------------------------------------- T5
def gen_workload_20k(path):
    rng = random.Random(3200)
    funct = ["title", "occupation", "employer", "capital", "place_of_birth",
             "work_location", "school", "country", "city", "hometown",
             "home", "favorite_book", "hobby", "color", "car",
             "favorite_season", "favorite_sport", "instrument", "favorite_food",
             "favorite_color", "nickname", "favorite_subject", "allergy", "boss",
             "landlord", "coach", "doctor", "dentist", "vet", "mentor"]
    multi = ["friend", "song", "tool", "rival", "guest", "partner", "rival2",
             "cousin", "neighbor", "mate", "colleague", "penpal"]
    rels = funct + multi
    A1 = ["Tal", "Bren", "Cor", "Dal", "Fen", "Gal", "Har", "Jel", "Kel",
          "Lor", "Mal", "Nel", "Pel", "Ral", "Sel", "Tor", "Vel", "Wen"]
    A2 = ["vo", "a", "i", "or", "en", "is", "al", "eth"]
    B1 = ["Bren", "Corv", "Dall", "Fenn", "Garr", "Hall", "Jenn", "Kell"]
    B2 = ["ick", "or", "en", "ath", "ow", "ey", "is", "an"]
    firsts = [a + b for a in A1 for b in A2]
    lasts = [a + b for a in B1 for b in B2]
    names = [f"{f} {l}" for f in firsts for l in lasts][:2000]
    lits = [a + b for a in
            ["Brel", "Tor", "Sal", "Kel", "Mar", "Fen", "Gal", "Har",
             "Del", "Nor", "Pel", "Ril", "Sul", "Vel", "Wyn", "Thal",
             "Brin", "Cor", "Drin", "El", "Fal", "Gren", "Hol", "Ith"]
            for b in ["mar", "holm", "way", "ford", "mere", "bank", "field",
                      "wick", "stead", "moor", "dale", "brook"]]
    n_teach, n_corr = 17000, 2000
    n_forget = 20000 - n_teach - n_corr
    ops, active, fpair = [], {}, {}
    ever = {}
    from collections import defaultdict as _dd
    ever = _dd(set)

    def fresh(s, r, ent):
        for _ in range(100):
            if ent:
                o = rng.randrange(2000)
                if o == s:
                    continue
                t = names[o]
                v = {"entity": o}
            else:
                t = rng.choice(lits)
                v = {"literal": t}
            if t not in ever[(s, r)]:
                return v, t
        raise RuntimeError("value pool exhausted")
    for i in range(n_teach):
        for _ in range(200):
            s = rng.randrange(2000)
            r = rng.choice(rels)
            if r in funct and (s, r) in fpair:
                continue
            ent = rng.random() < 0.5
            try:
                v, t = fresh(s, r, ent)
            except RuntimeError:
                continue
            break
        raw = rng.choice(_TPLS).format(s=names[s], r=r, v=t)
        ops.append({"kind": "teach", "s": s, "r": r, "v": v, "t": t, "raw": raw,
                    "eid": f"nb5-{i:07d}"})
        ever[(s, r)].add(t)
        active[i] = (s, r, ent)
        if r in funct:
            fpair[(s, r)] = i
    fa = [oi for oi, (s, r, e) in active.items() if r in funct]
    for k in range(n_corr):
        oi = rng.choice(fa)
        fa.remove(oi)
        s, r, ent = active.pop(oi)
        v, t = fresh(s, r, ent)
        raw = rng.choice(_OPENERS) + rng.choice(_TPLS).format(s=names[s], r=r, v=t)
        ops.append({"kind": "correct", "s": s, "r": r, "v": v, "t": t,
                    "raw": raw, "eid": f"nb5-c{k:07d}", "target": oi})
        ever[(s, r)].add(t)
        active[len(ops) - 1] = (s, r, ent)
        fpair[(s, r)] = len(ops) - 1
    live = list(active)
    for k in range(n_forget):
        oi = rng.choice(live)
        live.remove(oi)
        s, r, ent = active.pop(oi)
        fpair.pop((s, r), None)
        ops.append({"kind": "forget", "s": s, "r": r,
                    "eid": f"nb5-f{k:07d}", "target": oi})
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"names": names, "funct": funct,
                             "multi": multi}) + "\n")
        for op in ops:
            fh.write(json.dumps(op) + "\n")
    return path


def replay(factory, d, workload, gt_path=None):
    header, ops = None, []
    with open(workload, encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            if "names" in row:
                header = row
            else:
                ops.append(row)
    names = header["names"]
    nb = factory(str(d))
    for rel in sorted(set(header["funct"]) | set(header["multi"])):
        nb.declare_relation(f"nb5-rel-{rel}", rel, rel in set(header["funct"]))
    eid = {}
    for i, name in enumerate(names):
        eid[i] = nb.new_entity(f"nb5-ent-{i:06d}", name).detail["entity_id"]
    op2fid = {}
    fw = 0
    for k, op in enumerate(ops):
        subj = eid[op["s"]]
        if op["kind"] == "teach":
            v = op["v"]
            val = {"entity": eid[v["entity"]]} if "entity" in v else {"literal": v["literal"]}
            r = nb.assert_fact(op["eid"], "listening", "taught", subj, op["r"], val, raw=op["raw"])
            assert r.status == "SAVED", (k, r.status, r.detail)
            op2fid[k] = r.detail["fact_id"]
            fw += 1
        elif op["kind"] == "correct":
            v = op["v"]
            val = {"entity": eid[v["entity"]]} if "entity" in v else {"literal": v["literal"]}
            r = nb.assert_fact(op["eid"], "listening", "taught", subj, op["r"], val, correction=True, raw=op["raw"])
            assert r.status == "SAVED", (k, r.status, r.detail)
            op2fid[k] = r.detail["fact_id"]
            fw += 1
        else:
            nb.retract(op["eid"], "listening", op2fid[op["target"]], "nb5 forget")
    total = 0
    for p in Path(d).iterdir():
        if p.is_file():
            total += p.stat().st_size
    try:
        nb.close()
    except Exception:  # noqa: BLE001 contract notebook has no close
        pass
    return fw, total


def t5(root):
    w = Path(root) / "workload-20000.jsonl"
    gen_workload_20k(str(w))
    da = Path(root) / "t5a"
    db = Path(root) / "t5b"
    if da.exists():
        shutil.rmtree(da)
    if db.exists():
        shutil.rmtree(db)
    t0 = time.perf_counter()
    fw_a, bytes_a = replay(C.Notebook, str(da), str(w))
    wall_a = time.perf_counter() - t0
    t0 = time.perf_counter()
    fw_b, bytes_b = replay(open_compact, str(db), str(w))
    wall_b = time.perf_counter() - t0
    assert fw_a == fw_b
    dbfile = Path(db) / "store.db"
    return {"fact_writes": fw_a, "base_bytes": bytes_a,
            "base_per_fact": bytes_a / fw_a, "compact_dir_bytes": bytes_b,
            "compact_db_bytes": dbfile.stat().st_size,
            "compact_db_per_fact": dbfile.stat().st_size / fw_b,
            "compact_dir_per_fact": bytes_b / fw_b,
            "wall_a": wall_a, "wall_b": wall_b}


def main() -> int:
    parser = argparse.ArgumentParser(description="nb-321 unit tests T1-T5")
    parser.add_argument("cmd", nargs="?", default="all")
    parser.add_argument("--root", default="/tmp/nb321")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--ack", default=None)
    parser.add_argument("--n", type=int, default=0)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    if args.cmd == "crashchild":
        return crashchild(args)
    Path(args.root).mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    if args.cmd in ("all", "t1"):
        r = t1()
        print(f"T1 lifecycle: {r['pass']}/{r['n']}", flush=True)
        for n, note in r["fails"]:
            print(f"  FAIL {n} {note}", flush=True)
    if args.cmd in ("all", "t2"):
        for row in t2(args.root):
            print(f"T2 seed {row['seed']}: result_diffs={row['result_diffs']} "
                  f"asks={row['n_ask']} ask_diffs={len(row['ask_diffs'])} "
                  f"export_equal={row['export_equal']} "
                  f"sha={row['sha_b'][:12]} bytes={row['bytes_b']}", flush=True)
            for drow in row["diff_rows"][:10]:
                print(f"  DIFF {drow}", flush=True)
            for drow in row["ask_diffs"][:10]:
                print(f"  ASKDIFF {drow}", flush=True)
    if args.cmd in ("all", "t3"):
        r = t3(args.root)
        print(f"T3 crash: children={r['children']} acked_lost={r['acked_lost']} "
              f"duplicates={r['duplicates']} failed_opens={r['failed_opens']} "
              f"torn={r['torn_tails']}", flush=True)
    if args.cmd in ("all", "t4"):
        r = t4(args.root)
        print(f"T4 tamper: copies={r['tamper_copies']} caught_open={r['caught_open']} "
              f"caught_verify={r['caught_verify']} missed={len(r['missed'])} "
              f"blocked={r['blocked']}/2 verify_all_s={r['verify_s']:.2f}", flush=True)
        for m in r["missed"]:
            print(f"  MISS {m}", flush=True)
    if args.cmd in ("all", "t5"):
        r = t5(args.root)
        print(f"T5 size: fact_writes={r['fact_writes']} "
              f"base_per_fact={r['base_per_fact']:.1f} "
              f"compact_db_per_fact={r['compact_db_per_fact']:.1f} "
              f"compact_dir_per_fact={r['compact_dir_per_fact']:.1f} "
              f"wall_a={r['wall_a']:.1f}s wall_b={r['wall_b']:.1f}s", flush=True)
    print(f"done in {time.perf_counter()-t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
