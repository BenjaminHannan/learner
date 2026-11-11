# No G1 reruns (Ben, 1:17 AM ET 12 Oct 2026: "I don't think you should rerun g1, it's not worth it"; spec addendum AE). g1recover.ps1 (the
# 10:25 PM ET job, run by the Mac at 00:38 ET) had already started G1's reruns, and its install stopped at one test whose bit pin this CPU
# rounds differently (install_rr.ps1 now runs it through run_tests.py). Run once from in-rr2, over ssh; it returns in about a minute:
#   1. refuses (NOTHING STARTED) if the chain is already past G1, WORK\G1-DONE.txt or WORK\STOP exists, the post-G1 waiter is not running
#      once, a queue runner other than G1's runs, or a file is missing here;
#   2. stops the old pc_after_restart.ps1 FIRST (else it starts s401 when s400's runner ends), then G1's rerun runners (8aG1fR, 8aG1s401r:
#      their cmd trees and python processes), and waits until they are gone; their logs and partial result folders are kept;
#   3. renames WORK\g1recover-plan.json aside (.stopped-<stamp>) so nothing starts G1 again, and moves the G1 rerun cards to pc-jobs\done;
#   4. with no queue runner left, renames the G1 runs' GPU-BUSY.txt and pool locks aside (.stale-<stamp>), as g1recover.ps1 does;
#   5. starts pc_after_restart.ps1 detached: install_rr.ps1, then agent\install_agent.ps1, then WORK\G1-DONE.txt only after a clean
#      install_rr (NO-G1-RERUN.txt is here), so the post-G1 chain starts 5 quiet minutes later and never on the old code.
# The waiter cannot start the old chain meanwhile: without G1-DONE.txt or s401's ok RESULT.json it keeps waiting. Nothing is deleted.
$IN    = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO   = 'C:\Users\benja\custom-io'
$WORK  = "$CIO\work"
$JOBS  = 'C:\Users\benja\pc-jobs'
$PLOG  = "$WORK\q8aPost-waiter.log"
$RLOG  = "$WORK\q8aG1recover.log"
$BUSY  = 'C:\Users\benja\GPU-BUSY.txt'
$STAMP = (Get-Date).ToString('yyyyMMdd-HHmm')
$G1Q   = @('8aG1fR', '8aG1s401r')
function Say($m) { $l = "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET $m"; $l; $l | Add-Content -Encoding ascii $RLOG }
function Procs($name, $pat) { @(Get-CimInstance Win32_Process -Filter "Name like '$name%'" | Where-Object { $_.CommandLine -like $pat }) }
function G1Procs { @(foreach ($q in $G1Q) { Procs 'python' "*$q*" }) + @(Procs 'powershell' '*pc_after_restart.ps1*') + @(Procs 'powershell' '*q8aG1*_wait.ps1*') }

