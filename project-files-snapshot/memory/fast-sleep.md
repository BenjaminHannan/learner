---
name: fast-sleep
description: Fast sleep 10-06/07: memory sleep 1/30 FLOPs; 10-07 research loop: compliant big sleep = C2 holdout 71.3% first try (6 parents, ~2,400 TF); PR #48
metadata:
  type: project
  modified: 2026-10-07T03:09:13.549Z
---

Thread "fast sleep" (root cmsg_01GSLCHTCnZxn7DhV19qcDvM2dQvJ3bS3Qb4uXN2qc2mnn, Ben 8:58 PM ET 10-06: "sleep must learn quickly without many FLOPs").
Screen done 11:08 PM ET 10-06 on the cloud CPU, DEV only, parents = job 6's N (s100, s101), rebuilt exactly.
- Memory sleep = knn v2 (top-16 cosine votes on op + slot ids) + 512 warm add/mult programmes: ~0.85x job 6 gain at 25-32x fewer FLOPs.
- Files: /mnt/project-files/fast-sleep/{PASS-MARKS.md, RESULTS-2026-10-06.md}; code creative/fastsleep.py; PR #48 (stacked on #44, branch claude/project-thread-2kevpk).
- CONFIRM (s200-s205) FAILED one mark (s205 harm 3.9, answer note); answer note OFF -> harm 0 on all six, 0.84x B. Parents in /mnt/project-files/fast-sleep/confirm/sXXX.
- FRESH HARM CHECK PASS 10-07 (C2b arm M = memory + 512 old, answer note OFF): harm -0.28..-0.41 on all 8 parents.

- RESEARCH 10-07 (Ben 9:34 AM ET "more research into fast sleep"; write-up /mnt/project-files/fast-sleep/RESEARCH-2026-10-07.md, repo creative/results/fastsleep/research/):
  - Answer note with agreement gate (ans=2): harm 0 on all 8, gain +0.98 vs +1.0 needed -> stays off.
  - Night chaining into the notebook: PROVED WRONG (+0.7; equal to blind search; affine 0% even with ~200 correct affine notes).
  - Fine-tune on W + search records, 2-parent pilot: sq_plus 0-2 -> 20-27%, +4 to +8 over B at equal cost; affine ~0; between marks.
- RESEARCH LOOP DONE 5:06 PM ET 10-07 (Vast 5090, ~$2.9 of $4 cap, box 54663402 destroyed). Compliant sleep (own night + own temperature, chain search, replay on the day's own inputs, batch-1024 fine-tune 80 visits): C2 holdout first try 71.3 +/- 2.5 on s200-s205 (71.1 72.5 73.8 69.5 67.2 73.4; s204/s205 run after the loop, outside the harness). a*x+b 15.5, x^2 98.7, x^2+k 76.6, x mod 10 93.1, 2(x+k) 72.5. Pooled-5 harm none (in_dist harm UNMEASURED, see [[sleep7d-screens]]). Non-compliant segment 1: 72.7 (2 seeds). Replay = most of the gain (-16 without). Top-up trades a*x+b for x mod 10. Report creative/results/fastsleep/research-loop-2026-10-07/, code creative/rl/; GPT prompt reviews/gpt-c2-affine-after-big-sleep-2026-10-07.md.
- 7d SCREENS (S1/S1b pass, S3/S3' fail, skills harm by family): see [[sleep7d-screens]].
**Why:** Ben wants a cheap sleep. Memory was the only candidate that passed the screen; its confirm failed one mark.
**How to apply:** don't re-run the confirm or the 10-07 tests; a notebook only replays (it can't adapt constants), so multi-step rules need weights or a new idea; C2b's arm M (answer note off) is the fresh gain test. Related: [[creative-roadmap]], [[whole-model-roadmap]].
