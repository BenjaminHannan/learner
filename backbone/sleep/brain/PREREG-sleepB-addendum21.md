# Sleep-B addendum 21: addendum 19's arm runs again with a 16 h budget (written 2026-10-29 ~15:15Z, before the rerun)

Labels: shown / suggested / untested. A compute change only: no arm, flag or mark changes. Not the village model, not the card
experiments.

## What happened (shown, Ben's PC, `results_pc/run4`, chain `pc/sleepb_pc12.sh`)
- **Pre-check (Week-1, one night, generation only): RUN.** The fixed writer carded 22 of 27 reachable two-hop tests forward (addendum
  18's bar, reported only, is 24) and kept 105 chains; today's writer carded 19 and kept 72. No `</think>` in any reply row; the two
  hits in probe.json are the template's own `<think></think>` prompt tails.
- **The arm (l3_g570_w, gen-bs 24, PyTorch capped at 8.5 GiB because Ben's desktop apps hold ~6.7 GB of the card) stopped at its 10 h
  budget after night 5, so it has no result.**

| night | wall s | train steps at 200 / 400 / 800 (s) | cuda peak GiB | 570-question gate | undone |
|---|---|---|---|---|---|
| base | | | | 0.693 | |
| 1 | 768 | | 5.2 | 0.816 | no |
| 2 | 3389 | 248 / 634 / 1331 | 5.2 | 0.828 | no |
| 3 | 3491 | 248 / 679 / 1403 | 5.4 | 0.853 | no |
| 4 | 4434 | 262 / 842 / 1614 | 5.4 | 0.840 | no |
| 5 | 7984 | 579 / 1678 / 3331 | 5.4 | 0.844 | yes: consolidated recall 0.845 < 1.000 - 0.10 |

  - Night 5 is about 2x slower than night 4 in every part of the night at the same memory use. The REM pool grows night to night, but
    that would slow mostly the REM parts. **Suggested:** something else used the PC's GPU or CPU during night 5. **Untested.**
  - Forward recall after night 4 (curve): C2 17%, C4 55%.
  - ARC-Easy rose from 69.3 (base, 570 validation questions) to 81.6 after night 1. **Suggested:** the base LFM3 loses points to its
    answer format, and one night of short-answer cards fixes that. ARC-Easy 500 before sleep: 71.4.
- For comparison: K2 on this card took 826 and 5265 s for nights 1 and 2, so LFM3 nights 1-2 took 0.93x and 0.64x as long.

## The change
- **add19b:** addendum 19's arm l3_g570_w, with exactly addendum 19's command, runs again from the start (no saved state, seed 1). Its
  budget is 16 h, not 10 h. The projector (after night >= 2, end = now + (7 - n) x night x 1.25 + 4500 s) and the 90-minute silence
  watchdog are unchanged.
  - **Suggested:** at night 5's pace, the week needs about 12.5 h.
  - If it runs out of memory at gen-bs 24, it reruns at 16, as in addendum 19.
- add19b's result is addendum 19's result for all of addendum 19's marks (G, P1, P2, no harm). It also sets addendum 20's base, under
  addendum 20's own rule, so R8 and V8 get addendum 19's flags only if add19b passes no harm and P1.
- **Report only:** `pull4/gpuwatch.txt` logs GPU memory, utilization, temperature, clock and the WSL load average every 10 min while each
  job runs.
- If add19b also stops at its budget, two-step on LFM3 stays untested on this card. A faster writer is then the next addendum, decided at
  that point.

## Compute and PC order
- add19b takes the slot R8 had (flag `think2-p1/SEG3-DONE`) and writes `GO-LOOP-P2B` when done.
- R8 takes the slot V8 had (`handoff/GO-SLEEP-V8`) and writes `GO-AFTER-V8` when done (Notebook-2 starts then, as before).
- V8 waits for a new flag, `handoff/GO-SLEEP-V8B`, which the coordinator places in the PC queue, and writes `GO-AFTER-V8B`.
- Chain script `pc/sleepb_pc13.sh`. It replaces pc12 while pc12 waits for SEG3-DONE. Its mock runs through all three jobs and their flags.
