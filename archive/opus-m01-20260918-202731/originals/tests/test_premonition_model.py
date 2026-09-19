"""Premonition-mini model, store and FLOP counting (design/06 §7 tests 2, 4-8; build step 3).

Batches are synthetic `VisitBatch` objects, so nothing here depends on premonition.data.
"""
from __future__ import annotations

import random
import unittest

import torch
import torch.nn.functional as F

from learnlab.core import Core, CoreConfig
from learnlab.readonly import ReadOnlyViolation, read_only
from premonition.batch import MAX_ANSWER, MAX_GOLD, MAX_LINE_ENTS, N_ENT, NameTable, VisitBatch
from premonition.config import PARAM_BAND, MiniConfig
from premonition.flops import (core_flops_per_token, fit_flops, measure_core, measure_mini,
                               mini_hand_count)
from premonition.model import PremonitionMini, crop_to_windows, min_gru_scan
from premonition.store import CardStore, set_cross_entropy

VOCAB = 48                                  # tokenizer ids; ENT e is VOCAB + e
PAD, EOS = 0, 2
WORLD, TEACHER, QUESTION, ANSWER, FEEDBACK, NEWLINE = 4, 5, 6, 7, 8, 9
CONTENT = list(range(10, VOCAB))


def synthetic_batch(visits: int = 2, lines: int = 16, seed: int = 0, question_rate: float = 0.35,
                    vocab: int = VOCAB, reply_len: tuple[int, int] = (1, 3)) -> VisitBatch:
    """Visits of [world]/[teacher] lines (cards) and "[question] q [answer] a [feedback] f" lines.

    Tokens below `vocab` are tokenizer ids (content drawn from 10..47); `vocab + e` is ENT e."""
    rng = random.Random(seed)
    rows = []
    for visit in range(visits):
        tokens, line_of, card_end, lm_mask = [], [], [], []
        is_question, starts, ents, questions = [], [], [], []
        mentioned: list[int] = []
        for line in range(lines):
            start = len(tokens)
            starts.append(start)
            question = line >= 3 and rng.random() < question_rate
            line_ents: list[int] = []
            if not question:
                body = [rng.choice([WORLD, TEACHER])] + rng.sample(CONTENT, rng.randint(3, 7))
                if rng.random() < 0.7:
                    entity = rng.randrange(N_ENT)
                    body.insert(rng.randint(1, len(body)), vocab + entity)
                    line_ents.append(entity)
                    mentioned.append(entity)
                body.append(NEWLINE)
                keep = [True] * len(body)
            else:
                ask = [QUESTION] + rng.sample(CONTENT, rng.randint(2, 5)) + [ANSWER]
                if mentioned and rng.random() < 0.4:
                    reply = [vocab + rng.choice(mentioned)]
                else:
                    reply = rng.sample(CONTENT, rng.randint(*reply_len))
                body = ask + reply + [FEEDBACK, rng.choice(CONTENT), NEWLINE]
                # position i predicts token i + 1: the reply is never an L_lm target
                keep = [not (len(ask) - 1 <= i < len(ask) + len(reply) - 1) for i in range(len(body))]
                earlier = [l for l in range(line) if not is_question[l]]
                gold = [] if rng.random() < 0.25 else rng.sample(earlier, min(len(earlier), rng.randint(1, 3)))
                questions.append((line, start, start + len(ask), reply + [EOS], gold))
            tokens += body
            line_of += [line] * len(body)
            card_end += [False] * (len(body) - 1) + [not question]
            lm_mask += keep
            is_question.append(question)
            ents.append(line_ents)
        rows.append((tokens, line_of, card_end, lm_mask, is_question, starts, ents, questions))
    length = max(len(r[0]) for r in rows)
    batch = dict(
        tokens=torch.full((visits, length), PAD), line_of=torch.full((visits, length), -1),
        card_end=torch.zeros(visits, length, dtype=torch.bool),
        lengths=torch.tensor([len(r[0]) for r in rows]),
        lm_mask=torch.zeros(visits, length, dtype=torch.bool),
        line_is_question=torch.zeros(visits, lines, dtype=torch.bool),
        line_start=torch.full((visits, lines), -1),
        line_ents=torch.full((visits, lines, MAX_LINE_ENTS), -1),
    )
    q_rows = []
    for visit, (tokens, line_of, card_end, lm_mask, is_question, starts, ents, questions) in enumerate(rows):
        n = len(tokens)
        batch["tokens"][visit, :n] = torch.tensor(tokens)
        batch["line_of"][visit, :n] = torch.tensor(line_of)
        batch["card_end"][visit, :n] = torch.tensor(card_end)
        batch["lm_mask"][visit, :n - 1] = torch.tensor(lm_mask[:n - 1])
        batch["line_is_question"][visit] = torch.tensor(is_question)
        batch["line_start"][visit] = torch.tensor(starts)
        for line, line_ents in enumerate(ents):
            batch["line_ents"][visit, line, :len(line_ents)] = torch.tensor(line_ents, dtype=torch.long)
        q_rows += [(visit,) + q for q in questions]
    count = len(q_rows)
    answer = torch.full((count, MAX_ANSWER), -100)
    gold = torch.full((count, MAX_GOLD), -1)
    for i, (_, _, _, _, reply, lines_) in enumerate(q_rows):
        answer[i, :len(reply)] = torch.tensor(reply)
        gold[i, :len(lines_)] = torch.tensor(lines_, dtype=torch.long)
    return VisitBatch(
        **batch,
        q_visit=torch.tensor([q[0] for q in q_rows], dtype=torch.long),
        q_line=torch.tensor([q[1] for q in q_rows], dtype=torch.long),
        q_span=torch.tensor([[q[2], q[3]] for q in q_rows], dtype=torch.long).view(count, 2),
        answer=answer, gold_lines=gold,
        depth=torch.tensor([min(len(q[5]), 3) for q in q_rows], dtype=torch.long),
        question_ids=[f"q{i}" for i in range(count)],
        names=[NameTable({e: f"Name{e}" for e in range(N_ENT)}) for _ in range(visits)],
    )


