# V1 JOINT-DESIGN (draft for Opus review; nothing below is built yet)

Labels: **shown** = checked in code/files this session (path named); **suggested** = my proposal; **untested**.
Author: V1 assembly session. Spec: V1_SPEC.md (frozen). Per the coordinator's ruling, the join is NOT built until this is answered.

## 0. Two facts that change the spec's premise (read first)

1. **G1's evidence is not about PremonitionMini D (d128).** (shown) G1 = `--guard kfsoft/lock` + KL30: a K-FAC projection mask, 41 frozen tensors, and a KL-to-parent term on 32 replayed "diary" rows
   (`domain/far/FORGETTING-SOLVE-2026-10-16.md` item 2, branch claude/forgetting-round-g; code `mainbrain/kf*.py`, `mainbrain/fullrun.py` on claude/project-thread-trabt2). It runs on `custom_io` skills
   models loaded with `custom_io.models.load_model`. The parents it was measured on (T1SDR_s200..) are d_model 256, 3,314,132 params (shown: loaded `t1sdr/T1SDR_s200.pt` from claude/lt1-parent-checkpoints,
   token embedding 108x256). So spec line 10 ("brain stays d128, keeps ... the G1 evidence valid") does not hold for D: G1 on D would be a new, untested transfer. The 4-seed verdict is evidence for G1 on the d256 skills model, i.e. on the CREATIVE side's model family.
2. **C2b's sleep pipeline needs data this repo does not have.** (shown) `creative/c2b.py` takes `--skills-train train.jsonl --skills-data data_big` (skills replay in warm-up, every night and the harm check). Those come from
   `skills_curriculum.build --train 200000 --seed 1` (hash manifest FULL-BUILD-MANIFEST-200k-seed1.json). The forgetting doc says the package is on branch claude/project-thread-y0sxwe; it is not in main and I have not fetched it yet.
   The creative parent checkpoints exist (6 x 13.2 MB, claude/b2-confirm-checkpoints `custom_io/checkpoints/33-b2-confirm/B2_s200..s205`, sha256 files beside them).

## 1. Components (shown from code)
- D = `premonition.model.PremonitionMini`, d128, ~2.1M: READER (minGRU/attn) -> WRITER (cards) -> THINK (looped 2-layer block, 4 registers, rows = question, slots, cards, registers) -> DECODER. Trainer `premonition.train.MiniTrainer` (curriculum by FLOP share; I will drive it by step share).
- Creative = `custom_io` B2 (d256, ~3.3M), 9 answer registers, own 90-char vocab, own data (skills + creative/data/c2: warm 2048 add/mult, pool 1024 unlabelled puzzles of 5 held-out kinds, dev 256, sealed test 512).
- They share no vocab, tokenizer or data. Their only possible meeting point is hidden states.

## 2. Proposed join (suggested)
- P_dc: Linear(128 -> 256): D's final think state for the question (register 0, last loop) -> ONE extra memory row in B2's workspace input (next to the reader outputs X_t).
- P_cd: Linear(256 -> 128): mean of B2's 9 registers -> ONE extra row appended to D's think rows (own row-type id).
- **P_cd is zero-initialised**, so at step 0 the joint D equals plain D exactly; flag-off equals plain D bit for bit (to be tested on CPU). P_dc is default-initialised.
- Each side keeps its own tokenizer, batches and loss. A joint step = one D batch (village) and one B2 batch (puzzle/skills); the two forwards are connected only through P_dc/P_cd. Loss = L_D + L_B2 (+ G1 term).
- **Honest limit (suggested):** no v1 task needs information to cross the bridge, so W1 (village) and W2 (puzzles) can each be met by one side alone. The bridge is wired as the spec requires and checked live (nonzero gradient on both projections, P_cd nonzero after training, lesion = zero both projections at scoring). I will report the lesion result next to W1/W2 as a diagnostic, not a pass criterion.

## 3. Training plan (suggested)
- WAKE: joint steps; D on village train shards 0-379, B2 on warm/skills rows. Muon and S2 apply to FULL only.
- SLEEP (after wake, C2b recipe): B2 pipeline on creative/data/c2 (warm-up -> N' -> night records W, fresh AdamW, replay); projections trainable; village replay batches keep D in the loop.
- G1 in sleep: **choose A, B or both** (the KL term must be live and nonzero in Gate S either way):
  - **Option A (coordinator's proposal):** KL anchors D's logits on village dev rows to D's frozen pre-sleep logits. With D frozen and P_cd zero-init the KL is exactly 0 until P_cd or D moves; Gate S shows it nonzero after a few sleep updates. The K-FAC mask/freeze code does not exist for D (new, untested transfer).
  - **Option B (my recommendation):** G1 guards the CREATIVE module, where its 4-seed evidence lives: KL-to-parent on replayed skills/diary rows with the existing `mainbrain` code, plus Option A's D-side KL as a second cheap term. Needs `skills_curriculum` (fact 2).
- KL share of total loss is logged at every eval (consult item 3, abort rule A3).

## 4. Held-out sets (shown)
- W1: village `test` (sealed, 1,000 visits; hashes in V1_PARAMS once the build finishes). Dev: village train shards 380-399 (5%) + `validation` (held-out families/names/templates).
- W2: `creative/data/c2/test.jsonl` (512 rows, sha256 2bdadb18daf53f417792225d6eabd8160f6fe2039cf3fbcac64da040621953fa). Practised-with-labels kinds: add, mult only. The 5 test kinds (affine, square, sq_plus, last_digit, double_add) are disjoint from them, and there is zero prompt overlap with warm/pool/labelled/dev (computed). Caveat: the sleep pool holds the same 5 kinds UNLABELLED by design (C2b), so "held-out" means never taught with answers.

## 5. Questions for the coordinator / Opus
1. G1: option A, B, or both? 2. Fetch `skills_curriculum` from y0sxwe and rebuild the 200k skills set (hash-checked) for B2 replay, or run creative sleep without skills replay (a deviation from "exactly as C2b tested")? 3. Accept the bridge-is-inert caveat (section 2)? 4. Start B2 from the s200 parent checkpoint for both arms?
