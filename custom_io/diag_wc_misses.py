"""Amendment 6 / 7 CPU checks (MARKS-D0-T1-2026-10-07.md), read only, on saved T1S / T1SI / T1SD checkpoints:
(a) breakdown: write_copy_u's own draws (passes 0..P-1, the passes its WC.json used), every UNAMBIGUOUS operand copy event the model
    missed, classified per length from the call round's span pointer and gate (the misses at length L, default 8, are also listed):
      cells          the gate chose T1's cells, not the span
      other_result   the start pointer sits on the units digit of another entry's result
      other_number   the start pointer sits on the units digit of some other number (an operand inside an entry, or a prompt number)
      mid_number     the start pointer sits on a char that is not a number's units digit (e.g. inside the wanted number: the copy
                     then reads only the digits left of it, a front part of the number)
      cut_short      right start, the copy stopped early (the text is a suffix of the wanted number)
      too_long       right start, the copy ran on past the number's front
      other          right start, anything else
    unambiguous ANSWER misses (Amendment 7) are classified the same way from the talker's answer pointer, with 'not_span' (the mode head
    chose WORD or GEN, not the span) in place of 'cells' and 'same_entry_operand' (the pointer sits on an operand's units digit inside the
    entry whose result is the answer) and 'prompt_number' (on a number's units digit in the prompt) split out of other_number; the answer
    misses at --answer-lengths are also listed.
(b) noise: a fresh draw (oracle seed + '|fresh<p>', same rows and scorer rule) until the length-L unambiguous operand cell and every
    --answer-lengths answer cell have n >= --fresh-n, every operand / answer cell 1-9 reported with n.
Same rows, oracle and unambiguous rule as Tool.write_copy_u; CPU fp32 here (the box scored in bf16 on cuda), so counts can differ slightly.
python3 -m custom_io.diag_wc_misses --ck CK [--ck CK2 ...] --big-data DIR [--passes 2] [--length 8] [--answer-lengths 7 8 9]
    [--fresh-n 1000] --out OUT.json"""
import argparse, json, os, random, re, time
import torch
from custom_io.data import PAD, collate, Dataset, load_rows, to_device
from custom_io.evalx import is_hit, subsample
from custom_io.models import load_model, progparse as pp
from custom_io.models.tool import ENT_NUM, N_RES, rand_digits

CONSTS = {str(c) for c in pp.CONSTS}


def unamb(x, res, pn):
    return sum(y == x for y in res) == 1 and x not in pn and x not in CONSTS


def rows_of(big):
    rows = load_rows(os.path.join(big, 'dev', 'in_dist.jsonl'))
    prows = [r for r in rows if pp.row_targets(r)['prog']]
    return prows if len(prows) <= 3000 else subsample(prows, 3000)


@torch.no_grad()
def run_rows(m, rs, bs, oracle=None):
    """-> [(row, calls, answer, per-call span info {j: dict(side -> (gate>=0, start pos, segment string, segment start, slot))},
            answer span info (mode == 0, start pos, segment string, segment start, slot) or None)]"""
    out = []
    for s0 in range(0, len(rs), bs):
        part = rs[s0:s0 + bs]
        b = to_device(collate([Dataset(part, m.vocab, strict=False)[i] for i in range(len(part))]), torch.device('cpu'))
        o = m.run(b, oracle=None if oracle is None else (lambda i, t, c, _b=b: oracle(_b['rows'][i], t, c)))
        st = m.state_of(o)
        ans, modes = m.talk(st, b, return_modes=True)
        aseg = [None] * len(part)
        if m.span_copy:                                  # the talker's answer pointer, recomputed as Tool.talk computes it
            X, xm = m.read(b, talker=True)
            Xt, idt, vis = st[1:4]
            Xc, mc = torch.cat([X, Xt.to(X.dtype)], 1), torch.cat([xm, vis.bool()], 1)
            T, le = X.shape[1], Xt.shape[1] // N_RES
            la, ids_a = m.ptr(st[6], m.span_keys(Xc, T, le, mc), mc), torch.cat([b['prompt_ids'], idt.long()], 1)
            for i in range(len(part)):
                aseg[i] = (modes[i] == 0,) + seg_at(m, int(la[i].argmax()), T, le, ids_a[i].tolist())
        for i, r in enumerate(b['rows']):
            info = {}
            for j, c in enumerate(o['calls'][i]):
                st = o['steps'][c[0] - 1]
                if len(st) < 3:
                    continue
                sp, d = st[2], {}
                T, le, ids = sp['T'], sp['le'], sp['ids'][i].tolist()
                for side, (lk, gk) in enumerate((('la', 'ga'), ('lb', 'gb'))):
                    d[side] = (bool(sp[gk][i] >= 0),) + seg_at(m, int(sp[lk][i].argmax()), T, le, ids)
                info[j] = d
            out.append((r, o['calls'][i], ans[i], info, aseg[i]))
    return out


