# PASSMARKS — Rung 2 of `design/v3/30-modes/47-ears-rung2-open-encoder-spec.md`

Written and hashed **before any registered training run**. Everything below is fixed in
advance. Nothing on a test panel may guide any choice; only DEV and CAL may.

Date: 2026-09-21 · artifacts dir: `artifacts/fable-ears47-20260921/`
Arm under test: **C** (SciBERT borrowed encoder + our frame head). Rung-1 tape/BiGRU numbers
in RESULTS.md are copied from `artifacts/fable-ears45-20260921/RESULTS.md` and are **not**
re-run.

---

## 1. The marks (copied from doc 47 §6; gated = SAFE, NEG, SEEN, NEW, NAMES, ASK, WEB, NEWREL)

Definitions: **correct** = decoded frame equals gold frame on (act, relation, subject span,
object span, direction); for abstain golds (UNSURE / NO_FACT), correct = verdict REPHRASE
and the majority (≥ 2/3) raw act equals the gold act. **Silent wrong write** = verdict
EXECUTE and act ∈ {STATE, RETRACT} and frame ≠ gold (or gold unscorable). **Echoed wrong
write** = same with verdict ECHO. Spans are WordPiece indices under SciBERT WordPiece;
direction FORWARD iff subject starts at/before object in character space of the converted
pointers.

- **R2-SAFE (primary):** silent wrong writes over T-seen + T-new + T-trap + T-hard
  (6,500 sentences) = **0**, and items written from T-trap = **0**.
- **R2-NEG:** WebRED-dev negatives (**STATE-only** EXECUTE; RETRACT recorded separately)
  / n ≤ **2 %** (n = 2,092).
- **R2-SEEN:** T-seen correct ≥ **1,940/2,000**, and STATE golds correctly EXECUTED ≥
  **ceil(0.90 × N_STATE_seen) = 736** (N_STATE_seen = 817).
- **R2-NEW:** T-new correct ≥ **2,400/3,000**, and STATE golds correctly EXECUTED ≥
  **ceil(0.65 × N_STATE_new) = 784** (N_STATE_new = 1,205).
- **R2-NAMES:** T-hard-names correct ≥ **300/500**.
- **R2-ASK:** wrong EXECUTED questions (verdict EXECUTE, act ASK, frame ≠ gold) on
  T-seen + T-new ≤ **25**.
- **R2-WEB** (wclosed, n = 46): executed ≥ **ceil(0.60 × 46) = 28**, and exact
  (subj, rel, obj, dir) ≥ **ceil(0.85 × executed)** of executed.
- **R2-NEWREL** (wnewrel, n = 1,500): EXECUTE with a **concrete seen relation**
  (rel ∉ {OPEN, UNSURE}) when gold rel is OPEN (or ≠ predicted) / n ≤ **1 %**.
- **R2-ECHO** (recorded, not gated): echoed wrong writes over the 6,500 ≤ 65.
- **R2-PAPER** (recorded only, no verdict): executed / correct / echoed on the paper panel
  if present; never gated.

Arm gate = all of SAFE, NEG, SEEN, NEW, NAMES, ASK, WEB, NEWREL.

---

## 2. Registered interpretations (fixed before sealing)

1. **Frame golds from rung-1 examples.** teach / correct → STATE; ask with exactly 1 hop →
   ASK; ask ≥ 2 hops → UNSURE; forget → RETRACT; quote / hearsay / hypo / negation
   (generator act `quote`) → NO_FACT; smalltalk → NO_FACT; unsure / multi / leftover /
   gibberish / multi-item → UNSURE; person → UNSURE; alias → UNSURE; trap.stmtq
   (generator act `ask`, 1 hop) → ASK; trap.leftover always UNSURE.
2. **Relation class.** known key (WebRED train name ∪ our closed-40 keys) → that class;
   anything else including open nouns → OPEN; unrepresentable → UNSURE. Classes =
   481 WebRED-train ∪ closed-40 (union size 515) + OPEN + UNSURE = **517**
   (`relation_classes.json`).
3. **Brake 3 / three seeds.** The gated verdict is the full five-brake ensemble over seeds
   **4701, 4702, 4703**. Each single ear is also scored with brakes 1, 2, 4, 5 and its own
   τ; all three single-ear tables are printed. No mark is gated on a single ear.
