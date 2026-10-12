# After Ben's PC restart (11 Oct 2026, about 9:45 PM ET; spec addendum AC). Run from the folder the Mac copied (in-rr2), over ssh; it
# returns in about a minute. It prints what survived, then, only if nothing of G1 or the chain is running:
#   1. writes the rerun queues for the G1 arms that have no ok RESULT.json (s400 -> 8aG1fR, s401 -> 8aG1s401r) into src-8ag,
#   2. renames the stale GPU-BUSY.txt and pool locks aside (.stale-<stamp>), moves the dead runs' cards to pc-jobs\done,
#   3. restarts the post-G1 waiter (the same q8aPost3_wait.ps1 file, still v3d),
#   4. starts pc_after_restart.ps1 detached: the install (install_rr.ps1, while the memory is free), then the G1 reruns.
# Finished runs and their folders are never touched; nothing is deleted. If G1 or the waiter is already running, it changes nothing.
# With -Plan it prints the plan and changes nothing.
param([switch]$Plan)
$IN    = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO   = 'C:\Users\benja\custom-io'
$WORK  = "$CIO\work"
$SRC   = "$CIO\src-8ag"
$JOBS  = 'C:\Users\benja\pc-jobs'
$PLOG  = "$WORK\q8aPost-waiter.log"
$RLOG  = "$WORK\q8aG1recover.log"
$CAPS  = '3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78'
$STAMP = (Get-Date).ToString('yyyyMMdd-HHmm')
function Say($m) { $l = "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET $m"; $l; if (-not $Plan) { $l | Add-Content -Encoding ascii $RLOG } }
function Py($pat) { @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -like $pat }) }
function Ps($pat) { @(Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" | Where-Object { $_.CommandLine -like $pat }) }
function ArmOk($glob) {
  foreach ($r in @(Get-ChildItem $glob -ErrorAction SilentlyContinue)) {
    try { $j = Get-Content $r.FullName -Raw | ConvertFrom-Json; if ($j.status -eq 'ok') { return $r.FullName } } catch { }
  }
  return $null
}
function LastStep($glob) {
  $f = @(Get-ChildItem $glob -ErrorAction SilentlyContinue | Sort-Object LastWriteTime) | Select-Object -Last 1
  if (-not $f) { return '-' }
  $l = @(Select-String -Path $f.FullName -Pattern '"event": "train"' -SimpleMatch) | Select-Object -Last 1
  if (-not $l) { return "no update yet ($($f.FullName.Substring($WORK.Length + 1)))" }
  try { $j = $l.Line | ConvertFrom-Json; "update $($j.step) of 24000 ($($f.FullName.Substring($WORK.Length + 1)))" } catch { '?' }
}

# 1. What survived the restart.
$os = Get-CimInstance Win32_OperatingSystem
Say "g1recover: PC up since $($os.LastBootUpTime); free to commit $([math]::Floor($os.FreeVirtualMemory / 1024)) MB of $([math]::Floor($os.TotalVirtualMemorySize / 1024)) MB; GPU $((& nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader 2>$null) -join ' ')"
$runners = @(Py '*local_runner*'); $trainers = @(Py '*custom_io.train*') + @(Py '*custom_io.g8a.job*')
$waiters = @(Ps '*q8aPost3_wait.ps1*') + @(Ps '*q8aG1*_wait.ps1*') + @(Ps '*g1_share_watch.ps1*') + @(Ps '*pc_after_restart.ps1*')
foreach ($p in @($runners + $trainers + $waiters)) { Say "  running: pid $($p.ProcessId) $($p.CommandLine)" }
$arms = [ordered]@{}
foreach ($s in @(@('s400', '8aG1f*-pc\8aG1f*-10M-s400'), @('s401', '8aG1s401*-pc\8aG1s401*-10M-s401'))) {
  foreach ($a in @('B2', 'PT')) {
    $ok = ArmOk "$WORK\results\$($s[1])\$a\RESULT.json"
    $arms["$($s[0]) $a"] = [bool]$ok
    if ($ok) { Say "  10M $($s[0]) ${a}: ok ($($ok.Substring($WORK.Length + 1)))" }
    else { Say "  10M $($s[0]) ${a}: no ok RESULT.json; last log: $(LastStep "$WORK\results\$($s[1])\$a\stdout.txt")" }
  }
}
Say "  WORK\STOP: $(Test-Path "$WORK\STOP"); GPU-BUSY.txt: $(if (Test-Path 'C:\Users\benja\GPU-BUSY.txt') { (@(Get-Content 'C:\Users\benja\GPU-BUSY.txt') -join ' | ') } else { 'none' })"
Say "  post-G1 waiter log, last line: $(Get-Content $PLOG -Tail 1 -ErrorAction SilentlyContinue)"

# 2. Refuse if anything is running (no restart, or already recovered) or a stop was asked for.
if ($runners.Count -or $trainers.Count -or $waiters.Count) { Say 'NOTHING STARTED: G1 or the chain is still running (no restart, or already recovered)'; exit 0 }
if (Test-Path "$WORK\STOP") { Say 'NOTHING STARTED: WORK\STOP exists (someone asked for a stop)'; exit 1 }
if ((Get-FileHash "$SRC\custom_io\g8a\caps.py").Hash -ne $CAPS) { Say 'NOTHING STARTED: caps.py in src-8ag is not G1''s'; exit 1 }
foreach ($f in @('8aG1fR-pc.txt', '8aG1s401r-pc.txt', 'g1fr.template.md', 'g1s401r.template.md', 'pc_after_restart.ps1')) { if (-not (Test-Path "$IN\$f")) { Say "NOTHING STARTED: $f missing in $IN"; exit 1 } }
if (-not (Test-Path "$CIO\q8aPost3_wait.ps1")) { Say 'NOTHING STARTED: custom-io\q8aPost3_wait.ps1 missing'; exit 1 }

# 3. The plan: rerun only the arms without an ok RESULT.json (accum as G1: B2 16, PT 8).
$todo = @{}
foreach ($q in @(@('8aG1fR', 's400'), @('8aG1s401r', 's401'))) {
  $need = @(@('B2', 'PT') | Where-Object { -not $arms["$($q[1]) $_"] })
  if ($need.Count) { $todo[$q[0]] = @{ arms = ($need -join ' '); accum = (@($need | ForEach-Object { if ($_ -eq 'B2') { 'B2=16' } else { 'PT=8' } }) -join ',') } }
}
foreach ($k in $todo.Keys) { Say "plan: queue $k runs arms $($todo[$k].arms) (accum $($todo[$k].accum))" }
if (-not $todo.Count) { Say 'plan: every G1 arm has an ok RESULT.json; no G1 rerun' }
if ($Plan) { 'PLAN ONLY: nothing changed'; exit 0 }

# 4. Queues, stale files, cards.
foreach ($k in $todo.Keys) {
  $dst = "$SRC\custom_io\queue_local\$k-pc.txt"
  if (Test-Path $dst) { Rename-Item $dst "$k-pc.txt.before-$STAMP" }
  (Get-Content "$IN\$k-pc.txt") -replace '@ARMS@', $todo[$k].arms -replace '@ACCUM@', $todo[$k].accum | Set-Content -Encoding ascii $dst
  Say "wrote src-8ag\custom_io\queue_local\$k-pc.txt: $(@(Get-Content $dst | Where-Object { $_ -like 'g8a:*' }) -join '')"
}
if (Test-Path 'C:\Users\benja\GPU-BUSY.txt') { Rename-Item 'C:\Users\benja\GPU-BUSY.txt' "GPU-BUSY.txt.stale-$STAMP"; Say "GPU-BUSY.txt renamed GPU-BUSY.txt.stale-$STAMP (no runner is running)" }
foreach ($l in @(Get-ChildItem "$WORK\pools\*.lock", "$WORK\g8a\pools\*.lock" -ErrorAction SilentlyContinue)) { Rename-Item $l.FullName "$($l.Name).stale-$STAMP"; Say "pool lock $($l.Name) renamed .stale-$STAMP" }
New-Item -ItemType Directory -Force "$JOBS\done" | Out-Null
foreach ($c in @('g1f.md', 'g1s401.md')) { if (Test-Path "$JOBS\$c") { Move-Item -Force "$JOBS\$c" "$JOBS\done\"; Say "moved pc-jobs\$c to done (its run died in the restart)" } }
Copy-Item -Force "$IN\g1fr.template.md" "$CIO\g1fr.template.md"; Copy-Item -Force "$IN\g1s401r.template.md" "$CIO\g1s401r.template.md"
$todo | ConvertTo-Json | Set-Content -Encoding ascii "$WORK\g1recover-plan.json"

# 5. The post-G1 waiter again (same file; it waits for 10M s401's RESULT.json, which 8aG1s401r writes).
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="powershell -NoProfile -ExecutionPolicy Bypass -File $CIO\q8aPost3_wait.ps1"}
"$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET waiter restarted by g1recover.ps1 after the PC restart (pid $($r.ProcessId))" | Add-Content -Encoding ascii $PLOG
Say "restarted the post-G1 waiter (ReturnValue $($r.ReturnValue), pid $($r.ProcessId))"
for ($t = 0; $t -lt 12; $t++) {
  Start-Sleep -Seconds 5
  $last = @(Get-Content $PLOG | Where-Object { $_ -like '*chain waiter v3 started*' }) | Select-Object -Last 1
  if ("$last" -like "*pid $($r.ProcessId))*") { break }
}
Say "  waiter start line: $last"

# 6. The install, then the G1 reruns, detached (log WORK\q8aG1recover.log; install output WORK\in-rr2-install.txt).
$r2 = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="powershell -NoProfile -ExecutionPolicy Bypass -File $IN\pc_after_restart.ps1"}
Say "started pc_after_restart.ps1 (ReturnValue $($r2.ReturnValue), pid $($r2.ProcessId)): the install first, then G1"
'RECOVERY STARTED'
