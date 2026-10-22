# Panel hashes for the 13-gram check

`panel_hashes_all.npz` holds only 64-bit hashes (and counts) of the word windows of these panels' **text fields** (passages,
paraphrases, questions, prompts; never answers). 550,139 hashes. It cannot be turned back into text.

| panel | file(s) | text fields hashed | texts | ignored (< 8 words) |
|---|---|---|---|---|
| English eval R3 / R5 / R6 / GEN-HELDOUT-R4 | `custom_io/english_eval/*.json` on branch `claude/custom-reader-talker-4x309r` | source_text, paraphrase, questions[].question | 4 x 192 | 80 / 103 / 119 / 84 |
| skills dev, 40 per cell (seed 1) | `skills_curriculum.build --train 200000 --dev-per-cell 40 --seed 1` (hashes match `FULL-BUILD-MANIFEST-200k-seed1.json`) | prompt | 6,200 | 448 |
| skills dev, 200 per cell (seed 1) | same builder, `--dev-per-cell 200` | prompt | 31,000 | 2,352 |
| ARC-Easy test | `allenai/ai2_arc` | question stem only (no choices, no key) | 2,376 | 174 |
| GSM8K test | `openai/gsm8k` main | question only | 1,319 | 0 |
| bAbI test (20 tasks x 1,000) | `Muennighoff/babi` | passage, question | 40,000 | 18,048 |

NOT in here, by rule: GOLD-PRIVATE-v1.json and every reserved or blind panel. `overlap13.py index` refuses those names. Their owner
runs `python3 overlap13.py index --spec <their spec> --out theirs.npz` on their own side, shares only the .npz, and
`python3 overlap13.py merge --out all.npz panel_hashes_all.npz theirs.npz` adds it. Until then the pool is NOT cleared against them
(see section 6 of the plan).

Regenerate: copy the files above next to `spec_*.json`, run `index` for each spec, then `merge`.
