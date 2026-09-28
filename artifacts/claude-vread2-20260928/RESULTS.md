# vread2 results: crediting any copy of the owner's name (vector reader, backref)

**Verdict: INCONCLUSIVE.** The validity mark failed: on the fresh chats, arm A did not repeat the dev pattern
strongly enough in either seed. Its low-confidence share for names seen 3+ times was 17.5 and 7.0 points above the
share for names seen once, and the mark needed 25.
- **Low confidence (M1):** met in both seeds. Arm B's low-confidence share for names seen 3+ times fell to 8.1% and
  12.1%, from arm A's 35.5% and 23.8%.
- **Right saves (M2):** met in seed 327 and missed by 1 card in seed 331.
- **Wrong turns (M3):** met in seed 327 and failed in seed 331 (41 against 36).

Practice test on fresh Luna chats (chunks 11-13: 6,483 rows, 538 backref cards). The marks were sealed in
PASSMARKS.md at f53ce4525 before any training. Nothing joins the build. A blind recount by a separate subagent is in
RECOUNT.md.

## Marks (B against A at the same seed; shares are exact ratios)
| Mark | Seed 327: A | Seed 327: B | Seed 331: A | Seed 331: B | Bar | Met? |
|---|---|---|---|---|---|---|
| Validity: backref cards | 538 | | | | ≥ 200, with ≥ 60 at 3+ copies (150) | yes |
| Validity: A's low share, 1 copy | 38 of 212 (17.92%) | | 36 of 214 (16.82%) | | | |
| Validity: A's low share, 3+ copies | 50 of 141 (35.46%) | | 34 of 143 (23.78%) | | A: 3+ ≥ 1 copy + 25 points | **no, both seeds** (+17.54, +6.95) |
| M1: B's low share, 1 copy | | 30 of 220 (13.64%) | | 33 of 219 (15.07%) | | |
| M1: B's low share, 3+ copies | | 11 of 136 (8.09%) | | 17 of 141 (12.06%) | B: 3+ ≤ 1 copy + 10 points | yes, both (−5.55, −3.01) |
| M2: backref right saves at 0.97, history rule | 378 | 432 | 411 | 437 | B ≥ A + 26.9 | 327 yes (+54); **331 no** (+26, 437.9 needed) |
| M3: wrong turns, whole fresh set, own bar | 32 | 33 | 36 | 41 | B ≤ A + 2 | 327 yes; **331 no** (+5) |
| M3: backref wrong saves at 0.97 | 7 | 5 | 11 | 7 | B ≤ A + 2 | yes, both |
| Proved wrong: B's 3+ low share within 10 points of A's | 35.46% | 8.09% | 23.78% | 12.06% | both seeds | no (−27.4, −11.7) |

- **Own save bars**, from the calibration slice by vread's unchanged rule (bar.json, committed at 0571aadb1 before
  the fresh reads were scored): A-s327 0.85, B-s327 0.90, A-s331 0.90, B-s331 0.85. vread's single checkpoint had
  0.97.
- **Low** means card confidence below 0.97, the lowest of its 7 probabilities.
- **Right-owner cards** are backref cards that point at the right person, at any confidence.

## What it means (shown vs suggested)
- **Shown:** crediting every copy of the name lowered the share of right-person backref cards that end up
  unsure:
  - names seen 3+ times: 50 of 141 → 11 of 136 (seed 327) and 34 of 143 → 17 of 141 (seed 331);
  - names seen once: 38 of 212 → 30 of 220 and 36 of 214 → 33 of 219.
- **Why this cannot count as the fix under the marks (shown):** on these fresh chats the old reader's split between
  names seen once and names seen 3+ times was much smaller than on dev (dev: 19 of 30 against 8 of 49, a 47-point
  gap), and almost gone in seed 331. So the test could not show the pattern it was built to fix. That is what the
  validity mark checks.
- **Suggested:** in seed 327 the old reader's gap was 17.5 points and the change closed it completely (to −5.5). This
  fits the diagnosis that splitting across copies caused part of the low confidence. It is one seed, and the mark was
  not met.
- **Right saves on backref at 0.97 (shown):** up by 54 and 26, out of 538 backref cards.
- **Wrong turns in seed 331 (shown):** 41 against 36. B-s331's bar came out lower than A-s331's (0.85 against
  0.90), which lets more cards through. Whether that, and not the change itself, explains the extra 5 is
  **untested**.
- **Proved wrong:** not hit. B's share for 3+ copies moved by more than 10 points in both seeds.