def tiny_config(variant: str = "D", **overrides) -> MiniConfig:
    settings = dict(window=16, max_loops=6)
    settings.update(overrides)
    return MiniConfig.preset(variant, "tiny", vocab_size=VOCAB, **settings)


def tiny_model(variant: str = "D", seed: int = 0, **overrides) -> PremonitionMini:
    torch.manual_seed(seed)
    return PremonitionMini(tiny_config(variant, **overrides))


def eager(model: PremonitionMini) -> PremonitionMini:
    """Always ASK and never HALT, so evaluation fetches cards on every loop."""
    with torch.no_grad():
        model.heads.ask.bias.fill_(20.0)
        model.heads.halt.bias.fill_(-20.0)
    return model


class ParameterTest(unittest.TestCase):
    def test_full_config_matches_the_spec_table(self) -> None:
        config = MiniConfig.preset("D")
        expected = {"embedding": 817_664, "reader": 496_384, "card_writer": 25_089,
                    "think": 466_448, "heads": 8_515, "decoder": 199_040}
        self.assertEqual(config.parameter_breakdown(), expected)
        with torch.device("meta"):
            model = PremonitionMini(config)
        self.assertEqual(model.parameter_breakdown(), expected)
        self.assertEqual(model.num_parameters(), 2_013_140)
        for variant in ("D-noask", "D-noptr"):
            config = MiniConfig.preset(variant)
            with torch.device("meta"):
                model = PremonitionMini(config)
            self.assertEqual(model.parameter_breakdown(), config.parameter_breakdown(), variant)
            self.assertTrue(PARAM_BAND[0] <= model.num_parameters() <= PARAM_BAND[1], variant)

    def test_band_is_enforced_at_d128(self) -> None:
        with self.assertRaises(ValueError):
            MiniConfig.preset("D", think_mlp=8)
        self.assertEqual(tiny_model().parameter_breakdown(), tiny_config().parameter_breakdown())


