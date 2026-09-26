import json, re, ast, glob, os
from collections import Counter, defaultdict
from math import comb

B = '/home/user/learner/artifacts/claude-mu403-20260926'
ARMS = 'RFPT'

def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()]

# panel
items = jl(f'{B}/devchat/items.jsonl')
panel_kinds = {it['item_id']: [t['kind'] for t in it['turns']] for it in items}
n_turns_panel = sum(len(v) for v in panel_kinds.values())

# replies
chat = {}
kinds_ok = True
for a in ARMS:
    rows = jl(f'{B}/run/chat_{a}.jsonl')
    d = {}
    for r in rows:
        key = (r['item_id'], r['turn_i'])
        assert key not in d, ('dup', a, key)
        d[key] = r
    chat[a] = d
    # consistency with panel
    for iid, ks in panel_kinds.items():
        for i, k in enumerate(ks):
            # turn_i may be 0- or 1-based; detect below
            pass
# detect turn_i base
tis = sorted({k[1] for k in chat['R']})
base = min(tis)
for a in ARMS:
    for iid, ks in panel_kinds.items():
        for i, k in enumerate(ks):
            r = chat[a].get((iid, i + base))
            if r is None or r['kind'] != k:
                kinds_ok = False
    if len(chat[a]) != n_turns_panel:
        kinds_ok = False

conv_len = {iid: len(ks) for iid, ks in panel_kinds.items()}

# claims
key = json.load(open(f'{B}/judge/keys/claims_key.json'))
judgements = defaultdict(list)  # (arm,item) -> list of (judge, flags)
dup_in_judge = 0
unknown_pid = 0
for p in sorted(glob.glob(f'{B}/judge/out/claims_j*.jsonl')):
    j = os.path.basename(p)
    seen = set()
    for r in jl(p):
        if r['pid'] in seen:
            dup_in_judge += 1
        seen.add(r['pid'])
        if r['pid'] not in key:
            unknown_pid += 1
            continue
        k = key[r['pid']]
        judgements[(k['arm'], k['item_id'])].append((j, r['pid'], r['flags']))

bad_len = []
bad_vals = 0
res = {}
for a in ARMS:
    C = 0; both = 0; either = 0; by_kind = Counter(); two = 0; distinct_two = 0
    per_conv = {}
    for iid in panel_kinds:
        js = judgements.get((a, iid), [])
        if len(js) == 2:
            two += 1
            if js[0][0] != js[1][0]:
                distinct_two += 1
        L = conv_len[iid]
        for (jn, pid, fl) in js:
            if len(fl) != L:
                bad_len.append((a, iid, jn, pid, len(fl), L))
            for v in fl:
                if v not in (0, 1):
                    bad_vals += 1
        s = 0
        for t in range(L):
            vals = [fl[t] if t < len(fl) else 0 for (_, _, fl) in js]
            s += sum(vals)
            for v in vals:
                if v:
                    by_kind[panel_kinds[iid][t]] += 1
            if len(vals) == 2 and all(vals):
                both += 1
            if any(vals):
                either += 1
        per_conv[iid] = s
        C += s
    res[a] = dict(C=C, both=both, either=either, by_kind=dict(sorted(by_kind.items())),
                  two_judgements=two, two_distinct_judges=distinct_two, per_conv=per_conv)

def sign(x, y):
    more = sum(1 for i in panel_kinds if x[i] > y[i])
    fewer = sum(1 for i in panel_kinds if x[i] < y[i])
    n = more + fewer
    p = sum(comb(n, k) for k in range(more, n + 1)) / 2 ** n if n else 1.0
    return more, fewer, 80 - n, p

# V404
wf = None
for line in open(f'{B}/run/logR.txt'):
    if line.startswith('mu404: facts'):
        d = ast.literal_eval(line[len('mu404: facts'):].strip())
        wf = d['with_facts']
CR, CF, CP, CT = (res[a]['C'] for a in ARMS)
V404 = wf is not None and wf >= 40
N1 = (CR - CF >= 10) and (CF <= 0.67 * CR)
m, f, t, p = sign(res['R']['per_conv'], res['F']['per_conv'])
N2 = m > f and p <= 0.05
PW404 = CF >= CR
if not V404:
    v404 = 'INCONCLUSIVE'
elif PW404:
    v404 = 'PROVED WRONG'
elif V404 and N1 and N2:
    v404 = 'PASS'
else:
    v404 = 'FAIL'

# V403 sysline
diff = sum(1 for k in chat['R'] if chat['P'][k]['reply'] != chat['R'][k]['reply'])
nP = len(chat['P'])
V403 = diff >= nP / 3
M1 = (CR - CP >= 10) and (CP <= 0.67 * CR)
m2, f2, t2, p2 = sign(res['R']['per_conv'], res['P']['per_conv'])
M2 = m2 > f2 and p2 <= 0.05
wins = losses = ties = 0
pair_items = Counter()
for pj in ('p1', 'p2'):
    pk = json.load(open(f'{B}/judge/keys/pair_key_{pj}.json'))
    for r in jl(f'{B}/judge/out/pair_{pj}.jsonl'):
        k = pk[r['pid']]
        pair_items[pj] += 1
        w = r['winner']
        if w == 'tie':
            ties += 1
        elif k[w] == 'P':
            wins += 1
        elif k[w] == 'R':
            losses += 1
        else:
            raise SystemExit('bad pair arm')
M3 = (losses - wins) <= 16
M4 = CP <= CT
PW403 = CP >= CR
if not V403:
    v403 = 'INCONCLUSIVE'
elif PW403:
    v403 = 'PROVED WRONG'
elif all([V403, M1, M2, M3, M4]):
    v403 = 'PASS'
else:
    v403 = 'FAIL'

out = dict(
    panel=dict(conversations=len(items), turns=n_turns_panel, turn_i_base=base, kinds_consistent=kinds_ok),
    claims_rows_dup_in_judge=dup_in_judge, unknown_pids=unknown_pid, bad_flag_values=bad_vals,
    bad_len_packets=bad_len,
    arms={a: {k: v for k, v in res[a].items() if k != 'per_conv'} for a in ARMS},
    mu404=dict(with_facts=wf, V404=V404, C_R=CR, C_F=CF, N1_diff=CR - CF, N1_ratio_bar=0.67 * CR, N1=N1,
               N2_R_more=m, N2_R_fewer=f, N2_ties=t, N2_p=p, N2=N2, proved_wrong=PW404, verdict=v404),
    mu403=dict(differ=diff, of=nP, bar=nP / 3, V403=V403, C_R=CR, C_P=CP, M1_diff=CR - CP, M1_ratio_bar=0.67 * CR, M1=M1,
               M2_R_more=m2, M2_R_fewer=f2, M2_ties=t2, M2_p=p2, M2=M2,
               M3_P_wins=wins, M3_P_losses=losses, M3_ties=ties, M3_losses_minus_wins=losses - wins, M3=M3,
               pair_rows=dict(pair_items), C_T=CT, M4=M4, proved_wrong=PW403, verdict=v403),
)
json.dump(out, open('/tmp/claude-0/-home-user-learner/4d3f42a5-cfd2-59d7-9fb6-803bbe0862d0/scratchpad/recount404/mine.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
