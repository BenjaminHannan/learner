"""Fake client for screen.py tests: clusters cards in pairs; every 3rd family fails the screen."""
import json
import re
from types import SimpleNamespace as NS


class FakeClient:
    def __init__(self):
        self.calls = 0
        self.messages = NS(create=self._create)

    def _create(self, **kw):
        self.calls += 1
        user = kw["messages"][0]["content"]
        if "families" in kw["system"]:
            ids = re.findall(r"^(c\d{3}):", user, flags=re.M)
            fams = [{"name": f"f{i}", "members": ids[i:i + 2]} for i in range(0, len(ids), 2)]
            text = "ok " + json.dumps({"families": fams})
        else:
            n = self.calls % 3
            text = json.dumps({"implementable": n != 0, "known_item": "none" if n != 1 else "multi-head pooling",
                               "combination": False, "reason": "r"})
        usage = {"input_tokens": len(json.dumps(kw)) // 4, "output_tokens": 400}
        return NS(usage=NS(model_dump=lambda: usage), stop_reason="end_turn", content=[NS(type="text", text=text)])
