#!/usr/bin/env python3
"""Reading-list pipeline for the talker (design 24, build task 1).

Turns the downloaded reading list (SimpleStories, TinyStories-V2 GPT-4, TinyDialogues,
SODA) into uint16 token shards with a sentence index, plus an 8,192-piece byte-level BPE
tokenizer trained from scratch on that same reading list.

The on-disk contract is written out in full in
``artifacts/fable-talker24-20260920/INTERFACE-data.md`` and this file is its only producer.
Short version:

    <split>-<NNNNN>.tokens.u16   uint16 token ids
    <split>-<NNNNN>.ents.u16     uint16 entity code per position, 0xFFFF = none
    <split>-<NNNNN>.sents.u32    uint32 CSR boundaries into tokens (n_sentences + 1)
    <split>-<NNNNN>.docs.u32     uint32 CSR boundaries into sentences (n_documents + 1)
    <split>-<NNNNN>.json         sidecar with counts + sha256

Everything is deterministic given ``--seed``.

Stages (``python fable_talker24_data.py <stage>``):

    survey      list the input units that would be processed
    names       pass A: corpus word list, name list, simple-word list
    tokenizer   train the 8,192 byte-level BPE + write the numpy-only exports
    encode      pass B: encode every unit into a part file (parallel, resumable)
    merge       shuffle documents across parts and write the final shards
    stats       tokens per source, sentence-length histogram, vocabulary coverage
    s0          write the single smoke-test shard
    all         names -> tokenizer -> encode -> merge -> stats -> s0

Data files only: this script reads .parquet and .txt and never executes anything from the
dataset repositories.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import sys
import time
import unicodedata
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import numpy as np

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# --------------------------------------------------------------------------------------
# Constants that the INTERFACE document freezes
# --------------------------------------------------------------------------------------

SCHEMA_VERSION = 1
VOCAB_SIZE = 8192

SPECIALS: dict[str, int] = {
    "<pad>": 0,
    "<bos>": 1,
    "<eos>": 2,
    "<unk>": 3,
    "<ENT>": 4,
    "<SUBJ>": 5,
    "<OBJ>": 6,
    "<OLD>": 7,
    "<TURN>": 8,
    "<DOC>": 9,
    "<extra_0>": 10,
    "<extra_1>": 11,
    "<extra_2>": 12,
    "<extra_3>": 13,
    "<extra_4>": 14,
    "<extra_5>": 15,
}
N_SPECIAL = len(SPECIALS)
ID_ENT = SPECIALS["<ENT>"]
ID_TURN = SPECIALS["<TURN>"]

ENT_CODE_POOL = 4096
ENT_CODE_TRAIN_MAX = 3071          # codes 0..3071 are drawn; 3072..4095 stay reserved
ENT_NONE = 0xFFFF
MAX_ENTS_PER_DOC = 64

MAX_SENTENCE_TOKENS = 48
SHARD_TOKEN_CAP = 134_217_728      # 256 MiB of .tokens.u16

SOURCES = ("simplestories", "tinystories_v2", "tinydialogues", "soda")

# SODA simplicity filter (design 1.3: "keep only dialogues whose words are >= 98 % inside
# our simple word list").
SODA_SIMPLE_FRACTION = 0.98
SODA_MIN_WORDS = 12

# Pass-A thresholds.
WORD_LIST_MIN_COUNT = 5            # lowercase occurrences before a word counts as "known"
NAME_MIN_NONINITIAL = 3            # capitalised, mid-sentence, this many times
NAME_MAX_LOWER_RATIO = 0.05        # ... and almost never seen lowercase
SIMPLE_MIN_COUNT = 20              # for the SODA simple-word list


# --------------------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------------------

def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_json(path: str | Path, obj) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(p)


def read_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def doc_rng(seed: int, doc_uid: str) -> random.Random:
    """A per-document RNG that is a pure function of (seed, doc_uid)."""
    digest = hashlib.blake2b(f"{seed}|{doc_uid}".encode("utf-8"), digest_size=8).digest()
    return random.Random(int.from_bytes(digest, "big"))


# --------------------------------------------------------------------------------------
# Sentence splitting
# --------------------------------------------------------------------------------------

_ABBREV = {
    "mr", "mrs", "ms", "dr", "st", "jr", "sr", "prof", "gen", "capt", "sgt", "lt",
    "rev", "hon", "col", "vs", "etc", "inc", "ltd", "co", "dept", "fig", "no", "vol",
    "approx", "apt", "ave", "blvd", "mt", "mme", "mlle", "messrs", "esq", "min", "sec",
}
_SENT_END = re.compile(r'([.!?]+["\'”’\)\]]*)(\s+|$)')
_LAST_WORD = re.compile(r"([A-Za-zÀ-ɏ]+)[.!?\"'”’\)\]]*$")
_OPENERS = "\"'“‘(—-–"


def split_sentences(text: str) -> list[str]:
    """Split a document into sentences.

    Newlines always end a sentence (they are paragraph / turn breaks in every one of our
    sources). Inside a paragraph we cut at . ! ? unless the preceding word is a known
    abbreviation or a single-letter initial, or the next character cannot start a
    sentence.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    out: list[str] = []
    for para in text.split("\n"):
        para = para.strip()
        if para:
            out.extend(_split_paragraph(para))
    return out


def _split_paragraph(para: str) -> list[str]:
    sents: list[str] = []
    start = 0
    for m in _SENT_END.finditer(para):
        end = m.end(1)
        piece = para[start:end]
        lw = _LAST_WORD.search(piece)
        if lw is not None:
            w = lw.group(1)
            if w.lower() in _ABBREV and m.group(1).startswith("."):
                continue
            if len(w) == 1 and w.isupper() and m.group(1) == ".":
                continue  # "J. R. Tolkien"
        nxt = para[m.end():m.end() + 1]
        if nxt and not (nxt.isupper() or nxt.isdigit() or nxt in _OPENERS):
            continue
        s = piece.strip()
        if s:
            sents.append(s)
        start = m.end()
    tail = para[start:].strip()
    if tail:
        sents.append(tail)
    return sents


# --------------------------------------------------------------------------------------
# Name detection and the per-document name -> code swap
# --------------------------------------------------------------------------------------

# A candidate name: capitalised, optionally hyphenated or with an internal apostrophe.
# A trailing possessive "'s" is deliberately NOT swallowed -- it stays as ordinary text.
NAME_RE = re.compile(
    r"[A-Z][a-z]+(?:['’][A-Z][a-z]+)?(?:-[A-Z][a-z]+)*"
)
WORD_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")
NEVER_A_NAME = {"i", "i'm", "i'll", "i've", "i'd", "ok", "okay", "tv"}


@dataclass
class Lexicon:
    """The two corpus-derived lists the swapper needs (design 2.1)."""
    words: set[str] = field(default_factory=set)        # lowercase ordinary words
    names: set[str] = field(default_factory=set)        # lowercase name forms
    simple: set[str] = field(default_factory=set)       # lowercase simple-English words

    @staticmethod
    def load(path: str | Path) -> "Lexicon":
        j = read_json(path)
        return Lexicon(set(j["words"]), set(j["names"]), set(j["simple"]))

    def save(self, path: str | Path) -> None:
        write_json(path, {
            "words": sorted(self.words),
            "names": sorted(self.names),
            "simple": sorted(self.simple),
        })


