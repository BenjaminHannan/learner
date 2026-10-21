"""The only way trial-2 code talks to the Claude API. Wraps an Anthropic client with the money Guard.

Every request: bound its input, compute its worst case, HOLD that amount in the ledger (check and
reserve are one locked step), send, then charge the response's own usage and drop the hold.
A batch holds the sum of its worst cases until every result is charged.
DRAFT until code review passes; the real client path is not exercised without an API key.
"""

from __future__ import annotations

import json
import time

from money import Guard, MoneyStop, worst_case

# HTTP statuses that are rejections before any work was done: not billed. Anything else
# (5xx, 408, 409, no status such as a timeout or dropped connection) may have been billed.
NOT_BILLED = {400, 401, 402, 403, 404, 413, 422, 429}


def _dump(usage) -> dict:
    return usage if isinstance(usage, dict) else usage.model_dump()


class GuardedClient:
    def __init__(self, client, guard: Guard):
        self.client, self.guard = client, guard

    def input_upper(self, params: dict) -> int:
        blob = json.dumps({k: params.get(k) for k in ("system", "messages", "tools")}, default=str)
        return int(len(blob) / self.guard.p["worst_case"]["chars_per_token_floor"]) + 1

    @staticmethod
    def cache_ttl(params: dict) -> str | None:
        """The dearest cache TTL the request asks for, read from the request itself."""
        blob = json.dumps(params, default=str)
        if "cache_control" not in blob:
            return None
        return "1h" if '"1h"' in blob else "5m"

    @staticmethod
    def max_searches(params: dict) -> int:
        n = 0
        for t in params.get("tools") or []:
            if str(t.get("type", "")).startswith("web_search"):
                if not isinstance(t.get("max_uses"), int) or t["max_uses"] <= 0:
                    raise MoneyStop("a web_search tool must set max_uses (> 0): its cost cannot be bounded without it")
                n += t["max_uses"]
        return n

    def worst(self, params: dict) -> float:
        return worst_case(self.guard.p, params["model"], self.input_upper(params), params["max_tokens"],
                          max_searches=self.max_searches(params), cache_write=self.cache_ttl(params))

    def create(self, stage: str, tag: str, **params):
        worst = self.worst(params)
        hold = self.guard.hold(stage, worst, tag, what=tag)       # refused here = nothing sent
        try:
            resp = self.client.messages.create(**params)
        except Exception as e:
            if getattr(e, "status_code", None) in NOT_BILLED:
                self.guard.release(stage, hold, tag)
            else:
                self.guard.charge_unknown(stage, hold, params["model"], tag, repr(e)[:200])
            raise
        self.guard.charge(stage, params["model"], _dump(resp.usage), tag, hold_id=hold)
        return resp

    def batch_submit(self, stage: str, tag: str, requests: list[dict]):
        """requests: [{"custom_id": str, "params": {...}}]. Refused whole if the summed worst case does not fit."""
        hold = self.guard.hold_batch(stage, [self.worst(r["params"]) for r in requests], tag)
        try:
            batch = self.client.messages.batches.create(requests=requests)
        except Exception as e:
            if getattr(e, "status_code", None) in NOT_BILLED:
                self.guard.release(stage, hold, tag)
            else:                                                 # may have been accepted: keep the hold, as spend
                self.guard.charge_unknown(stage, hold, "-", tag, repr(e)[:200])
            raise
        return batch, hold

    def batch_collect(self, stage: str, tag: str, batch, hold: str, models: dict[str, str], poll_s: float = 30.0):
        """Wait, then charge every succeeded result at the batch rate (idempotent per custom_id).
        The hold shrinks as charges land and is dropped only after the last one."""
        while self.client.messages.batches.retrieve(batch.id).processing_status != "ended":
            time.sleep(poll_s)
        out = {}
        for r in self.client.messages.batches.results(batch.id):
            if r.result.type == "succeeded":
                self.guard.charge(stage, models[r.custom_id], _dump(r.result.message.usage), tag, batch=True,
                                  hold_id=hold, release="cost", key=f"{batch.id}/{r.custom_id}",
                                  custom_id=r.custom_id)
                out[r.custom_id] = r.result.message
        self.guard.release(stage, hold, tag)
        return out
