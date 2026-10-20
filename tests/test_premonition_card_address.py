"""S3 `card_address` pre-run tests (design/info-constraints/S3-STAGE0-CARD.md §2). DRAFT.

1. Flag off is bit-identical to D + S2 as committed at 90077ef2b (coordinator-reviewed): with only
   `decoder_raw_cards` on, init, RNG, the three training modes, answers with wipes, `answer_with_gold` and trainer
   steps match the modules loaded from git at that commit. Flag-off identity to 73b8e0224 (everything off) is
   `tests/test_premonition_decoder_raw_cards.py`, which runs on the same code.
2. Paired start: D + S2 + S3 has every shared weight and the global RNG stream of D + S2 at the same seed.
3. The address block follows the ring: same slot as the card and raw rows, overwritten together, never valid.
4. The decoder takes the card rows' and raw rows' keys from the address rows and every value from the rows.
5. Every mode trains with finite losses and gradients; refusals; hand FLOPs follow the measured increment.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import types
import unittest

import torch

from premonition import train as ptrain
from premonition.config import MiniConfig
from premonition.model import ROW_CARD, _norm, PremonitionMini
from premonition.store import age_bucket
from tests.test_premonition_decoder_raw_cards import differences, everything
from tests.test_premonition_model import VOCAB, synthetic_batch

S2_COMMIT = "90077ef2b"
ROOT = Path(__file__).resolve().parents[1]


def _git_source(path: str) -> str:
    try:
        return subprocess.run(["git", "show", f"{S2_COMMIT}:{path}"], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise unittest.SkipTest(f"S2 commit {S2_COMMIT} not available: {error}") from None


def _load(name: str, source: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = f"<{name}>"
    sys.modules[name] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


def s2_modules() -> tuple[types.ModuleType, ...]:
    """(config, store, model, train) exactly as at the reviewed S2 commit."""
    if "premonition_s2_train" in sys.modules:
        return tuple(sys.modules[f"premonition_s2_{name}"] for name in ("config", "store", "model", "train"))
    config = _load("premonition_s2_config", _git_source("premonition/config.py"))
    store = _load("premonition_s2_store", _git_source("premonition/store.py"))
    model = _load("premonition_s2_model", _git_source("premonition/model.py").replace(
        "from premonition.store import", "from premonition_s2_store import").replace(
        "from premonition.config import", "from premonition_s2_config import"))
    train = _load("premonition_s2_train", _git_source("premonition/train.py").replace(
        "from premonition.model import", "from premonition_s2_model import").replace(
        "from premonition.config import", "from premonition_s2_config import"))
    return config, store, model, train


def tiny(variant: str = "D", **flags) -> MiniConfig:
    return MiniConfig.preset(variant, "tiny", vocab_size=VOCAB, window=16, max_loops=6, **flags)


def build(config, seed: int, cls=PremonitionMini):
    torch.manual_seed(seed)
    model = cls(config)
    return model, torch.get_rng_state()


def preloaded(model, batch, cards=None):
    """An episode with each question's gold card inserted (or `cards` [Q, 1])."""
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    episode = model._start(batch, hidden, store, model._mentions(batch))
    everyone = torch.arange(batch.q_visit.shape[0])
    if cards is None:
        gold, _, _ = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
        cards = torch.where(gold, torch.arange(gold.shape[1]),
                            torch.full_like(gold, -1, dtype=torch.long)).topk(1, 1).values
    model._insert(episode, store, everyone, cards)
    return store, episode, everyone


class FlagOffMatchesReviewedS2Test(unittest.TestCase):
    def test_only_decoder_raw_cards_on_matches_90077ef2b(self) -> None:
        s2_config, _, s2_model, s2_train = s2_modules()
        for variant in ("D", "D-noptr"):
            for seed in (0, 1):
                with self.subTest(variant=variant, seed=seed):
                    mine = everything(PremonitionMini, tiny(variant, decoder_raw_cards=True), ptrain, seed)
                    theirs = everything(s2_model.PremonitionMini, s2_config.MiniConfig.preset(
                        variant, "tiny", vocab_size=VOCAB, window=16, max_loops=6, decoder_raw_cards=True),
                        s2_train, seed)
                    self.assertEqual(differences(mine, theirs), [])