def is_name(surface: str, lex: Lexicon) -> bool:
    lw = surface.lower()
    if lw in NEVER_A_NAME:
        return False
    if lw in lex.names:
        return True
    return lw not in lex.words


Segment = tuple[str, str]  # ("text", literal) | ("ent", surface-name)


def segment_sentence(sentence: str, lex: Lexicon) -> list[Segment]:
    """Split one sentence into literal-text and entity segments."""
    segs: list[Segment] = []
    pos = 0
    for m in NAME_RE.finditer(sentence):
        if not is_name(m.group(0), lex):
            continue
        if m.start() > pos:
            segs.append(("text", sentence[pos:m.start()]))
        segs.append(("ent", m.group(0)))
        pos = m.end()
    if pos < len(sentence):
        segs.append(("text", sentence[pos:]))
    return segs


def assign_codes(names_in_order: Sequence[str], seed: int, doc_uid: str) -> dict[str, int]:
    """Draw distinct codes from the training pool, freshly per document (design 4.3)."""
    uniq: list[str] = []
    seen: set[str] = set()
    for n in names_in_order:
        k = n.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(k)
    keep = uniq[:MAX_ENTS_PER_DOC]
    rng = doc_rng(seed, doc_uid)
    codes = rng.sample(range(ENT_CODE_TRAIN_MAX + 1), len(keep))
    return {k: c for k, c in zip(keep, codes)}


# --------------------------------------------------------------------------------------
# Input units
# --------------------------------------------------------------------------------------

@dataclass
class Unit:
    uid: str
    source: str
    split: str                # "train" | "valid"
    kind: str                 # "parquet_stories" | "parquet_soda" | "text_eot" | "text_td"
    path: str
    start: int = 0            # byte offset (text) or row-group index (parquet)
    end: int = -1             # exclusive; -1 = to the end
    max_bytes: int = -1       # -1 = no cap; used by --sample-bytes


RAW_FILES = [
    # (outname, source, split, kind)
    ("simplestories_train-00000.parquet", "simplestories", "train", "parquet_stories"),
    ("simplestories_train-00001.parquet", "simplestories", "train", "parquet_stories"),
    ("simplestories_train-00002.parquet", "simplestories", "train", "parquet_stories"),
    ("simplestories_train-00003.parquet", "simplestories", "train", "parquet_stories"),
    ("simplestories_train-00004.parquet", "simplestories", "train", "parquet_stories"),
    ("simplestories_train-00005.parquet", "simplestories", "train", "parquet_stories"),
    ("simplestories_train-00006.parquet", "simplestories", "train", "parquet_stories"),
    ("simplestories_test-00000.parquet", "simplestories", "valid", "parquet_stories"),
    ("tinystoriesv2_gpt4_train.txt", "tinystories_v2", "train", "text_eot"),
    ("tinystoriesv2_gpt4_valid.txt", "tinystories_v2", "valid", "text_eot"),
    # Ages 2/5/10 only -- age 15 is dropped (design 1.3). The repo's *_ordered.txt files
    # are sorted by age but carry no age marker, so the per-age files unpacked from
    # individual_age_data.zip are what make the drop exact.
    ("tinydialogue_age-2_train.txt", "tinydialogues", "train", "text_td"),
    ("tinydialogue_age-5_train.txt", "tinydialogues", "train", "text_td"),
    ("tinydialogue_age-10_train.txt", "tinydialogues", "train", "text_td"),
    ("tinydialogue_age-2_val.txt", "tinydialogues", "valid", "text_td"),
    ("tinydialogue_age-5_val.txt", "tinydialogues", "valid", "text_td"),
    ("tinydialogue_age-10_val.txt", "tinydialogues", "valid", "text_td"),
    ("soda_train.parquet", "soda", "train", "parquet_soda"),
    ("soda_valid.parquet", "soda", "valid", "parquet_soda"),
]

TEXT_CHUNK_BYTES = 256 << 20       # split big .txt files into ~256 MiB units
PARQUET_ROWS_PER_UNIT = 50_000     # ~60 MB of story text, so units stay comparable


def _parquet_unit_ranges(md) -> list[tuple[int, int]]:
    """Unit row ranges, ALIGNED TO ROW-GROUP BOUNDARIES.

    A unit reads only the row groups it overlaps, so cutting inside a row group would
    make every unit of that group decompress the whole group. SODA ships its 1.19M
    dialogues as a *single* row group, so there it deliberately yields one unit rather
    than 24 units that each re-read 688 MB.
    """
    ranges: list[tuple[int, int]] = []
    start = 0
    pos = 0
    for i in range(md.num_row_groups):
        pos += md.row_group(i).num_rows
        if pos - start >= PARQUET_ROWS_PER_UNIT or i == md.num_row_groups - 1:
            if pos > start:
                ranges.append((start, pos))
            start = pos
    return ranges or [(0, md.num_rows)]


