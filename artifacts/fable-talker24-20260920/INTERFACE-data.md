# INTERFACE-data.md — shard / tokenizer / sentence-index format (talker build task 1)

**Status: frozen contract.** Written 2026-09-20 before the heavy processing, so the model/trainer
builder can code against it in parallel. Producer: `scripts/fable_talker24_data.py`. If anything
here has to change, it changes here first.

Everything the GPU box needs is **numpy-only**: `np.memmap` / `np.fromfile` and one pure-Python
decode function. The `tokenizers` library is *not* required at training time.

---

## 0. Directory layout

```
artifacts/fable-talker24-20260920/
  data/
    DATASET-SURVEY.md
    download.sh
    raw/                      <- downloaded corpora (git-ignored by a local .gitignore of "*")
    MANIFEST-raw.json         <- sha256 + byte size of every downloaded file
  shards/                     <- git-ignored by a local .gitignore of "*"
    tokenizer.json            <- HuggingFace `tokenizers` native (Mac side only)
    tokenizer_vocab.json      <- {piece: id}, plain JSON      (GPU side: decoding)
    tokenizer_merges.txt      <- one "a b" merge per line     (GPU side: optional encoding)
    tokenizer_meta.json       <- specials, vocab size, sha256s
    decode_numpy.py           <- pure-Python/numpy ids -> text; no dependencies but numpy
    manifest.json             <- every shard, its counts and sha256s
    stats.json / stats.md     <- tokens per source, length histogram, vocabulary coverage
    train/  valid/  s0/       <- shard files (below)
  venv/                       <- project venv (git-ignored by a local .gitignore of "*")
  run_data_full.sh            <- full-corpus launcher (bash run_data_full.sh)
```

## 1. Shard files

A **shard** is four binary files plus a JSON sidecar that share a stem:

```
shards/<split>/<split>-<NNNNN>.tokens.u16
shards/<split>/<split>-<NNNNN>.ents.u16
shards/<split>/<split>-<NNNNN>.sents.u32
shards/<split>/<split>-<NNNNN>.docs.u32
shards/<split>/<split>-<NNNNN>.json
```

`<split>` ∈ {`train`, `valid`, `s0`}; `<NNNNN>` is a zero-padded shard index starting at `00000`.
All binaries are **raw little-endian arrays, no header, no padding**. (Little-endian is the only
byte order either machine uses; the sidecar records `"byte_order": "little"` so a reader can assert.)

| file | dtype | length | meaning |
|---|---|---|---|
| `.tokens.u16` | `uint16` | `n_tokens` | the token ids, one document after another |
| `.ents.u16` | `uint16` | `n_tokens` (1:1 with tokens) | entity **code id** at that position, or `0xFFFF` (=65535) where the position is not an entity |
| `.sents.u32` | `uint32` | `n_sentences + 1` | CSR boundaries into `.tokens.u16`: sentence *i* is `tokens[sents[i]:sents[i+1]]` |
| `.docs.u32` | `uint32` | `n_documents + 1` | CSR boundaries into the **sentence** index: document *j* is sentences `docs[j] .. docs[j+1]`, i.e. tokens `sents[docs[j]] : sents[docs[j+1]]` |

Invariants (asserted by the producer and by `tests/test_fable_talker24_data.py`):

- `sents[0] == 0`, `sents[-1] == n_tokens`, `sents` strictly increasing (no empty sentences).
- `docs[0] == 0`, `docs[-1] == n_sentences`, `docs` strictly increasing (no empty documents).
- Every document's sentences are contiguous; documents never straddle a shard boundary.
- `ents[i] != 0xFFFF` **iff** `tokens[i] == 4` (`<ENT>`). Exactly one code per placeholder.
- A shard holds at most `2**31 - 1` tokens, so `uint32` offsets never overflow. The default cap is
  **134,217,728 tokens (256 MiB of `.tokens.u16`)** per shard.

**Sentences are whitespace-stripped before encoding**, and no separator token sits between them:
the tokens of sentence *i* end with its final punctuation and the tokens of sentence *i+1* begin
with its first letter. Sentences are the unit the trainer consumes (design §B), so this is the
right primitive — but **a reader that concatenates sentences must insert its own separator**, or
it gets `.it shimmered`. Inside a sentence, spacing is preserved by the byte-level BPE exactly as
GPT-2 does it (a leading space is part of the following piece, `Ġthe`).

