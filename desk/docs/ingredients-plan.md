# Adding the missing ingredients of intelligence (plan, 2026-11-04)

Ben asked (2026-11-04): "Figure out how to add all the new ingredients." This plan covers the gaps found in the first-principles list. Nothing here is built. Every step is one change, with pass marks fixed before it runs and a result that would prove it wrong. Small test worlds (puzzles, synthetic days) stay separate from claims about the real Glim.

## The big idea: 3 engines + sleep
Most of the missing pieces are combinations of three engines that already exist or are being tested:
- **Guesser**: predicts what comes next (guesser.js today).
- **Checker**: judges "is this right?" (NEW, step 1).
- **Cabinet**: remembers (desk + filing cabinet, Experiment M1).

Sleep trains all three. Ben's rule (2026-09-21): sleep is automatic and mathematical. The model never writes rules or picks what to store. So "rules" below come from compression, not from Nanbeige writing them.

| Ingredient | Built from | Step |
|---|---|---|
| Knowing when it's right | checker | 1 |
| Knowing what it doesn't know | checker score = confidence | 1 |
| Experimenting (little scientist) | guesser + sandboxes; gives the checker free labels | 2 |
| Feeling time | timestamps in the cabinet + guesser predicts "when" | 3 |
| Rules from memories | sleep compresses the cabinet into pattern vectors | 4 |
| Analogy | pattern vectors have no names, so recall works by shape | 4 |
| Imagining ahead | guesser predicts "after action a" + checker scores it | 5 |

## Step 1. Checker (+ "I'm not sure")
- **What:** a small head on frozen Nanbeige hidden states (last token of an answer) → P(correct). Motes make K tries in one batch, the checker picks one, and a low top score means "I'm not sure" plus an entry on the wonder list.
- **Labels with known truth, all free:**
  - Learn-quiz answers (graded against sources);
  - generated puzzles (puzzle school, port from LFM3);
  - code it runs in the sandbox;
  - truthnotes marked confirmed or wrong.
- **Why first:** every later step uses it. The toy many-tries test (2026-10-17, far-transfer model, NOT Nanbeige) found the right answer was often among 16 tries (14.8% → 31.2%), but majority vote and self-confidence couldn't pick it.
- **Test (Nanbeige, puzzle-school items, held-out rules):**
  - Step 0 gate: pass@8 ≥ greedy + 8 points. If not, there's nothing to pick from; stop and report.
  - PASS: checker pick ≥ greedy + 5 AND ≥ majority vote + 3, McNemar p < 0.05 vs greedy.
  - Calibration: expected calibration error ≤ 0.10. When it says "not sure", accuracy on the remaining items rises ≥ 10 points.
  - Proven wrong: checker pick ≤ greedy.
- **Compute:** BensPC 5070 Ti after Bedwars and M1, about 1–2 h. Or a vast box with Ben's OK.

## Step 2. Little scientist (learn by poking, not only reading)
- **What:** in bored mode, Glim plays in sandboxes where the world answers back. It logs its guess before every test, and the result is the truth.
  - (a) Python sandbox: "what will this print?", then run it. No network and no Ben files.
  - (b) Puzzle generator.
  - (c) Small grid and text games.
- **What wrong guesses do:** a wrong guess is a surprise. It goes to the cabinet and to sleep, and it becomes a checker label.
- **Choosing the next experiment:** by learning progress (the Sep 21 bored-mode design). No novelty bonus, which avoids the noisy TV.
- **Rules:** memgauge and benFirst still apply. Related outside work to read: Absolute Zero (2025) uses a code runner as the judge of self-made tasks. Untested here.
- **Test:** same nights and same compute, "poking" vs "reading the same material".
  - PASS: poking ≥ reading + 10 points on held-out "what does this print?" + unseen puzzle rules, with no drop > 2 on the general set.
  - Proven wrong: poking ≤ reading.

## Step 3. Feeling time
- **What:**
  - every observation, note and cabinet vector carries a timestamp;
  - the desk gets time features (clock time, time since each slot was written);
  - the guesser also predicts *when* things happen.
