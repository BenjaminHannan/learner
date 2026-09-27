#!/usr/bin/env python3
"""brd-12: can the lucky-hits loop climb from easy key games to a harder level where plain luck is zero, when failed
attempts are relabelled as hits for the room they actually reached (hindsight replay)? Creative research thread,
2026-09-27; problem 7. Plan and draft marks: design/v3/30-modes/brd-12-games-her-plan.md; DEV:
artifacts/claude-brd12-20260927/DEV-NOTE.md.

World: Sleep research's key games (scripts/claude_textgames.py, imported, never edited). Level 0 = 1-2 step plans,
level 1 = 3-8 steps in 5-room mazes with 2 coloured doors. The game text is the prompt (code-made, loss-masked); the
checker simulates any plan. Sampling is plain (no rule keeper; the games have none), thinking off.

Loop (brd-9's recipe otherwise): 3 nights; each night the model that slept the night before practises 200 fresh
level-0 and 200 fresh level-1 games (the same games in both arms). Per game: the greedy reply if it reaches the asked
room, else the first of n_miss samples that does. A kept example is (game, the reply's own action lines up to the
step that reached the room), checked by claude_textgames.check. Each night a fresh LoRA from base is trained on
everything kept so far, 3 epochs (claude_blurt2.train_lora: r16, lr 2e-4, batch 8, prompt masked).
Arms (ONE change):
- H: plus hindsight: for each level-1 game with no hit, up to 2 relabelled examples. Each is the same maze with the
  goal rewritten to a room one sample's legal moves reached (not the start, not the asked room), target = that sample's
  own moves up to that room, checked by claude_textgames.check on the rewritten game.
- A: plus hits from EXTRA fresh level-0 games (practised the same way, in a fixed order) until A has at least as many
  examples that night as H has for the same LoRA seed and night. No repeats.
Test: 240 fresh level-1 games (seeds 901000-901239), ASKED goals only, n samples each, for base, night 1 and night 3
of both arms and every seed. Harm: Fix sleep's 300 items (claude_dl1_nights.harm_panel), greedy, base vs night 3.
Temperature: brd-9's DEV rule (more lucky samples on the DEV games the base misses; 1.0 vs 1.5, ties to 1.0) on DEV
seeds 900000-900019 at levels 0 and 1.

  python -B scripts/claude_brd12.py --model M --out DIR [--temps 1.0,1.5]
  python -B scripts/claude_brd12.py --selftest
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt2 as B2  # noqa: E402
import claude_dl1_nights as D1  # noqa: E402
import claude_textgames as G  # noqa: E402

NIGHTS = 3
TEST_SEEDS = range(901000, 901240)
DEV_SEEDS = range(900000, 900020)
ACT = re.compile(r"^(go|take|make|press)\b")


def night_seeds(k, level):
    """night k (1..3): 200 practice games per level, the same in both arms"""
    return range(902000 + 1000 * k + 500 * level, 902000 + 1000 * k + 500 * level + 200)


def extra_seeds(k):
    """night k's extra level-0 pool for arm A, practised in this order"""
    return range(910000 + 10000 * k, 910000 + 10000 * k + 3000)


def game(seed, level):
    return G.make_game("keys", seed, level)


def act_lines(reply):
    """the reply's action lines in order, as claude_textgames.check reads them (bullets stripped, case kept)"""
    out = []
    for x in reply.splitlines():
        a = re.sub(r"^[\s\-\*\d\.\)]*", "", x).strip()
        if ACT.match(a.lower().rstrip(".")):
            out.append(a)
    return out


def own_target(g, reply):
    """(ok, target): target = the reply's own action lines up to the step that reached the goal"""
    c = G.check(g, reply)
    return c["ok"], "\n".join(act_lines(reply)[:c["steps"]]) if c["ok"] else ""


def walk_rooms(g, reply):
    s, moves, _ = G._start_and_moves(g)
    rooms = []
    for a in act_lines(reply):
        nxt = dict((x.lower(), t) for x, t in moves(s)).get(a.lower().rstrip("."))
        if nxt is None:
            break
        s = nxt
        rooms.append(s[0])
    return rooms


def relabelled(g, replies, cap=2):
    """hindsight examples: same maze, goal = a room a sample's legal moves reached (not start, not asked goal)"""
    out, used = [], set()
    for t in replies:
        for r in walk_rooms(g, t):
            if len(out) >= cap:
                return out
            if r in used or r in (g["start"], g["goal"]):
                continue
            h = dict(g, goal=r)
            h["text"] = G.keys_text(h)
            ok, tgt = own_target(h, t)
            if ok:
                used.add(r)
                out.append((h, tgt))
    return out


