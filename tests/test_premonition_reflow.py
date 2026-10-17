"""Reflow of a visit cache (premonition.reflow): merged and split lines, labels remapped, questions untouched."""
from __future__ import annotations

from dataclasses import fields
import random
import unittest

import torch

from premonition.batch import MAX_LINE_ENTS
from premonition.data import VisitCache, collate
from premonition.reflow import reflow_cache

VOCAB = 48
NL, WORLD, QUESTION, ANSWER = 9, 4, 6, 7
PREFIXES = [[WORLD]]


def ents_of(line: list[int]) -> list[int]:
    """The line_ents row `premonition.data` writes for a non-question line."""
    found = list(dict.fromkeys(t - VOCAB for t in line if t >= VOCAB))[:MAX_LINE_ENTS]
    return found + [-1] * (MAX_LINE_ENTS - len(found))


def make_cache(visits: list[dict], vocab: int = VOCAB) -> VisitCache:
    """A cache built by hand like `data.build_cache`. A visit is {"id", "lines", "questions": [(line, gold)]};
    a line starting with QUESTION is a question line and holds ANSWER."""
    tokens: list[int] = []
    line_offsets, visit_lines, is_question, line_ents = [0], [0], [], []
    visit_questions, q_line, q_span, answer_end, gold = [0], [], [], [], []
    answer_lengths, qids = [], []
    for visit in visits:
        start = len(tokens)
        for line in visit["lines"]:
            question = line[0] == QUESTION
            shown = line[:line.index(ANSWER) + 1] if question else line
            line_ents.append(ents_of(shown))
            is_question.append(question)
            tokens.extend(line)
            line_offsets.append(len(tokens))
        visit_lines.append(len(is_question))
        for k, golds in visit["questions"]:
            line = visit["lines"][k]
            at = line_offsets[visit_lines[-2] + k] - start
            q_line.append(k)
            q_span.append((at, at + line.index(ANSWER) + 1))
            answer_end.append(at + len(line) - 1)
            gold.append(sorted(golds))
            qids.append(f"{visit['id']}/q{k}")
        visit_questions.append(len(q_line))
    count = len(q_line)
    answers = [[VOCAB + 1, 2] for _ in range(count)]
    return VisitCache(
        split="test", vocab_size=vocab, tokens=torch.tensor(tokens, dtype=torch.int16),
        line_offsets=torch.tensor(line_offsets, dtype=torch.int32), visit_lines=torch.tensor(visit_lines),
        line_is_question=torch.tensor(is_question, dtype=torch.bool),
        line_ents=torch.tensor(line_ents, dtype=torch.int8).reshape(-1, MAX_LINE_ENTS),
        visit_questions=torch.tensor(visit_questions), q_line=torch.tensor(q_line, dtype=torch.long),
        q_span=torch.tensor(q_span, dtype=torch.long).reshape(-1, 2),
        answer_end=torch.tensor(answer_end, dtype=torch.long),
        answer_offsets=torch.tensor([2 * i for i in range(count + 1)]),
        answer_ids=torch.tensor([t for a in answers for t in a], dtype=torch.int16),
        gold_offsets=torch.cumsum(torch.tensor([0] + [len(g) for g in gold]), 0),
        gold=torch.tensor([g for row in gold for g in row], dtype=torch.int16),
        depth=torch.ones(count, dtype=torch.int8), knowable=torch.ones(count, dtype=torch.bool),
        question_ids=qids, visit_ids=[str(v["id"]) for v in visits], names=[list("abcdefghi") for _ in visits],
        info={"source": "synthetic", "tokens": len(tokens)}, target_unbound=torch.zeros(count, dtype=torch.bool))


