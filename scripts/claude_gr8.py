#!/usr/bin/env python3
"""gr-8 dev: the reader's own likelihood picks the grid size (Plain-English puzzles thread, 2026-09-27; PLAN-gr8d.md).

gr-7d (RESULT-gr7d, 07ccf04be) found, post hoc, that 11 of the gr-7 reader's 16 wrong grids on a practice set had the
wrong size. Most were one size too big, and the extra cells were padded with blanks. In gr-4's grammar the first row's
length fixes the size, so one early step decides it. The one change here is how the size is chosen, with no training:
  1. The reader (gr-7's adapter, L7) copies greedily under gr-4's grammar, exactly as `claude_gr7.py run` does. If it
     writes none, or its grid is not kept, that is the answer.
  2. Otherwise, the same reader copies again with the grammar forced to each other size from 3 to 9, greedily.
  3. Each copy is scored by its TOTAL log-probability under the reader, over the whole vocabulary, including the
     closing token. A total, not a mean per cell, so padding a too-big grid with blanks costs more cells and cannot
     win by being easy (the Thread manager's 09:36 point).
  4. The kept grid with the highest total wins. A forced copy is stopped as soon as its running total falls below the
     best total so far; log-probabilities are never positive, so this gives the same winner as scoring every copy fully.
The grammar and the argmax over sizes are code (disclosed scaffolding). The probabilities are the reader's own.

  python -B scripts/claude_gr8.py --selftest
  python -B scripts/claude_gr8.py make --out PRACTICE_DIR
  python -B scripts/claude_gr8.py run --task squares|unseen|lookalikes|replay --model BASE --adapter L7.pt \
      --practice PRACTICE_DIR --out OUT
  python -B scripts/claude_gr8.py count --practice PRACTICE_DIR --run OUT
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_gr1 as G1  # noqa: E402
import claude_gr4 as G4  # noqa: E402
import claude_gr5 as G5  # noqa: E402
import claude_gr6 as G6  # noqa: E402
import claude_gr7_diag as DG  # noqa: E402

ROOT = SCRIPTS.parent
SEED_SQ, SEED_UN, SEED_FMT, SEED_LK, SEED_WRAP = 5081, 5082, 5083, 5084, 5085
SIZES = range(3, 10)
GR7D = ROOT / "artifacts/claude-gr7d-20260927"


# ------------------------------------------------------------------ a fresh practice set (gr-7d's maker, new seeds)
def draw_formats():
    """40 formats as gr-7d drew them (seed 5083), also unlike every gr-7d format"""
    rng = random.Random(SEED_FMT)
    lay = G6.draw_layouts()
    taken = G6.gr1_signatures() | {G6.signature(r) for r in lay} | {G6.signature(f) for f in DG.draw_formats()}
    seen = sorted(G6.training_seps(lay))
    seen_raw = [s for s in G6.SEPS if G6._norm(s) in seen]
    out = []
    for group, seps in (("seen", seen_raw), ("new", DG.NEW_SEPS)):
        n = 0
        while n < DG.N_FORMATS // 2:
            rc = DG._draw_format(rng, seps)
            sg = G6.signature(rc)
            if sg in taken:
                continue
            if rc["row_join"] not in ("\n", "\n\n") and G6._norm(rc["row_join"]) == G6._norm(rc["sep"]):
                continue
            ns = G6._norm(rc["sep"])
            if ns and (ns in G6._norm(rc["row_prefix"]) or ns in G6._norm(rc["row_suffix"])):
                continue
            taken.add(sg)
            out.append(dict(rc, id="F%02d" % len(out), group=group))
            n += 1
    return out


def make(a) -> None:
    import claude_gr5_make_panel as M5
    import claude_puzzle_reader as R
    import claude_rsn358b2_bridge as B
    import claude_rsn358b3_panel as P3
    rng = random.Random(SEED_WRAP)
    wr = G5._load(G6.GR1_WRAP)
    openers = [r["text"] for r in wr if r["keep"] and r["kind"] == "opener"]
    closers = [r["text"] for r in wr if r["keep"] and r["kind"] == "closer"]
    everyday = [r["raw"] for r in G5._load(G6.RT02H)]
    squares, mism = [], 0
    for i, (s, puz, broken) in enumerate(M5.squares_for(B, P3, SEED_SQ, DG.N_PER_SIZE)):
        layout = "row" if i % 2 == 0 else "bare"
        sq, cells = G1.render_recipe(puz, G1.layout_recipe(layout, s))
        text, cells = DG._wrap(rng, openers, closers, sq, cells)
        mism += int((R.read_latin(text) or {}).get("grid") != puz)
        squares.append({"id": "d8-sq-%03d" % i, "text": text, "size": s, "grid": puz, "broken": broken,
                        "layout": layout, "cells": cells})
    fm = draw_formats()
    unseen = []
    for i, (s, puz, broken) in enumerate(M5.squares_for(B, P3, SEED_UN, DG.N_PER_SIZE)):
        f = fm[i % DG.N_FORMATS]
        sq, cells = G1.render_recipe(puz, f)
        text, cells = DG._wrap(rng, openers, closers, sq, cells)
        unseen.append({"id": "d8-un-%03d" % i, "text": text, "size": s, "grid": puz, "broken": broken,
                       "format_id": f["id"], "sep_seen": f["group"] == "seen", "cells": cells})
    lrng = random.Random(SEED_LK)
    rec = G6.training_recipes(G6.draw_layouts())
    looks, redrawn = [], Counter()
    for kind in ("near", "nonsquare", "numbers"):
        n = 0
        while n < DG.N_LK_KIND:
            if kind == "near":
                s = lrng.randint(3, 7)
                shape = (s, s)
                g = [[lrng.randint(1, 9) for _ in range(s)] for _ in range(s)]
                if max(v for row in g for v in row) <= s:
                    g[lrng.randrange(s)][lrng.randrange(s)] = lrng.randint(s + 1, 9)
            elif kind == "nonsquare":
                r, c = lrng.sample(range(3, 8), 2)
                shape = (r, c)
                g = [[lrng.randint(1, max(r, c)) for _ in range(c)] for _ in range(r)]
            else:
                s = lrng.randint(3, 7)
                shape = (s, s)
                g = [[lrng.randint(1, 40) for _ in range(s)] for _ in range(s)]
                if max(v for row in g for v in row) < 10:
                    g[lrng.randrange(s)][lrng.randrange(s)] = lrng.randint(10, 40)
            if lrng.random() < 0.5 and kind != "numbers":
                g = [[0 if lrng.random() < 0.25 else v for v in row] for row in g]
            src, rc = lrng.choice(rec)
            blk = G1.render_recipe(g, G1.layout_recipe(rc, shape[1], lrng.randrange(4)) if src == "gr1" else rc)[0]
            t = lrng.choice(everyday + openers)
            text = t + "\n" + blk if lrng.random() < 0.6 else blk + "\n" + t
            if R.read_latin(text) is not None:
                redrawn[kind] += 1
                continue
            looks.append({"id": "d8-lk-%03d" % len(looks), "text": text, "square": None, "kind": kind,
                          "shape": list(shape)})
            n += 1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    seal = []
    for name, rows in (("squares.jsonl", squares), ("unseen.jsonl", unseen), ("lookalikes.jsonl", looks)):
        p = out / name
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        seal.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {name}")
    p = out / "formats.json"
    p.write_text(json.dumps(fm, ensure_ascii=False, indent=1), encoding="utf-8")
    seal.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  formats.json")
    (out / "SEAL-practice.sha256.txt").write_text("\n".join(seal) + "\n")
    print(json.dumps({"squares": len(squares), "squares_broken": sum(r["broken"] for r in squares),
                      "squares_read_latin_mismatch": mism, "unseen": len(unseen),
                      "unseen_sep_seen": sum(r["sep_seen"] for r in unseen), "formats": len(fm),
                      "lookalikes": len(looks), "lookalikes_redrawn_read_latin_square": dict(redrawn)}))


# ------------------------------------------------------------------ the size pick
class Copier8(G5.Copier5):
    def _decode(self, past0, logits0, m, allow_none, bound):
        """greedy constrained copy from the prompt's cache; (tokens, total log-prob incl. the closing token, machine),
        or None if the running total falls below bound"""
        torch = self.torch
        past, logits, out, total = copy.deepcopy(past0), logits0, [], 0.0
        for step in range(G4.MAX_NEW):
            if m.mode == "none":
                break
            opts = self.allowed(m, allow_none and step == 0)
            cand = list(opts)
            if m.can_end():
                cand.append(self.eos)
            if not cand:
                break
            idx = torch.tensor(cand, device=logits.device)
            pick = cand[int(logits[idx].argmax())]
            total += float(torch.log_softmax(logits.float(), -1)[pick])
            if bound is not None and total < bound:
                return None
            if pick == self.eos:
                break
            m = opts[pick]
            out.append(pick)
            r = self.model(input_ids=torch.tensor([[pick]], device=logits.device), past_key_values=past,
                           use_cache=True)
            past, logits = r.past_key_values, r.logits[0, -1]
        return out, total, m

    def _grid(self, out, m):
        raw = self.tok.decode(out)
        raw = raw.lower() if m.mode == "none" else raw
        ok = m.mode == "none" or m.can_end()
        return (G4.parse(raw) if ok else None), ok

    def copy8(self, text):
        torch = self.torch
        ids = G5.prompt_ids(self.one_b, text).unsqueeze(0).to(self.one_b.dev)
        with torch.no_grad():
            r = self.model(input_ids=ids, use_cache=True)
            past0, logits0 = r.past_key_values, r.logits[0, -1]
            out, total, m = self._decode(past0, logits0, G4.Machine(), True, None)
            greedy, complete = self._grid(out, m)
            res = {"greedy": greedy, "complete": complete, "pick": greedy, "scores": {}}
            if greedy is None:
                return res
            best, best_total = greedy, total
            res["scores"][str(len(greedy))] = round(total, 3)
            for s in SIZES:
                if s == len(greedy):
                    continue
                got = self._decode(past0, logits0, G4.Machine("start", 0, 0, s), False, best_total)
                if got is None:
                    res["scores"][str(s)] = "stopped"
                    continue
                g, _ = self._grid(got[0], got[2])
                if g is None:
                    res["scores"][str(s)] = "not kept"
                    continue
                res["scores"][str(s)] = round(got[1], 3)
                if got[1] > best_total:
                    best, best_total = g, got[1]
            res["pick"] = best
        return res


def run(a) -> None:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"L8_{a.task}.jsonl"
    if path.exists():
        raise SystemExit(f"gr8: {path} exists (each run is launched once)")
    src = GR7D / "practice/unseen.jsonl" if a.task == "replay" else Path(a.practice) / f"{a.task}.jsonl"
    items = G5._load(src)
    cp = Copier8(G5.load(a.model, a.adapter), plain=False)
    with path.open("w", encoding="utf-8") as f:
        for it in items:
            t0 = time.time()
            r = cp.copy8(it["text"])
            f.write(json.dumps({"id": it["id"], **r, "ms": round((time.time() - t0) * 1000, 1)}) + "\n")
            f.flush()
    rows = G5._load(path)
    print(json.dumps({"task": a.task, "rows": len(rows), "greedy_grid": sum(r["greedy"] is not None for r in rows),
                      "pick_differs": sum(r["pick"] != r["greedy"] for r in rows)}))


# ------------------------------------------------------------------ the count (PLAN-gr8d's marks)
def _res(g, t):
    return "exact" if g == t else ("none" if g is None else "wrong")


def count(a) -> None:
    pd, rd = Path(a.practice), Path(a.run)
    st = Counter()
    for task in ("squares", "unseen", "lookalikes"):
        truth = {r["id"]: r for r in G5._load(pd / f"{task}.jsonl")}
        got = G5._load(rd / f"L8_{task}.jsonl")
        assert sorted(r["id"] for r in got) == sorted(truth), f"gr8: {task} ids differ"
        st[f"{task}_incomplete"] += sum(not r["complete"] for r in got)
        for r in got:
            t = truth[r["id"]]
            for arm in ("greedy", "pick"):
                g = r[arm]
                if task == "lookalikes":
                    st[f"lookalikes_{arm}_false"] += int(g is not None)
                    continue
                grp = task if task == "squares" else ("unseen_sepseen" if t["sep_seen"] else "unseen_sepnew")
                res = _res(g, t["grid"])
                st[f"{grp}_{arm}_{res}"] += 1
                st[f"{task}_{arm}_{res}"] += 1
                if res == "wrong" and len(g) != len(t["grid"]):
                    st[f"{task}_{arm}_wrong_size"] += 1
            if task != "lookalikes" and r["greedy"] == t["grid"] and r["pick"] != t["grid"]:
                st["harmed_exact_to_not"] += 1
            if task != "lookalikes" and r["greedy"] != t["grid"] and r["pick"] == t["grid"]:
                st["fixed_not_to_exact"] += 1
    # the replay: gr-7d's unseen set, where L7's greedy reads are on file
    truth = {r["id"]: r for r in G5._load(GR7D / "practice/unseen.jsonl")}
    old = {r["id"]: r["grid"] for r in G5._load(GR7D / "run/L7_unseen.jsonl")}
    rp = G5._load(rd / "L8_replay.jsonl")
    assert sorted(r["id"] for r in rp) == sorted(truth), "gr8: replay ids differ"
    st["replay_greedy_equals_gr7d_L7"] = sum(r["greedy"] == old[r["id"]] for r in rp)
    wrong_size = [i for i, g in old.items() if g is not None and g != truth[i]["grid"] and len(g) != len(truth[i]["grid"])]
    st["replay_gr7d_wrong_size_n"] = len(wrong_size)
    by = {r["id"]: r for r in rp}
    for i in wrong_size:
        p, n = by[i]["pick"], len(truth[i]["grid"])
        st["replay_pick_exact"] += int(p == truth[i]["grid"])
        st["replay_pick_still_wrong_size"] += int(p is not None and len(p) != n)
        st["replay_pick_still_too_big"] += int(p is not None and len(p) > n)
    for r in rp:
        st["replay_all_greedy_exact"] += int(r["greedy"] == truth[r["id"]]["grid"])
        st["replay_all_pick_exact"] += int(r["pick"] == truth[r["id"]]["grid"])
    gw, pw = st["unseen_greedy_wrong"], st["unseen_pick_wrong"]
    marks = {
        "D1_unseen_wrong_halved": None if gw < 8 else pw * 2 <= gw,
        "D2_squares_no_loss": st["squares_pick_exact"] >= st["squares_greedy_exact"],
        "D3_false_not_up": st["lookalikes_pick_false"] <= st["lookalikes_greedy_false"],
        "D4_harm_at_most_2": st["harmed_exact_to_not"] <= 2,
        "P_replay_at_most_3_wrong_size": st["replay_pick_still_wrong_size"] <= 3,
        "R0_replay_greedy_matches": st["replay_greedy_equals_gr7d_L7"] == len(rp),
    }
    proved_wrong = st["replay_pick_still_too_big"] >= 6
    if not marks["R0_replay_greedy_matches"]:
        outcome = "MISMATCH (the greedy copy does not repeat gr-7d's)"
    elif proved_wrong:
        outcome = "PROVED-WRONG (the score still pays for padding)"
    elif marks["D1_unseen_wrong_halved"] is None:
        outcome = "TOO-FEW"
    else:
        outcome = "DEV-PASS" if all(marks.values()) else "DEV-FAIL"
    print(json.dumps(dict(sorted(st.items()))))
    print(json.dumps({**marks, "proved_wrong": proved_wrong, "outcome": outcome}))


# ------------------------------------------------------------------ selftest
def selftest() -> None:
    ok = 0
    m = G4.Machine("start", 0, 0, 4)
    ok += m.feed("1 2 3\n") is None                     # a forced size-4 row cannot end after 3 cells
    ok += m.feed("1 2 3 4 5") is None                   # nor take a fifth cell
    m2 = m.feed("1 2 3 4\n_ _ _ _\n_ _ _ _\n_ _ _ 1")
    ok += m2 is not None and m2.can_end()
    fm = draw_formats()
    old = {G6.signature(f) for f in DG.draw_formats()}
    ok += len(fm) == DG.N_FORMATS and not ({G6.signature(f) for f in fm} & old)
    print(f"gr8 selftest {ok}/4")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--out", required=True)
    r = sub.add_parser("run")
    for k in ("task", "model", "adapter", "practice", "out"):
        r.add_argument("--" + k, required=True)
    c = sub.add_parser("count")
    c.add_argument("--practice", required=True)
    c.add_argument("--run", required=True)
    a = ap.parse_args()
    {"make": make, "run": run, "count": count}[a.cmd](a)


if __name__ == "__main__":
    main()
