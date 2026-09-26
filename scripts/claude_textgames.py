#!/usr/bin/env python3
"""Code-made text games (sleep research thread, 2026-09-26; Ben 15:55 UTC: "What if we gave the model text based
games to train on?"). No outside game sets, fictional names only.

Three kinds, each with a difficulty knob `level` (1 = tiny; 0 = 1-2 step plans, added for Creative's curriculum), a seeded generator, an exact simulator, a shortest-plan
solver (breadth-first, fixed action order, so the canonical plan is unique) and a checker that accepts ANY valid
plan (optimality reported separately):
  keys      rooms joined by passages, some passages behind coloured doors; keys lie in rooms. Reach the goal room.
            actions: "go <room>", "take <key>"
  recipes   an inventory and rules "A + B -> C"; making C uses up A and B. End holding the goal item.
            actions: "make <item>"
  switches  lamps that are on or off; each switch flips a fixed set of lamps. Reach the goal pattern.
            actions: "press <switch>"
Every game has two forms: `text` (a chat prompt ending with the reply format: one action per line) for the 1B, and
`state` (plain Python data) for the small nets. The small nets' token-grid encoding is a later step.

  python -B scripts/claude_textgames.py selftest
  python -B scripts/claude_textgames.py sample --kind keys --level 2 --seed 7
"""
from __future__ import annotations

import argparse
import json
import random
import re
from collections import deque

ROOMS = ["Amberly", "Brisk Hall", "Cobble Nook", "Dunmere", "Elm Loft", "Fernway", "Glimmer Den", "Hollow Keep",
         "Ivystone", "Juniper Court", "Kestrel Attic", "Lantern Cellar"]
COLOURS = ["red", "blue", "green", "gold", "violet"]
ITEMS = ["flint", "twine", "reed", "clay", "salt", "moss", "ash", "wax", "pebble", "feather", "thorn", "honey",
         "resin", "copper", "chalk", "linen"]
LAMPS = ["L1", "L2", "L3", "L4", "L5", "L6"]
SWITCHES = ["S1", "S2", "S3", "S4", "S5", "S6"]
KINDS = ["keys", "recipes", "switches"]
MAX_STATES = 200000


def _bfs(start, moves, is_goal):
    """shortest plan; moves(state) -> [(action, next_state)] in a fixed order"""
    prev, q = {start: None}, deque([start])
    while q:
        s = q.popleft()
        if is_goal(s):
            plan = []
            while prev[s] is not None:
                s, a = prev[s]
                plan.append(a)
            return plan[::-1]
        for a, t in moves(s):
            if t not in prev:
                prev[t] = (s, a)
                q.append(t)
                if len(prev) > MAX_STATES:
                    return None
    return None


# ---------------- keys ----------------
def _keys_moves(g):
    adj = {}
    for a, b, door in g["passages"]:
        adj.setdefault(a, []).append((b, door)); adj.setdefault(b, []).append((a, door))
    for r in adj:
        adj[r].sort()

    def moves(s):
        room, held = s
        out = []
        for k, where in sorted(g["keys"].items()):
            if where == room and k not in held:
                out.append((f"take {k} key", (room, tuple(sorted(held + (k,))))))
        for nb, door in adj.get(room, []):
            if door is None or door in held:
                out.append((f"go {nb}", (nb, held)))
        return out
    return moves


def make_keys(rng, level):
    n = min(len(ROOMS), 3 + 2 * level)
    rooms = rng.sample(ROOMS, n)
    passages = [(rooms[i], rooms[rng.randrange(i)], None) for i in range(1, n)]      # a random tree
    for _ in range(level):                                                          # a few extra loops
        a, b = rng.sample(rooms, 2)
        if not any({a, b} == {x, y} for x, y, _ in passages):
            passages.append((a, b, None))
    colours = rng.sample(COLOURS, min(len(COLOURS), level + 1))
    locked = rng.sample(range(len(passages)), min(len(colours), len(passages)))
    for c, i in zip(colours, locked):
        a, b, _ = passages[i]
        passages[i] = (a, b, c)
    start = rng.choice(rooms)
    keys = {c: rng.choice(rooms) for c in colours}
    g = {"kind": "keys", "rooms": rooms, "passages": passages, "keys": keys, "start": start, "goal": None}
    best = []                                                           # goal = a room with the longest shortest plan
    for r in rooms:
        if r != start:
            g["goal"] = r
            plan = keys_solve(g)
            if plan and (not best or len(plan) > best[0][0]):
                best = [(len(plan), r)]
            elif plan and len(plan) == best[0][0]:
                best.append((len(plan), r))
    g["goal"] = rng.choice(best)[1] if best else rng.choice([r for r in rooms if r != start])
    return g