# 1. Refusals.
Say "nog1_go: free to commit $([math]::Floor((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1024)) MB; GPU $((& nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader 2>$null) -join ' ')"
foreach ($f in @('NO-G1-RERUN.txt', 'pc_after_restart.ps1', 'install_rr.ps1', 'run_tests.py')) { if (-not (Test-Path "$IN\$f")) { Say "NOTHING STARTED: $f missing in $IN"; exit 1 } }
if (Test-Path "$WORK\G1-DONE.txt") { Say "NOTHING STARTED: WORK\G1-DONE.txt already exists ($(@(Get-Content "$WORK\G1-DONE.txt") -join ' | '))"; exit 0 }
if (Test-Path "$WORK\STOP") { Say 'NOTHING STARTED: WORK\STOP exists (someone asked for a stop)'; exit 1 }
$w = @(Procs 'powershell' '*q8aPost3_wait.ps1*')
if ($w.Count -ne 1) { Say "NOTHING STARTED: expected one post-G1 waiter (q8aPost3_wait.ps1), found $($w.Count)"; exit 1 }
$lines = @(Get-Content $PLOG); $start = -1
for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*chain waiter v3 started*') { $start = $i } }
if ($start -lt 0) { Say "NOTHING STARTED: no 'chain waiter v3 started' line in $PLOG"; exit 1 }
for ($i = $start; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*gate G1 has ended*') { Say 'NOTHING STARTED: the waiter is already past gate G1'; exit 1 } }
$other = @(Procs 'python' '*local_runner*' | Where-Object { $c = $_.CommandLine; -not @($G1Q | Where-Object { $c -like "*$_*" }).Count })
if ($other.Count) { Say "NOTHING STARTED: a queue runner that is not G1's is running: $(@($other | ForEach-Object { "pid $($_.ProcessId) $($_.CommandLine)" }) -join ' | ')"; exit 1 }
Say "  waiter: pid $($w[0].ProcessId), $($lines[$start])"

# 2. Stop G1's reruns: pc_after_restart.ps1 first, then each queue's cmd tree and python processes.
foreach ($p in @(Procs 'powershell' '*pc_after_restart.ps1*') + @(Procs 'powershell' '*q8aG1*_wait.ps1*')) {
  Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue; Say "stopped pid $($p.ProcessId): $($p.CommandLine)"
}
foreach ($q in $G1Q) {
  foreach ($c in @(Procs 'cmd' "*q${q}_run.cmd*")) { $r = @(& taskkill /PID $c.ProcessId /T /F 2>&1); Say "taskkill /T $q cmd pid $($c.ProcessId): $($r -join ' ')" }
  foreach ($p in @(Procs 'python' "*$q*")) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue; Say "stopped $q python pid $($p.ProcessId)" }
}
for ($t = 0; $t -lt 24 -and (G1Procs).Count; $t++) { Start-Sleep -Seconds 5 }
$left = @(G1Procs)
if ($left.Count) { Say "NOTHING STARTED: still running after 2 minutes, NEEDS ATTENTION: $(@($left | ForEach-Object { "pid $($_.ProcessId) $($_.CommandLine)" }) -join ' | ')"; exit 1 }
foreach ($q in $G1Q) { $l = "$WORK\q$q.log"; if (Test-Path $l) { Say "  $q stopped; its last log line: $(Get-Content $l -Tail 1)" } }
"$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET nog1_go.ps1: G1 reruns stopped (Ben, 1:17 AM ET 12 Oct: no G1 rerun); G1-DONE.txt follows a clean install" | Add-Content -Encoding ascii $PLOG

# 3. Nothing starts G1 again; its cards go to done.
if (Test-Path "$WORK\g1recover-plan.json") { Rename-Item "$WORK\g1recover-plan.json" "g1recover-plan.json.stopped-$STAMP"; Say "renamed WORK\g1recover-plan.json to g1recover-plan.json.stopped-$STAMP" }
New-Item -ItemType Directory -Force "$JOBS\done" | Out-Null
foreach ($c in @('g1fr', 'g1s401r')) { if (Test-Path "$JOBS\$c.md") { Move-Item "$JOBS\$c.md" "$JOBS\done\$c.stopped-$STAMP.md"; Say "moved pc-jobs\$c.md to done\$c.stopped-$STAMP.md" } }

# 4. The killed runs' busy file and pool locks, only with no queue runner left.
if (-not @(Procs 'python' '*local_runner*').Count) {
  if (Test-Path $BUSY) { $b = @(Get-Content $BUSY) -join ' | '; Rename-Item $BUSY "GPU-BUSY.txt.stale-$STAMP"; Say "GPU-BUSY.txt ($b) renamed GPU-BUSY.txt.stale-$STAMP" }
  foreach ($l in @(Get-ChildItem "$WORK\pools\*.lock", "$WORK\g8a\pools\*.lock" -ErrorAction SilentlyContinue)) { Rename-Item $l.FullName "$($l.Name).stale-$STAMP"; Say "pool lock $($l.Name) renamed .stale-$STAMP" }
} else { Say 'NEEDS ATTENTION: a queue runner appeared; GPU-BUSY.txt and the pool locks were left alone' }

# 5. The install, then G1-DONE.txt (pc_after_restart.ps1, detached; log WORK\q8aG1recover.log).
foreach ($f in @('in-rr2-install.txt', 'in-agent-install.txt')) { if (Test-Path "$WORK\$f") { Rename-Item "$WORK\$f" "$f.before-$STAMP" } }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="powershell -NoProfile -ExecutionPolicy Bypass -File $IN\pc_after_restart.ps1"}
Say "started pc_after_restart.ps1 (ReturnValue $($r.ReturnValue), pid $($r.ProcessId)): install_rr, install_agent, then G1-DONE.txt after a clean install_rr"
'NOG1 GO STARTED'
