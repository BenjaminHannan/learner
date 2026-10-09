"""Fill-in-the-blank rows from human-written web text (8A spec section 4). Rows are made by a script, never by a model.

A web document is cut into chunks of whole words (<= CHUNK_MAX chars, so the prompt fits data.MAX_PROMPT). In each chunk ONE word of
WORD_MIN..WORD_MAX letters, drawn uniformly, is replaced by BLANK; the row's answer is that word. Deterministic: the draw depends only on
(seed, document id, chunk index), so a bigger slice that starts with the same documents gives the same rows first (nested pools), and
every arm of a seed sees identical rows.

A row is a normal skills-format row (id, prompt, answer, accepted, family='cloze', level, stage, variant, steps=[]), so B2 and
plain_tf_steps train on it unchanged. The plain LLM arm (models/plain_lm.py) rebuilds the unblanked chunk with `unblank(row)` and trains
a next-character loss on it.

Sizes are the spec's (addendum E): prompt <= 280 chars including the blank, blanked word 3..12 letters. They are longer than today's caps
(prompt 208, answer 8), so the models' caps are sized from the data (custom_io/g8a/caps.py), never by dropping or cutting rows.
Rows whose answer word also appears elsewhere in the chunk are KEPT (B2's WORD pointer can copy it); their share is reported.

  python3 -m custom_io.g8a.cloze --slice slice.jsonl --seed 400 --out rows.jsonl [--max-pieces N] [--stats stats.json]
"""
import argparse, functools, hashlib, json, re, sys, unicodedata

BLANK = '____'
CHUNK_MAX, CHUNK_MIN = 279, 60      # prompt <= 280 chars including the blank (blank is 4 chars, the shortest blanked word 3)
WORD_MIN, WORD_MAX = 3, 12
_CLEAN = {ord('’'): "'", ord('‘'): "'", ord('“'): '"', ord('”'): '"', ord('–'): '-', ord('—'): '-', ord('…'): '...', 0xa0: ' '}
_WORD_T = r"(?<![A-Za-z0-9'_-])[A-Za-z]{%d,%d}(?![A-Za-z0-9'_-])"
_ALL_WORDS = re.compile(r"[A-Za-z']+")


def norm_text(text):
    """NFC, curly quotes / dashes / no-break space -> ASCII, '_' -> space (so BLANK is unique in a chunk), whitespace collapsed."""
    t = unicodedata.normalize('NFC', text).translate(_CLEAN).replace('_', ' ')
    return ' '.join(t.split())


def chunks(text, chunk_max=CHUNK_MAX, chunk_min=CHUNK_MIN):
    """Greedy chunks of whole words, each <= chunk_max chars; a final chunk shorter than chunk_min is dropped."""
    out, cur, n = [], [], 0
    for w in text.split(' '):
        if len(w) > chunk_max:
            if cur:
                out.append(' '.join(cur))
            cur, n = [], 0
            continue
        if cur and n + 1 + len(w) > chunk_max:
            out.append(' '.join(cur))
            cur, n = [], 0
        cur.append(w)
        n += len(w) + (1 if n else 0)
    if cur:
        out.append(' '.join(cur))
    return [c for c in out if len(c) >= chunk_min]


def pick(seed, doc_id, idx, n):
    """Uniform draw in range(n), a pure function of (seed, doc id, chunk index)."""
    h = hashlib.blake2b(f'{seed}|{doc_id}|{idx}'.encode(), digest_size=8).digest()
    return int.from_bytes(h, 'little') % n


def row_id(seed, doc_id, idx):
    return 'cz-%d-%s' % (seed, hashlib.blake2b(f'{doc_id}|{idx}'.encode(), digest_size=7).hexdigest())


@functools.lru_cache(maxsize=None)
def _word_re(wmin, wmax):
    return re.compile(_WORD_T % (wmin, wmax))


def make_row(chunk, seed, doc_id, idx, wmin=WORD_MIN, wmax=WORD_MAX):
    """-> (row, copyable) or None when the chunk is not plain ASCII or has no candidate word."""
    if not chunk.isascii():
        return None
    cand = list(_word_re(wmin, wmax).finditer(chunk))
    if not cand:
        return None
    m = cand[pick(seed, doc_id, idx, len(cand))]
    ans = m.group()
    prompt = chunk[:m.start()] + BLANK + chunk[m.end():]
    rest = _ALL_WORDS.findall(chunk[:m.start()] + ' ' + chunk[m.end():])
    copyable = ans.lower() in {w.lower() for w in rest}
    return dict(id=row_id(seed, doc_id, idx), prompt=prompt, answer=ans, accepted=[ans], family='cloze', level=0, stage=0,
                variant='cloze', steps=[]), copyable


def unblank(row):
    """The full chunk of a cloze row (BLANK replaced by the answer)."""
    assert row['prompt'].count(BLANK) == 1, row['id']
    return row['prompt'].replace(BLANK, row['answer'])


def is_cloze(row):
    return row.get('family') == 'cloze'


class Stats:
    def __init__(self):
        self.d = dict(docs=0, docs_with_rows=0, chunks=0, rows=0, skipped_non_ascii=0, skipped_no_word=0, copyable=0, chars=0, pieces=0.0)

    def report(self):
        d = dict(self.d)
        d['copyable_share'] = d['copyable'] / max(d['rows'], 1)
        d['pieces_per_row'] = d['pieces'] / max(d['rows'], 1)
        return d


def cloze_rows(docs, seed, max_pieces=None, stats=None, chunk_max=CHUNK_MAX, wmin=WORD_MIN, wmax=WORD_MAX, long_share=0.0, long_max=1999):
    """Yield cloze rows from an iterable of {'id', 'text', 'token_count'} in file order, stopping before max_pieces (GPT-2 word pieces, the
    document's own token_count spread over its chunks by characters). Every row carries '_np' = its share of the pieces (stripped when written).
    B3 part C: long_share = the share of documents (a pure draw per seed and document id, no RNG state) cut into chunks of up to long_max letters (prompt <= 2,000
    with the blank) instead of chunk_max; 0.0 (default) = exactly the rows above, byte for byte."""
    st = stats or Stats()
    for doc in docs:
        st.d['docs'] += 1
        text = norm_text(doc['text'])
        if not text:
            continue
        per_char = doc['token_count'] / max(len(text), 1)
        got = False
        long_doc = long_share > 0 and pick(seed, doc['id'], 'long', 10 ** 6) < long_share * 10 ** 6
        for i, ch in enumerate(chunks(text, long_max if long_doc else chunk_max)):
            st.d['chunks'] += 1
            if not ch.isascii():
                st.d['skipped_non_ascii'] += 1
                continue
            r = make_row(ch, seed, doc['id'], i, wmin, wmax)
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
            got = True
            row['_np'] = np_
            yield row
        st.d['docs_with_rows'] += got


def read_slice(path):
    with open(path) as f:
        for line in f:
            yield json.loads(line)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--slice', required=True, help='web slice jsonl (id, text, token_count) from data_pool/web_slice.py')
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--max-pieces', type=float)
    ap.add_argument('--stats')
    a = ap.parse_args(argv)
    st = Stats()
    with open(a.out, 'w') as f:
        for r in cloze_rows(read_slice(a.slice), a.seed, a.max_pieces, st):
            r.pop('_np')
            f.write(json.dumps(r) + '\n')
    rep = st.report()
    if a.stats:
        json.dump(rep, open(a.stats, 'w'), indent=1)
    print(json.dumps(rep))


if __name__ == '__main__':
    main()