class ForwardTest(unittest.TestCase):
    def test_forward_backward_every_mode(self) -> None:
        model, batch = tiny_model(), synthetic_batch()
        generator = torch.Generator().manual_seed(0)
        for mode, p_own in (("gold", 0.0), ("teacher", 0.0), ("own", 0.5)):
            model.zero_grad(set_to_none=True)
            out = model(batch, mode=mode, p_own=p_own, generator=generator)
            for name in ("lm", "ask", "ans", "halt", "loss"):
                self.assertTrue(torch.isfinite(out[name]), (mode, name, out[name]))
            out["loss"].backward()
            grads = [p.grad for p in model.parameters() if p.grad is not None]
            self.assertTrue(grads and all(torch.isfinite(g).all() for g in grads), mode)
            self.assertEqual(int(out["metrics"]["gold_missing"]), 0)
            self.assertGreater(out["ask"].item(), 0.0)
        # "gold" runs two loops per question; "teacher" ceil(|G| / 4) + 3.
        out = model(batch, mode="gold")
        self.assertEqual(int(out["metrics"]["question_loops"]), 2 * batch.size[2])
        out = model(batch, mode="teacher", generator=generator)
        self.assertEqual(int(out["metrics"]["question_loops"]), 4 * batch.size[2])

    def test_controls_run(self) -> None:
        batch = synthetic_batch(seed=1)
        for variant in ("D-noask", "D-noptr"):
            model = tiny_model(variant)
            out = model(batch, mode="teacher")
            out["loss"].backward()
            self.assertTrue(torch.isfinite(out["loss"]), variant)
            answers = model.answer(batch)
            self.assertEqual(tuple(answers.tokens.shape), (batch.size[2], MAX_ANSWER))
        self.assertIsNone(tiny_model("D-noask").writer)
        self.assertEqual(tiny_model("D-noask")(batch)["ask"].item(), 0.0)
        self.assertIsNone(tiny_model("D-noptr").think.binder)

    def test_bf16_autocast_keeps_the_scan_in_fp32(self) -> None:
        model, batch = tiny_model(), synthetic_batch(seed=2)
        with torch.autocast("cpu", dtype=torch.bfloat16):
            out = model(batch, mode="teacher")
            gate = torch.randn(2, 40, 8).bfloat16()
            self.assertEqual(min_gru_scan(gate, gate, 16).dtype, torch.float32)
        out["loss"].backward()
        self.assertTrue(torch.isfinite(out["loss"]))

    def test_scan_matches_the_recurrence(self) -> None:
        gate, candidate = torch.randn(2, 37, 5), torch.randn(2, 37, 5)
        z = torch.sigmoid(gate)
        g = torch.where(candidate >= 0, candidate + 0.5, torch.sigmoid(candidate))
        h, expected = torch.zeros(2, 5), []
        for t in range(37):
            h = (1 - z[:, t]) * h + z[:, t] * g[:, t]
            expected.append(h)
        for chunk in (4, 16, 64):
            torch.testing.assert_close(min_gru_scan(gate, candidate, chunk), torch.stack(expected, 1),
                                       rtol=1e-4, atol=1e-5)

    def test_training_steps_reduce_the_loss(self) -> None:
        model, batch = tiny_model(), synthetic_batch(seed=3)
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3)
        losses = []
        for _ in range(25):
            out = model(batch, mode="teacher", generator=torch.Generator().manual_seed(0))
            optimizer.zero_grad()
            out["loss"].backward()
            optimizer.step()
            losses.append(out["loss"].item())
        self.assertLess(losses[-1], 0.8 * losses[0])


class EntityCopyTest(unittest.TestCase):
    def test_answers_copy_only_entities_already_mentioned(self) -> None:
        batch = synthetic_batch(visits=2, lines=20, seed=13)
        for variant in ("D", "D-noptr"):
            model = tiny_model(variant)
            with torch.no_grad():                    # make every answer token an ENT id
                model.embed.weight[:VOCAB] = 0.0
                model.embed.weight[VOCAB:] = 5.0 * torch.randn(N_ENT, model.config.d_model)
            answers = model.answer(batch)
            mentioned = model._mentions(batch)
            ents = [(q, t - VOCAB) for q, row in enumerate(answers.ids()) for t in row if t >= VOCAB]
            self.assertTrue(ents, variant)
            unmentioned = sum(not bool(mentioned[q, e]) for q, e in ents)
            if variant == "D":
                self.assertEqual(unmentioned, 0)
            else:                                    # D-noptr: ENT ids are ordinary tokens
                self.assertGreater(unmentioned, 0)


