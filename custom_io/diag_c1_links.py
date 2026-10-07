"""D0b (no-hard-coding plan, section 3.0; report only, no pass mark): where the text baseline with its calculator (C1') loses chain-5.
python3 -m custom_io.diag_c1_links --ckpt CK/tfsteps_s100/checkpoint.pt CK/tfsteps_s101/checkpoint.pt --big BIG_DATA [--out custom_io/results/d0/D0b_c1_links.json] [--relabel]
PlainTFSteps.generate returns only the final answer, so this re-generates the 1,000 chain-5 rows with lesion 'calc' (the same loop, CPU, fp32) and
keeps the written text and where the calculator filled in. Each wrong row gets the label of its FIRST wrong link against the row's gold steps:
  a  an operand's digits copied wrong (not any prompt number or earlier result, at most 1 digit from the gold operand)
  b  a wrong number chosen (another prompt number or an earlier result)
  c  a wrong operation (or a wrong number of operands in the step)
  d  a tool result copied wrong into a later step (the gold operand is an earlier result, the written one is not a known number)
  e  the final answer copied wrong (every step right)
  f  a step format the calculator did not fire on, with its own result wrong (or an operand that is not a number, or the answer written
     alone with no steps on a row whose target has steps)
  g  stopped early or ran too long
  h  a row whose training target is the answer alone (steps plus answer over 64 chars, plain_tf_steps.CAP)
  i  its own arithmetic wrong on a step the calculator never fires on (state_update arrows like '+5 -> 17', or a closing '2 + 13' with no '=')
  j  a wrong name (story_chain3 answers are names)
  x  none of these (printed in full)
Pooled over the seeds; (h)-(j) are reported apart and left out of the call: copying (a+d+e) >= half of the rest -> the copy path,
choosing (b+c) >= half -> the thinker's state, else mixed."""
import argparse, collections, json, os, re
import torch
from custom_io.data import BOS, EOS, N_SPECIAL, PAD, SEP, Dataset, collate, load_rows
from custom_io.evalx import CHAIN5, is_hit
from custom_io.models import load_model
from custom_io.models.plain_tf_steps import CAP, calc_fill, final_answer, target_text
from custom_io.models.progparse import NUM_RE

LABELS = dict(a='operand digits copied wrong', b='wrong number chosen', c='wrong operation', d='tool result copied wrong into a later step',
              e='final answer copied wrong', f='step format the calculator did not fire on', g='stopped early or ran too long',
              h='trained answer-only (steps + answer over 64 chars)', i='own arithmetic wrong on an arrow step (calculator never fires)',
              j='wrong name', x='none of these')
APART = 'hij'


@torch.no_grad()
def write(m, batch):
    """PlainTFSteps.generate(batch, 'calc') with the record kept -> [(text, [(char index, fill)], ended with EOS)] per row."""
    p, lens = batch['prompt_ids'], batch['prompt_mask'].sum(1)
    B, T = p.shape
    seq = p.new_full((B, T + 2 + m.max_new), PAD)
    seq[:, 0], seq[:, 1:1 + T] = BOS, p
    r = torch.arange(B, device=p.device)
    seq[r, 1 + lens] = SEP
    pl = m.place_seq(batch, seq.shape[1])
    txt, queue, done, fills = [''] * B, [[] for _ in range(B)], [False] * B, [[] for _ in range(B)]
    for t in range(m.max_new):
        n = int((2 + lens).max()) + t
        h = m.hidden_upto(seq, n, None, pl)[r, 1 + lens + t]
        nxt = m.logits(h).argmax(-1)
        forced = [(q.pop(0) if q and not d else None) for q, d in zip(queue, done)]
        if any(f is not None for f in forced):
            nxt = torch.tensor([f if f is not None else int(x) for f, x in zip(forced, nxt)], device=p.device)
        seq[r, 2 + lens + t] = nxt
        for i, x in enumerate(nxt.tolist()):
            if done[i]:
                continue
            if x == EOS:
                done[i] = True
            elif x >= N_SPECIAL:
                txt[i] += m.vocab.itos[x]
                if not queue[i] and forced[i] is None and (f := calc_fill(txt[i])):
                    queue[i] = m.vocab.encode(f)
                    fills[i].append((len(txt[i]), f))
        if all(done):
            break
    return [(s, f, d) for s, f, d in zip(txt, fills, done)]


_ARROW = re.compile(r'^([-+])\s*(\d+)\s*->\s*(-?\d+)$')
_CMP = re.compile(r'^compare\s+(\S+)\s+(\S+)$')
_EQ = re.compile(r'^(?:([A-Za-z])\s*=\s*)?(.+?)\s*=\s*(\S+)$')


