# Review 2: adversarial check of five sealed pass-mark sets, before any score

Written 2026-09-28 21:43 UTC (`date -u`) by Director helper "review2". Read-only: no training, no GPU, no rental, no sealed file edited.
This box has no torch, so no net code was run; what I ran is plain Python over files already on main (recounts, generator mixes,
one small simulation). Explainer page for Ben: https://claude.ai/artifact/Lfx275bk2fWvBJc1xw69cv.
Serves finish-line items 3 and 4.

Labels: **shown** = I counted it from a file or the code and you can too; **suggested** = my reading, or a calculation resting on stated
assumptions; **untested** = nobody has run it. Counts are "x of N". Severity: **BLOCKS** = the verdict word can read as a win when nothing was won,
or the test cannot finish as sealed; **WEAKENS** = a verdict is possible but says less than its words claim; **NIT** = cheap.
File:line for PASSMARKS is the line in the file itself (not a `cat -n` of several files).

Tests and files reviewed (all under `artifacts/`, scripts under `scripts/`):
A = `claude-dir-a-breadth-20260928` + `claude_dir_a_{kinds,practice,bench,marks}.py`; HB = `claude-dir-hb-dates-20260928` + `claude_dir_hb_{kinds,run,marks}.py`;
R1g = `claude-dir-r1g-20260928` + `claude_dir_r1g_*.py`; R2g = `claude-dir-r2g-tied-20260928` + `claude_dir_r2g_*.py`;
H12 = `claude-dir-h12-stop-20260928` + `claude_dir_h12_{stop,marks,selftest}.py`. H12 is already on main (commit `ebad351db`, seal 16 of 16 OK), so the branch was not needed.

---------------------------------------------------------------------------------------------------------------

## 1. Short answer

| Test | Can it give a meaningful verdict as sealed? | Worst finding |
|---|---|---|
| A practice breadth | Only after two fixes; a PASS can be reached with a broken plain comparator | A1 BM2 counts even when the plain net failed its own gate; A2 the comparator has a different item stream |
| HB dates | The verdict words do not match what the marks measure | HB1 "REFUTED" words fire on a single panel; HB2 M1 is reachable without calendar arithmetic |
| R1g reach channel | Yes for "maze F_eq +10"; no for the word "general" or "the channel did it" | R1g1 the credit check cannot tell use from damage; R1g2 the closure is a reachability solver by function |
| R2g tied directions | Yes for the numbers; two wordings contradict | R2g1 PASSMARKS:39 calls "+8 in both seeds" a refutation while :33 calls it NOT PROMOTED; R2g2 two changes in one |
| H12 stop on mazes | The stop can be shown to fire, not to be informative | H12-1 a stop that has learned only the base rate passes STOP LEARNED |

Counts: BLOCKS 4 (A1, HB1, R2g1, H12-1), WEAKENS 15, NIT 10. Every BLOCKS item is fixable by an addendum committed before the first maze / dev score
(nothing has been scored for any of the five). Proposed addenda text is in section 8.

What is sound (shown): all five seals verify today (`sha256sum -c`: A 4 of 4, HB 4 of 4, R1g 8 of 8, H12 16 of 16; R2g has no check-file, only the 15 hashes inside `INDEX.md`, all of which match today, see X5).
Every baseline number I recounted matches the sealed pages (section 7). None of the five trains on Claude-written text: the items come from code and every checker
re-derives answers from tokens (A DESIGN:26, HB DESIGN:21; R1g, R2g, H12 change only nets or losses). The F_eq +10 bar of R1g and R2g is far above the run-to-run noise I can estimate (section 2).

---------------------------------------------------------------------------------------------------------------

## 2. Cross-cutting findings

### X1. WEAKENS: the noise under an F_eq bar is not one number, and the bars differ a lot in how far above it they sit
Shown, from the raw `eq-runs/*/holdout.json` (my recount, section 7): the two seeds of the same arm give F_eq 51.00 / 51.29 (loop), 33.79 / 33.58 (plain),
20.67 / 21.50 (fresh loop), 22.46 / 25.00 (fresh plain). So the four seed-to-seed F_eq differences are 0.29, 0.21, 0.83, 2.54 (RMS 1.4).
But the rung-by-rung differences of the **same** two loops are 0, 0, 25, -53, -6, 35, -27, 19 of 300 (RMS 28 counts = 9.4 points), and they cancel in the mean by luck:
the k = 64 rung alone is 137 vs 190. H12 PASSMARKS:48 uses the rung route and gets 3.3 points as the SD of a difference of two runs' F_eq; the four direct pairs give 1.4.
My reading (suggested): the true SD of "a new run's F_eq minus the baseline's" is somewhere between 1.4 and 3.3 points, and for F_few it is larger (loop 13.83 vs 16.17, but fresh loop 8.00 vs 16.92).
What that does to each bar (suggested): R1g/R2g +10 F_eq is 3 to 7 SD: safe. H12 +7.0 / +8.5: about 2 SD by its own estimate: fine as report-only. **A's BM1 +5.0 on F_eq and +5.0 on F_few is 1.5 to 3.6 SD**, and its "REFUTED below 2.0" line is inside the band (A3).
The four seed pairs and the two-seed rung estimate are all this box has; a same-recipe replicate (cheapest test, one extra loop-pre run per seed with a different item-stream base, about 170 min per run on the Mac) would settle it.