def build_units(raw_dir: Path, sample_bytes: int = -1) -> list[Unit]:
    import pyarrow.parquet as pq

    units: list[Unit] = []
    for name, source, split, kind in RAW_FILES:
        path = raw_dir / name
        if not path.exists():
            continue
        if kind.startswith("parquet"):
            try:
                md = pq.ParquetFile(path).metadata
            except Exception as exc:                                  # noqa: BLE001
                print(f"WARNING: skipping unreadable {path.name} ({exc}); "
                      f"a partial download will silently shrink this source",
                      file=sys.stderr)
                continue
            for a, b in _parquet_unit_ranges(md):
                units.append(Unit(
                    uid=f"{name}:r{a:09d}", source=source, split=split, kind=kind,
                    path=str(path), start=a, end=b))
        else:
            size = path.stat().st_size
            n = max(1, math.ceil(size / TEXT_CHUNK_BYTES))
            step = math.ceil(size / n)
            for i in range(n):
                units.append(Unit(
                    uid=f"{name}:b{i:04d}", source=source, split=split, kind=kind,
                    path=str(path), start=i * step, end=min((i + 1) * step, size)))

    if sample_bytes > 0:
        # Sample mode: the first unit of each input FILE, with the per-source budget
        # shared between that source's files, so every file is represented.
        first: dict[str, Unit] = {}
        for u in units:
            first.setdefault(u.path, u)
        keep = list(first.values())
        per_ss: Counter = Counter((u.source, u.split) for u in keep)
        for u in keep:
            budget = sample_bytes if u.split == "train" else max(1 << 20, sample_bytes // 8)
            u.max_bytes = max(1 << 18, budget // per_ss[(u.source, u.split)])
        units = keep
    return units


# --------------------------------------------------------------------------------------
# Document readers -- each yields (doc_uid, list_of_utterances, approx_raw_bytes)
# --------------------------------------------------------------------------------------

def _iter_parquet_rows(u: Unit, columns: list[str], batch: int = 2048):
    """Stream the unit's row range, decompressing only the row groups it touches."""
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(u.path)
    md = pf.metadata
    end = u.end if u.end >= 0 else md.num_rows
    offs = [0]
    for i in range(pf.num_row_groups):
        offs.append(offs[-1] + md.row_group(i).num_rows)
    groups = [i for i in range(pf.num_row_groups)
              if offs[i] < end and offs[i + 1] > u.start]
    if not groups:
        return
    pos = offs[groups[0]]
    for b in pf.iter_batches(batch_size=batch, columns=columns, row_groups=groups):
        n = b.num_rows
        lo, hi = max(u.start, pos), min(end, pos + n)
        if hi > lo:
            yield pos, b.slice(lo - pos, hi - lo)
        pos += n
        if pos >= end:
            return


def _iter_parquet_stories(u: Unit) -> Iterator[tuple[str, list[str], int]]:
    used = 0
    for base, b in _iter_parquet_rows(u, ["story"]):
        for j, s in enumerate(b.column("story").to_pylist()):
            if not s:
                continue
            n = len(s)
            yield (f"{u.uid}#{base + j}", [s], n)
            used += n
            if 0 <= u.max_bytes <= used:
                return


def _iter_parquet_soda(u: Unit) -> Iterator[tuple[str, list[str], int]]:
    used = 0
    for base, b in _iter_parquet_rows(u, ["dialogue"]):
        for j, turns in enumerate(b.column("dialogue").to_pylist()):
            if not turns:
                continue
            turns = [t for t in turns if t and t.strip()]
            if not turns:
                continue
            n = sum(len(t) for t in turns)
            yield (f"{u.uid}#{base + j}", turns, n)
            used += n
            if 0 <= u.max_bytes <= used:
                return


_EOT = "<|endoftext|>"


def _iter_text_eot(u: Unit) -> Iterator[tuple[str, list[str], int]]:
    """Plain text with documents separated by "<|endoftext|>".

    The separator may sit on a line of its own (TinyStories-V2) or at the end of a
    one-line document (TinyDialogues), so lines are split on it rather than tested.
    A unit that starts mid-file drops its first partial line and stops at the first
    document boundary at or past ``end``, so every byte belongs to exactly one unit.
    """
    used = 0
    idx = 0
    buf: list[str] = []

    def take(chunk: str):
        nonlocal idx, used
        buf.append(chunk)
        doc = "".join(buf).strip()
        del buf[:]
        if not doc:
            return None
        idx += 1
        used += len(doc)
        return (f"{u.uid}#{idx}", [doc], len(doc))

    with open(u.path, "r", encoding="utf-8", errors="replace") as fh:
        if u.start:
            fh.seek(u.start)
            fh.readline()               # drop the partial line at the chunk start
        while True:
            line = fh.readline()
            if not line:
                break
            if _EOT in line:
                pieces = line.split(_EOT)
                for pc in pieces[:-1]:
                    got = take(pc)
                    if got is not None:
                        yield got
                        if 0 <= u.max_bytes <= used:
                            return
                buf.append(pieces[-1])
                if u.end >= 0 and fh.tell() >= u.end:
                    return
            else:
                buf.append(line)
    got = take("")
    if got is not None:
        yield got


# TinyDialogues: one conversation per line, ended by "<|endoftext|>"; turns separated by a
# LITERAL backslash-n backslash-n (not a real newline); each turn prefixed by a markdown
# speaker tag such as "**Babysitter**:" or "**Child** (struggling to pull the wagon):".
# The speaker tag is stripped -- who is speaking is a flag in the thought (design 3.2),
# never text -- and the turn boundary survives as the <TURN> token.
# The ordered files carry NO age marker (they are only sorted by age), so ages 2/5/10 are
# selected by using the per-age files unpacked from individual_age_data.zip; see
# RAW_FILES and data/DATASET-SURVEY.md.
_TD_TURN_SEP = re.compile(r"\s*\\n\s*(?:\\n\s*)+")
_TD_SPEAKER = re.compile(r"^\s*\*{0,2}[^*:\n]{1,40}\*{0,2}\s*(?:\([^)]{0,120}\))?\s*:\s*")
TD_KEEP_AGES = (2, 5, 10)          # design 1.3: use ages 2/5/10, drop 15


def _split_td_turns(body: str) -> list[str]:
    turns = []
    for chunk in _TD_TURN_SEP.split(body):
        chunk = chunk.strip()
        if not chunk:
            continue
        chunk = _TD_SPEAKER.sub("", chunk, count=1).strip()
        if chunk:
            turns.append(chunk)
    return turns


def _iter_text_td(u: Unit) -> Iterator[tuple[str, list[str], int]]:
    for doc_uid, docs, _n in _iter_text_eot(u):
        turns = _split_td_turns(docs[0])
        if not turns:
            continue
        yield (doc_uid, turns, sum(len(t) for t in turns))


_READERS = {
    "parquet_stories": _iter_parquet_stories,
    "parquet_soda": _iter_parquet_soda,
    "text_eot": _iter_text_eot,
    "text_td": _iter_text_td,
}


def iter_documents(u: Unit) -> Iterator[tuple[str, list[str], int]]:
    return _READERS[u.kind](u)


def iter_sampled(units: Sequence[Unit], per_source_bytes: int
                 ) -> Iterator[tuple[str, str, list[str]]]:
    """Walk the units, stopping each SOURCE once it has given `per_source_bytes`.

    The budget is per source, not per unit: a source with 49 units would otherwise be
    read 49 times over, which at full scale means scanning the whole corpus to build a
    lexicon that only needs a slice of it.
    """
    used: Counter = Counter()
    for u in units:
        if used[u.source] >= per_source_bytes:
            continue
        got = 0
        for doc_uid, turns, nbytes in iter_documents(u):
            yield u.source, doc_uid, turns
            got += nbytes
            if used[u.source] + got >= per_source_bytes:
                break
        used[u.source] += got
        print(f"  {u.uid}: +{got/1e6:.1f} MB "
              f"({used[u.source]/1e6:.1f}/{per_source_bytes/1e6:.0f} MB for {u.source})",
              file=sys.stderr)


# --------------------------------------------------------------------------------------
# Stage: names (pass A)
# --------------------------------------------------------------------------------------

def stage_names(args) -> None:
    out = Path(args.out)
    units = build_units(Path(args.raw), args.sample_bytes)
    units = [u for u in units if u.split == "train"]
    budget = args.names_bytes

    cnt = WordCounts()
    t0 = time.time()
    for source, _uid, turns in iter_sampled(units, budget):
        simple_source = source in ("simplestories", "tinystories_v2")
        for turn in turns:
            for sent in split_sentences(turn):
                _count_sentence(sent, cnt, simple_source)

    # Name-hood is decided first, from capitalisation evidence only.
    names = set()
    for w, c in cnt.cap_noninitial.items():
        if c < NAME_MIN_NONINITIAL:
            continue
        if cnt.lower.get(w, 0) <= NAME_MAX_LOWER_RATIO * cnt.cap_total.get(w, 1):
            names.add(w)
    names -= NEVER_A_NAME

    # The word list and the simple list then count EVERY occurrence of a non-name,
    # whatever its capitalisation. Counting only lowercase occurrences (the first cut
    # of this code) silently lost "I", "I'm", "I've" and every word that mostly starts
    # a sentence, which then made the SODA filter reject almost everything.
    words = {w for w, c in cnt.total.items() if c >= WORD_LIST_MIN_COUNT} - names
    simple = {w for w, c in cnt.simple.items() if c >= SIMPLE_MIN_COUNT} - names

    lex = Lexicon(words=words, names=names, simple=simple)
    lex.save(out / "lexicon.json")
    write_json(out / "lexicon_meta.json", {
        "n_words": len(words), "n_names": len(names), "n_simple": len(simple),
        "n_word_types_seen": len(cnt.total),
        "sample_bytes": args.sample_bytes,
        "profile": "full" if args.sample_bytes < 0 else "sample",
        "names_bytes": budget,
        "seconds": round(time.time() - t0, 1),
        "thresholds": {
            "WORD_LIST_MIN_COUNT": WORD_LIST_MIN_COUNT,
            "NAME_MIN_NONINITIAL": NAME_MIN_NONINITIAL,
            "NAME_MAX_LOWER_RATIO": NAME_MAX_LOWER_RATIO,
            "SIMPLE_MIN_COUNT": SIMPLE_MIN_COUNT,
        },
        "names_sample": sorted(names)[:80],
    })
    print(f"names: {len(words)} words, {len(names)} names, {len(simple)} simple words "
          f"-> {out/'lexicon.json'}")


@dataclass
class WordCounts:
    total: Counter = field(default_factory=Counter)           # every occurrence
    lower: Counter = field(default_factory=Counter)           # written lower-case
    cap_total: Counter = field(default_factory=Counter)       # written capitalised
    cap_noninitial: Counter = field(default_factory=Counter)  # ... mid-sentence
    simple: Counter = field(default_factory=Counter)          # in the simple sources


def _count_sentence(sent: str, cnt: WordCounts, simple_source: bool) -> None:
    first = True
    for m in WORD_RE.finditer(sent):
        w = m.group(0)
        lw = w.lower()
        cnt.total[lw] += 1
        if simple_source:
            cnt.simple[lw] += 1
        if w[0].isupper():
            cnt.cap_total[lw] += 1
            if not first:
                cnt.cap_noninitial[lw] += 1
        else:
            cnt.lower[lw] += 1
        first = False


# --------------------------------------------------------------------------------------
# Stage: tokenizer
# --------------------------------------------------------------------------------------

BYTE_DECODER_NOTE = "GPT-2 bytes_to_unicode, see decode_numpy.py"


def bytes_to_unicode() -> dict[int, str]:
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) \
        + list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {b: chr(c) for b, c in zip(bs, cs)}


def stage_tokenizer(args) -> None:
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

    out = Path(args.out)
    lex = Lexicon.load(out / "lexicon.json")
    units = [u for u in build_units(Path(args.raw), args.sample_bytes) if u.split == "train"]
    budget = args.tokenizer_bytes

    def corpus() -> Iterator[str]:
        for _source, _uid, turns in iter_sampled(units, budget):
            for turn in turns:
                for sent in split_sentences(turn):
                    for kind, payload in segment_sentence(sent, lex):
                        if kind == "text":
                            t = payload.lower()
                            if t.strip():
                                yield t

    tok = Tokenizer(models.BPE(unk_token=None))
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=True)
    tok.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(
        vocab_size=VOCAB_SIZE,
        special_tokens=list(SPECIALS.keys()),
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
        show_progress=False,
        min_frequency=2,
    )
    t0 = time.time()
    tok.train_from_iterator(corpus(), trainer=trainer)
    secs = time.time() - t0

    # The trainer must have produced exactly our special ids.
    for piece, want in SPECIALS.items():
        got = tok.token_to_id(piece)
        if got != want:
            raise RuntimeError(f"special {piece!r} landed at id {got}, expected {want}")
    if tok.get_vocab_size() != VOCAB_SIZE:
        raise RuntimeError(f"vocab size {tok.get_vocab_size()} != {VOCAB_SIZE}")

    out.mkdir(parents=True, exist_ok=True)
    tok.save(str(out / "tokenizer.json"))
    export_plain_tokenizer(out)
    (out / "decode_numpy.py").write_text(DECODE_NUMPY_SRC, encoding="utf-8")
    meta = {
        "vocab_size": VOCAB_SIZE,
        "model": "ByteLevel BPE",
        "lowercase": True,
        "add_prefix_space": False,
        "specials": SPECIALS,
        "ent_code_pool": ENT_CODE_POOL,
        "ent_code_train_max": ENT_CODE_TRAIN_MAX,
        "ent_code_reserved_min": ENT_CODE_TRAIN_MAX + 1,
        "ent_none": ENT_NONE,
        "train_seconds": round(secs, 1),
        "train_bytes_budget": budget,
        "sample_bytes": args.sample_bytes,
        "profile": "full" if args.sample_bytes < 0 else "sample",
        "byte_alphabet": BYTE_DECODER_NOTE,
        "sha256": {
            "tokenizer.json": sha256_file(out / "tokenizer.json"),
            "tokenizer_vocab.json": sha256_file(out / "tokenizer_vocab.json"),
            "tokenizer_merges.txt": sha256_file(out / "tokenizer_merges.txt"),
            "decode_numpy.py": sha256_file(out / "decode_numpy.py"),
        },
    }
    write_json(out / "tokenizer_meta.json", meta)
    print(f"tokenizer: {VOCAB_SIZE} pieces in {secs:.1f}s -> {out/'tokenizer.json'}")


