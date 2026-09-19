"""Step 1 tokenizer: exact round trips, atomic specials, deterministic training, save/load, syllable names."""
from __future__ import annotations

import json
from pathlib import Path
import random
import re
import sys
import tempfile
import time
import unittest

from learnlab.tokenizer import BYTES, DEFAULT_SPECIALS, PATTERN, Tokenizer

SYLLABLES = ("ba", "ke", "lo", "mi", "nu", "ra", "si", "to", "ve", "zo", "da", "fe", "gi", "ho", "ju", "pa")  # as learnlab.toy
OBJECTS = ("cup", "key", "coin", "book", "rope", "lamp", "bell", "comb")
PLACES = ("barn", "mill", "shed", "well", "hut", "loft", "yard", "pond")
TEMPLATES = (
    "{name} keeps the {obj} in the {place}.",
    "The {obj} of {name} is kept in the {place}.",
    "Where does {name} keep the {obj}? [answer] the {place} [done]",
    "[teacher] {name} hides the {obj} inside the {place}.",
    "[think] {name} left the {obj} at the {place}. [/think]",
)
SYLLABLE_PIECE = re.compile("(?:" + "|".join(SYLLABLES) + ")+")
NAMES = sorted({a + b + c for a in SYLLABLES for b in SYLLABLES for c in SYLLABLES if len({a, b, c}) == 3})
HELD_OUT = frozenset(random.Random(7).sample(NAMES, 60))
SAMPLES = (
    "",
    "Nera keeps the cup in the mill.",
    "  leading and trailing spaces  ",
    "tabs\tand\nnew\r\nlines\n\n\n",
    "Crème brûlée, naïve café, Straße, İstanbul, ǅemal",
    "日本語のテキスト 与 中文 and 한국어",
    "emoji 😀👍🏽 and flags 🇬🇧 plus zero\u200bwidth joiner 👩\u200d💻",
    "combining e\u0301 and a\u0308, math ∑∫√ and ½ ² ³",
    "right-to-left שלום مرحبا",
    "snake_case __dunder__ x_1 3.14159 1,000,000 -42",
    "[world] [teacher] Where is it? [question] [answer] barn [feedback] [think]hm[/think] [done] [sleep]",
    "<pad><bos>glued<eos><unk>[think]x[/think]",
    "[World] [THINK] <PAD> [thin k] [[think]] <0xC3> literal",
    "control \x00\x01\x7f chars and \ufeff bom",
)


def toy_corpus(lines: int, seed: int = 0) -> list[str]:
    """Toy-style village text; every name has three distinct syllables and none is held out."""
    rng = random.Random(seed)
    seen = [name for name in NAMES if name not in HELD_OUT]
    out = []
    for _ in range(lines):
        name = rng.choice(seen)
        out.append(rng.choice(TEMPLATES).format(
            name=name.capitalize() if rng.random() < 0.5 else name, obj=rng.choice(OBJECTS), place=rng.choice(PLACES),
        ))
    return out


def diverse_corpus(nbytes: int, seed: int = 1) -> list[str]:
    """Pseudo-words from 95 syllables, almost all distinct: a hard case for the word table."""
    rng = random.Random(seed)
    syllables = [c + v for c in "bcdfghjklmnprstvwz" for v in "aeiou"] + list("aeiou")
    lines, size = [], 0
    while size < nbytes:
        words = ("".join(rng.choices(syllables, k=rng.randint(1, 5))) for _ in range(rng.randint(4, 14)))
        line = " ".join(words).capitalize() + rng.choice(".?!,")
        lines.append(line)
        size += len(line) + 1
    return lines


def naive_merges(texts: list[str], merges: int, lowercase: bool) -> list[tuple[bytes, bytes]]:
    """Reference BPE that recounts every pair before each merge (same rules, no incremental counts)."""
    counts: dict[str, int] = {}
    for text in texts:
        for part in re.split("(" + "|".join(map(re.escape, DEFAULT_SPECIALS)) + ")", text)[::2]:
            for word in re.findall(PATTERN, part.lower() if lowercase else part):
                counts[word] = counts.get(word, 0) + 1
    words = {tuple(bytes([b]) for b in word.encode()): freq for word, freq in counts.items()}
    out = []
    for _ in range(merges):
        pairs: dict[tuple[bytes, bytes], int] = {}
        for word, freq in words.items():
            start = 1 if len(word) > 2 and word[0] == b" " else 0
            for pair in zip(word[start:], word[start + 1:]):
                pairs[pair] = pairs.get(pair, 0) + freq
        if not pairs or max(pairs.values()) < 2:
            break
        best = min(pairs, key=lambda pair: (-pairs[pair], pair))
        out.append(best)
        merged = {}
        for word, freq in words.items():
            start = 1 if len(word) > 2 and word[0] == b" " else 0
            new, i = list(word[:start]), start
            while i < len(word):
                if word[i:i + 2] == best:
                    new.append(best[0] + best[1])
                    i += 2
                else:
                    new.append(word[i])
                    i += 1
            merged[tuple(new)] = merged.get(tuple(new), 0) + freq
        words = merged
    return out


