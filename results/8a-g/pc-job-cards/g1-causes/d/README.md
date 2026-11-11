# D: free read-only measurements on G1's saved B2 weights (3M s400, 10M s400)

Roadmap source: `reviews/G1-OTHER-CAUSES-RANKED-2026-10-12.md` section 3, "D". Nothing is trained. One script, `g1diag.py`, reads the two final
checkpoints (same cfg except blocks 2 vs 8) and writes `G1DIAG.md` (rules first), `g1diag.json` (everything), `rows.jsonl` (one record per dev row),
`train_sample.jsonl` (the 4,000 train rows it used).

## What it measures
1. **Error ledger**, 6 dev splits (in_dist answer frame vocab variant family; pooled-5 = the first five), both models. For every row the three outputs
   talk() could print (NUM = value of the slot the answer pointer picks, if valid; WORD = the pointed prompt word; GEN = the GEN string), the mode and output
   talk() really chooses (with its fallbacks), and whether each hits (evalx `is_hit`). Self-check: the chosen output equals `model.generate(batch)` for
   every row (must be 0 mismatches), and the mirror also equals `talk(..., return_modes=True)` in output and mode. Gold mode (0 NUM / 1 WORD / 2 GEN) comes
   from progparse `row_targets`; also whether the model's own final workspace holds the gold number. Tables: wrong rows by split x family x chosen mode x
   gold mode; fixed / broken rows 3M -> 10M.
2. **Oracle-mode rescoring**: a row counts if ANY candidate hits. Pooled-5, the 13-family block (arith_bare backward_solve chain_ops story_addsub
   story_chain3 chain_story2 var_chain div_exact table_calc distance_units compare_numbers state_update percent_rate) and the 21-family block (every other
   family in the dev files), normal and oracle at 3M and 10M, gains and error ratios. Normal pooled-5 is compared with `--result3/--result10`.
3. **10M block knockout** on in_dist: skip block i (0..7) in every round, and blocks 3-8 together (indices 2..7), by swapping `model.core` for a ModuleList
   without them (restored after). Safe: `run()` builds each block's K/V (`kv_of`) and zips `self.core` on every call, nothing is cached on the module.
4. **Per-term teacher-forced train loss**: 2,000 web rows (family `cloze`) and 2,000 non-cloze ("skill") rows, one streamed pass with reservoir sampling,
   `random.Random(0)`; `model.loss()` under `no_grad` on group-only batches of 64; mean of total, prog, mode, ans, word, gen per group.
5. **Gold log-likelihood per family**: the same loss on the 5 dev splits, batches grouped by (split, family), per family and pooled.
6. **Sealed decision rules** (printed with their numbers; written into the JSON and first in G1DIAG.md):
   - R1: oracle-mode 10M gain >= +3.0 (vs +1.64) -> routing masks the thinker (cause 6) -> marginal mode loss test next.
   - R2: skipping blocks 3-8 at 10M costs < 1.0 point in_dist -> idle depth (cause 7 or 2) -> short lr test (5e-4 vs 1e-3).
   - R3: non-cloze (skill) total train loss at 10M <= half of 3M, with dev flat (G1's gain +1.64; D's own recomputed gain is shown too) -> memorisation
     (cause 2) confirmed.
   Doubt: R3 gives no number for "dev flat". D reads it as its own recomputed normal pooled-5 gain < 3.0 and prints both gains and the loss ratio, so a
   reader can overrule it. "Gain" in R1 is oracle pooled-5 at 10M minus oracle pooled-5 at 3M.

EmbeddingGemma (frozen, the same for both) is loaded once and shared; its states are computed once per batch and reused for both models and every knockout.
`ledger.py` is never changed. Before any model code: `caps.apply(caps.json)`; it asserts `N_REG == 36` (prints `N_REG 36`) and checks that a `run()` output
has register tokens `[B, 36, d]` (prints it): the in-run proof that G1 had the 36-slot fix. The checkpoint's chars must equal `charvocab.json`.
bf16 autocast on cuda exactly as train.py's eval; fp32 on CPU (a few rows may differ from G1's bf16 numbers; the report states the difference).

