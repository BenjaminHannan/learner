# Gate G1 (9 Oct 2026, spec addendum I): after 10M s400 ends, run g1_futility.py; unless it says skip (exit 3), start queue
# 8aG1s401 (10M s401). Started detached, so it outlives the ssh session. It stops nothing.
$WORK = 'C:\Users\benja\custom-io\work'
$SRC  = 'C:\Users\benja\custom-io\src-8ag'
$JOBS = 'C:\Users\benja\pc-jobs'
$PY   = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$LOG  = "$WORK\q8aG1s401-waiter.log"
function Say($m) { "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET $m" | Add-Content -Encoding ascii $LOG }
function G1Runner { @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -like '*local_runner*' -and $_.CommandLine -like '*queue_local\8aG1*' }).Count -gt 0 }
function Ten400Done {
  foreach ($r in @(Get-ChildItem "$WORK\results\8aG1*-pc\8aG1*-10M-s400\RESULT.json" -ErrorAction SilentlyContinue)) {
    try { if ((Get-Content $r.FullName -Raw | ConvertFrom-Json).status -eq 'ok') { return $true } } catch { }
  }
  return [bool](Select-String -Path "$WORK\q8aG1f.log" -Pattern 'queue 8aG1f-pc done' -SimpleMatch -Quiet -ErrorAction SilentlyContinue)
}

Say "waiting for 10M s400 to finish (waiter pid $PID)"
while (-not (Ten400Done) -or (G1Runner)) { Start-Sleep -Seconds 60 }
Start-Sleep -Seconds 30
if (G1Runner) { Say 'a G1 runner is running again: nothing to do'; exit }

$check = & $PY 'C:\Users\benja\custom-io\g1_futility.py' 2>&1
$rc = $LASTEXITCODE
Say "futility check rc=$rc $check"
if ($rc -eq 3) { Say 'seed 400 gain difference at or below -1.0: 10M s401 skipped (spec addendum I). G1 is finished.'; exit }

if (-not (Test-Path "$SRC\custom_io\queue_local\8aG1s401-pc.txt")) { Say 'queue file 8aG1s401-pc.txt missing: NOT started, NEEDS ATTENTION'; exit }
if ((Get-FileHash "$SRC\custom_io\g8a\caps.py").Hash -ne '3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78') { Say 'caps.py hash wrong: NOT started, NEEDS ATTENTION'; exit }
if (Test-Path "$WORK\STOP") { Say 'WORK\STOP exists: NOT started, NEEDS ATTENTION'; exit }
Set-Content -Encoding ascii 'C:\Users\benja\custom-io\q8aG1s401_run.cmd' -Value @(
  '@echo off',
  'set PYTHONUTF8=1',
  'set PYTHONUNBUFFERED=1',
  'cd /d C:\Users\benja\custom-io\src-8ag',
  'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe -m custom_io.local_runner run --work C:\Users\benja\custom-io\work --queue custom_io\queue_local\8aG1s401-pc.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt >> C:\Users\benja\custom-io\work\q8aG1s401.log 2>&1')
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='cmd.exe /c C:\Users\benja\custom-io\q8aG1s401_run.cmd'}
Say "started 8aG1s401 (ReturnValue $($r.ReturnValue), cmd pid $($r.ProcessId))"

$tpl = 'C:\Users\benja\custom-io\g1s401.template.md'
if (Test-Path $tpl) {
  (Get-Content $tpl) -replace '@STARTED@', "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET" | Set-Content -Encoding ascii "$JOBS\g1s401.md"
  New-Item -ItemType Directory -Force "$JOBS\done" | Out-Null
  if (Test-Path "$JOBS\g1f.md") { Move-Item -Force "$JOBS\g1f.md" "$JOBS\done\" }
  Say 'installed pc-jobs\g1s401.md and moved g1f.md to done'
}
