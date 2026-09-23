"""own-O0c pretraining data pipeline (plan 01-own-ear-mouth-plan.md, Task 2.1/5).

CPU-only. Additive-only experiment file: creates new outputs, never edits inputs.

Stages:
  sentence/turn splitting -> fictional name swapping -> uint16 shard writer
  with a document index -> deterministic (seed, step) data order.

Name pool is fictional (invented) names only. No TEST-ONLY panel is touched.
No network. No download. Run with:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with numpy python -B \
      scripts/claude_own_o0c_prep.py <subcommand> ...

Subcommands:
  order    write a deterministic (seed, step) permutation of N doc ids.
  process  split + name-swap + encode + shard a line-oriented sample file.
  verify   round-trip + stats check over written shards (used for Pown0c.1).

Sample input format for `process`: one JSON object per line with keys
  {"id": str, "source": str, "text": str}
or plain text (one document per line, source defaults to "txt").
"""

import argparse
import hashlib
import json
import os
import random
import re
import struct
import sys

# --------------------------------------------------------------------------
# Fictional name pool (invented names only; reserved names never used here:
# see PASSMARKS.md for the held-out list, which this file must not contain).
# --------------------------------------------------------------------------
FICTIONAL_NAMES = [
    "Mira", "Tal", "Oona", "Pip", "Fig", "Moss", "Bo", "Ada", "Rook",
    "Sarel", "Nix", "Wren", "Keth", "Liora", "Bram", "Tilda", "Oskar",
    "Fen", "Hazel", "Corin", "Dessa", "Ember", "Flint", "Greta",
    "Hollis", "Ivo", "Juniper", "Koda", "Lark", "Maple", "Nilo",
    "Odette", "Perrin", "Quill", "Rowan", "Sable", "Tansy", "Ulf",
    "Vesper", "Willow", "Xan", "Yara", "Zephyr", "Alder", "Birch",
    "Clover", "Dunlin", "Elm", "Fern", "Gale", "Heath", "Iris",
    "Jasper", "Kestrel", "Linden", "Meadow", "Nettle", "Otter",
    "Plover", "Quince", "Reed", "Sorrel", "Thrush", "Ursa", "Vetch",
    "Widgeon", "Yarrow", "Zinnia", "Ash", "Brook", "Cedar", "Dale",
    "Edda", "Firth", "Glen",     "Harbor", "Ines", "Jura", "Kano",
    "Lena", "Marisol", "Nadia", "Opal", "Petra", "Rosa", "Selma",
    "Tessa", "Uma", "Vera", "Willa", "Xenia", "Ysolde", "Zelda",
    "Ansel", "Bodil", "Cas", "Delia", "Elif", "Farah", "Gus",
    "Hana", "Ilsa", "Jon", "Kira", "Ludo", "Mara", "Nils",
    "Orla", "Pavel", "Rhea", "Silas", "Tove", "Umar", "Viggo",
]

# Words that look capitalised mid-sentence but are never names; left alone.
NON_NAME_KEEP = {
    "I", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
    "Saturday", "Sunday", "January", "February", "March", "April",
    "May", "June", "July", "August", "September", "October",
    "November", "December", "Christmas", "English", "God",
}

SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[]?[A-Z0-9])")
WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
CAP_RE = re.compile(r"^[A-Z][a-z]{1,15}$")


def split_sentences(text):
    """Split text into sentences/turns. Pure function, deterministic."""
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []
    # Dialogue turns stay separate: a blank line always breaks.
    chunks = re.split(r"\n\s*\n", text)
    out = []
    for ch in chunks:
        ch = " ".join(ch.split())
        if not ch:
            continue
        parts = SENT_SPLIT_RE.split(ch)
        for p in parts:
            p = p.strip()
            if p:
                out.append(p)
    return out


def first_token_len(sentence):
    m = WORD_RE.match(sentence)
    return m.end() if m else 0


