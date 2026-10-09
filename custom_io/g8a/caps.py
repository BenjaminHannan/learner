"""Caps sized from the data (8A spec addendum E: "don't cut off long answers").

Every fixed size in the models is a cap: prompt length, answer length, numbers per prompt, words per prompt, program steps (B2's workspace),
the plain arms' steps+answer target. compute(rows) reads them off the pool and dev rows; apply(caps) sets the module globals BEFORE any data or
model is built (train.py --caps FILE does this); report(rows, caps) counts the rows each cap would touch (target 0 everywhere).

A cap is never set below today's value, so on data that fits today's caps nothing changes (the 3M B2 stays 3,302,481 trained parameters):
    max_prompt   data.MAX_PROMPT, reader position table, plain_tf.MAX_PROMPT/MAX_LEN/pos table      today 208
    max_ans      data.MAX_ANS (answer chars before EOS)                                              today 8
    n_num        progparse/ledger N_NUM (prompt numbers on the workspace)                            today 16
    w_max        progparse/ledger/english W_MAX (words per prompt)                                   today 64
    n_res        progparse/ledger N_RES (program steps; B2 needs n_loops >= n_res + 1)               today 7
    n_reg        ledger N_REG/GEN_MAX = max_ans + 1 register slots; reader N_PLACE = n_reg + 1       today 9 / 16
    plain_target plain_tf_steps.CAP (longest steps+answer target), MAX_NEW, MAX_POS                   today 64
The only behaviour change a bigger N_PLACE brings: place ids of letters 15+ from a word's right end clamp at N_PLACE-2 instead of 14.

  python3 -m custom_io.g8a.caps compute POOL_DIR [DEV_DIR ...] --out caps.json     # reads POOL/train.jsonl and every dev/*.jsonl
  python3 -m custom_io.g8a.caps report caps.json POOL_DIR [DEV_DIR ...]            # rows touched per cap, today's caps and these
"""
import argparse, glob, json, os, sys

TODAY = dict(max_prompt=208, max_ans=8, n_num=16, w_max=64, n_res=7, n_reg=9, plain_target=64)


def _rows(paths):
    for p in paths:
        if os.path.isdir(p):
            fs = sorted(glob.glob(os.path.join(p, '*.jsonl')) + glob.glob(os.path.join(p, '**', '*.jsonl'), recursive=True))
            fs = list(dict.fromkeys(fs))
        else:
            fs = [p]
        for f in fs:
            with open(f, encoding='utf-8') as fh:
                for line in fh:
                    if line.strip():
                        yield json.loads(line)


def measure(r, progs=True):
    """One row's sizes."""
    from custom_io.data import word_spans
    from custom_io.models import progparse as pp
    from custom_io.models.plain_tf_steps import STEP_FAMILIES
    tgt = r['answer']
    if r.get('family') in STEP_FAMILIES and r.get('steps'):
        tgt = '; '.join(r['steps']) + ' # ' + r['answer']
    n_prog = 0
    if progs and r.get('family') != 'cloze':
        p, _ = pp.program_for(r)
        n_prog = len(p['prog']) if p is not None else 0
    return dict(max_prompt=len(r['prompt']), max_ans=len(r['answer']), n_num=len(pp.NUM_RE.findall(r['prompt'])),
                w_max=len(word_spans(r['prompt'])), n_res=n_prog, n_reg=len(r['answer']) + 1, plain_target=len(tgt))


def compute(paths, progs=True):
    """-> caps dict: max over every row of every size, never below today's. `rows` = how many rows were read."""
    mx, n = dict(TODAY), 0
    for r in _rows(paths):
        n += 1
        for k, v in measure(r, progs).items():
            if v > mx[k]:
                mx[k] = v
    mx['n_reg'] = max(mx['n_reg'], mx['max_ans'] + 1)
    mx['rows'] = n
    return mx


def compute_rows(rows, progs=True):
    """compute() on rows already in memory."""
    mx = dict(TODAY)
    for r in rows:
        for k, v in measure(r, progs).items():
            mx[k] = max(mx[k], v)
    mx['n_reg'] = max(mx['n_reg'], mx['max_ans'] + 1)
    mx['rows'] = len(rows)
    return mx


