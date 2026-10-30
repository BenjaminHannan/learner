"""Build the practice pool and the sibling test (Practice-1). Run once in a container with network:
  python -m practice.pools [--arc-dir DIR]
ARC-AGI-1 TRAINING tasks (github.com/fchollet/ARC-AGI data/training) with every grid <= 12x12 and a single test output are split deterministically
(by sha256 of the task id) into practice (150) and sibling test (30). Code-made puzzles (seeded, known answers) add 120 practice + 30 sibling.
Writes practice/data/practice_pool.jsonl and practice/data/sibling60.jsonl (fields id, source, kind, prompt, answer, answer_type)."""
import argparse
import hashlib
import itertools
import json
import random
import subprocess
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RAW = "https://raw.githubusercontent.com/fchollet/ARC-AGI/master/data/training/{}.json"
N_ARC_PRACTICE, N_ARC_SIB = 150, 30
GEN_KINDS = ["logic", "crypt", "seq", "maze", "count"]
GEN_PRACTICE_PER_KIND, GEN_SIB_PER_KIND = 24, 6
SEED_PRACTICE, SEED_SIB = 7101, 9203


# ------------------------------------------------------------------ ARC
def grid_text(g):
    return "\n".join(" ".join(str(c) for c in row) for row in g)


def arc_prompt(task):
    parts = ["Each grid below is a list of rows of digits 0-9 (0 is usually the background). The examples all follow one hidden rule. "
             "Find the rule and apply it to the test input. Give the output grid, one row per line, digits separated by spaces."]
    for i, p in enumerate(task["train"], 1):
        parts.append(f"Example {i} input:\n{grid_text(p['input'])}\nExample {i} output:\n{grid_text(p['output'])}")
    parts.append(f"Test input:\n{grid_text(task['test'][0]['input'])}\nTest output:")
    return "\n\n".join(parts)


def grid_keys(t):
    """Whole grids (non-trivial: >= 6 cells and more than one colour) of a task, as strings; two tasks sharing one are treated as near-duplicates."""
    out = set()
    for part in ("train", "test"):
        for p in t[part]:
            for k in ("input", "output"):
                g = p[k]
                if sum(len(r) for r in g) >= 6 and len({c for r in g for c in r}) > 1:
                    out.add(grid_text(g))
    return out


def small_task(t):
    if len(t["test"]) != 1:
        return False
    grids = [p[k] for part in ("train", "test") for p in t[part] for k in ("input", "output")]
    return all(len(g) <= 12 and len(g[0]) <= 12 for g in grids)


def ids_list():
    f = DATA / "arc_train_ids.txt"
    if f.exists():
        return f.read_text().split()
    import arckit  # noqa: F401  (id list only; the task files themselves are fetched from fchollet/ARC-AGI)
    import importlib.resources as r
    d = json.loads((r.files("arckit") / "data" / "arc1.json").read_text())
    ids = sorted(d["train"])
    f.write_text("\n".join(ids) + "\n")
    return ids


def load_arc(arc_dir):
    arc_dir = Path(arc_dir)
    arc_dir.mkdir(parents=True, exist_ok=True)
    tasks = {}
    for i in ids_list():
        p = arc_dir / f"{i}.json"
        if not p.exists():
            subprocess.run(["curl", "-sSf", "-o", str(p), RAW.format(i)], check=True)
        tasks[i] = json.loads(p.read_text())
    return tasks


def arc_rows(tasks):
    keep = sorted((i for i, t in tasks.items() if small_task(t)), key=lambda i: hashlib.sha256(i.encode()).hexdigest())
    pr = keep[:N_ARC_PRACTICE]
    seen = set().union(*[grid_keys(tasks[i]) for i in pr])
    sb = []
    for i in keep[N_ARC_PRACTICE:]:  # skip siblings that share a grid with the practice tasks (ARC has families of near-identical tasks)
        k = grid_keys(tasks[i])
        if k & seen:
            continue
        sb.append(i)
        seen |= k
        if len(sb) == N_ARC_SIB:
            break

    def row(i):
        t = tasks[i]
        return dict(id=f"arc-{i}", source="arc-agi-1-training", kind="arc", prompt=arc_prompt(t), answer=grid_text(t["test"][0]["output"]), answer_type="grid")
    return [row(i) for i in pr], [row(i) for i in sb], len(keep)


