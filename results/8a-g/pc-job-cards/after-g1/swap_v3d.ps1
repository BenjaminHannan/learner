# Replace the running post-G1 waiter v3c with v3d (11 Oct 2026, spec addendum T): same file name q8aPost3_wait.ps1.
# v3d adds fc100 part 3 right after part 2: custom-io\infer_speed.py times how fast the four ~100M shapes answer (read-only, alone on the GPU,
# at most about an hour), card fc100v3.md. Nothing else in the chain changes. Only while v3c still waits for G1. Everything is checked before
# anything changes. It stops nothing but the waiter and deletes nothing.
$IN    = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO   = 'C:\Users\benja\custom-io'
$WORK  = "$CIO\work"
$SRCG2 = "$CIO\src-b3g2"
$PY    = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$LOG   = "$WORK\q8aPost-waiter.log"
function Fail($m) { "FAILED: $m (the running waiter and its files were not changed)"; exit 1 }
function Waiters($name) { @(Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" | Where-Object { $_.CommandLine -like "*$name*" }) }

# 1. The new waiter parses and is v3d; the inputs are here.
$new = "$IN\q8aPost3_wait.ps1"
$e = $null
[void][System.Management.Automation.Language.Parser]::ParseFile($new, [ref]$null, [ref]$e)
if ($e.Count) { Fail "parse errors in the new waiter: $(($e | ForEach-Object { "line $($_.Extent.StartLineNumber): $($_.Message)" }) -join '; ')" }
if (-not (Select-String -Path $new -Pattern 'function InferStep' -SimpleMatch -Quiet)) { Fail 'the new file is not v3d' }
if (-not (Select-String -Path $new -Pattern 'function RunInserts' -SimpleMatch -Quiet)) { Fail 'the new file lost v3c' }
'new waiter parses (0 errors)'
foreach ($f in @('infer_speed.py', 'fc100v2.md', 'fc100v3.md')) { if (-not (Test-Path "$IN\$f")) { Fail "$f missing in $IN" } }
foreach ($f in @("$SRCG2\G2-SETUP-OK.txt", "$SRCG2\custom_io\queue_local\8aFC2-pc.txt", "$WORK\GX-ON-MAC.txt", "$WORK\insert\README.txt")) { if (-not (Test-Path $f)) { Fail "$f missing (is v3c installed?)" } }

# 2. v3c still waits for G1.
$w = @(Waiters 'q8aPost3_wait.ps1')
if ($w.Count -ne 1) { Fail "expected one q8aPost3_wait.ps1 waiter, found $($w.Count)" }
$lines = @(Get-Content $LOG)
$start = -1
for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*chain waiter v3 started*') { $start = $i } }
if ($start -lt 0) { Fail "no 'chain waiter v3 started' line in $LOG" }
if ($lines[$start] -notlike '*(v3c;*') { Fail "the running waiter is not v3c: $($lines[$start])" }
for ($i = $start; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*gate G1 has ended*') { Fail 'the waiter is already past gate G1 (swap by hand)' } }
"waiter pid $($w[0].ProcessId) (v3c) is still waiting for G1"

# 3. CPU check from src-b3g2: infer_speed.py runs one shape at a tiny width on test rows (no Gemma, no GPU) into a new folder under TEMP.
$env:PYTHONPATH = 'C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages'
$env:PYTHONUTF8 = '1'
$stamp = (Get-Date).ToString('yyyyMMdd-HHmm')
$st = "$env:TEMP\infer-selftest-$stamp"
Push-Location $SRCG2
$chk = & $PY "$IN\infer_speed.py" --src $SRCG2 --queue "$SRCG2\custom_io\queue_local\8aFC2-pc.txt" --selftest $st 2>&1
$rc = $LASTEXITCODE
Pop-Location
$chk | Select-Object -Last 6
if ($rc -ne 0 -or -not ("$chk" -like '*INFER SELFTEST OK*')) { Fail "CPU check failed (rc $rc)" }

# 4. Files: the script and both card templates.
Copy-Item -Force "$IN\infer_speed.py" "$CIO\infer_speed.py"
Copy-Item -Force "$IN\fc100v2.md" "$CIO\fc100v2.template.md"
Copy-Item -Force "$IN\fc100v3.md" "$CIO\fc100v3.template.md"
'copied infer_speed.py and the fc100v2 / fc100v3 card templates'

# 5. Swap the waiter.
$w = @(Waiters 'q8aPost3_wait.ps1')
if ($w.Count -ne 1) { "FAILED: expected one waiter before the swap, found $($w.Count); files were copied, the waiter was not changed"; exit 1 }
Stop-Process -Id $w[0].ProcessId -Force
Copy-Item -Force $new "$CIO\q8aPost3_wait.ps1"
"$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET waiter v3c (pid $($w[0].ProcessId)) stopped by swap_v3d.ps1 while waiting for G1; starting v3d" | Add-Content -Encoding ascii $LOG
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="powershell -NoProfile -ExecutionPolicy Bypass -File $CIO\q8aPost3_wait.ps1"}
"started v3d (ReturnValue $($r.ReturnValue), pid $($r.ProcessId))"
Start-Sleep -Seconds 15
"v3 waiters running: $(@(Waiters 'q8aPost3_wait.ps1').Count)"
Get-Content $LOG -Tail 4
