"""Premonition-mini names as pointers and the visit cache (design/06 §7 tests 1, 3 and 5; build step 2)."""
from __future__ import annotations

import json
from pathlib import Path
import random
import tempfile
import unittest

import torch

from learnlab import step1
from learnlab.leaks import normalize
from learnlab.tokenizer import Tokenizer
from memorylab.storage import Budget
from premonition import data
from premonition.batch import MAX_ANSWER, MAX_GOLD, N_ENT, PAD_ID, NameTable
from premonition.pointer import (WORD, NameDetector, NameOverflow, answer_text, detokenise, pointerize,
                                 pointerize_lines, random_order, restored)

TARGET = 0.999   # design/06 build step 2: detector precision and recall against the cast lists


def village():
    """(registry, pattern source), or skip when the village simulator is not importable."""
    try:
        from learnlab.village.render import PatternSource, village_registry
        from learnlab.village.scheduler import world_families
    except ImportError as error:
        raise unittest.SkipTest(f"village simulator not available: {error}")
    source = PatternSource.load()
    return village_registry(source, world_families()), source


class NameDetectorTest(unittest.TestCase):
    """Test 1: the detector against the true cast lists (Village.people + village name), with exact round trips."""

    @classmethod
    def setUpClass(cls) -> None:
        from learnlab.village.names import SYLLABLES
        from learnlab.village.shards import world_visit
        from learnlab.village.stream import render_visit
        registry, source = village()

        def visits(split, indices):
            out = []
            for index in indices:
                visit = world_visit(split, index, seed=0, registry=registry)
                out.append((visit, render_visit(visit, source, registry)))
            return out

        fit = visits("train", range(120))
        texts = [rendered.text for _, rendered in fit]
        cls.detector = NameDetector.fit(texts, source.text.values())
        cls.tokenizer = Tokenizer.train(texts, vocab_size=1200, syllables=SYLLABLES)
        # Fresh visits of every split: held-out names never reach the fitted text.
        cls.checked = visits("train", range(5000, 5040)) + visits("validation", range(40)) + visits("test", range(40))

    def test_precision_and_recall_against_the_cast_lists(self) -> None:
        hits = misses = false = 0
        for visit, rendered in self.checked:
            cast = set(visit["people"]) | {visit["village"]}
            for match in WORD.finditer(rendered.text):
                found, true = self.detector.is_name(match.group()), match.group() in cast
                hits += found and true
                false += found and not true
                misses += true and not found
            self.assertLessEqual(len(self.detector.names(rendered.text)), N_ENT, visit["id"])
        precision, recall = hits / (hits + false), hits / (hits + misses)
        self.assertGreater(hits, 1000)
        self.assertGreaterEqual(precision, TARGET, f"precision {precision:.5f} ({false} false names)")
        self.assertGreaterEqual(recall, TARGET, f"recall {recall:.5f} ({misses} missed)")

    def test_no_pool_name_is_ever_blocked(self) -> None:
        from learnlab.village.names import all_names
        self.assertEqual([name for name in all_names() if not self.detector.is_name(name)], [])

    def test_round_trip_is_exact(self) -> None:
        tokenizer, detector = self.tokenizer, self.detector
        rng = random.Random(0)
        for visit, rendered in self.checked:
            ids, table = pointerize_lines(rendered.lines, tokenizer, detector)
            flat = [i for line in ids for i in line]
            text = rendered.text + "\n"
            self.assertEqual(detokenise(flat, table, tokenizer), restored(text, tokenizer, detector))
            self.assertEqual(normalize(detokenise(flat, table, tokenizer)), normalize(text))
            self.assertEqual(list(table.spellings.values()), detector.names(text))
            self.assertLessEqual(set(table.spellings.values()), set(visit["people"]) | {visit["village"]})
            # Only a name's own pieces change: everything else is the tokenizer's encoding.
            plain = [i for i in flat if i < tokenizer.vocab_size]
            self.assertEqual(tokenizer.decode(plain), "".join(
                "" if is_name else tokenizer.normalize(part) for part, is_name in detector.split(text)))
            shuffled, other = pointerize(text, tokenizer, detector, order=random_order(rng))
            self.assertEqual(detokenise(shuffled, other, tokenizer), restored(text, tokenizer, detector))
            self.assertEqual(sorted(other.spellings.values()), sorted(table.spellings.values()))

    def test_detector_file_round_trip_and_capacity(self) -> None:
        again = NameDetector.from_json(self.detector.to_json())
        self.assertEqual(again.digest, self.detector.digest)
        tampered = json.loads(self.detector.to_json())
        tampered["lowercase"] = tampered["lowercase"][1:]
        with self.assertRaises(ValueError):
            NameDetector.from_json(json.dumps(tampered))
        crowd = [f"Zyx{chr(ord('a') + i)}" for i in range(N_ENT + 1)]
        self.assertEqual(self.detector.names(" ".join(crowd)), crowd)
        pointerize(" ".join(crowd[:N_ENT]), self.tokenizer, self.detector)
        with self.assertRaises(NameOverflow):
            pointerize(" ".join(crowd), self.tokenizer, self.detector)

    def test_rule_details(self) -> None:
        detector = NameDetector.fit(["[world] the kites are here.", "[world] Kelo met Rami."],
                                    ["Hmm, {fact}", "Tell me: where is {person}?"], vocabulary=())
        self.assertEqual(detector.names("Hmm, Kelo's kite. Tell Rami. The Kites met Kelo and Zuva."),
                         ["Kelo", "Rami", "Zuva"])
        self.assertTrue(detector.is_name("Rami"))
        self.assertFalse(detector.is_name("Kites"))    # seen lowercase
        self.assertFalse(detector.is_name("Hmm"))      # a literal template word
        self.assertFalse(detector.is_name("rami"))     # not capitalised
        self.assertFalse(NameDetector.fit([]).is_name("Kites"))   # the closed village vocabulary


