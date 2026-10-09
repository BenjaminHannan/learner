# Post-G1 chain on BensPC (9 Oct 2026, spec addendum K). After gate G1's last PC queue ends: test GX stage 1 (queue 8aGX, code
# src-8gx, Ben's "experts first"), then the 100M fit check part A (8aFC), then the G-PT 30M control (8aC30) unless B3 group 1
# is ready (WORK\B3-READY.txt). One queue at a time. WORK\STOP holds the chain (it never removes STOP). Started detached by
# install_post_g1.ps1, so it outlives the ssh session. It stops nothing and deletes nothing.
$CIO   = 'C:\Users\benja\custom-io'
$WORK  = "$CIO\work"
$SRC   = "$CIO\src-8ag"
$SRCGX = "$CIO\src-8gx"
$JOBS  = 'C:\Users\benja\pc-jobs'
$PY    = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$CAPS  = '3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78'
$LOG   = "$WORK\q8aPost-waiter.log"
function Now { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') }
function Say($m) { "$(Now) ET $m" | Add-Content -Encoding ascii $LOG }
function Runner { @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -like '*local_runner*' }).Count -gt 0 }
function G1Waiter { @(Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" | Where-Object { $_.CommandLine -like '*q8aG1*_wait.ps1*' }).Count -gt 0 }
function OkResult($glob) {
  foreach ($r in @(Get-ChildItem $glob -ErrorAction SilentlyContinue)) {
    try { if ((Get-Content $r.FullName -Raw | ConvertFrom-Json).status -eq 'ok') { return $true } } catch { }
  }
  return $false
}
# Free = no queue runner and no WORK\STOP at each of $mins one-minute checks in a row.
function Free($mins) {
  for ($n = 0; $n -lt $mins; $n++) {
    if ((Runner) -or (Test-Path "$WORK\STOP")) { return $false }
    Start-Sleep -Seconds 60
  }
  return $true
}
function WaitFree($why) {
  $k = 0
  while (-not (Free 5)) {
    if ($k % 360 -eq 0) { Say "waiting: $why (a queue runner or WORK\STOP is present)" }
    $k++; Start-Sleep -Seconds 60
  }
}
function Hold($flag, $why) {
  Say "HOLD, NEEDS ATTENTION: $why. The chain goes on when WORK\$flag exists."
  while (-not (Test-Path "$WORK\$flag")) { Start-Sleep -Seconds 60 }
  Say "WORK\$flag found: going on"
}
function MoveDone($pattern) {
  New-Item -ItemType Directory -Force "$JOBS\done" | Out-Null
  foreach ($c in @(Get-ChildItem "$JOBS\$pattern" -ErrorAction SilentlyContinue)) { Move-Item -Force $c.FullName "$JOBS\done\"; Say "moved pc-jobs\$($c.Name) to done" }
}
function Launch($q, $src) {
  $qf = "$src\custom_io\queue_local\$q-pc.txt"
  if (-not (Test-Path $qf)) { Say "queue file $qf missing: $q NOT started"; return $false }
  if ((Get-FileHash "$src\custom_io\g8a\caps.py").Hash -ne $CAPS) { Say "caps.py hash wrong in ${src}: $q NOT started"; return $false }
  if ((Runner) -or (Test-Path "$WORK\STOP")) { Say "a runner or STOP appeared: $q NOT started"; return $false }
  $cmd = "$CIO\q${q}_run.cmd"
  Set-Content -Encoding ascii $cmd -Value @(
    '@echo off',
    'set PYTHONUTF8=1',
    'set PYTHONUNBUFFERED=1',
    "cd /d $src",
    "$PY -m custom_io.local_runner run --work $WORK --queue custom_io\queue_local\$q-pc.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt >> $WORK\q$q.log 2>&1")
  $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="cmd.exe /c $cmd"}
  Say "started $q from $src (ReturnValue $($r.ReturnValue), cmd pid $($r.ProcessId)); log WORK\q$q.log"
  return $true
}
# After a launch: wait up to 10 minutes for its runner to appear, then until no runner and no STOP for 5 minutes in a row.
function WaitEnd($q) {
  for ($t = 0; ($t -lt 10) -and -not (Runner); $t++) { Start-Sleep -Seconds 60 }
  if (-not (Runner)) { Say "no queue runner seen 10 minutes after starting $q (see WORK\q$q.log)" }
  WaitFree "$q running"
  Say "$q ended (no queue runner and no STOP for 5 minutes)"
}
function Card($name, $lines) { $lines | Set-Content -Encoding ascii "$JOBS\$name"; Say "installed pc-jobs\$name" }
function FromTemplate($tpl, $name) {
  if (Test-Path "$CIO\$tpl") { Card $name ((Get-Content "$CIO\$tpl") -replace '@STARTED@', "$(Now) ET") } else { Say "template $tpl missing: no card" }
}
# G1 is over when 10M s401 has an ok RESULT.json (any spill letter), or the futility waiter skipped it, or WORK\G1-DONE.txt exists.
function G1Over {
  if (Test-Path "$WORK\G1-DONE.txt") { return $true }
  if (G1Waiter) { return $false }
  if (OkResult "$WORK\results\8aG1s401*-pc\8aG1s401*-10M-s401\RESULT.json") { return $true }
  $wl = "$WORK\q8aG1s401-waiter.log"
  return ((Test-Path $wl) -and [bool](Select-String -Path $wl -Pattern '10M s401 skipped' -SimpleMatch -Quiet))
}
# GX is ok when every g8a job in src-8gx's 8aGX-pc.txt has an ok RESULT.json under results\8aGX*-pc\8aGX*-<rung>-<seed>\.
function GXOk {
  $qf = "$SRCGX\custom_io\queue_local\8aGX-pc.txt"
  $jobs = @(Get-Content $qf -ErrorAction SilentlyContinue | Where-Object { $_ -match '^g8a:\s+\S+' } | ForEach-Object { ($_ -split '\s+')[1] })
  if ($jobs.Count -eq 0) { Say "no g8a jobs found in $qf"; return $false }
  foreach ($j in $jobs) {
    $tail = $j.Substring($j.IndexOf('-') + 1)
    if (-not (OkResult "$WORK\results\8aGX*-pc\8aGX*-$tail\RESULT.json")) { Say "GX job $j has no ok RESULT.json"; return $false }
  }
  return $true
}

Say "post-G1 chain waiter started (pid $PID): GX stage 1, then fc100, then c30 unless WORK\B3-READY.txt exists"

# 1. Gate G1 ends.
$k = 0
while (-not ((G1Over) -and (Free 5))) {
  if ($k % 360 -eq 0) { Say 'waiting for gate G1 to end (10M s401 ok, or its futility skip, or WORK\G1-DONE.txt; then 5 quiet minutes)' }
  $k++; Start-Sleep -Seconds 60
}
Say 'gate G1 has ended'
MoveDone 'g1*.md'

# 2. Test GX stage 1 (owner: thread "Many experts, many layers test"), unless it runs on the Mac.
if (Test-Path "$WORK\GX-ON-MAC.txt") {
  Say 'WORK\GX-ON-MAC.txt present: GX stage 1 runs on the Mac, skipped here'
} else {
  if (-not (Test-Path "$SRCGX\GX-SETUP-OK.txt")) { Say 'waiting for src-8gx\GX-SETUP-OK.txt (GX setup by install_post_g1.ps1), or WORK\GX-ON-MAC.txt' }
  while (-not (Test-Path "$SRCGX\GX-SETUP-OK.txt") -and -not (Test-Path "$WORK\GX-ON-MAC.txt")) { Start-Sleep -Seconds 60 }
  if (Test-Path "$WORK\GX-ON-MAC.txt") {
    Say 'WORK\GX-ON-MAC.txt present: GX stage 1 runs on the Mac, skipped here'
  } else {
    WaitFree 'before GX'
    if (Launch '8aGX' $SRCGX) {
      Card 'gx.md' (@("started: $(Now) ET by the post-G1 chain waiter C:\Users\benja\custom-io\q8aPost_wait.ps1 on Ben's go (setup steps 1-2 done",
                     "  by install_post_g1.ps1, step 3 by the waiter). When this queue ends the waiter starts the next job itself; never start one by hand.") +
                    @(Get-Content "$SRCGX\custom_io\queue_local\8aGX-card.md"))
      WaitEnd '8aGX'
    }
    if (GXOk) { Say 'GX stage 1: every job ok' }
    else { Hold 'GX-DONE.txt' 'GX stage 1 did not finish ok, so fc100 and c30 wait (Ben asked for experts first); fix and rerun GX, then create WORK\GX-DONE.txt' }
  }
}

# 3. 100M fit check part A (an out-of-memory run is a result, so the chain goes on either way).
WaitFree 'before fc100'
if (Launch '8aFC' $SRC) {
  MoveDone 'gx.md'
  FromTemplate 'fc100.template.md' 'fc100.md'
  WaitEnd '8aFC'
}

# 4. G-PT 30M control, unless B3 group 1 is ready to run first.
if (Test-Path "$WORK\B3-READY.txt") { Say 'WORK\B3-READY.txt present: B3 group 1 goes first, c30 NOT started. Chain finished.'; exit }
WaitFree 'before c30'
if (Test-Path "$WORK\B3-READY.txt") { Say 'WORK\B3-READY.txt present: B3 group 1 goes first, c30 NOT started. Chain finished.'; exit }
if (Launch '8aC30' $SRC) {
  MoveDone 'fc100.md'
  FromTemplate 'c30.template.md' 'c30.md'
  Say 'chain finished: c30 runs on (its card handles a spill)'
} else {
  Say 'chain finished, but c30 did NOT start: NEEDS ATTENTION'
}
