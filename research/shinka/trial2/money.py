"""Money stop for trial 2, enforced in code (research/shinka/TRIAL2-PLAN-OPUS.md section 4).

- Every cost is computed from the response's own usage figures (input, output, cache write,
  cache read, web-search request count) at the rates in pricing.json.
- A call or batch is authorised BEFORE it is sent: its worst case must fit in what is left of its
  own stage (no borrowing between stages) and, separately, under the whole-trial hard stop.
- The ledger (results/TRIAL2_LEDGER.jsonl) is re-read on every check, under a file lock, so
  separate processes see each other's spend.
Nothing here talks to the network.
"""

from __future__ import annotations

import fcntl
import json
import math
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRICING = HERE / "pricing.json"
LEDGER = HERE.parent / "results" / "TRIAL2_LEDGER.jsonl"


class MoneyStop(RuntimeError):
    """Raised before a call is sent (or after a charge that crossed a stop). Never caught by the pipeline."""


def load_pricing(path: Path = PRICING) -> dict:
    return json.loads(Path(path).read_text())


def _rates(p: dict, model: str, input_tokens: int) -> tuple[float, float, float]:
    m = p["models"].get(model)
    if m is None:
        raise MoneyStop(f"no rates for model {model!r} in pricing.json")
    if m.get("long_prompt_tokens") and input_tokens > m["long_prompt_tokens"]:
        return m["long_input"], m["long_output"], m["cache_read"]
    return m["input"], m["output"], m["cache_read"]


def usage_cost(p: dict, model: str, usage: dict, batch: bool = False) -> float:
    """Dollars for one response, from its own usage block (a dict, e.g. response.usage.model_dump())."""
    inp = int(usage.get("input_tokens") or 0)
    out = int(usage.get("output_tokens") or 0)
    read = int(usage.get("cache_read_input_tokens") or 0)
    write = int(usage.get("cache_creation_input_tokens") or 0)
    detail = usage.get("cache_creation") or {}
    w5, w1 = int(detail.get("ephemeral_5m_input_tokens") or 0), int(detail.get("ephemeral_1h_input_tokens") or 0)
    if w5 + w1 != write:                     # no or inconsistent breakdown: price all of it at the dearer 1-hour rate
        w5, w1 = 0, write
    searches = int(((usage.get("server_tool_use") or {}).get("web_search_requests")) or 0)
    r_in, r_out, r_read = _rates(p, model, inp + read + write)
    mult = p["cache_write_multiplier"]
    usd = (inp * r_in + out * r_out + read * r_read + w5 * r_in * mult["5m"] + w1 * r_in * mult["1h"]) / 1e6
    usd *= p["batch_discount"] if batch else 1.0
    return usd + searches * p["web_search_usd_per_search"]


def worst_case(p: dict, model: str, input_tokens_upper: int, max_tokens: int,
               max_searches: int = 0, cache_write: str | None = None) -> float:
    """Upper bound for one request: all input at the uncached price (x write multiplier if the
    request asks for caching), all of max_tokens as output, every allowed search used and each
    search adding its result tokens as input. No batch discount (deliberately generous)."""
    inp = input_tokens_upper + max_searches * p["worst_case"]["search_result_tokens_per_search"]
    r_in, r_out, _ = _rates(p, model, inp)
    mult = p["cache_write_multiplier"][cache_write] if cache_write else 1.0
    return (inp * r_in * mult + max_tokens * r_out) / 1e6 + max_searches * p["web_search_usd_per_search"]