def export_plain_tokenizer(out: Path) -> None:
    """Write vocab.json + merges.txt so the GPU box needs no `tokenizers`."""
    tj = read_json(out / "tokenizer.json")
    vocab = tj["model"]["vocab"]
    merges = tj["model"].get("merges", [])
    write_json(out / "tokenizer_vocab.json", vocab)
    lines = ["#version: 0.2"]
    for m in merges:
        lines.append(m if isinstance(m, str) else " ".join(m))
    (out / "tokenizer_merges.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------
# Stage: encode (pass B) -- one part file per unit, resumable, parallel
# --------------------------------------------------------------------------------------

@dataclass
class DocBuffer:
    tokens: list[int] = field(default_factory=list)
    ents: list[int] = field(default_factory=list)
    sent_ends: list[int] = field(default_factory=list)
    overflow: int = 0          # names beyond MAX_ENTS_PER_DOC, left as ordinary words


class Encoder:
    def __init__(self, out: Path, seed: int):
        from tokenizers import Tokenizer
        self.tok = Tokenizer.from_file(str(out / "tokenizer.json"))
        self.lex = Lexicon.load(out / "lexicon.json")
        self.seed = seed

    def encode_document(self, doc_uid: str, turns: Sequence[str], multi_turn: bool
                        ) -> DocBuffer | None:
        """Encode one document; returns None if nothing survives the filters."""
        # 1. sentences, with their segments, and the document's name order
        per_sentence: list[tuple[bool, list[Segment]]] = []
        names_in_order: list[str] = []
        for turn in turns:
            first_in_turn = True
            for sent in split_sentences(turn):
                segs = segment_sentence(sent, self.lex)
                if not segs:
                    continue
                per_sentence.append((multi_turn and first_in_turn, segs))
                first_in_turn = False
                for kind, payload in segs:
                    if kind == "ent":
                        names_in_order.append(payload)
        if not per_sentence:
            return None

        codes = assign_codes(names_in_order, self.seed, doc_uid)

        # 2. encode every literal segment of every sentence in one batch call
        literals: list[str] = []
        for _turn_start, segs in per_sentence:
            for kind, payload in segs:
                if kind == "text":
                    literals.append(payload.lower())
        encoded = self.tok.encode_batch(literals, add_special_tokens=False) if literals else []

        buf = DocBuffer()
        it = iter(encoded)
        for turn_start, segs in per_sentence:
            s_tokens: list[int] = []
            s_ents: list[int] = []
            if turn_start:
                s_tokens.append(ID_TURN)
                s_ents.append(ENT_NONE)
            for kind, payload in segs:
                if kind == "text":
                    ids = next(it).ids
                    s_tokens.extend(ids)
                    s_ents.extend([ENT_NONE] * len(ids))
                else:
                    code = codes.get(payload.lower())
                    if code is None:
                        # beyond MAX_ENTS_PER_DOC: fall back to ordinary words
                        buf.overflow += 1
                        ids = self.tok.encode(payload.lower(), add_special_tokens=False).ids
                        s_tokens.extend(ids)
                        s_ents.extend([ENT_NONE] * len(ids))
                    else:
                        s_tokens.append(ID_ENT)
                        s_ents.append(code)
            if not s_tokens or len(s_tokens) > MAX_SENTENCE_TOKENS:
                continue
            buf.tokens.extend(s_tokens)
            buf.ents.extend(s_ents)
            buf.sent_ends.append(len(buf.tokens))
        if not buf.sent_ends:
            return None
        return buf


def soda_is_simple(turns: Sequence[str], lex: Lexicon) -> bool:
    """Design 1.3: keep a dialogue only if >= 98 % of its words are simple.

    Words that the name detector treats as names are excluded from the test -- they are
    going to be replaced by a placeholder anyway, so an unusual name must not disqualify
    an otherwise simple dialogue.
    """
    total = 0
    inside = 0
    for t in turns:
        for m in WORD_RE.finditer(t):
            w = m.group(0)
            if w[0].isupper() and is_name(w, lex):
                continue
            total += 1
            if w.lower() in lex.simple:
                inside += 1
    if total < SODA_MIN_WORDS:
        return False
    return inside >= SODA_SIMPLE_FRACTION * total


def encode_unit(job: tuple[dict, str, int]) -> dict:
    udict, out_s, seed = job
    u = Unit(**udict)
    out = Path(out_s)
    parts = out / "parts"
    parts.mkdir(parents=True, exist_ok=True)
    stem = parts / u.uid.replace("/", "_").replace(":", "_")
    meta_path = stem.with_suffix(".json")
    if meta_path.exists():
        try:
            m = read_json(meta_path)
            # Reuse a finished part ONLY if it was produced from exactly this unit and
            # this seed. A sample run caps `max_bytes` while keeping the same uid, so
            # without this check a full run would silently resume truncated parts.
            if (m.get("status") == "ok"
                    and m.get("schema_version") == SCHEMA_VERSION
                    and m.get("seed") == seed
                    and m.get("unit") == udict):
                m["resumed"] = True
                return m
            print(f"  part {u.uid}: stale ({'seed' if m.get('seed') != seed else 'unit'} "
                  f"changed), recomputing", file=sys.stderr)
        except Exception:
            pass

    enc = Encoder(out, seed)
    multi_turn = u.kind in ("parquet_soda", "text_td")
    tokens: list[int] = []
    ents: list[int] = []
    sents: list[int] = [0]
    docs: list[int] = [0]
    n_docs_in = 0
    n_docs_kept = 0
    n_soda_dropped = 0
    n_long_dropped = 0
    ent_overflow = 0
    t0 = time.time()
    raw_bytes = 0

    for doc_uid, turns, nbytes in iter_documents(u):
        n_docs_in += 1
        raw_bytes += nbytes
        if u.source == "soda" and not soda_is_simple(turns, enc.lex):
            n_soda_dropped += 1
            continue
        n_sent_before = sum(len(split_sentences(t)) for t in turns)
        buf = enc.encode_document(doc_uid, turns, multi_turn)
        if buf is None:
            continue
        n_long_dropped += max(0, n_sent_before - len(buf.sent_ends))
        if buf.overflow:
            ent_overflow += 1
        base = len(tokens)
        tokens.extend(buf.tokens)
        ents.extend(buf.ents)
        sents.extend(base + e for e in buf.sent_ends)
        docs.append(len(sents) - 1)
        n_docs_kept += 1

    tok_arr = np.asarray(tokens, dtype="<u2")
    ent_arr = np.asarray(ents, dtype="<u2")
    sen_arr = np.asarray(sents, dtype="<u4")
    doc_arr = np.asarray(docs, dtype="<u4")
    tok_arr.tofile(f"{stem}.tokens.u16")
    ent_arr.tofile(f"{stem}.ents.u16")
    sen_arr.tofile(f"{stem}.sents.u32")
    doc_arr.tofile(f"{stem}.docs.u32")

    meta = {
        "status": "ok", "schema_version": SCHEMA_VERSION, "unit": asdict(u),
        "stem": str(stem), "source": u.source, "split": u.split,
        "n_tokens": int(tok_arr.size), "n_sentences": int(sen_arr.size - 1),
        "n_documents": int(doc_arr.size - 1),
        "n_documents_in": n_docs_in, "n_documents_kept": n_docs_kept,
        "soda_dropped": n_soda_dropped, "dropped_long_sentences": n_long_dropped,
        "ent_overflow_docs": ent_overflow, "raw_bytes": raw_bytes,
        "seconds": round(time.time() - t0, 2), "seed": seed,
    }
    write_json(meta_path, meta)
    return meta


def stage_encode(args) -> None:
    out = Path(args.out)
    units = build_units(Path(args.raw), args.sample_bytes)
    jobs = [(asdict(u), str(out), args.seed) for u in units]
    t0 = time.time()
    results: list[dict] = []
    if args.workers <= 1:
        for j in jobs:
            results.append(encode_unit(j))
            _log_part(results[-1])
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            for m in ex.map(encode_unit, jobs):
                results.append(m)
                _log_part(m)
    tot_tok = sum(r["n_tokens"] for r in results)
    tot_raw = sum(r["raw_bytes"] for r in results)
    secs = time.time() - t0
    write_json(out / "encode_summary.json", {
        "units": len(results), "n_tokens": tot_tok, "raw_bytes": tot_raw,
        "wall_seconds": round(secs, 2), "workers": args.workers,
        "raw_bytes_per_second": round(tot_raw / max(secs, 1e-9), 1),
        "tokens_per_second": round(tot_tok / max(secs, 1e-9), 1),
        "parts": results,
    })
    print(f"encode: {tot_tok:,} tokens from {tot_raw/1e6:.1f} MB raw in {secs:.1f}s "
          f"({tot_raw/max(secs,1e-9)/1e6:.2f} MB/s with {args.workers} workers)")


def _log_part(m: dict) -> None:
    tag = " (resumed)" if m.get("resumed") else ""
    print(f"  part {m['unit']['uid']}: {m['n_tokens']:,} tok, "
          f"{m['n_documents']:,} docs{tag}", file=sys.stderr)


# --------------------------------------------------------------------------------------
# Stage: merge -- shuffle documents across parts into final shards
# --------------------------------------------------------------------------------------

class ShardWriter:
    def __init__(self, out: Path, split: str, cap: int, seed: int, tok_sha: str,
                 producer_sha: str):
        self.dir = out / split
        self.dir.mkdir(parents=True, exist_ok=True)
        self.split = split
        self.cap = cap
        self.seed = seed
        self.tok_sha = tok_sha
        self.producer_sha = producer_sha
        self.index = 0
        self.shards: list[dict] = []
        self._reset()

    def _reset(self) -> None:
        self.tokens: list[np.ndarray] = []
        self.ents: list[np.ndarray] = []
        self.sent_ends: list[int] = []
        self.doc_ends: list[int] = []
        self.n_tokens = 0
        self.source_counts: Counter = Counter()

    def add_doc(self, source: str, tok: np.ndarray, ent: np.ndarray,
                sent_ends_rel: np.ndarray) -> None:
        if self.n_tokens and self.n_tokens + tok.size > self.cap:
            self.flush()
        self.tokens.append(tok)
        self.ents.append(ent)
        base = self.n_tokens
        self.sent_ends.extend((sent_ends_rel + base).tolist())
        self.doc_ends.append(len(self.sent_ends))
        self.n_tokens += int(tok.size)
        self.source_counts[source] += int(tok.size)

    def flush(self) -> None:
        if not self.doc_ends:
            return
        stem = self.dir / f"{self.split}-{self.index:05d}"
        tok = np.concatenate(self.tokens).astype("<u2", copy=False)
        ent = np.concatenate(self.ents).astype("<u2", copy=False)
        sen = np.asarray([0] + self.sent_ends, dtype="<u4")
        doc = np.asarray([0] + self.doc_ends, dtype="<u4")
        assert sen[-1] == tok.size, (int(sen[-1]), int(tok.size))
        assert doc[-1] == sen.size - 1
        tok.tofile(f"{stem}.tokens.u16")
        ent.tofile(f"{stem}.ents.u16")
        sen.tofile(f"{stem}.sents.u32")
        doc.tofile(f"{stem}.docs.u32")
        meta = {
            "split": self.split, "index": self.index, "byte_order": "little",
            "schema_version": SCHEMA_VERSION,
            "n_tokens": int(tok.size), "n_sentences": int(sen.size - 1),
            "n_documents": int(doc.size - 1),
            "source_counts": {s: int(self.source_counts.get(s, 0)) for s in SOURCES},
            "sha256": {
                "tokens": sha256_file(f"{stem}.tokens.u16"),
                "ents": sha256_file(f"{stem}.ents.u16"),
                "sents": sha256_file(f"{stem}.sents.u32"),
                "docs": sha256_file(f"{stem}.docs.u32"),
            },
            "tokenizer_sha256": self.tok_sha, "producer_sha256": self.producer_sha,
            "seed": self.seed,
        }
        write_json(f"{stem}.json", meta)
        self.shards.append(meta | {"stem": str(stem)})
        print(f"  shard {stem.name}: {tok.size:,} tok, {sen.size-1:,} sents, "
              f"{doc.size-1:,} docs", file=sys.stderr)
        self.index += 1
        self._reset()


def _load_part(stem: str):
    """Memory-map the two big arrays; the two index arrays are small enough to read.

    The merge visits documents in a shuffled order across every part of a split at once,
    so the token arrays must not all be resident: at full scale they are ~4 GB together.
    """
    def mm(path: str, dtype: str):
        if os.path.getsize(path) == 0:
            return np.empty(0, dtype=dtype)
        return np.memmap(path, dtype=dtype, mode="r")

    tok = mm(f"{stem}.tokens.u16", "<u2")
    ent = mm(f"{stem}.ents.u16", "<u2")
    sen = np.fromfile(f"{stem}.sents.u32", dtype="<u4")
    doc = np.fromfile(f"{stem}.docs.u32", dtype="<u4")
    return tok, ent, sen, doc


def stage_merge(args) -> None:
    out = Path(args.out)
    summary = read_json(out / "encode_summary.json")
    tok_sha = read_json(out / "tokenizer_meta.json")["sha256"]["tokenizer.json"]
    producer_sha = sha256_file(__file__)

    by_split: dict[str, list[dict]] = {}
    for p in summary["parts"]:
        by_split.setdefault(p["split"], []).append(p)

    manifest = {"schema_version": SCHEMA_VERSION, "seed": args.seed,
                "tokenizer_sha256": tok_sha, "producer_sha256": producer_sha,
                "producer": str(Path(__file__).name), "splits": {}}

    for split, parts in sorted(by_split.items()):
        parts = sorted(parts, key=lambda p: p["unit"]["uid"])
        loaded = {}
        plan: list[tuple[int, int]] = []
        for pi, p in enumerate(parts):
            if p["n_documents"] == 0:
                continue
            loaded[pi] = _load_part(p["stem"])
            plan.extend((pi, di) for di in range(p["n_documents"]))
        rng = random.Random(f"{args.seed}|merge|{split}")
        rng.shuffle(plan)

        w = ShardWriter(out, split, args.shard_tokens, args.seed, tok_sha, producer_sha)
        for pi, di in plan:
            tok, ent, sen, doc = loaded[pi]
            s0, s1 = int(doc[di]), int(doc[di + 1])
            t0, t1 = int(sen[s0]), int(sen[s1])
            w.add_doc(parts[pi]["source"], tok[t0:t1], ent[t0:t1],
                      sen[s0 + 1:s1 + 1] - t0)
        w.flush()
        manifest["splits"][split] = w.shards

    write_json(out / "manifest.json", manifest)
    tot = sum(s["n_tokens"] for v in manifest["splits"].values() for s in v)
    print(f"merge: {tot:,} tokens across "
          f"{sum(len(v) for v in manifest['splits'].values())} shards -> {out/'manifest.json'}")


# --------------------------------------------------------------------------------------
# Stage: stats
# --------------------------------------------------------------------------------------

def stage_stats(args) -> None:
    out = Path(args.out)
    manifest = read_json(out / "manifest.json")
    meta = read_json(out / "tokenizer_meta.json")
    encsum = read_json(out / "encode_summary.json")

    per_source = Counter()
    hist = np.zeros(MAX_SENTENCE_TOKENS + 1, dtype=np.int64)
    id_seen = np.zeros(VOCAB_SIZE, dtype=bool)
    n_tokens = n_sent = n_docs = n_ent = 0

    for split, shards in manifest["splits"].items():
        for s in shards:
            stem = s["stem"]
            tok = np.fromfile(f"{stem}.tokens.u16", dtype="<u2")
            sen = np.fromfile(f"{stem}.sents.u32", dtype="<u4")
            ent = np.fromfile(f"{stem}.ents.u16", dtype="<u2")
            lens = np.diff(sen.astype(np.int64))
            hist += np.bincount(np.clip(lens, 0, MAX_SENTENCE_TOKENS),
                                minlength=MAX_SENTENCE_TOKENS + 1)
            id_seen[np.unique(tok)] = True
            n_tokens += int(tok.size)
            n_sent += int(lens.size)
            n_docs += int(s["n_documents"])
            n_ent += int((ent != ENT_NONE).sum())
            for k, v in s["source_counts"].items():
                per_source[f"{split}/{k}"] += v

    # vocabulary coverage at the word level, measured on a sample of the corpus
    cov = _word_coverage(out, args)

    stats = {
        "n_tokens": n_tokens, "n_sentences": n_sent, "n_documents": n_docs,
        "n_entity_placeholders": n_ent,
        "entity_fraction_of_tokens": round(n_ent / max(n_tokens, 1), 5),
        "mean_sentence_tokens": round(n_tokens / max(n_sent, 1), 2),
        "tokens_per_source": dict(sorted(per_source.items())),
        "sentence_length_histogram": {str(i): int(c) for i, c in enumerate(hist) if c},
        "vocab_ids_used": int(id_seen.sum()),
        "vocab_ids_total": VOCAB_SIZE,
        "vocab_id_coverage": round(float(id_seen.sum()) / VOCAB_SIZE, 4),
        "unused_ids": [int(i) for i in np.nonzero(~id_seen)[0][:64]],
        "word_coverage": cov,
        "encode_throughput": {
            "raw_bytes_per_second": encsum["raw_bytes_per_second"],
            "tokens_per_second": encsum["tokens_per_second"],
            "workers": encsum["workers"], "wall_seconds": encsum["wall_seconds"],
        },
        "tokenizer_sha256": meta["sha256"],
    }
    write_json(out / "stats.json", stats)
    (out / "stats.md").write_text(_stats_md(stats), encoding="utf-8")
    print(f"stats: {n_tokens:,} tokens, {n_sent:,} sentences -> {out/'stats.md'}")


def _word_coverage(out: Path, args) -> dict:
    """How much of the corpus' word vocabulary is one BPE piece."""
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(out / "tokenizer.json"))
    lex = Lexicon.load(out / "lexicon.json")
    units = [u for u in build_units(Path(args.raw), args.sample_bytes) if u.split == "train"]
    counts: Counter = Counter()
    budget = min(args.tokenizer_bytes, 20 << 20)
    for _source, _uid, turns in iter_sampled(units, budget):
        for t in turns:
            for m in WORD_RE.finditer(t):
                w = m.group(0)
                if w[0].isupper() and is_name(w, lex):
                    continue
                counts[w.lower()] += 1
    types = list(counts)
    if not types:
        return {}
    enc = tok.encode_batch([" " + w for w in types], add_special_tokens=False)
    single_types = 0
    single_occ = 0
    total_pieces = 0
    for w, e in zip(types, enc):
        total_pieces += len(e.ids) * counts[w]
        if len(e.ids) == 1:
            single_types += 1
            single_occ += counts[w]
    total_occ = sum(counts.values())
    return {
        "word_types": len(types),
        "word_occurrences": total_occ,
        "single_token_types": single_types,
        "single_token_type_fraction": round(single_types / len(types), 4),
        "single_token_occurrence_fraction": round(single_occ / total_occ, 4),
        "mean_pieces_per_word": round(total_pieces / total_occ, 4),
    }