def keys_text(g):
    lines = [f"You are in {g['start']}. Get to {g['goal']}."]
    for a, b, door in g["passages"]:
        lines.append(f"A passage joins {a} and {b}" + (f", behind a {door} door." if door else "."))
    for k, where in sorted(g["keys"].items()):
        lines.append(f"The {k} key is in {where}.")
    lines.append("A door opens only if you carry its key. Reply with your moves, one per line, "
                 "like \"go <room>\" or \"take <colour> key\".")
    return "\n".join(lines)


def keys_solve(g):
    return _bfs((g["start"], ()), _keys_moves(g), lambda s: s[0] == g["goal"])


# ---------------- recipes ----------------
def make_recipes(rng, level):
    pool = rng.sample(ITEMS, min(len(ITEMS), 6 + 2 * level))
    base, made = pool[: 3 + level], pool[3 + level:]
    rules, have = [], list(base)
    for i, c in enumerate(made):
        a = made[i - 1] if i and rng.random() < 0.7 else rng.choice(have)   # mostly chains: deeper goals
        b = rng.choice([x for x in have if x != a])
        rules.append((a, b, c))
        have.append(c)
    goal = made[-1]
    inv = {x: 0 for x in base}
    need = [goal]                                                       # stock enough raw items for one route
    while need:
        x = need.pop()
        r = next((r for r in rules if r[2] == x), None)
        if r is None:
            inv[x] += 1
        else:
            need += [r[0], r[1]]
    for _ in range(level):                                              # a few spare items as distractors
        inv[rng.choice(base)] += 1
    rng.shuffle(rules)
    return {"kind": "recipes", "rules": rules, "inventory": inv, "goal": goal}


def _recipe_moves(g):
    names = sorted({x for r in g["rules"] for x in r} | set(g["inventory"]))

    def moves(s):
        inv = dict(zip(names, s))
        out = []
        for a, b, c in sorted(g["rules"], key=lambda r: r[2]):
            if (inv[a] >= 2 if a == b else inv[a] >= 1 and inv[b] >= 1):
                n2 = dict(inv); n2[a] -= 1; n2[b] -= 1; n2[c] += 1
                out.append((f"make {c}", tuple(n2[k] for k in names)))
        return out
    return names, moves


def recipes_text(g):
    lines = ["You hold: " + ", ".join(f"{n} {x}" for x, n in sorted(g["inventory"].items()) if n) + "."]
    for a, b, c in g["rules"]:
        lines.append(f"{a} + {b} -> {c}")
    lines.append(f"Making an item uses up the two items it is made from. End up holding {g['goal']}. "
                 "Reply with your steps, one per line, like \"make <item>\".")
    return "\n".join(lines)


def recipes_solve(g):
    names, moves = _recipe_moves(g)
    start = tuple(g["inventory"].get(k, 0) for k in names)
    gi = names.index(g["goal"])
    return _bfs(start, moves, lambda s: s[gi] >= 1)


# ---------------- switches ----------------
def make_switches(rng, level):
    k = min(len(LAMPS), 2 + level)
    lamps, sw = LAMPS[:k], SWITCHES[:k]
    flips = {s: sorted(rng.sample(lamps, rng.randint(1, max(1, k - 1)))) for s in sw}
    start = {l: rng.random() < 0.5 for l in lamps}
    presses = rng.sample(sw, rng.randint(1, k))                        # the goal is reachable by construction
    goal = dict(start)
    for s in presses:
        for l in flips[s]:
            goal[l] = not goal[l]
    if goal == start:
        goal[lamps[0]] = not goal[lamps[0]]
        flips[sw[0]] = sorted(set(flips[sw[0]]) ^ {lamps[0]}) or [lamps[0]]
        goal = dict(start)
        for s in presses:
            for l in flips[s]:
                goal[l] = not goal[l]
    return {"kind": "switches", "lamps": lamps, "flips": flips, "start": start, "goal": goal}


def switches_text(g):
    on = lambda d: ", ".join(l for l in g["lamps"] if d[l]) or "none"
    lines = [f"Lamps on now: {on(g['start'])}. Lamps that should be on at the end: {on(g['goal'])}."]
    for s, ls in sorted(g["flips"].items()):
        lines.append(f"Pressing {s} flips {', '.join(ls)}.")
    lines.append("Reply with your presses, one per line, like \"press <switch>\".")
    return "\n".join(lines)


def _switch_moves(g):
    lamps = g["lamps"]

    def moves(s):
        out = []
        for sw, ls in sorted(g["flips"].items()):
            t = list(s)
            for l in ls:
                t[lamps.index(l)] ^= 1
            out.append((f"press {sw}", tuple(t)))
        return out
    return moves


