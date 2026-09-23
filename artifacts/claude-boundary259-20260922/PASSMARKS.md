# Exp 259 PASSMARKS (value boundary) — written before the seal

Base: 252b (scripts/claude_loop252b_agent.py + artifacts/claude-correct252b-20260922/loop252b-config.json).
One change: scripts/claude_fix259_boundary.py (Boundary259EarsMixin), wired by scripts/claude_loop259_agent.py.
Driver: scripts/claude_bound259_runall.sh (stage pre = M2..M7 + dev259 info; stage m1 = blind panel).
Scorer: scripts/claude_bound259_score.py. Verdict PASS only if every mark M1..M7 passes.

## What the change does (as built)
1. Inside 252's explicit-denial path: if the denied span starts with a stored value of that (subject, relation)
   followed by ", " " - " " — " "; " " (" or the end, remove that value through 252's _remove252 with 252's
   "OK, I removed ..." reply. Case normalisation = 252's (lower-case). "Brimwell Hall" never matches "Brimwell".
   252's own clause-end words (_TAIL_RX: anymore, any more, now, ...) are dropped from the part before the boundary.
2. No match: "I don't have <part before first boundary> as S's R, so I didn't change anything."
3. Rule 3 (never "I don't have V" when (S,R,V) stored), interpreted to cover two places the pilot showed:
   3a tail landed in the relation words ("Tolly isn't Rune's boss (that was last year)") -> cut, re-read, then 1-2;
      unreadable -> 252's "Which fact is wrong?" ask (no write).
   3b "X's R is not V, <tail>." owned by 154f (b252-014 "... which is old news") -> 1-2 on 154f's own parse,
      only when the value holds a boundary; otherwise 154f unchanged.
   Plus: when the head is a stored value + extra words ("Garrow Hall" with "Garrow" stored), the reply is
   "I have S's R as Garrow, not Garrow Hall, so I didn't change anything." (no write), so it never reads as
   "I don't have Garrow".
Everything else is 252b, byte-identical. b252-035 "That's wrong, that's old news." is NOT fixed (stays junk).

## Marks, bars, predictions
| Mark | Bar | Prediction |
|---|---|---|
| M1 corrtail258 (80, blind) | that_denial >= 10/12; other_tail_denial >= 8/10; 0 false claims /80; 0 junk except that_correction / pure_denial_that items where 252b makes the same junk; 0 wrong values in that_denial + other_tail_denial; no other family newly wrong vs 252b; question_tail 6/6; unstored_tail 6/6; keep 8/8 + control 16/16 byte-identical to base252b | that_denial 7-11/12, other_tail_denial 5-9/10; false claims 0-2; question 6/6, unstored 6/6, keep 8/8, control 16/16. Likely FAIL on that_denial or other_tail_denial (and possible junk in other_tail_denial) |
| M2 dev252b | 5 false replies gone; 0 wrong removals; 0 question writes; junk only b252-035; controls identical except ms_per_turn; every other change as predicted | PASS |
| M3 corrpanel252 (test-only) | changes exactly as predicted; 0 new wrong values or junk writes | PASS (risk: an item shape not seen in dev) |
| M4 suites rt136,rt143,sessions152,bench | move list = 252b's; 0 new WRONG / WRONG-WRITE / junk / lost OK | PASS |
| M5 sleep smoke | identical to smoke-252b.json except labels, paths, timing | PASS |
| M6 restart dialogs (138k v-dialogs, v-supp) | 0 ghosts; 0 failed duplicate checks; replies = 252b's | PASS, 0 moves |
| M7 latency | median added per turn <= +5 ms vs 252b, same session | PASS (pilot +0.04 ms) |

## Predicted moves by id
M2 dev252b (vs 252b rows made in the same session): moves are exactly b252-001, b252-003, b252-010, b252-013,
b252-014, b252-015. Each becomes "OK, I removed <V> as <S>'s <R>." removing exactly that stored triple, follow-up
"I don't know <S>'s <R>." (001/003 Brimwell as Arlo's employer, 010/013 Pellic as Dagny's language,
014/015 Sill as Evard's manager — as seen in the pilot). All other rows identical. b252-035 stays junk.
(The brief says 5 false replies; the pilot shows 6 rows where 252b says "I don't have <V ...>" while V is stored;
014 is the 154f-routed one, fixed by 3b.)

M3 corrpanel252: items cannot be read before the seal (TEST-ONLY), so the prediction is the sealed mechanical rule
in claude_bound259_score.py m3: a row may move only if 252b's registered reply is "I don't have V as S's R[...]"
with a clause boundary in V or R, and may only become (a) "OK, I removed ..." removing exactly one (S, *, head(V))
triple, (b) "I don't have head(V) as S's ..." / "I have S's R as ..., not ..." with stores unchanged, or
(c) "Which fact is wrong? ..." with stores unchanged. Any other move, new wrong value or new junk = FAIL.
The moved ids are listed after the run.

M4: moves equal 252b's (rt136 4, sessions152 1, rt143 0, bench 0); rows equal 252b's except seconds.
M5: identical (probes 5/5, taught 50/50). M6: no moves.

dev259 (information, 66 items; pred field in dev259.jsonl): 259 right on every item marked "right";
misses 004 (", not anymore"), 008 (", sadly" junk from 252b's two-clause path), 010, 011, 012, 015
(base ears cannot read the sentence) stay as in 252b. Keep 15/15 identical to 252b; 058/059 junk stays (258's job).

## Known limits (predicted to stay wrong in M1)
First-person turns ("My boss isn't Tolly, that was last year."), "doesnt", "stopped working at", ", which is a
shame" -> "couldn't save" (unchanged); ", she retired" / ", unfortunately" / ", sadly" -> 252b's two-clause
correction path stores junk ("Nell retired", "unfortunately") — not the denial path, not changed by 259.

## Deviations / interpretations (declared before the seal)
- 3a and 3b go beyond the literal "denial path" text of rule 1; both are justified by rule 3 and only fire when a
  clause boundary is present. The pronoun denial path reaches _deny_named252 and is covered too.
- The "I have S's R as V, not V W" wording for stored-value-plus-words heads is my rule-3 wording choice.
- M3 ids cannot be listed before the seal (test-only panel); the sealed mechanical rule stands in.
- Scorers run under /usr/bin/python3 (3.9) because python3 in bash is a broken binary on this Mac.
