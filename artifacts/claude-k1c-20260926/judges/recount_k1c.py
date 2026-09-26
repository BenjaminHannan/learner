"""Blind recount of k1c_reg creative results. Prints numbers and arm ids only."""
import json, collections
from math import comb
from fractions import Fraction

S = '/tmp/claude-0/-home-user-learner/936f6d07-c919-50cf-a53a-bafcb44ae6da/scratchpad/k1c_reg'
PANELS = {'A': '/home/user/learner/artifacts/claude-k1cpanel-20260926/creative/items.jsonl',
          'B': '/home/user/learner/artifacts/claude-k1apanel-20260926/creative/items.jsonl'}
ARMS = ['C', 'K', 'T', 'Q', 'L']
FALLBACK = "I don't have a good idea for that yet, but I'm happy to try again if you tell me a bit more."

def rl(p):
    return [json.loads(l) for l in open(p) if l.strip()]

# panels: item_id, kind, turns length only
items = {}
for P, path in PANELS.items():
    for d in rl(path):
        items[d['item_id']] = {'panel': P, 'kind': d['kind'], 'nturns': len(d['turns'])}
assert len(items) == 160
lead = {i for i, v in items.items() if v['nturns'] > 1}

# judges
j1 = {d['id']: d for d in rl(S + '/j1.jsonl')}
j2 = {d['id']: d for d in rl(S + '/j2.jsonl')}
j3 = {d['id']: d for d in rl(S + '/judges/j3/judgments.jsonl')}
assert set(j1) == set(j2) and len(j1) == 716
for j in (j1, j2, j3):
    for d in j.values():
        assert d['useful'] in ('yes', 'no')
        assert isinstance(d['made_up_user_facts'], int)

agree_u = agree_m = 0
need_j3 = set()
verdict = {}
missing_j3 = 0
for lid in j1:
    u1, u2 = j1[lid]['useful'] == 'yes', j2[lid]['useful'] == 'yes'
    m1, m2 = j1[lid]['made_up_user_facts'] >= 1, j2[lid]['made_up_user_facts'] >= 1
    if u1 == u2:
        agree_u += 1; u = u1
    else:
        need_j3.add(lid)
        if lid in j3: u = j3[lid]['useful'] == 'yes'
        else: missing_j3 += 1; u = None
    if m1 == m2:
        agree_m += 1; m = m1
    else:
        need_j3.add(lid)
        if lid in j3: m = j3[lid]['made_up_user_facts'] >= 1
        else: missing_j3 += 1; m = None
    verdict[lid] = (u, m)
print('lines', len(j1), 'j3_lines', len(j3), 'lines_needing_j3', len(need_j3),
      'j3_extra', len(set(j3) - need_j3), 'missing_j3', missing_j3)

# keys -> per (arm,item) verdict
per = {}
for P in 'AB':
    key = json.load(open(S + f'/run/{P}/creative_key_u.json'))
    for lid, lst in key.items():
        for e in lst:
            k = (e['arm'], e['item_id'])
            assert k not in per, k
            assert items[e['item_id']]['panel'] == P
            per[k] = verdict[lid]
assert len(per) == 5 * 160

# run rows: last replies
last = {}
for P in 'AB':
    for a in ARMS:
        for d in rl(S + f'/run/{P}/creative_{a}.jsonl'):
            if d.get('last') is True:
                k = (a, d['item_id'])
                assert k not in last
                last[k] = d['reply']
assert len(last) == 800

# consistency: arms sharing a key line have identical last replies
bad = 0
for P in 'AB':
    key = json.load(open(S + f'/run/{P}/creative_key_u.json'))
    for lid, lst in key.items():
        rs = {last[(e['arm'], e['item_id'])] for e in lst}
        if len(rs) != 1 or len({e['item_id'] for e in lst}) != 1: bad += 1
print('key_lines_with_nonidentical_replies', bad)

useful = {a: {i for i in items if per[(a, i)][0]} for a in ARMS}
madeup = {a: {i for i in items if per[(a, i)][1]} for a in ARMS}
print('\n1. arm useful useful_A useful_B useful_lead made_up fallback fallback_stripped')
print('   lead items', len(lead))
for a in ARMS:
    U = useful[a]
    fb = sum(1 for i in items if last[(a, i)] == FALLBACK)
    fbs = sum(1 for i in items if last[(a, i)].strip() == FALLBACK)
    print(' ', a, len(U), sum(1 for i in U if items[i]['panel'] == 'A'),
          sum(1 for i in U if items[i]['panel'] == 'B'), len(U & lead), len(madeup[a]), fb, fbs)

def sign_p(b, c):
    n = b + c
    return float(Fraction(sum(comb(n, x) for x in range(b, n + 1)), 2 ** n)) if n else 1.0

b = len(useful['C'] - useful['K']); c = len(useful['K'] - useful['C'])
print('\n2. C_only', b, 'K_only', c, 'C_minus_K', len(useful['C']) - len(useful['K']), 'p_one_sided', '%.6g' % sign_p(b, c))

print('\n3. first rival first_only rival_only')
for f in ('C', 'K'):
    for r in ('T', 'Q', 'L'):
        print(' ', f, r, len(useful[f] - useful[r]), len(useful[r] - useful[f]))

print('\n4. items_C_last_differs_from_K', sum(1 for i in items if last[('C', i)] != last[('K', i)]))
print('\n5. j1_j2_agree_useful', agree_u, 'j1_j2_agree_madeup_ge1', agree_m)
