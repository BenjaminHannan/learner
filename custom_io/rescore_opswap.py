"""Confirm mark 5 (opswap) re-scored under MARKS-D0-T1 Amendment 12, read only, no training: the chain-5 rows of the big dev build, as
extra_evals' own opswap check (rows right when intact, answered from a call result / a NUM pointer, whose swapped replay changes that value),
for T1-line checkpoints (model 'tool') and B2 (model 'ledger'), with add <-> sub swapped in the calculator / executor.
  text_match   - T1 only: extra_evals' figure (an operand's source = the latest earlier call result with that text, else a literal)
  own_pointer  - the source of each operand is where the model's own pointer took it from: T1's span pointer (cells-path operands keep the
                 text match), B2's slot pointer (B2's own extra_evals definition)
  unambiguous  - only rows where no operand of the intact program has a text / value equal to both a question number and an earlier result;
                 scored with text_match for T1 and own_pointer for B2 (the two readings agree on these rows); ambiguous rows reported apart
  mark5        - Amendment 12: the LOWER of unambiguous and own_pointer, >= 99 with the unambiguous n >= 500 (the verdict is the judge's)
python3 -m custom_io.rescore_opswap --ck CK [CK ...] --big-data DIR --out OUT.json [--device cpu] [--threads 4]"""
import argparse, hashlib, json, os
import torch
from custom_io.data import collate, Dataset, load_rows, to_device
from custom_io.evalx import CHAIN5, evaluate, is_hit
from custom_io.models import load_model, progparse as pp

pc = lambda x, n: None if not n else round(100 * x / n, 2)


def batches(m, rs, dev, bs=100):
    for s in range(0, len(rs), bs):
        part = rs[s:s + bs]
        yield part, to_device(collate([Dataset(part, m.vocab, strict=False)[i] for i in range(len(part))]), dev)