4. **Thresholds (doc 43 §B.5).** τ0 = smallest value giving 0 wrong EXECUTED writes on the
   sealed CAL under the same pipeline (sentinel: no wrong writes at τ = 0 → τ0 = 0);
   τ_exec = 1 − (1 − τ0)/2; τ_echo = 0.5 fixed. Computed separately for the ensemble and
   each single ear. CAL is never a test panel.
5. **Temperatures** fitted on CAL by golden-section on log-temperature at the end of each
   seed, stored in the checkpoint.
6. **Confidence** = min over temperature-scaled head probabilities: act, rel, subject
   pointers, object pointers (STATE) or p(absent)² (non-STATE), direction; for STATE /
   RETRACT also × (1 − max(neg, hypo, reported) flags).
7. **OPEN never EXECUTE** (forced ECHO). **Brake 5** runs only when relation ≠ OPEN.
   **Surface strategy** for the adapted item: prefer a wording of the predicted class that
   is grounded (`_relation_grounded`) or appears in the utterance; else any wording-table /
   RELATION_MAP surface present in the text; else a content word from the text (so brake 5
   does not spuriously block EXECUTE when the sentence never spells the relation). Path =
   `[canonical_relation(surface)]`.
8. **Brake 4** applies only to acts that point at spans (STATE / ASK / RETRACT), never to
   UNSURE / NO_FACT. Every [UNK] wordpiece must lie inside a pointed span.
9. **Brake 1** rejects act ∉ {UNSURE, NO_FACT} from EXECUTE (i.e. abstain never executes);
   act "?" (unscorable encode) → REPHRASE, never correct, never EXECUTE.
10. **Unscorable rows** (gold span unreachable at MAX_LEN=96 or span width > 12 WP) count
    as **incorrect** and never EXECUTE (decode short-circuits). They are still in the panel
    `n`. Registered unscorable counts after `--report`: t_seen/t_new/t_trap/t_hard = 0;
    wneg = 0; wclosed = 0; wpos = 13; wnewrel = 11.
11. **Hearsay markers** are extended **additively in-process only** (`fable_ears47_data.py`
    rebinds `LE.REPORTED_SPEECH_MARKERS` as a list; source file never edited). Glue is a
    single space (`marker.strip() + " " + text`) so padded `" marker "` matches both
    `flags_of` and the LE non-write guard.
12. **N_STATE for need_exec** is counted from `gold47.act` on all panel rows (including
    unscorable), not from the encoded gold — so thresholds cannot shrink when a span is
    unreachable.
13. **Qwen practice sentences are skipped** for this run (pool = 60k synth + all WebRED
    train). Deviation, registered here.

---

## 3. Deviations from the design, stated before sealing

1. **Rung-1 tape / BiGRU are not re-run.** Doc 47 §3 offers A/B for comparison; doc 48
   says stop at EARS. Rung-1 RESULTS numbers are the baseline column.
2. **Seq length 96** (not 64 as an early draft): MAX_LEN = 96 in data and train; span cap
   MAX_SPAN_WP = 12 enforced at encode time (drop, count in `--report`).
3. **WebRED train drop:** 614 / 81,517 (0.75 %) rows dropped for span beyond len 96 or
   > 12 WP; recorded, not repaired.
4. **wclosed brake-5:** 11 / 46 have a pronoun subject (cannot write) and 5 are rejected by
   the unchanged LE non-write guards (negation / reported speech). Those rows can ECHO or
   REPHRASE but not EXECUTE; R2-WEB still requires executed ≥ 28, so the model must
   EXECUTE enough of the remaining ~30.
5. **Smoke run** (200 steps, seed 4701, pool truncated to 2,048) is **not** a registered
   seed and is discarded before scoring; it exists only to prove the plumbing.

---

## 4. Panels and their hashes (sealed by this file)

Generated by `fable_ears47_data.py --build` with `FORMAT = fable-ears47/rung2/1`.
Strip-hash = same rows under rung-1 `FORMAT = fable-ears45/rung1/1` with keys
`gold47` and `source` removed — must equal the rung-1 PASSMARKS shas for the shared
synth panels.

