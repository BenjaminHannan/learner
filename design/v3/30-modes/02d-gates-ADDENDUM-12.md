# 0.2d gates, ADDENDUM-12: re-plan under Redirect (Ben 16:04 UTC). Written 2026-09-26 16:08 UTC

Ben 16:04: "why fail something or even test it at all if it's worse than our design" (card: Redirect).
Ben 16:05: every fallback starts with "how does the brain do this?". Goals page (ben-goals-2026-09-26.md) wins.
This file replaces the supporting-gate list of the base file and ADDENDUM-1..11. The headline gates stay.

## What 0.2d is now
Ben's design only: reader -> notebook -> learned reasoner -> talker, plus sleep while dormant.
- Reader: lis-319f (verified PASS 2759100be). Notes: rd-378L when it passes. Notebook provenance check kept.
- Reasoner: the rsn-358b3 loop net (H-A). Its hand-written grid parser is disclosed test scaffolding, not part of
  the build; it is replaced when a learned chat-puzzle reader passes (owed by Sleep research).
- Talker: plain MiniCPM5-1B, fed the notebook through y1f's W input (whole chat when it fits), k1a for creative,
  "I don't know" when the notebook has nothing. No hand-written question rules, templates or answer "reasoner".
- Sleep (H-B): Fix sleep's first verified retention PASS under dl-3's marks (dl-6 live) + ip-1b interruptible row.

## What stops (tests already running finish; their verdicts stand; none joins 0.2d)
- 383 route (registered PASS 057664ed3): not joined, it is a rule route.
- q-404 ("you" gate on think299): rent-q404 launched ~16:06 UTC before Redirect; it finishes and is verified,
  not joined. No q-405.
- sel-02d router code: not written. Its sealed panel (2159153d4, TEST-ONLY) is kept as a memory/self row for the
  learned build.
- Rule puzzle routes (rt-02d, rt-02e, door-1) and the think299 gates: not joined.
- 0.2d-r (already ran): scored when the republish lands; report of 0.2c's rule build, not a 0.2d input.

## How 0.2d is judged (against plain same-size models, not the old build)
- Row A (headline): learned build vs loop-net-off vs plain MiniCPM5-1B, Qwen3.5-2B, LFM2.5-1.2B on a fresh blind
  chat-puzzle panel (seed 47311, 358b3's settings, blind writer after 358b3 seals; rivals via
  scripts/claude_bmriv_rivals.py). Marks fixed before any run, per ADDENDUM-7/8.
- Row B (headline): day-kind fresh problems after nights, vs the same build with sleep off; no-harm row separate.
- Carry-over row: examples needed to learn a new kind after practising others, vs a fresh net and vs plain with
  the same practice (goals page's main measure). Owner: Sleep research's carry-over tests; 0.2d reports it.
- Supporting rows, same rivals: memory (bank D answerable asks, sel-02d panel), made-up user facts and
  "I don't know" (S1/H3), wrong answers as fact (H1), everyday chat (C1 pair judge vs each rival),
  GSM8K + MMLU-Redux no-harm.
- 3x scaling reported on its own verdict. Demo set seed 47399 n=20, never a mark.

## Order
Nothing is built until H-A and H-B are verified PASS. Then one seal of the joined code, one DEV rehearsal, then
the registered run. Each supporting part joins only on its own verified PASS and only if it exists in Ben's design.
