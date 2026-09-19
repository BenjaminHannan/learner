"""Step 1 tokenizer: byte-level BPE trained on village text, in pure Python.

Ids are laid out as [special tokens][256 bytes][merged pieces]. Text is split
on special tokens first (exact, case-sensitive matches that are never broken
up), the rest is optionally lowercased and pre-tokenized into words, and
merges never cross a word. A word keeps its leading space, but the space
merges only with the whole rest of the word: frequent words become one
" word" piece, while a rare or unseen name splits into the same pieces after
a space as at the start of a line. Every piece is a byte string, so any text
round-trips exactly after normalization: `decode(encode(text)) == normalize(text)`.

Training counts pairs once over a word-frequency table and updates only the
words that contain each merged pair. The most frequent pair wins; ties go to
the smallest (left piece, right piece) in byte order, so training is
deterministic. Two merges that spell the same bytes share one piece.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import codecs
import hashlib
import heapq
import json
from pathlib import Path
import re
from typing import Iterable, Optional, Sequence, Union

FORMAT = "learnlab.tokenizer"
VERSION = 1
DEFAULT_SPECIALS = (
    "<pad>", "<bos>", "<eos>", "<unk>",
    "[world]", "[teacher]", "[question]", "[answer]", "[feedback]",
    "[think]", "[/think]", "[done]", "[sleep]",
)
# Letters, single digits, runs of other symbols (each with one optional leading
# space), then whitespace. Together the alternatives match every character.
PATTERN = r" ?[^\W\d_]+| ?\d| ?(?:[^\s\w]|_)+|\s+(?!\S)|\s+"
BYTES = 256
SPACE = 0x20
_CACHE_LIMIT = 100_000


def _name_bytes(error: UnicodeDecodeError) -> tuple[str, int]:
    return "".join(f"<0x{byte:02X}>" for byte in error.object[error.start:error.end]), error.end


codecs.register_error("learnlab-byte-names", _name_bytes)


class Tokenizer:
    """A trained (or empty) BPE tokenizer; build one with `Tokenizer.train` or `Tokenizer.load`."""

    def __init__(
        self,
        merges: Sequence[tuple[bytes, bytes]] = (),
        specials: Sequence[str] = DEFAULT_SPECIALS,
        lowercase: bool = True,
        pattern: str = PATTERN,
        syllables: Sequence[str] = (),
    ) -> None:
        if len(set(specials)) != len(specials) or not all(specials):
            raise ValueError("special tokens must be distinct non-empty strings")
        if any(len(s) != 2 or not s.isalpha() or s != s.lower() for s in syllables):
            raise ValueError("name syllables must be two lowercase letters")
        # Made-up names are built from these syllables; any word made only of them is split into its
        # syllables before BPE, so a seen name and a fresh name always tokenize alike.
        self.syllables = tuple(sorted(set(syllables)))
        self._syllable_set = frozenset(self.syllables)
        self.specials = tuple(specials)
        self.lowercase = lowercase
        self.pattern = pattern
        self._words = re.compile(pattern)
        self._special_split = (
            re.compile("(" + "|".join(re.escape(s) for s in sorted(specials, key=len, reverse=True)) + ")")
            if specials else None
        )
        self._pieces: list[bytes] = [bytes([b]) for b in range(BYTES)]   # internal symbol -> bytes
        self._piece_id: dict[bytes, int] = {piece: i for i, piece in enumerate(self._pieces)}
        self._ranks: dict[tuple[int, int], tuple[int, int]] = {}         # pair -> (rank, merged symbol)
        self.merges: list[tuple[bytes, bytes]] = []
        for left, right in merges:
            self._add_merge(bytes(left), bytes(right))
        self._cache: dict[str, list[int]] = {}
        self._offset = len(self.specials)
        self._special_ids = {token: i for i, token in enumerate(self.specials)}
        self._tokens = list(self.specials) + [
            piece.decode("utf-8", "learnlab-byte-names") for piece in self._pieces
        ]
        self._ids = {token: i for i, token in reversed(list(enumerate(self._tokens)))}  # lowest id wins

    def _add_merge(self, left: bytes, right: bytes) -> int:
        """Record a merge and return its symbol (an existing one if the bytes are already a piece)."""
        a, b = self._piece_id.get(left), self._piece_id.get(right)
        if a is None or b is None:
            raise ValueError(f"merge {left!r} + {right!r} uses an unknown piece")
        if (a, b) in self._ranks:
            raise ValueError(f"duplicate merge {left!r} + {right!r}")
        merged = left + right
        symbol = self._piece_id.get(merged)
        if symbol is None:
            symbol = self._piece_id[merged] = len(self._pieces)
            self._pieces.append(merged)
        self._ranks[a, b] = (len(self.merges), symbol)
        self.merges.append((left, right))
        return symbol

    @classmethod
    def train(
        cls,
        texts: Iterable[str],
        vocab_size: int = 8000,
        specials: Sequence[str] = DEFAULT_SPECIALS,
        lowercase: bool = True,
        min_frequency: int = 2,
        syllables: Sequence[str] = (),
    ) -> Tokenizer:
        """Learn merges until `vocab_size` ids exist or no pair occurs `min_frequency` times."""
        tokenizer = cls((), specials, lowercase, syllables=syllables)
        if vocab_size < tokenizer.vocab_size:
            raise ValueError(f"vocab_size {vocab_size} is below the {tokenizer.vocab_size} fixed ids")
        counts: Counter[str] = Counter()
        for text in texts:
            for part, special in tokenizer._parts(text):
                if not special:
                    counts.update(tokenizer._split(part.lower() if lowercase else part))
        for syllable in tokenizer.syllables:  # every name syllable is one piece, however rare
            tokenizer._add_merge(syllable[:1].encode(), syllable[1:].encode())
        offset = tokenizer._offset
        words = [[i - offset for i in tokenizer._encode_word(word)] for word in counts]
        freqs = list(counts.values())
        pairs: dict[tuple[int, int], int] = defaultdict(int)
        where: dict[tuple[int, int], set[int]] = defaultdict(set)
        for index, (symbols, freq) in enumerate(zip(words, freqs)):
            for pair in _pairs(symbols):
                pairs[pair] += freq
                where[pair].add(index)
        pieces = tokenizer._pieces
        heap = [(-count, pieces[a], pieces[b], a, b) for (a, b), count in pairs.items()]
        heapq.heapify(heap)
        while heap and tokenizer.vocab_size < vocab_size:
            negative, _, _, a, b = heapq.heappop(heap)
            if pairs.get((a, b), 0) != -negative:
                continue  # stale entry; a fresh one was pushed when the count changed
            if -negative < min_frequency:
                break
            merged = tokenizer._add_merge(pieces[a], pieces[b])
            delta: dict[tuple[int, int], int] = defaultdict(int)
            for index in where.pop((a, b)):
                symbols, freq = words[index], freqs[index]
                out = _merge(symbols, a, b, merged)
                if len(out) == len(symbols):
                    continue  # the pair left this word in an earlier merge
                for pair in _pairs(symbols):
                    delta[pair] -= freq
                for pair in _pairs(out):
                    delta[pair] += freq
                    where[pair].add(index)
                words[index] = out
            for pair, change in delta.items():
                if change:
                    count = pairs[pair] + change
                    if count > 0:
                        pairs[pair] = count
                        heapq.heappush(heap, (-count, pieces[pair[0]], pieces[pair[1]], *pair))
                    else:
                        del pairs[pair]
        return cls(tokenizer.merges, specials, lowercase, syllables=syllables)  # rebuilt with the merges in the id tables

    @property
    def vocab_size(self) -> int:
        return len(self.specials) + len(self._pieces)

    def normalize(self, text: str) -> str:
        """The text `decode(encode(text))` returns: non-special parts lowercased if configured."""
        return "".join(
            part if special or not self.lowercase else part.lower() for part, special in self._parts(text)
        )

    def encode(self, text: str) -> list[int]:
        ids: list[int] = []
        for part, special in self._parts(text):
            if special:
                ids.append(self._special_ids[part])
                continue
            if self.lowercase:
                part = part.lower()
            for word in self._split(part):
                cached = self._cache.get(word)
                if cached is None:
                    if len(self._cache) >= _CACHE_LIMIT:
                        self._cache.clear()
                    cached = self._cache[word] = self._encode_word(word)
                ids.extend(cached)
        return ids

    def encode_batch(self, texts: Iterable[str]) -> list[list[int]]:
        return [self.encode(text) for text in texts]

    def decode(self, ids: Iterable[int]) -> str:
        """Join the pieces; bytes that do not form valid UTF-8 become U+FFFD."""
        out = bytearray()
        size, offset = self.vocab_size, self._offset
        for index in ids:
            if not 0 <= index < size:
                raise ValueError(f"token id {index} is outside 0..{size - 1}")
            if index < offset:
                out += self.specials[index].encode("utf-8")
            else:
                out += self._pieces[index - offset]
        return out.decode("utf-8", "replace")

    def token_to_id(self, token: str) -> int:
        """Id of a special token or piece, spelled as `id_to_token` spells it."""
        return self._ids[token]

    def id_to_token(self, index: int) -> str:
        """The special token, or the piece as text with bytes that are not UTF-8 on their own as <0xNN>."""
        if not 0 <= index < self.vocab_size:
            raise ValueError(f"token id {index} is outside 0..{self.vocab_size - 1}")
        return self._tokens[index]

    def _parts(self, text: str) -> Iterable[tuple[str, bool]]:
        """(segment, is_special) pairs, specials matched exactly before any normalization."""
        if self._special_split is None:
            yield text, False
            return
        for position, part in enumerate(self._special_split.split(text)):
            if part:
                yield part, position % 2 == 1

    def _split(self, part: str) -> list[str]:
        """Pre-tokenized words, with name-like words (two or more known syllables) split into syllables."""
        words = self._words.findall(part)
        if not self._syllable_set:
            return words
        out: list[str] = []
        for word in words:
            core = word[1:] if word.startswith(" ") else word
            chunks = [core[i:i + 2] for i in range(0, len(core), 2)]
            if len(core) >= 4 and len(core) % 2 == 0 and all(c in self._syllable_set for c in chunks):
                if core is not word:
                    out.append(" ")
                out.extend(chunks)
            else:
                out.append(word)
        return out

    def _encode_word(self, word: str) -> list[int]:
        symbols = list(word.encode("utf-8"))
        ranks = self._ranks
        while len(symbols) > 1:
            best: Optional[tuple[int, int]] = None
            pair: Optional[tuple[int, int]] = None
            for candidate in _pairs(symbols):
                found = ranks.get(candidate)
                if found is not None and (best is None or found < best):
                    best, pair = found, candidate
            if pair is None:
                break
            symbols = _merge(symbols, pair[0], pair[1], best[1])
        return [symbol + self._offset for symbol in symbols]

    def payload(self) -> dict:
        return {
            "format": FORMAT,
            "version": VERSION,
            "lowercase": self.lowercase,
            "pattern": self.pattern,
            "specials": list(self.specials),
            "merges": [[left.decode("latin-1"), right.decode("latin-1")] for left, right in self.merges],
            **({"syllables": list(self.syllables)} if self.syllables else {}),
        }

    @property
    def digest(self) -> str:
        """SHA-256 of the canonical payload; equal digests mean identical encoding."""
        canonical = json.dumps(self.payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def to_json(self) -> str:
        return json.dumps({**self.payload(), "sha256": self.digest}, ensure_ascii=True, indent=1)

    @classmethod
    def from_json(cls, text: str) -> Tokenizer:
        """Parse saved JSON; raise ValueError if it is malformed, another version, or fails its digest."""
        try:
            data = json.loads(text)
            if data.get("format") != FORMAT or data.get("version") != VERSION:
                raise ValueError(f"not a {FORMAT} v{VERSION} file")
            tokenizer = cls(
                [(left.encode("latin-1"), right.encode("latin-1")) for left, right in data["merges"]],
                data["specials"],
                data["lowercase"],
                data["pattern"],
                syllables=data.get("syllables", ()),
            )
        except (AttributeError, KeyError, TypeError, ValueError, re.error) as error:
            raise ValueError(f"bad tokenizer file: {error}") from None
        if data.get("sha256") != tokenizer.digest:
            raise ValueError("tokenizer digest mismatch")
        return tokenizer

    def save(self, path: Union[str, Path]) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Union[str, Path]) -> Tokenizer:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


def _pairs(symbols: list[int]) -> Iterable[tuple[int, int]]:
    """Adjacent pairs that may merge; a leading space may join only the whole rest of its word."""
    start = 1 if len(symbols) > 2 and symbols[0] == SPACE else 0
    return zip(symbols[start:], symbols[start + 1:])


def _merge(symbols: list[int], a: int, b: int, merged: int) -> list[int]:
    """Replace each non-overlapping (a, b) that `_pairs` allows, left to right, with `merged`."""
    out: list[int] = symbols[:1] if len(symbols) > 2 and symbols[0] == SPACE else []
    i, last = len(out), len(symbols) - 1
    while i <= last:
        if i < last and symbols[i] == a and symbols[i + 1] == b:
            out.append(merged)
            i += 2
        else:
            out.append(symbols[i])
            i += 1
    return out