def parse(step):
    """'a op b = r' / 'v = a op b = r' / 'a+b-c=r' -> ('eq', [operands], [ops], result); '+5 -> 17' -> ('arrow', [5], ['+'], '17');
    'compare x y' -> ('compare', [x, y], [], None); anything else -> ('?', [], [], None). Operands stay strings."""
    s = step.strip()
    if (mt := _ARROW.match(s)):
        return 'arrow', [mt[2]], [mt[1]], mt[3]
    if (mt := _CMP.match(s)):
        return 'compare', [mt[1], mt[2]], [], None
    if (mt := _EQ.match(s)):
        toks, out = re.findall(r'\d+|[A-Za-z_]+|[-+*/]', mt[2]), []
        for k, tk in enumerate(toks):           # a '-' at the start or after an operator is a sign
            if out and out[-1] == '-' and tk.isdigit() and (len(out) == 1 or out[-2] in '+-*/'):
                out[-1] = '-' + tk
            else:
                out.append(tk)
        return 'eq', out[0::2], out[1::2], mt[3]
    return '?', [], [], None


def lev(a, b):
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, d[0] = d[0], i
        for j, cb in enumerate(b, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (ca != cb))
    return d[-1]


def is_int(s):
    return re.fullmatch(r'-?\d+', s or '') is not None


def label(row, text, fills, eos, cap=CAP):
    """-> (label, detail) for the row's first wrong link (the row is known to be wrong)."""
    if target_text(row, cap) == row['answer']:
        return 'h', 'training target is the answer alone'
    gold = [parse(s) for s in row['steps']]
    body, has_hash = (text.rsplit('#', 1)[0], True) if '#' in text else (text, False)
    pieces, pos, spans = body.split(';'), 0, []
    for pc in pieces:
        spans.append((pos, pos + len(pc)))
        pos += len(pc) + 1
    wsteps = [(pc.strip(), sp) for pc, sp in zip(pieces, spans) if pc.strip()]
    known = {int(x) for x in NUM_RE.findall(row['prompt'])}
    results = []                                # gold results of the steps before (all right so far)
    for k, (gk, (ws, sp)) in enumerate(zip(gold, wsteps)):
        wk = parse(ws)
        fired = any(sp[0] <= at <= sp[1] + 1 for at, _ in fills)
        if wk[0] != gk[0]:
            if wk[0] == '?':
                alone = is_int(ws) and len(wsteps) == 1
                return 'f', f'step {k + 1}: wrote {ws!r} for {row["steps"][k]!r}' + (' (the answer alone: no steps, so the calculator never fired)' if alone else '')
            return 'c', f'step {k + 1}: wrote {ws!r} for {row["steps"][k]!r}'
        seq_w = [x for pair in zip(wk[1], wk[2] + ['']) for x in pair][:-1] if wk[2] or wk[1] else []
        seq_g = [x for pair in zip(gk[1], gk[2] + ['']) for x in pair][:-1] if gk[2] or gk[1] else []
        if gk[0] == 'arrow':
            seq_w, seq_g = [wk[2][0], wk[1][0]], [gk[2][0], gk[1][0]]
        for j in range(max(len(seq_w), len(seq_g))):
            w, g = (seq_w[j] if j < len(seq_w) else None), (seq_g[j] if j < len(seq_g) else None)
            if w == g:
                continue
            where = f'step {k + 1}: wrote {ws!r} for {row["steps"][k]!r}'
            if w is None or g is None or (w in '+-*/') != (g in '+-*/') or w in '+-*/':
                return 'c', where
            if not is_int(w):
                return 'f', where + ' (operand not a number)'
            wi, gi = int(w), int(g)
            if wi in known or wi in results:
                return 'b', where + f' ({w} is {"an earlier result" if wi in results else "a prompt number"})'
            if gi in results:
                return 'd', where + f' (gold {g} is an earlier result; {w} is {lev(w, g)} digit edits away)'
            if lev(w.lstrip('-'), g.lstrip('-')) <= 1:
                return 'a', where
            return 'x', where + f' (operand {w} not in the prompt, {lev(w, g)} edits from gold {g})'
        if wk[3] != gk[3]:
            where = f'step {k + 1}: wrote {ws!r} for {row["steps"][k]!r}'
            if gk[0] == 'arrow':
                return 'i', where
            if not fired:
                return 'f', where + ' (calculator did not fire)'
            return 'x', where + ' (calculator fired, result still differs)'
        if is_int(gk[3]):
            results.append(int(gk[3]))
    if len(wsteps) != len(gold) or not has_hash or not eos:
        return 'g', f'{len(wsteps)} steps written for {len(gold)}' + ('' if has_hash else ', no #') + ('' if eos else ', no end')
    last = row['steps'][-1]
    if gold[-1][0] == '?' and re.search(r'\d\s*[-+*/x]\s*\d', last):       # e.g. state_update's closing '2 + 13': no '=', the model adds it up
        return 'i', f'last step {last!r} has no "=", so the calculator never fires; answer {final_answer(text)!r} for {row["answer"]!r}'
    return ('e' if is_int(row['answer']) else 'j'), f'answer {final_answer(text)!r} for {row["answer"]!r}'


