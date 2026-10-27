import sys, json, random, time
from collections import Counter
sys.path.insert(0, "/home/user/learner/scripts")
import claude_rsn358a_envs as E
CFG = dict(pre_steps=3000, night_steps=300, batch=64, days=3, n_day=300, n_test=400, n_harm=300, n_transfer=200)
# copied verbatim (data side only) from scripts/claude_slp358n_nights.py
def practice_item(rng):
    if rng.random() < 0.5:
        return E.make_sum(rng, rng.choice([1, 2, 3, 4]))
    return E.latin_item(rng, *E.make_latin_base(rng, 4))
def practice_batch(rng, B):
    first = practice_item(rng)
    same = (lambda: E.make_sum(rng, first.size)) if first.env == "sums" else \
        (lambda: E.latin_item(rng, *E.make_latin_base(rng, 4)))
    return [first] + [same() for _ in range(B - 1)]
def day_items(rng, n):
    sums = [E.make_sum(rng, rng.choice([5, 6])) for _ in range(n)]
    grids = [E.latin_item(rng, *E.make_latin_base(rng, 5)) for _ in range(n)]
    return sums, grids
def key(it): return json.dumps(it.tokens)
def skey(it):  # structural key for grids: blank pattern + solution up to relabelling
    if it.env != "grids": return key(it)
    return json.dumps(it.meta["puz"])
def answered(items, answers_from):
    return [E.Item(it.env, it.size, it.tokens, it.slot, src.target, it.meta) for it, src in zip(items, answers_from)]
def shuffled_answers(items, rng):
    by = {}
    for i, it in enumerate(items):
        by.setdefault((it.env, len(it.tokens), len(it.tokens[0])), []).append(i)
    src = list(range(len(items)))
    for idx in by.values():
        perm = idx[:]; rng.shuffle(perm)
        for a, b in zip(idx, perm): src[a] = b
    return answered(items, [items[j] for j in src]), src
def night_batches(arm, day, rng, cfg):
    groups = {}
    for it in day:
        groups.setdefault((it.env, len(it.tokens), len(it.tokens[0])), []).append(it)
    groups = list(groups.values())
    out = []; kinds = []
    for _ in range(cfg["night_steps"]):
        if arm == "R" or rng.random() < 0.5:
            out.append(practice_batch(rng, cfg["batch"])); kinds.append("practice")
        else:
            g = rng.choice(groups)
            out.append([rng.choice(g) for _ in range(cfg["batch"])]); kinds.append(g[0].env + str(len(g[0].tokens[0])))
    return out, kinds

cfg = CFG
trng = random.Random(58600)
tests = {"day_sums": [E.make_sum(trng, trng.choice([5, 6])) for _ in range(cfg["n_test"])],
         "day_grids": [E.latin_item(trng, *E.make_latin_base(trng, 5)) for _ in range(cfg["n_test"])],
         "harm_sums4": [E.make_sum(trng, 4) for _ in range(cfg["n_harm"])],
         "harm_grids4": [E.latin_item(trng, *E.make_latin_base(trng, 4)) for _ in range(cfg["n_harm"])],
         "transfer_sums8": [E.make_sum(trng, 8) for _ in range(cfg["n_transfer"])],
         "transfer_grids6": [E.latin_item(trng, *E.make_latin_base(trng, 6)) for _ in range(cfg["n_transfer"])]}
tk = {name: {key(it) for it in v} for name, v in tests.items()}
tsk = {name: {skey(it) for it in v} for name, v in tests.items()}
test_keys = set().union(*tk.values())
print("distinct test items per set:", {n: len(s) for n, s in tk.items()}, "structural:", {n: len(s) for n, s in tsk.items()})
def hits(items):
    ks = {key(i) for i in items}; sk = {skey(i) for i in items}
    return {n: (len(tk[n] & ks), len(tsk[n] & sk)) for n in tests}
for seed in (1, 2):
    t0 = time.time()
    rng = random.Random(58610 + seed)
    pre = [it for _ in range(cfg["pre_steps"]) for it in practice_batch(rng, cfg["batch"])]
    print(f"seed {seed} pretrain items {len(pre)} leaks (exact, structural):", hits(pre), f"{time.time()-t0:.0f}s")
    excl = 0
    for day in range(1, cfg["days"] + 1):
        drng = random.Random(58700 + 10 * seed + day)
        sums, grids = day_items(drng, cfg["n_day"])
        items = [it for it in sums + grids if key(it) not in test_keys]
        excl += len(sums) + len(grids) - len(items)
        dh = hits(items)
        zdata, src = shuffled_answers(items, random.Random(58800 + 10 * seed + day))
        fixed = sum(1 for a, b in enumerate(src) if a == b)
        # placebo grid targets with BLANK (0) in a slot cell
        zg = [z for z in zdata if z.env == "grids"]
        blank_slot = sum(1 for z in zg for r in range(5) for c in range(5) if z.slot[r][c] and z.target[r][c] == 0)
        slots = sum(1 for z in zg for r in range(5) for c in range(5) if z.slot[r][c])
        foreign = sum(1 for z in zg for r in range(5) for c in range(5)
                      if z.slot[r][c] and z.target[r][c] != 0 and (z.target[r][c] - E.SYM) not in z.meta["names"])
        per = {}
        for arm in "SRZ":
            data = items if arm == "S" else zdata
            b, kinds = night_batches(arm, data, random.Random(58900 + 10 * seed + day), cfg)
            per[arm] = (Counter(kinds), hits([it for bb in b if True for it in bb]), sum(len(bb) for bb in b))
        print(f" seed {seed} day {day}: day-item leaks into tests {dh}; Z fixed points {fixed}; "
              f"Z grid slot cells with BLANK target {blank_slot}/{slots}, foreign-symbol targets {foreign}")
        for arm in "SRZ":
            print(f"   {arm}: batches {dict(per[arm][0])} items {per[arm][2]} test hits {per[arm][1]}")
    print(f" seed {seed} excluded_day_items_in_tests recomputed = {excl}", f"{time.time()-t0:.0f}s")
