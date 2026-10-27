# rsn-358b2 pass marks (fixed before any run; sleep research thread, 2026-09-26)

Question: does putting the learned loop reasoner between the 1B's reading and the 1B's reply solve chat requests the
1B alone cannot? This is the first real chat turn with a learned middle (Ben's reader -> reasoner -> talker design,
13:53 UTC; thread manager 14:21 and Ben's goals interview 14:32-14:37: reasoning is a headline feature).
Code: scripts/claude_rsn358b2_bridge.py. 1B: plain MiniCPM5-1B (openbmb/MiniCPM5-1B, bf16, enable_thinking=False,
greedy). Loop net: rsn-358a loop-s1 final.pt (sha256 c9f4934f2ab62a0abd0c5103c10785b6286aea9fdafabd06ebbf7727bf3ca2c4,
358a v2 stop rule), picked before any bridge run. Because 358a nets cannot read a legend, only squares whose clues show
every number are used. Requests: code templates, seed 35900 + size, 100 per size, sizes 5 (practised by the net),
6 and 7 (bigger). Every score is read by code from the final message against the true puzzle.

| mark | pass |
|---|---|
| B0 validity | the 1B's copy of the square is exact on >= 80/100 at each size; else INCONCLUSIVE (a copying problem, not a reasoning one) |
| B1 | bridge right - 1B-alone right >= +40/100 on 6x6 AND on 7x7 |
| B2 | bridge "wrong answer given" <= 1B-alone "wrong answer given" at every size (the bridge may say "I couldn't", never guess more) |
| B3 report | per stage: copy exact / unreadable, net right given the copy, internal check pass, reply faithful to the net's grid; ceiling C (code reads the request); mean rounds; transcripts |

**PASS = B0, B1 and B2.** Anything else with B0 met = FAIL.
**Proved wrong** ("a learned reasoner in the middle beats the 1B alone on its own kind of problem"): B0 met and bridge
right - 1B-alone right <= +10 at 6x6 and 7x7.

Predictions before running: the 1B alone solves almost none (rv-385: restart 0/160 on 5x5 within 60 choices); the
358a loop solved 270/300 (grids6) and 192/300 (grids7) on its own tests, higher where no symbol was hidden. Expected
bridge right ~75 at 6x6 and ~55 at 7x7 if copying is good. PASS maybe 70%. Main risks: the 1B miscopies, or rewrites
the finished rows in its reply.
Limits: narrow (one puzzle kind); the net is 358a's (pre-legend); not the 0.2c build's turn loop (a stand-alone
chain), so it shows the design works end to end, not that the build uses it yet.
