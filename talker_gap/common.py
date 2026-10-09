"""Shared pieces for the small talker check (SPEC.md). Data prep and evaluation only; nothing here is part of any model.

Run `python common.py` for the self-test (rebuilds the v2 splits from TEACH and compares row counts with D4)."""
import gzip
import hashlib
import json
import os
import random
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DIAG = os.path.join(HERE, 'diag')
TEACH = '/Users/ben-hannan/Desktop/projects/b1-wt/b1_teach/results/teach_200k.jsonl.gz'
CACHE = '/Users/ben-hannan/talker_gap_cache'          # outside the repo
EG2 = '/Users/ben-hannan/eg2'
PY = '/Users/ben-hannan/ucv4/venv/bin/python'
TF519 = '/Users/ben-hannan/tf519'                      # PYTHONPATH for transformers 5.19 (EmbeddingGemma 2)
PREFIX = 'task: sentence similarity | query: '         # same prefix as custom_io/models/eg.py
N_TRAIN, N_DEV = 24000, 3000                           # fixed subsample sizes (SPEC.md)
SEED = 20261008
T_MAX, W_MAX = 64, 48                                  # max stored tokens / passage words per row


def en_norm(s):
    """custom_io/english.py en_norm: NFC, lower-case, curly quotes -> straight, collapse spaces, strip trailing [.!?,;:]"""
    s = unicodedata.normalize('NFC', s).lower().replace('’', "'").replace('‘', "'")
    s = re.sub(r'\s+', ' ', s).strip()
    return re.sub(r'[.!?,;:]+$', '', s).strip()


def norm_word(w):
    return re.sub(r"^[\"'(\[]+|[.,;:!?\"')\]]+$", '', en_norm(w))


def word_spans(text):
    """[(char_start, char_end)] of every whitespace-separated word."""
    return [(m.start(), m.end()) for m in re.finditer(r'\S+', text)]


def find_word_span(passage, accepted):
    """First accepted answer whose normalised words match a run of passage words -> (first_word, last_word); else None.
    Tries the answers in the given order, leftmost occurrence."""
    pw = [norm_word(passage[s:e]) for s, e in word_spans(passage)]
    for a in accepted:
        aw = [norm_word(w) for w in a.split()]
        aw = [w for w in aw if w]
        if not aw or len(aw) > len(pw):
            continue
        for i in range(len(pw) - len(aw) + 1):
            if pw[i:i + len(aw)] == aw:
                return i, i + len(aw) - 1
    return None


def is_hit(pred, accepted):
    gold = {en_norm(a) for a in accepted}
    return en_norm(pred) in gold


def hard_row(row):
    """Hard slice H (SPEC.md): short answer longer than 8 characters or with 2+ words."""
    if row['type'] != 'short_answer':
        return False
    a = row['answer']
    return len(a) > 8 or len(a.split()) >= 2


def _sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def iter_teach():
    with gzip.open(TEACH, 'rt') as f:
        for line in f:
            yield json.loads(line)


def build_splits():
    """-> dict split -> list of TEACH rows (dev | test | practised | train | dropped), following split_proposal_v2.json."""
    sp = json.load(open(os.path.join(DIAG, 'split_proposal_v2.json')))
    dev_k, test_k = set(sp['dev_kinds']), set(sp['test_kinds'])
    slice_ids = set(open(os.path.join(DIAG, 'practised_slice_ids.txt')).read().split())
    rows = list(iter_teach())
    dev_p = {r['source_text'] for r in rows if r['kind'] in dev_k}
    test_p = {r['source_text'] for r in rows if r['kind'] in test_k}
    out = {k: [] for k in ('dev', 'test', 'practised', 'train', 'dropped')}
    for r in rows:
        if r['kind'] in test_k:
            out['test'].append(r)
        elif r['kind'] in dev_k:
            (out['dropped'] if r['source_text'] in test_p else out['dev']).append(r)
        elif r['source_text'] in dev_p or r['source_text'] in test_p:
            out['dropped'].append(r)
        elif r['id'] in slice_ids:
            out['practised'].append(r)
        else:
            out['train'].append(r)
    return out


def make_row(r):
    """TEACH row -> the row the arms see. prompt = source_text + ' ' + question (as in custom_io/english.py qa_rows)."""
    prompt = r['source_text'] + ' ' + r['question']
    accepted = [r['canonical_answer']] + [a for a in r['accepted_answers'] if a != r['canonical_answer']]
    ws = word_spans(r['source_text'])
    answer = r['canonical_answer']
    gold = None
    if r['type'] == 'short_answer':
        gold = find_word_span(r['source_text'], accepted)
        if gold is not None:     # taught answer = the accepted string that appears in the passage
            pw = [r['source_text'][s:e] for s, e in ws][gold[0]:gold[1] + 1]
            for a in accepted:
                if en_norm(' '.join(norm_word(w) for w in pw)) == en_norm(' '.join(norm_word(w) for w in a.split())):
                    answer = a
                    break
    return dict(id=r['id'], kind=r['kind'], type=r['type'], passage=r['source_text'], question=r['question'], prompt=prompt,
                answer=answer, accepted=accepted, gold_words=list(gold) if gold else None, n_passage_words=len(ws))


def sample_rows(rows, n, tag):
    """Deterministic sample: order by sha256(tag + id), take the first n."""
    return sorted(rows, key=lambda r: _sha(tag + r['id']))[:n]


def paired_bootstrap(a, b, n=2000, seed=0):
    """a, b: per-row 0/1 hits on the same rows. -> (mean(a)-mean(b), lo, hi) with a 95% percentile interval, in points."""
    rng = random.Random(seed)
    n_rows = len(a)
    d = [x - y for x, y in zip(a, b)]
    stats = []
    for _ in range(n):
        s = 0
        for _ in range(n_rows):
            s += d[rng.randrange(n_rows)]
        stats.append(100.0 * s / n_rows)
    stats.sort()
    return 100.0 * sum(d) / n_rows, stats[int(0.025 * n)], stats[int(0.975 * n) - 1]


if __name__ == '__main__':
    sp = build_splits()
    counts = {k: len(v) for k, v in sp.items()}
    print(counts)
    want = {'train': 125544, 'practised': 2001, 'test': 18300}
    for k, v in want.items():
        assert counts[k] == v, (k, counts[k], v)
    assert counts['dev'] == 25127 - 130, counts['dev']
    rows = [make_row(r) for r in sample_rows(sp['dev'], 500, 'selftest')]
    span = sum(1 for r in rows if r['type'] == 'short_answer' and r['gold_words'])
    short = sum(1 for r in rows if r['type'] == 'short_answer')
    print('dev sample: short answers with a passage span', span, '/', short)
    assert en_norm('  Hugo. ') == 'hugo' and is_hit('Hugo.', ['hugo'])
    print(rows[0])
    print('common.py self-test OK')
