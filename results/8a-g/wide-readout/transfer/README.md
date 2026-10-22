# WIDE (10MW, B2, seed 400) files for the CPU miss-comparison test on the Mac

Temporary transfer copy, so the Mac can score WIDE on the PC's dev files. Source: Modal volume learner-wide-10mw, copied to
/mnt/project-files/whole-model-roadmap/wide-modal/8aWIDE-10MW-s400/B2-full/ on 2026-10-13.

| file | bytes | sha256 |
|---|---|---|
| wide-B2-checkpoint.pt | 40729082 | c6557e6b50cd79a4c22309d1eedd69013d87dfa76f5fd4d334f96dbfc01aa343 |
| wide-B2-RESULT.json | 206081 | 57876cc68310f25bc897867a065275bb5568d3f48c8c793f240637e2c2f85c0b |

The checkpoint holds only the 10,173,509 trained weights (the frozen EmbeddingGemma is not in it); name `ledger`, cfg d 448, 2 blocks, 7 heads, 12 loops, eg_embed true; its 95 characters equal the pool's charvocab.json.