def _stats_md(s: dict) -> str:
    L = ["# Reading-list statistics", "",
         f"- tokens: **{s['n_tokens']:,}**",
         f"- sentences: **{s['n_sentences']:,}** (mean {s['mean_sentence_tokens']} pieces)",
         f"- documents: **{s['n_documents']:,}**",
         f"- `<ENT>` placeholders: {s['n_entity_placeholders']:,} "
         f"({100*s['entity_fraction_of_tokens']:.2f} % of tokens)", "",
         "## Tokens per source", "", "| split/source | tokens |", "|---|---:|"]
    for k, v in s["tokens_per_source"].items():
        if v:
            L.append(f"| {k} | {v:,} |")
    L += ["", "## Sentence-length histogram (pieces)", "", "| len | sentences |", "|---:|---:|"]
    for k, v in sorted(s["sentence_length_histogram"].items(), key=lambda kv: int(kv[0])):
        L.append(f"| {k} | {v:,} |")
    c = s.get("word_coverage") or {}
    L += ["", "## Vocabulary coverage", "",
          f"- BPE ids actually used: {s['vocab_ids_used']} / {s['vocab_ids_total']} "
          f"({100*s['vocab_id_coverage']:.1f} %)"]
    if c:
        L += [f"- word types that are a single piece: {c['single_token_types']:,} / "
              f"{c['word_types']:,} ({100*c['single_token_type_fraction']:.1f} %)",
              f"- word *occurrences* that are a single piece: "
              f"{100*c['single_token_occurrence_fraction']:.1f} %",
              f"- mean pieces per word: {c['mean_pieces_per_word']}"]
    t = s["encode_throughput"]
    L += ["", "## Measured throughput", "",
          f"- {t['raw_bytes_per_second']/1e6:.2f} MB of raw text per second "
          f"with {t['workers']} worker(s)",
          f"- {t['tokens_per_second']:,.0f} tokens per second", ""]
    return "\n".join(L)


