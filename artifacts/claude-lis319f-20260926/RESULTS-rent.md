# lis-319f rental result (rent-lis-319f): FORMER mode trained, both readers read the sealed panel once

Rental run 2026-09-26 on vast.ai (reading thread's $2 line). Sealed code run unmodified
(scripts only; one env install: peft, see deviations). Panel readpanel371c read exactly
once per reader (OLD 14:15 UTC, NEW 14:19 UTC). Counts only; no panel turn is quoted.

## Marks

M1-M3 pending judges. The whole-claim marks need blind judges on the pairs files, which
the reading thread runs after this job. No verdict is computed here.

Counts for the judges' inputs (verbatim scorer stdout):

former_old.json (OLD = lis-319 merged, T 0.995):
{"former_as_current": 6, "former_items": 64, "former_rows": 49, "former_rows_with_such_save": 5, "rows": 240, "threshold": 0.995}

former_new.json (NEW = lis-319f merged, T 0.995):
{"former_as_current": 0, "former_items": 64, "former_rows": 49, "former_rows_with_such_save": 0, "rows": 240, "threshold": 0.995}

Validity per PASSMARKS: panel has 49 rows with a former item (>= 30 OK); OLD makes
6 former-as-current saves (>= 2 OK). The panel can test the change.

pairs_panel_old.jsonl counts (T 0.995):
{
 "0.995": {
  "rows": 240,
  "gold": 355,
  "saved": 125,
  "saved_exact": 72,
  "saved_needs_judge": 46,
  "saved_nomatch": 7
 },
 "pairs": 47
}

pairs_panel_new.jsonl counts (T 0.995):
{
 "0.995": {
  "rows": 240,
  "gold": 355,
  "saved": 119,
  "saved_exact": 76,
  "saved_needs_judge": 42,
  "saved_nomatch": 1
 },
 "pairs": 43
}

## Build counts

Base data (claude_lis319_data.py, same args as lis-319): train 50044, dev 1311, as expected.

BUILD.json (verbatim; parsed-JSON-equal to BUILD-dryrun.json: BUILD_MATCH):
{
 "train": 51244,
 "dev": 1461,
 "train_relabel": {
  "former:classmate": 4,
  "former:employer": 4,
  "former:occupation": 36,
  "former:roommate": 4,
  "former:teacher": 8,
  "former:work_location": 12,
  "rows_relabelled": 64,
  "rows_relabelled:chat318": 16,
  "rows_relabelled:hist319": 20,
  "rows_relabelled:opus": 4,
  "rows_relabelled:opus301": 24
 },
 "dev_relabel": {
  "former:city": 1,
  "former:classmate": 1,
  "former:occupation": 2,
  "former:roommate": 1,
  "former:work_location": 2,
  "rows_relabelled": 7,
  "rows_relabelled:chat318_dev": 2,
  "rows_relabelled:hist319_dev": 3,
  "rows_relabelled:o0a2": 1,
  "rows_relabelled:opus301_dev": 1
 },
 "templates_train": {
  "former_c_city": 91,
  "former_c_employer": 115,
  "former_c_job": 70,
  "former_city": 166,
  "former_employer": 163,
  "former_job": 189,
  "former_pair": 142,
  "former_person": 156,
  "former_pet": 108
 }
}

LENGTHS.json (verbatim; max-len 512, exit 0, nothing over):
{
 "train": {
  "rows": 51244,
  "max": 491,
  "p99": 320,
  "over": 0,
  "over_by_src": {}
 },
 "dev": {
  "rows": 1461,
  "max": 382,
  "p99": 315,
  "over": 0,
  "over_by_src": {}
 }
}

## Train summary (train_summary.json verbatim)

steps 6406/6406, stopped null, train_rows 51244, dev_rows 1461, dev_loss 0.04212199322723327,
trainable_params 22413312, all_params 1103046144, minutes 33.96, tok_per_s 6753.9,
device cuda, epochs 2.0, lr 0.0002, rank 32, batch 16 (no OOM, no batch-8 retry),
max_len 512, max_minutes 150.0, limit null, merge true, seed 300.

## DEV (report only, T 0.995)

dev_pred_new.jsonl: NEW read of $WORK/data319f/dev.jsonl, 1461 rows ("read 1461 rows on cuda").
dev_tpl.jsonl (on rental only): subset --src-prefix former319 -> 150 rows.
dev_pred_old_tpl.jsonl: OLD read of the 150 template rows ("read 150 rows on cuda").

dev_former_new.json (verbatim):
{"former_as_current": 3, "former_rows:chat318_dev": 2, "former_rows:former319_dev": 110, "former_rows:hist319_dev": 3, "former_rows:o0a2": 1, "former_rows:opus301_dev": 1, "former_rows_scored": 117, "saved_right": 17, "threshold": 0.995}

dev_former_old.json (verbatim; preds = lis-319 BensPC dev_pred.jsonl (1311 rows) + OLD template re-read):
{"former_as_current": 27, "former_rows:chat318_dev": 2, "former_rows:former319_dev": 110, "former_rows:hist319_dev": 3, "former_rows:o0a2": 1, "former_rows:opus301_dev": 1, "former_rows_scored": 117, "saved_right": 1, "threshold": 0.995}

dev_score_new.txt (lis-300 score, NEW on lis-319f dev, T 0.995, verbatim):
{
 "turns": 1461,
 "gold_writes": 1112,
 "pred_writes": 659,
 "wrong_facts": 2,
 "ask_turns": 140,
 "ask_ok": 130,
 "hits": 657,
 "gold_write_turns": 774,
 "turn_exact": 486,
 "held_back_facts": 446,
 "we_turns": 19,
 "we_asked": 19,
 "wrong_turns": 2,
 "wrong_turns_on_nosave_turns": 1,
 "threshold": 0.995,
 "recall_exact": 0.5908273381294964,
 "ask_acc": 0.9285714285714286,
 "we_ask_rate": 1.0,
 "wrong_turns_by_family": {
  "o0a2": 1,
  "teach_multi": 1
 },
 "ms_median": 748.2,
 "ms_p90": 993.5,
 "ms_max": 1650.7
}

## Readers

OLD (lis-319 merged): model.safetensors sha256 on the rental
e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76 (matches the
required value). Reached the rental by direct Mac rsync of
~/premonition-models/lis319-merged/ (Mac sha verified first, same value; BensPC
fallback not needed). Background upload ran 13:22-14:06 UTC while seals/data ran.

NEW (lis-319f merged): model.safetensors sha256 on the rental (SEAL-run.sha256.txt)
970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b.
Copied back to the Mac at ~/premonition-models/lis319f-merged/; Mac sha matched
SEAL-run before destroy. Weights never pushed to git.

BASE: openbmb/MiniCPM5-1B snapshot
/root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
(commit 87179e5c1f455ef22e6223592d2d61351b525bfc, as expected). No MiniLM, no
self122_head.pt, no route122 check.

## Seals

All six checks 0 failures (run from ~/tree where paths resolve; readpanel seal from
its own dir): lis300 14/14 OK, lis301 13/13 OK, lis318-data 14/14 OK, lis319-data
16/16 OK, lis319f 5/5 OK, readpanel371c 8/8 OK.

## Machine, money, wall time (UTC 2026-09-26)

- GPU: 1x RTX 5090 (vast.ai). Credit at start: 6.749200177269863 (balance 0), above
  the $3.00 rental floor.
- Rental 1: id 52750756, $0.4963/hr, created 13:10:52. Host 410852 could not pull the
  image (docker proxy refused, still "loading" at 13:16:44, past the 6-min rule) ->
  destroyed ~13:17 (~0.11 hr, ~$0.05).
- Rental 2: id 52751954, $0.5037/hr, created 13:17:32, running 13:19:05,
  ssh ssh9.vast.ai:31954, image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime, disk 80 GB.
  Destroyed 15:04:43 after copy-back (see ledger line); 1.79 hr x $0.5037 = ~$0.90.
- Running total ≈ $0.95 of the $2.00 budget (never near the $1.80 stop).
- Wall time: tree stream ~13:20-13:22; setup (pip+BASE) 13:22-13:24; seals ~13:24-13:25;
  base data 13:25-13:28; 319f data ~13:28; lencheck ~13:28-13:29; train attempt 1
  ~13:30 FAIL (peft); peft install ~13:31; train 13:32-14:07 (summary 33.96 min);
  seal+summary copy 14:11; panel rows 14:11, OLD read to 14:15, NEW read to 14:19
  (240 rows each, "read 240 rows on cuda"); former/pairs scores 14:20; dev subset
  14:21; NEW dev read 14:22-14:40 (1461 rows); OLD tpl read 14:40-14:42 (150 rows);
  dev scores 14:42; copy-back from 14:46.

## Deviations (all reported, none touch code or the panel)

1. Re-rented once: first host (410852) failed the 6-min start rule (host-side docker
   proxy error); destroyed by exact id, second host (406325, South Korea) ran in 90 s.
2. Streamed 4 tiny design text files to the rental (frame-spec.md, relation-names.txt,
   frame-spec-notes-301.md, frame-spec-notes-319f.md): the listed TREE paths omit files
   the five SEAL files hash, so "all OK" was otherwise impossible. Nothing staged on
   the Mac.
3. Streamed artifacts/claude-lis319-20260925/dev/dev_pred.jsonl (1311 rows, from
   origin/builder-outbox) to the rental: step 8 needs it as an input and the TREE list
   omits it.
4. pip installed peft 0.21.0 on the rental: scripts/claude_lis300_train.py imports it
   and the kit pip line omits it. Environment only; code untouched.
5. Re-ran the fullclaim_b pairs scorer (CPU-only, no model) to capture full stdout;
   outputs byte-identical to the pushed files (cmp SAME). Each reader's model read of
   the panel happened exactly once.
