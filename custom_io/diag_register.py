"""Diagnostics for the register loop (A / A0): step parsing, counterfactuals, staircase, round-1 register interchange.
Model side needs: model.rounds(batch, S0=None, start=0) -> iterator of S_r, model.talk(S[:, :n_reg], batch), model.n_loops, model.n_reg."""
import os, re
from collections import defaultdict
import torch
from custom_io.data import Dataset, collate, load_rows, to_device

try:
    from custom_io.evalx import CHAIN5
except ImportError:
    CHAIN5 = ['chain_ops', 'chain_story2', 'story_chain3', 'state_update', 'var_chain']

NUM = re.compile(r'(?:=|->)\s*(-?\d+)\s*$')                                           # value written at the end of a step line
ARITH = re.compile(r'^(?:\w+\s*=\s*)?(-?\d+)\s*([-+*/])\s*(-?\d+)\s*=\s*(-?\d+)$')    # 'a op b = c' and 'p = a op b = c'
DELTA = re.compile(r'^([+-])(\d+)\s*->\s*(-?\d+)$')                                   # state_update '+n -> v'


def step_values(row, use_steps=True):
    """Target list for the rounds: step values (strings), answer appended unless already last. Just [answer] unless use_steps
    and the row has >= 2 step LINES (as the prototype: one-line rows never get a separate round-1 target)."""
    st = row.get('steps') or []
    if not use_steps or len(st) < 2:
        return [row['answer']]
    v = [m.group(1) for s in st for m in [NUM.search(s)] if m]
    if not v or v[-1] != row['answer']:
        v.append(row['answer'])
    return v


def _op(a, o, b):
    if o == '+': return a + b
    if o == '-': return a - b
    if o == '*': return a * b
    return a // b if b != 0 and a % b == 0 else None        # exact division only


def counterfactual(row, v1):
    """Re-apply the row's operations 2..k starting from v1 (int) in place of its own first value -> int, or
    (None, reason). Needs every step line to parse as 'a op b = c' / 'p = a op b = c' / '+n -> v' with consistent
    arithmetic, the running value to be an operand (the left one if both match) and the last value to be the answer."""
    st = row.get('steps') or []
    if len(st) < 2:
        return None, 'one_step'
    prev, v = None, v1
    for i, s in enumerate(st):
        s = s.strip()
        m, d = ARITH.match(s), DELTA.match(s)
        if m:
            a, o, b, c = int(m[1]), m[2], int(m[3]), int(m[4])
            if _op(a, o, b) != c:
                return None, 'inconsistent'
            if i == 0:
                prev = c
                continue
            if a == prev:
                v = _op(v, o, b)
            elif b == prev:
                v = _op(a, o, v)
            else:
                return None, 'operand_not_running_value'
        elif d:
            n, c = int(d[2]) * (1 if d[1] == '+' else -1), int(d[3])
            if i == 0:
                prev = c
                continue
            if c != prev + n:
                return None, 'inconsistent'
            v += n
        else:
            return None, 'unparsed_step'
        if v is None:
            return None, 'inexact_division'
        prev = c
    return (v, None) if str(prev) == row['answer'] else (None, 'last_value_not_answer')


def pick_donors(rows):
    """-> ([(i, j, cf)], skipped {reason: n}) over rows with >= 2 step values. Donor j: same family (same variant
    preferred), integer first value different from i's, with >= 2 values, such that the counterfactual of row i from the
    donor's first value is computable and differs from i's own answer. Deterministic: first candidate after i in file order
    (cyclic), same-variant candidates before others. Independent of any model."""
    vals = [step_values(r) for r in rows]
    ok = [i for i, v in enumerate(vals) if len(v) >= 2 and rows[i].get('steps')]
    fam = defaultdict(list)
    for i in ok:
        fam[rows[i]['family']].append(i)
    out, skip = [], defaultdict(int)
    for i in ok:
        L = fam[rows[i]['family']]
        k = L.index(i)
        cands = [L[(k + t) % len(L)] for t in range(1, len(L))]
        cands = [j for j in cands if re.fullmatch(r'-?\d+', vals[j][0]) and vals[j][0] != vals[i][0]]
        cands = [j for j in cands if rows[j].get('variant') == rows[i].get('variant')] + [j for j in cands if rows[j].get('variant') != rows[i].get('variant')]
        why = 'no_donor' if not cands else None
        for j in cands:
            cf, why = counterfactual(rows[i], int(vals[j][0]))
            if cf is not None and str(cf) != rows[i]['answer']:
                out.append((i, j, str(cf)))
                break
            why = why or 'cf_equals_own_answer'
        else:
            skip[why] += 1
    return out, dict(skip)