def swap_names(doc, seed, doc_id, pool=None):
    """Replace capitalised non-initial tokens with fresh fictional names.

    Mapping is per-document and deterministic in (seed, doc_id): the same
    document always maps the same way, different documents draw fresh names.
    Returns (new_doc, {old: new}).
    """
    pool = list(pool or FICTIONAL_NAMES)
    key = hashlib.sha256(
        ("%d\x00%s" % (seed, doc_id)).encode("utf-8")
    ).digest()
    rng = random.Random(int.from_bytes(key[:8], "little"))
    order = pool[:]
    rng.shuffle(order)
    mapping = {}
    nxt = 0

    def fresh(old):
        nonlocal nxt
        if old not in mapping:
            if nxt >= len(order):  # more names than pool: reshuffle tail
                extra = pool[:]
                rng.shuffle(extra)
                order.extend(extra)
            # never map a name onto itself
            cand = order[nxt]
            nxt += 1
            if cand == old and nxt < len(order) + len(pool):
                cand = order[nxt % len(order)]
                nxt += 1
            mapping[old] = cand
        return mapping[old]

    sentences = split_sentences(doc)
    out_sents = []
    for sent in sentences:
        fl = first_token_len(sent)

        def repl(m):
            tok = m.group(0)
            if m.start() < fl:
                return tok  # sentence-initial: keep
            if not CAP_RE.match(tok):
                return tok
            if tok in NON_NAME_KEEP:
                return tok
            return fresh(tok)

        out_sents.append(WORD_RE.sub(repl, sent))
    # Preserve paragraph breaks of the input: rejoin single-spaced.
    return " ".join(out_sents), dict(mapping)


# --------------------------------------------------------------------------
# Tokenizer adapter (works with tokenizers.Tokenizer or a byte fallback).
# --------------------------------------------------------------------------
class ByteFallback:
    """UTF-8 byte encoder used only if no tokenizer file is available."""

    unk_id = -1

    def encode(self, text):
        return list(text.encode("utf-8"))

    def decode(self, ids):
        return bytes(ids).decode("utf-8", errors="replace")


def load_tokenizer(path):
    if path is None:
        return ByteFallback(), True
    from tokenizers import Tokenizer as _T

    tok = _T.from_file(path)
    return tok, False


def encode_text(tok, text):
    out = tok.encode(text)
    return out.ids if hasattr(out, "ids") else list(out)


def decode_ids(tok, ids):
    if hasattr(tok, "decode"):
        try:
            return tok.decode(list(ids))
        except TypeError:
            return tok.decode(list(ids), skip_special_tokens=False)
    return tok.decode(list(ids))


# --------------------------------------------------------------------------
# Shard writer: concatenated uint16 LE ids + JSON document index.
# --------------------------------------------------------------------------
def write_shards(encoded_docs, metas, out_dir, shard_size_tokens, prefix="shard"):
    os.makedirs(out_dir, exist_ok=True)
    index = []
    shard_no = 0
    buf = []
    buf_tokens = 0
    shard_name = None
    fh = None

    def open_shard():
        nonlocal shard_no, shard_name, fh
        shard_name = "%s_%05d.bin" % (prefix, shard_no)
        fh = open(os.path.join(out_dir, shard_name), "wb")

    open_shard()
    for ids, meta in zip(encoded_docs, metas):
        for v in ids:
            if not (0 <= v <= 65535):
                raise ValueError("token id %d exceeds uint16" % v)
        start = buf_tokens
        buf.extend(ids)
        buf_tokens += len(ids)
        index.append(
            {
                "id": meta["id"],
                "source": meta["source"],
                "shard": shard_name,
                "start": start,
                "length": len(ids),
            }
        )
        if buf_tokens >= shard_size_tokens:
            fh.write(struct.pack("<%dH" % len(buf), *buf))
            fh.close()
            shard_no += 1
            buf = []
            buf_tokens = 0
            open_shard()
    if buf:
        fh.write(struct.pack("<%dH" % len(buf), *buf))
        fh.close()
    else:
        fh.close()
        os.remove(os.path.join(out_dir, shard_name))
    # fix shard names recorded before a rollover: entries point at the shard
    # that was open when written; rollover already handled since shard_name is
    # read at append time. Recompute: entries are correct as-is.
    with open(os.path.join(out_dir, "index.json"), "w") as f:
        json.dump(index, f)
    return index


