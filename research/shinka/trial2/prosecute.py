#!/usr/bin/env python3
"""Stage 3a prosecutor: Sonnet 5.5 + web search tries to prove an idea card already exists.

DRAFT. The real-client path has not run (no API key in the build session). All calls go through
GuardedClient, so the stage cap and the $45 hard stop apply.

Usage (plumbing test, Stage 0, one call): python plumbing_test.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from guarded import GuardedClient  # noqa: E402
from money import Guard  # noqa: E402

MODEL = "claude-sonnet-5-5"
MAX_SEARCHES = 6
MAX_TOKENS = 3000
MAX_CONTINUES = 2          # pause_turn continuations; each one is guarded and charged separately
TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": MAX_SEARCHES}

SYSTEM = (
    "You are a prior-art prosecutor. Your job is to PROVE the idea card below already exists, in the "
    "literature or in the project's known list. Search the web for the closest published or "
    "open-source method. Be adversarial: a direct combination of two known items counts as known. "
    "Do not defend the card. Finish with ONE JSON object and nothing after it: "
    '{"closest": "<method/paper>", "citations": ["<url>", ...], "case": "<one paragraph>", '
    '"same_core_operation": true|false, "confidence": 1-5}.'
)


def parse_case(text: str) -> dict | None:
    """The last top-level JSON object in the text, or None (a non-parse counts as KNOWN downstream)."""
    end = text.rfind("}")
    while end != -1:
        depth = 0
        for i in range(end, -1, -1):
            depth += (text[i] == "}") - (text[i] == "{")
            if depth == 0:
                try:
                    return json.loads(text[i:end + 1])
                except json.JSONDecodeError:
                    break
        end = text.rfind("}", 0, end)
    return None


def prosecute(gc: GuardedClient, stage: str, card: dict, known_short: str, tag: str) -> dict:
    messages = [{"role": "user", "content":
                 f"KNOWN list (project):\n{known_short}\n\nIDEA CARD:\n{json.dumps(card, indent=2)}"}]
    text, n_search = "", 0
    for k in range(MAX_CONTINUES + 1):
        resp = gc.create(stage, f"{tag}#{k}", model=MODEL, max_tokens=MAX_TOKENS, system=SYSTEM,
                         messages=messages, tools=[TOOL], output_config={"effort": "medium"})
        n_search += sum(1 for b in resp.content if getattr(b, "type", "") == "server_tool_use")
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        if resp.stop_reason != "pause_turn":
            break
        messages = messages + [{"role": "assistant", "content": resp.content}]
    return {"case": parse_case(text), "raw_tail": text[-400:], "searches": n_search,
            "stop_reason": resp.stop_reason}


def make_client(guard: Guard) -> GuardedClient:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set; refusing to build a client")
    import anthropic
    return GuardedClient(anthropic.Anthropic(), guard)
