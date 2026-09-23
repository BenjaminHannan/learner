"""concept-toy20 (ct20-v1.1) PUBLIC loader.

The only module a learner, dataset or training loop is allowed to import.

It reads the frozen public tensors written by
`scripts/fable_concepttoy20_sim.py calibration-data` and nothing else.  It imports
NOTHING from the simulator module, so no world object, coefficient, family label,
verb map, latent state, noise-free response, query target or normalization constant
can reach a model through this path -- there is no code path from here to them.

It deliberately cannot see:
  * `private/` (it refuses to read any path under a `private` directory),
  * panel identity, horizon or pair membership,
  * the true `world_id` (public files carry an opaque 16-hex alias instead).

Fields it does expose are exactly the build plan's public batch contract:
reset/property tensor and action tokens (inside `records`), masked observed A targets,
fitting/selection episode roles, detector query IDs and padding masks.

    from fable_concepttoy20_public import PublicDataset
    dataset = PublicDataset('artifacts/fable-concept-toy20-20260920/calibration')
    for world_public_id, outer_split in dataset.worlds():
        support = dataset.support(world_public_id, budget=32)
        queries = dataset.queries(world_public_id)
        audit = dataset.fitting_audit(world_public_id)

Ruling B8: `outer_split` is COORDINATOR BOOKKEEPING.  `worlds()` returns it so a driver
can pick a pool, but it appears in no tensor, no batch object and no fitting choice.
The public hints this loader exposes are "randomly relabeled action IDs with public
argument/dose structure", not fully anonymous action semantics.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

RECORD_WIDTH = 44
N_RECORDS_FULL = 17
DETECTOR_WIDTH = 9
N_TRANSITIONS = 8
ROLE_FIT, ROLE_SELECTION = 0, 1

SL_PROPERTIES = slice(0, 24)
SL_ACTION = slice(24, 29)
SL_SOURCE = slice(29, 33)
SL_DESTINATION = slice(33, 38)
IX_DOSE = 38
IX_SENSOR = 39
IX_SENSOR_PRESENT = 40
SL_RECORD_TYPE = slice(41, 44)
RT_RESET, RT_QUERY, RT_OBSERVED = 0, 1, 2

_FORBIDDEN_ARRAYS = ('latent', 'truth', 'noise_free', 'noisy', 'coefficient', 'family')


class PublicBoundaryError(RuntimeError):
    """Raised when the loader is pointed at anything outside the public tensors."""


@dataclass(frozen=True)
class SupportBatch:
    """One world's nested discovery support set at a given budget."""
    world_public_id: str
    budget: int
    records: np.ndarray            # (n_episodes, 17, 44) float32
    padding_mask: np.ndarray       # (n_episodes, 17) uint8
    episode_role: np.ndarray       # (n_episodes,) int8, 0 fit / 1 selection
    observed_target: np.ndarray    # (n_episodes, 8) float32, zero where absent
    observed_present: np.ndarray   # (n_episodes, 8) uint8

    @property
    def n_episodes(self) -> int:
        return int(self.records.shape[0])

    @property
    def n_transitions(self) -> int:
        return self.n_episodes * N_TRANSITIONS

    def fit_indices(self) -> np.ndarray:
        return np.flatnonzero(self.episode_role == ROLE_FIT)

    def selection_indices(self) -> np.ndarray:
        return np.flatnonzero(self.episode_role == ROLE_SELECTION)


@dataclass(frozen=True)
class QueryBatch:
    """One world's 96 scored prediction points.  Carries no target of any kind."""
    world_public_id: str
    records: np.ndarray            # (96, 17, 44) float32
    padding_mask: np.ndarray       # (96, 17) uint8
    n_records: np.ndarray          # (96,) int32
    query_index: np.ndarray        # (96,) int32, row at which the prediction is read
    detector: np.ndarray           # (96, 9) float32
    record_id: list[str]           # opaque join keys for the private evaluator


@dataclass(frozen=True)
class FittingAuditBatch:
    """The deterministic start-up / fitting-audit set (prereg section 8, ruling C10).

    One case per (fit episode, horizon) at that episode's LAST eligible observed
    endpoint.  Predictions are read at `query_index`, exactly like a query batch.
    `observed_label` is the training label the learner already received in the support
    tensors; the noise-free response stays with the evaluator.

    Score this set ONCE at initialization and ONCE at the fixed B=512 endpoint, with the
    same cases both times, and save both prediction sets keyed by `audit_id`.
    """
    world_public_id: str
    records: np.ndarray            # (n_audit, 17, 44) float32
    padding_mask: np.ndarray       # (n_audit, 17) uint8
    n_records: np.ndarray          # (n_audit,) int32
    query_index: np.ndarray        # (n_audit,) int32
    detector: np.ndarray           # (n_audit, 9) float32
    observed_label: np.ndarray     # (n_audit,) float32, the training label
    episode_index: np.ndarray      # (n_audit,) int32
    horizon: np.ndarray            # (n_audit,) int32
    endpoint: np.ndarray           # (n_audit,) int32, 1-based
    audit_id: list[str]            # opaque join keys for the private evaluator