def base_visits() -> list[dict]:
    return [
        {"id": "v0", "lines": [
            [WORLD, 10, 11, 48, 12, NL],                  # 0
            [WORLD, 13, 49, 14, 15, NL],                  # 1
            [WORLD, 16, 17, NL],                          # 2
            [WORLD, 18, 48, 19, 50, NL],                  # 3
            [QUESTION, 20, 48, 21, ANSWER, 51, NL],       # 4  question
            [WORLD, 22, 23, NL],                          # 5
            [QUESTION, 24, 49, ANSWER, 25, NL],           # 6  question
        ], "questions": [(4, [1, 2]), (6, [0, 5])]},
        {"id": "v1", "lines": [
            [WORLD, 10, 52, 11, 53, 12, 54, NL],          # 0
            [WORLD, 13, 55, NL],                          # 1
            [WORLD, 14, NL],                              # 2  one interior position
            [QUESTION, 14, ANSWER, 15, NL],               # 3  question
        ], "questions": [(3, [1, 2])]},
        {"id": "v2", "lines": [                           # no question
            [WORLD, 10, 48, 49, 50, NL],                  # 0  3 entities
            [WORLD, 11, 51, 52, NL],                      # 1  2 more: 5 distinct once merged
        ], "questions": []},
    ]


def lines_of(cache: VisitCache, v: int) -> list[list[int]]:
    first, last = int(cache.visit_lines[v]), int(cache.visit_lines[v + 1])
    offsets = cache.line_offsets.tolist()
    return [cache.tokens[offsets[k]:offsets[k + 1]].tolist() for k in range(first, last)]


def bigger_visits(count: int = 20, size: int = 12) -> list[dict]:
    rng = random.Random(5)
    visits = []
    for v in range(count):
        lines = []
        for k in range(size):
            body = [rng.randrange(10, 47) for _ in range(rng.randrange(2, 7))]
            body.insert(rng.randrange(len(body) + 1), VOCAB + rng.randrange(6))
            lines.append([WORLD, *body, NL])
        lines[-1] = [QUESTION, 20, VOCAB, ANSWER, 51, NL]
        visits.append({"id": f"b{v}", "lines": lines, "questions": [(size - 1, [1, 3, size - 2])]})
    return visits


def same_cache(a: VisitCache, b: VisitCache) -> bool:
    for f in fields(VisitCache):
        x, y = getattr(a, f.name), getattr(b, f.name)
        if isinstance(x, torch.Tensor):
            if x.dtype != y.dtype or not torch.equal(x, y):
                return False
        elif f.name != "info" and x != y:
            return False
    return True


class ReflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cache = make_cache(base_visits())

    def test_fixture_is_consistent(self) -> None:
        cache = self.cache
        self.assertEqual(cache.line_counts.tolist(), [7, 4, 2])
        self.assertEqual(cache.tokens.numel(), int(cache.line_offsets[-1]))
        out = reflow_cache(cache, newline_id=NL)
        self.assertEqual(lines_of(out, 0)[4], [QUESTION, 20, 48, 21, ANSWER, 51, NL])

    def test_identity(self) -> None:
        out = reflow_cache(self.cache, newline_id=NL, drop_prefixes=PREFIXES, seed=3)
        self.assertTrue(same_cache(self.cache, out))
        self.assertEqual({k: v for k, v in out.info.items() if k != "reflow"}, self.cache.info)
        self.assertEqual(out.info["reflow"]["stats"], {"lines_before": 13, "lines_after": 13, "merged_lines": 0,
                                                       "split_lines": 0, "ents_over_max": 0})
        self.assertNotIn("reflow", self.cache.info)
        out, maps = reflow_cache(self.cache, newline_id=NL, return_map=True)
        self.assertEqual(maps[0], [[k] for k in range(7)])

    def test_merge_pairs(self) -> None:
        cache = self.cache
        out, maps = reflow_cache(cache, merge=1.0, max_merge=2, newline_id=NL, drop_prefixes=PREFIXES,
                                 return_map=True)
        # visit 0: (0,1) and (2,3) merge, the question lines stay, line 5 is followed by a question
        self.assertEqual(lines_of(out, 0), [
            [WORLD, 10, 11, 48, 12, 13, 49, 14, 15, NL],
            [WORLD, 16, 17, 18, 48, 19, 50, NL],
            [QUESTION, 20, 48, 21, ANSWER, 51, NL],
            [WORLD, 22, 23, NL],
            [QUESTION, 24, 49, ANSWER, 25, NL],
        ])
        self.assertEqual(maps[0], [[0], [0], [1], [1], [2], [3], [4]])
        self.assertEqual(lines_of(out, 1)[:2], [[WORLD, 10, 52, 11, 53, 12, 54, 13, 55, NL], [WORLD, 14, NL]])
        self.assertEqual(maps[1], [[0], [0], [1], [2]])
        self.assertEqual(maps[2], [[0], [0]])
        merges = 2 + 1 + 1
        self.assertEqual(out.tokens.numel(), cache.tokens.numel() - 2 * merges)
        self.assertEqual(out.line_counts.tolist(), [5, 3, 1])
        self.assertEqual(out.info["reflow"]["stats"]["merged_lines"], merges)
        # gold of the merged-away line 1 (and line 2) point at the merged lines
        self.assertEqual(out.gold_lines(0), [0, 1])
        self.assertEqual(out.gold_lines(1), [0, 3])
        self.assertEqual(out.gold_lines(2), [0, 1])
        self.assertEqual(out.gold_offsets.tolist(), [0, 2, 4, 6])
        self.assertEqual(out.line_ents[0].tolist(), ents_of([48, 49]))
        self.assertEqual(out.line_ents[1].tolist(), ents_of([48, 50]))
        self.assertEqual(out.line_ents[2].tolist(), cache.line_ents[4].tolist())    # a question keeps its row
        self.assertEqual(out.q_line.tolist(), [2, 4, 2])

    def test_merge_without_prefix_and_up_to_max(self) -> None:
        out = reflow_cache(self.cache, merge=1.0, max_merge=3, newline_id=NL)
        self.assertEqual(lines_of(out, 0)[0], [WORLD, 10, 11, 48, 12, WORLD, 13, 49, 14, 15, WORLD, 16, 17, NL])
        out = reflow_cache(self.cache, merge=1.0, max_merge=3, newline_id=NL, drop_prefixes=PREFIXES)
        self.assertEqual(lines_of(out, 0)[0], [WORLD, 10, 11, 48, 12, 13, 49, 14, 15, 16, 17, NL])
        self.assertEqual(lines_of(out, 0)[1], [WORLD, 18, 48, 19, 50, NL])   # a lone line before the question
        self.assertEqual(out.line_counts.tolist(), [5, 2, 1])

    def test_split_every_line(self) -> None:
        cache = self.cache
        out, maps = reflow_cache(cache, split=1.0, newline_id=NL, seed=1, return_map=True)
        cards = [(v, k) for v in range(3) for k in range(len(maps[v]))
                 if not cache.line_is_question[int(cache.visit_lines[v]) + k]]
        self.assertEqual(len(cards), 10)
        self.assertEqual(out.tokens.numel(), cache.tokens.numel() + len(cards))
        self.assertEqual(out.info["reflow"]["stats"]["split_lines"], len(cards))
        self.assertEqual(out.info["reflow"]["stats"]["lines_after"], 13 + len(cards))
        for v, k in cards:
            self.assertEqual(len(maps[v][k]), 2)
            first, second = (lines_of(out, v)[n] for n in maps[v][k])
            self.assertEqual(first[:-1] + second, lines_of(cache, v)[k])
            self.assertEqual(first[-1], NL)
            self.assertTrue(first[:-1] and second[:-1])
            base_row = int(out.visit_lines[v])
            for n, half in zip(maps[v][k], (first, second)):
                self.assertEqual(out.line_ents[base_row + n].tolist(), ents_of(half))
        # a gold line maps to both halves
        first, second = maps[0][1]
        self.assertEqual(second, first + 1)
        self.assertEqual(out.gold_lines(0), sorted({*maps[0][1], *maps[0][2]}))
        self.assertEqual(len(out.gold_lines(0)), 4)
        self.assertEqual(out.line_counts.tolist(), [7 + 5, 4 + 3, 2 + 2])

    def test_split_only_at_word_starts(self) -> None:
        cache = self.cache
        word_start = torch.zeros(VOCAB, dtype=torch.bool)
        word_start[[11, 15, 17]] = True
        for seed in range(6):
            out, maps = reflow_cache(cache, split=1.0, newline_id=NL, seed=seed, word_start=word_start,
                                     return_map=True)
            expected = 0
            for v in range(3):
                for k, line in enumerate(lines_of(cache, v)):
                    if line[0] == QUESTION:
                        self.assertEqual(maps[v][k], [maps[v][k][0]])
                        continue
                    ok = [i for i in range(1, len(line) - 1) if line[i] >= VOCAB or word_start[line[i]]]
                    expected += bool(ok)
                    self.assertEqual(len(maps[v][k]), 2 if ok else 1)
                    if ok:
                        first, second = (lines_of(out, v)[n] for n in maps[v][k])
                        self.assertIn(len(first) - 1, ok)
            self.assertEqual(out.info["reflow"]["stats"]["split_lines"], expected)
            self.assertEqual(out.tokens.numel(), cache.tokens.numel() + expected)
        # no allowed position at all and no entity: [WORLD, 16, 17, NL] stays whole
        none = torch.zeros(VOCAB, dtype=torch.bool)
        out, maps = reflow_cache(cache, split=1.0, newline_id=NL, word_start=none, return_map=True)
        self.assertEqual(maps[0][2], [maps[0][2][0]])
        self.assertEqual(len(maps[0][0]), 2)       # has an entity at an interior position

    def test_question_integrity(self) -> None:
        for cache in (self.cache, make_cache(bigger_visits())):
            for seed in range(8):
                out = reflow_cache(cache, merge=0.5, split=0.5, seed=seed, newline_id=NL, drop_prefixes=PREFIXES)
                for v in range(len(cache)):
                    old_tokens, new_tokens = cache.visit_tokens(v), out.visit_tokens(v)
                    old_lines, new_lines = lines_of(cache, v), lines_of(out, v)
                    for q in cache.questions_of(v):
                        old_k, new_k = int(cache.q_line[q]), int(out.q_line[q])
                        self.assertTrue(bool(out.line_is_question[int(out.visit_lines[v]) + new_k]))
                        self.assertEqual(new_lines[new_k], old_lines[old_k])
                        (a, b), (c, d) = cache.q_span[q].tolist(), out.q_span[q].tolist()
                        self.assertEqual(new_tokens[c:d].tolist(), old_tokens[a:b].tolist())
                        self.assertEqual(int(new_tokens[d - 1]), ANSWER)
                        self.assertEqual(c - a, d - b)
                        self.assertEqual(int(out.answer_end[q] - cache.answer_end[q]), c - a)
                        self.assertEqual(new_tokens[int(out.answer_end[q])].item(), NL)
                        self.assertEqual(out.line_ents[int(out.visit_lines[v]) + new_k].tolist(),
                                         cache.line_ents[int(cache.visit_lines[v]) + old_k].tolist())
                        golds = out.gold_lines(q)
                        self.assertEqual(golds, sorted(set(golds)))
                        self.assertTrue(golds)
                        for g in golds:
                            self.assertLess(g, new_k)
                            self.assertFalse(bool(out.line_is_question[int(out.visit_lines[v]) + g]))
                        # every old gold line's tokens (but newline and prefix) are inside its new lines
                        for g in cache.gold_lines(q):
                            body = [t for t in old_lines[g] if t not in (NL, WORLD)]
                            covered = [t for n in golds for t in new_lines[n] if t not in (NL, WORLD)]
                            for t in body:
                                self.assertIn(t, covered)
                    # the questions are never merged away: their count and order are unchanged
                    self.assertEqual(int(out.line_is_question[out.visit_lines[v]:out.visit_lines[v + 1]].sum()),
                                     int(cache.line_is_question[cache.visit_lines[v]:cache.visit_lines[v + 1]].sum()))
                self.assertTrue(torch.equal(out.visit_questions, cache.visit_questions))
                self.assertEqual(out.info["reflow"]["stats"]["lines_after"], int(out.visit_lines[-1]))

    def test_collate_on_reflowed_cache(self) -> None:
        for seed in range(3):
            out = reflow_cache(self.cache, merge=0.5, split=0.5, seed=seed, newline_id=NL, drop_prefixes=PREFIXES)
            for rng in (None, random.Random(seed)):
                batch = collate(out, [0, 1, 2], rng=rng)
                cards = (~out.line_is_question).sum().item()
                self.assertEqual(int(batch.card_end.sum()), cards)
                self.assertEqual(batch.lengths.tolist(), out.lengths.tolist())
                self.assertEqual(batch.size[2], 3)
                self.assertEqual(batch.q_line.tolist(), out.q_line.tolist())
                for i in range(3):
                    visit = batch.q_visit[i].item()
                    start, end = batch.q_span[i].tolist()
                    self.assertEqual(int(batch.tokens[visit, end - 1]), ANSWER)
                    self.assertTrue(bool(batch.line_is_question[visit, batch.q_line[i]]))
                    self.assertEqual(int(batch.line_start[visit, batch.q_line[i]]), start)
                    golds = [g for g in batch.gold_lines[i].tolist() if g >= 0]
                    self.assertTrue(all(g < batch.q_line[i] for g in golds))
        out = reflow_cache(self.cache, merge=1.0, max_merge=3, newline_id=NL, drop_prefixes=PREFIXES)
        batch = collate(out, [0, 1, 2])
        self.assertEqual(int(batch.card_end.sum()), 5)   # 3 + 1 + 1 cards after max_merge=3 merging

    def test_determinism_and_visit_independence(self) -> None:
        cache = make_cache(bigger_visits())
        kw = dict(merge=0.5, split=0.3, newline_id=NL, drop_prefixes=PREFIXES)
        a = reflow_cache(cache, seed=7, **kw)
        self.assertTrue(same_cache(a, reflow_cache(cache, seed=7, **kw)))
        b = reflow_cache(cache, seed=8, **kw)
        self.assertFalse(torch.equal(a.tokens, b.tokens))
        # a visit's result depends on its id and the seed only: reverse the visit order and compare by id
        order = list(range(len(cache)))[::-1]
        reversed_cache = make_cache([bigger_visits()[i] for i in order])
        c = reflow_cache(reversed_cache, seed=7, **kw)
        for position, i in enumerate(order):
            self.assertEqual(lines_of(c, position), lines_of(a, i))

    def test_entity_bookkeeping(self) -> None:
        out, maps = reflow_cache(self.cache, merge=1.0, max_merge=2, newline_id=NL, drop_prefixes=PREFIXES,
                                 return_map=True)
        row = int(out.visit_lines[2]) + maps[2][0][0]
        merged = lines_of(out, 2)[0]
        self.assertEqual(merged, [WORLD, 10, 48, 49, 50, 11, 51, 52, NL])
        self.assertEqual(len({t for t in merged if t >= VOCAB}), 5)
        self.assertEqual(out.line_ents[row].tolist(), [0, 1, 2, 3])          # first MAX_LINE_ENTS, in order
        self.assertEqual(out.line_ents.dtype, torch.int8)
        self.assertEqual(out.info["reflow"]["stats"]["ents_over_max"], 1)
        # exactly four distinct entities are not over the cap (visit 1: 52..55)
        self.assertEqual(out.line_ents[int(out.visit_lines[1])].tolist(), [4, 5, 6, 7])

    def test_rejects_bad_input(self) -> None:
        with self.assertRaises(ValueError):
            reflow_cache(self.cache, newline_id=NL + 1)
        with self.assertRaises(ValueError):
            reflow_cache(self.cache, merge=1.5, newline_id=NL)
        with self.assertRaises(ValueError):
            reflow_cache(self.cache, newline_id=NL, max_merge=0)
        with self.assertRaises(ValueError):
            reflow_cache(self.cache, newline_id=NL, drop_prefixes=[[]])
        with self.assertRaises(ValueError):
            reflow_cache(self.cache, newline_id=NL, word_start=torch.ones(VOCAB - 1, dtype=torch.bool))


if __name__ == "__main__":
    unittest.main()