class VisitCacheTest(unittest.TestCase):
    """The cache and collator on real village shards (tests 3 and 5 of design/06 §7)."""

    @classmethod
    def setUpClass(cls) -> None:
        from learnlab.village.names import SYLLABLES
        from learnlab.village.shards import write_shards
        village()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        for split, count in (("train", 40), ("validation", 30)):
            write_shards(split, count, cls.root / "d", 1, seed=0, visits_per_shard=16, verbose=False)
        texts = [text.read_text(encoding="utf-8") for text, _ in step1.shard_files(cls.root / "d" / "train")]
        cls.tokenizer = Tokenizer.train(texts, vocab_size=1200, syllables=SYLLABLES)
        cls.detector = data.fit_detector(cls.root / "d" / "train")
        cls.cache = data.build_cache(cls.root / "d" / "validation", cls.tokenizer, cls.detector)
        cls.questions = {q.id: q for text, meta in step1.shard_files(cls.root / "d" / "validation")
                         for q in step1.read_questions(text, meta, "validation")}
        cls.batch = data.collate(cls.cache, list(range(len(cls.cache))))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def id_of(self, token: str) -> int:
        return self.tokenizer.token_to_id(token)

    def test_pad_id_matches_the_tokenizer(self) -> None:
        self.assertEqual(self.tokenizer.token_to_id("<pad>"), PAD_ID)
        odd = Tokenizer((), specials=("<bos>", "<pad>", "<eos>", "[answer]"))
        with self.assertRaises(ValueError):
            data.check_tokenizer(odd)

    def test_cache_counts_and_clean_stats(self) -> None:
        cache, stats = self.cache, self.cache.info["stats"]
        self.assertEqual(len(cache), 30)
        self.assertEqual(len(cache.question_ids), len(self.questions))
        self.assertEqual(set(cache.question_ids), set(self.questions))
        for key in ("answers_over_max", "answer_names_unseen", "knowable_without_gold", "line_ents_over_max",
                    "evidence_unrendered", "unknowable_with_evidence"):
            self.assertEqual(stats.get(key, 0), 0, key)
        self.assertLessEqual(stats["names_max"], N_ENT)

    def test_shapes_and_padding(self) -> None:
        b, cache = self.batch, self.cache
        visits, width, count = b.size
        self.assertEqual((visits, count), (len(cache), len(cache.question_ids)))
        self.assertEqual(width, int(b.lengths.max()))
        newline = self.id_of("\n")
        for row in range(visits):
            size, lines = int(b.lengths[row]), int(cache.line_counts[row])
            self.assertTrue(bool((b.tokens[row, size:] == PAD_ID).all()))
            self.assertTrue(bool((b.line_of[row, size:] == -1).all()))
            self.assertTrue(bool((b.line_of[row, :size] >= 0).all()))
            self.assertFalse(bool(b.lm_mask[row, size - 1:].any()) or bool(b.card_end[row, size:].any()))
            self.assertTrue(bool((b.line_start[row, lines:] == -1).all()))
            self.assertTrue(bool((b.line_ents[row, lines:] == -1).all()))
            self.assertFalse(bool(b.line_is_question[row, lines:].any()))
            line_of = b.line_of[row, :size]
            self.assertEqual(torch.unique_consecutive(line_of).tolist(), list(range(lines)))
            starts = b.line_start[row, :lines]
            self.assertTrue(bool((line_of[starts] == torch.arange(lines)).all()))
            self.assertTrue(bool((starts[1:] > starts[:-1]).all()))
            questions = b.tokens[row, starts] == self.id_of(step1.QUESTION_TAG)
            self.assertTrue(bool((questions == b.line_is_question[row, :lines]).all()))
            ends = torch.nonzero(b.card_end[row]).flatten()
            self.assertEqual(len(ends), int((~questions).sum()))
            self.assertTrue(bool((b.tokens[row, ends] == newline).all()))
            inner = ends[ends + 1 < size]
            self.assertTrue(bool((b.line_of[row, inner + 1] == b.line_of[row, inner] + 1).all()))
            self.assertFalse(bool(b.line_is_question[row, b.line_of[row, ends]].any()))
            ents = b.line_ents[row, :lines]
            self.assertTrue(bool(((ents >= -1) & (ents < N_ENT)).all()))

    def test_every_gold_line_is_a_card_before_its_question(self) -> None:
        b, cache = self.batch, self.cache
        told = 0
        for q in range(b.size[2]):
            row, line = int(b.q_visit[q]), int(b.q_line[q])
            gold = b.gold_lines[q][b.gold_lines[q] >= 0]
            self.assertTrue(bool(b.line_is_question[row, line]))
            self.assertTrue(bool((gold < line).all()))
            self.assertFalse(bool(b.line_is_question[row, gold].any()))
            knowable = bool(cache.knowable[q])
            self.assertEqual(len(gold) > 0, knowable, b.question_ids[q])
            self.assertEqual(int(b.depth[q]) > 0, knowable, b.question_ids[q])
            full = cache.gold_lines(q)
            self.assertEqual(gold.tolist(), full[-MAX_GOLD:])
            source = self.questions[b.question_ids[q]]
            first = source.line - line
            self.assertEqual(sorted({e - first for e in source.evidence if e >= 0} if knowable else set()), full)
            told += len(gold) > 0
        self.assertGreater(told, 0)

    def test_a_record_pointing_at_a_question_line_is_refused(self) -> None:
        text, meta = step1.shard_files(self.root / "d" / "validation")[0]
        with tempfile.TemporaryDirectory() as folder:
            broken = Path(folder) / "validation"
            broken.mkdir()
            (broken / text.name).write_text(text.read_text(encoding="utf-8"), encoding="utf-8")
            rows = [json.loads(line) for line in meta.read_text(encoding="utf-8").splitlines() if line.strip()]
            asked = [row for row in rows if row["kind"] == "question"]
            first, second = asked[0], next(r for r in asked[1:] if r["text_line"] > asked[0]["text_line"])
            second["evidence_text_lines"] = [first["text_line"]]   # the earlier question's own line
            (broken / meta.name).write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(step1.ShardFormatError, "not a card before the question"):
                data.build_cache(broken, self.tokenizer, self.detector)

    def test_answers_never_appear_in_the_input_before_answer(self) -> None:
        """Test 3: the question span ends at [answer]; the answer is only what follows it, and is never trained."""
        from learnlab.village.stream import CHOICE_QTYPES
        b, answer_id, eos = self.batch, self.id_of(step1.ANSWER_TAG), self.id_of("<eos>")
        vocab = self.tokenizer.vocab_size
        for q in range(b.size[2]):
            row, (start, end) = int(b.q_visit[q]), b.q_span[q].tolist()
            source = self.questions[b.question_ids[q]]
            self.assertEqual(start, int(b.line_start[row, b.q_line[q]]))
            self.assertEqual(int(b.tokens[row, end - 1]), answer_id)
            self.assertNotIn(answer_id, b.tokens[row, start:end - 1].tolist())
            answer = b.answer[q][b.answer[q] != -100].tolist()
            self.assertEqual(answer[-1], eos)
            self.assertLessEqual(len(answer), MAX_ANSWER)
            self.assertEqual(b.tokens[row, end:end + len(answer) - 1].tolist(), answer[:-1])
            self.assertFalse(bool(b.lm_mask[row, end - 1:end + len(answer) - 2].any()))   # never an L_lm target
            self.assertTrue(bool(b.lm_mask[row, start:end - 1].all()))                     # the question itself is
            self.assertEqual(normalize(answer_text(answer, b.names[row], self.tokenizer)), normalize(source.answer))
            prompt = detokenise(b.tokens[row, start:end].tolist(), b.names[row], self.tokenizer)
            self.assertEqual(normalize(prompt), normalize(source.prompt_line))
            if source.qtype not in CHOICE_QTYPES:
                self.assertNotIn(f" {normalize(source.answer)} ", f" {normalize(prompt)} ", source.id)
            # The question line's entities are the question's own, never the answer's alone.
            asked = {i - vocab for i in b.tokens[row, start:end].tolist() if i >= vocab}
            ents = set(b.line_ents[row, b.q_line[q]].tolist()) - {-1}
            self.assertLessEqual(ents, asked)

    def test_permutation_changes_ids_not_spellings(self) -> None:
        cache, vocab = self.cache, self.tokenizer.vocab_size
        visits = list(range(6))
        plain = data.collate(cache, visits)
        one = data.collate(cache, visits, rng=random.Random(1))
        two = data.collate(cache, visits, rng=random.Random(2))
        entity = plain.tokens >= vocab
        self.assertTrue(bool(entity.any()))
        self.assertTrue(bool((one.tokens[~entity] == plain.tokens[~entity]).all()))
        self.assertTrue(bool(((one.tokens >= vocab) == entity).all()))
        self.assertFalse(bool((one.tokens[entity] == two.tokens[entity]).all()))
        for row in range(len(visits)):
            size = int(plain.lengths[row])
            texts = [detokenise(batch.tokens[row, :size].tolist(), batch.names[row], self.tokenizer)
                     for batch in (plain, one, two)]
            self.assertEqual(texts[0], texts[1])
            self.assertEqual(texts[0], texts[2])
            self.assertEqual(sorted(one.names[row].spellings.values()), sorted(plain.names[row].spellings.values()))
            self.assertEqual(plain.names[row], cache.name_table(visits[row]))
            order = {e: next(k for k, s in one.names[row].spellings.items() if s == spelling)
                     for e, spelling in plain.names[row].spellings.items()}
            mapped = plain.line_ents[row].clone()
            mapped[mapped >= 0] = torch.tensor([order[int(e)] for e in mapped[mapped >= 0]], dtype=torch.long)
            self.assertTrue(bool((mapped == one.line_ents[row]).all()))
        for q in range(plain.size[2]):
            row = int(plain.q_visit[q])
            self.assertEqual(answer_text(plain.answer[q].tolist(), plain.names[row], self.tokenizer),
                             answer_text(one.answer[q].tolist(), one.names[row], self.tokenizer))
        for field in ("q_span", "q_line", "gold_lines", "lm_mask", "card_end", "line_of", "depth"):
            self.assertTrue(bool((getattr(one, field) == getattr(plain, field)).all()), field)

    def test_length_buckets(self) -> None:
        lengths = self.cache.lengths.tolist()
        budget = 2 * max(lengths)
        fixed = data.length_batches(lengths, budget)
        self.assertEqual(fixed, data.length_batches(lengths, budget))
        for groups in (fixed, data.length_batches(lengths, budget, rng=random.Random(3), pool=1)):
            self.assertEqual(sorted(i for g in groups for i in g), list(range(len(lengths))))
            for group in groups:
                self.assertLessEqual(len(group) * max(lengths[i] for i in group), budget)
        self.assertEqual(data.length_batches([5, 50, 7], 10), [[0], [2], [1]])
        seen = [b.question_ids for b in data.batches(self.cache, budget, seed=0, epochs=2)]
        self.assertEqual(sorted(q for ids in seen for q in ids), sorted(self.cache.question_ids * 2))

    def test_budgeted_cache_round_trip_and_plain_control(self) -> None:
        budget = Budget(self.root, hard=10_000_000_000, steady=8_000_000_000)
        messages: list[str] = []
        detector = data.name_detector(budget, "d", log=messages.append)
        self.assertEqual(detector.digest, self.detector.digest)
        self.assertEqual(data.name_detector(budget, "d", log=messages.append).digest, detector.digest)
        built = data.load_or_build(budget, "d", "validation", self.tokenizer, detector, log=messages.append)
        logged = len(messages)
        loaded = data.load_or_build(budget, "d", "validation", self.tokenizer, detector, log=messages.append)
        self.assertEqual(len(messages), logged)   # the second call loads what the first wrote
        self.assertEqual(loaded.question_ids, built.question_ids)
        self.assertEqual(loaded.names, built.names)
        self.assertTrue(torch.equal(loaded.tokens, built.tokens))
        self.assertTrue(torch.equal(loaded.gold, built.gold))
        plain = data.load_or_build(budget, "d", "validation", self.tokenizer, None, log=messages.append)
        self.assertLess(int(plain.tokens.max()), self.tokenizer.vocab_size)
        self.assertTrue(bool((plain.line_ents == -1).all()))
        self.assertTrue(torch.equal(plain.q_line, built.q_line))
        self.assertTrue(torch.equal(plain.gold, built.gold))
        batch = data.collate(plain, [0, 1])
        self.assertEqual(batch.names, [NameTable(), NameTable()])


if __name__ == "__main__":
    unittest.main()
