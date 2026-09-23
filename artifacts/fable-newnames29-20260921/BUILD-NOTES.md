# Experiment 29 / M1-F10 — build notes (Fable, coordinator, 21 Sep 2026)

Script: scripts/fable_newnames29.py — a thin wrapper over experiment 27's script (written by GPT xhigh,
one coordinator fix). Run scripts derived from 27's by sed (paths, seeds 2106–2108, wave 2 = L + F6).

Disclosures, all made before any registered training run:
1. PASS-WITH-GAP tier STRUCK (coordinator ruling, FABLE-PREDICTIONS.md). Kept only as the descriptive label
   `cutoffs_met_paired_missed`. Verdict rule is 27's: ten cutoffs + paired mark >= -13, 3/3 seeds.
2. No p16-2 cell was built; the ten cells are 27's.
3. Per-question records hold indices only (no correct/wrong field). final.pt is kept, so they can be recomputed.
4. The report header and the panel suite filename still say "27" (inherited). Contents are experiment 29's:
   namespace newnames29-operator-v1-20260921, seed base 202609212900, registered true.
5. No tests file. Stand-ins, run by the coordinator: LR schedule check (F == F6 for the first 4,000 updates by
   construction, glide ends 1.0045e-4), fixture end-to-end for all four arms, override refusal on registered
   seeds (nothing left on disk, 27's globals restored), doctored-run integrity probe.
6. Coordinator fix after the probe: run_integrity compared the float32 name scale (1.2000000476837158) to 1.2
   exactly, which would have marked every real F/F6 run INVALID. Now a 1e-6 tolerance. Nothing else changed.
7. Because that fix changed the source fingerprint (afd44272… -> 2a046e54…), the data wave was re-run. The ten
   panel .pt files are byte-identical; only provenance fields differ. First run kept in data-wave-pre-fix/.
8. Independent GPT audit not obtained: the bridge failed three times (shell died, max turns, 502 on a 65 KB
   prompt). Coordinator self-check of the verdict logic stands in for it. Ben informed.
