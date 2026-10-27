"""Deterministic evaluator controls for the 128 x 128 persistent memory.

These utilities are deliberately simple.  They do not learn routes, infer
representations, or update model parameters; they only manipulate explicit
memory state for controls and baselines described in the test contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch

from .model import MatrixMemory, unit


MEMORY_WIDTH = 128
MATRIX_BYTES = MEMORY_WIDTH * MEMORY_WIDTH * torch.tensor([], dtype=torch.float32).element_size()


def _validate_matrix(memory: torch.Tensor, name: str = "memory") -> None:
    if not isinstance(memory, torch.Tensor):
        raise TypeError(f"{name} must be a torch.Tensor")
    if memory.ndim != 3 or memory.shape[0] <= 0 or memory.shape[1:] != (MEMORY_WIDTH, MEMORY_WIDTH):
        raise ValueError(
            f"{name} must have shape [batch,{MEMORY_WIDTH},{MEMORY_WIDTH}], got {tuple(memory.shape)}"
        )
    if memory.dtype != torch.float32:
        raise ValueError(f"{name} must use torch.float32")
    if not bool(torch.isfinite(memory).all().item()):
        raise ValueError(f"{name} contains non-finite values")


def _validate_vector(
    value: torch.Tensor,
    *,
    batch: int,
    device: torch.device,
    name: str,
) -> None:
    if not isinstance(value, torch.Tensor):
        raise TypeError(f"{name} must be a torch.Tensor")
    if value.shape != (batch, MEMORY_WIDTH):
        raise ValueError(f"{name} must have shape [batch,{MEMORY_WIDTH}]")
    if value.dtype != torch.float32:
        raise ValueError(f"{name} must use torch.float32")
    if value.device != device:
        raise ValueError(f"{name} and memory must be on the same device")
    if not bool(torch.isfinite(value).all().item()):
        raise ValueError(f"{name} contains non-finite values")


def zero_memory(memory: torch.Tensor) -> torch.Tensor:
    """Return a fresh all-zero control W without changing ``memory``."""
    _validate_matrix(memory)
    return torch.zeros_like(memory)


def swap_memory(memory: torch.Tensor, donor: torch.Tensor) -> torch.Tensor:
    """Return a fresh donor W for a cross-episode swap intervention."""
    _validate_matrix(memory, "memory")
    _validate_matrix(donor, "donor")
    if donor.shape != memory.shape:
        raise ValueError("memory and donor must have the same batch shape")
    if donor.device != memory.device:
        raise ValueError("memory and donor must be on the same device")
    return donor.clone()


def snapshot_memory(memory: torch.Tensor) -> torch.Tensor:
    """Take an independent rollback snapshot without changing ``memory``."""
    _validate_matrix(memory)
    return memory.detach().clone()


def rollback_memory(snapshot: torch.Tensor) -> torch.Tensor:
    """Restore a fresh W from a previously captured full snapshot."""
    _validate_matrix(snapshot, "snapshot")
    return snapshot.clone()


class OracleMatrixMemory:
    """PC-K rig: evaluator-supplied keys/values using the production delta rule."""

    def __init__(self) -> None:
        self._memory = MatrixMemory(MEMORY_WIDTH)

    def empty(
        self,
        batch: int = 1,
        device: Optional[torch.device | str] = None,
    ) -> torch.Tensor:
        return self._memory.empty(batch=batch, device=device)

    def one_hot_keys(
        self,
        count: int,
        *,
        batch: int = 1,
        device: Optional[torch.device | str] = None,
    ) -> torch.Tensor:
        if not isinstance(count, int) or not 1 <= count <= MEMORY_WIDTH:
            raise ValueError(f"count must be in [1,{MEMORY_WIDTH}]")
        if not isinstance(batch, int) or batch <= 0:
            raise ValueError("batch must be a positive integer")
        keys = torch.eye(MEMORY_WIDTH, dtype=torch.float32, device=device)[:count]
        return keys.unsqueeze(0).expand(batch, -1, -1).clone()

    def install(
        self,
        memory: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
    ) -> torch.Tensor:
        _validate_matrix(memory)
        return self._memory.delta_write(memory, key, value)

    def install_many(
        self,
        memory: torch.Tensor,
        keys: torch.Tensor,
        values: torch.Tensor,
    ) -> torch.Tensor:
        _validate_matrix(memory)
        batch = memory.shape[0]
        if keys.ndim != 3 or keys.shape[0] != batch or keys.shape[2] != MEMORY_WIDTH:
            raise ValueError(f"keys must have shape [batch,count,{MEMORY_WIDTH}]")
        if values.shape != keys.shape:
            raise ValueError("values must have the same shape as keys")
        if not 1 <= keys.shape[1] <= MEMORY_WIDTH:
            raise ValueError(f"association count must be in [1,{MEMORY_WIDTH}]")
        if keys.dtype != torch.float32 or values.dtype != torch.float32:
            raise ValueError("keys and values must use torch.float32")
        if keys.device != memory.device or values.device != memory.device:
            raise ValueError("memory, keys, and values must be on the same device")
        if not bool(torch.isfinite(keys).all().item()) or not bool(torch.isfinite(values).all().item()):
            raise ValueError("keys and values must be finite")

        updated = memory
        for index in range(keys.shape[1]):
            updated = self._memory.delta_write(updated, keys[:, index], values[:, index])
        return updated

    def recall(self, memory: torch.Tensor, key: torch.Tensor) -> torch.Tensor:
        _validate_matrix(memory)
        return self._memory.read(memory, key)

    def recall_many(self, memory: torch.Tensor, keys: torch.Tensor) -> torch.Tensor:
        _validate_matrix(memory)
        batch = memory.shape[0]
        if keys.ndim != 3 or keys.shape[0] != batch or keys.shape[2] != MEMORY_WIDTH:
            raise ValueError(f"keys must have shape [batch,count,{MEMORY_WIDTH}]")
        if keys.dtype != torch.float32 or keys.device != memory.device:
            raise ValueError("keys must be float32 on the memory device")
        if not bool(torch.isfinite(keys).all().item()):
            raise ValueError("keys must be finite")
        return torch.stack(
            [self._memory.read(memory, keys[:, index]) for index in range(keys.shape[1])],
            dim=1,
        )


@dataclass(frozen=True)
class SlotMemoryByteAccounting:
    slots: int
    payload_bytes: int
    slot_metadata_bytes: int
    header_bytes: int
    metadata_bytes: int
    total_bytes: int
    target_bytes: int
    exact_match: bool


@dataclass(frozen=True)
class SlotMemoryState:
    keys: torch.Tensor
    values: torch.Tensor
    metadata: torch.Tensor


class ByteMatchedSlotMemory:
    """Explicit softmax key/value store with deterministic overwrite policy.

    The serialized state uses 63 slots.  Each slot carries two 128-d float32
    vectors (1,024 payload bytes) plus 16 metadata bytes.  A 16-byte header
    makes the per-batch-item raw tensor storage exactly 65,536 bytes.

    Metadata layout is intentionally visible:
      header[0:8]   next write timestamp (little-endian int64)
      header[8:16]  format version (little-endian int64)
      slot[0]       occupied byte
      slot[1:8]     reserved/padding
      slot[8:16]    last-written timestamp (little-endian int64)
    """

    SLOTS = 63
    FLOAT_BYTES = 4
    PAYLOAD_BYTES_PER_SLOT = MEMORY_WIDTH * 2 * FLOAT_BYTES
    METADATA_BYTES_PER_SLOT = 16
    HEADER_BYTES = 16
    METADATA_BYTES = SLOTS * METADATA_BYTES_PER_SLOT + HEADER_BYTES
    PAYLOAD_BYTES = SLOTS * PAYLOAD_BYTES_PER_SLOT
    TOTAL_BYTES = PAYLOAD_BYTES + METADATA_BYTES
    FORMAT_VERSION = 1

    def __init__(
        self,
        *,
        overwrite_similarity_threshold: float = 0.95,
        read_temperature: float = 1.0,
    ) -> None:
        if not -1.0 <= overwrite_similarity_threshold <= 1.0:
            raise ValueError("overwrite_similarity_threshold must be in [-1,1]")
        if not read_temperature > 0.0:
            raise ValueError("read_temperature must be positive")
        self.overwrite_similarity_threshold = float(overwrite_similarity_threshold)
        self.read_temperature = float(read_temperature)

    @property
    def byte_accounting(self) -> SlotMemoryByteAccounting:
        return SlotMemoryByteAccounting(
            slots=self.SLOTS,
            payload_bytes=self.PAYLOAD_BYTES,
            slot_metadata_bytes=self.SLOTS * self.METADATA_BYTES_PER_SLOT,
            header_bytes=self.HEADER_BYTES,
            metadata_bytes=self.METADATA_BYTES,
            total_bytes=self.TOTAL_BYTES,
            target_bytes=MATRIX_BYTES,
            exact_match=self.TOTAL_BYTES == MATRIX_BYTES,
        )

    @staticmethod
    def _int64_to_le_bytes(values: torch.Tensor) -> torch.Tensor:
        shifts = torch.arange(8, dtype=torch.int64, device=values.device) * 8
        return ((values.to(torch.int64).unsqueeze(-1) >> shifts) & 0xFF).to(torch.uint8)

    @staticmethod
    def _le_bytes_to_int64(values: torch.Tensor) -> torch.Tensor:
        shifts = torch.arange(8, dtype=torch.int64, device=values.device) * 8
        return (values.to(torch.int64) << shifts).sum(dim=-1)

    def empty(
        self,
        batch: int = 1,
        device: Optional[torch.device | str] = None,
    ) -> SlotMemoryState:
        if not isinstance(batch, int) or batch <= 0:
            raise ValueError("batch must be a positive integer")
        keys = torch.zeros(batch, self.SLOTS, MEMORY_WIDTH, dtype=torch.float32, device=device)
        values = torch.zeros_like(keys)
        metadata = torch.zeros(batch, self.METADATA_BYTES, dtype=torch.uint8, device=device)
        header_indices = torch.arange(8, device=keys.device).unsqueeze(0).expand(batch, -1)
        next_write = torch.ones(batch, dtype=torch.int64, device=keys.device)
        version = torch.full((batch,), self.FORMAT_VERSION, dtype=torch.int64, device=keys.device)
        metadata = metadata.scatter(1, header_indices, self._int64_to_le_bytes(next_write))
        metadata = metadata.scatter(1, header_indices + 8, self._int64_to_le_bytes(version))
        return SlotMemoryState(keys=keys, values=values, metadata=metadata)

    def _validate_state(self, state: SlotMemoryState) -> None:
        if not isinstance(state, SlotMemoryState):
            raise TypeError("state must be a SlotMemoryState")
        if state.keys.ndim != 3 or state.keys.shape[0] <= 0 or state.keys.shape[1:] != (
            self.SLOTS,
            MEMORY_WIDTH,
        ):
            raise ValueError(f"slot keys must have shape [batch,{self.SLOTS},{MEMORY_WIDTH}]")
        if state.values.shape != state.keys.shape:
            raise ValueError("slot values must have the same shape as keys")
        if state.keys.dtype != torch.float32 or state.values.dtype != torch.float32:
            raise ValueError("slot keys and values must use torch.float32")
        if state.values.device != state.keys.device:
            raise ValueError("slot keys and values must be on the same device")
        if state.metadata.shape != (state.keys.shape[0], self.METADATA_BYTES):
            raise ValueError(f"metadata must have shape [batch,{self.METADATA_BYTES}]")
        if state.metadata.dtype != torch.uint8 or state.metadata.device != state.keys.device:
            raise ValueError("metadata must be uint8 on the same device as slot payloads")
        if not bool(torch.isfinite(state.keys).all().item()) or not bool(
            torch.isfinite(state.values).all().item()
        ):
            raise ValueError("slot payload contains non-finite values")
        version = self._le_bytes_to_int64(state.metadata[:, 8:16])
        if not bool(version.eq(self.FORMAT_VERSION).all().item()):
            raise ValueError("slot metadata format version is invalid")

    def tensor_bytes(self, state: SlotMemoryState) -> int:
        """Return raw tensor payload+packed-metadata bytes for the full batch."""
        self._validate_state(state)
        tensors = (state.keys, state.values, state.metadata)
        return sum(tensor.numel() * tensor.element_size() for tensor in tensors)

    def occupied_mask(self, state: SlotMemoryState) -> torch.Tensor:
        self._validate_state(state)
        blocks = state.metadata[:, self.HEADER_BYTES :].reshape(
            state.keys.shape[0], self.SLOTS, self.METADATA_BYTES_PER_SLOT
        )
        return blocks[:, :, 0].ne(0)

    def last_written(self, state: SlotMemoryState) -> torch.Tensor:
        self._validate_state(state)
        blocks = state.metadata[:, self.HEADER_BYTES :].reshape(
            state.keys.shape[0], self.SLOTS, self.METADATA_BYTES_PER_SLOT
        )
        return self._le_bytes_to_int64(blocks[:, :, 8:16])

    def _next_write(self, state: SlotMemoryState) -> torch.Tensor:
        return self._le_bytes_to_int64(state.metadata[:, :8])

    def read_weights(self, state: SlotMemoryState, query: torch.Tensor) -> torch.Tensor:
        self._validate_state(state)
        batch = state.keys.shape[0]
        _validate_vector(query, batch=batch, device=state.keys.device, name="query")
        q = unit(query).float()
        occupied = self.occupied_mask(state)
        scores = torch.bmm(state.keys, q.unsqueeze(-1)).squeeze(-1)
        scores = scores / self.read_temperature
        scores = scores.masked_fill(~occupied, torch.finfo(scores.dtype).min)
        weights = torch.softmax(scores, dim=-1)
        return torch.where(occupied.any(dim=-1, keepdim=True), weights, torch.zeros_like(weights))

    def read(self, state: SlotMemoryState, query: torch.Tensor) -> torch.Tensor:
        weights = self.read_weights(state, query)
        result = torch.bmm(weights.unsqueeze(1), state.values).squeeze(1)
        if not bool(torch.isfinite(result).all().item()):
            raise ValueError("slot-memory read produced non-finite values")
        return result

    def write(
        self,
        state: SlotMemoryState,
        key: torch.Tensor,
        value: torch.Tensor,
    ) -> SlotMemoryState:
        self._validate_state(state)
        batch = state.keys.shape[0]
        _validate_vector(key, batch=batch, device=state.keys.device, name="key")
        _validate_vector(value, batch=batch, device=state.keys.device, name="value")
        k = unit(key).float()
        occupied = self.occupied_mask(state)

        similarities = torch.bmm(state.keys, k.unsqueeze(-1)).squeeze(-1)
        masked = similarities.masked_fill(~occupied, torch.finfo(similarities.dtype).min)
        nearest_score, nearest_slot = masked.max(dim=-1)
        replace_nearest = occupied.any(dim=-1) & nearest_score.ge(self.overwrite_similarity_threshold)

        free = ~occupied
        has_free = free.any(dim=-1)
        first_free = free.to(torch.int64).argmax(dim=-1)
        timestamps = self.last_written(state)
        sentinel = torch.iinfo(torch.int64).max
        oldest_slot = torch.where(occupied, timestamps, torch.full_like(timestamps, sentinel)).argmin(dim=-1)
        target = torch.where(replace_nearest, nearest_slot, torch.where(has_free, first_free, oldest_slot))

        payload_index = target[:, None, None].expand(-1, 1, MEMORY_WIDTH)
        keys = state.keys.scatter(1, payload_index, k.unsqueeze(1))
        values = state.values.scatter(1, payload_index, value.unsqueeze(1))

        rows = torch.arange(batch, device=state.keys.device)
        occupied_index = self.HEADER_BYTES + target * self.METADATA_BYTES_PER_SLOT
        metadata = state.metadata.scatter(
            1,
            occupied_index.unsqueeze(1),
            torch.ones(batch, 1, dtype=torch.uint8, device=state.keys.device),
        )
        timestamp = self._next_write(state)
        timestamp_indices = occupied_index.unsqueeze(1) + 8 + torch.arange(
            8, device=state.keys.device
        ).unsqueeze(0)
        metadata = metadata.scatter(1, timestamp_indices, self._int64_to_le_bytes(timestamp))
        next_timestamp_indices = torch.arange(8, device=state.keys.device).unsqueeze(0).expand(batch, -1)
        metadata = metadata.scatter(
            1,
            next_timestamp_indices,
            self._int64_to_le_bytes(timestamp + 1),
        )
        del rows
        return SlotMemoryState(keys=keys, values=values, metadata=metadata)


@dataclass(frozen=True)
class InterventionResult:
    own_tokens: torch.Tensor
    zero_tokens: torch.Tensor
    swapped_tokens: torch.Tensor
    rollback_tokens: torch.Tensor

    def equality_to_own(self) -> dict[str, bool]:
        """Report token equality only; this does not assign representation semantics."""
        return {
            "zero": torch.equal(self.own_tokens, self.zero_tokens),
            "swapped": torch.equal(self.own_tokens, self.swapped_tokens),
            "rollback": torch.equal(self.own_tokens, self.rollback_tokens),
        }


def compare_interventions(
    model,
    query_tokens: torch.Tensor,
    own_memory: torch.Tensor,
    swapped_memory: torch.Tensor,
    rollback_snapshot: torch.Tensor,
    *,
    lengths: Optional[torch.Tensor] = None,
    max_new_tokens: Optional[int] = None,
    steps: Optional[int] = None,
) -> InterventionResult:
    """Generate under four explicit W conditions and return their token outputs."""
    _validate_matrix(own_memory, "own_memory")
    _validate_matrix(swapped_memory, "swapped_memory")
    _validate_matrix(rollback_snapshot, "rollback_snapshot")
    if swapped_memory.shape != own_memory.shape or rollback_snapshot.shape != own_memory.shape:
        raise ValueError("all intervention memories must have the same batch shape")
    if swapped_memory.device != own_memory.device or rollback_snapshot.device != own_memory.device:
        raise ValueError("all intervention memories must be on the same device")

    conditions = (
        own_memory.clone(),
        zero_memory(own_memory),
        swap_memory(own_memory, swapped_memory),
        rollback_memory(rollback_snapshot),
    )

    def generate_tokens(memory: torch.Tensor) -> torch.Tensor:
        output = model.generate(
            query_tokens,
            memory,
            lengths=lengths,
            max_new_tokens=max_new_tokens,
            steps=steps,
        )
        return output.decoding.tokens.detach().clone()

    with torch.no_grad():
        own_tokens, zero_tokens, swapped_tokens, rollback_tokens = (
            generate_tokens(memory) for memory in conditions
        )
    return InterventionResult(
        own_tokens=own_tokens,
        zero_tokens=zero_tokens,
        swapped_tokens=swapped_tokens,
        rollback_tokens=rollback_tokens,
    )
