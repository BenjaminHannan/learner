#!/usr/bin/env python3
"""Novelty judge for trial finalists (research/shinka/CARD.md, "Novelty check").

A separate LLM call (Opus 5.5), run once per finalist, that sees nothing about scores. It gets:
  - the finalist's CardWriter code;
  - KNOWN.md (the project's own ideas plus standard methods);
  - a web search tool, so it can look up the literature.
It must describe the mechanism in one paragraph, then answer "KNOWN: <method>"
or "NOT FOUND: closest is <method>".

Usage:
  ANTHROPIC_API_KEY=... python novelty_judge.py --out results/evo1/judge.jsonl prog1.py prog2.py ...
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import sys

import anthropic
from shinka.llm.providers.pricing import calculate_cost

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ledger  # noqa: E402

MODEL = "claude-opus-5-5"      # Ben's instruction, 2026-10-20: use Opus 5.5
PRICE_SEARCH = 10.0 / 1e3      # web search: $10 per 1,000 searches (not in Shinka's catalog)
MAX_TOKENS = 12000             # Opus 5.5 thinks across the search loop, then writes 6 fields
MAX_SEARCHES = 2               # per request
MAX_REQUESTS = 2               # one resume after pause_turn at most, to bound unestimated passes
SEARCH_CONTEXT = 20_000        # input tokens that one search's results may add


def turn_worst_usd(context_tokens: int) -> float:
    """Worst case for the next turn, assuming the input is billed again at every search
    step: (searches + 1) passes over the context, which grows by one search's results
    each step, plus a full-length output and the searches themselves."""
    # two billed passes per search (the search plus its result-filtering step), plus the answer
    billed_in = sum(context_tokens + (i // 2) * SEARCH_CONTEXT for i in range(2 * MAX_SEARCHES + 1))
    return sum(calculate_cost(MODEL, billed_in, MAX_TOKENS)) + MAX_SEARCHES * PRICE_SEARCH


def prompt_tokens(known: str, code: str) -> int:
    return len(PROMPT.format(known=known, code=code)) // 3  # generous chars-to-tokens bound

PROMPT = """You are a strict novelty judge for machine-learning mechanisms.

Below is a PyTorch module that turns the token states of one line of text into
one memory card (a retrieval key and a value). The aim was a NEW way of making
the card keep WHO a fact is about, not only the fact's value.

Your job is to decide whether its CORE mechanism is already known. Be strict: a
renamed or lightly recombined known method counts as KNOWN. Use web search to
check the literature (search for the core operation, not for the variable
names). Also check the project's own list of known ideas below.

Answer in exactly this format:
DESCRIPTION: <one plain paragraph: what the module computes, step by step>
CORE: <the one operation that is supposed to be new, in one sentence>
SEARCHES: <what you searched for and what you found, briefly>
VERDICT: KNOWN: <name of the method, with a citation or a KNOWN.md item number>
   or
VERDICT: NOT FOUND: closest is <method>, which differs because <reason>
CONFIDENCE: <low | medium | high>

=== KNOWN.md ===
{known}