# ------------------------------------------------------------------ generated puzzles
def gen_logic(rng):
    """3 houses (positions 1-3), categories colour / pet / drink. Add true clues until the solution is unique; ask for a house number."""
    cats = {"colour": ["red", "green", "blue"], "pet": ["cat", "dog", "fish"], "drink": ["tea", "milk", "juice"]}
    sol = {c: rng.sample(range(3), 3) for c in cats}  # sol[c][item index] = position (0..2)
    items = [(c, k) for c in cats for k in range(3)]
    pos = lambda it: sol[it[0]][it[1]]  # noqa: E731
    def name(it):
        v = cats[it[0]][it[1]]
        return {"colour": f"the {v} house", "pet": f"the house with the {v}", "drink": f"the house where {v} is drunk"}[it[0]]

    def holds(clue, s):
        kind, a, b = clue
        pa = s[a[0]][a[1]]
        if kind == "same":
            return pa == s[b[0]][b[1]]
        if kind == "left":
            return pa + 1 == s[b[0]][b[1]]
        if kind == "at":
            return pa == b
        if kind == "notat":
            return pa != b
    perms = list(itertools.permutations(range(3)))
    allsol = [dict(colour=a, pet=b, drink=c) for a in perms for b in perms for c in perms]
    # normalise: sol is the (item -> position) map
    cand = list(allsol)
    clues = []
    for _ in range(40):
        a, b = rng.sample(items, 2)
        k = rng.choice(["same", "same", "left", "at", "notat"])
        if k == "same" and a[0] == b[0]:
            continue
        if k in ("at", "notat"):
            b = rng.randrange(3) if k == "notat" else pos(a)
            if k == "notat" and b == pos(a):
                continue
        elif k == "same" and pos(a) != pos(b):
            continue
        elif k == "left" and pos(a) + 1 != pos(b):
            continue
        c = (k, a, b)
        new = [s for s in cand if holds(c, s)]
        if len(new) < len(cand):
            clues.append(c)
            cand = new
        if len(cand) == 1:
            break
    if len(cand) != 1:
        return None
    # question: which house number (1-3) has an item
    q = rng.choice([i for i in items if i[0] != "colour"])
    txt = []
    for k, a, b in clues:
        if k == "same":
            txt.append(f"{_cap(name(a))} is also {name(b)}.")
        elif k == "left":
            txt.append(f"{_cap(name(a))} is immediately to the left of {name(b)}.")
        elif k == "at":
            txt.append(f"{_cap(name(a))} is in house {b + 1}.")
        else:
            txt.append(f"{_cap(name(a))} is not in house {b + 1}.")
    rng.shuffle(txt)
    prompt = ("Three houses stand in a row, numbered 1, 2, 3 from left to right. Each house has one colour (red, green, blue), one pet (cat, dog, fish) "
              "and one drink (tea, milk, juice); all different. Clues:\n" + "\n".join(f"- {t}" for t in txt) +
              f"\nWhich house number is {name(q)}? Answer with the number.")
    return prompt, str(cand[0][q[0]][q[1]] + 1), "int"


def _cap(s):
    return s[0].upper() + s[1:]


