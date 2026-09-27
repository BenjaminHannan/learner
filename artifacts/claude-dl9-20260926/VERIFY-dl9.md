# dl-9 VERIFY (Fix-sleep thread, written 2026-09-27T12:18:55Z from `date -u`)

**Verdict: PASS**, in PASSMARKS' own words. The four marks all hold:
- H1 forgetting stopped;
- H2 learning kept;
- H3 switch learned;
- H4 choosing beats chance.

It is not INCONCLUSIVE, and it is not proved wrong.

The scope is narrow: 2 seeds, one frozen MiniCPM5-1B (rev 87179e5c), and number-puzzle days only. The switch had an easy job, because it only had to tell day puzzles apart from quiz questions the base wrote itself. See "Scope" below.

## Sources
- The builder's results are on origin/builder-outbox at dfb8e2895 (job 151-fixsleep-dl9pc-b, BensPC, $0). Copied to main unchanged:
  - RESULTS-gpu.md (sha256 82d9f1e6...7d81)
  - gpu/dl9_results.json (e636519c...8db0)
  - gpu/log.txt (991ccb75...fa16)
- scripts/claude_dl9_experts.py sha256 b6b0ac2c...6250 is the sealed file (ebe89c7a0). The builder reports no edits and "dl9 selftest ok".

## Blind recount
A read-only helper recounted everything from dl9_results.json. It did not see RESULTS-gpu.md or this file. It did not use the file's own "marks" block.
- It recomputed S's lost and gained items from base_harm_items and the night-7 adapter answers. Every count and every lost-item list matched, on every night.
- Its marks equal the stored marks and the builder's printed block, with no mismatch.
- score() (claude_dl9_experts.py:220-246) applies PASSMARKS' words as written.

Night 7 (lucky = right guesses out of 100 TEST puzzles x 20 samples; base L0 = 54; panel = 300 items, base right on 201):

| seed | mode | lucky | gain | panel lost | panel gained | panel right | on (of 400) |
|---|---|---|---|---|---|---|---|
| 16 | S always on | 231 | 177 | 20 | 55 | 236 | 400 |
| 16 | X switch | 231 | 177 | 0 | 0 | 201 | 100 |
| 16 | R random | 111 | 57 | 5 | 18 | 214 | 100 |
| 17 | S always on | 283 | 229 | 27 | 49 | 223 | 400 |
| 17 | X switch | 283 | 229 | 0 | 0 | 201 | 100 |
| 17 | R random | 133 | 79 | 8 | 9 | 202 | 100 |

The switch was on for 100 of 100 TEST puzzles and off for 300 of 300 panel items on both seeds. It was also off for 101 of 101 held-out base questions.

- **H1.** X lost 0 and 0, each at most 5. The sum 0 is at most 0.25 x 47 = 11.75. TRUE.
- **H2.** 177 ≥ 159.3 and 229 ≥ 206.1. TRUE.
- **H3.** On 100 and 100 (each ≥ 95); off 300 and 300 (each ≥ 285). TRUE.
- **H4.** X gain 406 ≥ 2 x 136 = 272, and X lost 0 ≤ R lost 13. TRUE.
- **INCONCLUSIVE?** No: L0 = 54 and the S lost sum = 47.
- **Proved wrong?** No: 0 is not above 10 or 13.5, and 177 and 229 are not below 141.6 and 183.2.

## What the recount adds (report-only, not marks)
1. **H2 passes by construction, not as a close call.** The switch was on for every TEST puzzle, so X's puzzle answers are S's answers. Likewise, X on the panel is exactly the base, because the switch was off for every panel item. Once the switch separates the two perfectly, the result follows. The real finding is that it separated them perfectly from night 2 on. The switch's training loss was 0.0 on nights 2-7 (3e-05 on night 1), so the two kinds are trivially separable.
2. **X also throws away S's panel gains.** Always-on S did not only forget; it gained items too:
   - Seed 16: 55 gained against 20 lost, so 236 right against the base's 201.
   - Seed 17: 49 gained against 27 lost, so 223 right.
   - Most of those gains were the number questions: bigger 44 of 55, and 39 of 49.
   - Most of the losses were capital-city questions: 17 of 20, and 22 of 27.

   X keeps the base's 201. So X meets "almost never worse", but it also blocks a helpful side effect of puzzle practice on number questions. That matters for Ben's transfer goal: a switch that is all-on or all-off per question cannot keep good spill and drop bad spill.
3. **Night 1 shows the look-alike weakness.** With only 150 day puzzles as positives, the switch turned on for 88 panel items on both seeds: bigger 86 and count 2.
   - That broke ADDENDUM-1's report-only expectation for night 1, which asked for 126 or more of the 139 number items to stay off. Only 51 stayed off.
   - Night 7 met it, with 139 of 139 off.
   - X gained 38 panel items on night 1 on both seeds and lost 0.
   - The same 88 on both seeds is plausible: the switch reads the same frozen base features, and the two seeds' adapters gave the same panel answer on 288 of 300 items.
