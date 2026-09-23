import json, re, sys
V = sys.argv[1]
cases = {c['id']: c for c in json.load(open(f'{V}/cases.json'))}
def rows(a): return {r['id']: r for r in map(json.loads, open(f'{V}/rows-{a}.jsonl'))}
base = rows('base228'); FIX = [245, 246, 247, 248, 249, 250, 251]
def has(rep, v): return re.search(r'(?<![A-Za-z0-9])' + re.escape(v) + r'(?![A-Za-z0-9])', rep, re.I) is not None
def judge(c, r):
    vals = {x for t in r['before'] for x in (t[0], t[2]) if x != 'USER'}
    gold = set(c['gold']); allow = set(c['allow'])
    wrong = sorted(v for v in vals if v not in gold and v not in allow and not has(c['question'], v) and has(r['reply'], v))
    right = all(has(r['reply'], g) for g in gold) and not wrong
    if not gold:  # a correct reply gives no stored value
        right = not wrong and not any(has(r['reply'], v) for v in vals if v not in allow and not has(c['question'], v))
    write = r['after'] != r['before']
    return right, wrong, write
out = {}; lines = []
for f in FIX:
    fr = rows(str(f)); S = dict(claim_right_base=0, claim_right_fix=0, n_claim=0, wrong_base=[], wrong_fix=[], added=[],
                              qwrites_base=[], qwrites_fix=[], keep_changed=[], worse=[], better=[], trap_value_fix=[])
    lines.append(f"\n## fix {f}\n| id | kind | question | base reply | fix reply | base right | fix right | wrong(fix) | added | write |\n|---|---|---|---|---|---|---|---|---|---|")
    for cid, c in cases.items():
        if c['fix'] != f: continue
        b, x = base[cid], fr[cid]
        rb, wb, qb = judge(c, b); rx, wx, qx = judge(c, x)
        same = b['reply'] == x['reply']
        added = [] if same else wx
        if c['kind'] == 'claim':
            S['n_claim'] += 1; S['claim_right_base'] += rb; S['claim_right_fix'] += rx
        if wb: S['wrong_base'].append((cid, wb))
        if wx: S['wrong_fix'].append((cid, wx))
        if added: S['added'].append((cid, c['question'], x['reply'], added))
        if qb: S['qwrites_base'].append(cid)
        if qx: S['qwrites_fix'].append(cid)
        if c['kind'] == 'keep' and not same: S['keep_changed'].append((cid, c['question'], b['reply'], x['reply']))
        if c['kind'] == 'trap' and not rx: S['trap_value_fix'].append(cid)
        if (rb and not rx) or added or (qx and not qb): S['worse'].append((cid, c['kind'], c['question'], b['reply'], x['reply']))
        if rx and not rb: S['better'].append(cid)
        tr = lambda s: s.replace('|', '/')[:90]
        lines.append(f"| {cid} | {c['kind']} | {tr(c['question'])} | {tr(b['reply'])} | {tr(x['reply'])} | {int(rb)} | {int(rx)} | {','.join(wx) or '-'} | {','.join(added) or '-'} | {int(qx)} |")
    # spillover: other fixes' cases where this fix changed the reply vs base
    spill = []
    for cid, c in cases.items():
        if c['fix'] == f: continue
        b, x = base[cid], fr[cid]
        if b['reply'] != x['reply']:
            rb, wb, _ = judge(c, b); rx, wx, qx = judge(c, x)
            spill.append((cid, c['question'], b['reply'][:70], x['reply'][:90], int(rb), int(rx), wx, int(qx)))
    S['spill'] = spill
    out[f] = S
json.dump(out, open(f'{V}/summary.json', 'w'), indent=1)
open(f'{V}/tables.md', 'w').write('\n'.join(lines) + '\n')
for f, S in out.items():
    print(f"fix {f}: claims base {S['claim_right_base']}/{S['n_claim']} fix {S['claim_right_fix']}/{S['n_claim']}; wrong base {len(S['wrong_base'])} fix {len(S['wrong_fix'])} added {len(S['added'])}; qwrites base {len(S['qwrites_base'])} fix {len(S['qwrites_fix'])}; keep changed {len(S['keep_changed'])}; traps giving value {len(S['trap_value_fix'])}; worse {len(S['worse'])}; better {len(S['better'])}; spill {len(S['spill'])}")
    for w in S['wrong_fix']: print('   wrong', w)
    for a in S['added']: print('   ADDED', a)
    for k in S['keep_changed']: print('   keepchg', k)
    for w in S['worse']: print('   worse', w)
    for s in S['spill']: print('   spill', s)
