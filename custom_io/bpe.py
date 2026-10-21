"""U0 (INPUT-UNITS-2026-10-07.md): byte-level BPE for the PROMPT only, learned on train prompts only.
python3 -m custom_io.bpe --data DATA --new 308 [--out custom_io/models/bpe_prompt.json]
Base symbols are the 95 printable ASCII characters (the char vocab's own ids, so the 13 specials + 95 letters keep their ids); merges are
learned GPT-2 style: the text is first cut by GPT-2's pre-tokenizer pattern (ASCII form: words with their leading space, digit runs
with their leading space, punctuation runs, spaces), then the most frequent adjacent pair is merged until `new` new tokens exist
(ties broken by the pair's text, so the result is the same on every machine). New tokens get ids len(vocab), len(vocab)+1, ...
in the order they were made. A frozen hand-written algorithm, by design: it is what U0 compares letters against."""
import argparse, collections, hashlib, json, os, re

PRE = re.compile(r"'s|'t|'re|'ve|'m|'ll|'d| ?[A-Za-z]+| ?[0-9]+| ?[^\sA-Za-z0-9]+|\s+(?!\S)|\s+")
DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'bpe_prompt.json')


def pretok(text):
    return PRE.findall(text)


def train(texts, new):
    """-> merges [(a, b)] in order, stopping when `new` distinct new tokens exist."""
    words = collections.Counter(w for t in texts for w in pretok(t))
    segs = {w: list(w) for w in words}
    merges, made = [], set()
    while len(made) < new:
        pairs = collections.Counter()
        for w, c in words.items():
            s = segs[w]
            for x, y in zip(s, s[1:]):
                pairs[x, y] += c
        if not pairs:
            break
        best = min(pairs.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        merges.append(best)
        tok = best[0] + best[1]
        if len(tok) > 1:
            made.add(tok)
        for w in words:
            s = segs[w]
            if len(s) < 2:
                continue
            out, i = [], 0
            while i < len(s):
                if i + 1 < len(s) and s[i] == best[0] and s[i + 1] == best[1]:
                    out.append(tok); i += 2
                else:
                    out.append(s[i]); i += 1
            segs[w] = out
    return merges


class BPE:
    """encode(text) -> ids: chars keep the char vocab's ids, merged tokens get base + k."""
    def __init__(self, vocab, path=DEFAULT):
        d = json.load(open(path))
        self.merges = [tuple(m) for m in d['merges']]
        self.rank = {m: i for i, m in enumerate(self.merges)}
        self.base = len(vocab)
        self.stoi = dict(vocab.stoi) if hasattr(vocab, 'stoi') else {c: i for i, c in enumerate(vocab.itos)}
        new = []
        for a, b in self.merges:
            if a + b not in self.stoi and a + b not in new:
                new.append(a + b)
        for k, t in enumerate(new):
            self.stoi[t] = self.base + k
        self.n_new = len(new)
        self._word, self._text = {}, {}

    def word(self, w):
        hit = self._word.get(w)
        if hit is None:
            s = list(w)
            while len(s) > 1:
                r = [(self.rank.get((x, y), 1 << 30), i) for i, (x, y) in enumerate(zip(s, s[1:]))]
                rk, i = min(r)
                if rk == 1 << 30:
                    break
                s[i:i + 2] = [s[i] + s[i + 1]]
            hit = self._word[w] = [self.stoi[t] for t in s]
        return hit

    def encode(self, text):
        hit = self._text.get(text)
        if hit is None:
            if len(self._text) > 400_000:
                self._text.clear()
            hit = self._text[text] = [i for w in pretok(text) for i in self.word(w)]
        return hit

    def tokens(self, text):
        itos = {i: t for t, i in self.stoi.items()}
        return [itos[i] for i in self.encode(text)]


def main(argv=None):
    from custom_io.data import DEFAULT_DATA, CharVocab, load_rows
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=DEFAULT_DATA)
    ap.add_argument('--new', type=int, default=308)
    ap.add_argument('--out', default=DEFAULT)
    a = ap.parse_args(argv)
    path = os.path.join(a.data, 'train.jsonl')
    texts = [r['prompt'] for r in load_rows(path, keep=('prompt',))]
    vocab = CharVocab.get(a.data)
    assert all(c in vocab.stoi for t in texts for c in set(t)), 'a train prompt has a char outside the vocab'
    merges = train(texts, a.new)
    sha = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    json.dump(dict(what='U0 prompt BPE: GPT-2 pre-tokenizer (ASCII), merges learned on train prompts only', train_sha256=sha, n_train_prompts=len(texts),
                   base=len(vocab), new=a.new, merges=merges), open(a.out, 'w'), indent=0)
    bpe = BPE(vocab, a.out)
    n_chars, n_toks = sum(map(len, texts)), sum(len(bpe.encode(t)) for t in texts)
    print(json.dumps(dict(merges=len(merges), new_tokens=bpe.n_new, ids=bpe.base + bpe.n_new, chars_per_token=round(n_chars / n_toks, 3),
                          example=bpe.tokens(texts[0]))))


if __name__ == '__main__':
    main()
