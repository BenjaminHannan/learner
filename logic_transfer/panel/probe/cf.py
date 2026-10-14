"""Counterfactual prompt builder.  Parses a converted row back into its sentences (facts, rules, query, option suffix) by matching
the generator's own templates against the prompt, verifies the parse reproduces the row (template ids in order, exact re-assembly),
then makes minimal edits.  Every edited problem is re-labelled by logicgen.checker (the generator's own forward-chaining checker).
"""
import hashlib, random, re
from logicgen import checker as ck
from logicgen import templates as T
from logicgen.lexicon import ENTITIES

SUF = re.compile(r' \((\w+)/(\w+)/(\w+)\)$')
MAXP = 208


def _rng(*parts):
    return random.Random(int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:12], 16))


def fact_cands(lit):
    kind = 'FN' if lit[0] else 'FP'
    return [(f'{kind}:{i}', T.cap(t.format(e=T.cap(lit[2]), p=lit[1]))) for i, t in enumerate(T.TEMPLATES[kind])]


def rule_text(r, kind, i):
    t = T.TEMPLATES[kind][i]
    if kind == 'R5':
        s = t.format(e=T.cap(r.ent), a=T.phrase(*r.lhs[0]), b=T.phrase(*r.rhs))
    elif kind == 'R3':
        s = t.format(p=r.lhs[0][1], q=r.lhs[1][1], c=T.phrase(*r.rhs))
    else:
        s = t.format(p=r.lhs[0][1], q=r.rhs[1])
    return T.cap(s)


def rule_cands(r):
    kind = T.rule_kind(r)
    return [(f'{kind}:{i}', rule_text(r, kind, i)) for i in range(len(T.TEMPLATES[kind]))]


def q_text(lit, i):
    return T.cap(T.TEMPLATES['Q'][i].format(e=T.cap(lit[2]), p=lit[1], n='not ' if lit[0] else ''))


def parse(row):
    """-> dict(segs [{'kind','obj','tid','text'}] in sentence order, query, qi, qtext, suf [3 words]) or None if the parse fails."""
    meta, prompt = row['meta'], row['prompt']
    m = SUF.search(prompt)
    if not m:
        return None
    body, suf = prompt[:m.start()], list(m.groups())
    try:
        facts, rules, query = ck.parse_program(meta['program'])
    except Exception:
        return None
    qm = [i for i in range(len(T.TEMPLATES['Q'])) if body == q_text(query, i) or body.endswith(' ' + q_text(query, i))]
    if not qm:
        return None
    qi = max(qm, key=lambda i: len(q_text(query, i)))
    qt = q_text(query, qi)
    ctx = body[:len(body) - len(qt)].rstrip(' ')
    items = [('fact', f) for f in facts] + [('rule', r) for r in rules]
    cands = [fact_cands(o) if k == 'fact' else rule_cands(o) for k, o in items]
    used = [False] * len(ctx)
    assign = {}
    for k in sorted(range(len(items)), key=lambda k: -max(len(t) for _, t in cands[k])):
        best = None
        for tid, t in sorted(cands[k], key=lambda x: -len(x[1])):
            st = 0
            while True:
                j = ctx.find(t, st)
                if j < 0:
                    break
                e = j + len(t)
                if (j == 0 or ctx[j - 1] == ' ') and (e == len(ctx) or ctx[e] == ' ') and not any(used[j:e]):
                    best = (j, e, tid, t)
                    break
                st = j + 1
            if best:
                break
        if not best:
            return None
        used[best[0]:best[1]] = [True] * (best[1] - best[0])
        assign[k] = best
    segs = sorted(({'kind': items[k][0], 'obj': items[k][1], 'tid': b[2], 'text': b[3], 'pos': b[0]} for k, b in assign.items()), key=lambda s: s['pos'])
    if ' '.join(s['text'] for s in segs) != ctx:
        return None
    if [s['tid'] for s in segs] + [f'Q:{qi}'] != list(meta['template_ids']):
        return None
    p = dict(segs=segs, query=query, qi=qi, qtext=qt, suf=suf)
    if assemble(p) != prompt:
        return None
    return p


