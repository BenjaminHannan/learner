# vread data: sealed before any training (vector-reader thread, 2026-09-27T22:52:13Z)

Built by `scripts/claude_vread_data.py build` (code only; no model reads, writes or judges any row). The pack
(`data/dialogs.json.xz`, `data/rows.json.xz`) and `data/build.json` are the only inputs both arms train and test on.
`scripts/claude_vread_data.py unpack` rebuilds every row file from the pack and stops unless every sha256 below matches.

## Inputs (read-only, pinned)
- Luna chats, chunks 1-10 only, from origin/builder-outbox `artifacts/claude-lis320-20260926/full-luna/chunkK/raw.new.jsonl.gz`
  (sha256 of each file in `data/build.json` → `inputs_sha256`). 2,028 rows joined in chunk order;
  `claude_lis320_resume_clean.clean` (ADDENDUM-11) keeps 2,028 of 2,028 (0 dropped, 0 unparsed).
- Seeds: `claude_lis320_seed_cr.py --seed 324 --n 6000 --ask-back` (the chunk jobs' command line), sha256
  9d17c5fe3e6171e0cb0ab87390d0144e325903de54200ef60f074302a29678d2, equal to chunk 1's SEEDS.sha256.txt.
- Kept rows: `claude_lis320_check_we3.py` unchanged. 13,891 of 14,239 turns kept, the same count and family mix as
  chunk 10's check.json. Every row is Luna-worded with a code label. No Claude-written row, and no test panel is read.

## Split (whole dialogs on one side only)
- dev (practice test) = `claude_lis320_build.is_dev(row id, 10.0)`: 211 dialogs, 1,444 rows.
- The rest is train. A calibration slice of train (sha256("vread-cal:" + dialog) % 1000 < 100) holds 179 dialogs,
  1,230 rows. The vector reader uses it only to pick its 1B layer and its save bar, and never trains on it.
- The LoRA reader trains on all 12,447 train rows (1,638 + 179 dialogs), as its sealed recipe does.
- Leak check: 0 dev dialogs in train or calibration (shown, `dev_dialogs_in_train_or_cal`).

## Cards
Each code-label fact with mode ASSERT, CORRECT or FORMER becomes a card: owner, relation (the 153-name table, all
labels are in it), value, and state (current, correction, former). The other modes (PLAN, CHECK, QUESTION, REPORTED,
SUPPOSE, UNCLEAR) and empty frames are "no fact". 14,483 cards from 16,920 label facts.
- Owner "me" points to the ME cell. Every other owner and every value points to one exact whole-word span of the
  prompt the LoRA reader sees (the turn, then the previous reply, then earlier turns newest first). A span is exact
  when its tokens decode to the label string itself.
- Labels that can't be mapped to exact spans: **0 of 14,483 cards** (0 owner and 0 value fields). So no row is
  dropped from either arm.
- Pointer check (50 train rows, 76 cards): the gold spans rebuild 76 of 76 gold cards exactly (shown, CPU, the real
  tokenizer at 87179e5c1f455ef22e6223592d2d61351b525bfc).

| side | rows | cards | dialogs |
|---|---:|---:|---:|
| train (vector reader) | 11,217 | 11,656 | 1,638 |
| calibration (part of train) | 1,230 | 1,319 | 179 |
| dev (practice test) | 1,444 | 1,508 | 211 |

Dev by family (rows): teach 500, backref 136, correct 117, ask 86, former 86, yes_after_ask 51, ack_after_ask 49,
jobhome 48, smalltalk 46, plan 43, someone_else 39, ambiguous_pronoun 37, hypothetical 36, doubt 31, confirm 30,
question 30, correct_ref 56, negation_only 23. Look-alike rows (question, plan, doubt, someone_else, hypothetical,
negation_only, confirm, ambiguous_pronoun): 269.

Dev cards: 1,422 are current or correction (the ones that can be saved), and 86 are former. 173 are corrections
(117 correct + 56 correct_ref) and 136 are backref. 192 of the 1,422 have an owner named only in an earlier turn. The
unchanged compiler can never save those (owner_not_span), for either arm. So a perfect reader saves 1,230 of 1,422
under the main rule and 1,422 of 1,422 under the history rule (shown, gold scored as a read).

## Row files (sha256; checked on every unpack)
- LoRA arm: train.jsonl dceb88b6b367535e56dacd3cbcf72233ead3566fd98d731712288b976a06ac7a,
  cal.jsonl a8ce561082e4ec363317722865ca9bb3b5cbc6ab08a24945c2e69e2a25620b1b,
  dev.jsonl bda83d4e310590055d78e9d78d6b3bc053027d3c3b86a95fb5853fe3073ff9fe
- Vector arm: train.cards.jsonl 65d9c3a81be553130a26c27f332a4a4a1d0c6d932467bcdc27a6da0f47969ea0,
  cal.cards.jsonl bece12ceb0f93c0a839ad9f59670ae834eb13227e56f1b4eaac4f35d360a2ad2,
  dev.cards.jsonl 100afee6296311b2a3555cf5362d2b7b1193b3c903a5f025824098ffda474c8b
- Pack: dialogs.json.xz e3cf8eb02a80d076cd72abd6d1a1613c81defdadba30deba198aa8a9a1d06ed0,
  rows.json.xz 4829d90c969d08565e715ad5e700ecda1520d48812d2984c24448a25e5a5fe24
