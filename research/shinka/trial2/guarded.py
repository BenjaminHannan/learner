"""The only way trial-2 code talks to the Claude API. Wraps an Anthropic client with the money Guard.

Every request: estimate a safe upper bound on input, compute its worst case, authorise it, send it,
charge the response's own usage. A batch is authorised on the sum of its worst cases before submit.
DRAFT until code review passes; the real client path is not exercised without an API key.
"""

from __future__ import annotations

import json
import time

from money import Guard, MoneyStop, worst_case


def _dump(usage) -> dict:
    return usage if isinstance(usage, dict) else usage.model_dump()


class GuardedClient:
    def __init__(self, client, guard: Guard):
        self.client, self.guard = client, guard

    def input_upper(self, params: dict) -> int:
        blob = json.dumps({k: params.get(k) for k in ("system", "messages", "tools")}, default=str)
        return int(len(blob) / self.guard.p["worst_case"]["chars_per_token_floor"]) + 1

    def worst(self, params: dict, cache_write: str | None = None) -> float:
        searches = sum(t.get("max_uses", 0) for t in params.get("tools") or []
                       if str(t.get("type", "")).startswith("web_search"))
        return worst_case(self.guard.p, params["model"], self.input_upper(params), params["max_tokens"],
                          max_searches=searches, cache_write=cache_write)

    def create(self, stage: str, tag: str, cache_write: str | None = None, **params):
        worst = self.worst(params, cache_write)
        self.guard.authorize(stage, worst, what=tag)
        try:
            resp = self.client.messages.create(**params)
        except Exception as e:
            status = getattr(e, "status_code", None)
            if status is not None and 400 <= status < 500 and status != 429:
                raise                                   # rejected before any work: not billed
            self.guard.charge_unknown(stage, params["model"], worst, tag, repr(e)[:200])
            raise
        self.guard.charge(stage, params["model"], _dump(resp.usage), tag)
        return resp

    def batch_submit(self, stage: str, tag: str, requests: list[dict], cache_write: str | None = None):
        """requests: [{"custom_id": str, "params": {...}}]. Refused whole if the summed worst case does not fit."""
        total = self.guard.authorize_batch(stage, [self.worst(r["params"], cache_write) for r in requests])
        batch = self.client.messages.batches.create(requests=requests)
        self.guard.reserve(stage, tag, total, batch.id)     # held until collected, so nothing else can spend it
        return batch

    def batch_collect(self, stage: str, tag: str, batch_id: str, models: dict[str, str], poll_s: float = 30.0):
        """Wait for the batch, charge each succeeded result at the batch rate. models: custom_id -> model."""
        while self.client.messages.batches.retrieve(batch_id).processing_status != "ended":
            time.sleep(poll_s)
        out = {}
        self.guard.release(stage, tag, batch_id)           # actual charges replace the hold (still bounded by it)
        for r in self.client.messages.batches.results(batch_id):
            if r.result.type == "succeeded":
                self.guard.charge(stage, models[r.custom_id], _dump(r.result.message.usage), tag, batch=True,
                                  custom_id=r.custom_id)
                out[r.custom_id] = r.result.message
        return out
