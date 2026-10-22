# PC job: Bid C load-gate record on BensPC (step 1 of the gate), $0, CPU only

**What it does:** makes the one record that load-gate check 1 needs. It is the eval of the C2b parent **s200** on the first 64 rows of **C2 dev** (never the C2 test; addendum A4), made with the unmodified code path (no caps applied). It trains nothing, uses no GPU and costs nothing. It takes a few minutes on CPU.

**Code:** branch `claude/bidc-calibration-drafts` at **e0d65adb6** (PR BenjaminHannan/learner#95; the final blocking-only review is clean, so the code counts as shipped).

**Run-card conditions (coordinator 10-22), which hold for this step AND for every later gate step (the P_0 `--record-eval` and the gate `run`):**
- Everything runs on **BensPC**, from **the same script below** (`bidc-benspc.ps1`), with **no Windows update in between**. Pause Windows Update until the gate has run. `platform.platform()` includes the Windows build, and a changed build makes check 3 REFUSED for good.
- The maths-library environment is set identically by that script for every step (block below). Do not run any gate step from another shell or script.

```powershell
# bidc-benspc.ps1  (one script for every Bid C gate step; pass the step name as the first argument)
param([Parameter(Mandatory=$true)][ValidateSet('record-c2b','record-p0','gate')] [string]$Step)
$ErrorActionPreference = 'Stop'
$env:OMP_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'; $env:MKL_CBWR = 'COMPATIBLE'    # identical for every step
Remove-Item Env:DNNL_MAX_CPU_ISA -ErrorAction SilentlyContinue
$Src  = 'C:\Users\benja\custom-io\src-bidc'          # a clean copy of claude/bidc-calibration-drafts at e0d65adb6
$Work = 'C:\Users\benja\creative\bidc'               # gate records and reports
$C2B  = 'C:\Users\benja\creative\ckpt\B2_s200.pt'    # the raw C2b parent s200 (CONFIRM this path; c2b ran with --ckpt ~/creative/ckpt/B2_s$S.pt)
Set-Location $Src
if ((git rev-parse HEAD) -ne 'e0d65adb6...') { }     # replace with the full hash; the script must refuse any other commit
New-Item -ItemType Directory -Force -Path $Work | Out-Null
switch ($Step) {
  'record-c2b' { python -m creative.bidc_load_gate record --ckpt $C2B --out "$Work\C2B_s200_RECORD.pt" --rows creative/data/c2/dev.jsonl }
  'record-p0'  { throw 'Calibration step: P_0 is trained with custom_io.train --caps custom_io/caps/caps-bidc.json --record-eval; it needs the coordinator''s calibration ruling first.' }
  'gate'       { throw 'Runs only after P_0 exists: python -m creative.bidc_load_gate run --c2b-parent ... --recorded ... --bidc-parent ... --bidc-recorded ... --report ...' }
}
```

**Now run only:** `.\bidc-benspc.ps1 record-c2b`. Before running, fill in the full commit hash check, so the script refuses any other commit.

**Send back:** the file `C2B_s200_RECORD.pt` (or its sha256), the console output, and `git rev-parse HEAD`. Check 1 itself runs later, in the gate run, from the same script.

**Not in this job:** training P_0 (calibration) and the gate run. Both need the coordinator's gate packet ruling first.
