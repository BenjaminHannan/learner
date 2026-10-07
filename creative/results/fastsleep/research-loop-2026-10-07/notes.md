# Research notes

Full literature passes (with per-source labels, verified arXiv ids, FT = full text read / abs = abstract only):
- /mnt/project-files/papers/fast-sleep-papers.md (memory, composition, gating, consolidation, verification; 10-07)
- /mnt/project-files/papers/research-loop-c2/angle-2-augmentation-constants.md (execution replay, dreaming, constants; 10-07)
- /mnt/project-files/papers/research-loop-c2/angle-1-self-training.md (expert iteration / self-training; pending)

Sources that drive the cards (read by the subagents in full text unless marked):
- Shin et al. 2019, arXiv 1912.12345: same programs with fresh I/O lifted narrow-test accuracy 0.04-24.30% -> 62.78-80.19%; narrow input ranges overfit. -> H1.
- Butt et al. 2024, CodeIt, arXiv 2402.04858: hindsight relabelling 49/400 vs 24/400; mutation 49 vs 17; priority replay 49 vs 38. -> H8, H12.
- Pourcel et al. 2025, SOAR, arXiv 2507.14172: at most 50 relabelled programs per task; best+worst mix best. -> dose for H1.
- Akyurek et al. 2024, arXiv 2411.07279: leave-one-out tasks from the shown pairs. -> H4.
- Gauthier and Urban 2022, arXiv 2202.11908: shortest program per target ~10% more solutions than a random one; constants from 0/1/2. -> H2.
- Bunel et al. 2018, arXiv 1805.04276: program aliasing hurts top-1. -> H2.
- DreamCoder, arXiv 2006.08381: replays + fantasies; early dreams of little value. -> H8, H11.
- Chen et al. 2019 (ICLR) execution-guided synthesis 71.91 -> 85.08; ExeDec arXiv 2307.13883 +5-7. -> out of scope here (needs an architecture change in locked code).
- Haluptzok 2023, arXiv 2207.14502: second self-training round helped little. -> H6 expectation.
- Nye 2020, arXiv 2003.05562 and SketchAdapt arXiv 1902.06349: no-search synthesis weak on unseen parts; 70% greedy is a stretch.

Local evidence (this project, DEV):
- job6 fine-tune on W: 36-39%; affine 0-2, sq_plus 0-10, double_add 0-16; square/last_digit 90-98.
- Same fine-tune on W + chain records (same updates): 43.8 / 43.4 on 2 parents; sq_plus 20-27%.
- Offline chain search over the parent's own notes finds a fitting program for 100% of pool questions the night missed; on DEV its pick was 100% right.
- Memory sleep cannot generalise across constants (affine 0% with ~200 notes).