# --------------------------------------------------------------------------------------
# Stage: s0 -- the single smoke-test shard
# --------------------------------------------------------------------------------------

def stage_s0(args) -> None:
    """Copy the first train shard (truncated at a document boundary) into shards/s0/."""
    out = Path(args.out)
    manifest = read_json(out / "manifest.json")
    train = manifest["splits"].get("train") or []
    if not train:
        raise SystemExit("no train shards; run merge first")
    src = train[0]
    tok, ent, sen, doc = _load_part(src["stem"])
    cap = args.s0_tokens
    # largest document boundary whose token offset is <= cap
    doc_tok_end = sen[doc[1:]].astype(np.int64)
    n_docs = int(np.searchsorted(doc_tok_end, cap, side="right"))
    n_docs = max(1, min(n_docs, int(doc.size - 1)))
    s_end = int(doc[n_docs])
    t_end = int(sen[s_end])

    d = out / "s0"
    d.mkdir(parents=True, exist_ok=True)
    stem = d / "s0-00000"
    tok[:t_end].tofile(f"{stem}.tokens.u16")
    ent[:t_end].tofile(f"{stem}.ents.u16")
    sen[:s_end + 1].tofile(f"{stem}.sents.u32")
    doc[:n_docs + 1].tofile(f"{stem}.docs.u32")
    meta = {
        "split": "s0", "index": 0, "byte_order": "little",
        "schema_version": SCHEMA_VERSION,
        "n_tokens": t_end, "n_sentences": s_end, "n_documents": n_docs,
        "derived_from": src["stem"],
        "source_counts": {"mixed": t_end},
        "sha256": {
            "tokens": sha256_file(f"{stem}.tokens.u16"),
            "ents": sha256_file(f"{stem}.ents.u16"),
            "sents": sha256_file(f"{stem}.sents.u32"),
            "docs": sha256_file(f"{stem}.docs.u32"),
        },
        "tokenizer_sha256": src["tokenizer_sha256"],
        "producer_sha256": sha256_file(__file__), "seed": args.seed,
    }
    write_json(f"{stem}.json", meta)
    manifest["splits"]["s0"] = [meta | {"stem": str(stem)}]
    write_json(out / "manifest.json", manifest)
    print(f"s0: {t_end:,} tokens, {s_end:,} sentences, {n_docs:,} docs -> {stem}")


