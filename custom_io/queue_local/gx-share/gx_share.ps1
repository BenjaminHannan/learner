# Test GX seed 400 BESIDE gate G1's two 10M runs on BensPC (spec design/8a-gx-experts-2026-10-09.md addendum F; Ben 8:23 PM ET 10-10:
# "move that to the front of the queue"). One script, run once after Ben's go in the Mac chat, started detached so it outlives ssh:
#   1. sets up src-8gxs from post-g1-in\gxs.zip (CPU checks only: caps.py hash, test_moe's 8 machine-independent tests, the memory cap is in train.py);
#   2. starts queue src-8gxs\custom_io\queue_local\gx-share\8aGXs400-pc.txt only if G1 still runs, nothing else holds GX, and 3,500 MiB are free;
#   3. watches, and stops ONLY the GX processes (never G1, never a runner) when a rule trips:
#      Rule 1 (memory): on 2 checks in a row (60 s apart), the python processes' shared GPU memory is more than 400 MiB above its level before
#              GX started, or the card's dedicated memory is above 16,000 MiB.
#      Rule 2 (G1 slowdown): a G1 B2 arm that is still training has gone more than 4,300 s since its last 500-update line (1.35x its 3,210 s
#              shared pace). It is checked while the stretch runs, so it fires before g1_share_watch.ps1's 5,000 s rule could stop G1 seed 401.
# After a stop, or if GX ends without an ok RESULT.json, the GX job folder is renamed aside (never deleted) once its runner has exited, so the
# post-G1 chain (q8aPost2_wait.ps1) runs GX seed 400 alone right after G1, as planned before. If GX ends ok, the chain's own 8aGXs400 launch
# finds RESULT.json in the same folder and skips the job. Every call that returns a list is wrapped in @() (PowerShell 5.1 unrolls one-item lists).
$CIO     = 'C:\Users\benja\custom-io'
$WORK    = "$CIO\work"
$IN      = "$CIO\post-g1-in"
$SRC     = "$CIO\src-8gxs"
$PY      = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$CAPS    = '3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78'      # caps.py of G1 and of the experts code
$Q       = '8aGXs400'
$QF      = "$SRC\custom_io\queue_local\gx-share\$Q-pc.txt"
$JOB     = "$WORK\results\$Q-pc\8aGX-3M-s400"
$LOG     = "$WORK\q8aGXshare-watch.log"
$G1JOBS  = @('8aG1f-10M-s400', '8aG1s401-10M-s401')
$G1B2    = @{ '8aG1f-10M-s400' = "$WORK\results\8aG1f-pc\8aG1f-10M-s400\B2"; '8aG1s401-10M-s401' = "$WORK\results\8aG1s401-pc\8aG1s401-10M-s401\B2" }
$LIMIT   = 4300       # Rule 2, seconds since a G1 B2 arm's last 500-update line
$NEED    = 3500       # MiB free on the card before GX may start (its cap 2,800 + its CUDA context + slack)
$UP      = 400        # Rule 1, MiB of shared GPU memory above the level before GX
$DEDMAX  = 16000      # Rule 1, MiB of dedicated memory on the 16,303 MiB card
$MOE8    = "import json; from custom_io.g8a import caps as CP; from custom_io.tests import test_moe as T; CP.apply(json.load(open(T.CAPS_G))); [t() for t in (T.test_shared_weights_identical, T.test_layer_matches_loop, T.test_gradients, T.test_checkpoint_same, T.test_sizes, T.test_bias_moves_only_in_training, T.test_training, T.test_report)]; print('ALL OK (8 of 9 tests)')"

