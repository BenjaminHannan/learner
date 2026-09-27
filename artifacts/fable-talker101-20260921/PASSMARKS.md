# Exp 101 PASSMARKS — talker first from-scratch run (Muse prep)

Sealed BEFORE any training run (smoke or full). Seed for this first run: **101, one seed only** (T4).
Model: `scripts/fable_talker101_model.py` (28,847,105 params, 28.85M).
Data: SimpleStories train (2,115,696 stories) minus sealed 1% val (21,156 stories,
`fable_talker101_val_idx.npy`, sha256 `bd7b390c…2a8220` — full hash in `fable_talker101_split_info.json`).
Tokenizer: 4,096-token byte-level BPE fit on TRAIN ONLY (200,000 train stories, seed 101).
Train tokens: 617,398,664. Val tokens: 6,263,221.

## Smoke gates (Mac CPU, 200 updates, tiny batch; must pass before the director's full GPU run)
- S1: final train loss (mean of last 20 steps) is below the mean of the first 20 steps.
- S2: checkpoint files exist at the 10%-fraction steps and `--resume` from
  `fable_talker101_ckpt_last.pt` continues the step counter with finite loss.

## Full-run gates (director's GPU run, seed 101 only)
- T1: final held-out val loss is below the 10%-checkpoint val loss by >= 0.30 nats.
- T2: BLiMP-10 accuracy >= 70% overall, reported per phenomenon (10/10 rows printed,
  no averaging across seeds — there is only one seed).
- T3: all 50 sampled continuations (10 prompts x 5, temp 0.8, seed 101) are stored
  verbatim in `fable_talker101_samples.json` for Ben to read. No gate — reported as-is.
- T4: one seed only (101). Stated plainly; nothing is averaged.

A registered FAIL on T1 or T2 is recorded as FAIL, never re-run into a pass.
BLiMP-10 files: determiner_noun_agreement_1, regular_plural_subject_verb_agreement_1,
anaphor_gender_agreement, transitive, principle_A_c_command, tough_vs_raising_1,
ellipsis_n_bar_1, irregular_past_participle_adjectives, npi_present_1,
existential_there_quantifiers_1 (official repo alexwarstadt/blimp; no licence file ships
with it — eval use only; paper Warstadt et al. 2020).