- **Test:** only after M1 v1 is reported (one change at a time). Add question type T ("how long ago…?", "what happened right before…?") to M1's synthetic days.
  - PASS: T ≥ B1 + 20 and no drop > 2 on R/L/C/2H.
  - Proven wrong: T ≤ B1.

## Step 4. Patterns = rules + analogy (by math, not by Nanbeige)
- **What:**
  - In sleep, clusters of similar cabinet vectors are compressed into **pattern vectors**: learned prototypes, trained to predict their members with names masked. A pattern is kept only if it lowers the guesser's surprise on the next day, so it has to earn its place.
  - Patterns sit in a second drawer and are recalled like any memory.
  - Because they carry no names, "Sam emailed: meeting moved" can recall the pattern learned from "Maya texted: practice moved". That is analogy.
  - The toy new-names work (Exp 29) showed name binding can be learned, in the toy only.
- **Needs:** M1 to pass first.
- **Test:** synthetic days with hidden repeating patterns and fresh names each day; question type P ("what usually happens after X?").
  - PASS: pattern-M1 ≥ M1 + 10 on P, with no drop > 2 on the other types.
  - Proven wrong: pattern-M1 ≤ M1 on P.

## Step 5. Imagining ahead
- **What:** predict the outcome of a few options, score them with the checker, then act.
  - Level 1 (tiny): the speak-o-meter compares "speak now" against "wait 5 min" using predicted reply/👎 odds.
  - Level 2 (Nanbeige): lookahead search in the step 2 games, where the guesser predicts the next state after each move.
- **Needs:** steps 1 and 2.
- **Test:** in held-out games at the same compute, plan-then-act vs act-at-once.
  - PASS: win rate +15 points.
  - Proven wrong: planning ≤ no planning.

## Order and reasons
1 → 2 → 3 → 4 → 5.
- The checker comes first because it gives the others a judge.
- The little scientist makes the checker's training data.
- Time is cheap and rides on M1.
- Patterns need a working cabinet.
- Planning needs everything before it.

The GPU is shared with Bedwars: one job at a time, ≤ 30 min per test where possible, $30/week cap.

## Related reading (background, not checked against our setup)
Titans (2025, surprise memory), Sleep-time Compute (2025, thinking while idle), Absolute Zero (2025, self-made tasks + code judge), generative verifiers (2024), DreamerV3 (2025, imagining inside a learned world model).

## Round 2 ideas (Ben, 2026-11-04 ~10:10): approved, queued after Tasks A and B finish
- **Watch me once:** Ben narrates out loud while doing a task on screen. Glim watches: eyes on the screen at 1–2 fps, ears turning speech into text, and the app/window steps. The narration is the text anchor. Result: a saved skill (steps + what each step looks like + Ben's words) that Glim can guide him through or redo with permission. Sleep trains on narrated demos.
- **Think longer when unsure, automatically:** no button. The checker's confidence decides: high → answer at once; low → more tries / more thinking (bored mode always; chat only within benFirst speed limits).
- **Model of Ben, trained into the weights by sleep:** what Ben knows, likes and is working on goes into the adapter, not only the notes. Sources: Ben's own words (text anchor) and feedback; `maybe` never trains. There must be a correction path (corrections are trained too). The LFM3 Idea 1 test found 3 of 6 facts never learned, so learning reliability is the risk.
- **Choose where to look:** spend attention (eye/OCR budget, wake-ups) on the most surprising window or region.
- **Grow new brain parts when full:** freeze what's there and add new capacity, trained only in sleep.
  - Option 1 (first): a new small expert adapter + router. The toy Exp 43G–I router over frozen skills was perfect 6/6, in the toy only.
  - Option 2: a new identity-initialised layer (block expansion, as in LLaMA Pro, 2024). It starts as a no-op; ~110M params each; each one makes the model ~4–5% slower.
  - "Full" = sleep can't learn new things without failing the seatbelt test on old ones.
  - Test idea: a sequence of sleeps on new topics. PASS: growing keeps old quiz scores (drop ≤ 2) AND is ≥ 15 points better on old topics than a fixed-size adapter, with new-topic learning within 5 points.
