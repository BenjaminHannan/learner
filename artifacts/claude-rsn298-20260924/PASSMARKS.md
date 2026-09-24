# rsn-298 pass marks (sealed before the panel is run)

Arms: 292 (build_agent292) and 298 (build_agent298 = 292 + install298). Same stubbed router as every
earlier 292 panel run (fable_self122.route122 declines). Scorer: scripts/claude_rsn298_score.py.
Panel: artifacts/claude-branchpanel298-20260924/items.jsonl (blind, 90 items, sealed after a blind
Opus key audit and before any arm is run on it).

- **P298.1 (the fix works).** SAME + DIFFER + PARTIAL + NONE (60 items): 298 right ≥ 48, and
  298 right ≥ 292 right + 30.
- **P298.2 (never invents).** 298 wrong (a "never" string in the reply) ≤ 292 wrong, and 0 wrong
  on NONE.
- **P298.3 (nothing else changes on the panel).** CONTROL: 298's reply is identical to 292's on
  15/15. OVER4: identical on 15/15.
- **P298.4 (read-only).** No question turn writes to the notebook on 298 (0/90).
- **P298.5 (no regressions).** On nhoppanel268, nhoppanel268b, yesnopanel293, corrpanel291 (turn
  and follow-up replies), mixpanel292, hx292 and hp293: 298's reply is identical to 292's on every
  item where 292's reply does not contain "Which one do you mean?". Every item that differs is listed.

298 PASSES only if all five pass. It is proved wrong by: right < 48 on the main four, any wrong on
NONE, any CONTROL or OVER4 reply that changes, or any changed reply in P298.5 outside the
"Which one" items.
