# Gate G1 (10 Oct 2026, spec addendum Q): start 10M s401 now, beside 10M s400, and watch the shared GPU.
# 10M s400 B2 runs at 6.24 s per update with the GPU 23% busy (6.1 GB used), so the card has room for a second run.
# This script starts queue 8aG1s401 with the same command q8aG1s401_wait.ps1 would use, then stops the s401 TRAINING processes
# (never its runner, never s400) if either rule below trips. The runner then ends normally, clears its GPU-BUSY line, and
# q8aG1s401_wait.ps1 (still waiting) reruns s401 after s400, which is the original plan.
#   Rule 1 (spill): the G1 training processes' shared GPU memory passes 1 GB on 3 checks in a row (60 s apart).
#   Rule 2 (slowdown): any 500-update stretch of s400 B2 that starts after s401 began takes more than 5,000 s (1.6x its 3,121 s alone).
# Every call of a function that returns a list is wrapped in @(): PowerShell 5.1 unrolls a one-item list, and .Count is then empty.
# Started detached, so it outlives the ssh session. It stops nothing else and deletes nothing.
$WORK = 'C:\Users\benja\custom-io\work'
$SRC  = 'C:\Users\benja\custom-io\src-8ag'
$LOG  = "$WORK\q8aG1share-watch.log"
$B2   = "$WORK\results\8aG1f-pc\8aG1f-10M-s400\B2"
$J401 = "$WORK\results\8aG1s401-pc\8aG1s401-10M-s401"
function Say($m) { "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET $m" | Add-Content -Encoding ascii $LOG }
function Trainers($tag) { @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -like "*$tag*" -and $_.CommandLine -notlike '*local_runner*' }) }
function Runner401 { @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -like '*local_runner*' -and $_.CommandLine -like '*queue_local\8aG1s401*' }).Count -gt 0 }
function SharedMiB($procs) {
  $s = @((Get-Counter '\GPU Process Memory(*)\Shared Usage' -ErrorAction SilentlyContinue).CounterSamples)
  $t = 0.0
  foreach ($x in $s) { foreach ($p in $procs) { if ($x.InstanceName -like "pid_$($p.ProcessId)_*") { $t += $x.CookedValue } } }
  [math]::Round($t / 1MB, 1)
}
function TrainLines($dir) {
  $f = "$dir\stdout.txt"
  if (-not (Test-Path $f)) { return @() }
  @(Select-String -Path $f -Pattern '"event": "train"' -SimpleMatch | ForEach-Object { try { $_.Line | ConvertFrom-Json } catch { } })
}
function Gpu { (& nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>$null) -join ' ' }

Say "watcher started (pid $PID)"
if (Test-Path "$WORK\STOP") { Say 'WORK\STOP exists: s401 NOT started'; exit }
if (Runner401) { Say 'an 8aG1s401 runner is already running: nothing to do'; exit }
if (Test-Path "$J401\RESULT.json") { Say '10M s401 already has RESULT.json: nothing to do'; exit }
if (Test-Path "$B2\RESULT.json") { Say 's400 B2 already finished: rule 2 has no baseline, s401 NOT started (the waiter runs it after s400)'; exit }
if (-not (Test-Path "$SRC\custom_io\queue_local\8aG1s401-pc.txt")) { Say 'queue file 8aG1s401-pc.txt missing: NOT started'; exit }
if ((Get-FileHash "$SRC\custom_io\g8a\caps.py").Hash -ne '3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78') { Say 'caps.py hash wrong: NOT started'; exit }
$base = SharedMiB @(Trainers '8aG1f-10M-s400')
$lines0 = @(TrainLines $B2)
$S0 = if ($lines0.Count) { [int]$lines0[-1].step } else { 0 }
Say "before s401: s400 B2 at update $S0, s400 shared GPU memory $base MiB, GPU $(Gpu)"
if ($base -gt 700) { Say 's400 already uses over 700 MiB of shared GPU memory: s401 NOT started'; exit }

Set-Content -Encoding ascii 'C:\Users\benja\custom-io\q8aG1s401_run.cmd' -Value @(
  '@echo off',
  'set PYTHONUTF8=1',
  'set PYTHONUNBUFFERED=1',
  'cd /d C:\Users\benja\custom-io\src-8ag',
  'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe -m custom_io.local_runner run --work C:\Users\benja\custom-io\work --queue custom_io\queue_local\8aG1s401-pc.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt >> C:\Users\benja\custom-io\work\q8aG1s401.log 2>&1')
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='cmd.exe /c C:\Users\benja\custom-io\q8aG1s401_run.cmd'}
Say "started 8aG1s401 beside s400 (ReturnValue $($r.ReturnValue), cmd pid $($r.ProcessId))"

$t0 = Get-Date; $hot = 0; $seen = $false; $gone = 0; $k = 0
while ($true) {
  Start-Sleep -Seconds 60
  $k++
  $t401 = @(Trainers '8aG1s401-10M-s401')
  if ($t401.Count) { $seen = $true; $gone = 0 } else { $gone++ }
  if (Test-Path "$J401\RESULT.json") { Say '10M s401 finished: watcher done'; exit }
  if (-not $seen -and ((Get-Date) - $t0).TotalMinutes -gt 30) { Say 's401 training never appeared in 30 min: watcher done (see q8aG1s401.log)'; exit }
  if ($seen -and $gone -ge 10) { Say 's401 training gone for 10 min without RESULT.json: watcher done (see q8aG1s401.log)'; exit }
  if (-not $t401.Count) { continue }
  $all = @($t401) + @(Trainers '8aG1f-10M-s400')
  $sh = SharedMiB $all
  if ($sh -gt 1024) { $hot++ } else { $hot = 0 }
  $why = $null
  if ($hot -ge 3) { $why = "rule 1: G1 shared GPU memory $sh MiB on 3 checks in a row" }
  if (-not $why -and -not (Test-Path "$B2\RESULT.json")) {
    $tl = @(TrainLines $B2 | Where-Object { [int]$_.step -ge $S0 + 500 })
    for ($i = 1; $i -lt $tl.Count; $i++) {
      $d = [double]$tl[$i].elapsed - [double]$tl[$i - 1].elapsed
      if ($d -gt 5000) { $why = "rule 2: s400 B2 updates $($tl[$i - 1].step)-$($tl[$i].step) took $([math]::Round($d)) s"; break }
    }
  }
  if ($k % 30 -eq 1) {
    $a = @(TrainLines $B2); $b = @(TrainLines "$J401\B2")
    Say "check: shared $sh MiB, GPU $(Gpu), s400 B2 update $(if ($a.Count) { $a[-1].step } else { '-' }), s401 B2 update $(if ($b.Count) { $b[-1].step } else { '-' })"
  }
  if ($why) {
    Say "${why}: stopping the s401 training processes (the runner ends, and q8aG1s401_wait.ps1 reruns s401 after s400)"
    foreach ($p in $t401) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
    Say "stopped: $(($t401 | ForEach-Object { $_.ProcessId }) -join ', ')"
    exit
  }
}