def assemble(p, segs=None, qtext=None, suf=None):
    segs = p['segs'] if segs is None else segs
    return ' '.join([s['text'] for s in segs] + [p['qtext'] if qtext is None else qtext]) + ' (' + '/'.join(p['suf'] if suf is None else suf) + ')'


def solve_of(segs, query):
    facts = [s['obj'] for s in segs if s['kind'] == 'fact']
    rules = [s['obj'] for s in segs if s['kind'] == 'rule']
    return ck.solve(facts, rules, query), facts, rules


def label_of(segs, query):
    res, _, _ = solve_of(segs, query)
    return 'error' if res.contradictions else res.label


def new_row(row, cond, prompt, answer, extra=None):
    r = {'id': f'cf-{cond}-{row["id"]}', 'prompt': prompt, 'answer': answer, 'accepted': [answer], 'family': row['family'], 'level': row['level'],
         'stage': 9, 'variant': 'cf', 'steps': ['none'], 'base_id': row['id'], 'cond': cond}
    if extra:
        r.update(extra)
    return r


PERMS = [(1, 0, 2), (0, 2, 1), (2, 1, 0), (1, 2, 0), (2, 0, 1)]     # the 5 non-identity permutations of 3 slots (new[i] = old[perm[i]])


def build(row, base_rows_for_donor=None):
    """-> dict cond -> list of new rows (each row carries 'exp' = checker label of the edited problem, plus bookkeeping), or None if unparsable."""
    p = parse(row)
    if p is None:
        return None
    meta, rid = row['meta'], row['id']
    lab = meta['label']
    out = {}
    query, segs = p['query'], p['segs']
    # (a) option permutations: two different non-identity permutations
    rg = _rng('perm', rid)
    for n, pm in enumerate(rg.sample(PERMS, 2)):
        suf2 = [p['suf'][pm[i]] for i in range(3)]
        out.setdefault('perm', []).append(new_row(row, f'perm{n}', assemble(p, suf=suf2), lab, dict(exp=lab, perm=list(pm), suf=suf2)))
    # (b) entity swap in the query: a same-length name that occurs nowhere in the problem
    rg = _rng('ent', rid)
    present = set(re.findall(r"[a-z]+", row['prompt'].lower()))
    e0 = query[2]
    pool = [e for e in ENTITIES if len(e) == len(e0) and e not in present]
    if pool:
        e2 = rg.choice(pool)
        q2 = (query[0], query[1], e2)
        exp = label_of(segs, q2)
        pr = assemble(p, qtext=q_text(q2, p['qi']))
        if exp != 'error' and len(pr) <= MAXP:
            out['ent'] = [new_row(row, 'ent', pr, exp, dict(exp=exp, new_ent=e2))]
    # (d) negate the query (same template)
    q2 = (not query[0], query[1], query[2])
    exp = label_of(segs, q2)
    pr = assemble(p, qtext=q_text(q2, p['qi']))
    if exp != 'error' and len(pr) <= MAXP:
        out['neg'] = [new_row(row, 'neg', pr, exp, dict(exp=exp))]
    # (c) delete the sentence that supports the answer / a sentence that does not
    res, facts, rules = solve_of(segs, query)
    used = []
    for k, s in enumerate(segs):
        if s['kind'] == 'fact' and s['obj'] in res.used_facts:
            used.append(k)
        if s['kind'] == 'rule' and rules.index(s['obj']) in res.used_rules:
            used.append(k)
    free = [k for k in range(len(segs)) if k not in used]
    rg = _rng('del', rid)
    if lab in ('true', 'false') and used:
        k = rg.choice(used)
        segs2 = segs[:k] + segs[k + 1:]
        exp = label_of(segs2, query)
        if exp != 'error':
            out['del_support'] = [new_row(row, 'del_support', assemble(p, segs=segs2), exp, dict(exp=exp, deleted=segs[k]['text'], n_free=len(free)))]
    if free:
        k = rg.choice(free)
        segs2 = segs[:k] + segs[k + 1:]
        exp = label_of(segs2, query)
        if exp == lab:
            out['del_distractor'] = [new_row(row, 'del_distractor', assemble(p, segs=segs2), exp, dict(exp=exp, deleted=segs[k]['text'], n_used=len(used)))]
    # (f) remove every context sentence: query + options only (the answer is unknown for any query)
    exp = label_of([], query)
    out['ctx_removed'] = [new_row(row, 'ctx_removed', assemble(p, segs=[]), exp, dict(exp=exp))]
    # (e) body swap: another row's whole question body with this row's option suffix
    if base_rows_for_donor:
        rg = _rng('body', rid)
        for _ in range(20):
            d = rg.choice(base_rows_for_donor)
            if d['id'] != rid:
                break
        dm = SUF.search(d['prompt'])
        pr = d['prompt'][:dm.start()] + ' (' + '/'.join(p['suf']) + ')'
        if pr != row['prompt']:
            out['body_swap'] = [new_row(row, 'body_swap', pr, d['meta']['label'], dict(exp=d['meta']['label'], donor=d['id']))]
    return out


