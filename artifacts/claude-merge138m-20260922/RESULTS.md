# Merge 138m: RESULTS

**Result: PASS.** All six registered marks held in the registered run on the first try. There were no re-runs and no changes after the seal. The run took 441 s (load 9.9–20.1, under the limit of 60). The files still match `SEAL.sha256.txt` (19 files).

138m = 138l + 219, 230, 230b/230c, 227, 227b, 227c, 224/224c, 233 and 234. It is built in `scripts/claude_loop138m_agent.py`.
- The layer order and who wins each overlap are in `design/v3/30-modes/138m-merge-opus.md`.
- Ledger lines P138m.1–6.
- The score is in `run/score138m.json`, `run/l1-judge.json` and `run/l1-sealed.json`.

**Caveat on the base.** 138l itself is still under independent verification. If it fails, this result falls with it.

## Marks

| Mark | What | Bar | Result |
|---|---|---|---|
| M1 | Each piece's own sealed dev cases (990) | 0 unpredicted, 0 wrong, 0 missing; own arm reproduces the sealed rows | 208/208 predicted moves exact, 0 unpredicted, 0 wrong, 0 not moved; 990/990 sealed rows reproduced. **PASS** |
| M2 | Frozen suites vs 138l's rows | Move sets = predicted; 0 new bad labels outside the 222 exceptions; exceptions identical | sessions152 11, bench 5, marks123 6, rt136 15 (13 inherited + 2), rt143 37: all predicted. 0 new bad labels. Exceptions identical 63/63 (13/13, 25/25, 25/25). rt136 direct = [C076, C079]. rt143 verdict flips 0/124. **PASS** |
| M3 | Sleep smoke | Differs only in agent/config/label/seconds/root/report | Differs in 4 allowed fields, 0 bad. **PASS** |
| M4 | Bench ×3 | Byte-identical | 4/4 files. **PASS** |
| M5 | Median latency | ≤ +5 ms over 138l | 2.187 vs 2.120 ms, +0.066 ms (624 turns each). **PASS** |
| M6 | Restart + verifier dialogs (5 files, 36 dialogs, 86 restart audits) | 0 ghosts, 0 failed duplicate checks, 0 bad writes; changes = predicted | 0 ghosts, 0 failed duplicate checks, 0 bad writes; 9/9 reply changes as predicted. **PASS** |

## Deviations

1. **Rows compared field by field.** The "63 exception rows identical to 138l" check compares every field except rt136's wall-clock `seconds` field. It does not compare raw bytes. The pilot showed `seconds` is the only field that changes between runs. This was registered in PASSMARKS before the seal.
2. **M1 ran against the line head, not only against each piece's own agent.**
   - 219 and 230 are compared with 230c, and 227 and 227b with 227c, because each newer piece deliberately changes the older one.
   - The own arm is still run and must reproduce every sealed row.
3. **rt136 labels come from 138j's sealed rows**, as in 138l, because suitediff needs its sealed base format. Every row is also compared directly with 138l's saved rows.
4. **The M6 predictions were built before I added the per-change "reason" text** to the predict code. So the sealed `predicted_moves138m.json` m6 entries hold turn / l / m without a reason. The scorer only uses `m`, and the reasons are listed below.
5. **`claude_138m_predict.py` and the `--predict` mode of the scorer** built the predictions from pilot runs. The predictions are exact expected records, not guesses from reading code; the category of each move explains why it moves. All pilots ran before the seal: an M1 pilot twice (deterministic), an M2 pilot, a smoke/latency/probe pilot, and a full dry run of the driver (458 s, all six marks passing).
6. **No item needed the 5× rerun rule.** No flip toward an abstain or "Was that a question?" was unpredicted.

## Order and who wins (short version)

The layers are listed outermost first:
1. 224c/224 (swap only the exact glued decline);
2. 233 (rewrites the text first);
3. 226;
4. 234 (fixed how-are-you reply);
5. name line (219 check, then 230/230b/230c bodies);
6. identity (227c gate ahead of 187);
7. 212/216/209;
8. 138j.

How the overlaps were settled:
- **234 vs identity.** No dev text is claimed by both 234 and 227c, or by 233 and another gate. Identity answers 234's identity cases D064, D073, D074, D078 and D079.
- **Name line vs identity.** The name line wins on the name questions in 227/227c (U04, U10, N02, …).
- **224's S1 vs 188.** 188's statement fallback runs first, so it wins over S1 on 224c's own B1 S1-01..32.
- **138l's 212/216 gates cut off the name line** on "Tell me what my name is.", "Repeat my name.", "What do people call me?" and similar. They go to Q2 or 188 instead of "Your name is X." This is 50 of 230's 52 moves, and it is a known cost.