def read_shard_ids(out_dir, entry):
    n = entry["length"]
    with open(os.path.join(out_dir, entry["shard"]), "rb") as f:
        f.seek(entry["start"] * 2)
        raw = f.read(n * 2)
    if len(raw) != n * 2:
        raise ValueError("short read for %s" % entry["id"])
    return list(struct.unpack("<%dH" % n, raw))


# --------------------------------------------------------------------------
# Deterministic (seed, step) data order.
# --------------------------------------------------------------------------
def data_order(n, seed, step):
    import numpy as np

    ss = np.random.SeedSequence([int(seed), int(step)])
    rng = np.random.default_rng(ss)
    return rng.permutation(int(n)).astype(np.uint64)


def cmd_order(args):
    import numpy as np

    perm = data_order(args.n, args.seed, args.step)
    arr = perm.astype("<u4") if args.n <= 2**32 else perm.astype("<u8")
    with open(args.out, "wb") as f:
        f.write(arr.tobytes())
    h = hashlib.sha256(arr.tobytes()).hexdigest()
    print("order n=%d seed=%d step=%d sha256=%s" % (args.n, args.seed, args.step, h))
    print("numpy=%s" % np.__version__)


def read_input_docs(path):
    docs = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.rstrip("\n")
            if not line.strip():
                continue
            if line.lstrip().startswith("{"):
                obj = json.loads(line)
                docs.append(
                    {
                        "id": str(obj.get("id", "doc-%d" % i)),
                        "source": str(obj.get("source", "txt")),
                        "text": str(obj.get("text", "")),
                    }
                )
            else:
                docs.append({"id": "doc-%d" % i, "source": "txt", "text": line})
    return docs


def cmd_process(args):
    tok, is_fallback = load_tokenizer(args.tokenizer)
    if is_fallback:
        print("WARNING: no tokenizer file; using UTF-8 byte fallback", file=sys.stderr)
    docs = read_input_docs(args.input)
    metas, encoded, proc_texts = [], [], []
    for d in docs:
        text = d["text"]
        if args.swap_names:
            text, _m = swap_names(text, args.seed, d["id"])
        sents = split_sentences(text)
        joined = " ".join(sents)
        ids = encode_text(tok, joined)
        metas.append({"id": d["id"], "source": d["source"]})
        encoded.append(ids)
        proc_texts.append(joined)
    index = write_shards(encoded, metas, args.out_dir, args.shard_tokens)
    with open(args.docs_out, "w", encoding="utf-8") as f:
        for m, t in zip(metas, proc_texts):
            f.write(json.dumps({"id": m["id"], "source": m["source"], "text": t}) + "\n")
    total = sum(len(e) for e in encoded)
    print(
        "docs=%d tokens=%d shards=%d fallback=%s"
        % (
            len(encoded),
            total,
            len(set(e["shard"] for e in index)),
            is_fallback,
        )
    )