class CardAddressTest(unittest.TestCase):
    def test_paired_start(self) -> None:
        for size in ("tiny", "full"):
            with self.subTest(size=size):
                plain = (tiny("D", decoder_raw_cards=True) if size == "tiny"
                         else MiniConfig.preset("D", "full", decoder_raw_cards=True))
                control, rng_c = build(plain, 3)
                treated, rng_t = build(plain.with_(card_address=True), 3)
                self.assertTrue(torch.equal(rng_c, rng_t))
                shared = dict(control.named_parameters())
                mine = dict(treated.named_parameters())
                self.assertEqual(sorted(set(mine) - set(shared)), ["address.pool.bias", "address.pool.weight",
                                                                   "address.proj.bias", "address.proj.weight"])
                for name, value in shared.items():
                    self.assertTrue(torch.equal(value, mine[name]), name)
                self.assertTrue(torch.equal(treated.address.pool.weight, treated.writer.pool.weight))
                self.assertEqual(treated.config.parameter_breakdown(), treated.parameter_breakdown())
        other, _ = build(tiny("D", decoder_raw_cards=True, card_address=True), 4)
        self.assertFalse(torch.equal(other.address.proj.weight,
                                     build(tiny("D", decoder_raw_cards=True, card_address=True), 3)[0]
                                     .address.proj.weight))                         # seed-dependent init

    def test_refusals(self) -> None:
        from premonition.answer_path import CardBypassMini
        with self.assertRaises(ValueError):
            tiny("D", card_address=True)                                   # needs S2
        with self.assertRaises(ValueError):
            tiny("D-noask", decoder_raw_cards=True, card_address=True)
        with self.assertRaises(ValueError):
            CardBypassMini(tiny("D", decoder_raw_cards=True, card_address=True))

    def test_every_mode_trains_and_answers(self) -> None:
        for variant in ("D", "D-noptr"):
            with self.subTest(variant=variant):
                model, _ = build(tiny(variant, decoder_raw_cards=True, card_address=True), 0)
                batch = synthetic_batch(seed=3)
                for mode in ("gold", "teacher", "own"):
                    model.zero_grad(set_to_none=True)
                    out = model(batch, mode=mode, p_own=0.5, generator=torch.Generator().manual_seed(0))
                    out["loss"].backward()
                    self.assertTrue(torch.isfinite(out["loss"]))
                    for name, param in model.named_parameters():
                        if param.grad is not None:
                            self.assertTrue(torch.isfinite(param.grad).all(), name)
                    self.assertIsNotNone(model.address.proj.weight.grad)          # the address is trained
                model.eval()
                model.answer(batch)
                ptrain.answer_with_gold(model, batch)
                window = (batch.q_line - 6).clamp_min(1)
                model.answer(batch, wipe="store", window_line=window)
                model.answer(batch, wipe="full", window_line=window)

    def test_address_rows_follow_the_ring_and_think_skips_them(self) -> None:
        model, _ = build(tiny("D", decoder_raw_cards=True, card_address=True, card_rows=2, top_k=1), 0)
        model.eval()
        config = model.config
        batch = synthetic_batch(seed=7)
        think, cards = config.rows, config.cards
        address = slice(think + cards, think + 2 * cards)
        with torch.no_grad():
            hidden = model.read(batch)
            store = model.build_store(hidden, batch)
            episode = model._start(batch, hidden, store, model._mentions(batch))
            self.assertEqual(episode.x.shape[1], think + 2 * cards)
            everyone = torch.arange(batch.q_visit.shape[0])
            seen = []
            for line in range(3):                                     # three distinct cards into two slots
                model._insert(episode, store, everyone, torch.full((everyone.numel(), 1), line))
                slot = line % 2
                visit = batch.q_visit
                want = (store.addresses[visit, line].float()
                        + model.think.age(age_bucket(batch.q_line - line, config.age_buckets)).float()
                        + model.think.row_type.weight[ROW_CARD].float())
                self.assertTrue(torch.allclose(episode.x[:, think + cards + slot], want))
                seen.append(episode.x[:, address].clone())
            self.assertFalse(episode.valid[:, address].any())               # never memory itself
            self.assertFalse(torch.equal(seen[2][:, 0], seen[0][:, 0]))     # third card overwrote slot 0
            self.assertTrue(torch.equal(seen[2][:, 1], seen[1][:, 1]))      # and kept slot 1
            before = episode.x[:, think:].clone()
            model._step(episode, everyone, 0, store)
            self.assertTrue(torch.equal(episode.x[:, think:], before))      # Think skips raw + address rows

    def test_keys_from_address_values_from_rows(self) -> None:
        model, _ = build(tiny("D", decoder_raw_cards=True, card_address=True), 0)
        model.eval()
        config = model.config
        think, cards, base = config.rows, config.cards, model._card_base
        batch = synthetic_batch(seed=5)
        seen = []
        handle = model.decoder.cross_kv.register_forward_hook(lambda _m, args, _out: seen.append(args[0].detach()))
        try:
            with torch.no_grad():
                store, episode, everyone = preloaded(model, batch)
                model._step(episode, everyone, 0, store)
                inputs = batch.tokens[batch.q_visit, batch.q_span[:, 1] - 1].unsqueeze(1)
                model._decode_logits(episode.x, episode.valid, inputs)
        finally:
            handle.remove()
        self.assertEqual(len(seen), 2)                                       # values pass, then keys pass
        values_in, keys_in = seen
        x = episode.x
        address = x[:, think + cards:]
        self.assertEqual(values_in.shape[1], think + cards)
        self.assertTrue(torch.equal(values_in, _norm(x[:, :think + cards])))           # V from every row
        self.assertTrue(torch.equal(keys_in[:, base:base + cards], _norm(address)))     # K of card rows
        self.assertTrue(torch.equal(keys_in[:, think:], _norm(address)))                # K of raw rows
        self.assertTrue(torch.equal(keys_in[:, :base], _norm(x[:, :base])))             # other K unchanged
        self.assertTrue(torch.equal(keys_in[:, base + cards:think], _norm(x[:, base + cards:think])))

    def test_flop_hand_count_follows_the_measured_increment(self) -> None:
        from premonition.flops import measure_mini, mini_hand_count
        s2, _ = build(tiny("D", decoder_raw_cards=True), 0)
        s3, _ = build(tiny("D", decoder_raw_cards=True, card_address=True), 0)
        for visits, lines, seed in ((2, 16, 1), (2, 30, 3)):
            batch = synthetic_batch(visits=visits, lines=lines, seed=seed)
            a = measure_mini(s2, batch, mode="teacher", generator=torch.Generator().manual_seed(seed))
            b = measure_mini(s3, batch, mode="teacher", generator=torch.Generator().manual_seed(seed))
            self.assertEqual(a.question_loops, b.question_loops)
            measured = b.flops - a.flops
            hand = mini_hand_count(s3.config, batch, b.question_loops) - mini_hand_count(s2.config, batch,
                                                                                        a.question_loops)
            self.assertGreater(measured, 0)
            self.assertLess(abs(measured - hand) / measured, 0.25, (measured, hand))


if __name__ == "__main__":
    unittest.main()
