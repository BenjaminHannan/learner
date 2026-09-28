# vread results: the thinker reading facts through a frozen 1B's vectors, against a LoRA reader (2026-09-28T00:36:40Z)

**Verdict: FAIL (narrowly; not proved wrong).** V1 holds easily. V2 misses by 1 turn. V3 misses on backref by 0.15
points. This is a practice-test result on Luna chats (dev = 1,444 turns, 211 dialogs), under the marks sealed in
PASSMARKS.md at fdee122c1 before any training. Nothing joins the build. A blind recount by a separate subagent, working
from PASSMARKS.md, bar.json and the four score files only, gets the same numbers and the same verdict.

## Marks (dev, each arm at its own bar: LoRA 0.995, vector 0.97)
| Mark | Vector reader | LoRA reader | Bar | Met? |
|---|---|---|---|---|
| Validity | - | 924 right saves | LoRA ≥ 615 (50% of 1,230 savable) | yes |
| V1 right saves | 1,098 of 1,230 | 924 of 1,230 | ≥ 0.95 × 924 = 877.8 | **yes** (+220) |
| V2 turns with a wrong save | 4 of 1,444 | 1 of 1,444 | ≤ 1 + 2 = 3 | **no** (over by 1) |
| V3 corrections | 103 of 173 (59.54%) | 77 of 173 (44.51%) | ≥ 39.51% | yes |
| V3 former, read as former | 82 of 86 (95.35%) | 55 of 86 (63.95%) | ≥ 58.95% | yes |
| V3 backref (history rule) | 81 of 136 (59.56%) | 88 of 136 (64.71%) | ≥ 59.71% | **no** (−0.15 points; 82 needed) |
| V3 look-alike rows with a save | 1 of 269 (0.37%) | 0 of 269 (0.00%) | ≤ 5.00% | yes |
| Proved wrong | 1,098 | 924 | < 739.2 | no |

Shares are exact ratios. PASSMARKS does not round, and whole-percent rounding would flip the backref line (60 vs 60),
so the recount flags it. Under the main rule both arms save 0 backref facts, as PASSMARKS says they must.
Score files: `scores/{lora,vector}_{main,hist}.json`. Verdict: `verdict.json`. Scorer:
`scripts/claude_vread_score.py`, unchanged since the seal.

## Report only
- **Same bar, both arms (shown, report-only files in scores/):**
  - at 0.995 (main rule): vector 948 right and 1 wrong turn; LoRA 924 and 1;
  - at 0.97 (main rule): LoRA 1,124 and 1; vector 1,098 and 4;
  - backref, history rule, post-hoc same-bar check: at 0.995, vector 63 and LoRA 88 of 136; at 0.97, vector 81 and
    LoRA 112 of 136.

  Suggested: on facts about people named in the turn, the two readers are close. The vector reader's lower own bar
  bought it more right saves, but also the extra wrong turns. On owners named only in earlier turns (backref) it is
  clearly behind at any bar. These same-bar numbers were computed after the sealed scoring and change no mark.