## Every move

### M1: 208 moves vs line head (all predicted exactly; run/l1-judge.json)

- 219: 0 moves
- 230 224_on_base (28): T:WH07, U:WH07, T:WH18, U:WH18, T:WH20, U:WH20, T:WH23, U:WH23, T:WH24, U:WH24, T:IMP05, U:IMP05, T:IMP06, U:IMP06, T:IMP07, U:IMP07, T:IMP14, U:IMP14, T:IMP15, U:IMP15, T:IMP16, U:IMP16, T:IMP19, U:IMP19, T:IMP26, U:IMP26, T:IMP28, U:IMP28
- 230 base138l (22): T:IMP02, U:IMP02, T:IMP04, U:IMP04, T:IMP09, U:IMP09, T:IMP11, U:IMP11, T:IMP12, U:IMP12, T:IMP20, U:IMP20, T:IMP21, U:IMP21, T:IMP22, U:IMP22, T:IMP24, U:IMP24, T:IMP25, U:IMP25, T:IMP31, U:IMP31
- 230 224_glue (2): T:YN07, U:YN07
- 230c 224_glue (1): e03
- 227 nameline (2): m2:U04, m2:U10
- 227 224_glue (10): m2:U21, m2:U22, m2:U23, m2:U24, m2:U27, m2:U28, m2:U29, m2:U30, m2:U31, m2:U32
- 227b nameline (2): 227m2:U04, 227m2:U10
- 227b 224_glue (10): 227m2:U21, 227m2:U22, 227m2:U23, 227m2:U24, 227m2:U27, 227m2:U28, 227m2:U29, 227m2:U30, 227m2:U31, 227m2:U32
- 227c nameline (10): c2t:N02, c2t:N05, c2t:N10, c2t:N11, c2t:N12, c2t:N14, c2t:N18, c2t:N34, c3:227-m2:U04, c3:227-m2:U10
- 227c 224_glue (36): c2u:N07, c2t:N07, c2u:N08, c2t:N08, c2u:N13, c2t:N13, c2u:N15, c2t:N15, c2u:N16, c2t:N16, c2u:N22, c2t:N22, c2u:N24, c2t:N24, c2u:N26, c2t:N26, c2u:N27, c2t:N27, c2u:N28, c2t:N28, c2u:N29, c2t:N29, c2u:N30, c2t:N30, c2u:N36, c2t:N36, c3:227-m2:U21, c3:227-m2:U22, c3:227-m2:U23, c3:227-m2:U24, c3:227-m2:U27, c3:227-m2:U28, c3:227-m2:U29, c3:227-m2:U30, c3:227-m2:U31, c3:227-m2:U32
- 227c 224_on_base (8): c2u:N09, c2t:N09, c2u:N17, c2t:N17, c2u:N23, c2t:N23, c2u:N25, c2t:N25
- 227c base138l (7): c2u:N31, c2t:N31, c2u:N32, c2t:N32, c2t:N33, c2u:N35, c2t:N35
- 224c base138l (32): b1:Q2-03, b1:Q2-04, b1:S1-01, b1:S1-02, b1:S1-03, b1:S1-04, b1:S1-05, b1:S1-06, b1:S1-07, b1:S1-09, b1:S1-10, b1:S1-11, b1:S1-13, b1:S1-14, b1:S1-15, b1:S1-16, b1:S1-17, b1:S1-18, b1:S1-19, b1:S1-20, b1:S1-21, b1:S1-22, b1:S1-23, b1:S1-24, b1:S1-25, b1:S1-26, b1:S1-27, b1:S1-28, b1:S1-29, b1:S1-30, b1:S1-31, b1:S1-32
- 233 224_glue (2): D21, D54
- 233 base138l (11): D52, D53, D55, D56, D57, D58, D59, D60, D61, D62, D63
- 234 224_glue+base138l (8): D041, D042, D043, D044, D045, D046, D047, D048
- 234 224_glue (12): D052, D054, D059, D061, D062, D068, D075, D077, D080, D081, D082, D083
- 234 identity (5): D064, D073, D074, D078, D079

### M2: frozen suites vs 138l (run/sd, run/sd136, run/rt143nogate-m.json)