=== CANDIDATE CODE ===
```python
{code}
```
"""


def evolve_block(src: str) -> str:
    m = re.search(r"# EVOLVE-BLOCK-START(.*?)# EVOLVE-BLOCK-END", src, re.S)
    return m.group(1).strip() if m else src


def judge(client: anthropic.Anthropic, code: str, known: str, budget_left: float) -> tuple[str, dict]:
    """budget_left: dollars this finalist may still spend (judge cap and trial cap, whichever is lower)."""
    messages = [{"role": "user", "content": PROMPT.format(known=known, code=code)}]
    text_parts, usage = [], {"input_tokens": 0, "output_tokens": 0, "searches": 0, "usd": 0.0}
    context = prompt_tokens(known, code)
    for turn in range(MAX_REQUESTS):  # resume server-tool turns that pause
        if budget_left - usage["usd"] < turn_worst_usd(context):
            if turn == 0:  # main() treats this as the trial-wide budget being used up
                text_parts.append("VERDICT: NOT JUDGED (budget stop before the judge finished); counts as KNOWN")
            else:  # only this finalist's resume does not fit; later finalists may still be judged
                text_parts.append("VERDICT: NOT JUDGED (still searching; resume did not fit the budget); counts as KNOWN")
            break
        # The tool definition stays identical across resumed turns (the API expects it);
        # max_uses applies per request, so a finalist gets at most MAX_SEARCHES x MAX_REQUESTS searches.
        r = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS, messages=messages,
            output_config={"effort": "medium"},
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": MAX_SEARCHES}],
        )
        stu = getattr(r.usage, "server_tool_use", None)
        searches = getattr(stu, "web_search_requests", 0) or 0
        turn_usd = sum(calculate_cost(MODEL, r.usage.input_tokens, r.usage.output_tokens)) + searches * PRICE_SEARCH
        ledger.record(MODEL, "novelty-judge", r.usage.input_tokens, r.usage.output_tokens, turn_usd,
                      searches=searches)
        # conversation size for the next turn's estimate: what was sent, plus this turn's
        # output and search results (billed input already counts repeated passes)
        context += r.usage.output_tokens + searches * SEARCH_CONTEXT
        usage["input_tokens"] += r.usage.input_tokens
        usage["output_tokens"] += r.usage.output_tokens
        usage["searches"] += searches
        usage["usd"] += turn_usd
        # citations split one answer into many text blocks; join them without separators
        text_parts.append("".join(b.text for b in r.content if b.type == "text"))
        if r.stop_reason == "refusal":
            text_parts.append("VERDICT: NOT JUDGED (judge refused); counts as KNOWN")
            break
        if r.stop_reason == "max_tokens":
            text_parts.append("VERDICT: NOT JUDGED (reply truncated at max_tokens); counts as KNOWN")
            break
        if r.stop_reason != "pause_turn":
            break
        # resume the paused server-tool turn: send its content back unchanged
        messages = messages + [{"role": "assistant", "content": r.content}]
    else:
        text_parts.append(f"VERDICT: NOT JUDGED (still searching after {MAX_REQUESTS} requests); counts as KNOWN")
    return "\n".join(text_parts), usage


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("programs", nargs="+",
                    help="finalists in CARD.md section 8 order: 6(b)-1, 6(a)-1, 6(b)-2, 6(a)-2, 6(a)-3, 6(a)-4")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-usd", type=float, default=1.60)
    a = ap.parse_args()
    known = (HERE / "KNOWN.md").read_text()
    client = anthropic.Anthropic()
    out = Path(a.out)
    if out.exists():
        raise SystemExit(f"{out} exists: the judge runs once per trial (one verdict per finalist)")
    spent = ledger.spent_with_tag("novelty-judge")  # judge spend so far counts against its cap
    print(f"trial spend before judging: ${ledger.total():.4f}", flush=True)
    out_of_budget = False
    for prog in a.programs:
        code = evolve_block(Path(prog).read_text())
        left = min(a.max_usd - spent, ledger.remaining())
        # once one finalist is skipped for budget, all later ones are too (CARD.md section 8:
        # the finalists last in the fixed order are the ones left NOT JUDGED)
        out_of_budget = out_of_budget or left < turn_worst_usd(prompt_tokens(known, code))
        if out_of_budget:
            msg = f"NOT JUDGED (budget: judge ${spent:.4f}, trial ${ledger.total():.4f}); counts as KNOWN"
            print(f"{prog}: {msg}")
            with out.open("a") as f:
                f.write(json.dumps({"t": time.time(), "program": prog, "verdict": msg,
                                    "usage": {"usd": 0.0}, "response": ""}) + "\n")
            continue
        before = ledger.total()
        try:
            text, usage = judge(client, code, known, left)
            if "budget stop before the judge finished" in text:
                out_of_budget = True  # keep the fixed order: no later finalist is judged
        except anthropic.APIError as exc:  # record and go on to the next finalist
            # turns paid before the error are already in the ledger; count them here too
            text = f"VERDICT: NOT JUDGED (judge error {type(exc).__name__}: {exc}); counts as KNOWN"
            usage = {"usd": ledger.total() - before}
            print(f"{prog}: judge error {exc} (its paid turns are in TRIAL_LEDGER.jsonl)", flush=True)
        spent += usage["usd"]
        verdicts = re.findall(r"VERDICT:\s*(.*)", text)  # the last one is the final answer
        final = verdicts[-1].strip() if verdicts else "NOT JUDGED (no verdict parsed); counts as KNOWN"
        rec = {"t": time.time(), "program": prog, "verdict": final,
               "usage": usage, "response": text}
        with out.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"{prog}: {rec['verdict']}  (${usage['usd']:.4f}, total ${spent:.4f})", flush=True)


if __name__ == "__main__":
    main()
