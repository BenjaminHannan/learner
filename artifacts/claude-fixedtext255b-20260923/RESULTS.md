# Exp 255b: the one follow-up to 255 (fixed-reply text) — results (finishing agent, 2026-09-23)

## Result first

**PASS on every mark I score (M2, M4, M5, M6, M7), exactly as predicted in P255b.1–P255b.9.**
The sealed scorer's mechanical labels pass: 162 M2 moves equal the 162 predicted ids (0 missing, 0 unpredicted), 38 M4 replies all "same meaning" (0 worse, 0 store changes), M5/M6/M7 all pass. The extra report shows the only 255b-vs-255 differences are 26 Part A (T02) lines, 0 unexpected. M1 (228 renders, sealed) and M3 (153 changed turns, runner done) are graded by the director and carry no grades here. Full exp PASS still needs the director's M1+M3 grades.

## Marks table (integer counts)

| Mark | Verdict | Counts |
|---|---|---|
| M1 fixed-text grammar | Graded by the director separately | fixedtext.jsonl: 228 rows (171 changed-template renders, 57 unchanged), seed 2550923, sealed in SEAL2 (verified OK). sha256 `1740e0b96f6062acd2b655f46f4359224277509774d874abcb2c83537ff019a4` |
| M2 suites vs 138m | PASS (sealed scorer) | Reply-only moves 162 (rt136 48, rt143 42, sessions152 25, bench 47 = 4+37+5+1); 0 verdict, 0 status, 0 store, 0 write changes; GATE clean; move list equals the 162 predicted ids exactly (0 missing, 0 unpredicted). rt143 no-gate: exactly the 45 predicted reply-only moves, 0 unexplained |
| M3 239 panel runner | Runner done, judging not run here | 30 conversations, 244 rows, 0 empty, 0 errors, run ONCE. Changes vs 138m registered transcripts: 244 turns compared, 153 changed turns, 0 unexplained, 0 store changes, 0 missing. Per part: 62 [A] (T02), 0 [B], 91 [carry]. Paths: artifacts/claude-fixedtext255b-20260923/m3-reg/transcripts-255b.jsonl + .md, changes-255b-vs-138m.jsonl + .md + -summary.json + .json (panel format). changes jsonl sha256 `81c6f393350dce7d3b7d80d79fb0747ae0d08e1e17ebf1fd9a87b9ff320a63c5` |
| M4 verifier probes | PASS (sealed scorer + fixed director ruling) | 38 changed replies: 38 same meaning (20 T02-lines incl. the 8 previously flagged probes A06, B04, B05, B20, D02, D03, D04, D08, now true under the ruling), 18 carryover; 0 worse (unexplained), 0 store/event changes, 0 unpredicted, 0 predicted-not-seen |
| M5 sleep smoke | PASS (sealed scorer) | Differing fields only: .agent, .config, .label, .seconds; 0 bad fields |
| M6 restart/dialogs | PASS (sealed scorer) | 17 reply changes (exactly the 17 predicted with predicted texts: 6 T02 new Part A text, 11 carryover byte-identical to 255), 0 ghosts, 0 failed duplicate checks, 0 bad writes, both vs 138m saved and vs same-session 138m |
| M7 latency | PASS (sealed scorer) | median 138m 2.285 ms, median 255b 2.293 ms, delta +0.008 ms (bar ≤ +2.0 ms); n 624 + 624 |
| S1 identity check | Not applicable | No new scorer version was added; all frozen anchors kept |
| Extra 255b vs 255 (no bar) | PASS | 26 differences on M4 probes + M6 dialogs, all Part A (20 M4 T02-lines, 6 M6 T02-lines), 0 unexpected, 0 zero-count lines hit |

Seals: `shasum -a 256 -c` on SEAL.sha256.txt (21 lines) and SEAL2.sha256.txt (fixedtext.jsonl) — every line OK, exit 0, after all runs. No sealed file changed after the seal.

## Every predicted move, per part (from predicted-moves255b.md)

- M2 162: 52 [A] T02-lines (new Part A text), 0 [B], 110 [carry] (T05 36, T06 42, T07 4, T08 19, T14 5, T16 2, T19 3, T60 1), all byte-identical to 255's registered texts except the [A] lines.
- M2 no-gate 45: 37 [A], 0 [B], 8 [carry].
- M4 38: 20 [A] (A02, A06, A15, B04, B05, B20, C14, D02, D03, D04, D06, D08, D10, N02, N03, N05, N07, N08, N09, R07 — all T02), 0 [B], 18 [carry].
- M6 17: 6 [A] (p3-dialogs d00t04, d01t01, d05t03; p3c-restart2 d00t06; p3d-ghost d00t06; v-dialogs d03t05 — all T02), 0 [B], 11 [carry] (T05 5, T39 4, T38 2).
- M3 153 changed turns: 62 [A] (T02), 0 [B], 91 [carry] (T05 57, T14 21, T03 7, T30/T08/T21/T16/T19/T06 1 each).
- Part B (zero-count) lines in live runs: 0 everywhere (no zero-count reply occurs in the suites, probes, dialogs or panel). Part B is proven by the unit sweep (519 renders, 0 failures) and the M1 zero-case renders the director grades.

## Moves, misses and deviations

- M2, M4, M5, M6, M7, Extra: every count above matches the sealed predictions exactly; 0 misses, 0 unexplained moves/differences, 0 store changes anywhere.
- Unit tests: 60 templates + 519 sweep renders, 0 failures (before the seal; re-run not needed after).
- The 239 panel was run exactly ONCE on 255b, after the seal. It was never read item by item, never tuned on, and nothing was graded or judged here; only mechanical counts were computed.
- Declared pre-seal deviations (from PASSMARKS.md, unchanged): 228-guard order via install-at-import; rt143 base rows from a same-session 138m run; base138m-rows under artifacts; single-text templates rendered once (171 changed renders); bench prose corrected to 47 (4+37+5+1); out-of-scope texts left unchanged incl. T04 keeping 255's text.
- No new deviations after the seal: no sealed file changed (seals re-verified OK), no driver-only fix, no re-runs (the ~1-in-800 flake never appeared: registered M2/M4/M6 matched the pilot id-for-id).
- M1 trial render (228 rows) was generated to scratch before the seal to validate the generator; the sealed fixedtext.jsonl was generated after the seal with the sealed code. The scratch trial was deleted.
- Out of scope / not mine (inherited from 255): "hello there" save-failure reply; "Hi! What's your name?" user-name reply; "Say my name." pretend routing; 212/216 name-question gates; "I'm Sabella." not saved; junk-person teaches; "Who lives in Oslo?" opinions reply.

## What it means (plain high-school English)

- Both dishonest wordings from 255 are gone. The confused-question reply no longer claims "I don't know that" when the answer is sitting in the notebook — it honestly says it didn't understand and asks you to rephrase. And no reply ever says the word "zero" for a count again ("zero turns" is now "we haven't had any turns yet", and six similar fixes).
- Nothing else moved: all 162 suite moves, all 38 probe replies and all 17 dialog replies are exactly the predicted ones, with zero wrong answers added or removed, nothing stored differently, and the agent is just as fast (+0.008 ms).

## What it doesn't mean

- It does not mean the agent got better at answering: 0 verdict changes everywhere; this experiment only fixes the wording of canned replies.
- It does not mean the conversation panel judged anything: the M3 judges never ran here, so the 153 changed conversation turns carry no correctness or grammar grades yet.
- It does not mean M1 passed: the director grades the 228 fixed-text renders separately.
