# Replace the running post-G1 waiter v3 with its revision v3b (10 Oct 2026, spec addendum R): same file name q8aPost3_wait.ps1.
# v3b adds: (1) a job folder whose job-level RESULT.json is not ok is renamed aside before a launch (local_runner would skip it);
# (2) group 2 waits (moves to the end, runs on WORK\G2-GO.txt) if group 1 s400 is proved wrong on B3-1, B3-2 or B3-3.
# Only while v3 still waits for G1. The new file is parse-checked first. It stops nothing else and deletes nothing.
$IN  = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO = 'C:\Users\benja\custom-io'
$LOG = "$CIO\work\q8aPost-waiter.log"
function Fail($m) { "FAILED: $m (the running waiter was not changed)"; exit 1 }
function Waiters($name) { @(Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" | Where-Object { $_.CommandLine -like "*$name*" }) }
$new = "$IN\q8aPost3_wait.ps1"
$e = $null
[void][System.Management.Automation.Language.Parser]::ParseFile($new, [ref]$null, [ref]$e)
if ($e.Count) { Fail "parse errors in the new waiter: $(($e | ForEach-Object { "line $($_.Extent.StartLineNumber): $($_.Message)" }) -join '; ')" }
if (-not (Select-String -Path $new -Pattern 'function ClearFailed' -SimpleMatch -Quiet)) { Fail 'the new file is not v3b' }
'new waiter parses (0 errors)'
$w = @(Waiters 'q8aPost3_wait.ps1')
if ($w.Count -ne 1) { Fail "expected one q8aPost3_wait.ps1 waiter, found $($w.Count)" }
if (@(Waiters 'q8aPost2_wait.ps1').Count) { Fail 'a v2 waiter is running too' }
$lines = @(Get-Content $LOG)
$start = -1
for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*chain waiter v3 started*') { $start = $i } }
if ($start -lt 0) { Fail "no 'chain waiter v3 started' line in $LOG" }
for ($i = $start; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*gate G1 has ended*') { Fail 'v3 is already past gate G1 (swap by hand)' } }
Stop-Process -Id $w[0].ProcessId -Force
Copy-Item -Force $new "$CIO\q8aPost3_wait.ps1"
"$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET waiter v3 (pid $($w[0].ProcessId)) stopped by swap_v3b.ps1 while waiting for G1; starting v3b" | Add-Content -Encoding ascii $LOG
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="powershell -NoProfile -ExecutionPolicy Bypass -File $CIO\q8aPost3_wait.ps1"}
"started v3b (ReturnValue $($r.ReturnValue), pid $($r.ProcessId))"
Start-Sleep -Seconds 15
"v3 waiters running: $(@(Waiters 'q8aPost3_wait.ps1').Count)"
Get-Content $LOG -Tail 4
