# Probe P0: can B2 find answers by trying many times? (2026-10-06, CPU, no training)

Creative roadmap thread. Spec written before any sampled candidate (`PROBE-SPEC.md`). Scored with the answer key
("known-answer"), so this is not a key-free checker.

- Model: B2 from `origin/claude/custom-reader-talker-4x309r` @ 883663c55a (`custom_io/models/ledger.py`, copy=True),
  checkpoints `/mnt/project-files/custom-io/checkpoints/29-b2-screen/B2_s100` and `B2_s101`.
- Data: `skills_curriculum` build `--train 200000 --dev-per-cell 40 --seed 1` (manifest equal to
  FULL-BUILD-MANIFEST-200k-seed1.json; `data_build.log`).
- Run from a worktree of that commit: `python p0_probe.py --ckpt <ckpt> --data <build dir> --out p0_B2_sXXX.json`, then
  `analyze_p0.py` (tables) and `supp_p0.py` (post-hoc table). Sanity: sampling at T=1e-4 matched greedy on 928 of 928
  rows (`sanity_lowT.txt`). Greedy scores reproduce RESULT.json exactly.
- Raw candidates: `p0_B2_s100.json.gz`, `p0_B2_s101.json.gz`.

## Result (shown)
- Held-out task families (clock_date, op_define, string_transform, unit_convert; 160 rows): greedy 0.6% / 1.2%;
  best pass@32 1.9% (s100, cold start by the fixed lines) and 5.6% (s101, weak signal). All but one hit are in
  unit_convert. clock_date, op_define and string_transform: 0 hits in 32 tries on both seeds, apart from one op_define
  row on s100.
- Variety is narrow: 2.1 to 4.5 distinct effective programs per held-out question out of 32 tries (`p0_supp_posthoc.md`).
- Rows B2 gets wrong on new sentence frames and new words: pass@32 rescue 4.8% to 25.0%, which crosses the fixed
  "signal" line, but a post-hoc check (not pre-registered) shows guessing a random prompt word 32 times scores 15.5% to
  25.0% on the same rows. Most rescues come from re-guessing the word pointer, not from different programs.
- Reading (suggested): sampling B2's heads is free and reaches the calculator, but it gives few distinct programs and
  no hits on new kinds whose answers the program language cannot express (dates, string edits).
