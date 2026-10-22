# Replace the running post-G1 waiter v3d with v3e (11 Oct 2026, spec addendum U): same file name q8aPost3_wait.ps1.
# v3e changes inserted jobs (WORK\insert): a job may come from any src-<name> folder in custom-io (with "caps: <SHA-256 of its caps.py>")
# or be a plain .cmd script in custom-io ("cmd: <file>.cmd"), for the creative/sleep jobs on new code; WORK\insert\README.txt is no longer
# taken for a job. And (addendum Y) with the reader-rule code in src-b3g2, group 2 (G2f) runs before group 1. Only while v3d still waits for G1. Everything is checked before anything changes. It stops nothing but the waiter and
# deletes nothing.
$IN    = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO   = 'C:\Users\benja\custom-io'
$WORK  = "$CIO\work"
$LOG   = "$WORK\q8aPost-waiter.log"
function Fail($m) { "FAILED: $m (the running waiter and its files were not changed)"; exit 1 }
function Waiters($name) { @(Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" | Where-Object { $_.CommandLine -like "*$name*" }) }

# 1. The new waiter parses and is v3e; v3d's pieces are installed.
$new = "$IN\q8aPost3_wait.ps1"
$e = $null
[void][System.Management.Automation.Language.Parser]::ParseFile($new, [ref]$null, [ref]$e)
if ($e.Count) { Fail "parse errors in the new waiter: $(($e | ForEach-Object { "line $($_.Extent.StartLineNumber): $($_.Message)" }) -join '; ')" }
foreach ($k in @('function InferStep', 'function RunInserts', '$script:icards', "'cmd:' goes alone", '$g2first')) {
  if (-not (Select-String -Path $new -Pattern $k -SimpleMatch -Quiet)) { Fail "the new file is not v3e (no '$k')" }
}
'new waiter parses (0 errors)'
foreach ($f in @("$CIO\infer_speed.py", "$CIO\fc100v3.template.md", "$WORK\GX-ON-MAC.txt", "$WORK\insert\README.txt")) { if (-not (Test-Path $f)) { Fail "$f missing (is v3d installed?)" } }
$jobs = @(Get-ChildItem "$WORK\insert\*.txt" | Where-Object { $_.Name -ne 'README.txt' })
"WORK\insert holds $($jobs.Count) job file(s)$(if ($jobs.Count) { ': ' + (($jobs | ForEach-Object { $_.Name }) -join ', ') })"

# 2. v3d still waits for G1.
$w = @(Waiters 'q8aPost3_wait.ps1')
if ($w.Count -ne 1) { Fail "expected one q8aPost3_wait.ps1 waiter, found $($w.Count)" }
$lines = @(Get-Content $LOG)
$start = -1
for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*chain waiter v3 started*') { $start = $i } }
if ($start -lt 0) { Fail "no 'chain waiter v3 started' line in $LOG" }
if ($lines[$start] -notlike '*(v3d;*') { Fail "the running waiter is not v3d: $($lines[$start])" }
for ($i = $start; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*gate G1 has ended*') { Fail 'the waiter is already past gate G1 (swap by hand)' } }
"waiter pid $($w[0].ProcessId) (v3d) is still waiting for G1"

# 3. The insert README says what v3e accepts.
Set-Content -Encoding ascii "$WORK\insert\README.txt" -Value @(
  'Inserted jobs for the post-G1 waiter (v3e). This README is never taken for a job. To add a job, write a file here named <order>-<name>.txt with either:',
  '  queue: <Q>   and   src: <src-name folder in custom-io>   (the queue file must be in <src>\custom_io\queue_local\<Q>-pc.txt)',
  '     plus, for a src other than src-b3g2 and src-b3:   caps: <SHA-256 of <src>\custom_io\g8a\caps.py>   (Get-FileHash)',
  'or',
  '  cmd: <file>.cmd   (a cmd file in custom-io that keeps its job in the foreground; the chain waits for it to exit)   optional  hours: N  (a NEEDS ATTENTION line every N hours, default 48)',
  'Optional for both:  card: <card template file in custom-io>.',
  'Each runs alone at the next check point after group 2 at 3M (also before g2c10s, before c30s, at the end), in name order; the file is then renamed .done-<stamp> (.refused / .notstarted on a problem).')
'WORK\insert\README.txt updated'

# 4. Swap the waiter.
$w = @(Waiters 'q8aPost3_wait.ps1')
if ($w.Count -ne 1) { "FAILED: expected one waiter before the swap, found $($w.Count); the README was updated, the waiter was not changed"; exit 1 }
Stop-Process -Id $w[0].ProcessId -Force
Copy-Item -Force $new "$CIO\q8aPost3_wait.ps1"
"$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET waiter v3d (pid $($w[0].ProcessId)) stopped by swap_v3e.ps1 while waiting for G1; starting v3e" | Add-Content -Encoding ascii $LOG
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="powershell -NoProfile -ExecutionPolicy Bypass -File $CIO\q8aPost3_wait.ps1"}
"started v3e (ReturnValue $($r.ReturnValue), pid $($r.ProcessId))"
Start-Sleep -Seconds 15
"v3 waiters running: $(@(Waiters 'q8aPost3_wait.ps1').Count)"
Get-Content $LOG -Tail 4
