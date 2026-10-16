"""Answer-word scorer (MARKS-LT2 Addendum 11 section 4). Free CPU; never run on a rented box.

For every row of a rung file (dev / newwords / hard) and each candidate answer word ("true", "false", "unknown"): the log-probability of that
full answer string through the SAME output path the model answers with (Tool.talk / Tool.answers), following Tool.loss's terms:
  mode head      lmode  [3]      0 = span/NUM (numbers; not used by these rows), 1 = WORD (copy a prompt word), 2 = GEN (write the chars)
  WORD mode      lword  [W_MAX]  the pointer over the prompt's words; P(word) = sum of softmax(lword) over the words equal to the candidate
  GEN mode       gen_copy p [9, V]: the 9 registers are parallel (no autoregression), so P(string) = prod of p[k, char_k] over the reversed
                 characters plus EOS, exactly the product Tool.loss's lgen takes the log of
  log P(word) = logsumexp( log P(mode=WORD) + log P_word(candidate) , log P(mode=GEN) + log P_gen(candidate) )
Mode 0 (span) is not given a term: its pointer reads numbers; its probability mass is reported per row (`p_mode0`) so a row whose greedy
answer came from mode 0 is visible. The greedy prediction is Tool.talk's own (model.answers on the argmax of every head), not recomputed.

  python -m logic_transfer.answer_words score --ckpt CKPT --rows DEV.jsonl [--rows ...] --out OUT.jsonl
"""
import argparse
import json
import math
import sys

import torch

OPTIONS = ('true', 'false', 'unknown')


def load(path, device='cpu'):
    from custom_io.data import CharVocab
    from custom_io.models import build
    ck = torch.load(path, map_location=device, weights_only=True)
    m = build(ck['name'], CharVocab(ck['chars']), **ck['cfg'])
    m.load_state_dict(ck['model'])
    return m.to(device).eval(), ck


@torch.no_grad()
def score_rows(model, rows, batch_size=64, options=OPTIONS):
    """-> one record per row, in the order of `rows`: id, gold, greedy pred + mode, logp {word: log P}, p_mode {0,1,2}, argmax word."""
    from custom_io.data import EOS, Dataset, collate, to_device, word_spans
    from custom_io.models.tool import GEN_MAX, N_RES, W_MAX
    dev = next(model.parameters()).device
    ds = Dataset(rows, model.vocab, strict=False)
    order = sorted(range(len(rows)), key=lambda i: len(rows[i]['prompt']))
    out = [None] * len(rows)
    cand = {w: model.vocab.encode(w[:GEN_MAX][::-1]) + [EOS] for w in options}
    for s in range(0, len(order), batch_size):
        idx = order[s:s + batch_size]
        batch = to_device(collate([ds[i] for i in idx]), dev)
        st = model.state(batch)
        R, Xt, idt, vis, lmode, lword = st[:6]
        X, xm = model.read(batch, talker=True)
        Xc, mc, idc = torch.cat([X, Xt.to(X.dtype)], 1), torch.cat([xm, vis.bool()], 1), torch.cat([batch['prompt_ids'], idt.long()], 1)
        p, _ = model.gen_copy(R, Xc, mc, idc, False)                       # [B, 9, V]
        # the greedy answer exactly as Tool.talk computes it
        span = None
        if model.span_copy:
            T, le = X.shape[1], Xt.shape[1] // N_RES
            span = model.span_read(model.ptr(st[6], model.span_keys(Xc, T, le, mc), mc), idc, mc, T, le)
        preds, modes = model.answers(p.argmax(-1).tolist(), lmode.argmax(-1).tolist(), lword.argmax(-1).tolist(), batch['rows'], span=span)
        lm = lmode.float().log_softmax(-1)                                  # [B, 3]
        lw = lword.float().log_softmax(-1)                                  # [B, W_MAX]
        lp = p.clamp_min(1e-30).log()                                       # [B, 9, V]
        for b, i in enumerate(idx):
            r = rows[i]
            sp = word_spans(r['prompt'])[:W_MAX]
            words = [r['prompt'][a:e].lower() for a, e in sp]
            rec = {}
            for w in options:
                ws = [k for k, x in enumerate(words) if x == w]
                lword_w = torch.logsumexp(lw[b, ws], 0) if ws else torch.tensor(-math.inf)
                ids = cand[w]
                lgen_w = sum(lp[b, k, c] for k, c in enumerate(ids))
                terms = [lm[b, 1] + lword_w, lm[b, 2] + lgen_w]
                rec[w] = dict(total=float(torch.logsumexp(torch.stack(terms), 0)), word=float(lword_w), gen=float(lgen_w))
            best = max(options, key=lambda w: rec[w]['total'])
            out[i] = dict(id=r['id'], gold=r['answer'], pred=preds[b], mode=int(modes[b]), logp={w: rec[w]['total'] for w in options},
                          logp_word_path={w: rec[w]['word'] for w in options}, logp_gen_path={w: rec[w]['gen'] for w in options},
                          p_mode=[float(x) for x in lm[b].exp()], argmax=best)
    return out


def agreement(recs, options=OPTIONS):
    """Addendum 11 section 4 check: the scorer's argmax vs the greedy prediction (case/space-normalised). -> counts."""
    norm = lambda s: ' '.join(str(s).strip().lower().split())
    n = len(recs)
    inset = [r for r in recs if norm(r['pred']) in options]
    same_all = sum(norm(r['pred']) == r['argmax'] for r in recs)
    same_in = sum(norm(r['pred']) == r['argmax'] for r in inset)
    return dict(n=n, agree_all=same_all, agree_all_pct=round(100 * same_all / max(n, 1), 2), pred_in_options=len(inset),
                agree_in_options=same_in, agree_in_options_pct=round(100 * same_in / max(len(inset), 1), 2),
                pred_out_of_options=n - len(inset), greedy_mode0=sum(r['mode'] == 0 for r in recs))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('score')
    s.add_argument('--ckpt', required=True)
    s.add_argument('--rows', action='append', required=True, help='NAME=path.jsonl (repeatable)')
    s.add_argument('--out', required=True)
    s.add_argument('--threads', type=int, default=4)
    s.add_argument('--batch', type=int, default=64)
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    from custom_io.data import load_rows
    m, ck = load(a.ckpt)
    with open(a.out, 'w') as f:
        summ = {}
        for spec in a.rows:
            name, path = spec.split('=', 1)
            rows = load_rows(path, keep=None)
            recs = score_rows(m, rows, a.batch)
            for r in recs:
                f.write(json.dumps(dict(r, set=name)) + '\n')
            summ[name] = agreement(recs)
            summ[name]['greedy_exact'] = sum(r['pred'].strip().lower() == r['gold'].strip().lower() for r in recs)
        print(json.dumps(summ))


if __name__ == '__main__':
    main()