def cmd_verify(args):
    tok, is_fallback = load_tokenizer(args.tokenizer)
    specials = set()
    unk_id = None
    if not is_fallback:
        try:
            specials = set(tok.get_added_tokens_decoder().keys())
        except Exception:
            specials = set()
        try:
            unk_id = tok.token_to_id("<unk>")
        except Exception:
            unk_id = None
    with open(args.docs, "r", encoding="utf-8") as f:
        docs = [json.loads(l) for l in f if l.strip()]
    with open(os.path.join(args.shards, "index.json")) as f:
        index = json.load(f)
    by_id = {d["id"]: d for d in docs}
    rng = random.Random(args.seed)
    sample = rng.sample(index, min(args.sample_n, len(index)))
    n_rt = 0
    n_miss = 0
    miss_ids = []
    tok_per_source = {}
    sent_lens = []
    n_unk = 0
    n_single_byte = 0
    n_tok_total = 0
    # full-corpus token/source counts + sentence histogram come from shards
    per_source_full = {}
    for entry in index:
        ids = read_shard_ids(args.shards, entry)
        doc = by_id[entry["id"]]
        per_source_full[doc["source"]] = per_source_full.get(doc["source"], 0) + len(ids)
        for s in split_sentences(doc["text"]):
            sent_lens.append(len(encode_text(tok, s)))
    for entry in sample:
        ids = read_shard_ids(args.shards, entry)
        doc = by_id[entry["id"]]
        dec = decode_ids(tok, ids)
        re_ids = encode_text(tok, doc["text"])
        ok = (dec == doc["text"]) and (list(re_ids) == list(ids))
        n_rt += 1
        if not ok:
            n_miss += 1
            miss_ids.append(entry["id"])
        tok_per_source[doc["source"]] = tok_per_source.get(doc["source"], 0) + len(ids)
        n_tok_total += len(ids)
        for i in ids:
            if unk_id is not None and i == unk_id:
                n_unk += 1
            if not is_fallback and i not in specials:
                try:
                    piece = tok.decode([i])
                    if len(piece.encode("utf-8", errors="replace")) <= 1:
                        n_single_byte += 1
                except Exception:
                    pass
    import collections

    bins = [0, 8, 16, 32, 64, 128, 256, 10**9]
    hist = collections.Counter()
    for L in sent_lens:
        for b0, b1 in zip(bins[:-1], bins[1:]):
            if b0 <= L < b1:
                hist[(b0, b1 if b1 < 10**9 else "inf")] += 1
                break
    print("roundtrip_sampled=%d misses=%d" % (n_rt, n_miss))
    if miss_ids[:10]:
        print("miss_ids=%s" % miss_ids[:10])
    print("tokens_per_source_sample=%s" % json.dumps(tok_per_source, sort_keys=True))
    print("tokens_per_source_full=%s" % json.dumps(per_source_full, sort_keys=True))
    print(
        "sentlen_hist=%s"
        % json.dumps({("%d-%s" % k): v for k, v in sorted(hist.items())})
    )
    print("sentences=%d" % len(sent_lens))
    unk_share = (n_unk / n_tok_total) if n_tok_total else 0.0
    sb_share = (n_single_byte / n_tok_total) if n_tok_total else 0.0
    print(
        "unk=%d single_byte=%d total=%d unk_share=%.6f single_byte_share=%.6f fallback=%s"
        % (n_unk, n_single_byte, n_tok_total, unk_share, sb_share, is_fallback)
    )
    return 0 if n_miss == 0 else 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("order")
    a.add_argument("--n", type=int, required=True)
    a.add_argument("--seed", type=int, required=True)
    a.add_argument("--step", type=int, required=True)
    a.add_argument("--out", required=True)
    a.set_defaults(fn=cmd_order)
    a = sub.add_parser("process")
    a.add_argument("--input", required=True)
    a.add_argument("--tokenizer", default=None)
    a.add_argument("--out-dir", required=True)
    a.add_argument("--docs-out", required=True)
    a.add_argument("--shard-tokens", type=int, default=200000)
    a.add_argument("--seed", type=int, default=7)
    a.add_argument("--swap-names", action="store_true")
    a.set_defaults(fn=cmd_process)
    a = sub.add_parser("verify")
    a.add_argument("--shards", required=True)
    a.add_argument("--docs", required=True)
    a.add_argument("--tokenizer", default=None)
    a.add_argument("--sample-n", type=int, default=1000)
    a.add_argument("--seed", type=int, default=7)
    a.set_defaults(fn=cmd_verify)
    args = ap.parse_args(argv)
    r = args.fn(args)
    return r if isinstance(r, int) else 0


if __name__ == "__main__":
    raise SystemExit(main())