function Stamp { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + ' ET' }
function Say($m) { "$(Stamp) $m" | Add-Content -Encoding ascii $LOG; "$(Stamp) $m" }
function Py { @(Get-CimInstance Win32_Process -Filter "Name like 'python%'") }
function Trainers($tag) { @(Py | Where-Object { $_.CommandLine -like "*$tag*" -and $_.CommandLine -notlike '*local_runner*' }) }
function ShareRunner { @(Py | Where-Object { $_.CommandLine -like '*local_runner*' -and $_.CommandLine -like '*gx-share*' }).Count -gt 0 }
function ChainGX { @(Py | Where-Object { $_.CommandLine -like '*local_runner*' -and $_.CommandLine -like "*queue_local\$Q*" -and $_.CommandLine -notlike '*gx-share*' }).Count -gt 0 }
function SharedMiB {
  $ids = @(Py | ForEach-Object { "pid_$($_.ProcessId)_" })
  $t = 0.0
  foreach ($x in @((Get-Counter '\GPU Process Memory(*)\Shared Usage' -ErrorAction SilentlyContinue).CounterSamples)) {
    foreach ($i in $ids) { if ($x.InstanceName -like "$i*") { $t += $x.CookedValue } }
  }
  [math]::Round($t / 1MB, 1)
}
function Card { $v = "$(& nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>$null)" -split ',\s*'; @{ util = [int]$v[0]; used = [int]$v[1]; total = [int]$v[2] } }
# The last line of an arm's stdout.txt if it is a 500-update train line: @{step; at}; else $null (evals, or nothing yet).
function LastTrain($dir) {
  $f = "$dir\stdout.txt"
  if (-not (Test-Path $f)) { return $null }
  $last = @(Get-Content $f -Tail 3 -ErrorAction SilentlyContinue | Where-Object { $_.Trim() }) | Select-Object -Last 1
  if (-not $last -or -not $last.StartsWith('{"event": "train"')) { return $null }
  try { $j = $last | ConvertFrom-Json } catch { return $null }
  @{ step = [int]$j.step; at = (Get-Item $f).LastWriteTime }
}
# Rule 2 for one G1 job: $null, or why it trips.
function Slow($job) {
  $dir = $G1B2[$job]
  if (Test-Path "$dir\RESULT.json") { return $null }                                           # B2 arm done
  $tr = @(Trainers $job | Where-Object { $_.CommandLine -like '*custom_io.train*' -and $_.CommandLine -like '*B2*' })
  if (-not $tr.Count) { return $null }                                                            # B2 arm not training now
  $lt = LastTrain $dir
  if (-not $lt) { return $null }
  if ($tr[0].CommandLine -match '--steps\s+(\d+)' -and $lt.step -ge [int]$Matches[1]) { return $null }   # training done, evals running
  $s = ((Get-Date) - $lt.at).TotalSeconds
  if ($s -gt $LIMIT) { return "rule 2: $job B2 has gone $([math]::Round($s)) s since update $($lt.step) (limit $LIMIT s)" }
  return $null
}
function OkResult($f) { try { return ((Get-Content $f -Raw | ConvertFrom-Json).status -eq 'ok') } catch { return $false } }
function MoveAside($why) {
  for ($t = 0; ($t -lt 15) -and (ShareRunner); $t++) { Start-Sleep -Seconds 60 }
  if (ShareRunner) { Say "the gx-share runner is still running 15 min after: GX folder NOT moved, NEEDS ATTENTION ($why)"; return }
  if (Test-Path $JOB) {
    $n = '8aGX-3M-s400.share-stopped-' + (Get-Date).ToString('yyyyMMdd-HHmm')
    Rename-Item -Path $JOB -NewName $n
    Say "renamed $JOB to $n ($why); the post-G1 chain runs GX seed 400 alone after G1"
  }
}
function CpuPy($dir, $pyargs) {
  $env:CUDA_VISIBLE_DEVICES = '-1'; $env:PYTHONUTF8 = '1'
  Push-Location $dir
  $out = @(& $PY @pyargs 2>&1 | ForEach-Object { "$_" })
  Pop-Location
  Remove-Item Env:\CUDA_VISIBLE_DEVICES
  return $out
}

Say "gx_share started (pid $PID)"
# 1. Setup (CPU only).
if (-not (Test-Path "$SRC\GXS-SETUP-OK.txt")) {
  if (-not (Test-Path "$IN\gxs.zip")) { Say "NEEDS ATTENTION: $IN\gxs.zip missing: GX NOT started"; exit 1 }
  if ((Test-Path $SRC) -and (@(Get-ChildItem $SRC -Force).Count -gt 0)) {
    $n = 'src-8gxs.failed-' + (Get-Date).ToString('yyyyMMdd-HHmm'); Rename-Item -Path $SRC -NewName $n; Say "old src-8gxs without a setup marker renamed to $n"
  }
  Expand-Archive -Path "$IN\gxs.zip" -DestinationPath $SRC
  if ((Get-FileHash "$SRC\custom_io\g8a\caps.py").Hash -ne $CAPS) { Say 'NEEDS ATTENTION: src-8gxs caps.py hash wrong: GX NOT started'; exit 1 }
  if (-not (Test-Path $QF)) { Say "NEEDS ATTENTION: $QF missing: GX NOT started"; exit 1 }
  if (-not (Select-String -Path "$SRC\custom_io\train.py" -Pattern 'CUSTOM_IO_MEM_CAP_MIB' -SimpleMatch -Quiet)) { Say 'NEEDS ATTENTION: train.py has no memory cap: GX NOT started'; exit 1 }
  $out = CpuPy $SRC @('-c', $MOE8)
  if (-not ($out -and ($out[-1] -match 'ALL OK'))) { Say "NEEDS ATTENTION: test_moe (8 tests) did not end ALL OK: GX NOT started. Last lines: $(($out | Select-Object -Last 3) -join ' | ')"; exit 1 }
  Set-Content -Encoding ascii "$SRC\GXS-SETUP-OK.txt" -Value @("caps.py $CAPS", 'test_moe 8 of 9 tests ALL OK (CPU)', (Stamp))
  Say 'src-8gxs set up: caps hash ok, memory cap present, test_moe 8 of 9 tests ALL OK'
}

