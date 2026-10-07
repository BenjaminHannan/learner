"""Night chaining (fast-sleep research 10-07; marks /mnt/project-files/fast-sleep/NIGHT-CHAIN-MARKS.md, commit 08c70a881). DEV only.

For pool questions the night's own tries did not solve, add records found by
  C (chain): the shortest P2(P1(x)) of two library programs (this parent's W programs + the 512 old add/mult notes) that fits the 3 examples;
  B (blind control): the first program from a breadth-first search over x and the constants 1/2/10/100 (no notes) that fits, budget 5,000.
The key is never read. Then memory sleep exactly as C2b's arm M on W, W + C and W + B.

  python3 -m creative.nightchain --out DIR [DIR ...] --skills-train train.jsonl --skills-data data_big
"""
import argparse, itertools, json, os, time
from creative import fastsleep as fs, fewshot, sleep, c2_stones, rules_real as R
from creative.programs import Try, R0, N_RES, apply
from creative import programs as P

DATA = 'creative/data/c2'
X, CONST_SLOTS = 6, (16, 17, 18, 19)
OPS = (1, 2, 3, 4, 5, 6, 7)
log = fs.log


def library(W):
    lib = {}
    for r in W + R.warm_records(R.load_split(DATA, 'warm'))[:512]:
        t = fewshot.record_try(r)
        tf = fewshot.train_form(t)
        if tf:
            lib[(tuple(tf[0]), tf[1])] = tf
    return list(lib.values())


def chain(tf1, tf2):
    """P2 after P1: P1's steps, then P2's with x -> P1's answer slot and P2's result slots shifted. None if longer than 7 steps."""
    (s1, a1), (s2, a2) = tf1, tf2
    n1 = len(s1)
    if n1 + len(s2) > N_RES:
        return None
    mp = lambda s: a1 if s == X else (s + n1 if s >= R0 else s)
    return Try.make(list(s1) + [(o, mp(a), mp(b)) for o, a, b in s2], mp(a2))


def _f(t, x, nums):
    n = list(nums); n[X] = x
    vals, valid = P.run(n, t)
    return vals[t.ans] if valid[t.ans] else None


def solve_chain(p, lib):
    """Shortest fitting candidate among single library programs and chains of two (steps counted); ties -> library order. Values are run in
    python first; only the chosen program goes through the full verdict (both executors)."""
    pts = p['xs'] + [p['q']]
    F = []
    for tf in lib:
        t = Try.make(*tf)
        if not fewshot.structure(p, t)[0]:
            continue
        v = [_f(t, x, p['nums']) for x in pts]
        if None not in v:
            F.append((tf, t, v))
    best = None
    for tf, t, v in F:
        if v[:-1] == p['ys'] and (best is None or len(tf[0]) < best[0]):
            best = (len(tf[0]), t)
    for tf1, t1, v1 in F:
        for tf2, t2, _ in F:
            n = len(tf1[0]) + len(tf2[0])
            if n > N_RES or (best is not None and n >= best[0]):
                continue
            v = [_f(t2, y, p['nums']) for y in v1]
            if None not in v and v[:-1] == p['ys']:
                best = (n, chain(tf1, tf2))
    if best is None:
        return None
    return best[1] if fewshot.verdict(p, best[1])[0] == 'accept' else None


def solve_blind(p, budget=5000):
    pts = p['xs'] + [p['q']]
    n = len(pts)
    nodes = [(tuple(pts), ('leaf', X))] + [(tuple([c] * n), ('leaf', s)) for c, s in zip((1, 2, 10, 100), CONST_SLOTS)]
    seen = {v for v, _ in nodes}
    used = 0
    while used < budget:
        grew = False
        for i, j in itertools.product(range(len(nodes)), range(len(nodes))):
            for op in OPS:
                a, b = nodes[i][0], nodes[j][0]
                v = []
                for k in range(n):
                    r = apply(op, a[k], b[k])
                    if r is None:
                        break
                    v.append(r)
                if len(v) < n or tuple(v) in seen:
                    continue
                v = tuple(v); seen.add(v); used += 1; grew = True
                nodes.append((v, (op, i, j)))
                if list(v[:-1]) == p['ys']:
                    t = _flatten(nodes, len(nodes) - 1)
                    if t is not None and fewshot.verdict(p, t)[0] == 'accept':
                        return t
                if used >= budget:
                    return None
        if not grew:
            return None
    return None