def seg_at(m, p0, T, le, ids):
    """-> (p0, the string p0 is in, its first position, entry slot or None for the prompt)."""
    lo, hi = (0, T) if p0 < T else (T + (p0 - T) // le * le, T + (p0 - T) // le * le + le)
    seg = ''.join(m.vocab.itos[x] if x != PAD else '\0' for x in ids[lo:hi]).split('\0')[0]
    return p0, seg, lo, None if p0 < T else (p0 - T) // le


def classify(want, got, d, want_slot, off='cells', split_same=False):
    span, p0, seg, lo, slot = d
    if not span:
        return off
    q = p0 - lo
    rx = pp.NUM_RE if slot is None else ENT_NUM
    toks = [(t.start(), t.end(), t.group()) for t in rx.finditer(seg)]
    at = [t for t in toks if t[1] - 1 == q]
    if not at:
        return 'mid_number'
    is_res = slot is not None and ' = ' in seg and at[0][0] > seg.index(' = ')
    if slot != want_slot or not is_res:
        if is_res or not split_same:
            return 'other_result' if is_res else 'other_number'
        return 'same_entry_operand' if slot == want_slot else 'prompt_number' if slot is None else 'other_number'
    if len(got) < len(want) and want.endswith(got):
        return 'cut_short'
    if len(got) > len(want) and got.endswith(want):
        return 'too_long'
    return 'other'


def events(m, rs, bs, tags, L, base, acc=None, keep_misses=False, AL=()):
    """Copy events of the oracle draws named by tags, added into acc (raw counts) -> acc."""
    acc = acc or dict(operand={}, answer={}, miss_kinds={}, answer_miss_kinds={}, misses=[], answer_misses=[], path_changed=0)
    for tag in tags:
        for r, calls, ans, info, ai in run_rows(m, rs, bs, lambda r, t, c, _tag=tag: rand_digits(random.Random(f"{r['id']}|{t}{_tag}"), 1, 9)):
            c0, a0 = base[r['id']]
            if [c[:2] for c in calls[:len(c0)]] != [c[:2] for c in c0]:
                acc['path_changed'] += 1
                continue
            pn = {x.group() for x in pp.NUM_RE.finditer(r['prompt'])}
            for j in range(len(c0)):
                earlier = [c0[k][4] for k in range(j)]
                for side in (0, 1):
                    x = c0[j][2 + side]
                    if x in earlier and unamb(x, earlier, pn):
                        k = max(k for k in range(j) if c0[k][4] == x)
                        want, got = calls[k][4], calls[j][2 + side]
                        d = acc['operand'].setdefault(len(want), [0, 0])
                        d[0] += 1; d[1] += got == want
                        if got != want and j in info:      # every length's misses are classified; the list keeps length L's
                            kind = classify(want, got, info[j][side], calls[k][0] - 1)
                            kd = acc['miss_kinds'].setdefault(len(want), {})
                            kd[kind] = kd.get(kind, 0) + 1
                            if keep_misses and len(want) == L:
                                acc['misses'].append(dict(id=r['id'], tag=tag, call=j, side=side, want=want, got=got, kind=kind,
                                                          picked_slot=info[j][side][4], want_slot=calls[k][0] - 1, segment=info[j][side][2],
                                                          earlier=[c[4] for c in calls[:j]]))
            res = [c[4] for c in c0]
            ks = [k for k in range(len(c0)) if c0[k][4] == a0]
            if ks and is_hit(a0, r) and unamb(a0, res, pn):
                want = calls[ks[-1]][4]
                d = acc['answer'].setdefault(len(want), [0, 0])
                d[0] += 1; d[1] += ans == want
                if ans != want and ai is not None:
                    ws = calls[ks[-1]][0] - 1
                    kind = classify(want, ans, ai, ws, off='not_span', split_same=True)
                    kd = acc['answer_miss_kinds'].setdefault(len(want), {})
                    kd[kind] = kd.get(kind, 0) + 1
                    if keep_misses and len(want) in AL:
                        acc['answer_misses'].append(dict(id=r['id'], tag=tag, want=want, got=ans, kind=kind, span=ai[0], picked_slot=ai[4],
                                                         want_slot=ws, pos_in_segment=ai[1] - ai[3], segment=ai[2], results=[c[4] for c in calls]))
    return acc


def table(acc):
    pc = lambda c: {str(n): dict(n=v[0], exact=round(100 * v[1] / v[0], 2)) for n, v in sorted(c.items())}
    return dict(operand=pc(acc['operand']), answer=pc(acc['answer']), miss_kinds={str(n): v for n, v in sorted(acc['miss_kinds'].items())},
                answer_miss_kinds={str(n): v for n, v in sorted(acc['answer_miss_kinds'].items())}, path_changed=acc['path_changed'],
                **(dict(misses=acc['misses']) if acc['misses'] else {}), **(dict(answer_misses=acc['answer_misses']) if acc['answer_misses'] else {}))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ck', nargs='+', required=True)
    ap.add_argument('--big-data', required=True)
    ap.add_argument('--passes', type=int, default=2, help="write_copy_u's own passes to re-draw for the breakdown (its WC.json 'passes')")
    ap.add_argument('--length', type=int, default=8)
    ap.add_argument('--answer-lengths', type=int, nargs='*', default=[], help='answer cells whose misses are listed (Amendment 7)')
    ap.add_argument('--fresh-n', type=int, default=1000)
    ap.add_argument('--max-fresh', type=int, default=16)
    ap.add_argument('--batch', type=int, default=128)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    rs, out = rows_of(a.big_data), {}
    for ck in a.ck:
        t0 = time.time()
        m = load_model(ck, 'cpu')
        name = os.path.basename(os.path.dirname(ck))
        base = {r['id']: (calls, ans) for r, calls, ans, _, _ in run_rows(m, rs, a.batch)}
        own = table(events(m, rs, a.batch, [''] + [f'|{p}' for p in range(1, a.passes)], a.length, base, keep_misses=True, AL=a.answer_lengths))
        print(json.dumps(dict(ck=name, part='breakdown', cell=own['operand'].get(str(a.length)), kinds=own['miss_kinds'].get(str(a.length)),
                              answer={n: (own['answer'].get(str(n)), own['answer_miss_kinds'].get(str(n))) for n in a.answer_lengths},
                              secs=round(time.time() - t0))), flush=True)
        acc, p = None, 0
        while p < a.max_fresh:
            acc = events(m, rs, a.batch, [f'|fresh{p}'], a.length, base, acc)
            p += 1
            n = min([acc['operand'].get(a.length, [0])[0]] + [acc['answer'].get(x, [0])[0] for x in a.answer_lengths])
            print(json.dumps(dict(ck=name, part='fresh', passes=p, n=n, secs=round(time.time() - t0))), flush=True)
            if n >= a.fresh_n:
                break
        fresh = table(acc)
        out[name] = dict(checkpoint=ck, breakdown=own, fresh=dict(fresh, passes=p), secs=round(time.time() - t0))
        json.dump(dict(length=a.length, answer_lengths=a.answer_lengths, n_rows=len(rs), device='cpu fp32', results=out), open(a.out, 'w'), indent=1)
    return out


if __name__ == '__main__':
    main()
