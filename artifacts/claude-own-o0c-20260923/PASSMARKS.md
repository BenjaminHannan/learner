# own-O0c PASSMARKS (sealed BEFORE the sample run, 2026-09-23)

Task: pretraining data pipeline + tokenizer for the own ear (plan §2.1, §5).
CPU only. No downloads in this task. Full-size run happens later on BensPC.

Sealed files (see SEAL.sha256.txt):
- scripts/claude_own_o0c_prep.py
- scripts/claude_own_o0c_tok.py
- artifacts/claude-own-o0c-20260923/PASSMARKS.md (this file)

Sample (fixed before sealing): first 4,000 stories of
data/open/simplestories/train-00000-of-00007.parquet (source tag
"simplestories") + first 15,000 lines of data/open/webred/frames/train.jsonl
`text` fields (source tag "webred"), name swapping ON (seed 7), tokenizer
trained on the sample text only, shard size 200,000 tokens. Raw sample text
is well under the 50 MB budget (about 9 MB expected).

Interpreter: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
--no-project --python 3.12 --with <deps> python -B <script> ...
(tokenizers 0.23.2 and numpy 2.5.3 verified present offline in the pilot.)

## Marks

- Pown0c.1 shards round-trip exactly: decode(encode(x)) == x AND
  re-encode(decode(ids)) == ids on 1,000 docs sampled with seed 7 from the
  written shards. Bar: 1,000 sampled, 0 misses. Predicted: PASS, 0 misses.
- Pown0c.2 same seed -> byte-identical data order twice: `order` run twice
  with (n = doc count, seed 7, step 0) gives identical sha256; (seed 7,
  step 1) gives a different order. Bar: identical hashes, plus step differs.
  Predicted: PASS.
- Pown0c.3 total planned download <= 7 GB: TinyStories-V2 GPT-4 file 2.23 GB
  + TinyDialogues 316 MB = 2.546 GB planned new downloads (plan §5 numbers,
  quoted; remote byte counts not re-verifiable offline, no network in this
  task). Bar: <= 7 GB. Predicted: PASS (2.546/7 GB, margin 4.454 GB).

Report-only (no bars): tokens per source; sentence-length histogram;
share of tokens that are <unk>/byte fallback (byte-level BPE: expect 0 unk;
single-byte-token share reported with its definition).

## Proved-wrong / FAIL conditions

- Pown0c.1 FAIL if misses > 0.
- Pown0c.2 FAIL if the two same-seed hashes differ.
- Pown0c.3 FAIL if the planned total exceeds 7 GB.
- If `tokenizers` is not importable offline, step 3 stops and the run is
  reported as BLOCKED (not PASS/FAIL); pilot showed it IS importable.
- Any change to a sealed file after the seal makes the verdict FAIL.

Fictional names only in all outputs. No TEST-ONLY panel touched.
Sample outputs over 5 MB live in scratchpad/o0c-scratch-20260923 (listed in
RESULTS.md); only small files (tokenizer.json, index.json, logs) are kept in
this artifact folder.
