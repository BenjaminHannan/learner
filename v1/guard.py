"""Memory guard read from the detected card (never a constant): limit = FRACTION x the card's total memory."""
from __future__ import annotations

import torch

FRACTION = 0.9
GIB = 2 ** 30


class MemoryGuardError(RuntimeError):
    def __init__(self, message: str, peak: int, limit: int) -> None:
        super().__init__(message)
        self.peak, self.limit = peak, limit


def detect_memory_bytes(device: torch.device) -> int:
    """Total memory of the CUDA card, or of the host (MemTotal) on CPU."""
    if device.type == "cuda":
        return int(torch.cuda.get_device_properties(device).total_memory)
    with open("/proc/meminfo", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    raise RuntimeError("cannot read MemTotal from /proc/meminfo")


def limit_bytes(device: torch.device, fraction: float = FRACTION) -> int:
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    return int(detect_memory_bytes(device) * fraction)


def peak_bytes(device: torch.device) -> int:
    return int(torch.cuda.max_memory_reserved(device)) if device.type == "cuda" else 0


def check(device: torch.device, limit: int) -> int:
    peak = peak_bytes(device)
    if peak > limit:
        raise MemoryGuardError(f"peak reserved {peak / GIB:.2f} GiB exceeds the guard {limit / GIB:.2f} GiB "
                               f"(0.9 x detected card memory); stopping before the card spills or crashes", peak, limit)
    return peak