def gen_crypt(rng):
    for _ in range(200):
        n1, n2 = rng.choice([(2, 2), (3, 2), (3, 3)])
        letters = rng.sample("ABCDEFGHIJ", 10)
        digs = rng.sample(range(10), 10)
        m = dict(zip(letters, digs))
        a = rng.randrange(10 ** (n1 - 1), 10 ** n1)
        b = rng.randrange(10 ** (n2 - 1), 10 ** n2)
        c = a + b
        used = sorted(set(str(a) + str(b) + str(c)))
        if len(used) > 6:
            continue
        sym = dict(zip(used, rng.sample("ABCDEFGHIJ", len(used))))
        w = lambda x: "".join(sym[d] for d in str(x))  # noqa: E731
        wa, wb, wc = w(a), w(b), w(c)
        ls = sorted(set(wa + wb + wc))
        lead = {wa[0], wb[0], wc[0]}
        sols = []
        for p in itertools.permutations(range(10), len(ls)):
            mp = dict(zip(ls, p))
            if any(mp[x] == 0 for x in lead):
                continue
            v = lambda s: int("".join(str(mp[ch]) for ch in s))  # noqa: E731
            if v(wa) + v(wb) == v(wc):
                sols.append(v(wc))
                if len(set(sols)) > 1:
                    break
        if len(set(sols)) == 1 and len(sols) <= 1:
            return (f"In the sum {wa} + {wb} = {wc} each letter stands for a different digit (0-9), the same letter always the same digit, "
                    f"and no number starts with 0. The solution is unique. What is the number {wc}?"), str(c), "int"
    return None


