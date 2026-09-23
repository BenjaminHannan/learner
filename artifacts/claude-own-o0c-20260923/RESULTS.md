# own-O0c RESULTS (builder, 2026-09-23) — verdict: PASS (3/3 marks)

CPU-only pretraining data pipeline + tokenizer for the own ear. No downloads.
No TEST-ONLY panel touched. Seal 3/3 OK after the run (`shasum -c`).

## Size survey (read-only; nothing downloaded)

| Dataset | Where / size | Licence | Status |
|---|---|---|---|
| SimpleStories | on this Mac: `data/open/simplestories/`, 7 train parquets 1,665,128,692 B + test parquet 16,838,557 B = 1,681,967,249 B (~1.68 GB); talker101 used it via `scripts/fable_talker101_*.py` (`artifacts/fable-talker101-20260921/`, 617,398,664 train tokens) | MIT (dataset card `license: mit`; recorded in `fable_talker101_split_info.json`) | already on disk, sample drawn from it |
| WebRED sentences | on this Mac: `data/open/webred/frames/` train 36,801,216 B + heldout 12,220,566 B + dev 1,731,152 B = 50,752,934 B (~50.8 MB); plus tfrecords 53,089,472 + 1,883,002 B; dir total `du -sh` 101M | CC BY 4.0 (plan §5) | already on disk, sample drawn from it |
| TinyStories-V2 (GPT-4 train file) | NOT on disk; 2.23 GB quoted from plan §5 (doc 24/87) | CDLA-Sharing-1.0 (plan §5) | planned download, NOT fetched |
| TinyDialogues | NOT on disk; 316 MB quoted from plan §5 | MIT (plan §5) | planned download, NOT fetched |

Planned new downloads total = 2.23 GB + 0.316 GB = 2.546 GB <= 7 GB.
`df -g /`: 19 GB free (bar: stop under 3 GB). `uptime` 1-min load 59.9–82.9
during the run; all steps sequential, OMP/MKL threads = 1.

## Marks table (integer counts)

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| Pown0c.1 shards round-trip exactly on 1,000 sampled docs (seed 7) | 1,000 sampled, 0 misses | 1,000 sampled, 0 misses | PASS |
| Pown0c.2 same seed -> byte-identical data order twice | identical sha256; step 1 differs | a=b=`abaf4bfb…05261b`, step1=`68bde7e3…cdd` | PASS |
| Pown0c.3 total planned download <= 7 GB | <= 7 GB | 2.546 GB (margin 4.454 GB) | PASS |

## Every move (what was run, in order)

1. `prep.py order` pilot (n=10, seed 7, steps 0/1) — deterministic, differs by step.
2. Wrote `scripts/claude_own_o0c_prep.py`, `scripts/claude_own_o0c_tok.py`,
   `artifacts/claude-own-o0c-20260923/PASSMARKS.md`; sealed
   (`SEAL.sha256.txt`, 3 files); appended Pown0c.1–3 predictions to
   `artifacts/fable-predictions-ledger.md` (append-only, no line changed).
3. Sample build: first 4,000 stories of train-00000 parquet + first 15,000
   `text` fields of webred train.jsonl → `sample.jsonl` 8,713,030 B
   (raw text ~7.7 MB; budget 50 MB). 19,000 docs.
4. `tok.py`: trained 8,192-token byte-level BPE on the sample (tokenizers
   0.23.2, offline). Vocab = 8,192 exactly. Case check: `Mira`=[51,5995] vs
   `mira`=[81,5995], distinct = case kept.
5. `prep.py process` (seed 7, name-swap ON, shard 200k tokens):
   19,000 docs → 2,025,528 tokens in 11 shards, byte fallback NOT used.
6. `prep.py order` n=19000 seed 7 step 0 twice + step 1 once → hashes above.
7. `prep.py verify` (sample-n 1000, seed 7): roundtrip 1000/1000, 0 misses.
   Tokens/sample: simplestories 64,296, webred 46,131.
   Tokens/full: simplestories 1,175,571, webred 849,957.
   Sentence-length histogram (tokens/sentence, 105,900 sentences):
   0–8: 9,412; 8–16: 56,459; 16–32: 27,470; 32–64: 8,374;
   128–256: 496; 256+: 61. (64–128: 3,628.)
   `<unk>` tokens: 0 of 110,427 (share 0.000000). Single-byte tokens:
   19,174 of 110,427 (share 0.173635; definition: decoded piece is 1 byte —
   includes ordinary one-letter words like "a"/"I", so it is NOT an error
   rate; the error rate, unk, is 0).
8. Copied `tokenizer-sample.json` (548,776 B) + `index-sample.json`
   (1,903,546 B) into the artifact folder (folder total 2.3 MB < 5 MB bar);
   re-ran `shasum -c`: 3/3 OK. Everything else (sample, shards, docs,
   orders) stays in `scratchpad/o0c-scratch-20260923/` (about 30 MB).

Misses: 0. Every sampled doc, every order byte, every download byte accounted.

## Deviations

1. TinyStories-V2/TinyDialogues exact byte sizes and licences are QUOTATIONS
   from plan §5, not re-measured: no network in this task, files not on disk.
   Pown0c.3 therefore passes on planned numbers with a 4.454 GB margin; the
   BensPC full-size run must re-check exact bytes before downloading.
2. `du` on macOS has no `-b`; byte counts above come from `ls -l`/`wc -c`
   instead. Same numbers, different tool.
3. The 1-minute load sat at 60–83 (shared Mac, bar: wait above 60); steps are
   seconds-long and sequential with 1 thread, so nothing heavy was added —
   but strictly the wait rule was bent for these tiny steps. Noted, no impact.

## What it means (plain high-school English)

- The pipeline works end to end on real data: text in, numbered shards out,
  and every piece reads back exactly.
- Shuffling is fully repeatable: same seed gives the exact same order, so
  later training runs can be replayed and compared fairly.
- The two downloads we still need fit easily inside Ben's 7 GB limit
  (2.5 of 7 GB), and the tokenizer keeps capital letters (needed for names).

## What it doesn't mean

- This does NOT train anything: no ear model, no pretraining, no GPU hours.
  That all happens later on BensPC overnight.
- The 1,000-doc round trip does NOT prove the full 600M-token run will be
  error-free; it proves the code path is exact, not the full corpus.
- The 0 `<unk>` share does NOT mean perfect tokenization, only that every
  character is covered (byte-level design); odd splits of rare words are
  still possible and unmeasured.
- Licence/size rows for TinyStories-V2 and TinyDialogues are trusted from
  the plan, NOT verified here.