# --------------------------------------------------------------------------------------
# Stage: manifest for raw downloads
# --------------------------------------------------------------------------------------

def stage_manifest_raw(args) -> None:
    raw = Path(args.raw)
    files = []
    total = 0
    for p in sorted(raw.iterdir()):
        if p.name.startswith(".") or not p.is_file():
            continue
        size = p.stat().st_size
        total += size
        files.append({"name": p.name, "bytes": size, "sha256": sha256_file(p)})
        print(f"  {size:>14,}  {files[-1]['sha256'][:16]}  {p.name}", file=sys.stderr)
    write_json(raw.parent / "MANIFEST-raw.json",
               {"total_bytes": total, "n_files": len(files), "files": files})
    print(f"raw manifest: {len(files)} files, {total:,} bytes")


# --------------------------------------------------------------------------------------
# The numpy-only decoder that gets shipped to the GPU box
# --------------------------------------------------------------------------------------

DECODE_NUMPY_SRC = r'''"""Pure-Python/numpy decoder for the talker's byte-level BPE (ids -> text).

Written by scripts/fable_talker24_data.py. Needs only the standard library (numpy is
optional -- ids may be a list or any numpy integer array). The GPU box has torch+numpy
but no `tokenizers`, so this is the only decoder it needs.

    from decode_numpy import Decoder
    dec = Decoder("shards/tokenizer_vocab.json")
    dec.decode(ids)
    dec.decode(ids, ents=codes, names={7: "Mira"})
"""

import json

SPECIALS = {
    "<pad>": 0, "<bos>": 1, "<eos>": 2, "<unk>": 3, "<ENT>": 4, "<SUBJ>": 5,
    "<OBJ>": 6, "<OLD>": 7, "<TURN>": 8, "<DOC>": 9, "<extra_0>": 10, "<extra_1>": 11,
    "<extra_2>": 12, "<extra_3>": 13, "<extra_4>": 14, "<extra_5>": 15,
}
ENT_NONE = 0xFFFF
_INVISIBLE = {0, 1, 2, 3, 9}          # pad, bos, eos, unk, doc  -> ""
ID_ENT, ID_TURN = 4, 8
COPY_IDS = {5: "<SUBJ>", 6: "<OBJ>", 7: "<OLD>"}


def bytes_to_unicode():
    bs = (list(range(ord("!"), ord("~") + 1))
          + list(range(0xA1, 0xAC + 1)) + list(range(0xAE, 0xFF + 1)))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {b: chr(c) for b, c in zip(bs, cs)}


class Decoder:
    def __init__(self, vocab_path):
        with open(vocab_path, "r", encoding="utf-8") as fh:
            vocab = json.load(fh)
        size = max(vocab.values()) + 1
        self.id_to_piece = [""] * size
        for piece, i in vocab.items():
            self.id_to_piece[i] = piece
        self.byte_decoder = {v: k for k, v in bytes_to_unicode().items()}

    def piece_to_text(self, piece):
        return bytes(self.byte_decoder[c] for c in piece).decode("utf-8", errors="replace")

    def decode(self, ids, ents=None, names=None, copy=None,
               capitalize_sentences=False):
        """ids -> text. `ents[i]` supplies the entity code at an <ENT> position."""
        out = []
        buf = []                     # pending byte-level pieces

        def flush():
            if buf:
                out.append(self.piece_to_text("".join(buf)))
                del buf[:]

        for i, raw in enumerate(ids):
            t = int(raw)
            if t in _INVISIBLE:
                continue
            if t == ID_TURN:
                flush()
                out.append("\n")
                continue
            if t == ID_ENT:
                flush()
                code = int(ents[i]) if ents is not None else ENT_NONE
                if names is not None and code in names:
                    out.append(names[code])
                elif code != ENT_NONE:
                    out.append("<ent:%d>" % code)
                else:
                    out.append("<ENT>")
                continue
            if t in COPY_IDS:
                flush()
                out.append((copy or {}).get(t, COPY_IDS[t]))
                continue
            piece = self.id_to_piece[t] if t < len(self.id_to_piece) else ""
            buf.append(piece)
        flush()
        text = "".join(out)
        if capitalize_sentences:
            text = _capitalize(text)
        return text


def _capitalize(text):
    out = []
    start = True
    for ch in text:
        if start and ch.isalpha():
            out.append(ch.upper())
            start = False
        else:
            out.append(ch)
            if ch in ".!?\n":
                start = True
    return "".join(out)
'''


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