- **Where the vector reader's saves go wrong (shown, dev, bar 0.97):**
  - main rule, 4 wrong saves:
    - 2 facts saved to "me" that belong to a named person (the LoRA reader's only wrong save is one of these same two);
    - 1 correction saved as current;
    - 1 hearsay fact (someone_else) saved as current;
  - history rule, 5 more: every one has its owner pointer on the wrong earlier person (4 backref, 1 correct_ref).
- **Do the pointers land on the right words? (shown)**
  - Of the 1,312 vector cards at or above the bar, 1,302 have exactly the right words:
    - 0 values are wrong;
    - 8 owners are wrong;
    - 2 cards have no gold card with the same relation and state;
    - 1 card's text is not a whole-word span (this tag overlaps the others).
  - Every dev and calibration card's text equals the prompt text at its token pointers: 1,497 of 1,497 and 1,312 of
    1,312. So no card holds a word that was not in the chat.
  - LoRA, for comparison: 1,100 of 1,101 cards at its bar have the right words, with 1 owner wrong.
- **former_as_current:** 0 for both arms.
- **Look-alike saves:** vector 1 and LoRA 0 (of 269 rows).
- **Long turns (over 20 words, main rule):** vector 366 and LoRA 321 of 439 gold facts.
- **Under the history rule for everything:** vector 1,220 right with 9 wrong turns; LoRA 1,045 right with 1 wrong turn
  (of 1,422).
- **Thinking rounds (shown):** 1.0 on every dev and calibration turn. The learned stop said "done" after the first
  round every time: stop probability at least 0.88 on dev, median 0.999. So the loop never ran a second round at read
  time. This reader behaved as a 2-block reader, and this result says nothing about whether looping helps reading.
- **Time per turn (shown, the same RTX 4090, each arm reading dev alone, one turn at a time):**
  - vector: 17.7 ms median (p90 18.8), including the 1B's forward pass;
  - LoRA: 1,129.5 ms median (p90 1,561.5), with greedy JSON generation;
  - so the vector reader is about 64 times faster.
- **Trainable weights:**
  - vector: 9,281,982 (adapter 790,016; thinker 6,308,640; heads 2,183,326);
  - LoRA: 22,413,312 adapter weights;
  - both use the same frozen 1.1B MiniCPM5-1B at run time.
- **Choices made on the calibration slice (disclosed):**
  - 1B layer 12, the chosen one: right 1,192, extra 182, score 1,010;
  - layer 6: right 992, extra 359, score 633;
  - layer 18: right 1,062, extra 252, score 810;
  - layer 24: right 844, extra 443, score 401;
  - save bar 0.97: 961 saves on the slice, 3 wrong; at 0.95 it would be 6 of 982.
  - Committed at 2d3915187, before dev was scored.
- **Training:**
  - LoRA: 1,556 steps in 25.0 min on 12,447 rows; no trainable matrix without a gradient on the first step;
  - vector: 4,000 steps in 11.1 min on 11,217 rows. The last logged step shows the loss at 0.0027 and every training
    batch fully right.

## Checks before training (shown, on the rental and before that on CPU)
- Gradient check (fp32, no autocast, CUDA): 62 of 62 trainable tensors got a nonzero gradient, and 0 frozen 1B
  weights got one.
- Pointer check: 76 of 76 gold cards from 50 train rows were rebuilt exactly.
- Leak check: 0 dev dialogs in train or calibration.
- 15 of 15 packed files matched their sha256, and the unpacked row files matched DATA.md.
- MiniCPM5-1B model file sha256 7ab8fd86… is identical on the rental and locally.

## GPU, time and money
- **Machine:** one RTX 4090 on vast.ai (instance 53054936, machine 57839, $0.4007/hr), image
  pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime, torch 2.11.0+cu128, transformers 5.17.0, peft 0.21.0.
- **Timeline (UTC):**
  - created 23:06:36;
  - job started 23:08:38;
  - both arms trained side by side 23:09:33-23:46:13;
  - dev reads 23:46:13-00:16:31;
  - stopped 00:18:07;
  - destroyed 00:34:13, after the checked copy-back, and confirmed gone from the instance list.
- **Two earlier launches died in their first minute, before any work (logs in run/):**
  - 53054097: the image has no `xz` binary;
  - 53054638: the image's Python refuses a plain `pip install`.

  Both were destroyed at once and fixed in 86e4a1abd and 5b7bf0bc4.
- **Cost, from $/hr × time:** about $0.017 + $0.009 + $0.48 of running time, plus a few cents at most of storage
  while stopped. That is about $0.51 of the $4 cap. The account credit fell $1.07 over the same period, but other
  sessions' instances were running, so that figure is an upper bound. No other session's instance was touched.

## Deviations (all of them)
1. **Copy-back route.** The job sent its results as base64 lines of 4,000 characters in the container log, and the
   log service cut every line to 500 characters, so the block could not be decoded. Nothing had been read or scored.
   The instance was stopped, not destroyed. Every text result file was then read off its disk with vast's `execute`
   (`cat`, allowed on stopped instances).
   - 33 of 33 byte sizes equal `ls -l` on the instance (run/sizes_on_instance.json).
   - Ids are in sealed order: 1,444 / 1,444 / 1,230.
   - 1,444 of 1,444 LoRA frames equal the parse of their raw text.
   - Every vector card equals the prompt text at its pointers.
   - The one piece of the cut log that can still be decoded, the first 2 archive members, is byte-identical to the
     pulled files.
   - Not shown: a single sha256 over the whole result set. The archive's own sha256 could not be checked, because
     binary output does not pass through `cat`.
   - The vector checkpoint (37 MB binary) was not copied. Its sha256 is in run/out/weights_sha.log. The LoRA adapter
     was not copied either.
2. **Ordering on the machine.** The dev reads existed before bar.json was committed. They were first opened after it:
   bar at 2d3915187, then scores.
3. **Launches.** Three launches under the one job. The first two did no work.
4. **Numbers seen before scoring.** One summary line of the vector dev read (rows, median ms, mean rounds) appeared
   while checking which vast commands work. It holds no card or score.

## What it means (plain words)
The new reader, where the small thinking net reads the 1B's inner numbers and points at words, got more facts right
than the normal reader (1,098 against 924). It was much better at "used to" facts and corrections, and about 64 times
faster. But it made 4 bad saves where the normal reader made 1, and the marks allowed 3. It also lost track of who
"she" or "my boss" meant when that person was named in an earlier message: 81 against 88 of 136, with 82 needed.

At the same confidence bar, the two readers are about even on facts about people named in the current message. The
normal reader is clearly better at linking back to earlier messages. The thinking loop never went past its first
round, so this test did not use the "thinking" part at all.

**Limits:**
- one training seed per arm;
- a practice split of the same Luna chats, not a sealed panel;
- the vector reader trained on 1,230 fewer rows than the LoRA reader.

**Next step (Ben's call):** not a sealed test yet. First find out why owner pointers miss people named in earlier
turns: the 1B layer, the loop stopping at round 1, or too little backref practice. Test one fix on fresh Luna chats
(chunks 11 onward), because this dev split has now been used.

## Commits
- fdee122c1: data, code and marks sealed.
- 3836b9290, e5e02040e, 86e4a1abd, 4ce14659c, 5b7bf0bc4: rental mechanics and launch fixes.
- 2d3915187: run copied back, and the save bar from calibration.
- This commit: scores, verdict and RESULTS.
