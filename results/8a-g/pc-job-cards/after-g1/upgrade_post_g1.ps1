# Upgrades the post-G1 chain on BensPC to version 2 (spec addendum O), on Ben's go. Run after install_post_g1.ps1 and while G1 still runs;
# it starts no GPU work itself. Version 2 adds B3 group 1 at 3M (seed 400, then seed 401 only if alive) and splits test GX by seed.
# Expects in C:\Users\benja\custom-io\post-g1-in: q8aPost2_wait.ps1, b3_readout.py, b3_capcheck.py, gx-head.md, the queue files 8aGXs400-pc.txt and
# 8aGXs401-pc.txt (src-8gx), 8aG2C3s401-pc.txt (src-b3), 8aB3G1s400-pc.txt and 8aB3G1s401-pc.txt (src-b3r), the cards fc100, g2c3, g2c3s401,
# g2c10, c30, b3g1 (.md), long-dev.jsonl (B3-5's held-out long rows); and, once it exists, b3r.zip (custom_io of PR #56 with the H1 round-cap fix).
# Safe to run again: with v2 already running it only sets up what is new (src-b3r) and refreshes files. Stops at the first problem.
$CIO    = 'C:\Users\benja\custom-io'
$WORK   = "$CIO\work"
$IN     = "$CIO\post-g1-in"
$SRCGX  = "$CIO\src-8gx"
$SRCB3  = "$CIO\src-b3"
$SRCB3R = "$CIO\src-b3r"
$B3IN   = "$WORK\b3-inputs"
$PY     = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$JSONB3 = 'BD81C67F0B6F33686718587A3FBDCD73E939C1FF9CB832DC6D68F34DEE4F7550'    # g8a/caps_b3.json (unchanged since c24bce9489)
$LDEV   = '7AB9B5B9E897209760CDF89EB8A21519D74E1385182B91B26B0ED899CA280AFB'    # B3-5's held-out long rows (1,360; f1to6a 4265e32b7f custom_io/g8a/long_dev/)
$GXQ    = @('8aGXs400-pc.txt', '8aGXs401-pc.txt')
$B3Q    = @('8aG2C3s401-pc.txt')
$B3RQ   = @('8aB3G1s400-pc.txt', '8aB3G1s401-pc.txt')
$CARDS  = @('fc100', 'g2c3', 'g2c3s401', 'g2c10', 'c30', 'b3g1')
function Fail($m) { "NEEDS ATTENTION: $m"; exit 1 }
function Hash($f) { (Get-FileHash $f).Hash }
# A failed src-b3r setup renames the new folder aside (nothing is deleted), so a rerun with a better b3r.zip can unpack afresh.
function FailB3R($m) { $n = 'src-b3r.failed-' + (Get-Date).ToString('yyyyMMdd-HHmm'); Rename-Item -Path $SRCB3R -NewName $n; Fail "$m (src-b3r renamed to $n)" }
function Stamp { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + ' ET' }
# Callers wrap it in @(): a function's one-item array unrolls to a bare CimInstance, whose .Count is empty in Windows PowerShell 5.1 (seen 10-09: v1 was
# not stopped).
function Waiters($name) { @(Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" | Where-Object { $_.CommandLine -like "*$name*" }) }
function Unpack($zip, $dir, $marker) {
  if (Test-Path "$dir\$marker") { return $false }
  if ((Test-Path $dir) -and (@(Get-ChildItem $dir -Force).Count -gt 0)) { Fail "$dir exists and is not empty but has no ${marker}: not overwriting" }
  Expand-Archive -Path $zip -DestinationPath $dir
  return $true
}
# CPU-only python in a code folder; returns its output lines, exit code in $rc. The GPU stays G1's.
function CpuPy($dir, $pyargs) {
  $env:CUDA_VISIBLE_DEVICES = '-1'
  $env:PYTHONUTF8 = '1'
  Push-Location $dir
  $out = @(& $PY @pyargs 2>&1 | ForEach-Object { "$_" })
  $script:rc = $LASTEXITCODE
  Pop-Location
  Remove-Item Env:\CUDA_VISIBLE_DEVICES
  return $out
}

$need = @('q8aPost2_wait.ps1', 'b3_readout.py', 'b3_capcheck.py', 'gx-head.md', 'long-dev.jsonl') + $GXQ + $B3Q + $B3RQ + ($CARDS | ForEach-Object { "$_.md" })
foreach ($f in $need) { if (-not (Test-Path "$IN\$f")) { Fail "missing $IN\$f" } }
if (-not (Test-Path "$SRCGX\GX-SETUP-OK.txt")) { Fail 'src-8gx is not set up: run install_post_g1.ps1 first' }
if (-not (Test-Path "$SRCB3\B3-SETUP-OK.txt")) { Fail 'src-b3 is not set up: run install_post_g1.ps1 first' }
if ((Hash "$B3IN\caps_b3.json") -ne $JSONB3) { Fail 'work\b3-inputs\caps_b3.json missing or its hash is wrong' }

# 1. B3's code with the round-cap fix into src-b3r (only when b3r.zip is here) and its CPU checks.
if (Test-Path "$IN\b3r.zip") {
  if (Unpack "$IN\b3r.zip" $SRCB3R 'B3R-SETUP-OK.txt') {
    if ((Hash "$SRCB3R\custom_io\g8a\caps_b3.json") -ne $JSONB3) { FailB3R 'src-b3r caps_b3.json hash wrong' }
    $out = CpuPy $SRCB3R @("$IN\b3_capcheck.py", $SRCB3R, "$B3IN\caps_b3.json")
    $out | Select-Object -Last 2
    if ($rc -ne 0) { FailB3R 'b3_capcheck: B3''s thinking-round cap is not 32 in this code: src-b3r NOT set up' }
    $out = CpuPy $SRCB3R @('-m', 'custom_io.tests.test_g8a')
    $out | Select-Object -Last 2
    if ($rc -ne 0 -or ($out -match '^FAIL')) { FailB3R "test_g8a failed (rc $rc): src-b3r NOT set up" }
    $out = CpuPy $SRCB3R @('-m', 'custom_io.tests.test_b3_run')
    $out | Select-Object -Last 2
    if (-not ($out -and ($out[-1] -match 'ALL OK'))) { FailB3R 'test_b3_run did not end "ALL OK": src-b3r NOT set up' }
    $capsr = Hash "$SRCB3R\custom_io\g8a\caps.py"
    Set-Content -Encoding ascii "$SRCB3R\B3R-SETUP-OK.txt" -Value @("caps.py $capsr", "caps_b3.json $JSONB3", 'b3_capcheck 32, test_g8a ok, test_b3_run ALL OK (CPU)', (Stamp))
    "src-b3r: set up (caps.py $capsr), round cap 32, test_g8a ok, test_b3_run ALL OK"
  } else { 'src-b3r: already set up (B3R-SETUP-OK.txt present)' }
} else { 'b3r.zip not here: src-b3r not set up yet (the waiter holds before B3 until it is; rerun this script with b3r.zip)' }
if ((Hash "$IN\long-dev.jsonl") -ne $LDEV) { Fail 'long-dev.jsonl hash wrong' }
Copy-Item -Force "$IN\long-dev.jsonl" "$B3IN\long-dev.jsonl"
'long-dev.jsonl (1,360 held-out long rows, hash ok) copied to work\b3-inputs'

# 2. Queue files, card templates (the GX card = gx-head.md + the experts thread's 8aGX-card.md), the readout and the cap check.
foreach ($f in $GXQ) { Copy-Item -Force "$IN\$f" "$SRCGX\custom_io\queue_local\" }
foreach ($f in $B3Q) { Copy-Item -Force "$IN\$f" "$SRCB3\custom_io\queue_local\" }
if (Test-Path "$SRCB3R\B3R-SETUP-OK.txt") { New-Item -ItemType Directory -Force "$SRCB3R\custom_io\queue_local" | Out-Null; foreach ($f in $B3RQ) { Copy-Item -Force "$IN\$f" "$SRCB3R\custom_io\queue_local\" } }
@(Get-Content "$IN\gx-head.md") + @(Get-Content "$SRCGX\custom_io\queue_local\8aGX-card.md") | Set-Content -Encoding ascii "$CIO\gx.template.md"
foreach ($c in $CARDS) { Copy-Item -Force "$IN\$c.md" "$CIO\$c.template.md" }
Copy-Item -Force "$IN\b3_readout.py" "$CIO\b3_readout.py"
Copy-Item -Force "$IN\b3_capcheck.py" "$CIO\b3_capcheck.py"
'copied the queue files, card templates, b3_readout.py and b3_capcheck.py'

# 3. Waiter v2 replaces v1 while v1 still waits for G1.
$v2 = @(Waiters 'q8aPost2_wait.ps1')
if ($v2.Count -gt 0) { "chain waiter v2 already runs (pid $($v2[0].ProcessId)): files refreshed, nothing restarted"; exit 0 }
$v1 = @(Waiters 'q8aPost_wait.ps1')
if ($v1.Count -gt 0) {
  if (@(Get-Content "$WORK\q8aPost-waiter.log" -ErrorAction SilentlyContinue) -match 'gate G1 has ended') { Fail 'waiter v1 has already started the chain: not replacing it' }
  foreach ($p in $v1) { Stop-Process -Id $p.ProcessId -Force; "stopped chain waiter v1 (pid $($p.ProcessId)); it was still waiting for G1 and had started nothing" }
  "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET waiter v1 stopped by upgrade_post_g1.ps1 (replaced by v2)" | Add-Content -Encoding ascii "$WORK\q8aPost-waiter.log"
}
Copy-Item -Force "$IN\q8aPost2_wait.ps1" "$CIO\q8aPost2_wait.ps1"
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\benja\custom-io\q8aPost2_wait.ps1'}
"chain waiter v2 started: ReturnValue $($r.ReturnValue), pid $($r.ProcessId)"
Start-Sleep -Seconds 10
Get-Content "$WORK\q8aPost-waiter.log" -Tail 3 -ErrorAction SilentlyContinue
