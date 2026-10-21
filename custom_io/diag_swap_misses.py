"""Confirm mark 5 (opswap) miss breakdown, read only, CPU fp32: the chain-5 rows of Tool.extra_evals' opswap check (right when intact, answer =
a call result, the swapped replay changes that value), run again with add <-> sub swapped in the calculator; every row whose answer is not the
model's own intact calls replayed with the swap is listed with both call lists, and classified by the first place the swapped run leaves the replay:
  program  - a different op (or a call added / dropped) in the swapped run, before any operand differs
  operand  - same ops so far, but an operand that should be an earlier (swapped) result or the same literal is written differently
  answer   - every call follows the replay, the final answer text is not the expected result
plus whether the replay holds a negative value (sub of a smaller by a larger number) and the expected answer's length.
Second reading (own_pointer): the same check with each operand's source taken from where the model's own span pointer copied it (a prompt
number or entry k), as B2's opswap uses B2's own pointers, instead of Tool.sources' text match (which credits an earlier result whenever the text
equals one). Operands written by the cells path keep the text match.
python3 -m custom_io.diag_swap_misses --ck CK [--ck CK2 ...] --big-data DIR --out OUT.json"""
import argparse, collections, json, os
import torch
from custom_io.data import collate, Dataset, load_rows, to_device
from custom_io.evalx import CHAIN5, is_hit
from custom_io.models import load_model
from custom_io.models.tool import INT_RE


@torch.no_grad()
def run_rows(m, rows, lesion=None, bs=100):
    """-> [(row, calls, answer, own)]: own[j] = per side ('p', None) a prompt span, ('t', entry k) an entry span, None = the cells path."""
    res = []
    for s0 in range(0, len(rows), bs):
        part = rows[s0:s0 + bs]
        b = to_device(collate([Dataset(part, m.vocab, strict=False)[i] for i in range(len(part))]), torch.device('cpu'))
        o = m.run(b, lesion=lesion)
        ans = m.talk(m.state_of(o), b)
        for i, r in enumerate(part):
            own = []
            for (t, *_) in o['calls'][i]:
                sp = o['steps'][t - 1][2] if len(o['steps'][t - 1]) > 2 else None
                side = []
                for k in ('a', 'b'):
                    if sp is None or float(sp['g' + k][i]) < 0:
                        side.append(None); continue
                    pos = int(sp['l' + k][i].argmax())
                    side.append(('p', None) if pos < sp['T'] else ('t', (pos - sp['T']) // sp['le']))
                own.append(side)
            res.append((r, o['calls'][i], ans[i], own))
    return res


def own_sources(m, calls, own):
    """Tool.sources, except a span-copied operand's source is the string the pointer copied from."""
    srcs = m.sources(calls, '')
    out = []
    for j, (src, sides) in enumerate(zip(srcs, own)):
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


def own_pointer(m, rows):
    """opswap with own-pointer sources -> dict(n_affected, match, unchanged, invalid)."""
    base = [x for x in run_rows(m, rows) if is_hit(x[2], x[0])]
    keep, st = [], dict(n_from_call=0, unchanged=0, invalid=0)
    for r, calls, ans, own in base:
        ks = [k for k in range(len(calls)) if calls[k][4] == ans]
        if not ks:
            continue
        st['n_from_call'] += 1
        v2 = m.replay(calls, own_sources(m, calls, own), swap=True)[ks[-1]]
        if v2 is None:
            st['invalid'] += 1
        elif str(v2) == ans:
            st['unchanged'] += 1
        else:
            keep.append((r, str(v2)))
    sw = {r['id']: ans for r, _, ans, _ in run_rows(m, [k[0] for k in keep], lesion='opswap')}
    hit = sum(sw[r['id']] == w for r, w in keep)
    return dict(st, n_affected=len(keep), match=round(100 * hit / max(len(keep), 1), 2), n_miss=len(keep) - hit)


def classify(c0, vals, c1, want, ans):
    """c0 intact calls, vals their swapped replay values, c1 the swapped run's calls -> (kind, call index, detail)."""
    srcs = None
    for j in range(max(len(c0), len(c1))):
        if j >= len(c0) or j >= len(c1) or c0[j][1] != c1[j][1]:
            return 'program', j, dict(intact=c0[j][1:4] if j < len(c0) else None, swapped=c1[j][1:4] if j < len(c1) else None)
    from custom_io.models.tool import Tool
    srcs = Tool.sources(c0, '')
    for j, (src, c) in enumerate(zip(srcs, c1)):
        for k, s in enumerate(src):
            exp = None if s is None else str(vals[s[1]]) if s[0] == 'e' else str(s[1])
            if exp is not None and c[2 + k] != exp:
                return 'operand', j, dict(side='ab'[k], want=exp, got=c[2 + k], from_result=s[0] == 'e')
    return 'answer', len(c1), dict(want=want, got=ans, got_is_a_result=ans in [c[4] for c in c1])


def misses(m, rows):
    base = [x[:3] for x in run_rows(m, rows) if is_hit(x[2], x[0])]
    keep = []
    for r, calls, ans in base:
        ks = [k for k in range(len(calls)) if calls[k][4] == ans]
        if not ks:
            continue
        vals = m.replay(calls, m.sources(calls, r['prompt']), swap=True)
        v2 = vals[ks[-1]]
        if v2 is not None and str(v2) != ans:
            keep.append((r, calls, vals, str(v2)))
    sw = {r['id']: (calls, ans) for r, calls, ans, _ in run_rows(m, [k[0] for k in keep], lesion='opswap')}
    out = []
    for r, c0, vals, want in keep:
        c1, ans = sw[r['id']]
        if ans == want:
            continue
        kind, j, det = classify(c0, vals, c1, want, ans)
        out.append(dict(id=r['id'], family=r['family'], kind=kind, at_call=j, detail=det, want=want, got=ans, negative=any(v is not None and v < 0 for v in vals),
                        want_len=len(want.lstrip('-')), intact_calls=[c[1:] for c in c0], swapped_calls=[c[1:] for c in c1], replay=vals))
    return out, len(keep)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ck', nargs='+', required=True)
    ap.add_argument('--big-data', required=True)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    rows = [r for r in load_rows(os.path.join(a.big_data, 'dev', 'in_dist.jsonl')) if r['family'] in CHAIN5]
    res = {}
    for ck in a.ck:
        m = load_model(ck, 'cpu')
        ms, n = misses(m, rows)
        summ = dict(n_affected=n, n_miss=len(ms), match=round(100 * (n - len(ms)) / max(n, 1), 2),
                    kinds=dict(collections.Counter(x['kind'] for x in ms)),
                    negative=dict(collections.Counter(f"{x['kind']} / {'negative in replay' if x['negative'] else 'no negative'}" for x in ms)),
                    families=dict(collections.Counter(x['family'] for x in ms)),
                    operand_from_result=dict(collections.Counter(str(x['detail'].get('from_result')) for x in ms if x['kind'] == 'operand')))
        summ['own_pointer'] = own_pointer(m, rows)
        res[ck] = dict(summary=summ, misses=ms)
        print(ck, json.dumps(summ))
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    json.dump(res, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
