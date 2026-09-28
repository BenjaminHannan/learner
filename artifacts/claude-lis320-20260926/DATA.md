# lis-320 DATA (sealed before training)

Written 2026-09-28T13:25:01Z. Source outbox: 43f2691c2c01322ef3809434a9123ee0e1202838. Seed: 324, 6,000 dialogs.

Shown: all 6,000 dialogs have one parsed row after the registered resume cleaner;
rawcheck2 is OK, writer GPT-6 Luna only, temperature null (route default).
No Claude-written or Claude-judged training rows or labels are used.
The legacy src tag `glm320` and style key `glm_kept` name the existing code format;
provenance is Luna. GLM contributes 0 dialogs and 0 kept turns.

Code-kept turns: 41054. Train: 39695 turns / 5801 dialogs.
Dev: 1359 turns / 199 dialogs. Split: sealed builder, dev-pct 3.
Dialog overlap: 0. Existing code recased 10 labels; no manual fixes.
Counts and all hashes are in full-luna/final/COUNTS.json. Chunk compressed hashes
pin the exact raw data. DATA-HASHES.json pins the reconstructed seeds, raw, kept,
train and dev bytes. The training job must reproduce and match every hash.

| Family | Seeded turns | Kept Luna turns | Luna dialogs containing family |
|---|---:|---:|---:|
| ack_after_ask | 1385 | 1225 | 1238 |
| ambiguous_pronoun | 1056 | 1054 | 979 |
| ask | 2601 | 2597 | 2196 |
| backref | 3398 | 3371 | 2705 |
| confirm | 1010 | 1010 | 939 |
| correct | 3325 | 3250 | 2719 |
| correct_ref | 1764 | 1742 | 1598 |
| doubt | 1010 | 1003 | 954 |
| former | 2569 | 2484 | 2135 |
| hypothetical | 1035 | 1021 | 951 |
| jobhome | 1581 | 1550 | 1454 |
| negation_only | 939 | 938 | 871 |
| plan | 1034 | 993 | 960 |
| question | 1046 | 1046 | 967 |
| smalltalk | 1388 | 1374 | 1253 |
| someone_else | 994 | 992 | 934 |
| teach | 14602 | 14265 | 6000 |
| yes_after_ask | 1307 | 1139 | 1188 |

A dialog can contain several families. Per-writer counts are in COUNTS.json.
Style versus DEV chats and bank: full-luna/final/style.json (report only).
Suggested: this meets the sealed data provenance and completion gates.
Untested: the trained reader and all readpanel320 marks.

Training remains MiniCPM5-1B revision 87179e5c1f455ef22e6223592d2d61351b525bfc,
LoRA rank 32, 2 epochs, lr 2e-4, batch 16, max-len 512, seed 300,
claude_lis319_common.build_prompt_hist; unchanged compiler, T=0.995.