def _pct(c, n):
    return 100 * c / max(n, 1)


@torch.no_grad()
def staircase(model, rows, device, batch_size=100, amp=None):
    """Rows with >= 2 step values: for r=1..R, % whose round-r register readout equals vals[min(r,k)-1]."""
    R, ds = model.n_loops, Dataset(rows, model.vocab, strict=False)
    hit, fam = [[0] * R for _ in rows], defaultdict(lambda: [0, [0] * R])
    for s in range(0, len(rows), batch_size):
        ids = list(range(s, min(s + batch_size, len(rows))))
        b = to_device(collate([ds[i] for i in ids]), device)
        with (amp() if amp else torch.autocast('cpu', enabled=False)):
            for r, S in enumerate(model.rounds(b)):
                for i, p in zip(ids, model.talk(S[:, :model.n_reg], b)):
                    v = step_values(rows[i])
                    hit[i][r] = int(p == v[min(r + 1, len(v)) - 1])
    for r_, h in zip(rows, hit):
        f = fam[r_['family']]
        f[0] += 1
        f[1] = [a + b for a, b in zip(f[1], h)]
    tot = [sum(h[r] for h in hit) for r in range(R)]
    return {'n': len(rows), 'by_round': [_pct(c, len(rows)) for c in tot],
            'by_family': {k: {'n': n, 'by_round': [_pct(c, n) for c in cs]} for k, (n, cs) in fam.items()}}


@torch.no_grad()
def interchange(model, rows, device, batch_size=100, amp=None):
    """Round-1 register interchange. Donor row's prompt -> registers after round 1; rounds 2..R then run from those registers
    (the CURRENT row's own round-1 scratch and prompt are kept; full-state swap reported as cf_match_full / own_match_full). cf_match = % equal to the counterfactual; own_match = % equal to the
    row's own answer; intact_own = the unmodified model on the same rows."""
    pairs, skipped = pick_donors(rows)
    ds = Dataset(rows, model.vocab, strict=False)
    cf = own = intact = cff = ownf = 0
    fam = defaultdict(lambda: [0, 0, 0, 0])
    for s in range(0, len(pairs), batch_size):
        ch = pairs[s:s + batch_size]
        cur, don = (to_device(collate([ds[k] for k in ks]), device) for ks in ([c[0] for c in ch], [c[1] for c in ch]))
        with (amp() if amp else torch.autocast('cpu', enabled=False)):
            S1d, S1c = (next(iter(model.rounds(b_, loops=1))) for b_ in (don, cur))
            outs = []
            for S0 in (torch.cat([S1d[:, :model.n_reg], S1c[:, model.n_reg:]], 1), S1d):     # register swap, full swap
                S = None
                for S in model.rounds(cur, S0=S0, start=1):
                    pass
                outs.append(model.talk(S[:, :model.n_reg], cur))
            out, outf = outs
            full = model.talk(model.state(cur), cur)
        for (i, _, c), p, q, pf in zip(ch, out, full, outf):
            a = rows[i]['answer']
            f = fam[rows[i]['family']]
            f[0] += 1; f[1] += p == c; f[2] += p == a; f[3] += q == a
            cf += p == c; own += p == a; intact += q == a; cff += pf == c; ownf += pf == a
    n = len(pairs)
    return {'n_scored': n, 'n_skipped': sum(skipped.values()), 'skip_reasons': skipped,
            'cf_match': _pct(cf, n), 'own_match': _pct(own, n), 'intact_own': _pct(intact, n),
            'cf_match_full': _pct(cff, n), 'own_match_full': _pct(ownf, n),
            'by_family': {k: {'n': a, 'cf_match': _pct(b, a), 'own_match': _pct(c, a), 'intact_own': _pct(d, a)} for k, (a, b, c, d) in fam.items()}}


def chain5_rows(root):
    """CHAIN5 in_dist rows of a data root (root/dev/in_dist.jsonl or root/in_dist.jsonl) with >= 2 step values."""
    d = os.path.join(root, 'dev')
    rows = load_rows(os.path.join(d if os.path.isdir(d) else root, 'in_dist.jsonl'))
    return [r for r in rows if r['family'] in CHAIN5 and len(step_values(r)) >= 2]
