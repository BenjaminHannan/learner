# Practice-2 results so far (pilots on the M1, Oct 27 2026)

Knights and knaves, OpenCode harness (the agent OpenBot runs), K2-3.7B q4. 60 practice puzzles x 2 tries, 1 night, the same 40 fresh test puzzles, 1 try each.

| Model | Accuracy | Tool calls/try | Tokens/try | First turn is a bare answer |
|---|---|---|---|---|
| A0 (base) | 42.5% (17/40) | 1.15 | 460 | 13/40 |
| P1, pilot 1 (bare answers trained) | 32.5% (13/40) | 0.125 | 124 | 31/40 |
| Pilot-1 adapter at 1/4 strength | 40.0% | 0.85 | 380 | 18/40 |
| Pilot-1 adapter at 1/2 strength | 22.5% | 0.125 | 71 | 36/40 |
| P1, pilot 2 (addendum 2: bare answers masked) | 52.5% (21/40) | 2.225 | 1031 | 0/40 |

Pilot 2 against the addendum-2 marks (shown): first-turn answer-first 0 <= 20 PASS; tool calls 2.225 >= 0.58 PASS; accuracy 52.5% >= 37.5% PASS. The wrong-if line (tool calls < 0.3) was not hit.
Pilot 2 vs A0, paired: both right 9, only A0 8, only P1 12 (+4 net, sign test p ~ 0.5): NOT a significant gain at n = 40. The pilot shows the collapse is fixed, not that practice helps.
Training peak 11.7 GB (pilot 1: 37.4 GB before the trained-positions-only logits fix). Next: C arm (no checker) on the same day-1 tries; then the full run (PREREG-2) on a 4090.