Sidecar `<split>-<NNNNN>.json`:

```json
{
  "split": "train", "index": 0, "byte_order": "little",
  "n_tokens": 134217728, "n_sentences": 11203344, "n_documents": 612004,
  "source_counts": {"simplestories": 90112000, "tinystories_v2": 40000000, "...": 0},
  "sha256": {"tokens": "...", "ents": "...", "sents": "...", "docs": "..."},
  "tokenizer_sha256": "...", "seed": 24, "producer_sha256": "...",
  "schema_version": 1
}
```

`source_counts` maps a source name to how many of the shard's tokens came from it. Sources are
`simplestories`, `tinystories_v2`, `tinydialogues`, `soda`. Documents from different sources are
interleaved in a fixed, seed-determined order, so any prefix of a shard is already a mixed diet.

### Loading a shard with numpy only

```python
import numpy as np, json, pathlib

def load_shard(stem):                       # stem = ".../train/train-00000"
    stem = pathlib.Path(stem)
    meta   = json.loads(stem.with_suffix(".json").read_text())
    tokens = np.memmap(f"{stem}.tokens.u16", dtype="<u2", mode="r")
    ents   = np.memmap(f"{stem}.ents.u16",   dtype="<u2", mode="r")
    sents  = np.fromfile(f"{stem}.sents.u32", dtype="<u4")
    docs   = np.fromfile(f"{stem}.docs.u32",  dtype="<u4")
    return meta, tokens, ents, sents, docs

# every sentence of 4..12 pieces, as (start, end) pairs -- the S1 stage-1 curriculum
lens  = np.diff(sents)
keep  = np.nonzero((lens >= 4) & (lens <= 12))[0]
s, e  = sents[keep], sents[keep + 1]

# one training sentence
i   = keep[0]
ids = np.asarray(tokens[sents[i]:sents[i+1]])          # uint16 token ids
cod = np.asarray(ents  [sents[i]:sents[i+1]])          # 0xFFFF where not a name
```

`np.memmap` on `.tokens.u16` / `.ents.u16` keeps RSS flat; `.sents.u32` / `.docs.u32` are small
enough (≈ 4 bytes per sentence) to read fully — 134M tokens gives ≈ 11M sentences ≈ 45 MB.

## 2. Token ids

Vocabulary size **8,192** (`0 .. 8191`). Byte-level BPE, **lower-cased text**, trained by us on
the reading list. Ids `0..15` are reserved specials and are never produced by the BPE:

| id | piece | meaning |
|---:|---|---|
| 0 | `<pad>` | padding. **Never appears in a shard**; the trainer adds it. |
| 1 | `<bos>` | start of sequence. **Never appears in a shard**; the trainer adds it. |
| 2 | `<eos>` | end of sequence. **Never appears in a shard**; the trainer adds it. |
| 3 | `<unk>` | unreachable in practice (byte-level BPE covers every byte); reserved. |
| 4 | `<ENT>` | **name placeholder.** Its code is in `.ents.u16` at the same index. |
| 5 | `<SUBJ>` | copy action: print the subject slot's name |
| 6 | `<OBJ>` | copy action: print the object slot's value |
| 7 | `<OLD>` | copy action: print the pre-correction value |
| 8 | `<TURN>` | start of a new utterance inside a dialogue document |
| 9 | `<DOC>` | document separator. Reserved; **not emitted** (use `.docs.u32`). |
| 10–15 | `<extra_0>` … `<extra_5>` | reserved for build task 2 / the trainer |

Ids `16 .. 8191` are the 8,176 learned BPE pieces (the 256 byte-level alphabet symbols are among
them). **The shards contain only ids 4, 8 and 16..8191.** `<pad>/<bos>/<eos>` are the trainer's
job, so the trainer is free to choose the sequence framing without a re-run of the data pipeline.

**Copy actions are inside the vocabulary** (ids 5/6/7), not three extra logits bolted onto an
8,192-wide head. Design §2.2 said "8,192 pieces + 3 copy actions" without saying which; putting
them inside keeps the mouth's output exactly 8,192-wide, keeps the tied embedding table at
8,192 × 384 = 3.15M as costed, and — the real reason — guarantees build task 2's generator and this
pipeline cannot disagree about an id. *A model builder who prefers separate logits can map
`logit[8192+k] <-> id 5+k`; the data format does not change.* Noted as a judgement call.