### X2. WEAKENS: the three-draw sleep gate passes a design identical to the loop only about two times in three (R1g, R2g; also H3, H12 report-only)
R1g PASSMARKS:40-42 and R2g PASSMARKS:29 use `max(6, 2 x SE)` with SE from 3 draws per side (`claude_dir_h3_report_add1.py:39-55`, sample variance with n - 1 = 2).
Simulation (suggested; normal noise, independent draws, the four cells k = 64 / 16,384 x sums / grids, per-draw SD sums / grids = 14 / 5, 10 / 4, 20 / 8, taken around H8 X1's spreads; no true difference): one seed passes all four cells 82%, 85%, 79% of the time; **both seeds 67%, 73%, 63%**.
So a design that really is as good as the loop is read as breaking a gate about a third of the time, and a real winner (+10 F_eq) is turned into NOT PROMOTED at the same rate. It is a false-negative, not a false-win, risk. It also makes REJECTED (the "gain made only by breaking a gate" clause) more likely than it should be.
Cheapest test: run the loop's own sleep six times from one checkpoint and read the spread before any design is scored. Fix in section 8 (R1g-3: more draws; pooling does not help).

### X3. BLOCKS for R2g, WEAKENS for R1g: "sleep gates not judged" is reachable by circumstance, and the skip is decided after dev scores are known
R2g PASSMARKS:29 lets the Director commit `SLEEPS-SKIPPED.txt`; queue-r2g-3 line 6 and line 25 stop if baseline `k64.pt`/`k16384.pt` are not found on the machine; queue-r2g-4 line 20 accepts the file. In R1g the holdout job writes `SLEEPS-SKIPPED.txt` itself if the loop checkpoints are absent (queue-r1g-3 lines 29-41).
Whether those checkpoints exist is unknown to me (untested; they are on a Mac I cannot see and are not in git). If they do not, the best both designs can read is "PASS (sleep gates not judged)" (`claude_dir_r1g_report.py:72-73`, `claude_dir_h3_report_add1.py:112-113`), and the row that is skipped is the one H8 X1 found noisiest.
The R2g route depends on a human choice made after job 2's dev table exists. Fix: decide it before any dev run (check the four checkpoint files at job 1 and commit the decision then).

### X4. WEAKENS: imported code is not inside the seals
R1g imports `claude_dir_h3_report_add1.py` and `claude_sparse_race.py` (`claude_dir_r1g_report.py:24-25`); R2g imports `claude_dir_h3_report_add1.py` (`claude_dir_r2g_report.py:22`); A imports `claude_dir_h1_marks.py`, `claude_dir_h1_bench.py`, `claude_dir_h1_kinds.py` (`claude_dir_a_marks.py:25`, `claude_dir_a_bench.py:37-39`) and the ruler.
None of these is in the A, R1g or R2g seal (H12 does seal the ruler files, `SEAL-code.sha256.txt`). `claude_dir_h3_report_add1.py` changed at 21:14 UTC today (commit `6c5f4441b`) and is the function that decides every R1g/R2g sleep gate and the verdict word.
Fix: add those files to each seal now (addenda text in section 8).

### X5. NIT: seal coverage is uneven and A's timestamps are ahead of its commit
A's seal lists only its four scripts (`SEAL-code.sha256.txt:1-4`), not `PASSMARKS.md` or `DESIGN.md`; R2g has no check-file at all (hashes sit in a table, `INDEX.md:7-21`, and the INDEX cannot hash itself).
A's files say written at 21:25 (PASSMARKS:3), 21:30 (DESIGN:3), 21:35 (queue line 1) while the commit that holds all of them is `d88f12437` at 21:24:36 UTC: the times were not read from `date -u` (rules.md). Harmless here (nothing has run), but it weakens the seal-before-score evidence.

### X6. NIT: the maze holdout is opened by many designs
R1g, R2g, A (maze arm), the patch race, the relation-net race and H3 all read the same 300 holdout 9x9 mazes. At +10 (3 SD or more) that is safe; at A's +5 with several looks it is less so (suggested). No fix needed for R1g/R2g; note it beside any A maze PASS.

---------------------------------------------------------------------------------------------------------------

## 3. Test A: practice breadth

**A1. BLOCKS: BM2 can be passed because the plain comparator is broken.**
`claude_dir_a_marks.py:81` computes BM2 as `Bloop - Bplain >= 5` and puts it in `main_pass` (:85). The plain net's own gate is only a **label**: V1a_plain false or V4 false gives "expressivity" (`gate()` :189-190, PASSMARKS:26, :29) and `score()` (:201-211) never looks at the label before the verdict.
Ten kinds include parity and bitop (DESIGN:35-39, risk 1 at DESIGN:60: "parity is famously slow"), so a plain 8-block net that fails 3 of 10 kinds is likely, and then a collapsed Bplain gives BM2 for free. In the published maze table plain is 33.79 / 33.58 and loop minus plain is 17.2 / 17.7, so BM2 is nearly implied by BM1 anyway (BM1 needs loop +5 over the two-kind loop): it adds real protection only when the plain net is healthy, and that is exactly when the label says so.
Fix: if the label is "expressivity" for a kind, BM2 is "n/a" and the kind cannot be PASS (word: NOT-SHOWN (no fair plain)). Cheapest check: the dev gate already records `plain_label` and `V4_breadth_plain_k16384_dev`.

**A2. WEAKENS: the comparator (Aloop) is a different net trained on a different item stream, possibly on a different machine.**
DESIGN:18 (`7000000+seed` vs `7100000+seed`), DESIGN:22 (the two-kind arms are not re-run), PASSMARKS:21 (paired panels and pools) and DESIGN:62 risk 3 (no bit-level determinism across machines). So "the mixture" is not the only change; a new source-net draw is another. The X1 noise is exactly the size of this effect.
Cheapest control (untested): one two-kind practice run per seed with the ten-kind stream base 7100000+seed (same code, only the stream), then read how far it moves from Aloop. About 45 min of practice per net; add its maze dev ladder only if the Director wants the full number.

**A3. WEAKENS: BM1's +5.0 and the "REFUTED below 2.0" line sit inside the noise band of X1.**
PASSMARKS:37 (BM1), :42 (REFUTED < 2.0), :52 (the reasoning: "largest swing 2.54", a 4-pair estimate). With SD 3.3 (H12's rung estimate), a true gain of +3 reads REFUTED in a seed 38% of the time, both seeds about 14%; with a true gain of 0 it is 73% per seed, 53% both. Two REFUTED kinds give PROVED-WRONG-HERE (`claude_dir_a_marks.py:121`). Luck-passing BM1 in both seeds at true 0 is about 0.5% (suggested), so a false PASS is unlikely; the risk is a false "did not help".
Fix: keep the +5 but move REFUTED to below 0.0 in both seeds (or 3.0), and say in the roll-up sentence that the noise was estimated (addendum A-2).

**A4. WEAKENS: V3 is judged on "any seed", the marks on "every seed".**
`claude_dir_a_marks.py:185` (`v3 = any(...)`), PASSMARKS:28 ("in at least one seed"). If only seed 0 has a usable ladder, the gate passes and the holdout is opened for both, and seed 1 (perhaps all zeros or at ceiling) is judged by BM1 to BM4 anyway. That can only make a non-win (NOT-SHOWN), not a win, but it opens the holdout for a kind that cannot answer. Fix: V3 in both seeds.

**A5. WEAKENS: BM4 is implied for maze; the plain-net gain from breadth is not marked.**
`claude_dir_a_marks.py:83`: BM4 (Bloop >= Floop + 5 and >= 20) is implied by BM1 when Aloop - Floop is 30.3 / 29.8 (maze recount, section 7); it can bite only on graph/rank if H1's practised loop is not above fresh. Meanwhile "did the plain net also gain from breadth" (`report_breadth_plain_minus_two_kind_plain`, :74) is report-only, though it decides whether the gain is specific to the loop. Ben's premise is a learned reasoner beating plain nets, so the roll-up should quote both gains side by side (addendum A-3).

**A6. WEAKENS: nearest neighbours to the exam kinds are inside the practice set, and the roll-up sentence does not carry the disclosure.**
DESIGN:50: `multi` counts equal digits (rank counts smaller ones), `compose` chains two lookups (graph-hop follows links). PASSMARKS:44-46 and the roll-up (`claude_dir_a_marks.py:119-120`) say "held-out kinds" with no caveat. A PASS on rank could come from `multi` alone (untested). The leave-out follow-up is listed but not marked. Fix: the sentence must add "nearest practised neighbour: multi / compose; leave-out untested" (addendum A-4).

**A7. NIT: hand-written parts.** Eight generators and checkers written by a Claude agent (DESIGN:26-41, :66). They are code-made token grids, and DESIGN:66 says the Claude-written-text rule does not apply; goals page line "sentence frames or templates that a Claude agent wrote for a code generator count as Claude-written" (16:45 UTC reading) is about sentence frames. It is a reading the Director should confirm once; I think it holds because the grids contain no words.
**A8. NIT: unsealed imports and the H1 dependency.** X4. `queue-a-breadth.md:157` (step 1) checks A's seal but not the H1 scripts it imports; it drops graph and rank at start if H1's 16 files are not all there, so files that arrive later are never used (conservative, fine).
**A9. NIT: PASSMARKS/DESIGN not in the seal; timestamps** (X5).

Queue job risks (`queue-a-breadth.md`, STATUS HELD): the marks say the practice for the eight new kinds was never run (learnability unknown, DESIGN:60), so job step 3 is the real first test and it stops on V1a false, which is the correct behaviour but can waste the 45-minute source. Step 5 puts 12 jobs on eight processes for up to 720 min (line 153) while other queue jobs (R1g, R2g, H12, the pile-up on the Director board) share the same Mac: the baseline's 169-minute figure was with eight at once on ten cores (H12 DESIGN:78), so anything else running pushes A over its cap and it stops by PID with no verdict (TIME-STOP). Step 4's timing pilot exists to catch this. `git archive origin/main` needs H1's graph/rank files already on main (line 157), otherwise A silently becomes maze-only, and then BREADTH-HELPS cannot be reached (DESIGN:63).

---------------------------------------------------------------------------------------------------------------

## 4. Test HB: fact combining (dates and multi-part)

**HB1. BLOCKS: the "REFUTED" words fire on one panel, and the second one on a mix of panels and seeds.**
`claude_dir_hb_marks.py:53` `cannot_combine = s1 < 60 or s2 < 60`, `:54` `no_better_than_plain = s1 <= plain s1 or s2 <= plain s2`, `:57-59` (both seeds, "any panel"). PASSMARKS:35, :60-61 word them as "in both seeds the loop is below 60 on s1 or on s2".
Consequences (shown by reading the code; the selftest at `:98-99` even asserts the mixed case): a loop that does multi-part at 200 of 300 and dates at 55 in both seeds gets **REFUTED-cannot-combine**, while PASSMARKS:62 says that result is to be reported as "the loop filters and counts but cannot do calendar arithmetic". Likewise a loop 200 above plain on s1 but one below plain on s2 gets REFUTED-no-better-than-plain, and seed 0 can fail on s1 while seed 1 fails on s2 and still count "in both seeds".
Fix: REFUTED words require the **same** panel to fail in both seeds, and dates-only failure gets its own word (addendum HB-1).

**HB2. WEAKENS: M1 (150 of 300) can be reached without general calendar arithmetic; per-op rates are report-only.**
Shown, from the generator (`claude_dir_hb_kinds.py:299-306` and a 200,000-item draw of `sample_ops`): s1 is uniform over DIFF, PLUS, DIFFT, FIRST (25% each; FIRST is a two-row choice, 50% by coin toss = about 37 of 300). So a net that solves FIRST and **one** of the three arithmetic ops reaches 150 exactly. On s2, 68.6% of items contain no arithmetic op at all (57.2% use only JOIN, SETM, COUNT, COUNTM), so s2 >= 150 needs no dates. The claim in PASSMARKS:8 ("answers date questions ...") is wider than what M1 requires. `parts_by_op` is reported (DESIGN:99) but does not gate.
Fix: a per-op floor on s1 (each date op at least 40 of 100 in both seeds) or word the PASS "answers about half of date questions" (addendum HB-2). Cheapest test: none needed; it is arithmetic on the sealed mix.

**HB3. WEAKENS: no chance-level baseline for answer formats.** V0 (PASSMARKS:21, "at most 45 of 300") covers three wrong-by-design predictors; none is a per-kind prior (most common count for COUNT, a coin for FIRST, "most recent date" for PLUS). Add one prior predictor per op and a required margin over it on s1 and s2 (addendum HB-3).

**HB4. WEAKENS: everything is in-distribution; no unseen combination is held out.** Practice (`sample_ops('train')`, kinds.py:312-320) and s1 to s3 draw ops iid from the same set; compound items are practised. So M1 measures "learned the practised ops", not "combines facts it was never shown combined". Only s3 changes store size (16-20 vs 6-12). Fix (untested, next test): hold out one op pair from practice.

**HB5. WEAKENS: same untuned learning rate for both arms; plain is size-matched, not compute-matched.**
`claude_dir_hb_run.py:310` lr 3e-4 for both; loop 2 shared d512 layers x up to 16 rounds of training, plain 8 layers d256 (about 6.3M each: 2 x 12 x 512^2 = 6.29M vs 8 x 12 x 256^2 = 6.29M, matches PASSMARKS:11). M2's +30 is easy against a plain net at an lr picked for neither. The ruler's own races tuned plain lr on source dev; here no tuning at all. Fix: a fair-comparator sentence in the PASS wording and, if a run fails M2 narrowly, no retune (addendum HB-4).

**HB6. WEAKENS: V1 for plain is 200 of 300, for loop 270.** PASSMARKS:22. A plain net that recalls at 66% is not a healthy twin; M2 against it is easy. Raise plain to 250 or make M2 conditional on plain recall >= 250 (HB-4).

**HB7. NIT: noise is imported from maze.** PASSMARKS:39 quotes "up to 2.5 points" from a different test; near 50%, a steep learning curve can swing more. Both seeds are required, which helps.
**HB8. NIT: hand-written parts.** Reader stand-in, op list, flag cells, answer columns, the mix of ops in practice (15% WHEN / 30% date / 20% multi / 35% compound, kinds.py:312-320): all disclosed (DESIGN:17-18, PASSMARKS:76).

Queue job (`handoff/queue/hb-dates-a.md`): STATUS line reads HELD-UNTIL with a condition (3) "Ben's yes", now moot under the 21:34 rule; the 10-hour cap rests on an estimate of 150 x the 200-step minutes (step 3) with four nets at 30,000 steps of up to 16 loop rounds, so TOO-SLOW is plausible; one GPU job at a time; the torch code has never run (`claude_dir_hb_run.py selftest` is the first run, step 3), so an early bug wastes the box. No retry path after a failed V1.

---------------------------------------------------------------------------------------------------------------

## 5. Test R1g: reach channel

**R1g1. WEAKENS: the credit check cannot tell "the net uses reach" from "switching 10 inputs off breaks the net".**
PASSMARKS:57-59, `claude_dir_r1g_report.py:29`, :91. The check zeroes ten features at inference on a net trained with them (`Net.REACH_OFF`) and a drop of 30 of 300 lets the PASS say "the reach channel passed". Any ten extra inputs that a zero-initialised mix layer has learned to add, even bias-like ones, produce a drop when removed. There is no control for "removing any ten features". Fix: also report the drop when the ten features are replaced by their dev-panel means, or shuffled across mazes; the sentence needs the shuffled drop >= 30 (addendum R1g-1). Cheapest test: the same dev run, two more inference passes (no training).

**R1g2. WEAKENS: "general" is argued from identifiers, but the channel is a reachability solver by function.**
DESIGN:20-26 and :33-40: 63-step transitive closure by five squarings of a learned link table over the items, T = 81 items, the loop's own row and column offsets. The self-test shows it is name-blind and renumbering-equivariant (:35-37), which is real, but a module whose only job is "what is reachable from what, in up to 63 steps" is the maze primitive whatever the names say; H11 called R1's vocabulary "a route-finder's" and this keeps the computation. The horizon 63 and T = 81 are hand-set and grid-sized (a 9x9 maze has 81 cells). PASSMARKS:65-71 already says a PASS is a maze result: good. Fix: the PASS sentence must say "maze only; kind-blind by construction, general only if the H1 ruler agrees" (R1g-2). Ben rejects maze-shaped designs (DESIGN:5): the Director should decide whether kind-blind-by-code is enough or the exam must include graph and rank before any generality wording.

**R1g3. WEAKENS: no same-size null control.** +8,472 weights and about +4% compute (DESIGN:40, :42). The comparison is loop vs loop plus channel; nothing separates the reach idea from "more capacity in the round", and the credit check is not that control (R1g1). Untested cheapest control: the same mix layer fed with ten fixed random projections of the state (a null channel), one dev ladder per seed.

**R1g4. WEAKENS: sleep-gate escape** X3 (PASSMARKS:40-42 "void" is undefined: who decides a draw file is void, and when). Fix: void = draw 0 differs from the harness's recorded sleep, judged by the script before R1g's numbers are read (addendum R1g-3).

**R1g5. NIT: rows 2a and 2b are implied by row 1** (loop minus plain 17.2 / 17.7 and loop minus fresh 30.3 / 29.8, section 7) so they cannot fail on their own. Harmless.
**R1g6. NIT: practice differs from the baseline in one more thing.** `claude_dir_r1g_practice.py` is a copy of the H3 v2 practice (checked by `diff`: only names and the mix-weight record differ) with the gamma / link / probe biases exempt from weight decay (DESIGN:16-17), which the baseline loop does not have. It is a part of the plug-in change, and DESIGN says so; I note it because PASSMARKS:11 says "nothing else differs from the loop" (:11).

Queue jobs (`queue-r1g-1/2/3`): all HELD; jobs 2 and 3 must run on the same machine as job 1 (they read `$HOME/premonition-r1g/.../source.pt`, queue-2 line 5, queue-3 line 5); an unattended crash between jobs strands the checkpoints. Time caps 330 / 330 / 240 min rest on "about 15 to 30 percent slower than the loop" measured at 2 threads for a smoke test (queue-1 line 5) and the baseline's 169-minute figure taken with eight jobs at once; with other tests queued on the same Mac these can be exceeded (untested). Job 3 writes `SLEEPS-SKIPPED.txt` itself when the loop's checkpoints are missing (lines 29-41) and then runs the holdout: X3.

---------------------------------------------------------------------------------------------------------------

## 6. Test R2g: tied directions

**R2g1. BLOCKS (wording): two sealed paragraphs disagree about what "proved wrong" means.**
PASSMARKS:39-40 "Rows 1 and 3 both fail in both seeds. That rejects 'sharing one distance table ... helps ...'" versus PASSMARKS:33-37 (`REJECTED` = F_eq no higher than the loop in both seeds, or a gain made only by breaking a gate) and :37 "above without reaching +10 is NOT PROMOTED". A run with F_eq +8 and F_few +3 in both seeds fails rows 1 and 3 in both seeds: line 39 says the idea is rejected, the verdict script (`claude_dir_h3_report_add1.py:112-116`) says NOT PROMOTED. R1g has no such paragraph (its :47-50 are consistent).
Fix: delete or restate line 39 as "reported as NOT PROMOTED; the idea is rejected only by the REJECTED rule" (addendum R2g-1).

**R2g2. WEAKENS: three changes, sold as one.** DESIGN:35-36 admits tie table + cross mask are "two halves"; PASSMARKS:11 calls it "the single change". The fixed 0.3 residual also changes the effective learning pace of the old tables (DESIGN:15-17). A PASS or a REJECTED cannot be pinned on symmetry. The table-only variant (`TiedBlock.CROSS = False`) is built and selftested but not run; cheapest test: run it on one seed's dev ladder (about 170 min) only if the full design fails.

**R2g3. WEAKENS: the swap-check credit line can be met by a net that is simply bad.**
PASSMARKS:43: gap = original minus transposed dev count at k = 1,024, "at most half the loop's" gives the symmetry wording. A net that scores low on both (say 40 and 35) has a tiny gap and no symmetry. Fix: the wording also needs R2g's original count >= the loop's original count minus 15 (R2g-2). The loop's k = 1,024 checkpoint is searched with `find $HOME ...` (queue-r2g-2 line 43) and may not exist: the sentence then reads "not checked".

**R2g4. WEAKENS: sleep-gate escape** X3 (PASSMARKS:29, queue-r2g-3 lines 6, 25; queue-r2g-4 lines 20-23). The skip is the Director's call **after** job 2's dev records exist.

**R2g5. NIT: "Also rejected at this budget: the source guard fails"** (PASSMARKS:36) turns a plumbing failure of a fixed hyperparameter (0.3) into REJECTED for the idea; DESIGN:30 (risk) says sums may need a faster residual. The report script has no source-guard input (`claude_dir_r2g_report.py:38-46`), so the word would be hand-written. Fix: word it "INVALID at 0.3", not REJECTED.
**R2g6. NIT: hand-set constants** (0.3 mix, distance table 0..4, cross mask at |d| > 1) and the symmetry prior are disclosed (DESIGN:15-24). A 1-axis text sequence has left/right meaning (causal order), so "one table for both signs" is a grid-shaped assumption that DESIGN:24 admits is not tested outside grids.
**R2g7. NIT: INDEX hashes.** Shown: all 15 hashes in `INDEX.md` match the files as they are today (my recompute); the INDEX just is not a check-file (X5).

Queue jobs (`queue-r2g-1..4`): chained on the same machine and on checkpoint files at `$HOME/premonition-r2g`; job 2 needs the loop's `k1024.pt` (line 43), job 3 the loop's `k64.pt`/`k16384.pt` (line 25) and both will fail or skip silently-ish if the baseline run folder is elsewhere (`find $HOME -maxdepth 6`); job 3 is 24 sleeps (line 5, an untested 255 s each). Job 4 holdouts wait on the Director's file (X3). All four HELD, cost $0 (CPU).

---------------------------------------------------------------------------------------------------------------

## 7. Test H12: stop training on mazes

**H12-1. BLOCKS (for the word STOP LEARNED): a stop that fires without being informative passes.**
Shown from the scorer: the ruler stops at the first round r >= 3 where `q[r] > 0.5` **and** the last three predictions agree (`claude_fewex_bench.py:76-78`). S1 (PASSMARKS:37-41; `claude_dir_h12_marks.py:44-53`) checks that the cap is not hit much, that mean rounds are below a line, and that `right >= 31`. S2 (:42; marks.py:56-57) checks `right >= fixed_right - 6` **inside the same net**.
A halt head that has learned only the base rate of "exact now" (most mazes at k >= 256 are solved, 256 to 292 of 300 in the baseline dev, section 7) outputs above 0.5 everywhere, and the rule reduces to "stop when the last three predictions agree". That passes S1 if predictions settle early, and passes S2 if the settled answer is as good as round 16. Nothing distinguishes it from a head that says "this maze is hard, keep going". Ben's aim (goals page, "decides its own thinking time") needs the second. The baseline has 300 of 300 cap hits at seven rungs, so either its halt is below 0.5 or its predictions never agree three rounds; the marks do not say which (untested).
Cheapest test, no new training: on the kept `k1024.pt` of each seed's dev run, compute (a) the read with the halt ignored (agreement rule only) and (b) the area under the curve of the halt probability against exact-now at round 16 across the 300 dev mazes. Fix: STOP LEARNED may be quoted only if (b) >= 0.8 in both seeds and (a) is worse than the learned read by the S1 margin; otherwise the word is "STOP FIRES (informative: untested)" (addendum H12-1).

**H12-2. WEAKENS: S2 is internal, so a stop loss that damages the body passes.**
S2 compares H12's learned read to H12's **own** fixed-16 read; the comparison with the baseline is the accuracy words, whose HURTS bar is -7.0 F_eq / -8.5 F_few in both seeds (PASSMARKS:48-53, marks.py:85-90) and the body reading is report-only. So a run at -6 F_eq and -8 F_few in both seeds is STOP LEARNED, "NOT SEPARABLE FROM NOISE", and recommendable (:60). Fix: recommend only if both accuracy words are not HURTS **and** the body delta is above -3.5 in both seeds (H12-2).

**H12-3. WEAKENS: the word WRONG overstates.** PASSMARKS:58 "This is the result that proves the idea wrong" and DESIGN:96 admits rounds 1-3, 6-8, 11-13, 16-18 and 21+ have no stop loss on mazes (DESIGN:51-53), so a failure may be the Learner's round schedule. Two seeds, one weight (0.5), one schedule. Fix: the word is WRONG-AT-THIS-RECIPE, and it only "proves wrong" the sentence "the maze stop loss with the baseline round schedule gives a maze stop".

**H12-4. NIT: V5 slack of 1 count across torch builds** (PASSMARKS:18; marks.py:140-145) and the Mac's torch build is untested (DESIGN:93): if the cold 9x9 count moves by 2 on a different build the whole two-job run (about 170 min each) reads INVALID-START. Cheaper: allow 3 and compare `source.pt` sha256 instead.
**H12-5. NIT: bars come from two seeds** (PASSMARKS:48 admits it). Fine as report-only.
**H12-6. NIT: S1 (a) floor 31 of 300 at k = 64 in seed 0/1 baseline is 126 / 173** so the rung counts; fine. The rungs 1 / 4 / 16 are excluded for the right reason (PASSMARKS:12).

Queue job (`handoff/queue/h12-stop-1-dev.md`): hard-codes the Mac path `/Users/ben-hannan/Desktop/projects/beautiful-model/...` for the qualified sources (line 1 of the script block, `SRC=`); the harness has no resume (a crash at hour 2.5 loses the run; the job says so and refuses a partial folder); both runs at once on one machine with whatever else is queued; time cap 300 min against a 169-minute baseline that was measured with eight at once (H12 DESIGN:78). The HELD-UNTIL text still lists conditions (a) that are now met (files are on main) and (d) "Mac not busy", which is not automatic. Seals are checked by the job (16 of 16), good.

### Recounts from raw files (shown)
1. Maze holdout, loop-pre, seed 0 counts 1, 0, 28, 137, 256, 271, 257, 274: sum 1,224, F_eq 51.00, F_few 13.83; seed 1: 1, 0, 3, 190, 262, 236, 284, 255: sum 1,231, F_eq 51.29, F_few 16.17. Matches R1g PASSMARKS:21-22 and R2g PASSMARKS:16-17.
2. Plain-pre holdout sums 811 / 806 (33.79 / 33.58); fresh loop 496 / 516 (20.67 / 21.50). Match A DESIGN:46 and R1g/R2g.
3. Dev, loop-pre, seed 0 at k = 64, 256, 1,024, 4,096, 16,384: right / fixed-16 / mean rounds / cap hits 126/122/48.0/300, 263/254/48.0/300, 275/272/48.0/300, 256/243/48.0/300, 286/285/29.4/143; seed 1: 173/171/43.8/265, 277/268/48.0/300, 233/220/19.9/61, 292/288/34.7/196, 261/259/35.3/194; dev F_eq 51.21 / 51.67 and F_few 12.42 / 14.75 (learned); these match H12 PASSMARKS:23-29 line for line. The seed-to-seed dev differences 2, 0, 17, -47, -14, 42, -36, 25 match H12 PASSMARKS:48.
4. Generator mixes (200,000 draws of `sample_ops`, HB): s1 PLUS 25.1%, DIFFT 25.0%, FIRST 25.0%, DIFF 24.9%; s2 all-non-arithmetic 68.6%; s3 49.6%.
5. Weights: loop 2 x 12 x 512^2 = 6.29M vs plain 8 x 12 x 256^2 = 6.29M (HB PASSMARKS:11); R1g stored 1,654,198 vs 1,645,726 = +0.515%.

---------------------------------------------------------------------------------------------------------------

## 8. Proposed addenda text (for the Director to commit before any dev/maze score; each is a NEW file named ADDENDUM-1.md in that test's folder)

Common preamble for each: "Written <date -u> before any run, dev score or holdout score of this test. These change the words a verdict may use and add read-only checks. They never change a number a seed was already judged by, and none can turn a REJECTED into a PASS."

### A ADDENDUM-1
- **A-1 (BM2).** BM2 is judged only when `plain_label` is "few-example" (V1a_plain and V4 true in the dev gate). If the label is "expressivity", BM2 is "n/a", and the kind verdict cannot be PASS; the best word is NOT-SHOWN (no fair plain comparison). In `claude_dir_a_marks.py` `main_pass` and `kind_verdict` must read the label.
- **A-2 (noise, REFUTED).** REFUTED needs gain below 0.0 in both seeds (not below 2.0). The roll-up sentence adds: "the run-to-run noise of one F_eq is estimated at 1.4 to 3.3 points; two source nets were not re-drawn". One extra control is welcome and is not a mark: the two-kind practice with the ten-kind stream base 7100000+seed, same code, reported next to Aloop.
- **A-3 (plain gain).** The roll-up sentence quotes "Bloop minus Aloop" and "Bplain minus Aplain" for each kind, both seeds, side by side.
- **A-4 (neighbours).** The roll-up sentence ends "nearest practised neighbours: multi (rank), compose (graph); leave-out untested".
- **A-5 (V3).** V3 must hold in **both** seeds (change `any` to `all` at `claude_dir_a_marks.py:185`; PASSMARKS:28).
- **A-6 (seal).** Add PASSMARKS.md, DESIGN.md, `claude_dir_h1_marks.py`, `claude_dir_h1_bench.py`, `claude_dir_h1_kinds.py` to `SEAL-code.sha256.txt` and have step 1 of the queue check them.

### HB ADDENDUM-1
- **HB-1 (words).** REFUTED-cannot-combine: the loop is below 60 of 300 on the **same** panel (s1, or s2) in both seeds **and** the other of the two is also below 150. If only s1 is below 60 in both seeds and s2 >= 150: the word is DATES-ONLY-FAIL (the loop filters and counts but cannot do calendar arithmetic). REFUTED-no-better-than-plain: the loop is at or below plain on the **same** panel in both seeds.
- **HB-2 (per-op floor).** M1 also requires, in both seeds, at least 40 of 100 right on each of the four date ops (DIFF, PLUS, DIFFT, FIRST) of s1, read from `parts_by_op`; otherwise the PASS is worded "answers some date questions".
- **HB-3 (chance floor).** V0 adds per-op prior predictors (most common answer per op from practice; a fixed coin for FIRST; the latest stored date for PLUS). M1 needs the loop 60 of 300 above the best of them on s1 and on s2 in both seeds.
- **HB-4 (comparator).** M2 is read only if plain has s0 >= 250 of 300 on dev (V1 plain raised from 200), and the PASS sentence says "same size, same untuned lr, not the same compute".
- **HB-5 (scope).** The PASS sentence adds "in-distribution: practised ops; no unseen op pair was held out".

### R1g ADDENDUM-1
- **R1g-1 (credit).** The credit check adds a second inference pass on the dev panel with the ten features replaced by their dev means (and a third with them shuffled across mazes). "The reach channel passed" needs the shuffled and the mean drop both at least 30 of 300 in both seeds.
- **R1g-2 (wording).** Any PASS sentence ends "maze only; the reach channel computes reachability by construction; generality is untested until the H1 kinds agree".
- **R1g-3 (sleep).** A draw file is void only if draw 0 differs from the harness's recorded sleep, judged by the script before any R1g holdout number is read. Use 5 draws per side instead of 3 (about 255 s each on one thread, so about 40 core-minutes more per branch and seed): my simulation (suggested, same assumptions as X2) lifts the chance that an identical design passes all four cells in both seeds from 67% to 78% (per-draw SD 14 / 5) and from 63% to 72% (SD 20 / 8), and 8 draws give 85% / 77%. Pooling the variance across the two sides changes nothing (82% either way per seed), and a floor of 10 instead of 6 gives 88% per seed with 3 draws. The rule itself keeps a floor of about 10% failure from four one-sided 2-SE cells.
- **R1g-4 (seal).** Add `claude_dir_h3_report_add1.py` and `claude_sparse_race.py` to `SEAL.sha256.txt`.

### R2g ADDENDUM-1
- **R2g-1.** PASSMARKS:39-40 is read as "Rows 1 and 3 both failing in both seeds is reported NOT PROMOTED; the idea is rejected only by the REJECTED rule (:33-35)".
- **R2g-2 (swap).** "The gain can be read as symmetry" also needs R2g's original dev count >= the loop's original count minus 15 in both seeds.
- **R2g-3 (sleep).** The Director decides now, before job 1, whether the loop's k64 / k1024 / k16384 checkpoints exist (a four-line `ls` on the Mac), and commits the result; a later skip is not allowed.
- **R2g-4 (source guard).** "Source guard fails" reads INVALID-AT-0.3, not REJECTED.
- **R2g-5 (wording).** The PASS sentence adds "tie table and cross mask changed together; table-only variant not run".
- **R2g-6 (seal).** A `SEAL.sha256.txt` in `sha256sum -c` format for PASSMARKS, DESIGN, the six scripts and `claude_dir_h3_report_add1.py`.

### H12 ADDENDUM-1
- **H12-1.** Before the word STOP LEARNED, on each seed's kept k = 1,024 checkpoint (dev, no training, no holdout): (a) the agreement-only read (halt ignored) and (b) the AUC of the halt probability at round 16 against exact-now over the 300 dev mazes. STOP LEARNED needs AUC >= 0.8 in both seeds and the agreement-only read worse than the learned read by at least 6 of 300 on one judged rung or more mean rounds; otherwise the word is STOP FIRES (informative: not shown).
- **H12-2.** Recommending the loss for the maze recipe needs both accuracy words not HURTS and the body delta (fixed-16 F_eq) above -3.5 in both seeds.
- **H12-3.** The word WRONG is renamed WRONG-AT-THIS-RECIPE and its meaning is limited to "the maze stop loss with the baseline round schedule (rounds 4, 5, 9, 10, 14, 15, 19, 20) and weight 0.5".
- **H12-4.** V5 tolerance is 3 of 300 and 3 of 200, or equal `source.pt` sha256 (the Mac job already prints it).

---------------------------------------------------------------------------------------------------------------

## 9. What I could not test

No torch here: none of the net code ran; every statement about what a net does is **suggested** or **untested**. I did not read the R1g/R2g/A plug-in code line by line for bugs (only the marks, report and queue code, and the parts named). The sleep-gate simulation and the noise ranges use assumptions written beside them. I did not open any blind panel or readpanel320.

## 10. One question for Ben (through the Director), recommendation marked
Should R1g and R2g keep their maze-only ruler for a first read, or should a graph or rank exam be added first?
(a) Keep maze-only now, add a "generality untested" sentence to any PASS (recommended: no new compute, honest wording);
(b) hold both until H1's graph and rank ladders exist.
