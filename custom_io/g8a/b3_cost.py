"""Cost check of B3 at 2,000 letters (B3-GROUP1-BUILD-2026-10-09.md sec. 4; report-only, CPU here). A separate file from tok_cost.py.

Tiny-width B3_G1 (d 48, 1 block; every B3 switch on: eg_embed with a stub Gemma, any_round, gap_p 0.25) built under caps_g.json with max_prompt 280, and again with
max_prompt --letters (2000) and w_max / n_num scaled by the same factor (the numbers the 2,000-letter pool would give, about 1,485 and 650). ONE training step each
at --batch (2) on rows of that many letters: a prose chunk (seeded synthetic text, or --text FILE) followed by a two-step arithmetic question, so the calculator is
used. Per config it prints the thinker's key positions per row (valid letters, number slots = the padded workspace width and the filled ones, tape = TAPE entries x
the longest entry in the step) and the step time. The real fit check (memory on the 16 GB PC at 3M and 100M) is the big-run thread's.
  python -m custom_io.g8a.b3_cost [--letters 2000] [--batch 2] [--steps 1] [--text FILE] [--out cost.json]"""
import argparse, json, os, time
import torch
from custom_io.data import CharVocab, Dataset, collate
from custom_io.g8a import caps as CP
from custom_io.g8a.tok_cost import synth_text
from custom_io.models import build

SMALL = dict(d=48, n_heads=2, reader_layers=1, blocks=1, mlp=2.0)
SW = dict(label='settled', span_copy=True, span_idx=True, span_end=True, ans_drill=0.25, eg_embed=True, any_round=True, gap_p=0.25)


def make_rows(text, letters, n, seed=0):
    rows = []
    for i in range(n):
        a, b, c = 120 + 17 * i + seed, 340 + 29 * i, 7 + i
        q = f' Tom has {a} apples and buys {b} more, then gives {c} away. How many apples now?'
        body = text[i * letters:(i + 1) * letters - len(q)]
        body = body[:body.rfind(' ')] if len(body) == letters - len(q) else body
        rows.append(dict(id=f'cost{i}', family='chain_story2', prompt=(body + q)[-letters:] if len(body + q) > letters else body + q, answer=str(a + b - c),
                         steps=[f'{a} + {b} = {a + b}', f'{a + b} - {c} = {a + b - c}']))
    return rows


def one(label, caps, letters, batch, steps, text):
    from custom_io.tests.test_b3 import StubEG
    c = CP.apply(dict(caps))
    from custom_io.models import ledger as L
    cfg = dict(SMALL, n_loops=max(8, c['n_res'] + 1), **SW)
    torch.manual_seed(0)
    V = CharVocab.build([])
    m = build('b3', V, **cfg)
    m._eg = [StubEG()]
    rows = make_rows(text, letters, batch)
    b = collate([Dataset(rows, V, strict=False)[i] for i in range(batch)])
    T = b['prompt_ids'].shape[1]
    ns, ne, nv, ws, we = m.tokenize(b)
    slots = int(((ne - ns) > 0).sum(-1).float().mean())
    opt = torch.optim.AdamW(m.parameters(), lr=1e-3)
    m.train()
    times = []
    torch.manual_seed(123)          # the same rounds draw K in both configs, so the step times compare
    for _ in range(steps):
        t = time.perf_counter()
        loss, aux = m.loss(b)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
        opt.step(); opt.zero_grad(set_to_none=True)
        times.append(time.perf_counter() - t)
    n_tape = m.tape * max(len(x) for r in rows for x in m.row_gold(r)[2] if x)
    res = dict(config=label, max_prompt=c['max_prompt'], n_num=c['n_num'], w_max=c['w_max'], letters_per_row=T, number_slots_padded=L.N_NUM,
               number_slots_filled=slots, tape_positions=n_tape, thinker_keys_per_row=T + L.N_NUM + n_tape, rounds_in_step=int(aux['rounds']), step_s=round(times[-1], 3),
               loss=round(float(loss.detach()), 3), trained_params=m.n_params())
    print(json.dumps(res), flush=True)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--letters', type=int, default=2000)
    ap.add_argument('--batch', type=int, default=2)
    ap.add_argument('--steps', type=int, default=1)
    ap.add_argument('--text')
    ap.add_argument('--caps', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'caps_g.json'))
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    caps = json.load(open(a.caps))
    text = open(a.text).read() if a.text else synth_text(a.batch * a.letters + 4000)
    short = one('280 letters', caps, caps['max_prompt'], a.batch, a.steps, text)
    f = a.letters / caps['max_prompt']
    long = one(f'{a.letters} letters', dict(caps, max_prompt=a.letters, w_max=int(caps['w_max'] * f), n_num=int(caps['n_num'] * f)), a.letters, a.batch, a.steps, text)
    print('\nconfig         letters  number slots (padded/filled)  tape  thinker keys/row  step s')
    for r in (short, long):
        print(f"{r['config']:<13} {r['letters_per_row']:>8} {r['number_slots_padded']:>14}/{r['number_slots_filled']:<10} {r['tape_positions']:>6} {r['thinker_keys_per_row']:>14} {r['step_s']:>9}")
    print(f"ratio: keys x{long['thinker_keys_per_row'] / short['thinker_keys_per_row']:.2f}, step time x{long['step_s'] / max(short['step_s'], 1e-9):.2f}")
    if a.out:
        json.dump(dict(batch=a.batch, short=short, long=long), open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
