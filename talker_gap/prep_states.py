#!/usr/bin/env python3
"""Cache frozen EmbeddingGemma-2 token states for the small talker check (prep only; nothing is trained here).

  PYTHONPATH=/Users/ben-hannan/tf519 /Users/ben-hannan/ucv4/venv/bin/python prep_states.py --selftest
  PYTHONPATH=/Users/ben-hannan/tf519 /Users/ben-hannan/ucv4/venv/bin/python prep_states.py   # all splits -> common.CACHE

Per split (dev, practised, train) it writes into common.CACHE:
  rows_<s>.json     make_row dicts, in array order
  states_<s>.npy    float16 [N, T_MAX, 768], zero-padded: per-token last_hidden_state of the kept tokens
  tok_len_<s>.npy   int16 [N]: kept tokens stored, min(kept, T_MAX)
  tok_off_<s>.npy   int16 [N, T_MAX, 2]: char (start, end) of each kept token inside row['prompt']; (0,0) padding
  word_tok_<s>.npy  int16 [N, W_MAX, 2]: first/last stored-token index overlapping each of the first W_MAX passage words;
                    (-1,-1) for padding words or words whose characters are all past the token cap
meta.json: per split n, n_truncated, seconds, sha256 of each file. A split is skipped when its meta entry and files exist.

Token rule: the model sees exactly PREFIX + prompt with the tokenizer's <bos>/<eos>, as eg_ref.FrozenEG.encode does.
Kept tokens: non-empty offsets that end after the prefix. The token that straddles the prefix edge (its leading space belongs
to PREFIX) keeps its text, with its start clamped to 0 (same clamp as eg_ref.FrozenEG.align).
"""
import hashlib
import json
import os
import sys
import tempfile
import time

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'diag'))
import common  # noqa: E402
from eg_ref import FrozenEG  # noqa: E402

H = 768
BATCH = 64
DEVICE = torch.device('cpu')
PFX = len(common.PREFIX)
SPLITS = ('dev', 'practised', 'train')   # smallest first, so finished splits land early
STEMS = ('states', 'tok_len', 'tok_off', 'word_tok')


def load_eg():
    torch.set_num_threads(8)
    return FrozenEG(common.EG2).load(DEVICE)


def kept_tokens(eg, prompt):
    """-> (all token ids incl. prefix/bos/eos, positions of kept tokens in that list, kept (start, end) relative to prompt)."""
    enc = eg.tok(common.PREFIX + prompt, return_offsets_mapping=True)
    keep, offs = [], []
    for j, (s, e) in enumerate(enc['offset_mapping']):
        if e <= s:                       # <bos>/<eos> carry (0, 0)
            continue
        if e - PFX <= 0:                 # prefix-only token
            continue
        keep.append(j)
        offs.append((max(s - PFX, 0), e - PFX))
    return list(enc['input_ids']), keep, offs


@torch.no_grad()
def embed_batch(eg, pre):
    """pre: [(ids, keep, offs)] from kept_tokens. Runs the model as FrozenEG.encode does (right padding + attention mask).
    -> [(fp32 states [k,768] of the first T_MAX kept tokens, offsets int64 [k,2], n_kept_total)]."""
    L = max(len(ids) for ids, _, _ in pre)
    ids_t = torch.full((len(pre), L), eg.tok.pad_token_id, dtype=torch.long)
    am = torch.zeros((len(pre), L), dtype=torch.long)
    for b, (ids, _, _) in enumerate(pre):
        ids_t[b, :len(ids)] = torch.tensor(ids, dtype=torch.long)
        am[b, :len(ids)] = 1
    Ht = eg.m(input_ids=ids_t, attention_mask=am).last_hidden_state.float()
    out = []
    for b, (_, keep, offs) in enumerate(pre):
        k = min(len(keep), common.T_MAX)
        st = Ht[b, keep[:k]].clone().numpy()
        out.append((st, np.asarray(offs[:k], np.int64).reshape(-1, 2), len(keep)))
    return out


def iter_embed(eg, rows):
    """Yields (row index, fp32 states, offsets, n_kept). Batches of BATCH rows sorted by token length."""
    pre = [kept_tokens(eg, r['prompt']) for r in rows]
    order = sorted(range(len(rows)), key=lambda i: len(pre[i][0]))
    for s in range(0, len(order), BATCH):
        idx = order[s:s + BATCH]
        for i, (st, off, nk) in zip(idx, embed_batch(eg, [pre[j] for j in idx])):
            yield i, st, off, nk