class GameSolver(B2.Solver):
    """claude_blurt2.Solver with the game text as the prompt and plain sampling (no rule keeper)."""

    def prompt(self, g) -> str:
        return self.tok.apply_chat_template([{"role": "user", "content": g["text"]}], tokenize=False,
                                            add_generation_prompt=True, enable_thinking=False)

    def generate(self, g, n, temp, model=None):
        m = model or self.model
        ids = self.tok(self.prompt(g), return_tensors="pt").to(self.dev)
        cut = ids["input_ids"].shape[1]
        kw = {"do_sample": True, "temperature": temp, "top_p": 1.0, "num_return_sequences": n} if temp else \
             {"do_sample": False}
        with self.torch.no_grad():
            out = m.generate(**ids, max_new_tokens=12 * len(g["plan"]) + 24, pad_token_id=self.tok.eos_token_id,
                             **kw)
        return [self.tok.decode(o[cut:], skip_special_tokens=True).strip() for o in out]


def practise(s, g, n_miss, temp, model, her):
    """one game -> (examples, row)"""
    ok, tgt = own_target(g, s.answer(g, model))
    if ok:
        return [(g, tgt)], {"seed": g["seed"], "level": g["level"], "kind": "own", "her": 0}
    reps = s.generate(g, n_miss, temp, model)
    for t in reps:
        ok, tgt = own_target(g, t)
        if ok:
            return [(g, tgt)], {"seed": g["seed"], "level": g["level"], "kind": "win", "her": 0}
    ex = relabelled(g, reps) if her and g["level"] == 1 else []
    return ex, {"seed": g["seed"], "level": g["level"], "kind": "miss", "her": len(ex)}


def gather(s, games, n_miss, temp, model, her):
    ex, rows = [], []
    for g in games:
        e, r = practise(s, g, n_miss, temp, model, her)
        ex += e
        rows.append(r)
    return ex, rows


def coverage(s, games, n, temp, model=None):
    out = []
    for g in games:
        hits = [G.check(g, t)["ok"] for t in s.generate(g, n, temp, model)]
        out.append((hits.index(True) + 1 if any(hits) else 0, sum(hits)))
    return out


def summ(st, games):
    r = {f"cov@{k}": sum(1 for f, _ in st if 0 < f <= k) for k in (1, 5, 10, 30)}
    r["lucky"] = sum(h for _, h in st)
    r["cov@30_by_plan_len"] = {}
    for (f, _), g in zip(st, games):
        d = r["cov@30_by_plan_len"].setdefault(str(len(g["plan"])), [0, 0])
        d[0] += f > 0
        d[1] += 1
    return r


def boot_ci(a_streams, b_streams, reps=2000, seed=0):
    """game-level bootstrap of the mean cov@30 difference (a - b) in points of the panel, averaged over seeds"""
    n, rng, diffs = len(a_streams[0]), random.Random(seed), []
    for _ in range(reps):
        idx = [rng.randrange(n) for _ in range(n)]
        da = sum(sum(1 for i in idx if st[i][0] > 0) for st in a_streams) / len(a_streams)
        db = sum(sum(1 for i in idx if st[i][0] > 0) for st in b_streams) / len(b_streams)
        diffs.append((da - db) / n)
    diffs.sort()
    return round(diffs[int(0.025 * reps)] * 100, 2), round(diffs[int(0.975 * reps)] * 100, 2)


def counts(rows):
    r = {f"L{lv}_{k}": sum(x["kind"] == k and x["level"] == lv for x in rows) for lv in (0, 1)
         for k in ("own", "win", "miss")}
    r["her_examples"] = sum(x["her"] for x in rows)
    return r


def pick_temp(s, temps, n):
    temps = [float(t) for t in temps.split(",")]
    dev = [game(sd, lv) for lv in (0, 1) for sd in DEV_SEEDS]
    missed = [g for g in dev if not G.check(g, s.answer(g))["ok"]]
    c = {str(t): sum(G.check(g, x)["ok"] for g in missed for x in s.generate(g, n, t)) for t in temps}
    best = max(temps, key=lambda t: (c[str(t)], -temps.index(t)))
    print(f"[dev] lucky by T {c} on {len(missed)} missed DEV games -> T {best}", flush=True)
    return best, {"dev_missed": len(missed), "dev_lucky_by_temp": c, "temp_chosen": best}


def worlds():
    """test games; each night's practice games; each night's extra level-0 pool. Every practice game is distinct from
    the test and DEV games and from every earlier practice game (same game text = same game)."""
    test = [game(sd, 1) for sd in TEST_SEEDS]
    seen = {g["text"] for g in test} | {game(sd, lv)["text"] for lv in (0, 1) for sd in DEV_SEEDS}

    def fresh(gs):
        out = []
        for g in gs:
            if g["text"] not in seen:
                seen.add(g["text"])
                out.append(g)
        return out
    nights = [fresh(game(sd, lv) for lv in (0, 1) for sd in night_seeds(k, lv)) for k in range(1, NIGHTS + 1)]
    extras = [fresh(game(sd, 0) for sd in extra_seeds(k)) for k in range(1, NIGHTS + 1)]
    return test, nights, extras


def distinct_check(test, *sets):
    tt = {g["text"] for g in test}
    for gs in sets:
        assert not tt & {g["text"] for g in gs}, "a practice or DEV game equals a test game"


