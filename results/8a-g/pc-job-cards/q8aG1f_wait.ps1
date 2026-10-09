# Gate G1 (9 Oct 2026): wait until the 8aG1e queue runner has exited, then start queue 8aG1f (the two 10M jobs).
# Started detached, so it outlives the ssh session. It stops nothing; it only moves WORK\STOP and starts the next queue.
$WORK = 'C:\Users\benja\custom-io\work'
$SRC  = 'C:\Users\benja\custom-io\src-8ag'
$JOBS = 'C:\Users\benja\pc-jobs'
$LOG  = "$WORK\q8aG1f-waiter.log"
function Say($m) { "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET $m" | Add-Content -Encoding ascii $LOG }
function Running($pat) { @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -like "*$pat*" }).Count -gt 0 }

Say "waiting for the 8aG1e runner to exit (waiter pid $PID)"
while (Running '8aG1e-pc.txt') { Start-Sleep -Seconds 60 }
Start-Sleep -Seconds 30
if (Running '8aG1f-pc.txt') { Say '8aG1f already running: nothing to do'; exit }
if (-not (Test-Path "$SRC\custom_io\queue_local\8aG1f-pc.txt")) { Say 'queue file 8aG1f-pc.txt missing: NOT started, NEEDS ATTENTION'; exit }
if ((Get-FileHash "$SRC\custom_io\g8a\caps.py").Hash -ne '3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78') { Say 'caps.py hash wrong: NOT started, NEEDS ATTENTION'; exit }

$stamp = Get-Date -Format 'yyyyMMdd-HHmm'
if (Test-Path "$WORK\STOP") { Move-Item "$WORK\STOP" "$WORK\STOP.used-$stamp" }
Set-Content -Encoding ascii 'C:\Users\benja\custom-io\q8aG1f_run.cmd' -Value @(
  '@echo off',
  'set PYTHONUTF8=1',
  'set PYTHONUNBUFFERED=1',
  'cd /d C:\Users\benja\custom-io\src-8ag',
  'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe -m custom_io.local_runner run --work C:\Users\benja\custom-io\work --queue custom_io\queue_local\8aG1f-pc.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt >> C:\Users\benja\custom-io\work\q8aG1f.log 2>&1')
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='cmd.exe /c C:\Users\benja\custom-io\q8aG1f_run.cmd'}
Say "started 8aG1f (ReturnValue $($r.ReturnValue), cmd pid $($r.ProcessId))"

$tpl = 'C:\Users\benja\custom-io\g1f.template.md'
if (Test-Path $tpl) {
  (Get-Content $tpl) -replace '@STARTED@', "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET" | Set-Content -Encoding ascii "$JOBS\g1f.md"
  New-Item -ItemType Directory -Force "$JOBS\done" | Out-Null
  if (Test-Path "$JOBS\g1e.md") { Move-Item -Force "$JOBS\g1e.md" "$JOBS\done\" }
  Say 'installed pc-jobs\g1f.md and moved g1e.md to done'
}
