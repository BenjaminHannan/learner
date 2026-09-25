#!/usr/bin/env python3
"""slp-366: the MULTI-NIGHT SCORECARD (Fix-sleep thread, 2026-09-25; roadmap 365, sleep research round 2 item 6).

A world that grows for 6 days. Each day: new people are taught (a new compound word becomes learnable, plus
"transfer" people for every word introduced so far, taught but never asked), the day's questions are asked, one
older fact is corrected; then a night; then a restart from the state folder the next morning (as in 336).
After every night the scorecard asks, in the gate's sandbox (nothing it asks is kept):
  taught      every current taught one-hop fact (corrections applied)       -> right rate
  word_old    every word introduced on an earlier day, on that day's people -> right rate (forgetting shows here)
  word_new    those words on transfer people taught AFTER that word's night -> right rate (did it generalise?)
  lures       broken chains + invented names                                -> made-up answers (must be 0)
and logs practice variety (distinct words with queued episodes that night) and whether the night was kept.

Arms: SLEEP = 360 + 361 + 364 (scrap layer, undo, self-check); NOSLEEP = 360, the same turns, never sleeps.
It is a ruler: the same scorecard will score 363's practice-school nights later.

  python3 -B scripts/claude_slp366_scorecard.py --out artifacts/claude-slp366-20260925/results.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

DAYS366 = ("maternal_grandmother", "boss_of_father", "doctor_of_mothers_friend",
           "father_of_mother", "boss_of_mother", "teacher_of_mother")
ASKED366 = 10          # people per day whose word question is asked (episodes; the sleeper needs >= 8)
HELD366 = 3            # people per day for the day's word, taught, never asked
TRANSFER366 = 3        # people per earlier word, taught each later day, never asked
INVENTED366 = ("Qzorvath", "Xyllimund")
LETTERS = "BCDFGHJKLMNPRSTVWZ"


def _chain(word: str) -> list[str]:
    import fable_sleep130_agent as S130
    return list(S130.CHAINS130[S130.WORDS130.index(word)])


def _name(day: int, group: str, i: int, hop: int) -> str:
    # fictional, unique, name-shaped: e.g. "Bavo" + codes; letters vary by hop so chains never collide
    return f"{LETTERS[(day * 3 + hop) % len(LETTERS)]}{'aeiou'[hop % 5]}{group}{day}{i:02d}"


def build_days(seed: int) -> list[dict]:
    """Deterministic world. Returns one dict per day: teach turns, ask turns, correction, groups."""
    days = []
    for d, word in enumerate(DAYS366, start=1):
        chain = _chain(word)
        teach, asks, groups = [], [], []

        def person(group: str, i: int, w: str, ch: list[str]) -> dict:
            names = [_name(d, group, i, h) + ("" if seed == 1 else f"s{seed}") for h in range(len(ch) + 1)]
            for h, rel in enumerate(ch):
                teach.append(f"{names[h]}'s {rel.replace('_', ' ')} is {names[h + 1]}.")
            return {"word": w, "start": names[0], "chain_names": names, "day": d}

        asked = [person("q", i, word, chain) for i in range(ASKED366)]
        held = [person("h", i, word, chain) for i in range(HELD366)]
        for p in asked:
            asks.append(f"Who is {p['start']}'s {word.replace('_', ' ')}?")
        groups += [dict(p, role="asked") for p in asked] + [dict(p, role="held") for p in held]
        for k, old in enumerate(DAYS366[: d - 1]):
            for i in range(TRANSFER366):
                groups.append(dict(person(f"t{k}", i, old, _chain(old)), role="transfer"))
        # a broken chain (lure): first hop only
        lure = _name(d, "x", 0, 0) + ("" if seed == 1 else f"s{seed}")
        mid = _name(d, "x", 0, 1) + ("" if seed == 1 else f"s{seed}")
        teach.append(f"{lure}'s {chain[0].replace('_', ' ')} is {mid}.")
        days.append({"day": d, "word": word, "teach": teach, "asks": asks, "groups": groups,
                     "lure": {"start": lure, "word": word}})
    # one correction per day from day 2: the first asked person of the previous day gets a new first hop
    for d in range(2, len(days) + 1):
        prev = [g for g in days[d - 2]["groups"] if g["role"] == "asked"][0]
        ch = _chain(prev["word"])
        new_mid = prev["chain_names"][1] + "n"
        days[d - 1]["correction"] = {"text": f"Actually, {prev['start']}'s {ch[0].replace('_', ' ')} is {new_mid}.",
                                     "start": prev["start"], "word": prev["word"]}
    return days


def _probes(loop, days_so_far: list[dict], night: int) -> list[dict]:
    """Probe set after night `night` (1-based): taught one-hops from the notebook, words, lures."""
    import claude_slp364_gate as G
    nb = G._nb(loop)
    probes = [p for p in G.build_probes(loop) if p["kind"] == "T"]
    for p in probes:
        p["cat"] = "taught"
    names = {n.lower(): e for e, n in nb.entities.items()}
    for day in days_so_far:
        for g in day["groups"]:
            eid = names.get(g["start"].lower())
            if eid is None:
                continue
            chain = _chain(g["word"])
            end = G._walk(nb, eid, chain)
            path = G._path(nb, eid, chain)
            word_day = DAYS366.index(g["word"]) + 1
            if end is None:
                continue
            if g["role"] in ("asked", "held"):
                cat = "word_old" if word_day < night else "word_today"
            else:
                cat = "word_new"                  # taught on a later day than its word's first night
            probes.append({"kind": "W", "cat": cat, "word": g["word"],
                           "q": f"Who is {g['start']}'s {g['word'].replace('_', ' ')}?",
                           "want": [nb.entities[end]], "ok": path[:-1]})
        lure = day["lure"]
        probes.append({"kind": "L", "cat": "lure", "word": lure["word"], "want": [],
                       "q": f"Who is {lure['start']}'s {lure['word'].replace('_', ' ')}?",
                       "ok": G._path(nb, names.get(lure["start"].lower(), ""), _chain(lure["word"]))
                       if lure["start"].lower() in names else []})
    for fake in INVENTED366:
        probes.append({"kind": "L", "cat": "lure", "word": "", "want": [], "ok": [],
                       "q": f"Who is {fake}'s {DAYS366[0].replace('_', ' ')}?"})
    return probes


def _score(rows: list[dict]) -> dict:
    out = {}
    for cat in ("taught", "word_old", "word_today", "word_new", "lure"):
        rs = [r for r in rows if r["cat"] == cat]
        if cat == "lure":
            out[cat] = {"n": len(rs), "made_up": sum(r["grade"] in ("wrong", "right") for r in rs)}
        else:
            out[cat] = {"n": len(rs), "right": sum(r["grade"] == "right" for r in rs),
                        "wrong": sum(r["grade"] == "wrong" for r in rs)}
    return out


def run_arm(args) -> dict:
    seed, arm, root = args
    import claude_slp360_test as X
    import claude_slp364_gate as G
    d = Path(root) / f"{arm}-s{seed}"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    days = build_days(seed)
    nights = []
    t_all = time.time()
    loop = None
    for i, day in enumerate(days):
        loop = X.build(str(d), seed, "P")               # every morning: restart from the state folder
        gate = G.install_gate364(loop) if arm == "SLEEP" else None
        replies = []
        for text in day["teach"] + ([day["correction"]["text"]] if "correction" in day else []) + day["asks"]:
            replies.append(X.say(loop, text))
        episodes = list(getattr(loop.reasoner, "episodes", []) or [])
        variety = len({e.get("word") for e in episodes})
        t0 = time.time()
        kept = None
        if arm == "SLEEP":
            X.force_sleep(loop)
            kept = bool(gate.last.get("kept"))
        night = {"night": i + 1, "word": day["word"], "episodes": len(episodes), "variety": variety,
                 "kept": kept, "gate_reasons": (gate.last.get("reasons", [])[:6] if gate else []),
                 "sleep_seconds": round(time.time() - t0, 1),
                 "saved_replies": sum(r.startswith(("Saved", "Updated")) for r in replies),
                 "teach_turns": len(day["teach"]) + int("correction" in day)}
        probes = _probes(loop, days[: i + 1], i + 1)
        graded = G.ask_all(loop, probes)
        for g, p in zip(graded, probes):
            g["cat"], g["word"] = p["cat"], p.get("word")
        night["score"] = _score(graded)
        night["words_right"] = {}
        for w in DAYS366[: i + 1]:
            rs = [g for g in graded if g["kind"] == "W" and g["word"] == w]
            night["words_right"][w] = f"{sum(g['grade'] == 'right' for g in rs)}/{len(rs)}"
        nights.append(night)
        del loop
    return {"arm": arm, "seed": seed, "nights": nights, "seconds": round(time.time() - t_all, 1)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", default="1,2")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    root = tempfile.mkdtemp(prefix="slp366-")
    jobs = [(int(s), arm, root) for s in args.seeds.split(",") for arm in ("SLEEP", "NOSLEEP")]
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        res = list(ex.map(run_arm, jobs))
    full = {"runs": res}
    full["marks"] = marks366(full)
    Path(args.out).write_text(json.dumps(full, indent=1), encoding="utf-8")
    print(json.dumps(full["marks"], indent=1))
    for r in res:
        print(r["arm"], r["seed"], r["seconds"], "s")
        for n in r["nights"]:
            s = n["score"]
            print(f"  night {n['night']} {n['word']:<26} kept={n['kept']} eps={n['episodes']} "
                  f"taught {s['taught']['right']}/{s['taught']['n']} old {s['word_old']['right']}/{s['word_old']['n']} "
                  f"today {s['word_today']['right']}/{s['word_today']['n']} new {s['word_new']['right']}/{s['word_new']['n']} "
                  f"made-up {s['lure']['made_up']}/{s['lure']['n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ------------------------------------------------------------ registered marks (PASSMARKS in the artifact)
def _frac(s: str) -> tuple[int, int]:
    a, b = s.split("/")
    return int(a), int(b)


def marks366(res: dict) -> dict:
    out = {}
    for seed in sorted({r["seed"] for r in res["runs"]}):
        S = next(r for r in res["runs"] if r["seed"] == seed and r["arm"] == "SLEEP")
        N = next(r for r in res["runs"] if r["seed"] == seed and r["arm"] == "NOSLEEP")
        n = S["nights"]
        learned = {}                                   # word -> night it first scored >= 90% on its own night
        for night in n:
            r, t = _frac(night["words_right"][night["word"]])
            if t and r / t >= 0.9:
                learned[night["word"]] = night["night"]
        keep_ok = True
        for night in n:
            for w, first in learned.items():
                if night["night"] > first:
                    r, t = _frac(night["words_right"][w])
                    if t and r / t < 0.95:
                        keep_ok = False
        new_ok = all(night["score"]["word_new"]["n"] == 0
                     or night["score"]["word_new"]["right"] / night["score"]["word_new"]["n"] >= 0.9
                     for night in n[1:])

        def final_rate(run):
            sc = run["nights"][-1]["score"]
            right = sum(sc[c]["right"] for c in ("word_old", "word_today", "word_new"))
            tot = sum(sc[c]["n"] for c in ("word_old", "word_today", "word_new"))
            return 100.0 * right / tot if tot else 0.0

        out[f"s{seed}"] = {
            "P366.1": all(x["score"]["taught"]["right"] == x["score"]["taught"]["n"] for x in n),
            "P366.2": all(x["score"]["lure"]["made_up"] == 0 for x in n),
            "P366.3": keep_ok and len(learned) >= 1,
            "P366.4": new_ok,
            "P366.5": final_rate(S) - final_rate(N) >= 50.0,
            "detail": {"learned_on_night": learned, "final_word_rate_sleep": round(final_rate(S), 1),
                       "final_word_rate_nosleep": round(final_rate(N), 1),
                       "kept": [x["kept"] for x in n]}}
    return out