class Guard:
    def __init__(self, ledger: Path = LEDGER, pricing: dict | None = None):
        self.ledger = Path(ledger)
        self.p = pricing or load_pricing()

    # --- ledger -----------------------------------------------------------------------------
    def _rows(self) -> list[dict]:
        if not self.ledger.exists():
            return []
        return [json.loads(x) for x in self.ledger.read_text().splitlines() if x.strip()]

    def spent(self, stage: str | None = None) -> float:
        """Dollars already charged, PLUS dollars held for batches submitted but not yet collected."""
        return sum(r["usd"] + r.get("reserved", 0.0) for r in self._rows() if stage is None or r["stage"] == stage)

    def _append(self, row: dict) -> None:
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger.open("a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(row) + "\n")
            f.flush()
            fcntl.flock(f, fcntl.LOCK_UN)

    # --- limits -----------------------------------------------------------------------------
    def stage_cap(self, stage: str) -> float:
        s = self.p["stages"].get(str(stage))
        if s is None:
            raise MoneyStop(f"unknown stage {stage!r}")
        return s["cap_usd"]

    def stage_left(self, stage: str) -> float:
        return self.stage_cap(stage) - self.spent(str(stage))

    def trial_left(self) -> float:
        return self.p["whole_trial"]["hard_stop_usd"] - self.spent()

    def authorize(self, stage: str, worst_usd: float, what: str = "call") -> None:
        """Refuse (raise MoneyStop) unless the worst case fits in the stage AND under the hard stop."""
        stage = str(stage)
        cap, hard = self.stage_cap(stage), self.p["whole_trial"]["hard_stop_usd"]
        in_stage, in_trial = self.spent(stage), self.spent()
        if in_stage + worst_usd > cap:  # GUARD-stage
            raise MoneyStop(f"refused {what}: worst case ${worst_usd:.4f} + stage {stage} spent "
                            f"${in_stage:.4f} exceeds the stage cap ${cap:.2f}")
        if in_trial + worst_usd > hard:  # GUARD-trial
            raise MoneyStop(f"refused {what}: worst case ${worst_usd:.4f} + trial spent "
                            f"${in_trial:.4f} exceeds the whole-trial hard stop ${hard:.2f}")

    def authorize_batch(self, stage: str, worst_each: list[float]) -> float:
        total = math.fsum(worst_each)
        self.authorize(stage, total, what=f"batch of {len(worst_each)}")  # GUARD-batch (the batch's summed worst case)
        return total

    def reserve(self, stage: str, tag: str, usd: float, batch_id: str) -> None:
        self._append({"t": time.time(), "stage": str(stage), "model": "-", "tag": tag, "usd": 0.0,
                      "reserved": usd, "batch_id": batch_id})

    def release(self, stage: str, tag: str, batch_id: str) -> None:
        held = sum(r.get("reserved", 0.0) for r in self._rows() if r.get("batch_id") == batch_id)
        self._append({"t": time.time(), "stage": str(stage), "model": "-", "tag": tag, "usd": 0.0,
                      "reserved": -held, "batch_id": batch_id})

    # --- charging ---------------------------------------------------------------------------
    def charge(self, stage: str, model: str, usage: dict, tag: str, batch: bool = False, **extra) -> float:
        usd = usage_cost(self.p, model, usage, batch=batch)
        self._append({"t": time.time(), "stage": str(stage), "model": model, "tag": tag,
                      "usd": usd, "batch": batch, "usage": usage, **extra})
        self._after_charge(str(stage))
        return usd

    def charge_unknown(self, stage: str, model: str, worst_usd: float, tag: str, why: str) -> float:
        """A request that may have been billed but gave no usage: record its worst case."""
        self._append({"t": time.time(), "stage": str(stage), "model": model, "tag": tag,
                      "usd": worst_usd, "unknown_outcome": why})
        self._after_charge(str(stage))
        return worst_usd

    def _after_charge(self, stage: str) -> None:
        if self.spent(stage) > self.stage_cap(stage):  # GUARD-overshoot-stage
            raise MoneyStop(f"stage {stage} is over its cap after this charge (${self.spent(stage):.4f})")
        if self.spent() > self.p["whole_trial"]["hard_stop_usd"]:  # GUARD-overshoot-trial
            raise MoneyStop(f"whole trial is over the hard stop after this charge (${self.spent():.4f})")

    def warn(self) -> bool:
        return self.spent() >= self.p["whole_trial"]["warn_usd"]
