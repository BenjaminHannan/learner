"""Steal 4, `engram`: hashed name lookup on card values (design/steals-2026-10-17/SPEC.md section 4)."""
from __future__ import annotations

import math
import os
from pathlib import Path
import subprocess
import sys
import unittest

import torch

from premonition.batch import NameTable
from premonition.config import MiniConfig
from premonition.model import PremonitionMini, _norm, engram_indices
from tests.test_premonition_model import synthetic_batch, tiny_config, tiny_model

ROOT = Path(__file__).resolve().parents[1]
KNOWN = {"Name0": (252, 141, 589, 499), "Ent3": (102, 762, 585, 322), "<ent 5>": (589, 79, 434, 369),
         "Alice": (419, 559, 45, 194), "Brookhaven": (64, 1014, 993, 107)}   # blake2b("h:spelling") % 1024


def model(seed: int = 0, **overrides) -> PremonitionMini:
    return tiny_model(seed=seed, engram=True, **overrides)


def with_ents(batch, ent: int, spellings: list):
    """Every named line of every visit mentions only entity `ent`; visit v spells it spellings[v]."""
    batch.line_ents[:] = torch.where(batch.line_ents >= 0, torch.full_like(batch.line_ents, ent), batch.line_ents)
    batch.names = [NameTable({ent: spelling}) for spelling in spellings]
    return batch


class HashTest(unittest.TestCase):
    def test_known_indices(self) -> None:
        for spelling, expected in KNOWN.items():
            self.assertEqual(engram_indices(spelling, 4, 1024), expected)

    def test_indices_are_reduced_mod_rows(self) -> None:
        got = engram_indices("Alice", 4, 512)
        self.assertTrue(all(0 <= i < 512 for i in got))
        self.assertEqual(got, tuple(i % 512 for i in engram_indices("Alice", 4, 1024)))

    def test_deterministic_across_processes(self) -> None:
        code = "from premonition.model import engram_indices as f; print(f('Alice', 4, 1024))"
        for hash_seed in ("0", "12345"):
            out = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, check=True, capture_output=True,
                                 text=True, env=dict(os.environ, PYTHONHASHSEED=hash_seed)).stdout
            self.assertEqual(out.strip(), str(KNOWN["Alice"]))


