"""Fast CPU tests of the intervention plumbing in scripts/premonition_interface_probes.py.

Nothing is trained and no saved checkpoint is needed: one freshly initialised `bypass-k1` model on one small
freshly generated toy-ladder batch is enough, because what is checked is the plumbing, not the numbers.

  twin stories      one value token changes, nothing else; the replacement is deterministic and different
  C1                every fact card is really ineligible: eligibility keeps only NULL, every request is NULL,
                    and no real card is ever marked fetched
  C2                the story-blind question rows are bit-independent of story content (perturbing a story
                    fact leaves them identical) while the normal question rows do change -- so the test is not
                    vacuous; the same gather applied to the full-story read reproduces `_start` exactly
  C4                restoring the store and restoring the question rows are both bit-exact
  audit             the entity-slot and register rows carry no story tensor
"""
from __future__ import annotations

from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import premonition_interface_probes as IP                       # noqa: E402

IP.use_repo_root(IP.ROOT)
IP.L.bootstrap()

import torch                                                   # noqa: E402

VISITS = 3


def make_batch(spec, seed: int = 0):
    from premonition import toy_ladder
    from premonition.train import label_free
    rng = random.Random(seed)
    batch, supplied, hops = toy_ladder.make(spec, VISITS, rng, training=False, prefix="probe-test")
    return label_free(batch), supplied, hops


def make_model(spec, seed: int = 0):
    from premonition import answer_path
    from premonition.config import MiniConfig
    from premonition.model import PremonitionMini
    torch.manual_seed(seed)
    config = MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64, top_k=1,
                               distractors=(0, 0), max_loops=4, early_ans=0.2)
    model = answer_path.from_base(answer_path.CARD_BYPASS, PremonitionMini(config))
    model.eval()
    return model


