# Replace the running post-G1 waiter v3b with v3c (11 Oct 2026, spec addendum S): same file name q8aPost3_wait.ps1.
# v3c: (1) fc100 is split: part 1 (8aFC, src-b3) only builds the pool, part 2 (8aFC2, src-b3g2) measures four ~100M group 2 shapes
# (21 x 512, 30 x 432, 37 x 384, 54 x 320; FINISHED-MODEL item 10); (2) inserted jobs from WORK\insert\*.txt run at check points after
# group 2 at 3M (for the 10M depth pair, whose config comes after group 2's readout). GX stays skipped by WORK\GX-ON-MAC.txt.
# Only while v3b still waits for G1. Everything is checked before anything changes; the old src-b3 8aFC-pc.txt is kept as a copy.
# It stops nothing but the waiter and deletes nothing.
$IN    = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO   = 'C:\Users\benja\custom-io'
$WORK  = "$CIO\work"
$SRCB3 = "$CIO\src-b3"
$SRCG2 = "$CIO\src-b3g2"
$PY    = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$LOG   = "$WORK\q8aPost-waiter.log"
function Fail($m) { "FAILED: $m (the running waiter and its files were not changed)"; exit 1 }
function Waiters($name) { @(Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" | Where-Object { $_.CommandLine -like "*$name*" }) }

# 1. The new waiter parses and is v3c; the inputs are here.
$new = "$IN\q8aPost3_wait.ps1"
$e = $null
[void][System.Management.Automation.Language.Parser]::ParseFile($new, [ref]$null, [ref]$e)
if ($e.Count) { Fail "parse errors in the new waiter: $(($e | ForEach-Object { "line $($_.Extent.StartLineNumber): $($_.Message)" }) -join '; ')" }
if (-not (Select-String -Path $new -Pattern 'function RunInserts' -SimpleMatch -Quiet)) { Fail 'the new file is not v3c' }
'new waiter parses (0 errors)'
foreach ($f in @('8aFC-pc.txt', '8aFC2-pc.txt', 'fc100.md', 'fc100v2.md', 'fc2check.py')) { if (-not (Test-Path "$IN\$f")) { Fail "$f missing in $IN" } }
if (-not (Test-Path "$SRCG2\G2-SETUP-OK.txt")) { Fail 'src-b3g2\G2-SETUP-OK.txt missing' }
if (-not (Test-Path "$WORK\GX-ON-MAC.txt")) { Fail 'WORK\GX-ON-MAC.txt missing (GX would run first)' }

# 2. v3b still waits for G1.
$w = @(Waiters 'q8aPost3_wait.ps1')
if ($w.Count -ne 1) { Fail "expected one q8aPost3_wait.ps1 waiter, found $($w.Count)" }
$lines = @(Get-Content $LOG)
$start = -1
for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*chain waiter v3 started*') { $start = $i } }
if ($start -lt 0) { Fail "no 'chain waiter v3 started' line in $LOG" }
for ($i = $start; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*gate G1 has ended*') { Fail 'the waiter is already past gate G1 (swap by hand)' } }
"waiter pid $($w[0].ProcessId) is still waiting for G1"

# 3. CPU check from src-b3g2: 8aFC2 parses and each of its eight configs builds at about 100M trained.
$env:PYTHONPATH = 'C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages'
$env:PYTHONUTF8 = '1'
Push-Location $SRCG2
$chk = & $PY "$IN\fc2check.py" "$IN\8aFC2-pc.txt" 2>&1
$rc = $LASTEXITCODE
Pop-Location
$chk
if ($rc -ne 0 -or -not ("$chk" -like '*FC2 CPU CHECK OK*')) { Fail "CPU check failed (rc $rc)" }

# 4. Files: queues (old src-b3 8aFC kept as a copy), card templates, the insert folder.
$stamp = (Get-Date).ToString('yyyyMMdd-HHmm')
Copy-Item "$SRCB3\custom_io\queue_local\8aFC-pc.txt" "$SRCB3\custom_io\queue_local\8aFC-pc.txt.v3b-$stamp"
Copy-Item -Force "$IN\8aFC-pc.txt" "$SRCB3\custom_io\queue_local\8aFC-pc.txt"
Copy-Item -Force "$IN\8aFC2-pc.txt" "$SRCG2\custom_io\queue_local\8aFC2-pc.txt"
Copy-Item -Force "$IN\fc100.md" "$CIO\fc100.template.md"
Copy-Item -Force "$IN\fc100v2.md" "$CIO\fc100v2.template.md"
New-Item -ItemType Directory -Force "$WORK\insert" | Out-Null
Set-Content -Encoding ascii "$WORK\insert\README.txt" -Value @(
  'Inserted jobs for the post-G1 waiter (v3c). To add one: put its queue file in <src>\custom_io\queue_local\<Q>-pc.txt, then a file',
  'here named <order>-<name>.txt with the lines "queue: <Q>" and "src: src-b3g2" (or "src: src-b3"), optional "card: <template file in custom-io>".',
  'It runs alone at the next check point after group 2 at 3M (also before g2c10s, before c30s, at the end), then the file is renamed .done-<stamp>.')
'copied 8aFC (pool only; old kept as .v3b copy), 8aFC2, both fc100 card templates; WORK\insert ready'

# 5. Swap the waiter.
$w = @(Waiters 'q8aPost3_wait.ps1')
if ($w.Count -ne 1) { "FAILED: expected one waiter before the swap, found $($w.Count); files were copied, the waiter was not changed"; exit 1 }
Stop-Process -Id $w[0].ProcessId -Force
Copy-Item -Force $new "$CIO\q8aPost3_wait.ps1"
"$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET waiter v3b (pid $($w[0].ProcessId)) stopped by swap_v3c.ps1 while waiting for G1; starting v3c" | Add-Content -Encoding ascii $LOG
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="powershell -NoProfile -ExecutionPolicy Bypass -File $CIO\q8aPost3_wait.ps1"}
"started v3c (ReturnValue $($r.ReturnValue), pid $($r.ProcessId))"
Start-Sleep -Seconds 15
"v3 waiters running: $(@(Waiters 'q8aPost3_wait.ps1').Count)"
Get-Content $LOG -Tail 4
