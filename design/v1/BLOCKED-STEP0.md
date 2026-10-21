# V1 assembly: Step 0 BLOCKED (2026-10-21)

Stopped before writing V1_PARAMS.md, per the instruction "if any fact is genuinely missing, stop and tell the coordinator". Nothing trained, $0 spent, spec untouched (sha256 a2abfe31... verified).

## Missing facts (checked in the repo + 20 remote branches)
1. **No main-task (village) sealed file, dev file or training shards exist.** `data/village/` holds only pattern banks. Village text comes from `learnlab.village.shards.write_shards` ("large-seed0-..." builds, splits train/validation/test); no build, no sealed path, no hash is committed. The only sealed file with a hash I could find is the creative one: `creative/data/c2/test.jsonl` on `claude/project-thread-2zeaoc` (512 rows, sha256 2bdadb18daf53f417792225d6eabd8160f6fe2039cf3fbcac64da040621953fa; dev.jsonl is 256 rows). W1 (sealed main-task accuracy, village) therefore has no file to be measured on.
2. **The components live in different codebases/branches and have never been combined:**
   - Main brain D (PremonitionMini): `premonition/` (this branch, main).
   - Muon: `premonition/muon.py` on `claude/steals-8`.
   - G1 (forgetting guard, E0-READY a1adcb196): `claude/forgetting-round-g`.
   - S2 unwashed copy: only a toy (d=32, `decoder_raw_cards`) on `claude/info-constraint-solutions`; I found no implementation in PremonitionMini itself.
   - Defer: port on `claude/launch-bound-solve` (parked, 25 tests).
   - Creative/sleep (C2b, B2): `creative/` on `claude/project-thread-2zeaoc`, built on `custom_io` B2 (arithmetic puzzle kinds, 90-id char vocab, its own data). It is a different model and data domain from the village D. No code exists for "one linear projection each way" between D (d128) and B2 (d256); that is new design, not wiring.
3. **Sleep + G1 on the creative side:** G1 is a guard on D's forgetting; the spec says to run it with sleep, but there is no existing definition of which model's logits the KL term anchors in the joint model.
4. Environment: this cloud box has no torch and no GPU (CPU wheel is downloadable, 4 CPUs).

## Decisions needed from the coordinator (one answer each)
- A. Where do the village train/dev/sealed builds come from (generate with a stated seed and sha, or exists on Ben's PC)? Which test split is "sealed"?
- B. Is "creative joins D via two linear projections" meant literally (new joint model, trained on village + puzzle data together), and which model does G1's KL anchor to?
- C. Is S2 meant to be newly implemented in PremonitionMini (never done outside the toy)?
- D. Approve a larger scope: this is a multi-branch integration (about 6 branches, 2 codebases), not an assembly of ready parts. I can start by consolidating the branches onto claude/v1-assembly and building the infrastructure items (memory guard, Dockerfile, tarball+COMMIT, checkpoint/resume, preflight) which do not depend on A-C.
