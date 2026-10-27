# Brain-1: judge against an explicit list of the job's relations ("executive check")

Fixed 2026-10-27 ~09:00Z, before any Brain-1 test is written. Ben (07:48Z): "make it emulate creativity from the
human brain". Literature sweep: /mnt/project-files/creative/brain/ (2 rounds, ~800 distinct papers, ranked synthesis).
Brain idea (suggested): creative work alternates loose generation (default-mode network) with evaluation by the
executive network; rostrolateral prefrontal cortex is argued to bind several relations at once when judging, rather
than relying on a felt "this seems right" (Ellamil 2012; Beaty 2018; Christoff 2001; Bunge 2005; the aha feeling can be
induced falsely, Laukkonen 2020). Our data agree that evaluation, not generation, is the bottleneck: K2 already makes
~8 different plans in 12 tries (shown, Guess-1 IND), and the picker decides the outcome (Pick-1/2, Probe-1/2).

## One change
The Probe-2 test writer (sees the request and the start state) first writes a short list: every person, file, date,
time and amount the request names or implies with the exact matching items in the data, saying if more than one or
none match; which actions could not be undone; what must stay unchanged. Then it writes the checks from that list
(switch `PROBE_CHECKLIST=1` in creative/probe1/write_probes.py; text in CHECKLIST_TEXT). The list never says what the
right answer is (no "ask first" hint). Because the reply is longer, the token cap is 1,536 (Probe-2: 768).
Everything else as in Probe-2/Probe-3: same 192 pools of 12 Guess-1 tries, replay, 4 samples at T0.7 / top_p 0.95,
scoring, pickers and tie-breaks (PROBE-S primary).

## Arms (all K2-Horizon-3.7B bf16 on MLX, untuned, same M3 run as Probe-3's MLX-BASE control)
- BASE = Probe-3's MLX-BASE arm (Probe-2 prompt). CHECK = the same with the checklist.
- Haiku (Batches, default sampling) with the checklist: reference only, compared with Probe-2's Haiku 44.3%.

## Pass marks (fixed now)
- P1: CHECK PROBE-S pick rate >= BASE + 4 points (on 192 pools; effective n ~48 tasks).
- P2: reference agreement of CHECK's valid tests >= BASE's + 8 points (the mechanism: better-bound tests).
PASS = P1 and P2. PROVED WRONG: CHECK <= BASE + 1 point. Otherwise INCONCLUSIVE.

## Diagnostics
Validity rate, tests per sample, share of trap tasks (confirm_irreversible, clarify) where some valid test is a
"did not act" check, all-tie rate, and how often the list says "more than one matches".

## If it passes
The checklist becomes the default test-writer prompt, and Probe-3's tuned writer is retrained on Haiku's checklist
tests. If it fails, the bottleneck is the writer's skill, not its procedure.

## Cost
192 K2 generations on the M3 (~30-60 min, after Probe-3); Haiku batch ~$0.05.