@dataclass(frozen=True)
class TaskBFittingBatch:
    """Task-B fitting batch: task-A records plus B labels in a TARGET-ONLY field.

    `b_label` is never concatenated into `records` and must never be given to a state
    updater or encoder; it is a training target only.
    """
    world_public_id: str
    records: np.ndarray
    padding_mask: np.ndarray
    observed_target: np.ndarray
    observed_present: np.ndarray
    b_detector: np.ndarray
    b_label: np.ndarray            # target-only


class PublicDataset:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        public = self.root / 'public'
        self.public_root = public if public.is_dir() else self.root
        if self.public_root.name != 'public':
            raise PublicBoundaryError(
                f'{self.root} has no public/ directory; the loader reads public files only')
        self.index: dict[str, Any] = json.loads(
            (self.public_root / 'worlds.json').read_text(encoding='utf-8'))

    # -- boundary ----------------------------------------------------------------------
    def _array(self, world_public_id: str, name: str) -> np.ndarray:
        if any(token in name for token in _FORBIDDEN_ARRAYS):
            raise PublicBoundaryError(f'{name!r} is not a public array')
        base = self.public_root.resolve()
        path = (self.public_root / world_public_id / f'{name}.npy').resolve()
        if not path.is_relative_to(base):
            raise PublicBoundaryError(f'{path} is outside the public tree')
        # Checked RELATIVE to the public root: an absolute check would match macOS's
        # own /private prefix on a temporary directory.
        if 'private' in path.relative_to(base).parts:
            raise PublicBoundaryError(f'{path} is outside the public tree')
        return np.load(path)

    # -- listing -----------------------------------------------------------------------
    def worlds(self) -> list[tuple[str, str]]:
        return [(row['world_public_id'], row['outer_split'])
                for row in self.index['worlds']]

    def worlds_in_split(self, outer_split: str) -> list[str]:
        return [wpid for wpid, split in self.worlds() if split == outer_split]

    def budgets(self) -> list[int]:
        return list(self.index['budgets'])

    # -- batches -----------------------------------------------------------------------
    def support(self, world_public_id: str, budget: int | None = None) -> SupportBatch:
        """Nested prefix: budget=32 returns the first four episodes, 64 the first eight,
        and so on.  Selection episodes are inside the prefix and are not free."""
        rung = self._array(world_public_id, 'support_budget_rung')
        records = self._array(world_public_id, 'support_records')
        if budget is None:
            keep = np.arange(records.shape[0])
            budget = int(keep.size * N_TRANSITIONS)
        else:
            if budget not in self.budgets():
                raise ValueError(f'budget {budget} is not a registered rung')
            keep = np.flatnonzero(rung <= self.budgets().index(budget))
        return SupportBatch(
            world_public_id=world_public_id, budget=int(budget),
            records=records[keep],
            padding_mask=self._array(world_public_id, 'support_padding_mask')[keep],
            episode_role=self._array(world_public_id, 'support_episode_role')[keep],
            observed_target=self._array(world_public_id, 'support_observed_target')[keep],
            observed_present=self._array(world_public_id, 'support_observed_present')[keep],
        )

    def queries(self, world_public_id: str) -> QueryBatch:
        ids = json.loads((self.public_root / world_public_id / 'query_record_ids.json')
                         .read_text(encoding='utf-8'))
        return QueryBatch(
            world_public_id=world_public_id,
            records=self._array(world_public_id, 'query_records'),
            padding_mask=self._array(world_public_id, 'query_padding_mask'),
            n_records=self._array(world_public_id, 'query_n_records'),
            query_index=self._array(world_public_id, 'query_index'),
            detector=self._array(world_public_id, 'query_detector'),
            record_id=list(ids),
        )

    def fitting_audit(self, world_public_id: str) -> FittingAuditBatch:
        keys = json.loads((self.public_root / world_public_id / 'audit_keys.json')
                          .read_text(encoding='utf-8'))
        return FittingAuditBatch(
            world_public_id=world_public_id,
            records=self._array(world_public_id, 'audit_records'),
            padding_mask=self._array(world_public_id, 'audit_padding_mask'),
            n_records=self._array(world_public_id, 'audit_n_records'),
            query_index=self._array(world_public_id, 'audit_index'),
            detector=self._array(world_public_id, 'audit_detector'),
            observed_label=self._array(world_public_id, 'audit_observed_label'),
            episode_index=self._array(world_public_id, 'audit_episode_index'),
            horizon=self._array(world_public_id, 'audit_horizon'),
            endpoint=self._array(world_public_id, 'audit_endpoint'),
            audit_id=[row['audit_id'] for row in keys],
        )

    @staticmethod
    def audit_key(world_public_id: str, episode_index: int, horizon: int,
                  endpoint: int) -> str:
        """The one supported join-key format; see SCHEMA.md section 3."""
        return f'{world_public_id}-fit{int(episode_index):04d}h{int(horizon)}e{int(endpoint)}'

    # -- helpers -----------------------------------------------------------------------
    @staticmethod
    def record_types(records: np.ndarray) -> np.ndarray:
        """-1 for padding, else RT_RESET / RT_QUERY / RT_OBSERVED."""
        onehot = records[..., SL_RECORD_TYPE]
        return np.where(onehot.any(axis=-1), onehot.argmax(axis=-1), -1)

    @staticmethod
    def properties(records: np.ndarray) -> np.ndarray:
        return records[..., SL_PROPERTIES].reshape(*records.shape[:-1], 4, 6)