def gen_seq(rng):
    k = rng.choice(["arith", "geom", "quad", "fib", "alt", "cube", "tri", "diffgrow"])
    if k == "arith":
        a, d = rng.randint(-9, 20), rng.randint(2, 13)
        s = [a + d * i for i in range(7)]
    elif k == "geom":
        a, r = rng.randint(1, 5), rng.choice([2, 3, 4, -2])
        s = [a * r ** i for i in range(7)]
    elif k == "quad":
        a, b, c = rng.randint(1, 4), rng.randint(-5, 6), rng.randint(-6, 9)
        s = [a * i * i + b * i + c for i in range(1, 9)]
    elif k == "fib":
        x, y = rng.randint(1, 6), rng.randint(1, 9)
        s = [x, y]
        while len(s) < 8:
            s.append(s[-1] + s[-2])
    elif k == "alt":
        a, d, b, e = rng.randint(1, 9), rng.randint(2, 6), rng.randint(20, 40), rng.randint(2, 7)
        s = []
        for i in range(8):
            s.append(a + d * (i // 2) if i % 2 == 0 else b - e * (i // 2))
    elif k == "cube":
        c = rng.randint(-5, 9)
        s = [i ** 3 + c for i in range(1, 8)]
    elif k == "tri":
        c = rng.randint(0, 9)
        s = [i * (i + 1) // 2 * rng.choice([1]) + c for i in range(1, 9)]
    else:  # differences grow by a constant, starting at d0
        a, d0, g = rng.randint(1, 9), rng.randint(1, 5), rng.randint(2, 4)
        s = [a]
        for i in range(7):
            s.append(s[-1] + d0 + g * i)
    shown, nxt = s[:-1], s[-1]
    return f"What is the next number in the sequence {', '.join(map(str, shown))}, ...? Answer with the integer.", str(nxt), "int"


def gen_maze(rng):
    for _ in range(100):
        h, w = rng.randint(5, 8), rng.randint(5, 8)
        g = [["#" if rng.random() < 0.3 else "." for _ in range(w)] for _ in range(h)]
        s, e = (0, 0), (h - 1, w - 1)
        g[0][0], g[h - 1][w - 1] = "S", "E"
        dist = {s: 0}
        q = deque([s])
        while q:
            r, c = q.popleft()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (r + dr, c + dc)
                if 0 <= n[0] < h and 0 <= n[1] < w and g[n[0]][n[1]] != "#" and n not in dist:
                    dist[n] = dist[(r, c)] + 1
                    q.append(n)
        if e in dist and dist[e] >= h + w - 2 + 2:
            return ("In the maze below, S is the start, E is the exit, # is a wall and . is open floor. You may move one step up, down, left or right "
                    "(no diagonals) onto open floor. What is the smallest number of steps from S to E?\n" + "\n".join("".join(r) for r in g)), str(dist[e]), "int"
    return None


def gen_count(rng):
    k = rng.choice(["choose", "paths", "divis", "nofront", "anagram", "digits", "derange", "coins"])
    if k == "choose":
        n, r = rng.randint(8, 14), rng.randint(3, 5)
        from math import comb
        return f"A club has {n} members. In how many ways can a committee of {r} members be chosen?", str(comb(n, r)), "int"
    if k == "paths":
        a, b = rng.randint(3, 7), rng.randint(3, 7)
        from math import comb
        return f"A robot walks on a grid from the bottom-left corner to the top-right corner, moving only right or up. The grid needs {a} right steps and {b} up steps. How many different routes are there?", str(comb(a + b, a)), "int"
    if k == "divis":
        n, p, q = rng.randint(100, 500), rng.choice([2, 3, 4]), rng.choice([5, 7, 6])
        cnt = sum(1 for i in range(1, n + 1) if i % p == 0 or i % q == 0)
        return f"How many integers from 1 to {n} (inclusive) are divisible by {p} or by {q} (or both)?", str(cnt), "int"
    if k == "nofront":
        n = rng.randint(6, 12)
        cnt = sum(1 for m in range(2 ** n) if "11" not in bin(m)[2:].zfill(n))
        return f"How many binary strings of length {n} contain no two adjacent 1s?", str(cnt), "int"
    if k == "anagram":
        word = rng.choice(["LEVEL", "BANANA", "APPLE", "ERROR", "MISSISSIPPI"[:7], "COOKIE", "TATTOO", "LETTER"])
        cnt = len(set(itertools.permutations(word)))
        return f"How many different arrangements (distinct strings) can be made by rearranging all the letters of the word {word}?", str(cnt), "int"
    if k == "digits":
        n, s = rng.choice([3, 4]), rng.randint(5, 14)
        cnt = sum(1 for m in range(10 ** (n - 1), 10 ** n) if sum(map(int, str(m))) == s)
        return f"How many {n}-digit positive integers (no leading zero) have digits that add up to {s}?", str(cnt), "int"
    if k == "derange":
        n = rng.randint(4, 7)
        cnt = sum(1 for p in itertools.permutations(range(n)) if all(p[i] != i for i in range(n)))
        return f"{n} people each throw their hat in a pile and each takes one hat back at random. In how many of the {n}! possible outcomes does nobody get their own hat?", str(cnt), "int"
    coins = sorted(rng.sample([1, 2, 3, 5, 10, 25], 3))
    t = rng.randint(12, 40)
    ways = [1] + [0] * t
    for c in coins:
        for i in range(c, t + 1):
            ways[i] += ways[i - c]
    return f"In how many ways can you make exactly {t} cents using unlimited coins of values {', '.join(map(str, coins))} cents? (Order does not matter.)", str(ways[t]), "int"


GENS = {"logic": gen_logic, "crypt": gen_crypt, "seq": gen_seq, "maze": gen_maze, "count": gen_count}


def gen_rows(seed, per_kind, prefix, banned):
    rng = random.Random(seed)
    rows = []
    for kind in GEN_KINDS:
        n, tries = 0, 0
        while n < per_kind:
            tries += 1
            assert tries < 5000, kind
            r = GENS[kind](rng)
            if r is None or r[0] in banned:
                continue
            banned.add(r[0])
            rows.append(dict(id=f"{prefix}-{kind}-{n:03d}", source="code-made", kind=kind, prompt=r[0], answer=r[1], answer_type=r[2]))
            n += 1
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arc-dir", default=str(DATA / "arc_cache"))
    a = ap.parse_args()
    tasks = load_arc(a.arc_dir)
    arc_p, arc_s, n_small = arc_rows(tasks)
    banned = set()
    gen_p = gen_rows(SEED_PRACTICE, GEN_PRACTICE_PER_KIND, "gp", banned)
    gen_s = gen_rows(SEED_SIB, GEN_SIB_PER_KIND, "gs", banned)
    pr, sb = arc_p + gen_p, arc_s + gen_s
    for name, rows in (("practice_pool.jsonl", pr), ("sibling60.jsonl", sb)):
        with open(DATA / name, "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"arc_small_tasks": n_small, "practice": len(pr), "sibling": len(sb), "arc_practice": len(arc_p), "arc_sibling": len(arc_s)}))


if __name__ == "__main__":
    sys.exit(main())
