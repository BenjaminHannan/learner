"""Fake Anthropic client for pipeline tests (no network, no key). Echoes 5 plausible cards per request."""

import json
from types import SimpleNamespace as NS


def _cards(lens: str, n: int, salt: str) -> str:
    cards = [{"core_operation": f"{lens} operation {i} {salt} variant{i*7 % 5}", "mechanism": "m", "why_novel_names": "w",
              "nearest_known": "none", "prediction": "p", "fits_interface": "yes" if i != 4 else "no"} for i in range(n)]
    return json.dumps({"cards": cards})


class FakeClient:
    def __init__(self):
        self.reqs = {}
        self.messages = NS(batches=NS(create=self._create, retrieve=lambda i: NS(processing_status="ended"),
                                      results=self._results))

    def _create(self, requests):
        self.reqs["b"] = requests
        return NS(id="batch_fake")

    def _results(self, bid):
        for r in self.reqs["b"]:
            p = r["params"]
            lens = p["messages"][0]["content"].split("LENS for this call: ")[1].split(".\n")[0]
            usage = {"input_tokens": len(json.dumps(p)) // 4, "output_tokens": 3000}
            msg = NS(usage=NS(model_dump=lambda u=usage: u), stop_reason="end_turn",
                     content=[NS(type="text", text="Here you go.\n" + _cards(lens, 5, r["custom_id"]))])
            yield NS(custom_id=r["custom_id"], result=NS(type="succeeded", message=msg))
