"""Cost check of test TK at 2,000 letters (TOKENS-EXPERIMENT-2026-10-09.md sec. 4; report-only, run on the PC in minutes, no data pool needed).

Memory-only builds of the 3M G-B2 (EGE: eg_embed), TK (tok_think) and TKN (tok_think, reader_layers 0, tkn_mlp) under caps_g.json with max_prompt raised to
--letters (2000) and w_max / n_num scaled by the same factor for every arm (these builds are NOT the trained models and skip the size band). Rows: 2,000-letter
cloze rows made by joining text chunks (a plain text file, or the unblanked prompts of a cloze jsonl; default a seeded synthetic prose for smoke tests), with
fresh ids. ONE training step (bf16 autocast on cuda, AdamW) of --batch (8) rows per arm. Per arm it prints: thinker key positions per row (valid letters for G-B2,
valid token spots for TK / TKN, workspace excluded), total peak GPU memory (torch.cuda.max_memory_allocated, Gemma and the model included), the activation peak
(peak reset after Gemma has loaded: peak minus what was resident then) and the step time. --steps 2 adds a second, warm step to the time.
  python -m custom_io.g8a.tok_cost [--text FILE | --cloze ROWS.jsonl] [--letters 2000] [--batch 8] [--arms EGE TK TKN] [--out cost.json]
CPU smoke (stub Gemma, tiny model): python -m custom_io.g8a.tok_cost --stub --letters 300 --small
caps.apply must reach the lazily imported ledger module (8b fix in caps.py): main() asserts it did (ledger.N_NUM / W_MAX / N_REG, reader.MAX_PROMPT, the position table)."""
import argparse, gc, json, os, random, time
import torch
from custom_io.data import CharVocab, Dataset, collate, to_device
from custom_io.g8a import caps as CP
from custom_io.g8a import cloze as Z
from custom_io.g8a import configs as C
from custom_io.models import build

SMALL = dict(d=48, n_heads=2, reader_layers=1, blocks=1, mlp=2.0)
WORDS = ('the of and to in is that it was for on are as with his they at be this from have or by one had not but what all were when we there can an your which '
         'their said if do will each about how up out them then she many some so these would other into has more her two like him see time could no make than first '
         'been its who now people my made over did down only way find use may water long little very after words called just where most know').split()


def synth_text(n_chars, seed=0):
    rng, out, n = random.Random(seed), [], 0
    while n < n_chars:
        w = rng.choice(WORDS)
        out.append(w)
        n += len(w) + 1
    return ' '.join(out)


def make_rows(text, letters, n_rows, seed=0):
    """n_rows cloze rows of 0.9..1.0 x `letters` letters (prompt incl. the blank <= letters), fresh ids, from consecutive chunks of `text`."""
    rows = []
    for i, ch in enumerate(Z.chunks(Z.norm_text(text), chunk_max=letters - 4, chunk_min=int(0.9 * letters))):
        r = Z.make_row(ch, seed, f'tokcost{os.getpid()}', i)
        if r is not None:
            rows.append(r[0])
        if len(rows) == n_rows:
            return rows
    raise SystemExit(f'text too short: {len(rows)} rows of {letters} letters, need {n_rows}')


def arm_cfgs(small, loops):
    """{arm: ledger cfg}. TKN's mlp is solved under caps_g.json (the real trained TKN), before the long caps are applied."""
    ex = dict(eg_embed=True, **loops)
    if small:
        base = dict(dict(SMALL, n_loops=8, copy=True), **ex)
        return {'EGE': base, 'TK': dict(base, tok_think=True), 'TKN': dict(base, tok_think=True, reader_layers=0)}
    mlp, tkn, _, _ = C.tkn_mlp('3M', dict(ex, tok_think=True))
    return {'EGE': C.b2_cfg('3M', ex), 'TK': C.b2_cfg('3M', dict(ex, tok_think=True)), 'TKN': C.b2_cfg('3M', dict(tkn, **loops))}