class CausalityTest(unittest.TestCase):
    def test_reader_is_causal(self) -> None:
        model, batch = tiny_model(), synthetic_batch(lines=24, seed=4)
        model.eval()
        length = batch.tokens.shape[1]
        with torch.no_grad():
            base = model.read(batch)
            for cut in (5, 16, 17, 40, length - 3):     # inside, at and across 16-token blocks
                changed = batch.tokens.clone()
                changed[:, cut:] = torch.randint(10, VOCAB + N_ENT, changed[:, cut:].shape)
                moved = model.read(VisitBatch(**{**batch.__dict__, "tokens": changed}))
                torch.testing.assert_close(moved[:, :cut], base[:, :cut], rtol=0, atol=1e-5)
                self.assertFalse(torch.allclose(moved[:, cut:], base[:, cut:]))

    def test_no_card_on_or_after_the_question_line_is_scored(self) -> None:
        model, batch = tiny_model(), synthetic_batch(lines=20, seed=5)
        with torch.no_grad():
            store = model.build_store(model.read(batch), batch)
        count = batch.size[2]
        eligible = store.eligible(batch.q_visit, batch.q_line)
        lines = torch.arange(store.lines)
        self.assertFalse((eligible[:, :store.null] & (lines >= batch.q_line.unsqueeze(1))).any())
        self.assertTrue(eligible[:, store.null].all())
        scores = store.ask(torch.randn(count, store.keys.shape[-1]), batch.q_visit, batch.q_line,
                           torch.tensor(10.0), torch.zeros(16))
        self.assertTrue(torch.isinf(scores[:, :store.null][lines >= batch.q_line.unsqueeze(1)]).all())
        self.assertTrue(torch.isfinite(scores[:, store.null]).all())
        # A question on line 0 sees only NULL, also after its cards are fetched.
        first = store.eligible(batch.q_visit[:1], torch.zeros(1, dtype=torch.long),
                               fetched=torch.ones(1, store.lines + 1, dtype=torch.bool))
        self.assertEqual(first.nonzero()[:, 1].tolist(), [store.null])
        self.assertTrue(store.valid.sum() > 0)
        self.assertFalse((store.valid & batch.line_is_question).any())

    def test_answers_ignore_everything_after_the_question(self) -> None:
        batch = synthetic_batch(visits=2, lines=24, seed=6)
        model = eager(tiny_model())
        model.eval()
        pick = int(batch.size[2] // 2)
        visit, cut = int(batch.q_visit[pick]), int(batch.q_span[pick, 1])
        changed = batch.tokens.clone()
        tail = changed[visit, cut:batch.lengths[visit]]
        changed[visit, cut:batch.lengths[visit]] = torch.randint(10, VOCAB + N_ENT, tail.shape)
        base = model.answer(batch)
        moved = model.answer(VisitBatch(**{**batch.__dict__, "tokens": changed}))
        same = (batch.q_visit != visit) | (batch.q_span[:, 1] <= cut)
        self.assertTrue(same.sum() >= 2)
        torch.testing.assert_close(moved.halt_prob[same], base.halt_prob[same], rtol=0, atol=1e-5)
        self.assertTrue(torch.equal(moved.tokens[same], base.tokens[same]))
        self.assertTrue(torch.equal(moved.fetched[same], base.fetched[same]))
        lines = torch.arange(base.fetched.shape[1] - 1)
        late = base.fetched[:, :-1] & (lines >= batch.q_line.unsqueeze(1))
        self.assertFalse(late.any())
        self.assertTrue(base.fetched[:, :-1].any())


class StoreTest(unittest.TestCase):
    def test_planted_keys_set_cross_entropy_goes_to_zero(self) -> None:
        torch.manual_seed(0)
        visits, lines, dim, count = 2, 30, 16, 8
        store = CardStore(
            keys=F.normalize(torch.randn(visits, lines, dim), dim=-1), values=torch.zeros(visits, lines, 4),
            valid=torch.ones(visits, lines, dtype=torch.bool), tags=torch.zeros(visits, lines, dtype=torch.long),
            ents=torch.full((visits, lines, MAX_LINE_ENTS), -1), line_start=torch.zeros(visits, lines, dtype=torch.long),
            line_len=torch.ones(visits, lines, dtype=torch.long),
            null_key=F.normalize(torch.randn(dim), dim=0), null_value=torch.zeros(4))
        q_visit = torch.tensor([0, 0, 1, 1, 0, 1, 0, 1])
        q_line = torch.tensor([10, 29, 5, 20, 25, 28, 3, 15])
        gold_lines = torch.full((count, MAX_GOLD), -1)
        for i, lines_ in enumerate([[2, 7], [0, 14, 28], [4], [1, 19], [], [3, 9, 27], [], [11]]):
            gold_lines[i, :len(lines_)] = torch.tensor(lines_, dtype=torch.long)
        gold, told, missing = store.gold(gold_lines, q_visit, q_line)
        self.assertEqual(int(missing.sum()), 0)
        self.assertEqual(gold[:, store.null].tolist(), (~told).tolist())
        fetched = torch.zeros(count, lines + 1, dtype=torch.bool)
        fetched[1, 14] = fetched[5, 9] = True          # already fetched: out of the target and the softmax
        query = torch.randn(count, dim, requires_grad=True)
        log_kappa = torch.tensor(2.3, requires_grad=True)
        age_bias = torch.zeros(16, requires_grad=True)
        optimizer = torch.optim.Adam([query, log_kappa, age_bias], lr=0.05)
        need = gold & ~fetched
        for _ in range(300):
            scores = store.ask(query, q_visit, q_line, log_kappa.exp(), age_bias, fetched)
            loss = set_cross_entropy(scores, need).mean()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        self.assertLess(float(loss), 0.02)
        # The set target only needs the mass on some card of G minus F: the best card is gold.
        best = store.top(scores.detach(), 1)[:, 0]
        self.assertTrue(need[torch.arange(count), best].all())
        self.assertFalse(fetched[torch.arange(count), best].any())

    def test_wipes_return_only_window_cards(self) -> None:
        batch = synthetic_batch(visits=2, lines=24, seed=7)
        model = eager(tiny_model())
        model.eval()
        # Window = the last 6 lines before each question (at least line 1).
        window = (batch.q_line - 6).clamp_min(1)
        with torch.no_grad():
            store = model.build_store(model.read(batch), batch).wipe(window)
        eligible = store.eligible(batch.q_visit, batch.q_line)
        lines = torch.arange(store.lines)
        outside = (lines < window.unsqueeze(1)) | (lines >= batch.q_line.unsqueeze(1))
        self.assertFalse((eligible[:, :store.null] & outside).any())
        self.assertTrue(eligible[:, store.null].all())
        for wipe in ("store", "full"):
            answers = model.answer(batch, wipe=wipe, window_line=window)
            self.assertFalse((answers.fetched[:, :-1] & outside).any(), wipe)
            self.assertTrue(answers.fetched[:, :-1].any(), wipe)
            chosen = answers.first_top
            ok = (chosen == -1) | ((chosen >= window.unsqueeze(1)) & (chosen < batch.q_line.unsqueeze(1)))
            self.assertTrue(ok.all(), wipe)

    def test_full_wipe_rereads_only_the_window(self) -> None:
        batch = synthetic_batch(visits=2, lines=20, seed=8)
        window = (batch.q_line - 4).clamp_min(0)
        cropped = crop_to_windows(batch, window)
        self.assertEqual(cropped.size[0], batch.size[2])
        for q in range(batch.size[2]):
            visit = int(batch.q_visit[q])
            start = int(batch.line_start[visit, window[q]])
            end = int(batch.q_span[q, 1])
            self.assertTrue(torch.equal(cropped.tokens[q, :end - start], batch.tokens[visit, start:end]))
            self.assertTrue((cropped.line_start[q, :window[q]] == -1).all())
        model = tiny_model()
        with torch.no_grad():
            store = model.build_store(model.read(cropped), cropped)
        lines = torch.arange(store.lines)
        self.assertFalse((store.valid & (lines < window.unsqueeze(1))).any())

    def test_evaluation_is_read_only(self) -> None:
        model, batch = tiny_model(), synthetic_batch(seed=9)
        with torch.no_grad():
            store = model.build_store(model.read(batch), batch)
        with read_only(model, stores=[store]):
            model.answer(batch)
            model.answer(batch, wipe="store", window_line=(batch.q_line - 3).clamp_min(0))
        with self.assertRaises(ReadOnlyViolation):
            with read_only(model, stores=[store]):
                model.answer(batch)
                with torch.no_grad():
                    model.heads.halt.weight.add_(1.0)
        with self.assertRaises(ReadOnlyViolation):
            with read_only(model, stores=[store]):
                store.values.add_(1.0)


class FlopTest(unittest.TestCase):
    def test_core_hand_count_matches_the_counter(self) -> None:
        for size, vocab, context, batch in (("4M", 6372, 768, 1), (None, 64, 64, 4)):
            config = (CoreConfig.preset(size, vocab, context) if size
                      else CoreConfig(vocab, context, d_model=32, n_layers=2, n_heads=2))
            torch.manual_seed(0)
            model = Core(config)
            counted = measure_core(model, torch.randint(0, vocab, (batch, context + 1)))
            hand = core_flops_per_token(config, context) * batch * context
            self.assertLess(abs(counted - hand) / hand, 0.10, (size, counted, hand))

    def test_mini_fit_and_hand_count(self) -> None:
        model = tiny_model()
        samples = []
        for visits, lines, seed in ((1, 12, 0), (2, 16, 1), (3, 20, 2), (2, 30, 3)):
            batch = synthetic_batch(visits=visits, lines=lines, seed=seed)
            sample = measure_mini(model, batch, mode="teacher",
                                  generator=torch.Generator().manual_seed(seed))
            hand = mini_hand_count(model.config, batch, sample.question_loops)
            self.assertLess(abs(sample.flops - hand) / hand, 0.15, (sample, hand))
            samples.append(sample)
        fit = fit_flops(samples)
        self.assertGreater(fit.a, 0)
        self.assertGreater(fit.b, 0)
        self.assertLess(fit.worst, 0.15)


if __name__ == "__main__":
    unittest.main()
