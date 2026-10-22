"""Long-chunk cloze rows (big-run REPLAN 10-09: inputs up to 2,000 letters). Drop-in for custom_io/g8a/cloze.cloze_rows.

Same row format, same blanked-word rule (3..12 letters, uniform draw), same nesting (a bigger slice that starts with the same documents gives the
same rows first). The only change: each chunk draws its own length ceiling from a fixed table of buckets, by a hash of (seed, document id, chunk
index), so the short/long mix is the same for every arm of a seed.

  bucket  ceiling (chars, incl. blank)   share of word pieces
  short   280                            80%   (today's rows)
  mid     700                            7%    (280-700 bucket of the G2 readout)
  long    1300                           7%    (700-1,300)
  xlong   2000                           6%    (1,300-2,000)

The shares are by pieces, not rows: a chunk is drawn with probability share / mean-chunk-chars, so long chunks do not take over the pool. The
mix is a default (suggested, untested at training time); it is one constant table below, and `--mix` takes another.

  python3 data_pool/cloze_long.py --slice slice.jsonl --seed 400 --out rows.jsonl [--max-pieces N] [--stats stats.json] [--cloze-src DIR]

--cloze-src is the directory holding custom_io/g8a/cloze.py (the 8a build branch); the module is imported from there, never copied.
"""
import argparse, hashlib, json, os, sys

MIX = [(280, 0.80), (700, 0.07), (1300, 0.07), (2000, 0.06)]       # (prompt ceiling incl. blank, share of pieces)
CHUNK_MIN = 60


def _load_cloze(src):
    if src:
        sys.path.insert(0, src)
    from custom_io.g8a import cloze as Z
    return Z


def bucket_probs(mix):
    """Per-chunk draw probabilities that give the wanted piece shares: p_i proportional to share_i / ceiling_i (chunks fill to ~their ceiling)."""
    w = [s / c for c, s in mix]
    t = sum(w)
    return [x / t for x in w]


def _u(seed, doc_id, idx):
    h = hashlib.blake2b(f'L|{seed}|{doc_id}|{idx}'.encode(), digest_size=8).digest()
    return int.from_bytes(h, 'little') / 2 ** 64


def pick_ceiling(seed, doc_id, idx, mix, probs):
    u, acc = _u(seed, doc_id, idx), 0.0
    for (c, _), p in zip(mix, probs):
        acc += p
        if u < acc:
            return c
    return mix[-1][0]


def chunks_mixed(text, seed, doc_id, mix, probs, chunk_min=CHUNK_MIN):
    """Greedy whole-word chunks; chunk k gets its own ceiling (prompt <= ceiling means chunk <= ceiling - 1). -> [(chunk, ceiling)]."""
    out, cur, n, k = [], [], 0, 0
    cm = pick_ceiling(seed, doc_id, k, mix, probs) - 1
    for w in text.split(' '):
        if len(w) > cm:
            if cur:
                out.append((' '.join(cur), cm + 1))
                k += 1
            cur, n = [], 0
            cm = pick_ceiling(seed, doc_id, k, mix, probs) - 1
            continue
        if cur and n + 1 + len(w) > cm:
            out.append((' '.join(cur), cm + 1))
            k += 1
            cur, n = [], 0
            cm = pick_ceiling(seed, doc_id, k, mix, probs) - 1
        cur.append(w)
        n += len(w) + (1 if n else 0)
    if cur:
        out.append((' '.join(cur), cm + 1))
    return [(c, m) for c, m in out if len(c) >= chunk_min]


def cloze_rows_mixed(Z, docs, seed, max_pieces=None, stats=None, mix=MIX, wmin=3, wmax=12):
    """Like Z.cloze_rows, with per-chunk length ceilings. Rows carry '_np' (pieces); stats = Z.Stats plus per-bucket counts in stats.extra."""
    probs = bucket_probs(mix)
    st = stats or Z.Stats()
    ex = st.extra = getattr(st, 'extra', {})
    for doc in docs:
        st.d['docs'] += 1
        text = Z.norm_text(doc['text'])
        if not text:
            continue
        per_char = doc['token_count'] / max(len(text), 1)
        got = False
        for i, (ch, ceil) in enumerate(chunks_mixed(text, seed, doc['id'], mix, probs)):
            st.d['chunks'] += 1
            if not ch.isascii():
                st.d['skipped_non_ascii'] += 1
                continue
            r = Z.make_row(ch, seed, doc['id'], i, wmin, wmax)
            if r is None:
                st.d['skipped_no_word'] += 1
                continue
            row, cp = r
            np_ = per_char * len(ch)
            if max_pieces is not None and st.d['pieces'] + np_ > max_pieces:
                return
            st.d['rows'] += 1
            st.d['copyable'] += cp
            st.d['chars'] += len(ch)
            st.d['pieces'] += np_
            b = ex.setdefault(str(ceil), dict(rows=0, pieces=0.0, chars=0, max_prompt=0))
            b['rows'] += 1
            b['pieces'] += np_
            b['chars'] += len(ch)
            b['max_prompt'] = max(b['max_prompt'], len(row['prompt']))
            got = True
            row['_np'] = np_
            yield row
        st.d['docs_with_rows'] += got


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--slice', required=True)
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--max-pieces', type=float)
    ap.add_argument('--stats')
    ap.add_argument('--cloze-src', help='dir with custom_io/g8a/cloze.py (8a build branch checkout)')
    ap.add_argument('--mix', help='JSON list of [ceiling, share] pairs; default MIX')
    a = ap.parse_args(argv)
    Z = _load_cloze(a.cloze_src)
    mix = [tuple(x) for x in json.loads(a.mix)] if a.mix else MIX
    st = Z.Stats()
    with open(a.out, 'w') as f:
        for r in cloze_rows_mixed(Z, Z.read_slice(a.slice), a.seed, a.max_pieces, st, mix):
            r.pop('_np')
            f.write(json.dumps(r) + '\n')
    rep = st.report()
    tot = rep['pieces'] or 1
    rep['mix'] = mix
    rep['buckets'] = {k: dict(v, piece_share=v['pieces'] / tot, mean_prompt=v['chars'] / max(v['rows'], 1)) for k, v in st.extra.items()}
    rep['max_prompt'] = max((v['max_prompt'] for v in st.extra.values()), default=0)
    if a.stats:
        json.dump(rep, open(a.stats, 'w'), indent=1)
    print(json.dumps(rep))


if __name__ == '__main__':
    main()