def word_table(passage, offs):
    """-> int16 [W_MAX, 2]: first/last stored-token index whose characters overlap each of the first W_MAX passage words."""
    out = np.full((common.W_MAX, 2), -1, np.int16)
    for w, (ws, we) in enumerate(common.word_spans(passage)[:common.W_MAX]):
        hit = np.nonzero((offs[:, 0] < we) & (offs[:, 1] > ws))[0]
        if hit.size:
            out[w] = (hit[0], hit[-1])
    return out


def sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 22), b''):
            h.update(chunk)
    return h.hexdigest()


def write_split(eg, name, rows, outdir):
    """Embeds rows, writes the five files for split `name` into outdir, then records the split in outdir/meta.json."""
    t0 = time.time()
    N = len(rows)
    if max(len(r['prompt']) for r in rows) >= 32768:
        raise ValueError('prompt too long for int16 offsets')

    def p(stem):
        return os.path.join(outdir, f'{stem}_{name}.npy')

    states = np.lib.format.open_memmap(p('states'), mode='w+', dtype=np.float16, shape=(N, common.T_MAX, H))
    tok_len = np.zeros(N, np.int16)
    tok_off = np.zeros((N, common.T_MAX, 2), np.int16)
    word_tok = np.full((N, common.W_MAX, 2), -1, np.int16)
    n_trunc = done = 0
    for i, st, off, nk in iter_embed(eg, rows):
        k = len(st)
        states[i, :k] = st.astype(np.float16)
        tok_len[i] = k
        tok_off[i, :k] = off
        word_tok[i] = word_table(rows[i]['passage'], off)
        n_trunc += nk > common.T_MAX
        done += 1
        if done % 2000 == 0:
            print(f'  {name}: {done}/{N} rows, {time.time() - t0:.0f}s', flush=True)
    states.flush()
    del states
    np.save(p('tok_len'), tok_len)
    np.save(p('tok_off'), tok_off)
    np.save(p('word_tok'), word_tok)
    rows_path = os.path.join(outdir, f'rows_{name}.json')
    with open(rows_path, 'w') as f:
        json.dump(rows, f)
    files = [p('states'), p('tok_len'), p('tok_off'), p('word_tok'), rows_path]
    entry = dict(n=N, n_truncated=int(n_trunc), tok_len_mean=round(float(tok_len.mean()), 2), tok_len_max=int(tok_len.max()),
                 seconds=round(time.time() - t0, 1), sha256={os.path.basename(f): sha_file(f) for f in files})
    meta_path = os.path.join(outdir, 'meta.json')
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    meta.setdefault('splits', {})[name] = entry
    meta.update(T_MAX=common.T_MAX, W_MAX=common.W_MAX, batch=BATCH, prefix=common.PREFIX, model=eg.path)
    tmp = meta_path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(meta, f, indent=1)
    os.replace(tmp, meta_path)
    return entry


