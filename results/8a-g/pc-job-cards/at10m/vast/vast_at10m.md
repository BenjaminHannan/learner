# 8aAT10M on a rented Vast.ai RTX 5090 (kit; nothing here has been launched)

The agent model (B3AT, arm AT), rung 10M, seed 400, queue `8aAT10M`, job `8aAT10M-10M-s400`: the PC job moved to a rented card. The training code is `custom_io` at commit
`6e72a5fae514a343c217c4d95cde37bc3b587c8e` (branch `claude/project-thread-emwjvn`), untouched. Same pool (`p10-rung30-s400-a64-L`), `caps_b3g2.json`, frozen EmbeddingGemma
(`eg_embed`), same job flags as `8aAT10M-pc.txt`. Expected trained parameters: 9,824,546 (checked on the CPU from the fetched commit by `at10mcheck.py`).

Files here: `at10m_box.sh` (runs on the box), `vast.py` (runs where you are: search / create / status / tail / waitfor / collect / collectck / destroy / credit), `selftest.sh`
(offline checks), this file. Built from `custom_io/box/{vast.py,box.sh,gx_box.sh,ck_export.sh}` on `claude/project-thread-x2cm2v` (that branch is not modified).
`vast.py` never reads or prints a key (the proxy adds it); it is run from this folder.

