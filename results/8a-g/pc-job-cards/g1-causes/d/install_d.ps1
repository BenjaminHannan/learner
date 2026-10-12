# Installs diagnostic D (G1 diagnostic: free, read-only measurements on G1's saved 3M and 10M B2 weights) on BensPC as inserted job 47-g1diag.txt
# (a `cmd:` insert that runs custom-io\g1diag.cmd from src-8ag, alone, at the post-G1 waiter's next check point). Run from the folder the Mac copied;
# it needs g1diag.py and g1diag.cmd beside it. It checks the pinned hashes of src-8ag's caps.py, ledger.py and evalx.py, that both final checkpoints
# and the pool files exist, copies g1diag.py to custom-io\g1diag\ and g1diag.cmd to custom-io, runs `g1diag.py --selftest` on the CPU (no GPU, no
# EmbeddingGemma, tiny random models), and only then writes WORK\insert\47-g1diag.txt. It changes nothing in src-8ag, results or pools and deletes nothing.
$IN     = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO    = 'C:\Users\benja\custom-io'
$WORK   = "$CIO\work"
$LOG    = "$WORK\q8aPost-waiter.log"
$PY     = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$EGPATH = 'C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages'
$SRC1   = "$CIO\src-8ag"        # G1's code: custom_io at 612f5c5b01 + the caps fix (read only)
$POOL   = "$WORK\g8a\pools\p10-rung30-s400-a64"
$CK3    = "$WORK\results\8aG1d-pc\8aG1d-3M-s400\B2\checkpoint.pt"
$CK10   = "$WORK\results\8aG1f-pc\8aG1f-10M-s400\B2\checkpoint.pt"
$CAPS   = '3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78'   # g8a\caps.py, G1's (the 36-slot fix)
$LEDGER = '0418BFE77A8DF215C67F48F5F89529C333737BBAA20026B0050CB50ABF946733'   # models\ledger.py
$EVALX  = '35887EC44CE56CF70A6BECBC292AB9999CDBC2A88D1C3F5ED74F8D248CEA0937'   # evalx.py at 612f5c5b01
$INS    = "$WORK\insert\47-g1diag.txt"
$STAMP  = (Get-Date).ToString('yyyyMMdd-HHmm')
function Stamp { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + ' ET' }
function Fail($m) { "FAILED: $m (nothing was inserted; src-8ag, results and pools were not touched)"; exit 1 }
function Hash($p) { if (Test-Path $p) { (Get-FileHash $p).Hash } else { 'missing' } }

# 1. Already installed?
if ((Test-Path "$CIO\g1diag\g1diag.py") -and (Test-Path "$CIO\g1diag.cmd") -and @(Get-ChildItem "$WORK\insert\47-g1diag.txt*" -ErrorAction SilentlyContinue).Count) {
  "g1diag is already installed: $(@(Get-ChildItem "$WORK\insert\47-g1diag.txt*" | ForEach-Object { $_.Name }) -join ', ')"
  'INSTALL D DONE'
  exit 0
}
foreach ($f in @('g1diag.py', 'g1diag.cmd')) { if (-not (Test-Path "$IN\$f")) { Fail "$f missing in $IN" } }
if (-not (Test-Path "$WORK\insert\README.txt")) { Fail 'WORK\insert\README.txt missing (is the post-G1 waiter v3e installed?)' }

# 2. G1's code is G1's; the weights and the pool are there.
foreach ($k in @(@("$SRC1\custom_io\g8a\caps.py", $CAPS), @("$SRC1\custom_io\models\ledger.py", $LEDGER), @("$SRC1\custom_io\evalx.py", $EVALX))) {
  if ((Hash $k[0]) -ne $k[1]) { Fail "$($k[0]) is not G1's ($(Hash $k[0]))" }
}
foreach ($p in @($CK3, $CK10, "$POOL\train.jsonl", "$POOL\charvocab.json", "$POOL\caps.json", "$POOL\dev\in_dist.jsonl", "$POOL\dev\variant.jsonl",
                 "$WORK\results\8aG1d-pc\8aG1d-3M-s400\B2\RESULT.json", "$WORK\results\8aG1f-pc\8aG1f-10M-s400\B2\RESULT.json")) {
  if (-not (Test-Path $p)) { Fail "$p is missing" }
}
"checked: caps.py, ledger.py, evalx.py are G1's; both checkpoints, RESULT.json files and the pool files exist"

# 3. Into place (new files only; an older copy is kept beside it), then the CPU self-test from src-8ag.
New-Item -ItemType Directory -Force "$CIO\g1diag" | Out-Null
if (Test-Path "$CIO\g1diag\g1diag.py") { Copy-Item -Force "$CIO\g1diag\g1diag.py" "$CIO\g1diag\g1diag.py.before-$STAMP" }
if (Test-Path "$CIO\g1diag.cmd") { Copy-Item -Force "$CIO\g1diag.cmd" "$CIO\g1diag.cmd.before-$STAMP" }
Copy-Item -Force "$IN\g1diag.py" "$CIO\g1diag\g1diag.py"
Copy-Item -Force "$IN\g1diag.cmd" "$CIO\g1diag.cmd"
$env:CUDA_VISIBLE_DEVICES = '-1'; $env:PYTHONUTF8 = '1'; $env:PYTHONPATH = $EGPATH
Push-Location $SRC1
$out = @(& $PY "$CIO\g1diag\g1diag.py" --src $SRC1 --selftest 2>&1 | ForEach-Object { "$_" })
$rc = $LASTEXITCODE
Pop-Location
Remove-Item Env:\CUDA_VISIBLE_DEVICES, Env:\PYTHONPATH -ErrorAction SilentlyContinue
$out | Select-Object -Last 3 | ForEach-Object { "  selftest: $_" }
if ($rc -ne 0 -or -not ("$out" -like '*D SELFTEST OK*')) { $out | Select-Object -Last 10; Fail "g1diag.py --selftest failed (rc $rc); g1diag.py and g1diag.cmd were copied into custom-io but no insert was written" }

# 4. The insert file (the waiter reads it at its next check point).
Set-Content -Encoding ascii $INS -Value @('cmd: g1diag.cmd', 'hours: 3')
"$(Stamp) install_d.ps1: custom-io\g1diag\g1diag.py, custom-io\g1diag.cmd and WORK\insert\47-g1diag.txt (G1 diagnostic D, GPU, read only) installed" | Add-Content -Encoding ascii $LOG
"WORK\insert\47-g1diag.txt written:"
Get-Content $INS | ForEach-Object { "  $_" }
"output will be WORK\results\8aG1diag (G1DIAG.md first) and the log WORK\q8aG1diag.log"
'INSTALL D DONE'
