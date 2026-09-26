# lis-319c registered result (BensPC): PASS — bar 0.98 saves more with safety held

Builder run 2026-09-25/26 on BensPC (RTX 5070 Ti, CUDA). Sealed code run
unmodified. Panel readpanel319c read ONCE with the lis-319 merged reader;
the same reads scored at both bars. Category counts only; no panel text
is quoted.

## Verdict: PASS

| Mark | Bar | Got (integers) | Verdict |
|---|---|---|---|
| S1 more saved: B saved_right | >= A's + 25 (= 138 + 25 = 163) | B 185/424 (A 138/424), +47 | PASS |
| S2 no less safe: B wrong_turns | <= A's + 1 (= 2) AND <= 3 of 239 | B 2 of 239 (A 1 of 239) | PASS |
| S3 no invention: B nofact_rows_with_save | <= 1 | 0 | PASS |

Proved-wrong clause (PASSMARKS): B wrong_turns (2) >= A wrong_turns (1) + 3 (= 4)
is FALSE, so 0.98 does not let in real errors the practice data hid.

## score_A.json (verbatim; same reads at T = 0.995)

{
 "rows": 239,
 "gold": 424,
 "R0": 326,
 "saved_right": 138,
 "held_right": 188,
 "saved_wrong": 1,
 "wrong_turns": 1,
 "parse_fail": 1,
 "threshold": 0.995,
 "ms_median": 1788.6,
 "per_kind": {
  "backref:R0": 39,
  "backref:gold": 59,
  "backref:saved_right": 2,
  "long_multi:R0": 219,
  "long_multi:gold": 291,
  "long_multi:saved_right": 101,
  "long_multi:wrong_turns": 1,
  "short:R0": 68,
  "short:gold": 74,
  "short:saved_right": 35
 },
 "gold_hist": 57,
 "R0_hist": 37,
 "gold_local": 367,
 "R0_local": 289
}

## score_B.json (verbatim; same reads at T = 0.98)

{
 "rows": 239,
 "gold": 424,
 "R0": 326,
 "saved_right": 185,
 "held_right": 141,
 "saved_wrong": 2,
 "wrong_turns": 2,
 "parse_fail": 1,
 "threshold": 0.98,
 "ms_median": 1788.6,
 "per_kind": {
  "backref:R0": 39,
  "backref:gold": 59,
  "backref:saved_right": 3,
  "long_multi:R0": 219,
  "long_multi:gold": 291,
  "long_multi:saved_right": 140,
  "long_multi:wrong_turns": 2,
  "short:R0": 68,
  "short:gold": 74,
  "short:saved_right": 42
 },
 "gold_hist": 57,
 "R0_hist": 37,
 "gold_local": 367,
 "R0_local": 289
}

(nofact_rows_with_save is absent from both files because the count is 0:
the scorer only emits nonzero counters. So S3 = 0 for A and 0 for B.
parse_fail = 1 in both arms comes from the same read, unaffected by bar.)

## Report only

- held_right: A 188, B 141 (of 326 found; B releases 47 more to save).
- per-kind saved_right A -> B: backref 2 -> 3 (of 59), long_multi 101 -> 140
  (of 291), short 35 -> 42 (of 74).
- Greedy R0 split (same reads, bar-independent): needs_history 37/57,
  other facts 289/367.
- Read ms median 1788.6 both arms (same reads scored twice).

## Seals, reader, independence

- BensPC tree root: `sha256sum -c
  artifacts/claude-lis319c-20260926/SEAL.sha256.txt` → PASSMARKS.md OK.
- `cd artifacts/claude-readpanel319c-20260926 && sha256sum -c
  SEAL.sha256.txt` → 5/5 OK (panel, label_B, adjudication, README, AUDIT).
- READER C:/Users/benja/lis319/work/run/merged/model.safetensors sha256
  e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76 — match.
- History: `claude_lis319_rows.py` → rows 239 with history 209.
- Panel read ONCE: `claude_lis319_read.py` → read 239 rows on cuda.
- The panel label files were never opened, printed or quoted. Only scorer
  counts were viewed. WORK/panel_reads.jsonl, WORK/panel_hist.jsonl and
  WORK/read.log were deleted on BensPC after scoring; nothing from the
  panel was copied back.

## Training, device, money

- Device: BensPC NVIDIA GeForce RTX 5070 Ti, cuda, greedy decode.
- No training, no downloads, no rental, $0.
- Panel read ms (239 turns): median 1788.6.

## Wall time per step

- Mac setup (fetch, full tree build builder-outbox + main on top, tree.tgz
  164 MB, slow scp restarted): ~21:14-21:41 local.
- BensPC stage (local copy of prior lis-319 tree, 40 KB update with current
  scripts + seals on top, seals, READER sha, WORK mkdir, rows): ~21:35-21:46
  EDT (rows 239 with history 209 at ~21:46).
- GPU wait: another job (rsn358a2 train) was active until ~21:50 EDT; read
  launched when nvidia-smi showed 0% util, 426 MiB, no compute processes.
- Read: launched ~21:50 EDT, `read 239 rows on cuda` by ~22:01 EDT
  (~11 min; a second job started mid-read, sharing the GPU, no CUDA error).
- Scores (CPU): A at ~22:02, B at ~22:03 EDT; WORK panel files deleted
  22:03 EDT; score files copied back to Mac 22:03-22:04.
- Total ~50 min, inside the 1 h cap.

## Deviations (env only; sealed code untouched)

1. Reused the lis-300 venv (torch 2.11.0+cu128) and the existing lis-319
   merged reader, as tasked; set PYTHONUTF8=1 (env only).
2. Full 164 MB tree.tgz upload over ssh was ~1 MB/min, so the BensPC tree
   was staged as a local copy of C:/Users/benja/lis319/tree with a 40 KB
   update (current scripts, claude-lis319c-20260926, readpanel319c) extracted
   on top; seals re-checked after (1/1 + 5/5 OK). Content equals
   builder-outbox + main on top for every file the task uses.
3. shasum absent on BensPC; seals checked with git-bash sha256sum -c (same
   file format), per the lis-319 fix.
4. Long GPU step launched with nohup + disown in git-bash (no setsid) and
   the ssh session kept alive past launch, per the lis-319 fix; native
   Windows paths passed to python.exe.
5. Mac free disk read 666 MiB-1.6 GiB during staging (other agents active);
   BensPC work needs no Mac disk beyond the 550-byte score files, so the run
   continued; /tmp tree cleaned after packing.
6. A second GPU job started mid-read; both shared the GPU to completion with
   no errors; read time ~11 min, median ms as scored.

## What it means (plain high-school English)

- Lowering the save bar from 0.995 to 0.98 saves 47 more facts (138 to 185)
  on the fresh sealed panel, while wrong saves go from 1 to 2 (limit 3) and
  invented saves stay 0. All three marks pass.
- It doesn't mean the gate is solved: even at 0.98 the reader still holds
  back 141 of 326 found facts to stay safe.
- It doesn't mean the test leaked: panel read once, seals checked first,
  same reads scored at both bars, only counts viewed.