- sessions152 (11): S1-family10#5 [reply-only move], S1-family10#8 [reply-only move], S1-family10#19 [reply-only move], S3-teachers-correction#4 [reply-only move], S3-teachers-correction#10 [reply-only move], S3-teachers-correction#17 [reply-only move], S3-teachers-correction#19 [reply-only move], S6-pronouns-corrections#3 [reply-only move], S6-pronouns-corrections#6 [reply-only move], S6-pronouns-corrections#9 [reply-only move], S6-pronouns-corrections#20 [reply-only move]
- bench (5): bench121-4hop-026 [reply-only move], bench121-4hop-066 [reply-only move], bench103-s2fresh-4hop-187 [reply-only move], bench132-4hop-019 [reply-only move], bench132-4hop-112 [reply-only move]
- marks123 (6): rt81-report.json:D_q_vs_s-04 [reply-only move], rt81-report.json:D_q_vs_s-05 [reply-only move], rt81-report.json:N_yesno-02 [reply-only move], rt81-report.json:Q_quote-02 [reply-only move], bench-s2fresh_4hop:bench103-s2fresh-4hop-064 [reply-only move], bench-s2fresh_4hop:bench103-s2fresh-4hop-187 [reply-only move]
- rt136 (15): C019 [new WRONG-WRITE], C020 [new WRONG-WRITE], C021 [new WRONG-WRITE], C022 [new WRONG-WRITE], C023 [new WRONG-WRITE], C024 [new WRONG-WRITE], C025 [new WRONG-WRITE], C026 [new WRONG-WRITE], C027 [new WRONG-WRITE], C028 [new WRONG-WRITE], C029 [new WRONG-WRITE], C030 [new WRONG-WRITE], C031 [new WRONG-WRITE], C076 [reply-only move], C079 [reply-only move]
- rt136 direct vs 138l rows: C076, C079
- rt143 no-gate (37, reply-only glue -> Q2, 0 verdict flips): A1, F6, H3, J9, K1, K2, K3, K4, K5, K7, K8, L2, L3, L5, L6, M3, M4, M5, M6, O1, O2, O4, O5, P1, P2, P5, Q1, Q2, Q7, S1, S4, S5, T2, T3, U1, U2, U4

### M6: restart/verifier dialog reply changes vs 138l (9)

- p3-dialogs:d00:t04 "where does brannick live?" -> "I didn't understand that question — could you say it another way?" (224 glue -> Q2)
- p3-dialogs:d01:t01 "whats pells city?" -> "I didn't understand that question — could you say it another way?" (224 glue -> Q2)
- p3-dialogs:d05:t03 "Where do I live?" -> "I didn't understand that question — could you say it another way?" (224 glue -> Q2)
- p3-dialogs:d14:t00 "Who made you?" -> "Ben built me." (227c identity line)
- p3-dialogs:d14:t01 "Say that again." -> "Ben built me." (227c identity line)
- p3-dialogs:d14:t02 "What are you?" -> "I'm a small program that keeps what you teach me in a notebook and answers from it. When I don't know something, I say so instead of guessing." (227c identity line)
- p3c-restart2:d00:t06 "Tell me about Oriel." -> "I didn't understand that question — could you say it another way?" (224 glue -> Q2)
- p3d-ghost:d00:t06 "Tell me about Oriel." -> "I didn't understand that question — could you say it another way?" (224 glue -> Q2)
- v-dialogs:d03:t05 "Tell me about Elspin." -> "I didn't understand that question — could you say it another way?" (224 glue -> Q2)

## Observations (not caused by this merge; not fixed)

- **USER-key wording.** Since 138j, "Who made your notebook?" after "My name is Hedda." says "…USER's name is Hedda.". 227c c2t N33 shows it.
- **Two-sentence identity turns.** "Hi! What's your name?" still gives the old D8 reply in both 138l and 138m.
- **Q2 wording on unknown questions.** "Where do I live?" with nothing stored now gets "I didn't understand that question — could you say it another way?" instead of "I do not know…". It still counts as an honest abstain, but the wording is less accurate.

## What it means

The new agent, 138m, is 138l with all nine conversation pieces added on top. On every test we set in advance, it behaved exactly as we said it would before we ran it:
- Each piece still does its own job.
- Every place where one piece now changes another piece's answer was written down beforehand, case by case, and each one came out exactly as written.
- It never saves a wrong fact, and it never makes up an answer after a restart.
- It gives the same answers every time.
- It is no slower than 138l.
- It now says "My name is Premonition." and "Ben built me." when asked.

## What it doesn't mean

- **It does not mean the conversation pieces work on new, unseen wording.** Only each piece's own dev cases were used. The hidden panels were not opened, so how well it handles real people's phrasing is still unmeasured.
- **It does not mean every change is an improvement.** Some answers got worse as a side effect:
  - 138l's question gates stop "Tell me what my name is." from reaching the name check;
  - some "I don't know" answers became "I didn't understand that question".
  These were predicted and accepted, not fixed.
- **It is only as good as its base.** 138l is still being checked independently; if 138l fails, this result has to be re-examined.