## Run A: on the Mac (preferred by the roadmap)
Code: this repo at commit `612f5c5b01` (custom_io), with ONE file replaced: `custom_io/g8a/caps.py` <- the overlay (git commit `e9125e9013`, file
`g8b/overlay/custom_io/g8a/caps.py`). Check `shasum -a 256 custom_io/g8a/caps.py` = `3da2dfbb0ddde64f0b4a263ccc025a01e70ca35c7c69fd9e9fdbb9c2d2325f78`
(the repo's own caps.py is the old 9-register one). Python with torch and numpy and `transformers >= 5.19` (EmbeddingGemma 2 needs it).

Copy from the PC (C:\Users\benja\custom-io\work\...) to the Mac, keeping this shape:

    g1d/
      src/custom_io/                    (the repo's custom_io at 612f5c5b01 + the overlay caps.py; or the PC folder src-8ag\custom_io)
      g1diag.py                         (this folder)
      ckpt3.pt     <- work\results\8aG1d-pc\8aG1d-3M-s400\B2\checkpoint.pt
      ckpt10.pt    <- work\results\8aG1f-pc\8aG1f-10M-s400\B2\checkpoint.pt
      RESULT3.json <- work\results\8aG1d-pc\8aG1d-3M-s400\B2\RESULT.json      (optional, for the comparison line)
      RESULT10.json<- work\results\8aG1f-pc\8aG1f-10M-s400\B2\RESULT.json     (optional)
      pool/dev/                         <- work\g8a\pools\p10-rung30-s400-a64\dev\          (the whole folder: six .jsonl files)
      pool/charvocab.json               <- work\g8a\pools\p10-rung30-s400-a64\charvocab.json
      pool/caps.json                    <- work\g8a\pools\p10-rung30-s400-a64\caps.json
      train-sample.jsonl                <- made on the PC (below); the 1.4M-row train.jsonl is NOT copied
      eg2/                              <- C:\Users\benja\eg2   (the EmbeddingGemma folder)

Make the train sample on the PC (pure python, no torch, about a minute; reads train.jsonl once; deterministic):

    set PYTHONUTF8=1
    "C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe" g1diag.py --train C:\Users\benja\custom-io\work\g8a\pools\p10-rung30-s400-a64\train.jsonl --sample-only C:\Users\benja\custom-io\work\g1diag-train-sample.jsonl

(2,000 web + 2,000 skill rows, ~1-2 MB.) On the Mac, `--train train-sample.jsonl` makes the same sample again from it (it already holds exactly 2,000 per group).

Run (from `g1d/`; first a quick debug with `--max-rows 100 --out out-debug`, then without it):

    export CUSTOM_IO_EG2=$PWD/eg2 PYTHONUTF8=1
    python g1diag.py --src src --data pool --train train-sample.jsonl --ckpt3 ckpt3.pt --ckpt10 ckpt10.pt \
        --result3 RESULT3.json --result10 RESULT10.json --out out --device cpu

(`--device auto` also works.) Read `out/G1DIAG.md` first, then `out/g1diag.json`.
Selftest of the Mac setup (no checkpoints, no EmbeddingGemma, seconds): `python g1diag.py --src src --selftest`.

Expected CPU time (an estimate, not measured on the real model): on the 4-vCPU box used to build it, a 3M-size model (d 256, blocks 2) needs 11 s per 128-row
batch of 150-char prompts and the 10M-size (8 blocks) 34 s; a loss batch of 64 takes 9.5 s / 29 s. The work: dev eval 6,200 rows x 2 models (each run twice:
candidates + the generate() self-check) about 45 min; 9 knockouts on 1,360 in_dist rows about 30 min; train loss 4,000 rows about 40 min; dev loss 6,040 rows
about 50 min; EmbeddingGemma (271M parameters, about 137M of them in the transformer) once per row for about 16,000 row-encodes, about 10-25 min. Plan for
roughly 3 hours on such a CPU, 1.5 to 4 hours on a laptop; memory about 3 GB (EmbeddingGemma fp32 1.1 GB). Use `--max-rows` to see the speed first.

## Run B: on the PC as insert 47-g1diag.txt (GPU, minutes)
Put `g1diag.py`, `g1diag.cmd` and `install_d.ps1` in one folder on the PC and run `powershell -ExecutionPolicy Bypass -File install_d.ps1`. It checks the
src-8ag hashes (caps.py 3DA2DFBB...5F78, ledger.py 0418BFE7...6733, evalx.py 35887EC4...0937), both checkpoints, both RESULT.json files and the pool files,
copies `g1diag.py` to `custom-io\g1diag\` and `g1diag.cmd` to `custom-io`, runs `g1diag.py --selftest` on the CPU (CUDA_VISIBLE_DEVICES=-1) from src-8ag, then
writes `WORK\insert\47-g1diag.txt` (`cmd: g1diag.cmd` / `hours: 3`) and logs one line to `q8aPost-waiter.log`. Already installed: exit 0. It deletes nothing.
The waiter runs `g1diag.cmd` alone at its next check point (foreground, exit code = python's); output in `WORK\results\8aG1diag\`, log `WORK\q8aG1diag.log`.
Needs the GPU free (the waiter makes sure no runner is active) and EmbeddingGemma at `C:\Users\benja\eg2`.