## 3. Entity codes (`.ents.u16`)

Design §4.3: a name is a placeholder plus a code, **re-drawn per document**.

- Code pool: **4,096** codes, ids `0 .. 4095`.
  - `0 .. 3071` — **training pool.** Documents draw from here.
  - `3072 .. 4095` — **reserved, never drawn by this pipeline.** They exist so M1-style held-out
    evaluation can use codes the talker has provably never seen.
- Per document, the distinct names found in that document are mapped to distinct codes drawn
  **without replacement** from the training pool, using a per-document RNG seeded by
  `blake2b(f"{seed}|{doc_uid}")`. Same seed ⇒ same codes, every run, on every machine.
- A document with more than 64 distinct names has its 65th-and-later names left as ordinary words
  (they are lowercased and BPE'd). Counted and reported in `stats.json` as `ent_overflow_docs`.
- `0xFFFF` in `.ents.u16` means "no code here"; `0xFFFF` is therefore **not** a valid code and the
  pool never reaches it.

The code is an **index**, not a vector. The symbol table (frozen random 48-number codes, owned by
the model/operator side, `subject`/`object` fields of the 416-number thought) is looked up by this
index. This pipeline never invents the 48 numbers.

**Name detection rule** (design §2.1), applied to the *original cased* text before lower-casing:

1. A token is a candidate if it matches `[A-Z][a-z'’-]*` (a capitalised word).
2. It is a **name** if it is on the corpus name list, **or** if its lower-cased form never appears
   in the corpus word list.
3. A capitalised word that is only ever sentence-initial and whose lower-cased form *is* a common
   corpus word (`The`, `Once`, `Then`, …) is **not** a name.
4. Possessives: `Mira's` → `<ENT>` + `'s`; the `'s` is ordinary BPE. Hyphenated and apostrophed
   name parts stay in the one placeholder.
5. `I` is hard-excluded.

The corpus name list and word list are built in a first pass over a fixed sample and written to
`shards/name_list.json` / `shards/word_list.json` (both hashed in `manifest.json`), so the swap in
pass two is a pure function of those two files plus the seed.

## 4. Tokenizer export for the GPU box

`shards/tokenizer_vocab.json` — `{"piece": id, ...}` for all 8,192 ids, including the 16 specials.
`shards/tokenizer_merges.txt` — the BPE merge table, one `left right` pair per line, in rank order,
with a leading `#version: 0.2` comment line (the `tokenizers` convention). Decoding needs only the
vocab; merges are there so the box can encode without `tokenizers` if it ever has to.

`shards/tokenizer_meta.json`:

```json
{"vocab_size": 8192, "model": "ByteLevel BPE", "lowercase": true,
 "specials": {"<pad>":0,"<bos>":1,"<eos>":2,"<unk>":3,"<ENT>":4,"<SUBJ>":5,"<OBJ>":6,"<OLD>":7,
              "<TURN>":8,"<DOC>":9,"<extra_0>":10,"<extra_1>":11,"<extra_2>":12,"<extra_3>":13,
              "<extra_4>":14,"<extra_5>":15},
 "ent_code_pool": 4096, "ent_code_train_max": 3071, "ent_code_reserved_min": 3072,
 "ent_none": 65535,
 "sha256": {"tokenizer.json":"...","tokenizer_vocab.json":"...","tokenizer_merges.txt":"..."}}
```

### Pure-Python / numpy decode (ids → text)

`shards/decode_numpy.py` is written by the pipeline and is **self-contained** (stdlib + numpy):

```python
from decode_numpy import Decoder
dec = Decoder("shards/tokenizer_vocab.json")          # ~30 ms
dec.decode(ids)                                       # ids: list/np.ndarray of uint16
dec.decode(ids, ents=cod, names={7: "Mira", 12: "Oren"})
```

- Byte-level BPE, so decoding is: id → piece → concatenate → map each character back through the
  inverse GPT-2 `bytes_to_unicode` table → `bytes.decode("utf-8", errors="replace")`.
- `<pad>/<bos>/<eos>/<unk>/<DOC>` render as `""`; `<TURN>` renders as `"\n"`.
- `<ENT>` renders as `names[code]` when `ents` and `names` are supplied, otherwise as
  `f"<ent:{code}>"`, otherwise as `"<ENT>"`. **This is the only way a name can reach the output**,
  which is the point of the design: the decoder has no other path to a name string.
- `<SUBJ>/<OBJ>/<OLD>` render as `names[...]` only if the caller passes a `copy=` mapping; by
  default they render as `"<SUBJ>"` etc. so an un-resolved copy action is visible, never silent.
- Capital letters are **not** restored by this function — the shards are lower-case by design and
  the printer (build task 3) restores casing. `decode()` has `capitalize_sentences=True` as an
  opt-in convenience for eyeballing samples; it is off by default.

## 5. What the trainer is expected to do (not enforced here)

- Add `<bos>` / `<eos>` around a sentence; pad with `<pad>` (id 0) and mask it.
- Look the 48-number code up from the symbol table using `.ents.u16`; feed it as the `<ENT>`
  position's input embedding (design §2.1).
- Length curricula come from `np.diff(sents)`: ≤ 12, then ≤ 24, then ≤ 48 pieces (design §B).
- Sentences longer than **48 pieces are already dropped by this pipeline** (counted in
  `stats.json` as `dropped_long_sentences`), so no sentence in a shard exceeds 48 tokens. A
  document keeps its remaining sentences; only the over-long sentence is dropped.

## 6. Splits

- `train/` — SimpleStories `train-0000{0..6}`, TinyStories-V2 `train`, TinyDialogues `train`,
  SODA `train` (post-filter).
- `valid/` — SimpleStories `test`, TinyStories-V2 `valid`, TinyDialogues `val`, SODA `valid`.
  These are the corpora's own held-out files; nothing from `train/` leaks in.
- `s0/` — the single smoke-test shard (design S0), see `shards/manifest.json` for its token count.
  It is a **prefix of the interleaved train stream**, cut at a document boundary, so it is already
  a mixed diet; its sidecar reports `"source_counts": {"mixed": n_tokens}` rather than a per-source
  split (the per-source breakdown of the same documents is in `train-00000.json`).

`shards/manifest.json` lists every shard with its counts and sha256s, plus the tokenizer hashes and
the producer script hash, so a run is reproducible and a corrupted file is detectable.

## 7. What is on disk right now (SAMPLE build — read this before you train)

The shards currently in `shards/` are a **sample build**: 48 MB of raw text per source, produced to
test the pipeline end to end. `shards/tokenizer_meta.json` carries `"profile": "sample"`, which is
the flag to check — the full build writes `"profile": "full"`, and `run_data_full.sh` refuses to
mix the two (it moves a sample build aside before starting). **The tokenizer differs between the
two builds**, so a model trained on these shards cannot read full-build shards, and vice versa.

Use these for the smoke test and for wiring the loader. Rerun `bash run_data_full.sh 4` for the
real corpus.

| shard | tokens | sentences | documents | `.tokens.u16` bytes |
|---|---:|---:|---:|---:|
| `shards/train/train-00000` | 40,560,207 | 3,854,743 | 186,089 | 81,120,414 |
| `shards/valid/valid-00000` | 5,053,064 | 479,224 | 23,193 | 10,106,128 |
| **`shards/s0/s0-00000`** | **29,999,893** | **2,851,692** | **137,646** | **59,999,786** |

**The S0 smoke-test shard is `artifacts/fable-talker24-20260920/shards/s0/s0-00000.*`** — 30.0 M
tokens, 0.06 GB of `.tokens.u16`, inside the ≤ 0.2 GB the brief asked for.

Sample-build train mix (tokens): simplestories 11,392,915 · tinystories_v2 12,312,606 ·
tinydialogues 10,878,420 · soda 5,976,266. SODA is smaller than its 48 MB share because the
simplicity filter keeps ≈ 32 % of it, which is what design §1.3 predicted.

Tokenizer health on this build (`shards/stats.json`): 7,972 of 8,192 ids occur; 95.1 % of word
occurrences are a single piece; 1.054 pieces per word on average; 2.0 % of positions are `<ENT>`.

Measured throughput, for planning the full run: **1.52 MB/s of raw text per core**, **4.79 MB/s
with 4 workers**, **213,446 tokens per raw MB**. The full corpus (≈ 5.81 GB of raw text after the
SODA filter's input is counted whole) is therefore ≈ 1.23 B tokens, ≈ 16 min of encoding at 4
workers, ≈ 40–45 min end to end. It will produce ≈ 10 train shards at the 134 M-token cap.
