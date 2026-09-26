import json, re
from math import comb
from collections import Counter

D = '/tmp/claude-0/-home-user-learner/936f6d07-c919-50cf-a53a-bafcb44ae6da/scratchpad/k1a_reg/'
ITEMS = '/home/user/learner/artifacts/claude-k1apanel-20260926/creative/items.jsonl'
ARMS = ['X', 'K', 'B', 'KB', 'KB0', 'T']
FALLBACK = "I don't have a good idea for that yet. Tell me a bit more about what you'd like?"
BARE = re.compile(r"(?:^|\n)\s*\d+[.)]\s*$")

# items: only item_id, len(turns), kind
items = {}
for l in open(ITEMS):
    if not l.strip():
        continue
    r = json.loads(l)
    items[r['item_id']] = {'nturns': len(r['turns'] or []), 'kind': r['kind']}
lead = {i for i, v in items.items() if v['nturns'] > 0}
nolead = set(items) - lead
print('items', len(items), 'lead', len(lead), 'nolead', len(nolead))
print('kind x lead:', sorted(Counter((v['kind'], v['nturns']) for v in items.values()).items()))

# key
key = json.load(open(D + 'creative_key_u.json'))
cover = Counter()
for lid, lst in key.items():
    for e in lst:
        cover[(e['arm'], e['item_id'])] += 1
exp = {(a, i) for a in ARMS for i in items}
print('key lines', len(key), 'pairs', sum(cover.values()),
      'missing pairs', len(exp - set(cover)), 'extra pairs', len(set(cover) - exp),
      'multi-covered pairs', sum(1 for v in cover.values() if v > 1))


def load(f):
    out = {}; dup = 0; vals = Counter(); bad = 0
    for l in open(D + f):
        if not l.strip():
            continue
        r = json.loads(l)
        if r['id'] in out:
            dup += 1
        u = r['useful']; m = r['made_up_user_facts']
        vals[(u, type(m).__name__)] += 1
        if u not in ('yes', 'no') or not isinstance(m, int) or isinstance(m, bool):
            bad += 1
        out[r['id']] = (u == 'yes', int(m))
    return out, dup, vals, bad


j1, d1, v1, b1 = load('j1/judgments.jsonl')
j2, d2, v2, b2 = load('j2/judgments.jsonl')
j3, d3, v3, b3 = load('j3/judgments.jsonl')
for n, j, d, v, b in [('j1', j1, d1, v1, b1), ('j2', j2, d2, v2, b2), ('j3', j3, d3, v3, b3)]:
    print(n, 'rows', len(j), 'dups', d, 'bad', b, 'value types', dict(v),
          'ids not in key', len(set(j) - set(key)))
ids = set(key)
miss1 = ids - set(j1); miss2 = ids - set(j2)
print('missing from j1', len(miss1), 'missing from j2', len(miss2))

verdict = {}
agree_u = 0; agree_m = 0; splits = set(); miss3 = 0
for lid in ids:
    u1, m1 = j1[lid]; u2, m2 = j2[lid]
    su = (u1 != u2); sm = ((m1 >= 1) != (m2 >= 1))
    agree_u += not su; agree_m += not sm
    if su or sm:
        splits.add(lid)
        if lid not in j3:
            miss3 += 1
            verdict[lid] = None
            continue
    u = u1 if not su else j3[lid][0]
    m = (m1 >= 1) if not sm else (j3[lid][1] >= 1)
    verdict[lid] = (u, m)
print('agree useful', agree_u, 'of', len(ids), '; agree made-up>=1', agree_m,
      '; split lines', len(splits), '; split lines missing from j3', miss3,
      '; j3 ids that were not splits', len(set(j3) - splits))

# expand to (arm,item)
res = {}
for lid, lst in key.items():
    for e in lst:
        res[(e['arm'], e['item_id'])] = verdict[lid]