def build_extra(row):
    """Content-free edits: (g) extra spaces after the first sentence (+2, +6 chars; same words, same label), (j) the same sentences in another order."""
    p = parse(row)
    if p is None or not p['segs']:
        return None
    out = {}
    lab = row['meta']['label']
    full = assemble(p)
    cut = len(p['segs'][0]['text'])
    for k in (2, 6):
        pr = full[:cut] + ' ' * k + full[cut:]
        if len(pr) <= MAXP:
            out[f'pad{k}'] = [new_row(row, f'pad{k}', pr, lab, dict(exp=lab))]
    if len(p['segs']) >= 2:
        rg = _rng('reorder', row['id'])
        for _ in range(50):
            order = list(range(len(p['segs'])))
            rg.shuffle(order)
            if [p['segs'][i]['text'] for i in order] != [s['text'] for s in p['segs']]:
                break
        segs2 = [p['segs'][i] for i in order]
        out['reorder'] = [new_row(row, 'reorder', assemble(p, segs=segs2), lab, dict(exp=lab))]
    return out


def build_extra2(row):
    """(h) swap the query predicate for a fresh same-length word (checker: unknown); (i) flip the polarity of the stated fact about the query pair (checker: true<->false)."""
    from logicgen.lexicon import COMMON_WORDS, nonsense_word
    p = parse(row)
    if p is None:
        return None
    out = {}
    query, segs = p['query'], p['segs']
    rid = row['id']
    present = set(re.findall(r"[a-z]+", row['prompt'].lower()))
    rg = _rng('predswap', rid)
    pool = [w for w in COMMON_WORDS if len(w) == len(query[1]) and w not in present]
    for _ in range(200):
        w = nonsense_word(rg)
        if len(w) == len(query[1]) and w not in present:
            pool.append(w)
    if pool:
        w2 = rg.choice(pool)
        q2 = (query[0], w2, query[2])
        exp = label_of(segs, q2)
        pr = assemble(p, qtext=q_text(q2, p['qi']))
        if exp != 'error' and len(pr) <= MAXP:
            out['predswap'] = [new_row(row, 'predswap', pr, exp, dict(exp=exp, new_pred=w2))]
    for k, s in enumerate(segs):
        if s['kind'] == 'fact' and s['obj'][1] == query[1] and s['obj'][2] == query[2]:
            neg, pred, ent = s['obj']
            i = int(s['tid'].split(':')[1])
            kind2 = 'FP' if neg else 'FN'
            lit2 = (not neg, pred, ent)
            t2 = T.cap(T.TEMPLATES[kind2][i].format(e=T.cap(ent), p=pred))
            segs2 = segs[:k] + [{'kind': 'fact', 'obj': lit2, 'tid': f'{kind2}:{i}', 'text': t2}] + segs[k + 1:]
            exp = label_of(segs2, query)
            pr = assemble(p, segs=segs2)
            if exp not in ('error', row['meta']['label']) and len(pr) <= MAXP:
                out['factflip'] = [new_row(row, 'factflip', pr, exp, dict(exp=exp))]
            break
    return out