def run_arm(name, cfg, rows, vocab, dev, steps, stub, say=print):
    cuda = dev.type == 'cuda'
    gc.collect()
    if cuda:
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    torch.manual_seed(0)
    model = build('ledger', vocab, **cfg).to(dev)
    if stub:
        from custom_io.tests.test_tok_think import StubEG
        model._eg = [StubEG()]
    elif hasattr(model.eg(), 'load'):
        model.eg().load(dev)                # Gemma is resident before the activation peak is measured
    batch = to_device(collate([Dataset(rows, vocab)[i] for i in range(len(rows))]), dev)
    if cuda:
        torch.cuda.synchronize()
        resident = torch.cuda.memory_allocated()
        torch.cuda.reset_peak_memory_stats()
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, betas=(0.9, 0.95), weight_decay=0.1)
    model.train()
    times = []
    for _ in range(steps):
        t = time.perf_counter()
        with (torch.autocast('cuda', dtype=torch.bfloat16) if cuda else torch.autocast('cpu', enabled=False)):
            out = model.loss(batch)
        loss = out[0] if isinstance(out, tuple) else out
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step(); opt.zero_grad(set_to_none=True)
        if cuda:
            torch.cuda.synchronize()
        times.append(time.perf_counter() - t)
    n_rows = len(rows)
    letters = sum(len(r['prompt']) for r in rows) / n_rows
    keys = model._tk_spots / (n_rows * steps) if hasattr(model, '_tk_spots') else letters
    res = dict(arm=name, trained_params=model.n_params(), thinker_keys_per_row=round(keys, 1), letters_per_row=round(letters, 1), loss=round(float(loss.detach()), 4),
               step_s=round(times[-1], 3), step_s_all=[round(x, 3) for x in times])
    if cuda:
        res.update(total_peak_mib=round(torch.cuda.max_memory_allocated() / 2 ** 20), resident_after_gemma_mib=round(resident / 2 ** 20),
                   activation_peak_mib=round((torch.cuda.max_memory_allocated() - resident) / 2 ** 20))
    say(json.dumps(res))
    del model, opt, batch, out, loss
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--text', help='plain text file (default: seeded synthetic prose)')
    ap.add_argument('--cloze', help='jsonl of cloze rows: their unblanked prompts are joined into the text')
    ap.add_argument('--letters', type=int, default=2000)
    ap.add_argument('--batch', type=int, default=8)
    ap.add_argument('--steps', type=int, default=1)
    ap.add_argument('--arms', nargs='+', default=['EGE', 'TK', 'TKN'], choices=['EGE', 'TK', 'TKN'])
    ap.add_argument('--caps', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'caps_g.json'))
    ap.add_argument('--stub', action='store_true', help='CPU smoke: a stub stands in for EmbeddingGemma (tokens = words and digits)')
    ap.add_argument('--small', action='store_true', help='CPU smoke: tiny model (d 48)')
    ap.add_argument('--device', default='auto')
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    dev = torch.device('cuda' if a.device == 'auto' and torch.cuda.is_available() else 'cpu' if a.device == 'auto' else a.device)
    caps = json.load(open(a.caps))
    caps1 = CP.apply(caps)                                          # the trained shapes first: TKN's mlp is solved under them
    loops = dict(n_loops=CP.n_loops_needed(caps1)) if CP.n_loops_needed(caps1) > 8 else {}
    cfgs = arm_cfgs(a.small, loops)
    f = a.letters / caps1['max_prompt']
    big = dict(caps, max_prompt=a.letters, w_max=int(caps1['w_max'] * f), n_num=int(caps1['n_num'] * f))      # same for every arm
    caps2 = CP.apply(big)
    from custom_io import data
    from custom_io.models import ledger as L, progparse as pp, reader
    assert (L.N_NUM, L.W_MAX, L.N_REG, L.M) == (big['n_num'], big['w_max'], caps2['n_reg'], pp.M) and reader.MAX_PROMPT == data.MAX_PROMPT == a.letters, 'caps did not reach the ledger'
    print(f'caps: max_prompt {a.letters}, w_max {big["w_max"]}, n_num {big["n_num"]} (x{f:.2f}); n_loops {cfgs["EGE"]["n_loops"]}; device {dev}; stub {a.stub}', flush=True)
    text = Z.norm_text(' '.join(Z.unblank(json.loads(l)) for l in open(a.cloze))) if a.cloze else open(a.text).read() if a.text else synth_text(int(a.batch * a.letters * 1.3) + 1000)
    rows = make_rows(text, a.letters, a.batch)
    vocab = CharVocab.build([])
    res = [run_arm(n, cfgs[n], rows, vocab, dev, a.steps, a.stub) for n in a.arms]
    base = res[0]
    print('\narm    keys/row  letters/row  total peak MiB  activation peak MiB  step s    (vs %s)' % base['arm'])
    for r in res:
        print(f"{r['arm']:<5} {r['thinker_keys_per_row']:>9} {r['letters_per_row']:>12} {r.get('total_peak_mib', 'n/a'):>14} {r.get('activation_peak_mib', 'n/a'):>19} {r['step_s']:>7}    "
              f"keys x{r['thinker_keys_per_row'] / base['thinker_keys_per_row']:.2f}" + (f"  peak x{r['total_peak_mib'] / base['total_peak_mib']:.2f}  act x{r['activation_peak_mib'] / base['activation_peak_mib']:.2f}" if 'total_peak_mib' in r else ''))
    if a.out:
        json.dump(dict(letters=a.letters, batch=a.batch, caps=big, cfgs=cfgs, arms=res), open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