@torch.no_grad()
def tool_rows(m, rows, dev, lesion=None):
    """T1 line -> [(row, calls, answer, own)]; own[j] per side: ('p',) a question-number span, ('t', k) entry k's span, None = cells path."""
    res = []
    for part, b in batches(m, rows, dev):
        o = m.run(b, lesion=lesion)
        ans = m.talk(m.state_of(o), b)
        for i, r in enumerate(part):
            own = []
            for (t, *_) in o['calls'][i]:
                st = o['steps'][t - 1]
                sp = st[2] if len(st) > 2 else None
                side = []
                for k in ('a', 'b'):
                    if sp is None or float(sp['g' + k][i]) < 0:
                        side.append(None)
                    else:
                        pos = int(sp['l' + k][i].argmax())
                        side.append(('p',) if pos < sp['T'] else ('t', (pos - sp['T']) // sp['le']))
                own.append(side)
            res.append((r, o['calls'][i], ans[i], own))
    return res


def tool_ambiguous(calls, prompt):
    qn = {str(x) for x in pp.prompt_numbers(prompt)}
    return any(x in qn and x in {c[4] for c in calls[:j]} for j, c in enumerate(calls) for x in (c[2], c[3]))


def tool_own_sources(m, calls, own):
    from custom_io.models.tool import INT_RE
    out = []
    for j, (src, sides) in enumerate(zip(m.sources(calls, ''), own)):
        row = []
        for k, (s, w) in enumerate(zip(src, sides)):
            x = calls[j][2 + k]
            if w is None:
                row.append(s)
            elif w[0] == 'p':
                row.append(('v', int(x)) if INT_RE.fullmatch(x or '') else None)
            else:
                ks = [q for q in range(j) if calls[q][0] - 1 == w[1]]
                row.append(('e', ks[-1]) if ks else s)
        out.append(row)
    return out


def score_tool(m, rows, dev):
    base = [x for x in tool_rows(m, rows, dev) if is_hit(x[2], x[0])]
    want = {}                                       # reading -> {row id: expected swapped answer}
    cnt = {k: dict(n=0, invalid=0, unchanged=0) for k in ('text_match', 'own_pointer', 'unambiguous')}
    amb = dict(rows=0)
    for r, calls, ans, own in base:
        ks = [k for k in range(len(calls)) if calls[k][4] == ans]
        if not ks:
            continue
        a = tool_ambiguous(calls, r['prompt'])
        amb['rows'] += a
        for key, srcs in (('text_match', m.sources(calls, r['prompt'])), ('own_pointer', tool_own_sources(m, calls, own))):
            for kk in ((key, 'unambiguous') if key == 'text_match' and not a else (key,)):
                cnt[kk]['n'] += 1
                v2 = m.replay(calls, srcs, swap=True)[ks[-1]]
                if v2 is None:
                    cnt[kk]['invalid'] += 1
                elif str(v2) == ans:
                    cnt[kk]['unchanged'] += 1
                else:
                    want.setdefault(kk, {})[r['id']] = str(v2)
    ids = set().union(*[set(w) for w in want.values()]) if want else set()
    sw = {r['id']: ans for r, _, ans, _ in tool_rows(m, [r for r in rows if r['id'] in ids], dev, lesion='opswap')}
    out = {}
    for k, c in cnt.items():
        w = want.get(k, {})
        hit = sum(sw[i] == v for i, v in w.items())
        out[k] = dict(c, n_affected=len(w), match=pc(hit, len(w)), n_miss=len(w) - hit)
    out['ambiguous'] = dict(rows_from_call=cnt['text_match']['n'], ambiguous_rows=amb['rows'], rate=pc(amb['rows'], cnt['text_match']['n']))
    return out


@torch.no_grad()
def score_ledger(m, rows, dev):
    from custom_io.models.ledger import ADD, SUB, R0, N_NUM, replay
    ip = evaluate(m, rows, 100, dev, None, return_preds=True)['preds']
    c = {k: dict(n=0, invalid=0, unchanged=0, aff=0, match=0) for k in ('own_pointer', 'unambiguous')}
    amb = 0
    for part, b in batches(m, [r for r in rows if is_hit(ip[r['id']], r)], dev):
        o = m.run(b)
        outs = m.talk(m.state(b, lesion='opswap'), b)
        ops, a, bb = o['prog']
        v2, ok2 = replay(o['vals'], o['valid'], ops, a, bb, swap=True)
        k = o['lans'].argmax(-1, keepdim=True)
        num = ((o['lmode'].argmax(-1) == 0) & o['valid'].gather(1, k)[:, 0]).tolist()
        ok_sw, chg = ok2.gather(1, k)[:, 0].tolist(), (v2.gather(1, k)[:, 0] != o['vals'].gather(1, k)[:, 0]).tolist()
        want = [str(x) for x in v2.gather(1, k)[:, 0].tolist()]
        vals, valid = o['vals'].tolist(), o['valid'].tolist()
        for i in range(len(want)):
            if not num[i]:
                continue
            qn = {vals[i][j] for j in range(N_NUM) if valid[i][j]}
            res = lambda s: {vals[i][R0 + q] for q in range(s) if int(ops[i, q]) != 0 and valid[i][R0 + q]}
            is_amb = any(int(ops[i, s]) != 0 and vals[i][int(p[i, s])] in qn and vals[i][int(p[i, s])] in res(s)
                         for s in range(ops.shape[1]) for p in (a, bb))
            amb += is_amb
            for key in (('own_pointer',) if is_amb else ('own_pointer', 'unambiguous')):
                x = c[key]
                x['n'] += 1
                if not ok_sw[i]:
                    x['invalid'] += 1
                elif not chg[i]:
                    x['unchanged'] += 1
                else:
                    x['aff'] += 1; x['match'] += outs[i] == want[i]
    out = {k: dict(n=x['n'], invalid=x['invalid'], unchanged=x['unchanged'], n_affected=x['aff'], match=pc(x['match'], x['aff']),
                   n_miss=x['aff'] - x['match']) for k, x in c.items()}
    out['ambiguous'] = dict(rows_from_call=c['own_pointer']['n'], ambiguous_rows=amb, rate=pc(amb, c['own_pointer']['n']))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ck', nargs='+', required=True)
    ap.add_argument('--big-data', required=True)
    ap.add_argument('--device', default='cpu')
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    dev = torch.device(a.device)
    path = os.path.join(a.big_data, 'dev', 'in_dist.jsonl')
    rows = [r for r in load_rows(path) if r['family'] in CHAIN5]
    res = dict(in_dist_sha256=hashlib.sha256(open(path, 'rb').read()).hexdigest(), n_chain5=len(rows), device=a.device, runs={})
    if os.path.exists(a.out):
        res['runs'] = json.load(open(a.out)).get('runs', {})
    for ck in a.ck:
        m = load_model(ck, dev)
        m.eval()
        name = os.path.basename(os.path.dirname(ck))
        kind = type(m).__name__
        s = score_tool(m, rows, dev) if hasattr(m, 'sources') else score_ledger(m, rows, dev)
        lo = [s[k]['match'] for k in ('unambiguous', 'own_pointer') if s[k]['match'] is not None]
        s['mark5'] = dict(value=min(lo) if len(lo) == 2 else None, unambiguous_n=s['unambiguous']['n_affected'],
                          ok=len(lo) == 2 and min(lo) >= 99 and s['unambiguous']['n_affected'] >= 500)
        res['runs'][name] = dict(model=kind, ck=ck, ck_sha256=hashlib.sha256(open(ck, 'rb').read()).hexdigest(), **s)
        print(name, json.dumps({k: (v.get('match') if isinstance(v, dict) and 'match' in v else v) for k, v in s.items()}), flush=True)
        json.dump(res, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
