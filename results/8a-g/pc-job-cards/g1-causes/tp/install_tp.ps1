# Installs test T-P on BensPC (G1-OTHER-CAUSES-RANKED-2026-10-12 section 3, cause 3): B2 seed 400 at 3M with self-found programs (self_prog 8), otherwise exactly G1's
# 3M B2. Run by the post-G1 waiter v3e as an inserted job (WORK\insert\46-tp.txt, after 40-g2c10s and before B3 group 1). Run from the folder the Mac copied; it needs
# ledger.py, 8aTP-pc.txt, tpcheck.py and tp.template.md beside it. G1's code folder src-8ag is copied (never changed) to src-tp.new-<stamp>, its pinned hashes are
# checked, models\ledger.py is swapped for the one with self_prog only, and tpcheck.py runs on the CPU (identity with G1's ledger.py at self_prog 0, sizes on torch's
# meta device, the hit picker, loss with self_prog 8, the queue; it needs no EmbeddingGemma weights and no GPU). Only then is the folder renamed src-tp and
# WORK\insert\46-tp.txt written. A failed check renames the new folder src-tp.failed-<stamp>. It stops nothing, never touches G1's runs, results, pools or
# checkpoints, and deletes nothing.
$IN     = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO    = 'C:\Users\benja\custom-io'
$WORK   = "$CIO\work"
$LOG    = "$WORK\q8aPost-waiter.log"
$PY     = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$EGPATH = 'C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages'
$SRC1   = "$CIO\src-8ag"        # G1's code: custom_io at 612f5c5b01 + the caps fix (read only)
$SRCT   = "$CIO\src-tp"
$CAPS   = '3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78'   # g8a\caps.py, G1's (the 36-slot fix)
$CAPSG  = '61DE482D1FA1420D0E8DC702171305CBAB876D7F44183156C9E84B98D6DD5DB0'   # g8a\caps_g.json, G1's pinned caps
$CFG1   = '2849D2B431C6815095732575C36F8294DC36EE49857D16A6DF9571486203B4D3'   # g8a\configs.py at 612f5c5b01 (unchanged here)
$LED1   = '0418BFE77A8DF215C67F48F5F89529C333737BBAA20026B0050CB50ABF946733'   # models\ledger.py at 612f5c5b01 (G1's)
$LEDT   = '5690B77890812C0810C5339A58248F1B41C3A5D000CEA294DD2AC6DF0DA56100'   # the same file plus self_prog (this folder's ledger.py)
$INS    = "$WORK\insert\46-tp.txt"
$STAMP  = (Get-Date).ToString('yyyyMMdd-HHmm')
$script:made = $null
function Stamp { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + ' ET' }
function Fail($m) {
  if ($script:made -and (Test-Path $script:made)) { $n = (Split-Path -Leaf $script:made) -replace '\.new-', '.failed-'; Rename-Item -Path $script:made -NewName $n; "renamed $(Split-Path -Leaf $script:made) to $n (kept)" }
  "FAILED: $m (the waiter, src-8ag and WORK\insert were not changed)"
  exit 1
}
function Hash($p) { if (Test-Path $p) { (Get-FileHash $p).Hash } else { 'missing' } }
function Waiters($name) { @(Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" | Where-Object { $_.CommandLine -like "*$name*" }) }
# Free memory (MB) the OS can still commit; a CPU check starts only with its need plus 2 GB to spare (install_rr ran out at 9:20 PM ET 11 Oct).
function NeedMem($mb, $what) {
  $free = [math]::Floor((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1024)
  if ($free -lt $mb + 2048) { Fail "only $free MB free to commit; $what needs about $mb MB plus 2,048 to spare (run again when a G1 run has ended)" }
  "  memory: $free MB free to commit (need $mb + 2048 for $what)"
}

# 1. Already installed? Everything here, the waiter is v3e and running.
if ((Test-Path "$SRCT\TP-SETUP-OK.txt") -and @(Get-ChildItem "$WORK\insert\46-tp.txt*" -ErrorAction SilentlyContinue).Count) {
  "src-tp and its insert are already installed: $(@(Get-Content "$SRCT\TP-SETUP-OK.txt") -join ' | ') | $(@(Get-ChildItem "$WORK\insert\46-tp.txt*" | ForEach-Object { $_.Name }) -join ', ')"
  'INSTALL TP DONE'
  exit 0
}
foreach ($f in @('ledger.py', '8aTP-pc.txt', 'tpcheck.py', 'tp.template.md')) { if (-not (Test-Path "$IN\$f")) { Fail "$f missing in $IN" } }
if ((Hash "$IN\ledger.py") -ne $LEDT) { Fail "ledger.py here is not the self_prog one ($(Hash "$IN\ledger.py"))" }
if (Test-Path $SRCT) { Fail "$SRCT exists without a finished install (rename it aside by hand first)" }
if (@(Get-ChildItem "$WORK\insert\*-tp.txt*" -ErrorAction SilentlyContinue).Count) { Fail "WORK\insert already holds a tp file: $(@(Get-ChildItem "$WORK\insert\*-tp.txt*" | ForEach-Object { $_.Name }) -join ', ')" }
# (install_rr.ps1 may have started v3e seconds ago: give it up to 2 minutes to write its start line)
for ($t = 0; $t -lt 12; $t++) {
  $start = @(Get-Content $LOG | Where-Object { $_ -like '*chain waiter v3 started*' }) | Select-Object -Last 1
  if ("$start" -like '*(v3e;*') { break }
  Start-Sleep -Seconds 10
}
if ("$start" -notlike '*(v3e;*') { Fail "the running waiter is not v3e (inserted jobs from another src folder need v3e): $start" }
$w = @(Waiters 'q8aPost3_wait.ps1')
if ($w.Count -ne 1) { Fail "expected one q8aPost3_wait.ps1 waiter, found $($w.Count)" }
if (-not (Test-Path "$WORK\insert\README.txt")) { Fail 'WORK\insert\README.txt missing (is v3e installed?)' }
"waiter v3e (pid $($w[0].ProcessId)) is running; the insert will run at its next check point (after 40-g2c10s, before B3 group 1)"

# 2. Copy G1's code and check it is G1's.
foreach ($k in @(@("$SRC1\custom_io\g8a\caps.py", $CAPS), @("$SRC1\custom_io\g8a\caps_g.json", $CAPSG), @("$SRC1\custom_io\g8a\configs.py", $CFG1), @("$SRC1\custom_io\models\ledger.py", $LED1))) {
  if ((Hash $k[0]) -ne $k[1]) { Fail "$($k[0]) is not G1's ($(Hash $k[0]))" }
}
$new = "$SRCT.new-$STAMP"
if (Test-Path $new) { Fail "$new already exists" }
New-Item -ItemType Directory $new | Out-Null
$script:made = $new
Copy-Item -Recurse "$SRC1\custom_io" "$new\custom_io"
foreach ($k in @(@("$new\custom_io\g8a\caps.py", $CAPS), @("$new\custom_io\g8a\caps_g.json", $CAPSG), @("$new\custom_io\g8a\configs.py", $CFG1), @("$new\custom_io\models\ledger.py", $LED1))) {
  if ((Hash $k[0]) -ne $k[1]) { Fail "the copy of $(Split-Path -Leaf $k[0]) differs from src-8ag's" }
}
Copy-Item -Force "$IN\ledger.py" "$new\custom_io\models\ledger.py"
New-Item -ItemType Directory -Force "$new\custom_io\queue_local" | Out-Null
Copy-Item -Force "$IN\8aTP-pc.txt" "$new\custom_io\queue_local\8aTP-pc.txt"
if ((Hash "$new\custom_io\models\ledger.py") -ne $LEDT) { Fail 'ledger.py did not copy' }
"src-tp: copied src-8ag's custom_io into $(Split-Path -Leaf $new); caps.py, caps_g.json, configs.py and ledger.py were G1's; ledger.py now has self_prog"

# 3. CPU check: identity with G1's ledger.py at self_prog 0, 3,544,913 trained at self_prog 8 inside the band (meta device), hit picker, loss, queue.
NeedMem 2000 'tpcheck (python + torch, three 3.3M-parameter models on the CPU)'
$env:CUDA_VISIBLE_DEVICES = '-1'; $env:PYTHONUTF8 = '1'; $env:PYTHONPATH = $EGPATH
Push-Location $new
$out = @(& $PY "$IN\tpcheck.py" "$SRC1\custom_io\models\ledger.py" 2>&1 | ForEach-Object { "$_" })
$rc = $LASTEXITCODE
Pop-Location
Remove-Item Env:\CUDA_VISIBLE_DEVICES, Env:\PYTHONPATH -ErrorAction SilentlyContinue
$out | Select-Object -Last 3 | ForEach-Object { "  tpcheck: $_" }
if ($rc -ne 0 -or -not ("$out" -like '*TP CPU CHECK OK*')) { $out | Select-Object -Last 8; Fail "tpcheck failed (rc $rc)" }
Set-Content -Encoding ascii "$new\TP-SETUP-OK.txt" -Value @("caps.py $CAPS", "caps_g.json $CAPSG", "configs.py $CFG1 (G1's, unchanged)", "ledger.py $LEDT (G1's $LED1 + self_prog)",
  'custom_io copied from src-8ag (612f5c5b01 + the caps fix); queue 8aTP; tpcheck ok (CPU, meta device); install_tp.ps1', (Stamp))

# 4. Into place: the folder, the card template, then the insert file (the waiter reads it at its next check point).
try { Rename-Item -Path $new -NewName (Split-Path -Leaf $SRCT) -ErrorAction Stop } catch { Fail "could not rename $(Split-Path -Leaf $new) to src-tp: $($_.Exception.Message)" }
$script:made = $null
if (Test-Path "$CIO\tp.template.md") { Copy-Item -Force "$CIO\tp.template.md" "$CIO\tp.template.md.before-$STAMP" }
Copy-Item -Force "$IN\tp.template.md" "$CIO\tp.template.md"
Set-Content -Encoding ascii $INS -Value @('queue: 8aTP', 'src: src-tp', "caps: $CAPS", 'card: tp.template.md')
"$(Stamp) install_tp.ps1: src-tp (G1's code + self_prog in ledger.py) and WORK\insert\46-tp.txt (test T-P, B2 3M s400) installed" | Add-Content -Encoding ascii $LOG
"src-tp: in place; card template tp.template.md; WORK\insert\46-tp.txt written:"
Get-Content $INS | ForEach-Object { "  $_" }
'INSTALL TP DONE'