def run(a):
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = GameSolver(a.model)
    s.model.name_or_path = a.model
    test, nights, extras = worlds()
    distinct_check(test, [game(sd, lv) for lv in (0, 1) for sd in DEV_SEEDS], *nights, *extras)
    harm = D1.harm_panel()[:a.n_harm]
    temp, res = pick_temp(s, a.temps, a.n)
    res.update({"temp": temp, "n_test": len(test), "night_games": [len(x) for x in nights]})
    base = coverage(s, test, a.n, temp)
    res["base"] = summ(base, test)
    base_harm = D1.harm_scores(s, s.model, harm)
    res["base_harm_right"] = sum(base_harm)
    print(f"[brd12] base {res['base']} harm right {res['base_harm_right']}", flush=True)
    streams, log = {}, {}
    for sd in [int(x) for x in a.lora_seeds.split(",")]:
        ex = {"H": [], "A": []}
        m = {"H": None, "A": None}
        for k in range(1, NIGHTS + 1):
            eh, rh = gather(s, nights[k - 1], a.n_miss, temp, m["H"], True)
            ea, ra = gather(s, nights[k - 1], a.n_miss, temp, m["A"], False)
            used = 0
            for g in extras[k - 1]:
                if len(ea) >= len(eh):
                    break
                e, r = practise(s, g, a.n_miss, temp, m["A"], False)
                ea += e
                ra.append(dict(r, extra=1))
                used += 1
            ex["H"] += eh
            ex["A"] += ea
            res[f"night{k}_seed{sd}"] = {"H": counts(rh) | {"examples": len(eh)},
                                         "A": counts(ra) | {"examples": len(ea), "extra_games": used,
                                                            "matched": len(ea) >= len(eh)}}
            log[f"H_night{k}_seed{sd}"], log[f"A_night{k}_seed{sd}"] = rh, ra
            print(f"[brd12] seed {sd} night {k} practice {res[f'night{k}_seed{sd}']}", flush=True)
            for arm in ("H", "A"):
                old, m[arm] = m[arm], None
                del old
                if s.dev == "cuda":
                    s.torch.cuda.empty_cache()
                m[arm] = B2.train_lora(s, list(ex[arm]), a.epochs, sd)
                if k in (1, NIGHTS):
                    st = coverage(s, test, a.n, temp, m[arm])
                    streams.setdefault(f"{arm}{k}", []).append(st)
                    res[f"{arm}{k}_seed{sd}"] = summ(st, test) | {"examples": len(ex[arm])}
                if k == NIGHTS:
                    res[f"{arm}{k}_seed{sd}"]["harm"] = D1.flips(base_harm, D1.harm_scores(s, m[arm], harm))
                print(f"[brd12] {arm} seed {sd} night {k}: {res.get(f'{arm}{k}_seed{sd}', 'trained')}", flush=True)
        m = None
        if s.dev == "cuda":
            s.torch.cuda.empty_cache()
        (out / "practice.json").write_text(json.dumps(log), encoding="utf-8")
        (out / "brd12_partial.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for name, x, y in (("H3_minus_A3", "H3", "A3"), ("H3_minus_base", "H3", None), ("A3_minus_base", "A3", None),
                       ("H1_minus_A1", "H1", "A1"), ("H3_minus_H1", "H3", "H1"), ("A3_minus_A1", "A3", "A1")):
        res[f"ci95_{name}_cov30_pct"] = boot_ci(streams[x], streams[y] if y else [base])
    (out / "streams.json").write_text(json.dumps({"base": base, **streams}), encoding="utf-8")
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "brd12_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def selftest():
    g = game(900000, 1)
    plan = "\n".join(g["plan"])
    assert own_target(g, "Sure:\n1. " + plan.replace("\n", "\n- ") + "\nDone.") == (True, plan)
    assert own_target(g, g["plan"][0]) == (False, "")
    h = relabelled(g, [g["plan"][0]])
    assert len(h) == 1 and h[0][0]["goal"] != g["goal"] and G.check(h[0][0], h[0][1])["ok"]
    assert h[0][0]["text"].startswith(f"You are in {g['start']}. Get to {h[0][0]['goal']}.")
    assert relabelled(g, ["go Nowhere"]) == [] and len(relabelled(g, [plan], cap=2)) <= 2
    test = [game(sd, 1) for sd in list(TEST_SEEDS)[:40]]
    assert len({x["text"] for x in test}) == 40
    assert all(set(night_seeds(k, lv)).isdisjoint(TEST_SEEDS) for k in (1, 2, 3) for lv in (0, 1))
    assert min(night_seeds(1, 0)) > max(TEST_SEEDS) and max(extra_seeds(3)) < 1_000_000
    t, ns, xs = worlds()
    allp = [g["text"] for x in ns + xs for g in x]
    assert len(allp) == len(set(allp)) and not set(allp) & {g["text"] for g in t}
    assert all(len(x) >= 390 for x in ns) and all(len(x) >= 2500 for x in xs)
    assert boot_ci([[(1, 1), (0, 0)]], [[(0, 0), (0, 0)]], reps=50)[1] > 0
    print("brd12 selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--n-miss", type=int, default=30)
    ap.add_argument("--n-harm", type=int, default=300)
    ap.add_argument("--temps", default="1.0,1.5")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lora-seeds", default="0,1,2")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        run(a)


if __name__ == "__main__":
    main()