# 2. Start, only if it still makes sense.
if (Test-Path "$WORK\STOP") { Say 'WORK\STOP exists: GX NOT started'; exit }
if (ShareRunner) { Say 'a gx-share runner already runs: nothing to do'; exit }
if (ChainGX) { Say 'the post-G1 chain already runs GX seed 400: nothing to do'; exit }
if (Test-Path "$JOB\RESULT.json") { Say "$JOB already has RESULT.json: nothing to do"; exit }
$g1 = @($G1JOBS | ForEach-Object { Trainers $_ })
if (-not $g1.Count) { Say 'no G1 training process runs: GX NOT started here (the post-G1 chain starts it)'; exit }
$c = Card
$free = $c.total - $c.used
$base = SharedMiB
Say "before GX: GPU $($c.util)% busy, $($c.used) of $($c.total) MiB used ($free free), shared $base MiB; G1 B2 at $(@($G1JOBS | ForEach-Object { $l = LastTrain $G1B2[$_]; if ($l) { "$_ update $($l.step)" } else { "$_ -" } }) -join ', ')"
if ($free -lt $NEED) { Say "only $free MiB free (needs $NEED): GX NOT started; it starts right after G1 as planned"; exit }
Set-Content -Encoding ascii "$CIO\q${Q}share_run.cmd" -Value @(
  '@echo off',
  'set PYTHONUTF8=1',
  'set PYTHONUNBUFFERED=1',
  "cd /d $SRC",
  "$PY -m custom_io.local_runner run --work $WORK --queue custom_io\queue_local\gx-share\$Q-pc.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt >> $WORK\q${Q}share.log 2>&1")
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = "cmd.exe /c $CIO\q${Q}share_run.cmd"}
Say "started GX seed 400 beside G1 (ReturnValue $($r.ReturnValue), cmd pid $($r.ProcessId)); log WORK\q${Q}share.log"

# 3. Watch.
$t0 = Get-Date; $seen = $false; $hot = 0; $k = 0
while ($true) {
  Start-Sleep -Seconds 60
  $k++
  if ((Test-Path "$JOB\RESULT.json") -and (OkResult "$JOB\RESULT.json")) { Say 'GX seed 400 finished ok beside G1: watcher done'; exit }
  $gx = @(Trainers '8aGX-3M-s400')
  if ($gx.Count) { $seen = $true }
  if (-not (ShareRunner)) {
    if (-not ((Test-Path "$JOB\RESULT.json") -and (OkResult "$JOB\RESULT.json"))) { MoveAside 'GX ended without an ok RESULT.json (see WORK\q8aGXs400share.log)' }
    exit
  }
  if (-not $seen) {
    if (((Get-Date) - $t0).TotalMinutes -gt 90) { Say 'GX training never appeared in 90 min (see WORK\q8aGXs400share.log): NEEDS ATTENTION' ; $t0 = Get-Date }
    continue
  }
  if (-not $gx.Count) { continue }                     # between steps of the runner
  $c = Card; $sh = SharedMiB
  if (($sh -gt $base + $UP) -or ($c.used -gt $DEDMAX)) { $hot++ } else { $hot = 0 }
  $why = $null
  if ($hot -ge 2) { $why = "rule 1: shared GPU memory $sh MiB (before GX $base), dedicated $($c.used) MiB, on 2 checks in a row" }
  if (-not $why) { foreach ($j in $G1JOBS) { $w = Slow $j; if ($w) { $why = $w; break } } }
  if ($k % 30 -eq 1) {
    $gl = LastTrain "$JOB\B2"
    Say "check: GPU $($c.util)% busy, $($c.used) MiB used, shared $sh MiB; GX update $(if ($gl) { $gl.step } else { '-' }); G1 B2 $(@($G1JOBS | ForEach-Object { $l = LastTrain $G1B2[$_]; if ($l) { "$_ $($l.step) at $($l.at.ToString('HH:mm'))" } else { "$_ -" } }) -join ', ')"
  }
  if ($why) {
    Say "${why}: stopping the GX processes only ($(($gx | ForEach-Object { $_.ProcessId }) -join ', '))"
    foreach ($p in $gx) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
    MoveAside $why
    exit
  }
}
