# Post-G1 chain on BensPC (9 Oct 2026, spec addenda K-N). After gate G1's last PC queue ends, one queue at a time:
# test GX stage 1 (8aGX, code src-8gx, Ben's "experts first"); the 100M fit check part A on B3 inputs (8aFC); G2's plain
# controls at the B3 caps, 3M then 10M (8aG2C3, 8aG2C10); the G-PT 30M control at the B3 caps (8aC30) unless the B3 ladder is
# ready (WORK\B3-READY.txt). 8aFC, 8aG2C* and 8aC30 run from src-b3. WORK\STOP holds the chain (it never removes STOP).
# Started detached by install_post_g1.ps1, so it outlives the ssh session. It stops nothing and deletes nothing.
$CIO   = 'C:\Users\benja\custom-io'
$WORK  = "$CIO\work"
$SRCGX = "$CIO\src-8gx"
$SRCB3 = "$CIO\src-b3"
$JOBS  = 'C:\Users\benja\pc-jobs'
$PY    = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$CAPS  = '3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78'      # caps.py of the experts code (src-8gx; same as G1's)
$CAPSB3 = 'D276FAC05E1127D9979E9B8EA3A4F4E6CC4D7BAC33C218FA164117B60F1B4AA8'     # caps.py at c24bce9489 (src-b3)
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
function Launch($q, $src, $hash) {
  $qf = "$src\custom_io\queue_local\$q-pc.txt"
  if (-not (Test-Path $qf)) { Say "queue file $qf missing: $q NOT started"; return $false }
  if ((Get-FileHash "$src\custom_io\g8a\caps.py").Hash -ne $hash) { Say "caps.py hash wrong in ${src}: $q NOT started"; return $false }
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

Say "post-G1 chain waiter started (pid $PID): GX stage 1, fc100, g2c3, g2c10, then c30 unless WORK\B3-READY.txt exists"

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
    if (Launch '8aGX' $SRCGX $CAPS) {
      Card 'gx.md' (@("started: $(Now) ET by the post-G1 chain waiter C:\Users\benja\custom-io\q8aPost_wait.ps1 on Ben's go (setup steps 1-2 done",
                     "  by install_post_g1.ps1, step 3 by the waiter). When this queue ends the waiter starts the next job itself; never start one by hand.") +
                    @(Get-Content "$SRCGX\custom_io\queue_local\8aGX-card.md"))
      WaitEnd '8aGX'
    }
    if (GXOk) { Say 'GX stage 1: every job ok' }
    else { Hold 'GX-DONE.txt' 'GX stage 1 did not finish ok, so the rest of the chain waits (Ben asked for experts first); fix and rerun GX, then create WORK\GX-DONE.txt' }
  }
}

# 3-5. src-b3 queues. A failed or out-of-memory run is reported by its card; the chain goes on either way.
function B3Step($q, $tpl, $card, $old) {
  WaitFree "before $q"
  if (-not (Test-Path "$SRCB3\B3-SETUP-OK.txt")) { Say "src-b3\B3-SETUP-OK.txt missing: $q NOT started, NEEDS ATTENTION"; return }
  if (Launch $q $SRCB3 $CAPSB3) {
    foreach ($c in $old) { MoveDone $c }
    FromTemplate $tpl $card
    WaitEnd $q
  } else { Say "$q did NOT start: NEEDS ATTENTION" }
}
B3Step '8aFC' 'fc100.template.md' 'fc100.md' @('gx.md')
B3Step '8aG2C3' 'g2c3.template.md' 'g2c3.md' @('gx.md', 'fc100.md')
B3Step '8aG2C10' 'g2c10.template.md' 'g2c10.md' @('gx.md', 'fc100.md', 'g2c3.md')

# 6. G-PT 30M control, unless the B3 ladder is ready to run first.
if (Test-Path "$WORK\B3-READY.txt") { Say 'WORK\B3-READY.txt present: the B3 ladder goes first, c30 NOT started. Chain finished.'; exit }
WaitFree 'before c30'
if (Test-Path "$WORK\B3-READY.txt") { Say 'WORK\B3-READY.txt present: the B3 ladder goes first, c30 NOT started. Chain finished.'; exit }
if (-not (Test-Path "$SRCB3\B3-SETUP-OK.txt")) {
  Say 'src-b3\B3-SETUP-OK.txt missing: c30 NOT started, NEEDS ATTENTION. Chain finished.'
} elseif (Launch '8aC30' $SRCB3 $CAPSB3) {
  foreach ($c in @('gx.md', 'fc100.md', 'g2c3.md', 'g2c10.md')) { MoveDone $c }
  FromTemplate 'c30.template.md' 'c30.md'
  Say 'chain finished: c30 runs on (its card handles a spill)'
} else {
  Say 'chain finished, but c30 did NOT start: NEEDS ATTENTION'
}