def switches_solve(g):
    start = tuple(int(g["start"][l]) for l in g["lamps"])
    goal = tuple(int(g["goal"][l]) for l in g["lamps"])
    return _bfs(start, _switch_moves(g), lambda s: s == goal)


# ---------------- common ----------------
MAKERS = {"keys": make_keys, "recipes": make_recipes, "switches": make_switches}
TEXT = {"keys": keys_text, "recipes": recipes_text, "switches": switches_text}
SOLVE = {"keys": keys_solve, "recipes": recipes_solve, "switches": switches_solve}
MIN_LEN = {"keys": lambda lv: lv + 2 if lv else 1, "recipes": lambda lv: lv + 2 if lv else 1,
           "switches": lambda lv: lv + 1}
MAX_LEN = {0: 2}                   # level 0 (added 2026-09-26 for Creative's curriculum): 1-2 step plans only


def make_game(kind, seed, level):
    """a solvable game with its canonical shortest plan; retries inside the seed until solvable"""
    rng = random.Random(f"{kind}:{level}:{seed}")
    for _ in range(500):
        g = MAKERS[kind](rng, level)
        plan = SOLVE[kind](g)
        if plan and MIN_LEN[kind](level) <= len(plan) <= MAX_LEN.get(level, len(plan)):
            g["plan"] = plan
            g["text"] = TEXT[kind](g)
            g["seed"], g["level"] = seed, level
            return g
    raise RuntimeError("no solvable game")


def _start_and_moves(g):
    k = g["kind"]
    if k == "keys":
        return (g["start"], ()), _keys_moves(g), lambda s: s[0] == g["goal"]
    if k == "recipes":
        names, moves = _recipe_moves(g)
        gi = names.index(g["goal"])
        return tuple(g["inventory"].get(n, 0) for n in names), moves, lambda s: s[gi] >= 1
    goal = tuple(int(g["goal"][l]) for l in g["lamps"])
    return tuple(int(g["start"][l]) for l in g["lamps"]), _switch_moves(g), lambda s: s == goal


def check(g, reply):
    """simulate the reply's action lines (other lines ignored); returns {ok, steps, optimal, illegal}"""
    s, moves, is_goal = _start_and_moves(g)
    acts = [re.sub(r"^[\s\-\*\d\.\)]*", "", l).strip().lower().rstrip(".") for l in reply.splitlines()]
    acts = [a for a in acts if re.match(r"^(go|take|make|press)\b", a)]
    for i, a in enumerate(acts):
        nxt = dict((x.lower(), t) for x, t in moves(s)).get(a)
        if nxt is None:
            return {"ok": False, "steps": i, "optimal": False, "illegal": a}
        s = nxt
        if is_goal(s):
            return {"ok": True, "steps": i + 1, "optimal": i + 1 == len(g["plan"]), "illegal": None}
    return {"ok": is_goal(s), "steps": len(acts), "optimal": False, "illegal": None}


def selftest():
    for kind in KINDS:
        seen = set()
        for level in (1, 2, 3):
            lens = []
            for seed in range(60):
                g = make_game(kind, seed, level)
                assert check(g, "\n".join(g["plan"])) == {"ok": True, "steps": len(g["plan"]), "optimal": True,
                                                          "illegal": None}, (kind, level, seed)
                assert not check(g, "")["ok"] or not g["plan"]
                assert make_game(kind, seed, level)["text"] == g["text"]
                seen.add(g["text"]); lens.append(len(g["plan"]))
            print(f"{kind} level {level}: plan length min {min(lens)} mean {sum(lens) / len(lens):.1f} max {max(lens)}")
        assert len(seen) >= 175, (kind, len(seen))                     # tiny level-1 spaces may repeat
    for kind in KINDS:                                                  # level 0: 1-2 step plans
        lens, texts = [], set()
        for seed in range(60):
            g = make_game(kind, seed, 0)
            assert check(g, "\n".join(g["plan"]))["optimal"] and 1 <= len(g["plan"]) <= 2, (kind, seed)
            lens.append(len(g["plan"])); texts.add(g["text"])
        print(f"{kind} level 0: plan lengths 1: {lens.count(1)}, 2: {lens.count(2)}; {len(texts)} distinct of 60")
    g = make_game("keys", 1, 2)
    bad = check(g, "go Nowhere Street")
    assert not bad["ok"] and bad["illegal"] == "go nowhere street"
    print("selftest ok: every canonical plan checks as valid and shortest; games are seeded and distinct")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    p = sub.add_parser("sample"); p.add_argument("--kind", choices=KINDS, required=True)
    p.add_argument("--level", type=int, default=1); p.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    else:
        g = make_game(a.kind, a.seed, a.level)
        print(g["text"]); print("--- plan:"); print("\n".join(g["plan"]))