class StructureTest(unittest.TestCase):
    def test_modules_only_under_the_flag(self) -> None:
        off = tiny_model()
        self.assertFalse(any("engram" in name for name, _ in off.named_parameters()))
        on = model()
        writer, config = on.writer, on.config
        self.assertEqual(len(writer.engram_tables), config.engram_heads)
        for table in writer.engram_tables:
            self.assertEqual(table.weight.shape, (config.engram_rows, config.d_model // config.engram_heads))
        self.assertEqual(writer.engram_key.weight.shape, (config.d_model,) * 2)
        self.assertEqual(on.parameter_breakdown(), config.parameter_breakdown())

    def test_full_size_cost(self) -> None:
        extra = MiniConfig.preset("D", engram=True).num_parameters() - 2_013_140
        self.assertEqual(extra, 164_096)

    def test_tables_use_the_small_embedding_init(self) -> None:
        self.assertAlmostEqual(model().writer.engram_tables[0].weight.std().item(), 0.02, delta=0.003)


class ValueTest(unittest.TestCase):
    def setUp(self) -> None:
        self.batch = synthetic_batch(visits=2, lines=20, seed=4)
        self.model = model()
        self.writer = self.model.writer
        shape = (*self.batch.line_start.shape, self.model.config.d_model)
        self.pooled = torch.randn(shape, generator=torch.Generator().manual_seed(0))

    def values(self, batch=None, pooled=None) -> torch.Tensor:
        return self.writer._values(self.pooled if pooled is None else pooled, batch or self.batch)

    def lookup(self, batch, visit: int, line: int) -> torch.Tensor:
        """e of one line by hand, straight from the table rows."""
        rows = []
        for ent in batch.line_ents[visit, line].tolist():
            if ent >= 0:
                idx = engram_indices(batch.names[visit].spelling(ent), self.writer.engram_heads,
                                     self.writer.engram_rows)
                rows.append(torch.cat([t.weight[i] for t, i in zip(self.writer.engram_tables, idx)]))
        return torch.stack(rows).mean(0)

    def test_matches_the_formula_by_hand(self) -> None:
        d, checked = self.model.config.d_model, 0
        with torch.no_grad():
            got = self.values()
            for visit in range(2):
                for line in range(20):
                    if (self.batch.line_ents[visit, line] >= 0).any():
                        e, p = self.lookup(self.batch, visit, line), self.pooled[visit, line]
                        alpha = torch.sigmoid((_norm(p) * _norm(self.writer.engram_key(e))).sum() / math.sqrt(d))
                        want = self.writer.value(p) + alpha * self.writer.engram_value(e)
                        torch.testing.assert_close(got[visit, line], want, rtol=1e-5, atol=1e-6)
                        checked += 1
        self.assertGreater(checked, 5)

    def test_lines_without_names_are_unchanged(self) -> None:
        with torch.no_grad():
            got, base = self.values(), self.writer.value(self.pooled)
        named = (self.batch.line_ents >= 0).any(-1)
        self.assertTrue(named.any() and not named.all())
        self.assertTrue(torch.equal(got[~named], base[~named]))
        self.assertFalse(torch.equal(got[named], base[named]))

    def test_a_zero_value_projection_adds_nothing(self) -> None:
        with torch.no_grad():
            self.writer.engram_value.weight.zero_()
            self.assertTrue(torch.equal(self.values(), self.writer.value(self.pooled)))

    def test_same_spelling_in_two_visits_gives_the_same_e(self) -> None:
        batch = with_ents(synthetic_batch(visits=2, lines=20, seed=4), 3, ["Maren", "Maren"])
        batch.line_ents[1] = batch.line_ents[0]
        line = int((batch.line_ents[0] >= 0).any(-1).nonzero()[0])
        self.assertTrue(torch.equal(self.lookup(batch, 0, line), self.lookup(batch, 1, line)))
        pooled = self.pooled.clone()
        pooled[1] = pooled[0]
        with torch.no_grad():
            out = self.values(batch, pooled)
        self.assertTrue(torch.equal(out[0], out[1]))

    def test_different_spellings_give_different_e(self) -> None:
        batch = with_ents(synthetic_batch(visits=2, lines=20, seed=4), 3, ["Maren", "Osric"])
        batch.line_ents[1] = batch.line_ents[0]
        line = int((batch.line_ents[0] >= 0).any(-1).nonzero()[0])
        self.assertFalse(torch.equal(self.lookup(batch, 0, line), self.lookup(batch, 1, line)))
        pooled = self.pooled.clone()
        pooled[1] = pooled[0]
        with torch.no_grad():
            out = self.values(batch, pooled)
        self.assertFalse(torch.equal(out[0, line], out[1, line]))

    def test_an_entity_without_a_spelling_counts_as_no_name(self) -> None:
        """Review round 4, item 4: no spelling (empty NameTable, or no NameTable for the visit) means no Engram
        addition. ENT ids are per-visit variables, so they must never share a fallback row."""
        batch = synthetic_batch(visits=2, lines=20, seed=4)
        pooled = torch.randn(2, batch.line_start.shape[1], self.model.config.d_model,
                             generator=torch.Generator().manual_seed(1))
        with torch.no_grad():
            plain = self.model.writer.value(pooled)
            batch.names = [NameTable({}), NameTable({})]                         # no spellings at all
            self.assertTrue(torch.equal(self.values(batch, pooled), plain))
            batch.names = [NameTable({e: f"Name{e}" for e in range(16)})]        # visit 1 has no NameTable
            out = self.values(batch, pooled)
            self.assertTrue(torch.equal(out[1], plain[1]))
            named = (batch.line_ents[0] >= 0).any(-1)
            self.assertTrue(named.any())
            self.assertFalse(torch.equal(out[0][named], plain[0][named]))
            batch.names = [NameTable({}), NameTable({e: f"Name{e}" for e in range(16)})]
            out = self.values(batch, pooled)
            self.assertTrue(torch.equal(out[0], plain[0]))                       # visit 0's ids get no row
            ent = int(batch.line_ents[0][batch.line_ents[0] >= 0][0])
            batch.names = [NameTable({e: f"Name{e}" for e in range(16) if e != ent})] * 2
            out = self.values(batch, pooled)                                     # only `ent` lacks a spelling
            alone = (batch.line_ents[0] == ent).any(-1) & ((batch.line_ents[0] >= 0).sum(-1) == 1)
            if alone.any():
                self.assertTrue(torch.equal(out[0][alone], plain[0][alone]))

    def test_several_names_pool_by_mean(self) -> None:
        batch = synthetic_batch(visits=1, lines=20, seed=4)
        batch.names = [NameTable({e: f"N{e}" for e in range(16)})]
        batch.line_ents[0, 2] = torch.tensor([1, 2, -1, -1])
        two = self.lookup(batch, 0, 2)
        batch.line_ents[0, 2] = torch.tensor([1, -1, -1, -1])
        one = self.lookup(batch, 0, 2)
        batch.line_ents[0, 2] = torch.tensor([2, -1, -1, -1])
        other = self.lookup(batch, 0, 2)
        torch.testing.assert_close(two, (one + other) / 2)
        batch.line_ents[0, 2] = torch.tensor([1, 2, -1, -1])         # and the vectorised path agrees
        with torch.no_grad():
            got = self.values(batch, self.pooled[:1])[0, 2]
            alpha = torch.sigmoid((_norm(self.pooled[0, 2]) * _norm(self.writer.engram_key(two))).sum()
                                  / math.sqrt(two.numel()))
            want = self.writer.value(self.pooled[0, 2]) + alpha * self.writer.engram_value(two)
        torch.testing.assert_close(got, want, rtol=1e-5, atol=1e-6)

    def test_gradient_reaches_tables_and_projections(self) -> None:
        out = self.model(self.batch, mode="teacher", generator=torch.Generator().manual_seed(0))
        out["loss"].backward()
        for name, param in self.writer.named_parameters():
            if "engram" in name:
                self.assertIsNotNone(param.grad, name)
                self.assertGreater(param.grad.abs().sum().item(), 0, name)
        touched = sum(int((t.weight.grad.abs().sum(-1) > 0).sum()) for t in self.writer.engram_tables)
        self.assertGreater(touched, 0)
        self.assertLess(touched, sum(t.weight.shape[0] for t in self.writer.engram_tables))   # sparse rows

    def test_the_flag_changes_the_loss_and_stays_finite(self) -> None:
        batch = synthetic_batch(visits=2, lines=24, seed=2)
        off, on = tiny_model(), model()
        on.load_state_dict(off.state_dict(), strict=False)
        a = off(batch, mode="gold", generator=torch.Generator().manual_seed(0))["loss"]
        b = on(batch, mode="gold", generator=torch.Generator().manual_seed(0))["loss"]
        self.assertTrue(torch.isfinite(b))
        self.assertNotEqual(a.item(), b.item())

    def test_runs_under_cpu_autocast(self) -> None:
        with torch.autocast("cpu", dtype=torch.bfloat16):
            out = self.model(self.batch, mode="own", p_own=0.5, generator=torch.Generator().manual_seed(0))
        self.assertTrue(torch.isfinite(out["loss"]))


if __name__ == "__main__":
    unittest.main()