def _flatten(nodes, root):
    steps, slot = [], {}

    def go(i):
        kind = nodes[i][1]
        if kind[0] == 'leaf':
            return kind[1]
        if i in slot:
            return slot[i]
        op, a, b = kind
        sa, sb = go(a), go(b)
        steps.append((op, sa, sb))
        slot[i] = R0 + len(steps) - 1
        return slot[i]
    ans = go(root)
    return Try.make(steps, ans) if len(steps) <= N_RES and ans >= R0 else None


def night_records(out, which):
    path = os.path.join(out, f'night_{which}.json')
    N, vocab, meta, s = fs.load_setup(out)
    W = s['records']['W']
    solved = {r['source'] for r in W}
    pool = c2_stones._with_nums(R.load_split(DATA, 'pool'))
    lib = library(W)
    recs, kinds = [], {}
    t0 = time.time()
    for row in pool:
        if row['id'] in solved:
            continue
        p = fewshot.parse(row['prompt'])
        t = solve_chain(p, lib) if which == 'C' else solve_blind(p)
        if t is not None:
            recs.append(fewshot._record(row, t, which, 0))
            kinds[row['kind']] = kinds.get(row['kind'], 0) + 1
    info = dict(which=which, unsolved=len(pool) - len(solved), found=len(recs), by_kind=kinds, library=len(lib), seconds=round(time.time() - t0))
    log('night', os.path.basename(out), info)
    return N, vocab, s, W, recs, info


def run(out, skills_train, skills_data, device='cpu', seed=0):
    path = os.path.join(out, 'nightchain.json')
    res = json.load(open(path)) if os.path.exists(path) else {}
    replay = sleep.load_replay(skills_train, None, seed)
    dev = c2_stones._with_nums(R.load_split(DATA, 'dev'))
    kw = dict(c=50.0, theta=0.9, cal=0.99, old=512, ans=0)
    for arm in ('M', 'MC', 'MB'):
        if arm in res:
            continue
        if arm == 'M':
            N, vocab, meta, s = fs.load_setup(out)
            W, extra, info = s['records']['W'], [], {}
        else:
            N, vocab, s, W, extra, info = night_records(out, arm[1])
        if 'N' not in res:
            d, _ = fs.dev_eval(N, dev, vocab, device)
            res['N'] = dict(dev_right=d['right'], by_kind=d['by_kind'], skills5=fs.skills5(N, skills_data, device))
        recs = W + extra
        (m, minfo), flops, secs = fs.count_flops(lambda: fs.m_knn(N, recs, replay, vocab, device, len(recs), **kw))
        d, _ = fs.dev_eval(m, dev, vocab, device)
        res[arm] = dict(records=len(recs), extra=info, sleep_tflops=flops / 1e12, dev_gain=100 * (d['right'] - res['N']['dev_right']), by_kind=d['by_kind'],
                        chain5_harm=round(100 * (res['N']['skills5'] - fs.skills5(m, skills_data, device)), 6))
        json.dump(res, open(path, 'w'), indent=1)
        log('NIGHTCHAIN', os.path.basename(out), arm, {k: res[arm][k] for k in ('records', 'sleep_tflops', 'dev_gain', 'chain5_harm')}, d['by_kind'])
    return res


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--out', nargs='+', required=True); a.add_argument('--skills-train'); a.add_argument('--skills-data')
    a = a.parse_args()
    for o in a.out:
        run(o, a.skills_train, a.skills_data)
