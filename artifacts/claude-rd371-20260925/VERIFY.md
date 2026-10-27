# rd-371 = REGISTERED FAIL (verified by the "Fix: reading facts from chat" thread, 2026-09-25 ~20:50 UTC)

Builder result: origin/builder-outbox:artifacts/claude-rd371-20260925/RESULTS.md (vast.ai 5090, ~$0.37 of $1.50).

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| V1 right facts saved | B >= A + 30 (136) | B 15, A 106 | FAIL |
| V2 safe | B wrong turns <= 2 and <= A + 1 | B 0, A 2 | PASS |
| V3 no invention | <= 1 | 0 | PASS |
| G1 dev all-or-nothing hits | B at T_B >= A at 0.995 | B 400, A 462 | FAIL |
| G2 time | B median <= A + 400 ms | 977 vs 958 ms | PASS |

Proved-wrong clause TRUE (15 <= 116): as registered, the checker does not recover facts the cutoff throws away.

## What I checked
- Dev sweep recount from the pushed dev_verified.jsonl with claude_lis300_score.py on lis-301 dev (959 turns, 761 gold):
  B hits/wrong turns 0.95 718/3, 0.99 705/3, 0.995 682/3, 0.999 590/2, 0.9995 529/1, 0.9999 400/1; A at 0.995 462/2. Exact match.
- score_A/score_B read from the pushed JSONs (counter keys; absent = 0). Panel files not opened.

## Diagnosis (dev only; inferred for the panel, which is never read)
1. My threshold rule was lopsided. A's rule (lis-300) falls back to 0.995 when no value reaches 0 wrong turns; B's rule fell back
   to the LARGEST grid value. One dev turn that no cutoff removes pushed B to 0.9999: "Guess my favorite color is blue." (o0a2-q050,
   key says no save; the checker says yes at 0.99992, and the old gate saves it too, at min-token 0.99988). At A's own dev safety
   (2 wrong turns) B keeps 590 dev hits vs A's 462 (T chosen on dev, so optimistic; report only, not a result).
2. The checker never saw a long turn. Its training prompts are at most 450 characters (rebuilt vdata: p50 201, p99 339); lis-301 dev
   turns are all under ~200 characters. The panel is long multi-fact chat: B saved 1 of 153 read long_multi facts (A 38) and
   8 of 126 trap facts (A 53), a far bigger drop than on dev (400 vs 462). Suggested, untested.

## Next (the one diagnosis-driven follow-up; not queued)
Train the checker on long sources (whole chat turns and the 6-turn windows rd-378 notes cite), ask it about plain sentences as well as
relation facts, and pick T by the same rule as the arm it replaces. Built after rd-378 lands, because the note checker is where the
answer path uses it (382 store: every answer statement is checked against its cited text).