DEFAULT_ART = (Path(__file__).resolve().parents[1]
               / "artifacts" / "fable-talker24-20260920")


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("stage", choices=["survey", "names", "tokenizer", "encode", "merge",
                                     "stats", "s0", "manifest-raw", "all"])
    p.add_argument("--raw", default=str(DEFAULT_ART / "data" / "raw"))
    p.add_argument("--out", default=str(DEFAULT_ART / "shards"))
    p.add_argument("--seed", type=int, default=24)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--sample-bytes", type=int, default=-1,
                   help="read at most this many raw bytes per source (sample mode)")
    p.add_argument("--names-bytes", type=int, default=200 << 20,
                   help="raw bytes per source used to build the lexicon")
    p.add_argument("--tokenizer-bytes", type=int, default=200 << 20,
                   help="raw bytes per source used to train the BPE")
    p.add_argument("--shard-tokens", type=int, default=SHARD_TOKEN_CAP)
    p.add_argument("--s0-tokens", type=int, default=100_000_000)
    return p


def stage_survey(args) -> None:
    units = build_units(Path(args.raw), args.sample_bytes)
    for u in units:
        print(f"{u.source:16s} {u.split:6s} {u.kind:16s} {u.uid}"
              f"{'' if u.max_bytes < 0 else f'  cap={u.max_bytes}'}")
    print(f"{len(units)} units")


STAGES = {
    "survey": stage_survey, "names": stage_names, "tokenizer": stage_tokenizer,
    "encode": stage_encode, "merge": stage_merge, "stats": stage_stats,
    "s0": stage_s0, "manifest-raw": stage_manifest_raw,
}


def main(argv=None) -> int:
    args = make_parser().parse_args(argv)
    if args.stage == "all":
        for s in ("names", "tokenizer", "encode", "merge", "stats", "s0"):
            print(f"=== {s} ===")
            STAGES[s](args)
    else:
        STAGES[args.stage](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