# run files
fb = {}; bare = {}; lastcnt = {}
for a in ARMS:
    f = 0; b = 0; seen = Counter()
    for l in open(D + f'run/creative_{a}.jsonl'):
        if not l.strip():
            continue
        r = json.loads(l)
        if r.get('last') is not True:
            continue
        seen[r['item_id']] += 1
        rep = r['reply']
        if rep == FALLBACK:
            f += 1
        if BARE.search(rep):
            b += 1
    fb[a] = f; bare[a] = b
    lastcnt[a] = (len(seen), sum(seen.values()), set(seen) == set(items))
print('last rows per arm (distinct items, rows, matches items):', lastcnt)

S = {}
for a in ARMS:
    U = lambda sub: sum(1 for i in sub if res[(a, i)][0])
    S[a] = dict(useful=U(items), lead=U(lead), nolead=U(nolead),
                madeup=sum(1 for i in items if res[(a, i)][1]),
                fallbacks=fb[a], bare=bare[a])
    kinds = Counter(); kt = Counter()
    for i in items:
        kt[items[i]['kind']] += 1
        kinds[items[i]['kind']] += res[(a, i)][0]
    S[a]['per_kind'] = {k: f'{kinds[k]}/{kt[k]}' for k in sorted(kt)}
for a in ARMS:
    print(a, S[a])


def sign_p(b, c):
    n = b + c
    return sum(comb(n, k) for k in range(b, n + 1)) / 2 ** n if n else 1.0


def signs(A, Bm, sub):
    b = sum(1 for i in sub if res[(A, i)][0] and not res[(Bm, i)][0])
    c = sum(1 for i in sub if res[(Bm, i)][0] and not res[(A, i)][0])
    return b, c, sign_p(b, c)


X, K, B, T = S['X'], S['K'], S['B'], S['T']
b, c, p = signs('K', 'X', lead)
d = K['lead'] - X['lead']
k11 = d >= 6 and p <= 0.05
k12 = K['madeup'] <= X['madeup'] + 2
k13 = K['fallbacks'] <= X['fallbacks'] + 2
print(f"K1a.1 lead K={K['lead']} X={X['lead']} diff={d:+d} K-only={b} X-only={c} p={p:.6f} -> {'PASS' if k11 else 'FAIL'}")
print(f"K1a.2 madeup K={K['madeup']} X={X['madeup']} -> {'PASS' if k12 else 'FAIL'}")
print(f"K1a.3 fallbacks K={K['fallbacks']} X={X['fallbacks']} -> {'PASS' if k13 else 'FAIL'}")
print('K1a VERDICT', 'PASS' if (k11 and k12 and k13) else 'FAIL')
k21 = B['bare'] == 0 or B['bare'] < X['bare'] / 4
k22 = B['useful'] >= X['useful']
k23 = B['madeup'] <= X['madeup'] + 2 and B['fallbacks'] <= X['fallbacks'] + 2
bb, bc, bp = signs('B', 'X', items)
print(f"K1b.1 bare B={B['bare']} X={X['bare']} -> {'PASS' if k21 else 'FAIL'}")
print(f"K1b.2 useful60 B={B['useful']} X={X['useful']} -> {'PASS' if k22 else 'FAIL'}  (report-only sign test B-only={bb} X-only={bc} p={bp:.6f})")
print(f"K1b.3 madeup B={B['madeup']} X={X['madeup']}; fallbacks B={B['fallbacks']} X={X['fallbacks']} -> {'PASS' if k23 else 'FAIL'}")
print('K1b VERDICT', 'PASS' if (k21 and k22 and k23) else 'FAIL')
print('K-X no-lead', K['nolead'] - X['nolead'], '; K-T lead', K['lead'] - T['lead'])
for a in ['X', 'K', 'B', 'KB', 'KB0']:
    print(f"K1 line {a}: useful60={S[a]['useful']} T={T['useful']} >=T {S[a]['useful'] >= T['useful']} >=36 {S[a]['useful'] >= 36} -> {'MET' if S[a]['useful'] >= T['useful'] and S[a]['useful'] >= 36 else 'NOT MET'}")
print(f"T useful60={T['useful']} >=36 {T['useful'] >= 36}")