def selftest():
    eg = load_eg()
    sp = common.build_splits()
    rows = [common.make_row(r) for r in common.sample_rows(sp['dev'], common.N_DEV, 'dev')[:40]]
    tmp = tempfile.mkdtemp(prefix='prep_states_selftest_')
    write_split(eg, 'selftest', rows, tmp)
    rows_back = json.load(open(os.path.join(tmp, 'rows_selftest.json')))
    assert rows_back == rows, 'rows json differs'
    states = np.load(os.path.join(tmp, 'states_selftest.npy'))
    tok_len = np.load(os.path.join(tmp, 'tok_len_selftest.npy'))
    tok_off = np.load(os.path.join(tmp, 'tok_off_selftest.npy'))
    word_tok = np.load(os.path.join(tmp, 'word_tok_selftest.npy'))
    N = len(rows)

    # (a) offsets inside the prompt; kept tokens cover every non-space character (untruncated rows)
    n_tok = n_cov = n_trunc = 0
    for i, r in enumerate(rows):
        prompt = r['prompt']
        k = int(tok_len[i])
        assert 0 < k <= common.T_MAX
        off = tok_off[i, :k].astype(int)
        assert ((off[:, 0] >= 0) & (off[:, 1] > off[:, 0]) & (off[:, 1] <= len(prompt))).all(), (i, off)
        assert (tok_off[i, k:] == 0).all() and (states[i, k:] == 0).all(), i
        n_tok += k
        if len(kept_tokens(eg, prompt)[1]) > common.T_MAX:
            n_trunc += 1
            continue
        covered = np.zeros(len(prompt), bool)
        for s, e in off:
            covered[s:e] = True
        missing = [j for j, c in enumerate(prompt) if not c.isspace() and not covered[j]]
        assert not missing, (i, missing[:5])
        n_cov += 1
    print(f'(a) offsets: {N}/{N} rows, {n_tok} kept tokens, all inside their prompt; non-space chars covered in '
          f'{n_cov}/{n_cov} untruncated rows ({n_trunc} truncated rows skipped); padding zero OK')

    # (b) batched (padded, fp32) vs one row at a time (no padding, fp32); stored float16 vs fp32 for information
    batched = {i: st for i, st, _, _ in iter_embed(eg, rows)}
    lens = [len(kept_tokens(eg, r['prompt'])[0]) for r in rows]
    worst = worst16 = 0.0
    for i in range(8):
        ids, keep, offs = kept_tokens(eg, rows[i]['prompt'])
        (st1, _, _), = embed_batch(eg, [(ids, keep, offs)])
        assert len(st1) == len(batched[i]), i
        worst = max(worst, float(np.abs(st1 - batched[i]).max()))
        worst16 = max(worst16, float(np.abs(st1 - states[i, :len(st1)].astype(np.float32)).max()))
    assert worst < 1e-3, worst
    print(f'(b) 8 rows one-at-a-time vs padded batch (40 rows, padded to {max(lens)} tokens, shortest {min(lens)}): '
          f'max abs diff fp32 {worst:.2e} < 1e-3 OK; stored float16 vs fp32 single {worst16:.2e} (cast rounding only)')

    # (c) word_tok vs an independent char->token map, all 40 rows; row 0 first 5 words printed by hand
    ids0, keep0, _ = kept_tokens(eg, rows[0]['prompt'])
    for i, r in enumerate(rows):
        prompt, k = r['prompt'], int(tok_len[i])
        off = tok_off[i, :k].astype(int)
        c2t = np.full(len(prompt), -1)
        for t, (s, e) in enumerate(off):
            c2t[s:e] = t
        wsp = common.word_spans(r['passage'])
        for w in range(common.W_MAX):
            f, l = (int(x) for x in word_tok[i, w])
            if w >= len(wsp):
                assert (f, l) == (-1, -1), (i, w)
                continue
            s, e = wsp[w]
            seen = c2t[s:e][c2t[s:e] >= 0]
            want = (-1, -1) if seen.size == 0 else (int(seen.min()), int(seen.max()))
            assert (f, l) == want, (i, w, (f, l), want)
    parts = []
    for w, (s, e) in enumerate(common.word_spans(rows[0]['passage'])[:5]):
        f, l = (int(x) for x in word_tok[0, w])
        toks = [eg.tok.convert_ids_to_tokens(ids0[keep0[t]]) for t in range(f, l + 1)]
        parts.append(f"'{rows[0]['passage'][s:e]}'[{s}:{e}]->tok {f}-{l} {toks}")
    print('(c) word_tok matches independent char map for 40 rows x all words; row 0 first 5 words: ' + ' | '.join(parts))
    print(f'selftest dir: {tmp}')
    print('prep_states selftest OK')


def main():
    os.makedirs(common.CACHE, exist_ok=True)
    meta_path = os.path.join(common.CACHE, 'meta.json')
    done = json.load(open(meta_path)).get('splits', {}) if os.path.exists(meta_path) else {}

    def finished(s):
        return s in done and all(os.path.exists(os.path.join(common.CACHE, f'{st}_{s}.npy')) for st in STEMS) \
            and os.path.exists(os.path.join(common.CACHE, f'rows_{s}.json'))

    todo = [s for s in SPLITS if not finished(s)]
    if not todo:
        print('all splits already done:', sorted(done), flush=True)
        return
    print('todo:', todo, flush=True)
    sp = common.build_splits()
    make = {
        'dev': lambda: [common.make_row(r) for r in common.sample_rows(sp['dev'], common.N_DEV, 'dev')],
        'practised': lambda: [common.make_row(r) for r in sp['practised']],
        'train': lambda: [common.make_row(r) for r in common.sample_rows(sp['train'], common.N_TRAIN, 'train')],
    }
    eg = load_eg()
    for name in todo:
        rows = make[name]()
        print(f'{name}: {len(rows)} rows', flush=True)
        entry = write_split(eg, name, rows, common.CACHE)
        print(name, json.dumps({k: v for k, v in entry.items() if k != 'sha256'}), flush=True)
    print('meta:', meta_path, flush=True)


if __name__ == '__main__':
    selftest() if '--selftest' in sys.argv else main()