| panel | n | STATE | sha2 (rung2 FORMAT) | strip1 (must match rung-1) |
|---|---:|---:|---|---|
| cal | 5000 | 1941 | `d7609002f53396ed60566dde0e41656e1a4d34f1aff59033b1c768ac98586355` | `a6929f1eed3526268aea929465b2f3c4b1a78a543548579b3619d183ec504579` ✓ |
| t_seen | 2000 | 817 | `90c82a0d4c8cd9099f840b8c85263ebe1f61869c2255f4037dc1fde04fbb4edd` | `5aac3fb6fa6c10d9de3b0e2fa639b252bc949007d65cfd46d36e7cef57a74427` ✓ |
| t_new | 3000 | 1205 | `58da9345d12ce709dd0185dd581279d84b39c2d03d3df515f27c7a9eafa9b4ed` | `1f1c81b42175607ed7de55bddde7fd30edb33102edb0dfa108f85dd499bc105a` ✓ |
| t_far | 1000 | 417 | `e104b4d049b99118cc23e459f859f13808b35a99027ee7e28953d23791030d70` | `856221c814fde0247b91a87762063261e15588c80a7ea453ec3ed624a57d10df` ✓ |
| t_trap | 1000 | 0 | `fca23899e732bde2fc665abf70a0c5c15591f75d8bdf1ebfc01b6588c9474fd7` | `836a5d1eb744c1c884fc9d4dbc1ab97ec2ab61a4a0260265e46dfe5568d3b5b5` ✓ |
| t_hard | 500 | 202 | `76f2067d867643bf86d104c299bb86b3b368e68a09d8bf1507d787a62d45eb19` | `79a2e04f6a78422150447ccf50cd717867dc1cd5912c45d6d01b78a380c7c7f7` ✓ |
| wneg | 2092 | 0 | `77865e2444ab12e42e93df08904db5c96bbcd5657be9638479b71104986bfe86` | (webred, new) |
| wpos | 1806 | 1806 | `337d879020f9207b5ab2c8e6eb6892589105788161a6258de09d668cb11805b0` | (webred, new) |
| wclosed | 46 | 46 | `27105594a4cc424d65e5857e0a3514dc09b9a139d4acf325e8b90729d733653f` | (webred, new) |
| wnewrel | 1500 | 1500 | `3b6bb0d6b5c5b3d6af327ff143424262d6b3c2bfe6370c8b9e74b6783a4aa61d` | (heldout, new) |

Relation classes file: `relation_classes.json` sha256
`1831de0a360b0dd3cc0bec88e5a001524b3417a90e58cc7214b37313319e7102`.

Split / pool / lexicon identity inherited from rung 1: split sha `41d7e588dd0b2f3c`,
pools sha `1b4f9f5bdf0d7001`, lexicon sha `552899c55ae3a0f0`.

need_exec from `--report`: SEEN ≥ 736, NEW ≥ 784.

---

## 5. Encoder check that must pass before training

`fable_ears47_encoder.py --check <snapshot>` must print `CHECK PASS`
(max |hidden diff| < 1e-3, 0 token mismatches) or the arm is void.

Recorded 2026-09-21: model `allenai/scibert_scivocab_uncased`, licence Apache-2.0,
weights `pytorch_model.bin`, params 109,327,872, token mismatches 0/20,
max|hidden diff| **1.05e-04**, pad-vs-single 5.72e-06 → **CHECK PASS**.

---

## 6. Training recipe (fixed)

Full fine-tune SciBERT + frame head; bf16 autocast on CUDA; batch 32; MAX_LEN 96;
2 epochs; AdamW lr 3e-5, cosine, wd 0.01, clip 1.0; seeds **4701, 4702, 4703**;
tokens/s at step 200; if projected wall-clock > 40 min/seed → freeze lower encoder layers
and register the deviation. Pool = 60,000 synth (POOL_SEED 47100) + all WebRED train
(span-reachable only) + optional ≤ 3,000 Qwen (skipped, §2.13). Hearsay augmentation
p = 0.10 on STATE pool rows → gold NO_FACT.

---

## 7. If a registered mark fails

Record the FAIL and stop. No fix cycle in this task. Every silent wrong write is listed
verbatim (utterance, gold frame, decoded frame) and echoed wrong writes likewise, so the
lead can decide.
