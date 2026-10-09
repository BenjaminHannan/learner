---
name: two-doors-pointer-exit
description: two-doors (PR #30): pointer/all-words exit PASS (stand-in, real model); English 93% fresh with generated practice, beats 8-shot bare 1.2B (75%)
metadata:
  type: project
  modified: 2026-10-03T22:33:07.224Z
---

Thread "more information into the model" (cmsg_01GSLCHTCnZxn7DhV19qcDvMJakHkU8NWjvyPrMw1ab2WC), PR #30, branch claude/project-thread-ajo58u, code in reasoner_ptr/ (a reimplementation, not the PC pipeline).

- Diagnosis (shown in code): attention inside the core is fine. The two narrow doors are the reader (2048->32) and the exit (all positions averaged into 8 prefix vectors).
- F-E1 (free check): 74% of wrong fresh English pilot answers (269/362) are TRAIN answers, and all 22 right ones are too.
- Story task, 6 paired seeds: the pointer exit (core points at input words; the LM gets their own embeddings) took unseen answers from 0 to 51.1% (CI +45 to +57) and seen answers from 17 to 51%. A uniform-pointer lesion gives 0. Wider reader 32->256: +10.2 on two-hop (narrow PASS). On top of the pointer: +3.5 (in between). Learned pooling: 0 effect.
- Still about 51-55% overall, with train fit 68% (underfit) and weak new wording.
- REAL PIPELINE (23:45 UTC, reasoner_ptr/real/RESULTS-R2.md, PR #33 modules: ctx reader + 9M core + StatePrefix): 6 paired seeds, 384 fresh story Qs. pool unseen 0.0 / seen 16.8; ptr 56.7 / 57.9 (+56.7, CI +47.7..+65.7) PASS; uniform lesion 0. emb arm (append all prompt token embeddings, the PC fix as I read it) 87.2 / 89.6, +30.6 over ptr (read, not judged); zeroing core's 8 vectors -> ~0 in both (crude lesion; shuffled-core lesion untested). ptr weak on new wording (38 vs 77), underfit. Cost ~$0.68, credit $6.55 after.
- Ben 02:01 10-04 "I don't care" -> default exit = all-words + pointer (allptr).
- ENGLISH RERUN (03:45 UTC 10-04, reasoner_ptr/real/english/RESULTS-R3.md): train = pilot's 48 QA, fresh = our FRESH-EN-R3.json (48 passages, 192 Qs). allptr 34.7% vs pool 4.3% (+30.4, CI +12.7..+48.0) PASS; new-word answers 0 -> 33%. But train fit 100% both, seeds 21-68%, frozen LM alone 29.7% exact / 76% contains. Read: data (48 Qs) is now the limit. Next: allptr on many generated English rows of the 6 families. Cost ~$1.12; credit $5.19.
- vast lesson: execute (cat) works only on STOPPED instances. A job that waits with `pgrep -f script` matches its own bash args and hangs; wait on PIDs instead.

See [[director-role-and-rules]].

- ENGLISH R4 (RESULTS-R4.md): allptr + 8000 generated examples -> fresh 92.6% vs bare 8-shot 75.0% PASS. R5: 6 new kinds 79.9 vs bare 67.7 PASS; not practising a kind costs ~16 pts.
- ENGLISH R6 (16:14 UTC 10-04): 12 vs 6 practised kinds: 83.0 vs 81.1 (IN BETWEEN); second unseen set ties bare (78 vs 78); speech ~45%.
- ENGLISH R7 (21:25 UTC 10-04, RESULTS-R7.md; Ben asked why the talker re-reads the question): pooled 576 Qs: allptr 82.9; question-first + reused KV cache 75.2 (-7.6 FALSIFIED); core vectors only (pool+pointer, no words) 18.9 (FALSIFIED) -> talker NEEDS the words. Speed batch 1 (3090): all arms ~3.0x bare to first token, 1.3x for 8 tokens; reuse saves nothing -> overhead is core + one extra LM pass, not the re-read (inferred). Cost ~$2.30.
