# Installs the post-G1 chain on BensPC (spec addendum K). Run ONCE, after Ben's go, while G1 still runs; it starts no GPU work itself.
# Expects in C:\Users\benja\custom-io\post-g1-in: gx.zip (custom_io of the experts branch at the pinned commit, from git archive),
# q8aPost_wait.ps1, 8aFC-pc.txt, 8aC30-pc.txt, fc100.md, c30.md. Prints what it did and stops at the first problem.
$CIO   = 'C:\Users\benja\custom-io'
$IN    = "$CIO\post-g1-in"
$SRC   = "$CIO\src-8ag"
$SRCGX = "$CIO\src-8gx"
$PY    = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$CAPS  = '3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78'
function Fail($m) { "NEEDS ATTENTION: $m"; exit 1 }

if (@(Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" | Where-Object { $_.CommandLine -like '*q8aPost_wait.ps1*' }).Count -gt 0) { Fail 'a post-G1 chain waiter already runs' }
foreach ($f in 'gx.zip', 'q8aPost_wait.ps1', '8aFC-pc.txt', '8aC30-pc.txt', 'fc100.md', 'c30.md') { if (-not (Test-Path "$IN\$f")) { Fail "missing $IN\$f" } }
if ((Get-FileHash "$SRC\custom_io\g8a\caps.py").Hash -ne $CAPS) { Fail 'src-8ag caps.py hash wrong' }

# 1. GX code into src-8gx and the CPU check (8aGX-card.md setup steps 1-2). CPU only: the GPU stays G1's.
if (Test-Path "$SRCGX\GX-SETUP-OK.txt") {
  'src-8gx: already set up (GX-SETUP-OK.txt present)'
} else {
  if ((Test-Path $SRCGX) -and (@(Get-ChildItem $SRCGX -Force).Count -gt 0)) { Fail "$SRCGX exists and is not empty but has no GX-SETUP-OK.txt: not overwriting" }
  Expand-Archive -Path "$IN\gx.zip" -DestinationPath $SRCGX
  if ((Get-FileHash "$SRCGX\custom_io\g8a\caps.py").Hash -ne $CAPS) { Fail 'src-8gx caps.py hash wrong' }
  if (-not (Test-Path "$SRCGX\custom_io\queue_local\8aGX-pc.txt")) { Fail 'src-8gx has no 8aGX-pc.txt' }
  $env:CUDA_VISIBLE_DEVICES = '-1'
  $env:PYTHONUTF8 = '1'
  Push-Location $SRCGX
  $out = @(& $PY -m custom_io.tests.test_moe 2>&1 | ForEach-Object { "$_" })
  Pop-Location
  $out | Select-Object -Last 3
  if (-not ($out -and ($out[-1] -match 'ALL OK'))) { Fail 'test_moe did not end "ALL OK": GX NOT set up' }
  Set-Content -Encoding ascii "$SRCGX\GX-SETUP-OK.txt" -Value @("caps.py $CAPS", 'test_moe ALL OK (CPU)', "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET")
  'src-8gx: set up, caps hash ok, test_moe ALL OK'
}

# 2. Queue files (new files; the running G1 queues read theirs at start) and card templates.
Copy-Item -Force "$IN\8aFC-pc.txt", "$IN\8aC30-pc.txt" "$SRC\custom_io\queue_local\"
Copy-Item -Force "$IN\fc100.md" "$CIO\fc100.template.md"
Copy-Item -Force "$IN\c30.md" "$CIO\c30.template.md"
Copy-Item -Force "$IN\q8aPost_wait.ps1" "$CIO\q8aPost_wait.ps1"
'copied 8aFC-pc.txt and 8aC30-pc.txt to src-8ag queue_local; card templates and waiter to custom-io'

# 3. Start the chain waiter detached.
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\benja\custom-io\q8aPost_wait.ps1'}
"chain waiter started: ReturnValue $($r.ReturnValue), pid $($r.ProcessId)"
Start-Sleep -Seconds 10
Get-Content "$CIO\work\q8aPost-waiter.log" -Tail 3 -ErrorAction SilentlyContinue
