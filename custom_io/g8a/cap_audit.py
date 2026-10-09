"""No-truncation audit of the build (scorecard row 6; roadmap sec. 4 "target 0"; 8a addenda E, G).

  python3 -m custom_io.g8a.cap_audit CAPS.json [--model ledger|tool] [--rows PATH_OR_DIR ...] [--sample N] [--out audit.json]

1. MODEL SIDE. Applies CAPS exactly as train.py --caps does (g8a.caps.apply), builds the model (default Ledger, B2's shape, no Gemma) and checks that
   EVERY fixed size in the code equals the cap: module constants (data, reader, plain_tf, plain_tf_steps, plain_lm, progparse, ledger, tool, english) and
   the size of every table built from them (reader position table = max_prompt, place table = n_reg + 1, ledger/tool register and workspace tables).
2. DATA SIDE (--rows). Runs every row through the model's OWN cutting code (Ledger.spans / Ledger.gold / progparse.row_targets / Dataset / plain target) and
   prints the cap-hit counters of custom_io/capcount.py. Target: all 0. Then the same counts by simple measurement (g8a.caps.report) as a cross-check.
Exit code 1 when any check fails or any counter is above 0.
"""
import argparse, json, sys


def model_side(caps, model_name='ledger'):
    from custom_io.g8a import caps as CP
    c = CP.apply(caps)
    from custom_io import data
    from custom_io.data import CharVocab
    from custom_io.models import build, plain_tf, plain_tf_steps, progparse as pp, reader
    from custom_io.g8a import configs as C
    import importlib
    problems, seen = [], {}

    def chk(name, got, want):
        seen[name] = got
        if got != want:
            problems.append(f'{name} = {got}, cap says {want}')
    chk('data.MAX_PROMPT', data.MAX_PROMPT, c['max_prompt'])
    chk('data.MAX_ANS', data.MAX_ANS, c['max_ans'])
    chk('reader.MAX_PROMPT', reader.MAX_PROMPT, c['max_prompt'])
    chk('reader.N_PLACE', reader.N_PLACE, max(16, c['n_reg'] + 1))
    chk('plain_tf.MAX_PROMPT', plain_tf.MAX_PROMPT, c['max_prompt'])
    chk('plain_tf_steps.CAP', plain_tf_steps.CAP, c['plain_target'])
    chk('progparse.N_NUM', pp.N_NUM, c['n_num'])
    chk('progparse.N_RES', pp.N_RES, c['n_res'])
    chk('progparse.W_MAX', pp.W_MAX, c['w_max'])
    for name in ('custom_io.models.ledger', 'custom_io.models.tool', 'custom_io.models.plain_lm', 'custom_io.english'):
        m = importlib.import_module(name)
        for k, want in dict(N_NUM=c['n_num'], N_RES=c['n_res'], W_MAX=c['w_max'], N_REG=c['n_reg'], GEN_MAX=c['n_reg'] - 1, MAX_PROMPT=c['max_prompt'],
                            CAP=c['plain_target']).items():
            if hasattr(m, k):
                chk(f'{name.split(".")[-1]}.{k}', getattr(m, k), want)
    from custom_io.models import tool_h1, b3
    chk('tool_h1.CAP (H1 round cap, fixed)', tool_h1.CAP, 32)
    chk('b3.CAP (H1 round cap, fixed)', b3.CAP, 32)
    from custom_io.models import ledger as L
    chk('ledger.M (workspace slots)', L.M, c['n_num'] + len(pp.CONSTS) + c['n_res'])
    from custom_io.data import CharVocab
    vocab = CharVocab(list(' abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,?!-+*/=:;#()\'"%$<>_'))
    cfg = C.b2_cfg('3M')
    cfg = dict(cfg, n_loops=max(cfg.get('n_loops', 8), CP.n_loops_needed(c)))
    m = build(model_name, vocab, **cfg)
    chk('reader.pos table rows', m.reader.pos.num_embeddings, c['max_prompt'])
    chk('reader.place table rows', m.reader.place.num_embeddings, max(16, c['n_reg'] + 1))
    chk('n_loops >= n_res + 1', m.n_loops >= c['n_res'] + 1, True)
    if model_name == 'tool':
        from custom_io.models import tool as T
        chk('tool.CELLS >= 21 (longest int64 string 20 chars + EOS)', T.CELLS >= 21, True)
        chk('place table covers the calculator cells', m.reader.place.num_embeddings >= T.CELLS, True)
        # tool.py keeps register-count constants (9) inside its code; the cap-hit audit must read them, not the cap file
        import inspect
        src = inspect.getsource(importlib.import_module('custom_io.models.tool'))
        for pat in ('place.weight[:9]', 'np.full((B, 9)'):
            if pat in src:
                problems.append(f'tool.py still hard-codes 9 registers ({pat}): answers are cut or the batch cannot hold {c["n_reg"]} targets')
    return dict(caps=c, seen=seen, problems=problems, model=m)


def data_side(m, caps, paths, sample=None, say=print):
    import numpy as np, torch
    from custom_io import capcount, data
    from custom_io.g8a import caps as CP
    from custom_io.models import plain_tf_steps as pts
    capcount.reset()
    n = 0
    buf = []
    def flush():
        if not buf:
            return
        if hasattr(m, 'gold'):
            m.gold(buf, torch.device('cpu'))
        for r in buf:
            m.spans(r['prompt'])
            if len(r['prompt']) > data.MAX_PROMPT:
                capcount.hit('prompt_over_max')
            if len(r['answer']) > data.MAX_ANS:
                capcount.hit('answer_over_max')
            if len(pts.target_text(r)) > pts.CAP + 12:
                capcount.hit('plain_target_over')
        buf.clear()
    for r in CP._rows(paths):
        buf.append(r)
        n += 1
        if len(buf) == 512:
            flush()
        if n % 200000 == 0:
            say('rows', n, capcount.snapshot())
        if sample and n >= sample:
            break
    flush()
    return dict(rows=n, hits=capcount.snapshot(), report=CP.report(caps, paths, progs=True) if not sample else None)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('caps')
    ap.add_argument('--model', default='ledger', choices=['ledger', 'tool'])
    ap.add_argument('--rows', nargs='*', default=[])
    ap.add_argument('--sample', type=int)
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    caps = json.load(open(a.caps))
    ms = model_side(caps, a.model)
    out = dict(model=a.model, caps=ms['caps'], model_side_checked=len(ms['seen']), model_side_problems=ms['problems'])
    print(json.dumps(dict(model_side_checked=len(ms['seen']), problems=ms['problems']), indent=1))
    ok = not ms['problems']
    if a.rows:
        ds = data_side(ms['model'], ms['caps'], a.rows, a.sample)
        out['data_side'] = ds
        print(json.dumps(dict(rows=ds['rows'], cap_hits=ds['hits']), indent=1))
        ok = ok and ds['hits']['total'] == 0
    out['ok'] = ok
    if a.out:
        json.dump(out, open(a.out, 'w'), indent=1, default=str)
    print('AUDIT', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