def compute_global(own72, web_slice, dev_paths, max_ans, seed=400, say=print, cloze_long=None):
    """Caps for the whole ladder (addendum F d): the longest case in the LARGEST pool = all of own72 (the 30M rung's own rows contain the smaller rungs')
    plus every cloze row of the 30M web slice plus the dev splits. Every rung then uses these same caps, so N_RES, n_loops and the tables are identical."""
    from custom_io.g8a import cloze as Z, pool as P
    mx, n = dict(TODAY), 0
    def take(r, progs):
        for k, v in measure(r, progs).items():
            if v > mx[k]:
                mx[k] = v
    st = {s_: P._newstat() for s_ in ('skills', 'english', 'teach')}
    for line, _, _ in P.own72_iter(own72, 30, max_ans, set(), st):
        take(json.loads(line), True)
        n += 1
        if n % 200000 == 0:
            say('own rows measured', n, {k: mx[k] for k in TODAY})
    own_n = n
    for r in P.web_rows(web_slice, seed, None, Z.Stats(), cloze_long):
        take(r, False)
        n += 1
    for r in _rows(dev_paths):
        take(r, True)
        n += 1
    mx['n_reg'] = max(mx['n_reg'], mx['max_ans'] + 1)
    mx.update(rows=n, own_rows=own_n, source='largest pool: own72 (rung <= 30) + rung30 web slice (%s, seed %d) + dev' % ('long-chunk cloze rows, data_pool/cloze_long.py' if cloze_long else 'cloze rows', seed))
    return mx


def report(caps, paths, progs=True):
    """Rows over each cap (today's and the given one) and the longest value seen. Target 0 under the given caps."""
    over_today, over, seen, n = {k: 0 for k in TODAY}, {k: 0 for k in TODAY}, {k: 0 for k in TODAY}, 0
    for r in _rows(paths):
        n += 1
        for k, v in measure(r, progs).items():
            seen[k] = max(seen[k], v)
            over_today[k] += v > TODAY[k]
            over[k] += v > caps[k]
    return dict(rows=n, longest=seen, today=TODAY, caps={k: caps[k] for k in TODAY}, rows_over_today=over_today, rows_over_caps=over)


def apply(caps):
    """Patch the module globals. Call before building any Dataset / model, and before anything imports these names by value."""
    import importlib
    from custom_io import data
    from custom_io.models import progparse as pp, reader, plain_tf, plain_tf_steps
    caps = {k: max(int(caps.get(k, v)), v) for k, v in TODAY.items()}
    caps['n_reg'] = max(caps['n_reg'], caps['max_ans'] + 1)
    data.MAX_PROMPT = caps['max_prompt']
    data.set_max_ans(caps['max_ans'])
    reader.MAX_PROMPT = caps['max_prompt']
    reader.N_PLACE = max(16, caps['n_reg'] + 1)
    reader.PLACE_NONE = reader.N_PLACE - 1
    plain_tf.MAX_PROMPT = caps['max_prompt']
    plain_tf.MAX_LEN = max(224, 2 + caps['max_prompt'] + caps['max_ans'] + 1)
    plain_tf.N_PLACE, plain_tf.PLACE_NONE = reader.N_PLACE, reader.PLACE_NONE
    plain_tf_steps.CAP = caps['plain_target']
    plain_tf_steps.MAX_NEW = caps['plain_target'] + 3 + caps['max_ans'] + 1
    plain_tf_steps.MAX_POS = max(288, 2 + caps['max_prompt'] + plain_tf_steps.MAX_NEW + 1)
    pp.N_NUM, pp.N_RES, pp.W_MAX = caps['n_num'], caps['n_res'], caps['w_max']
    pp.R0 = pp.N_NUM + len(pp.CONSTS)
    pp.M = pp.R0 + pp.N_RES
    for name in ('custom_io.models.ledger', 'custom_io.models.tool', 'custom_io.english', 'custom_io.models.plain_lm'):
        # import before patching: ledger / tool / plain_lm are imported lazily (models.build), AFTER train.py's apply(), so `sys.modules.get` used to skip
        # them and the Ledger kept N_REG 9 / GEN_MAX 8 (9 register tokens, GEN targets cut to 8 letters; found 10-08, g8b/README.md)
        m = importlib.import_module(name)
        for k, v in dict(N_NUM=pp.N_NUM, N_RES=pp.N_RES, W_MAX=pp.W_MAX, R0=pp.R0, M=pp.M, MAX_PROMPT=caps['max_prompt'], CAP=caps['plain_target']).items():
            if hasattr(m, k):
                setattr(m, k, v)
        if hasattr(m, 'N_REG'):
            m.N_REG, m.GEN_MAX = caps['n_reg'], caps['n_reg'] - 1
    return caps


def n_loops_needed(caps):
    return max(8, caps['n_res'] + 1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['compute', 'report'])
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    if a.cmd == 'compute':
        caps = compute(a.paths)
        print(json.dumps(caps))
        if a.out:
            json.dump(caps, open(a.out, 'w'))
    else:
        caps = json.load(open(a.paths[0]))
        print(json.dumps(report(caps, a.paths[1:]), indent=1))


if __name__ == '__main__':
    main()