def run(ckpt, rows, bs):
    m = load_model(ckpt, 'cpu')
    ds = Dataset(rows, m.vocab, strict=False)
    order = sorted(range(len(rows)), key=lambda i: len(rows[i]['prompt']))
    out = {}
    for s in range(0, len(order), bs):
        idx = order[s:s + bs]
        for i, w in zip(idx, write(m, collate([ds[i] for i in idx]))):
            out[i] = w
    wrong, fam = [], collections.Counter()
    for i, r in enumerate(rows):
        text, fills, eos = out[i]
        if is_hit(final_answer(text), r):
            continue
        lb, det = label(r, text, fills, eos, m.cap)
        fam[r['family']] += 1
        wrong.append(dict(id=r['id'], family=r['family'], label=lb, detail=det, prompt=r['prompt'], gold=target_text(r, m.cap), gold_steps=r['steps'],
                          written=text, fills=fills, ended=eos))
    return dict(ckpt=ckpt, cap=m.cap, n=len(rows), exact=100 * (len(rows) - len(wrong)) / len(rows), wrong_by_family=dict(fam),
                labels=dict(collections.Counter(w['label'] for w in wrong)), wrong=wrong)


def relabel(path, big):
    """Re-apply label() to the rows a saved run wrote (no generation): the written text, fills and end flag are kept per row."""
    res = json.load(open(path))
    gold = {r['id']: r for r in load_rows(os.path.join(big, 'dev', 'in_dist.jsonl')) if r['family'] in CHAIN5}
    per = collections.defaultdict(collections.Counter)
    for w in res['rows']:
        w['label'], w['detail'] = label(gold[w['id']], w['written'], [tuple(f) for f in w['fills']], w['ended'])
        per[w['seed_ckpt']][w['label']] += 1
    for sd in res['seeds']:
        sd['labels'] = dict(per[sd['ckpt']])
    pooled = collections.Counter(w['label'] for w in res['rows'])
    res.update(pooled=dict(pooled), call=call(pooled))
    return res


def call(counts):
    rest = {k: v for k, v in counts.items() if k not in APART}
    n = sum(rest.values())
    copy, choose = sum(rest.get(k, 0) for k in 'ade'), sum(rest.get(k, 0) for k in 'bc')
    verdict = ('copy path' if n and 2 * copy >= n else "thinker's state" if n and 2 * choose >= n else 'mixed')
    return dict(rows_in_call=n, copying_ade=copy, choosing_bc=choose, apart_hij={k: counts.get(k, 0) for k in APART}, verdict=verdict)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', nargs='+')
    ap.add_argument('--big', required=True, help='the big build (200 per cell dev/in_dist.jsonl)')
    ap.add_argument('--batch', type=int, default=100)
    ap.add_argument('--out', default='custom_io/results/d0/D0b_c1_links.json')
    ap.add_argument('--relabel', action='store_true', help='re-label the rows already in --out (no generation)')
    a = ap.parse_args(argv)
    if a.relabel:
        res = relabel(a.out, a.big)
        json.dump(res, open(a.out, 'w'), indent=1)
        print(json.dumps(dict(seeds=[sd['labels'] for sd in res['seeds']], pooled=res['pooled'], call=res['call'])))
        return res
    torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))
    rows = [r for r in load_rows(os.path.join(a.big, 'dev', 'in_dist.jsonl')) if r['family'] in CHAIN5]
    per = [run(c, rows, a.batch) for c in a.ckpt]
    pooled = collections.Counter()
    for p in per:
        pooled.update(p['labels'])
    res = dict(what='D0b: first wrong link of every chain-5 row the text baseline gets wrong with its calculator on (C1\')', labels=LABELS,
               seeds=[dict(ckpt=p['ckpt'], exact=p['exact'], n=p['n'], wrong_by_family=p['wrong_by_family'], labels=p['labels']) for p in per],
               pooled=dict(pooled), call=call(pooled), rows=[dict(seed_ckpt=p['ckpt'], **w) for p in per for w in p['wrong']])
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    json.dump(res, open(a.out, 'w'), indent=1)
    for p in per:
        print(json.dumps(dict(ckpt=p['ckpt'], exact=p['exact'], labels=p['labels'], wrong_by_family=p['wrong_by_family'])))
    print(json.dumps(dict(pooled=dict(pooled), call=res['call'])))
    return res


if __name__ == '__main__':
    main()