4. **Rewording row (night 7).** GLM's four other puzzle wordings were never trained. The switch stayed on for 100 of 100 under each wording, on both seeds. Greedy solves out of 100:

   | wording | base | seed 16 adapter (= X) | seed 17 adapter (= X) |
   |---|---|---|---|
   | F1 | 2 | 7 | 12 |
   | F2 | 2 | 16 | 22 |
   | F3 | 4 | 21 | 22 |
   | F4 | 2 | 21 | 19 |

   So the switch does not block these rewordings, and the learning reaches them. All four are close paraphrases of one instruction, so this is not a test of very different wording.
5. **R is a fair control.** R's on count equalled X's on every night: 188 on night 1, then 100 on nights 2-7, out of the same 400. R lost 5 and 8, which is roughly a quarter of S's losses, as a random quarter should be.
6. **Hygiene.**
   - None of the 5 saved pool sample questions equals a panel question, and none contains a digit.
   - The full pool is not saved. The code's filter drops digits and every panel word (claude_dl3_replay.py:49-69; ADDENDUM-1 item 1), and all 300 panel items contain a panel word.
   - TEST puzzles are removed from the day puzzles (claude_dl9_experts.py:260-263).

## Builder's 7 deviations (RESULTS-gpu.md "Every deviation")
1. Ran under the disclosed lowered 3 GB disk gate, which follows Ben's 01:30:47 floor. C: had 4.4 GB free at start. This is the re-run of job 150, which stopped at 4.4 GB under the old 5 GB gate.
2. Launched through Windows Task Scheduler (task "dl9run" running C:\Users\benja\dl9\run_dl9.bat) instead of a shell-background start. The builder found that Win32-OpenSSH kills detached children when ssh ends.
3. Two earlier launch attempts, PIDs 16372 and 11360, died within a minute. They left no processes or files; the builder checked with tasklist.
4. The helper files (run_dl9.ps1, run_dl9.bat and the scheduled task) exist only on BensPC and were not pushed. A 22-byte mech-test.txt was deleted on BensPC before copy-back.
5. The time projection was made at 04:08 UTC from nights 1-3. The run finished whole inside the 4-hour cap, with no time-stop.
6. GPU-BUSY.txt already named this job, which the task allows. It was left for the watcher.
7. No code edited; selftest ok; sealed steps unchanged.

None of these touches the method or the numbers.

**Leftover to clear:** the scheduled task "dl9run" and C:\Users\benja\dl9\ (about 23 MB) are still on BensPC. They are finished and no longer needed. Removing them is the Director's or Ben's call; nothing gets deleted without Ben's words.

## Scope (what PASS does and does not show)
- **Shown:** on 2 seeds of one frozen 1B, keeping each night's number-puzzle learning in one LoRA expert did two things. A switch learned from where items came from turned that expert on only for puzzles, which removed all measured panel forgetting (0 of 300 lost vs 20 and 27 always-on). It also kept all of the puzzle learning (+177 and +229 over 54).
- **Not shown:**
  - Picking a skill among look-alike requests. Every positive shares one GLM instruction, and the negatives are short quiz questions. Night 1's 86 of 119 "bigger" items switched on is the warning sign. Sol's INPUT-AUDIT raises the same point.
  - More than one expert, or experts that must share. The switch is on/off for one expert, not a choice among several.
  - Grids or chat skills.
  - Keeping helpful spill: X drops S's panel gains (item 2).
  - Live serving. X and R reuse stored answers, a registered limit. A real switch costs one extra prompt pass through the frozen base per question (ADDENDUM-1 item 3: 1.18 s vs 0.76 s on CPU).
- **Ben's 11:34 ask:** he wants the model to decide the skill for each request itself. This switch does decide per request, from the question alone, with no task id. That is the right shape, but it is only shown for one expert and two kinds that look nothing alike.

## What it means for H-B in 0.2d
- ADDENDUM-12:14 fills H-B with "Fix sleep's first verified retention PASS under dl-3's marks". dl-9 is under its own marks, not dl-3's, so it does not fill H-B by itself. Retention across nights under dl-3's marks is not what dl-9 measured.
- A switch plus an expert is an architecture change (PASSMARKS:7; goals:96 "Only Ben approves architecture changes"). It joins 0.2d only with Ben's yes.
- Without his yes, H-B stays open. The Fix-sleep candidates stay dl-10 (replay + switch, PLAN.md, not sealed) and EWC. dl-8 stays held.

## Next, as I see it (not sealed; for the Thread manager)
The obvious next test is the one Ben asked for at 11:34: several experts with a learned router on look-alike requests. For example, number puzzles vs "bigger" number questions vs grid questions in GLM or Luna wording. It would test whether the switch still picks correctly when the kinds look alike, and whether spill that helps can be kept. That needs Ben's yes on the architecture first.