def random_text(rng: random.Random, length: int) -> str:
    """Arbitrary Unicode scalar values (no surrogates), weighted towards ASCII and whitespace."""
    chars = []
    for _ in range(length):
        roll = rng.random()
        if roll < 0.5:
            chars.append(chr(rng.randint(0x20, 0x7E)))
        elif roll < 0.6:
            chars.append(rng.choice(" \t\n\r\x0b\x0c\u00a0\u3000"))
        else:
            point = rng.randint(0, 0x10FFFF)
            chars.append(chr(point) if not 0xD800 <= point <= 0xDFFF else "?")
    return "".join(chars)


class TokenizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = toy_corpus(6000)
        cls.tok = Tokenizer.train(cls.corpus + list(SAMPLES), vocab_size=1200)
        cls.cased = Tokenizer.train(cls.corpus + list(SAMPLES), vocab_size=1200, lowercase=False)

    def test_round_trip_is_exact_after_normalization(self):
        rng = random.Random(3)
        texts = list(SAMPLES) + self.corpus[:200] + [random_text(rng, rng.randint(0, 80)) for _ in range(300)]
        for text in texts:
            with self.subTest(text=text[:40]):
                self.assertEqual(self.tok.decode(self.tok.encode(text)), self.tok.normalize(text))
                self.assertEqual(self.tok.normalize(text), text.lower())
                self.assertEqual(self.cased.decode(self.cased.encode(text)), text)
        self.assertEqual(self.tok.encode(""), [])
        self.assertEqual(self.tok.encode_batch(texts[:20]), [self.tok.encode(text) for text in texts[:20]])
        with self.assertRaises(ValueError):
            self.tok.decode([self.tok.vocab_size])
        with self.assertRaises(ValueError):
            self.tok.decode([-1])

    def test_special_tokens_are_atomic_first_and_stable(self):
        for tok in (self.tok, self.cased, Tokenizer()):
            self.assertEqual([tok.id_to_token(i) for i in range(len(DEFAULT_SPECIALS))], list(DEFAULT_SPECIALS))
            for index, special in enumerate(DEFAULT_SPECIALS):
                self.assertEqual(tok.token_to_id(special), index)
                self.assertEqual(tok.encode(special), [index])
                self.assertEqual(tok.encode(f"x{special}y"), tok.encode("x") + [index] + tok.encode("y"))
        # Specials in the training text are cut out first, so no learned piece contains or is one.
        for index in range(len(DEFAULT_SPECIALS), self.tok.vocab_size):
            piece = self.tok.decode([index])
            self.assertFalse(any(special in piece for special in DEFAULT_SPECIALS), piece)
        # Matches are exact: case variants and broken-up specials are ordinary text.
        ids = self.cased.encode("[THINK] [thin k] <Pad>")
        self.assertFalse(set(ids) & set(range(len(DEFAULT_SPECIALS))))
        custom = Tokenizer.train(["[B] hello <a> world"] * 5, vocab_size=400, specials=("<a>", "[B]", "[b]"))
        self.assertEqual([custom.id_to_token(i) for i in range(3)], ["<a>", "[B]", "[b]"])
        self.assertEqual(custom.encode("[B][b]<a>"), [1, 2, 0])
        self.assertEqual(custom.decode(custom.encode("[B] Hi")), "[B] hi")
        with self.assertRaises(ValueError):
            Tokenizer(specials=("<a>", "<a>"))

    def test_vocabulary_layout_and_word_boundaries(self):
        tok = self.tok
        self.assertEqual(tok.vocab_size, len(DEFAULT_SPECIALS) + BYTES + len(tok.merges))
        self.assertLessEqual(tok.vocab_size, 1200)
        words = re.compile(PATTERN)
        for index in range(tok.vocab_size):
            token = tok.id_to_token(index)
            self.assertEqual(tok.token_to_id(token), index)
            if index >= len(DEFAULT_SPECIALS) + BYTES and "<0x" not in token:
                self.assertEqual(words.findall(token), [token], "a merge crossed a word boundary")
        self.assertEqual(tok.encode(" the"), [tok.token_to_id(" the")])   # frequent words keep their space

    def test_training_is_deterministic_and_breaks_ties_lexicographically(self):
        again = Tokenizer.train(self.corpus + list(SAMPLES), vocab_size=1200)
        shuffled = self.corpus + list(SAMPLES)
        random.Random(5).shuffle(shuffled)
        reordered = Tokenizer.train(shuffled, vocab_size=1200)
        self.assertEqual(again.merges, self.tok.merges)
        self.assertEqual(reordered.merges, self.tok.merges)
        self.assertEqual(again.digest, self.tok.digest)
        base = len(DEFAULT_SPECIALS) + BYTES
        tied = Tokenizer.train(["xy", "ab", "cd"], vocab_size=base + 3, min_frequency=1)
        self.assertEqual(tied.merges, [(b"a", b"b"), (b"c", b"d"), (b"x", b"y")])
        frequent = Tokenizer.train(["xy", "xy", "ab"], vocab_size=base + 3, min_frequency=1)
        self.assertEqual(frequent.merges, [(b"x", b"y"), (b"a", b"b")])
        self.assertEqual(Tokenizer.train(["xy", "xy", "ab"], vocab_size=base + 3).merges, [(b"x", b"y")])
        with self.assertRaises(ValueError):
            Tokenizer.train(["xy"], vocab_size=base - 1)

    def test_incremental_counts_match_a_naive_recount(self):
        texts = self.corpus[:400] + list(SAMPLES) + ["    indented\n        twice   ", "aaaa aaa aa a"] * 3
        for lowercase in (True, False):
            fast = Tokenizer.train(texts, vocab_size=len(DEFAULT_SPECIALS) + BYTES + 250, lowercase=lowercase)
            self.assertEqual(len(fast.merges), 250)
            self.assertEqual(fast.merges, naive_merges(texts, 250, lowercase))

    def test_save_and_load_encode_identically(self):
        rng = random.Random(9)
        texts = list(SAMPLES) + self.corpus[:300] + [random_text(rng, 60) for _ in range(100)]
        for tok in (self.tok, self.cased):
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "tokenizer.json"
                tok.save(path)
                loaded = Tokenizer.load(path)
                saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["version"], 1)
            self.assertEqual(saved["sha256"], tok.digest)
            self.assertEqual(loaded.digest, tok.digest)
            self.assertEqual((loaded.merges, loaded.specials, loaded.lowercase), (tok.merges, tok.specials, tok.lowercase))
            self.assertEqual(loaded.encode_batch(texts), tok.encode_batch(texts))
            self.assertEqual([loaded.id_to_token(i) for i in range(tok.vocab_size)],
                             [tok.id_to_token(i) for i in range(tok.vocab_size)])
            tampered = dict(saved, merges=saved["merges"][:-1])
            with self.assertRaisesRegex(ValueError, "digest"):
                Tokenizer.from_json(json.dumps(tampered))
            for bad in (json.dumps(dict(saved, version=2)), "[]", "{", json.dumps(dict(saved, merges=[["a"]]))):
                with self.assertRaises(ValueError):
                    Tokenizer.from_json(bad)

    def test_unseen_names_split_into_syllable_pieces(self):
        training_text = " ".join(self.corpus).lower()
        pieces_per_name = []
        for name in sorted(HELD_OUT):
            self.assertNotIn(name, training_text)
            alone = [self.tok.id_to_token(i) for i in self.tok.encode(name)]
            with self.subTest(name=name, pieces=alone):
                self.assertTrue(all(SYLLABLE_PIECE.fullmatch(piece) for piece in alone), alone)   # syllable-aligned
                self.assertGreater(len(alone), 1)                                                 # not memorised
                self.assertEqual("".join(alone), name)
                # The same pieces wherever the name stands: after a space, capitalized, or mid-sentence.
                self.assertEqual(self.tok.encode(" " + name), self.tok.encode(" ") + self.tok.encode(name))
                self.assertEqual(self.tok.encode(name.capitalize()), self.tok.encode(name))
                sentence = self.tok.encode(f"Where does {name.capitalize()} keep the cup?")
                spaced = self.tok.encode(" " + name)
                self.assertTrue(any(sentence[i:i + len(spaced)] == spaced for i in range(len(sentence))))
            pieces_per_name.append(len(alone))
        print(f"\n  unseen names: {sum(pieces_per_name) / len(pieces_per_name):.2f} pieces per 3-syllable name, "
              f"e.g. {[self.tok.id_to_token(i) for i in self.tok.encode(sorted(HELD_OUT)[0])]}", file=sys.stderr)

    def test_training_speed_on_one_megabyte(self):
        corpus = diverse_corpus(1_000_000)
        started = time.perf_counter()
        tok = Tokenizer.train(corpus, vocab_size=8000)
        seconds = time.perf_counter() - started
        megabytes = sum(len(line) + 1 for line in corpus) / 1e6
        print(f"\n  trained {len(tok.merges)} merges (vocab {tok.vocab_size}) on {megabytes:.2f} MB "
              f"in {seconds:.1f} s", file=sys.stderr)
        self.assertEqual(tok.vocab_size, 8000)
        self.assertLess(seconds, 120)


if __name__ == "__main__":
    unittest.main()
