# Installs the post-G1 chain on BensPC (spec addenda K, L and M). Run ONCE, after Ben's go, while G1 still runs; it starts no GPU work itself.
# Expects in C:\Users\benja\custom-io\post-g1-in (from the Mac): gx.zip (custom_io of the experts branch at c1464d19b7), b3.zip (custom_io
# at c24bce9489), cloze_long.py (data_pool/cloze_long.py at 3d0afbeadd), q8aPost_wait.ps1, 8aFC-pc.txt, 8aC30-pc.txt, fc100.md, c30.md.
# Prints what it did and stops at the first problem.
$CIO    = 'C:\Users\benja\custom-io'
$WORK   = "$CIO\work"
$IN     = "$CIO\post-g1-in"
$SRC    = "$CIO\src-8ag"
$SRCGX  = "$CIO\src-8gx"
$SRCB3  = "$CIO\src-b3"
$B3IN   = "$WORK\b3-inputs"
$PY     = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$CAPS   = '3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78'    # caps.py of G1 and of the experts code
$CAPSB3 = 'D276FAC05E1127D9979E9B8EA3A4F4E6CC4D7BAC33C218FA164117B60F1B4AA8'    # caps.py at c24bce9489
$JSONB3 = 'BD81C67F0B6F33686718587A3FBDCD73E939C1FF9CB832DC6D68F34DEE4F7550'    # g8a/caps_b3.json at c24bce9489
$LONG   = 'FF6A2E12CF9E4B6A3880C503274898F64B3CB14CBAA853CEEAEB51819EDB8CC9'    # data_pool/cloze_long.py at 3d0afbeadd
function Fail($m) { "NEEDS ATTENTION: $m"; exit 1 }
function Hash($f) { (Get-FileHash $f).Hash }
# Unpack a git-archive zip into an empty folder (or keep a folder whose marker says it is already set up).
function Unpack($zip, $dir, $marker) {
  if (Test-Path "$dir\$marker") { return $false }
  if ((Test-Path $dir) -and (@(Get-ChildItem $dir -Force).Count -gt 0)) { Fail "$dir exists and is not empty but has no ${marker}: not overwriting" }
  Expand-Archive -Path $zip -DestinationPath $dir
  return $true
}
# CPU-only test in a code folder; returns its output lines. The GPU stays G1's.
function CpuTest($dir, $module) {
  $env:CUDA_VISIBLE_DEVICES = '-1'
  $env:PYTHONUTF8 = '1'
  Push-Location $dir
  $out = @(& $PY -m $module 2>&1 | ForEach-Object { "$_" })
  $script:rc = $LASTEXITCODE
  Pop-Location
  Remove-Item Env:\CUDA_VISIBLE_DEVICES
  return $out
}
function Stamp { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + ' ET' }

if (@(Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" | Where-Object { $_.CommandLine -like '*q8aPost_wait.ps1*' }).Count -gt 0) { Fail 'a post-G1 chain waiter already runs' }
foreach ($f in 'gx.zip', 'b3.zip', 'cloze_long.py', 'q8aPost_wait.ps1', '8aFC-pc.txt', '8aC30-pc.txt', 'fc100.md', 'c30.md') { if (-not (Test-Path "$IN\$f")) { Fail "missing $IN\$f" } }
if ((Hash "$SRC\custom_io\g8a\caps.py") -ne $CAPS) { Fail 'src-8ag caps.py hash wrong' }
if ((Hash "$IN\cloze_long.py") -ne $LONG) { Fail 'cloze_long.py hash wrong' }

# 1. Experts code into src-8gx and its CPU check (8aGX-card.md setup steps 1-2).
if (Unpack "$IN\gx.zip" $SRCGX 'GX-SETUP-OK.txt') {
  if ((Hash "$SRCGX\custom_io\g8a\caps.py") -ne $CAPS) { Fail 'src-8gx caps.py hash wrong' }
  if (-not (Test-Path "$SRCGX\custom_io\queue_local\8aGX-pc.txt")) { Fail 'src-8gx has no 8aGX-pc.txt' }
  $out = CpuTest $SRCGX 'custom_io.tests.test_moe'
  $out | Select-Object -Last 3
  if (-not ($out -and ($out[-1] -match 'ALL OK'))) { Fail 'test_moe did not end "ALL OK": GX NOT set up' }
  Set-Content -Encoding ascii "$SRCGX\GX-SETUP-OK.txt" -Value @("caps.py $CAPS", 'test_moe ALL OK (CPU)', (Stamp))
  'src-8gx: set up, caps hash ok, test_moe ALL OK'
} else { 'src-8gx: already set up (GX-SETUP-OK.txt present)' }

# 2. B3 code (c24bce9489) into src-b3, its inputs into WORK\b3-inputs, and its CPU check.
if (Unpack "$IN\b3.zip" $SRCB3 'B3-SETUP-OK.txt') {
  if ((Hash "$SRCB3\custom_io\g8a\caps.py") -ne $CAPSB3) { Fail 'src-b3 caps.py hash wrong' }
  if ((Hash "$SRCB3\custom_io\g8a\caps_b3.json") -ne $JSONB3) { Fail 'src-b3 caps_b3.json hash wrong' }
  New-Item -ItemType Directory -Force $B3IN | Out-Null
  Copy-Item -Force "$IN\cloze_long.py" "$B3IN\cloze_long.py"
  Copy-Item -Force "$SRCB3\custom_io\g8a\caps_b3.json" "$B3IN\caps_b3.json"
  $out = CpuTest $SRCB3 'custom_io.tests.test_g8a'
  $out | Select-Object -Last 3
  if ($rc -ne 0 -or ($out -match '^FAIL')) { Fail "test_g8a failed (rc $rc): fc100 NOT set up" }
  Set-Content -Encoding ascii "$SRCB3\B3-SETUP-OK.txt" -Value @("caps.py $CAPSB3", "caps_b3.json $JSONB3", "cloze_long.py $LONG", 'test_g8a ok (CPU)', (Stamp))
  'src-b3: set up, hashes ok, test_g8a ok; cloze_long.py and caps_b3.json in work\b3-inputs'
} else { 'src-b3: already set up (B3-SETUP-OK.txt present)' }

# 3. fc100's and c30's queue files into src-b3 (both run on c24bce9489 at the B3 caps), card templates and the waiter.
Copy-Item -Force "$IN\8aFC-pc.txt", "$IN\8aC30-pc.txt" "$SRCB3\custom_io\queue_local\"
Copy-Item -Force "$IN\fc100.md" "$CIO\fc100.template.md"
Copy-Item -Force "$IN\c30.md" "$CIO\c30.template.md"
Copy-Item -Force "$IN\q8aPost_wait.ps1" "$CIO\q8aPost_wait.ps1"
'copied 8aFC-pc.txt and 8aC30-pc.txt to src-b3 queue_local; card templates and waiter to custom-io'

# 4. Start the chain waiter detached.
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\benja\custom-io\q8aPost_wait.ps1'}
"chain waiter started: ReturnValue $($r.ReturnValue), pid $($r.ProcessId)"
Start-Sleep -Seconds 10
Get-Content "$WORK\q8aPost-waiter.log" -Tail 3 -ErrorAction SilentlyContinue