## Report only
- **Wrong person** (matched backref cards pointing at a different name):

  | | A-s327 | B-s327 | A-s331 | B-s331 |
  |---|---|---|---|---|
  | wrong person, all matched cards | 40 of 532 | 38 of 531 | 31 of 530 | 30 of 532 |
  | wrong person, rival named in the prompt | 35 of 135 | 28 of 135 | 29 of 134 | 21 of 135 |
  | the wrong name comes after the newest copy of the right name | 23 | 10 | 17 | 8 |

  Shown: the change did not fix picking the wrong person, which stays at roughly 30-40 cards in each checkpoint.
  Suggested: B picks the more recently named person less often. The marks do not test this.
- **Which of the 7 probabilities is lowest on low cards** (right-owner backref cards below 0.97):
  - owner start or end: A-s327 104 of 114, B-s327 46 of 61, A-s331 72 of 88, B-s331 41 of 62;
  - owner end alone: 72, 34, 49 and 30.

  So the owner pointer is the weak part, and the end more than the start. On all low cards in the fresh set, the
  "does this card exist" probability is lowest most often (231-326 per checkpoint).
- **Main-rule right saves, own bar, of 5,592 savable:** A-s327 5,248; B-s327 5,198; A-s331 5,162; B-s331 5,207.
  Wrong saves: 33, 36, 36 and 45. The bars differ.
- **Thinking rounds:** 1.0 on every read (all 4 checkpoints, calibration and fresh), as in vread.
- **Training:** 4,000 steps for each pair. The two seeds ran side by side on one GPU, 37.5 and 37.8 minutes. Last
  logged losses: A 0.0025 and 0.0042, B 0.0098 and 0.0056, with every training batch fully right.
- **Read time:** 26-27 ms median per turn, with two processes sharing the GPU. This is not comparable to vread's
  17.7 ms.

## Checks (shown)
- **On CPU before sealing:** arm A's weights after 3 steps were bit-identical to `claude_vread_model.py train`.
  B's loss equals A's when a name has one copy.
- **On the rental:**
  - gradient check: 62 of 62 tensors per arm get a gradient, and 0 frozen 1B weights do;
  - single-copy losses equal: 24.968784 for both arms;
  - pointer check: 76 of 76;
  - copy check: 6,594 named-owner train cards, 0 copies that fail to decode to the owner;
  - 17 of 17 packed files matched their sha256, and the 1B file sha256 7ab8fd86… matched.
- **Copy-back:**
  - all 4 checkpoints (37,144,933 bytes each) and results.tar.gz have the sha256 in the rental's manifest (run/);
  - each checkpoint loads into the reader (layer 12, 9,281,982 weights);
  - checkpoints are in run/ckpt/.

## GPU, time and money
- **Machine:** one RTX 4090 on vast.ai (instance 53087164, machine 51606, $0.4167/hr). Image
  pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime, torch 2.11.0+cu128, transformers 5.17.0.
- **Timeline (UTC):**
  - created 02:19:35;
  - checks passed by 02:22:06;
  - training and reads 02:22-03:07:34;
  - stopped 03:08:50;
  - copy-back until 04:33:50;
  - destroyed 04:33:58, confirmed gone from the instance list.
- **Cost:** about $0.34 of running time (49 minutes), plus a few cents of disk while stopped. That is well under the
  $4 cap. One launch; it did not fail.

## Deviations (all of them)
1. **Copy-back route.** The container cannot reach the rental's ports, and an inbound tunnel was refused by this
   session's safety check. Its draft script was deleted, never committed and never run. The route used was vast
   `execute` + `cat` of base64 parts on the stopped instance.
   - The first pull got an empty manifest (just after the stop).
   - The 8 MB parts came back cut to 2,033,903 bytes.
   - The second pull used the 1 MB parts, and every file checked.
2. **Rental script timing.** The rental script was committed after the marks (600760bc9), still before any
   training.
3. **Ordering on the machine.** The fresh reads existed on the machine before bar.json was committed. They were
   scored only after it.
4. **Arm A and vread's checkpoint.** A-s327 cannot be compared with vread's checkpoint, which came back empty. The
   identity with vread's code is shown on CPU only.

## Plain words
The fix (counting any copy of the person's name) made the reader much less unsure about people named several times.
But on these new chats the old reader was not as unsure as it was on the practice chats, so the test could not prove
that this was the problem. It also added a few bad saves in one of the two seeds, and fell 1 card short of the
right-save goal in that seed. Picking the wrong person is still there: about 30-40 cards each time, a bit fewer with
the fix.

## Commits
- f53ce4525: marks, fresh data and code, sealed.
- 69c67c64e: handoff note.
- 600760bc9: rental control.
- 0571aadb1: run copied back, and the bars.
- This commit: scores, verdict, RESULTS and RECOUNT.