## What the box does (stages print `=== STAGE name <time>`)
1. `setup`: pip (transformers 5.17.0, pyarrow, numpy ...). 2. `code`: fetches exactly commit 6e72a5fae5 (sparse, `custom_io` only) and checks nine pinned files (the list in
`install_at10m.ps1`): `g8a/caps.py` = `433475405AE7...F62D3`, `g8a/caps_b3g2.json` = `EE551D3AAC...D7ED4` (the caps file is read straight from the commit; the PC's `b3-inputs` copy has this same hash).
3. `gemma`: EmbeddingGemma 2 at its pinned revision into `/job/eg2`, then `python -m custom_io.models.eg check cuda`. 4. `skills`: the 200k seed-1 skills curriculum twice (dev 40 and
dev 200 per cell) with the FULL-BUILD manifest hash check, as `box.sh`. 5. `data`: `data-pool-8b` at 12d30d0ce9 (own72/web manifests, panel index, `cloze_long.py`, whose sha256 `FF6A2E12...8CC9` is checked) and the tip of `claude/8a-own-data`,
then `custom_io.g8a.get_data ... --expect-manifest-sha e8f32daf...0763b0` (the PC's `8a-data` line): FineWeb-Edu shard 0 (2.15 GB) from Hugging Face, web slices rebuilt and hash-checked. 6. `train`:
the PC's `g8a` line, `custom_io.g8a.job --rung 10M --seed 400 --arms AT --b2-extra '{"eg_embed": true}' --cloze-long <cloze_long.py> --caps-file <caps_b3g2.json> --accum AT=$ACCUM`,
with the prefix `local_runner` adds (`--work --local --out --skills --big-data --data8a`). Git steps have timeouts and 4 tries; every wait prints a line; a `TICK` line every 5 minutes shows stage,
uptime, the last train line, the data folder sizes and the GPU. Any failure prints `CIO-FAIL <why>` and the container waits `FAIL_SLEEP` (billed) so you can read it: destroy it.

Env knobs (`create --env "NAME=VALUE ..."`; no spaces inside a value):

| name | default | meaning |
|---|---|---|
| `ACCUM` | 64 | micro-batches per 256-row update (the PC value; a guess, see below) |
| `OOM_DOUBLE` | 1 | on a CUDA out-of-memory death restart with ACCUM doubled (64, 128, 256), as the PC card's `on_spill`; the pool is reused. `0` = stop instead |
| `MAXH` | 40 | hard wall-clock stop, hours since the box started (setup included). Nothing is saved when it fires (see Checkpoints), so set it above the longest run you would accept |
| `PROJ_CAP_USD` | 70 | speed guard cap. **The weekly cap in SPEND.md is $50: pass `PROJ_CAP_USD=50` unless Ben says otherwise** |
| `GUARD_STEP` / `STEPS` / `EXTRA_H` | 1000 / 24000 / 1.5 | guard reads the train line at step >= GUARD_STEP; 24,000 updates at 10M; hours the final evals (chain-5, lesions) add to the projection (a guess) |
| `EXPORT_CK` / `PACE` | 1 / 100 | after the result is printed, print `AT/checkpoint.pt` in 3 MB parts (about 40 MB, about 25 min); `0` skips |
| `TFVER`, `END_SLEEP`, `FAIL_SLEEP` | 5.17.0, 14400, 14400 | transformers version; seconds the box stays up (billed) after the end / a failure |
| `DPH` | (set by `--dph`) | dollars per hour of this offer, for the guard |

How to pick ACCUM. 64 is the PC's memory guess for a 16 GB card (it is B3G2-10M's value). A 5090 has 32 GB, so 64 should fit, but nothing measured the agent model (up to 17 turns per row; the PC
card says it "may need more"). With `OOM_DOUBLE=1` a too-small value costs a restart (the pool is reused, so a few minutes of lost training start-up if it dies early, more if a long
row hits late). A smaller ACCUM (32, 16) is faster per update but is untested: only use it if Ben has a measured `peak_mem_mib` from AT-1 (`RESULT.json` of 8aAT; if peak is under ~12 GB at accum 32, 32 fits in 32 GB).
The update is 256 rows either way, so the training result does not depend on ACCUM (up to floating point).

## Speed guard
`guard.py` (written to `/job` by the box) reads the first `"event": "train"` line with step >= 1000 (train.py prints one every 500 steps) and prints
`GUARD step=1000 sec_per_update=.. train_total_h=.. up_h=.. projected_total_h=.. dph=.. projected_usd=.. cap_usd=..`; projected total = hours already up + remaining updates at that speed + `EXTRA_H`.
If `projected_usd > PROJ_CAP_USD` it prints `GUARD STOP ...` and stops the job (the processes are killed; the box then prints the partial result lines and `AT10M DONE rc=...`). It is checked once per
launch (a restart after an out-of-memory death is checked again). It needs `--dph` to be right: copy `dph_total` from `search`.

## Checkpoints: train.py cannot save mid-run or resume
Read from `custom_io/train.py` at 6e72a5fae5: `torch.save(... checkpoint.pt)` runs once, after the last update (line 237), inside `if args.out:`; there is no periodic save, no `--resume`, no
`--init`, and the optimizer state is never saved. `g8a/job.py` has no resume either (it only reuses a finished *pool*). So: **one uninterrupted run; a lost box = start over** (setup and data are the only
part that could be reused, and not across boxes). Nothing was changed in the training code. Consequences: `MAXH` and `GUARD STOP` stop the job with no model; the only things the box keeps are the
result files and, if the run finishes, the final `checkpoint.pt` (exported by `EXPORT_CK=1`; useful for `b3_readout.py --ckpt`; Gemma is not in it).

## Commands (Whole-model roadmap thread; run from this folder; all calls are Vast API calls through the proxy)
Before anything: **credit was $0.21 on 10-13 (and on 10-12)**. Ben must add credit first (estimate $20 to $65, see below). `python3 vast.py credit` must show it and no instances.
```
cd results/8a-g/pc-job-cards/at10m/vast
bash selftest.sh                                   # offline: expect SELFTEST OK
python3 vast.py credit                             # credit and the list of running instances (expect none)
python3 vast.py search --gpu "RTX 5090" --n 8      # verified, on-demand, 1 GPU, GPU RAM >= 31000 MB (a 32 GB 5090 lists 32607), disk >= 100 GB,
                                                   # reliability >= 0.98, CUDA >= 12.8, down >= 300 Mbit, >= 8 cores, cheapest first, Japan dropped
                                                   # (add --exclude-geo "" to keep Japan; take it only if a box there is shown to work)
```
Pick the cheapest row with `inet_down` >= 400, `cpu_cores_effective` >= 16 and enough `cpu_ram` (the pool build and caps report are CPU work). Write the SPEND.md row (below), then:
```
python3 vast.py create --offer <id> --dph <dph_total> --label at10m --env "ACCUM=64 PROJ_CAP_USD=50 MAXH=40"
#   prints {"success": true, "new_contract": <INSTANCE_ID>, ...}; --disk defaults to 120 GB container disk
python3 vast.py status --id <INSTANCE_ID>          # every 2 min until actual_status is running (a few minutes; the image is pulled)
python3 vast.py tail --id <INSTANCE_ID> --grep "STAGE|CIO-FAIL|GUARD|AT10M|MAXH|TICK" --n 12     # every 10 min through setup and data, then every 30 to 60 min
python3 vast.py waitfor --id <INSTANCE_ID> --max-min 110   # optional: polls every 2 min, returns on a finished job or a failure; keep each watcher under 2 h
```
What to see, in order: `CIO START`, `AT10M START accum=...`, `STAGE code`, `STAGE gemma`, `STAGE skills`, `STAGE data` (the long one: shard download, slice rebuild, then the pool and caps
report happen inside `STAGE train` before the first train line), `AT10M TRAIN START`, a `TICK` with `"event": "train", "step": 500`, then **one `GUARD ...` line** about 10 to 40 minutes after
training starts (step 1000). If it says `GUARD STOP`, stop here (abort rule 1). Also read it yourself: `sec_per_update`, `projected_total_h`, `projected_usd` go into SPEND.md.
When `AT10M RESULT PRINTED` shows:
```
python3 vast.py collect --id <INSTANCE_ID> --out <RESULTS_ROOT>/8aAT10M-vast      # decodes the result block, checks its sha256; prints {"8aAT10M-vast": "ok"}
python3 vast.py collectck --id <INSTANCE_ID> --out <RESULTS_ROOT>/8aAT10M-vast --max-min 60   # optional, EXPORT_CK=1: checkpoint.pt (about 14 parts, about 25 min)
```
Check `<RESULTS_ROOT>/8aAT10M-vast/8aAT10M-10M-s400/`: `rc.txt` says `rc=0`; `box.json` has `arms.AT.rc` 0; `AT/RESULT.json` has `"status": "ok"`, `n_params` 9824546, `steps` 24000.
Run `collect` right after `AT10M RESULT PRINTED` (the log API returns at most the last 20,000 lines, and about 8,400 lines of checkpoint parts follow per 3 MB part, so the first
print is buried after about two parts); the result is printed again at the very end of the checkpoint export, so a late `collect`/`collectck` finds it too. If `collect` says `sha-mismatch`, read again. Then:
```
python3 vast.py destroy --id <INSTANCE_ID>         # prints {"destroy": true} and {"still_listed": false}
python3 vast.py credit                             # expect no instance rows; note the credit for SPEND.md
```
Confirm `/instances/` shows 0 (the credit command lists them). If `still_listed` is true, destroy again and re-check. Never leave the box to `END_SLEEP`.

## SPEND.md (`/mnt/project-files/vast/SPEND.md`)
Before create: add the Boxes row: `box <INSTANCE_ID after create, or "pending"> | 8aAT10M (agent model, 10M, seed 400) | 1 x RTX 5090 (<offer id>, <geolocation>) | <start ET> | | est. = 1 (setup+data)
+ 24000 x sec_per_update/3600 + 1.5 evals) x dph (before the guard: "unmeasured, cap $<PROJ_CAP_USD>") | |`, and a Credit row (`python3 vast.py credit`, ET time). The weekly cap is $50
(week Monday 12:00 AM to Sunday 11:59 PM ET): if the estimate would pass it, ask Ben before create. After the GUARD line: replace the estimate with the measured projection. After destroy: fill
Destroyed (ET), Actual (credit before minus credit after, or the Vast invoice) and Week total.

## Abort rules (any one: stop, destroy, write it in SPEND.md, tell Ben)
1. `GUARD STOP` (the box already stopped the job): destroy. Do not raise the cap on your own; Ben decides.
2. Stall in the data step: `STAGE data` (or `skills`, `gemma`) for more than 30 minutes with no growth in the TICK `data8a=` / `shard=` MB and no new line, or any `CIO-FAIL` line: destroy and re-rent a different
   host (another `search` row, different country). A box once stalled silently after a failed git fetch; here fetches time out and print `retry k/4 failed`, but the rule stays.
3. No `STAGE train` line 90 minutes after create, or `status` shows `exited`/`loading` for 20 minutes: destroy, re-rent.
4. Two out-of-memory restarts that reach ACCUM=256 and still die, or a Traceback in the TICK line, or `AT10M JOB END rc=` not 0 without a GUARD/MAXH line: read the tail, report, destroy.
5. Total spend passing the SPEND.md cap, or the 30 minutes in rule 2 repeated on the second box: stop renting and ask Ben.
A `MAXH` stop also ends with no model: it is a cost cap, not a plan.

## PC side: when the box is running, the PC must not also run it
The waiter lists `WORK\insert` once and re-reads each file's content when it reaches it, so **overwrite `16-at10m.txt` in place** (same file name; do not rename or delete it) after the box has printed
its first `GUARD` line (the run is real) and before the waiter reaches that job. Over ssh, as one PowerShell command (stamp = `yyyyMMdd-HHmm`):
```
$f='C:\Users\benja\custom-io\work\insert\16-at10m.txt'; $s=(Get-Date).ToString('yyyyMMdd-HHmm'); Copy-Item $f "$f.vast-$s"; Set-Content -Encoding ascii -Path $f -Value 'cmd: at10m_skipped.cmd'; Get-Content $f; dir "$f*"
```
Expected: the file reads `cmd: at10m_skipped.cmd` and `16-at10m.txt.vast-<stamp>` holds the original four lines (`queue: 8aAT10M`, `src: src-at`, `caps: ...`, `card: at10m.template.md`). Note: `at10m_skipped.cmd` echoes
"was gated off by at10m_gate.ps1" whatever the reason; the true reason is the `.vast-<stamp>` file. If the gate (`15-at10mgate`) already turned 16 into a no-op (`16-at10m.txt.gated-<stamp>` exists), the run is not wanted: do not rent. If the waiter has
already started 16 on the PC, do not rent (never two copies). If the box fails and the PC should run it after all, copy `16-at10m.txt.vast-<stamp>` back over `16-at10m.txt` (in place) before the waiter reaches it.

## How the result comes back and is read the same way
`collect` unpacks to `<RESULTS_ROOT>/8aAT10M-vast/8aAT10M-10M-s400/` with the PC's layout: `AT/RESULT.json` (the model's result: status, steps, steps_per_s, peak_mem_mib, final_eval, lesions, chain5,
extra evals, cap_hits), `RESULT.json` and `box.json` (job level, with `arms.AT.accum`, `rc`), `caps.json`, `caps_report.json`, `pool_MANIFEST.json`, `job.log`, `get_data.log`, `guard.out`, `oom.txt` (if any).
`AT/stdout.txt` is the **key lines only** (events `start`, `size`, `caps`, `cap_hits`, `train`, `quick_eval`, `done`, plus any Traceback / error lines): that is what `at10m_gate.py`
(the end-of-training `cap_hits` line without `"final"`) and the seconds-per-update read (`elapsed` of each `train` line, every 500 updates; `steps_per_s` in `RESULT.json`) need; the rest of the PC's stdout is not kept.
The PC's files are `WORK\results\8aAT10M*-pc\8aAT10M-10M-s400\AT\RESULT.json`; this run's is `...\8aAT10M-vast\8aAT10M-10M-s400\AT\RESULT.json`, so any reader that takes the RESULT.json path
(`b3_readout.py --b3 <path>`) reads it unchanged; give it `--ckpt <RESULTS_ROOT>/8aAT10M-vast/8aAT10M-10M-s400/AT/checkpoint.pt` if `collectck` brought the checkpoint. Record in the readout that the run was on a rented 5090, accum <value from
box.json>, transformers 5.17.0 (the PC uses its own `eg_site`; see below).

