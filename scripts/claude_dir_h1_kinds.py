#!/usr/bin/env python3
"""Two new held-out puzzle kinds for the few-example ruler (Director helper H1, 2026-09-28).

Design: artifacts/claude-dir-h1-heldout-20260928/DESIGN.md; marks: PASSMARKS.md (same folder).
Pure python (no torch, no numpy). Same token format as the ruler's nets: an H x W grid of token ids
(claude_rsn358a_envs vocabulary, 125 tokens), a fill-slot grid (1 = the net writes here) and a target grid.
The nets get no puzzle-kind input; the kind is only in the tokens.

  graph  "hop distance on a graph".  Rows are edge rows [EDGE, label_u, label_v] and node rows
         [NODE, label, fill]; one node row already carries distance 0 (the start).  The net writes, for every
         other node, how many edges away it is from the start (one token per node) or UNREACH.
         Nothing spatial: graph edges are content-matched by anonymous labels, relabelled every item.
         Every token id is one the source practice (sums, grids) never used except the blank marker.
  rank   "rank the list".  Row 0 is n digits (ties allowed); the net writes under each digit how many of the
         n digits are strictly smaller than it.  Uses the digit tokens the sums practice already knows,
         so it tests whether known number sense carries over.

Both are made by code and graded by exact code that re-derives the answer from the TOKENS (not from the
stored target).  Sizes: graph n = 12 / 14 (graded, trained) / 16 nodes; rank n = 7 / 9 (graded, trained) / 10.

  python3 -B scripts/claude_dir_h1_kinds.py selftest
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # vocabulary and Item class only

VAL, DIG, MASK, BLANK = E.VAL, E.DIG, E.MASK, E.BLANK

# ---- graph tokens (all in the VAL block, which sums/grids practice never used) ----
G_LAB0, G_NLAB = VAL + 50, 40          # anonymous node labels VAL+50 .. VAL+89
NODE_T, EDGE_T = VAL + 95, VAL + 96
UNREACH = VAL + 99                     # distance d is written as VAL+d
DMIN, DMAX, MIN_REACH = 3, 6, 6        # accepted farthest reachable distance, and reachable-node floor

KINDS = {
    "graph": {"sizes": (12, 14, 16), "graded": 14},
    "rank": {"sizes": (7, 9, 10), "graded": 9},
}
PANEL_COUNTS = {0: (24, 48), 1: (300, 300), 2: (300, 300)}   # index into sizes: small, graded, large
RUNGS = (1, 4, 16, 64, 256, 1024, 4096, 16384)
POOL_N = RUNGS[-1]
N_BATCHES, MAZE_BATCH = 512, 32                              # the ruler's equal-practice recipe
PANEL_SEED = {"graph": 9402800, "rank": 9402900}
POOL_SEED = {"graph": 9412800, "rank": 9412900}
BATCH_SEED = {"graph": 9422800, "rank": 9422900}


def edges_for(n):
    return n + 1


# =============================== graph ===============================
def _bfs(adj, src):
    dist = {src: 0}
    q = deque([src])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


def make_graph(rng, n):
    m = edges_for(n)
    pairs = list(itertools.combinations(range(n), 2))
    tries = 0
    while True:
        tries += 1
        es = rng.sample(pairs, m)
        adj = [[] for _ in range(n)]
        for a, b in es:
            adj[a].append(b)
            adj[b].append(a)
        src = rng.choice([v for v in range(n) if adj[v]])
        dist = _bfs(adj, src)
        if DMIN <= max(dist.values()) <= DMAX and len(dist) >= MIN_REACH:
            break
    lab = rng.sample(range(G_NLAB), n)
    nodes = list(range(n))
    rng.shuffle(nodes)
    edges = [(a, b) if rng.random() < .5 else (b, a) for a, b in es]
    rng.shuffle(edges)
    tokens, slot, target = [], [], []
    for a, b in edges:
        tokens.append([EDGE_T, G_LAB0 + lab[a], G_LAB0 + lab[b]])
        slot.append([0, 0, 0])
        target.append([0, 0, 0])
    for v in nodes:
        if v == src:
            tokens.append([NODE_T, G_LAB0 + lab[v], VAL])
            slot.append([0, 0, 0])
            target.append([0, 0, 0])
        else:
            tokens.append([NODE_T, G_LAB0 + lab[v], MASK])
            slot.append([0, 0, 1])
            target.append([0, 0, VAL + dist[v] if v in dist else UNREACH])
    return E.Item("graph", n, tokens, slot, target,
                  {"tries": tries, "dmax": max(dist.values()), "reach": len(dist)})


def parse_graph(tokens):
    edges, nodes, src = [], {}, []
    for row in tokens:
        if row[0] == EDGE_T:
            edges.append((row[1], row[2]))
        elif row[0] == NODE_T:
            nodes[row[1]] = row[2]
            if row[2] == VAL:
                src.append(row[1])
    if len(src) != 1:
        raise ValueError("graph item must have exactly one start node")
    return edges, nodes, src[0]


def graph_expected(tokens):
    """label -> answer token, derived from the tokens only."""
    edges, nodes, src = parse_graph(tokens)
    adj = {lab: [] for lab in nodes}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    dist = _bfs(adj, src)
    return {lab: (VAL + dist[lab] if lab in dist else UNREACH) for lab in nodes}, dist


def check_graph(item, pred):
    exp, _ = graph_expected(item.tokens)
    for r, row in enumerate(item.tokens):
        if row[0] == NODE_T and item.slot[r][2]:
            if pred[r][2] != exp[row[1]]:
                return False
    return True


def graph_struct_key(item):
    """Rooted structure with the labels and row order removed (1-WL colour refinement, 6 rounds).
    Two items with the same key have the same graph up to renaming, for all practical purposes;
    training pools are kept disjoint from panels on THIS key, not merely on the printed text."""
    edges, nodes, src = parse_graph(item.tokens)
    adj = {lab: [] for lab in nodes}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    col = {lab: ("s" if lab == src else "o") for lab in nodes}
    for _ in range(6):
        col = {lab: hashlib.sha256((col[lab] + "|" + ",".join(sorted(col[x] for x in adj[lab]))).encode()
                                   ).hexdigest()[:16] for lab in nodes}
    body = ",".join(sorted(col.values())) + f"|{len(nodes)}|{len(edges)}"
    return hashlib.sha256(body.encode()).hexdigest()


def graph_reference_rounds(item):
    """A synchronous message-passing loop that is enough to solve the item: one hop = two rounds
    (edge rows read their two node rows; node rows read their edge rows).  Returns (rounds, ok)."""
    edges, nodes, src = parse_graph(item.tokens)
    known = {src: 0}
    rounds = 0
    while True:
        new = dict(known)
        for a, b in edges:
            if a in known and b not in known:
                new[b] = known[a] + 1
            if b in known and a not in known:
                new[a] = known[b] + 1
        if new == known:
            break
        known = new
        rounds += 2
    exp, _ = graph_expected(item.tokens)
    ok = all((VAL + known[lab] if lab in known else UNREACH) == exp[lab] for lab in nodes)
    return rounds, ok


def graph_baselines(item):
    """Cheap wrong-by-design predictors; each returns a full-size prediction grid."""
    edges, nodes, src = parse_graph(item.tokens)
    adj = {lab: [] for lab in nodes}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    out = {}
    for name in ("all_unreach", "all_one", "two_hops_only"):
        grid = [row[:] for row in item.tokens]
        dist = _bfs(adj, src)
        for r, row in enumerate(item.tokens):
            if row[0] == NODE_T and item.slot[r][2]:
                lab = row[1]
                if name == "all_unreach":
                    grid[r][2] = UNREACH
                elif name == "all_one":
                    grid[r][2] = VAL + 1
                else:
                    d = dist.get(lab)
                    grid[r][2] = VAL + d if d is not None and d <= 2 else UNREACH
        out[name] = grid
    return out


# =============================== rank ===============================
def make_rank(rng, n):
    while True:
        vals = [rng.randrange(10) for _ in range(n)]
        if len(set(vals)) >= 5:
            break
    ranks = [sum(w < v for w in vals) for v in vals]
    return E.Item("rank", n, [[DIG + v for v in vals], [MASK] * n], [[0] * n, [1] * n],
                  [[0] * n, [DIG + r for r in ranks]], {"vals": vals})


def rank_expected(tokens):
    vals = [t - DIG for t in tokens[0]]
    return [DIG + sum(w < v for w in vals) for v in vals]


def check_rank(item, pred):
    return list(pred[1]) == rank_expected(item.tokens)


def rank_key(item):
    return "r" + "".join(str(t - DIG) for t in item.tokens[0])


def rank_baselines(item):
    n = item.size
    vals = [t - DIG for t in item.tokens[0]]
    out = {}
    for name in ("copy_value", "all_zero", "scaled_value"):
        row = [DIG + (v if name == "copy_value" else 0 if name == "all_zero" else v * (n - 1) // 9)
               for v in vals]
        out[name] = [item.tokens[0][:], row]
    return out


# =============================== common ===============================
def make_item(kind, rng, n):
    return make_graph(rng, n) if kind == "graph" else make_rank(rng, n)


def check(item, pred):
    if item.env == "graph":
        return check_graph(item, pred)
    if item.env == "rank":
        return check_rank(item, pred)
    raise ValueError(item.env)


def item_key(item):
    return graph_struct_key(item) if item.env == "graph" else rank_key(item)


def baselines(item):
    return graph_baselines(item) if item.env == "graph" else rank_baselines(item)


def reference_rounds(item):
    if item.env == "graph":
        return graph_reference_rounds(item)
    return 2, list(rank_expected(item.tokens)) == list(item.target[1])


def unique_item(kind, rng, n, forbidden, seen):
    while True:
        it = make_item(kind, rng, n)
        key = item_key(it)
        if key not in forbidden and key not in seen:
            seen.add(key)
            return it


def panels(kind):
    """{'dev': {n: items}, 'holdout': {n: items}}, disjoint by item_key across every panel.
    Holdout items are generated here so the pool can avoid them; nothing scores them until the gate passes."""
    out, banned = {"dev": {}, "holdout": {}}, set()
    for i, n in enumerate(KINDS[kind]["sizes"]):
        nd, nh = PANEL_COUNTS[i]
        rng = random.Random(PANEL_SEED[kind] + n)
        for split, cnt in (("dev", nd), ("holdout", nh)):
            items = []
            while len(items) < cnt:
                items.append(unique_item(kind, rng, n, banned, banned))
            out[split][n] = items
    return out, banned


def make_pool(kind, seed, banned):
    """One ordered, nested, panel-disjoint support pool per paired seed (graded size only)."""
    n = KINDS[kind]["graded"]
    rng = random.Random(POOL_SEED[kind] + seed)
    seen = set()
    pool = [unique_item(kind, rng, n, banned, seen) for _ in range(POOL_N)]
    assert len(seen) == POOL_N and not seen & banned
    digest = hashlib.sha256("\n".join(item_key(x) for x in pool).encode()).hexdigest()
    return pool, seen, digest


def batches(kind, pool, k, seed):
    """Exactly 16,384 slots in shuffled cycles of the first k pool items, shared across arms."""
    rng = random.Random(BATCH_SEED[kind] + 1000 * seed + k)
    order = list(range(k))
    pos = k
    for _ in range(N_BATCHES):
        batch = []
        while len(batch) < MAZE_BATCH:
            if pos == k:
                rng.shuffle(order)
                pos = 0
            take = min(MAZE_BATCH - len(batch), k - pos)
            batch.extend(pool[i] for i in order[pos:pos + take])
            pos += take
        yield batch


def fingerprint(items):
    return hashlib.sha256("\n".join(item_key(x) for x in items).encode()).hexdigest()


# =============================== self-test ===============================
def _perturb(item, rng):
    """A prediction grid equal to the target except one fill cell changed to another plausible token."""
    grid = [[item.target[r][c] if item.slot[r][c] else item.tokens[r][c] for c in range(len(item.tokens[0]))]
            for r in range(len(item.tokens))]
    cells = [(r, c) for r in range(len(grid)) for c in range(len(grid[0])) if item.slot[r][c]]
    r, c = rng.choice(cells)
    if item.env == "graph":
        opts = [VAL + d for d in range(0, 9)] + [UNREACH]
    else:
        opts = [DIG + d for d in range(10)]
    grid[r][c] = rng.choice([t for t in opts if t != grid[r][c]])
    return grid


def _gold(item):
    return [[item.target[r][c] if item.slot[r][c] else item.tokens[r][c] for c in range(len(item.tokens[0]))]
            for r in range(len(item.tokens))]


def selftest():
    rng = random.Random(1)
    report = {}
    for kind, cfg in KINDS.items():
        info = {"sizes": {}}
        for n in cfg["sizes"]:
            items = [make_item(kind, rng, n) for _ in range(300)]
            shapes = {(len(x.tokens), len(x.tokens[0])) for x in items}
            assert len(shapes) == 1, shapes                      # one shape per size (batches stack)
            max_rounds = 0
            for it in items:
                assert max(max(row) for row in it.tokens) < E.VOCAB
                assert max(max(row) for row in it.target) < E.VOCAB
                gold = _gold(it)
                assert check(it, gold)
                for _ in range(3):
                    assert not check(it, _perturb(it, rng))
                rounds, ok = reference_rounds(it)
                assert ok and rounds <= 48, (rounds, ok)
                max_rounds = max(max_rounds, rounds)
                if kind == "graph":                              # answer re-derived from tokens == stored target
                    exp, dist = graph_expected(it.tokens)
                    for r, row in enumerate(it.tokens):
                        if row[0] == NODE_T and it.slot[r][2]:
                            assert it.target[r][2] == exp[row[1]]
            info["sizes"][str(n)] = {"grid": list(shapes.pop()), "items_ok": len(items),
                                     "max_reference_rounds": max_rounds}
        # distribution facts at the graded size
        n = cfg["graded"]
        many = [make_item(kind, rng, n) for _ in range(1000)]
        if kind == "graph":
            dm = {}
            for x in many:
                dm[x.meta["dmax"]] = dm.get(x.meta["dmax"], 0) + 1
            unreach = sum(sum(1 for r, row in enumerate(x.tokens) if row[0] == NODE_T and x.target[r][2] == UNREACH)
                          for x in many) / (1000 * (n - 1))
            info["graded_stats"] = {"farthest_distance_histogram": dict(sorted(dm.items())),
                                    "mean_reachable_nodes": sum(x.meta["reach"] for x in many) / 1000,
                                    "fraction_of_answers_unreachable": round(unreach, 3),
                                    "mean_sampling_tries": sum(x.meta["tries"] for x in many) / 1000}
            lab_graphs = math.comb(n * (n - 1) // 2, edges_for(n))
            info["structure_space_lower_bound"] = {
                "labelled_graphs": lab_graphs, "divided_by_n_factorial": lab_graphs // math.factorial(n)}
        else:
            ranks_used = {}
            for x in many:
                for t in x.target[1]:
                    ranks_used[t - DIG] = ranks_used.get(t - DIG, 0) + 1
            info["graded_stats"] = {"rank_value_histogram": dict(sorted(ranks_used.items())),
                                    "mean_distinct_digits": sum(len(set(x.meta['vals'])) for x in many) / 1000}
            info["input_space"] = 10 ** n
        # panels and pools
        pan, banned = panels(kind)
        total_panel = sum(sum(PANEL_COUNTS[i]) for i in range(3))
        assert len(banned) == total_panel, (len(banned), total_panel)
        for split in pan:
            for n2, items in pan[split].items():
                assert len({item_key(x) for x in items}) == len(items)
        info["panel_counts"] = {sp: {str(n2): len(v) for n2, v in pan[sp].items()} for sp in pan}
        info["panel_fingerprints"] = {sp: fingerprint([x for n2 in pan[sp] for x in pan[sp][n2]]) for sp in pan}
        pools = {}
        for seed in (0, 1):
            pool, seen, digest = make_pool(kind, seed, banned)
            assert len(seen) == POOL_N and not seen & banned
            for k in RUNGS:
                visit = {item_key(x): 0 for x in pool[:k]}
                for b in batches(kind, pool, k, seed):
                    assert len(b) == MAZE_BATCH
                    for x in b:
                        visit[item_key(x)] += 1
                assert set(visit.values()) == {N_BATCHES * MAZE_BATCH // k}
            pools[seed] = seen
            info[f"pool_seed{seed}"] = {"unique_keys": len(seen), "panel_overlap": len(seen & banned),
                                        "sha256": digest}
        info["pool_seed0_vs_seed1_key_overlap"] = len(pools[0] & pools[1])
        # cheap wrong-by-design predictors on the DEV graded panel only (holdout is not scored here)
        dev = pan["dev"][cfg["graded"]]
        wins = {}
        for it in dev:
            for name, grid in baselines(it).items():
                wins[name] = wins.get(name, 0) + int(check(it, grid))
        info["dev_graded_baselines_right_of_300"] = wins
        assert all(v <= 15 for v in wins.values()), wins        # each must stay under 5%
        report[kind] = info
    print(json.dumps(report, indent=2, sort_keys=True))
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        print(__doc__)