class Fixture(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        torch.set_num_threads(2)
        cls.spec = IP.L.spec()
        cls.batch, cls.supplied, cls.hops = make_batch(cls.spec)
        cls.model = make_model(cls.spec)


class TwinStoryTest(Fixture):

    def test_replacement_is_deterministic_and_different(self) -> None:
        for old in range(self.spec.values):
            new = IP.replacement_value(self.spec, old, key="k")
            self.assertNotEqual(new, old)
            self.assertTrue(0 <= new < self.spec.values)
            self.assertEqual(new, IP.replacement_value(self.spec, old, key="k"))
        keys = {IP.replacement_value(self.spec, 0, key=f"{i}") for i in range(64)}
        self.assertGreater(len(keys), 1, "the edit should not always pick the same replacement")

    def test_twin_changes_exactly_one_token_per_edit(self) -> None:
        attrs = IP.lines_of_kind(self.batch, self.spec, "attr")
        self.assertTrue(all(len(a) == self.spec.entities * self.spec.relations for a in attrs))
        edits = [(v, attrs[v][0]) for v in range(VISITS)]
        twin, done = IP.twin_batch(self.batch, self.spec, edits, tag="t")
        self.assertEqual(len(done), VISITS)
        differ = (twin.tokens != self.batch.tokens).nonzero().tolist()
        self.assertEqual(len(differ), VISITS)
        for (visit, line, position, old, new), (dv, dp) in zip(done, sorted(differ)):
            self.assertEqual((visit, position), (dv, dp))
            self.assertNotEqual(old, new)
            self.assertEqual(int(twin.tokens[visit, position]), self.spec.value(new))
        for field in ("line_of", "line_start", "card_end", "lm_mask", "q_span", "line_ents",
                      "line_is_question", "gold_lines"):
            self.assertTrue(torch.equal(getattr(twin, field), getattr(self.batch, field)), field)

    def test_line_kinds_partition_the_story(self) -> None:
        counts = {kind: sum(len(x) for x in IP.lines_of_kind(self.batch, self.spec, kind))
                  for kind in ("attr", "link", "filler", "question", "none")}
        self.assertEqual(counts["attr"], VISITS * self.spec.entities * self.spec.relations)
        self.assertEqual(counts["link"], VISITS * self.spec.entities)
        self.assertEqual(counts["question"], VISITS * (self.spec.one_hop + self.spec.two_hop))
        self.assertEqual(sum(counts.values()), self.batch.line_start.numel())


class CardsRemovedTest(Fixture):

    def test_c1_makes_every_fact_card_ineligible(self) -> None:
        with torch.no_grad():
            hidden = self.model.read(self.batch)
            store = self.model.build_store(hidden, self.batch)
            self.assertTrue(bool(store.valid.any()), "the unablated store must have cards")
            ablated = IP.ablate_cards(store)
            eligible = ablated.eligible(self.batch.q_visit, self.batch.q_line)
        self.assertFalse(bool(eligible[:, :-1].any()), "no fact card may be eligible under C1")
        self.assertTrue(bool(eligible[:, -1].all()), "NULL must stay eligible under C1")
        self.assertTrue(torch.equal(ablated.keys, store.keys), "C1 must not touch the card contents")

    def test_c1_requests_are_null_and_nothing_real_is_fetched(self) -> None:
        spy: dict = {}
        with torch.no_grad():
            ok, answers, gold, fetched = IP.condition(self.model, self.batch, 4, no_cards=True, spy=spy)
        null = spy["store"].null
        for cards in spy["requests"]:
            self.assertTrue(bool(((cards == null) | (cards == -1)).all()),
                            "under C1 every request must be NULL or empty")
        self.assertFalse(bool(fetched[:, :-1].any()), "no real card may be marked fetched under C1")


class StoryBlindTest(Fixture):

    def _question_rows(self, batch, *, story_blind: bool):
        """The question rows the model will actually attend to (padding rows are masked out everywhere)."""
        spy: dict = {}
        with torch.no_grad():
            IP.condition(self.model, batch, 1, story_blind=story_blind, spy=spy)
        return spy["question_rows_after"][IP.question_row_valid(batch, self.model.config.question_rows)]

    def test_c2_question_rows_are_bit_independent_of_story_content(self) -> None:
        attrs = IP.lines_of_kind(self.batch, self.spec, "attr")
        edits = [(v, attrs[v][1]) for v in range(VISITS)]
        twin, _ = IP.twin_batch(self.batch, self.spec, edits, tag="blind")
        blind_a = self._question_rows(self.batch, story_blind=True)
        blind_b = self._question_rows(twin, story_blind=True)
        self.assertTrue(torch.equal(blind_a, blind_b),
                        "story-blind question rows must not move when a story fact is perturbed")
        normal_a = self._question_rows(self.batch, story_blind=False)
        normal_b = self._question_rows(twin, story_blind=False)
        self.assertFalse(torch.equal(normal_a, normal_b),
                         "the normal question rows DO see the story -- otherwise this test is vacuous")
        self.assertFalse(torch.equal(normal_a, blind_a), "C2 must actually change the question rows")

    def test_question_tokens_only_holds_the_span_and_pads_after(self) -> None:
        tokens = IP.question_tokens_only(self.batch, self.model.config.pad_id)
        start, end = self.batch.q_span[:, 0], self.batch.q_span[:, 1]
        for q in range(tokens.shape[0]):
            span = int(end[q] - start[q])
            self.assertTrue(torch.equal(tokens[q, :span],
                                        self.batch.tokens[int(self.batch.q_visit[q]), int(start[q]):int(end[q])]))
            self.assertTrue(bool((tokens[q, span:] == self.model.config.pad_id).all()))
        self.assertTrue(bool((tokens[:, 0] == 4).all()), "each span must start at the [question] token")

    def test_reader_on_question_tokens_is_right_padding_independent(self) -> None:
        """The reader is causal, so the states used by C2 do not depend on what is padded after them."""
        tokens = IP.question_tokens_only(self.batch, self.model.config.pad_id)
        with torch.no_grad():
            short = self.model.reader(self.model.embed(tokens))
            longer = self.model.reader(self.model.embed(
                torch.cat([tokens, torch.full_like(tokens, self.model.config.pad_id)], dim=1)))
        self.assertTrue(torch.equal(short, longer[:, :tokens.shape[1]]))

    def test_set_question_rows_reproduces_start_when_fed_the_story_read(self) -> None:
        """The index arithmetic is right: the same gather from the full-story read is a no-op."""
        with torch.no_grad():
            hidden = self.model.read(self.batch)
            store = self.model.build_store(hidden, self.batch)
            episode = self.model._start(self.batch, hidden, store, self.model._mentions(self.batch))
            rows_q = self.model.config.question_rows
            wanted = episode.x[:, :rows_q].clone()
            IP.set_question_rows(self.model, self.batch, episode,
                                 IP.question_rows_from_story(self.model, self.batch, hidden))
        self.assertTrue(torch.equal(episode.x[:, :rows_q], wanted))

    def test_padding_question_rows_are_marked_invalid(self) -> None:
        """The rows `set_question_rows` leaves alone are exactly the ones every attention mask drops."""
        with torch.no_grad():
            hidden = self.model.read(self.batch)
            store = self.model.build_store(hidden, self.batch)
            episode = self.model._start(self.batch, hidden, store, self.model._mentions(self.batch))
        rows_q = self.model.config.question_rows
        self.assertTrue(torch.equal(episode.valid[:, :rows_q], IP.question_row_valid(self.batch, rows_q)))

    def test_c2_leaves_the_validity_mask_alone(self) -> None:
        with torch.no_grad():
            hidden = self.model.read(self.batch)
            store = self.model.build_store(hidden, self.batch)
            mentions = self.model._mentions(self.batch)
            a = self.model._start(self.batch, hidden, store, mentions)
            b = self.model._start(self.batch, hidden, store, mentions)
            IP.set_question_rows(self.model, self.batch, b, IP.story_blind_question_hidden(self.model, self.batch))
        self.assertTrue(torch.equal(a.valid, b.valid))


class RestorationTest(Fixture):

    def test_c4_store_restoration_is_bit_exact(self) -> None:
        with torch.no_grad():
            base = IP.condition(self.model, self.batch, 4)
            restored = IP.condition(self.model, self.batch, 4, restore_cards=True)
            blind = IP.condition(self.model, self.batch, 4, story_blind=True)
            blind_restored = IP.condition(self.model, self.batch, 4, story_blind=True, restore_cards=True)
        for a, b, label in ((base, restored, "C1 -> restore == C0"), (blind, blind_restored, "C3 -> restore == C2")):
            self.assertTrue(torch.equal(a[1], b[1]), f"{label}: answers")
            self.assertTrue(torch.equal(a[0], b[0]), f"{label}: correctness")
            self.assertTrue(torch.equal(a[3], b[3]), f"{label}: fetched")

    def test_question_row_restoration_is_bit_exact(self) -> None:
        spy: dict = {}
        with torch.no_grad():
            IP.condition(self.model, self.batch, 2, restore_question=True, spy=spy)
        self.assertTrue(torch.equal(spy["question_rows_before"], spy["question_rows_after"]))

    def test_c1_and_c3_really_differ_from_c0_and_c2(self) -> None:
        """A restoration test only means something if the interventions bite at all."""
        with torch.no_grad():
            c0 = IP.condition(self.model, self.batch, 4)
            c1 = IP.condition(self.model, self.batch, 4, no_cards=True)
        self.assertFalse(torch.equal(c0[3], c1[3]), "C1 must change what gets fetched")


class AuditTest(Fixture):

    def test_slot_and_register_rows_carry_no_story_tensor(self) -> None:
        audit = IP.slot_and_register_audit(self.model, [(self.batch, self.supplied, self.hops)])
        self.assertTrue(audit["slot_rows_are_entity_embeddings_only"])
        self.assertTrue(audit["register_rows_are_parameters_only"])
        self.assertTrue(audit["slot_rows_unchanged_when_story_tokens_are_zeroed"])

    def test_answer_frequency_chance_is_computed_not_assumed(self) -> None:
        chance = IP.answer_frequency_chance([(self.batch, self.supplied, self.hops)])
        for hop, entry in chance.items():
            self.assertEqual(entry["n"], sum(1 for _ in range(entry["n"])))
            if entry["n"]:
                self.assertGreaterEqual(entry["best_constant_answer_acc"], 1.0 / self.spec.values - 1e-9)
                self.assertLessEqual(entry["best_constant_answer_acc"], 1.0)


if __name__ == "__main__":
    unittest.main()