## What the dry run proved, and what only a real box can show
Proved here (no Vast instance was created): `bash -n`, `py_compile`; the fetches of commit 6e72a5fae5 (by full sha, sparse) and the data-pool commit work and the pinned hashes match; the CPU parameter check on the fetched
commit gives 9,824,546; the 200k skills curriculum builds in 1 min 38 s here and its manifest hashes match; the job accepts every flag of the box command and then waits for `data8a/READY.json`; the guard prints and stops correctly in unit tests
and the watcher kills a fake `python -m custom_io.train` process (and not itself); `emit` and `collect` round-trip a fake result (no `.pt`, sha checked), and the checkpoint parts round-trip through `collectck` byte for byte; read-only `credit` and `search` work.
Only a real box shows: pip and the 5090 driver / torch 2.11 cu128 pairing, the Hugging Face downloads (EmbeddingGemma, the 2.15 GB shard; rate limits), the web-slice rebuild time and hash equality there, the pool and caps-report time, GPU memory at ACCUM=64, the real
seconds per update, and whether transformers 5.17.0 gives the same EmbeddingGemma front as the PC's `eg_site` build (untested; the earlier rentals used it for the 3M GX jobs).
Setup estimate: about 30 to 50 minutes (previous rentals: 15 to 40 minutes for setup and data; this adds the 10M pool and caps report before the first update).
Cost: dph is about $0.47 now (cheapest verified 5090s on 10-13: US $0.44, Korea $0.47). Every 0.1 s per update is 0.67 h, about $0.31. Speed is unmeasured: the PC's 5070 Ti ran the plain 10M B2 at 0.156 updates/s (about 43 h).
SPEND.md's $50 to $65 estimate is unmeasured too; treat it as such until the GUARD line.

## Supplied by whom
Nothing is read from the PC. Everything comes from public GitHub branches (code `claude/project-thread-emwjvn` at the pinned commit, `claude/data-pool-8b`, `claude/8a-own-data`, `claude/project-thread-y0sxwe`) and Hugging Face (anonymous). Ben must supply Vast credit.
If a branch is deleted or rewritten, `fetch_sha` fails with `CIO-FAIL fetch-src-at` / `clone-dp` and nothing runs.
