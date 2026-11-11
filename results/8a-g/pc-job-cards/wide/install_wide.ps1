# Installs test WIDE on BensPC (roadmap spec addendum AB, 11 Oct 2026): B2 seed 400 at about 10M by width (rung 10MW), run by the post-G1
# waiter v3e as an inserted job after B3 group 2 at 3M (G2f). Run from the folder the Mac copied; it needs configs.py, 8aWIDE-pc.txt,
# widecheck.py and wide.template.md beside it. G1's code folder src-8ag is copied (never changed) to src-wide.new-<stamp>, its pinned hashes
# are checked, configs.py is swapped for the one with rung 10MW only, and widecheck.py builds the model on torch's meta device (shapes only;
# G1 keeps the GPU and most of the memory). Only then is the folder renamed src-wide and WORK\insert\20-wide.txt written. A failed check
# renames the new folder src-wide.failed-<stamp>. It stops nothing, never touches G1's runs, results or pools, and deletes nothing.
$IN     = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO    = 'C:\Users\benja\custom-io'
$WORK   = "$CIO\work"
$LOG    = "$WORK\q8aPost-waiter.log"
$PY     = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$EGPATH = 'C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages'
$SRC1   = "$CIO\src-8ag"        # G1's code: custom_io at 612f5c5b01 + the caps fix (read only)
$SRCW   = "$CIO\src-wide"
$CAPS   = '3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78'   # g8a\caps.py, G1's (the 36-slot fix)
$CAPSG  = '61DE482D1FA1420D0E8DC702171305CBAB876D7F44183156C9E84B98D6DD5DB0'   # g8a\caps_g.json, G1's pinned caps
$CFG1   = '2849D2B431C6815095732575C36F8294DC36EE49857D16A6DF9571486203B4D3'   # g8a\configs.py at 612f5c5b01
$CFGW   = '4D273A6405AD880326435A2D991B295041BECF8225712645E7F5B492F0F411A8'   # the same file plus the rung 10MW row (this folder's configs.py)
$INS    = "$WORK\insert\20-wide.txt"
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
if ((Test-Path "$SRCW\WIDE-SETUP-OK.txt") -and @(Get-ChildItem "$WORK\insert\20-wide.txt*" -ErrorAction SilentlyContinue).Count) {
  "src-wide and its insert are already installed: $(@(Get-Content "$SRCW\WIDE-SETUP-OK.txt") -join ' | ') | $(@(Get-ChildItem "$WORK\insert\20-wide.txt*" | ForEach-Object { $_.Name }) -join ', ')"
  'INSTALL WIDE DONE'
  exit 0
}
foreach ($f in @('configs.py', '8aWIDE-pc.txt', 'widecheck.py', 'wide.template.md')) { if (-not (Test-Path "$IN\$f")) { Fail "$f missing in $IN" } }
if ((Hash "$IN\configs.py") -ne $CFGW) { Fail "configs.py here is not the rung-10MW one ($(Hash "$IN\configs.py"))" }
if (Test-Path $SRCW) { Fail "$SRCW exists without a finished install (rename it aside by hand first)" }
if (@(Get-ChildItem "$WORK\insert\*wide*" -ErrorAction SilentlyContinue).Count) { Fail "WORK\insert already holds a wide file: $(@(Get-ChildItem "$WORK\insert\*wide*" | ForEach-Object { $_.Name }) -join ', ')" }
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
"waiter v3e (pid $($w[0].ProcessId)) is running; the insert will run at its next check point (after group 2 at 3M, if it has not passed it)"

# 2. Copy G1's code and check it is G1's.
foreach ($k in @(@("$SRC1\custom_io\g8a\caps.py", $CAPS), @("$SRC1\custom_io\g8a\caps_g.json", $CAPSG), @("$SRC1\custom_io\g8a\configs.py", $CFG1))) {
  if ((Hash $k[0]) -ne $k[1]) { Fail "$($k[0]) is not G1's ($(Hash $k[0]))" }
}
$new = "$SRCW.new-$STAMP"
if (Test-Path $new) { Fail "$new already exists" }
New-Item -ItemType Directory $new | Out-Null
$script:made = $new
Copy-Item -Recurse "$SRC1\custom_io" "$new\custom_io"
foreach ($k in @(@("$new\custom_io\g8a\caps.py", $CAPS), @("$new\custom_io\g8a\caps_g.json", $CAPSG), @("$new\custom_io\g8a\configs.py", $CFG1))) {
  if ((Hash $k[0]) -ne $k[1]) { Fail "the copy of $(Split-Path -Leaf $k[0]) differs from src-8ag's" }
}
Copy-Item -Force "$IN\configs.py" "$new\custom_io\g8a\configs.py"
New-Item -ItemType Directory -Force "$new\custom_io\queue_local" | Out-Null
Copy-Item -Force "$IN\8aWIDE-pc.txt" "$new\custom_io\queue_local\8aWIDE-pc.txt"
if ((Hash "$new\custom_io\g8a\configs.py") -ne $CFGW) { Fail 'configs.py did not copy' }
"src-wide: copied src-8ag's custom_io into $(Split-Path -Leaf $new); caps.py, caps_g.json and configs.py were G1's; configs.py now has rung 10MW"

# 3. CPU check on the meta device: queue parses, B2 at 10MW = 10,173,509 trained, 448 wide, 2 blocks, 12 rounds, inside the band.
NeedMem 1500 'widecheck (python + torch, models on the meta device)'
$env:CUDA_VISIBLE_DEVICES = '-1'; $env:PYTHONUTF8 = '1'; $env:PYTHONPATH = $EGPATH
Push-Location $new
$out = @(& $PY "$IN\widecheck.py" 2>&1 | ForEach-Object { "$_" })
$rc = $LASTEXITCODE
Pop-Location
Remove-Item Env:\CUDA_VISIBLE_DEVICES, Env:\PYTHONPATH -ErrorAction SilentlyContinue
$out | Select-Object -Last 2 | ForEach-Object { "  widecheck: $_" }
if ($rc -ne 0 -or -not ("$out" -like '*WIDE CPU CHECK OK*')) { $out | Select-Object -Last 8; Fail "widecheck failed (rc $rc)" }
Set-Content -Encoding ascii "$new\WIDE-SETUP-OK.txt" -Value @("caps.py $CAPS", "caps_g.json $CAPSG", "configs.py $CFGW (G1's $CFG1 + rung 10MW)",
  'custom_io copied from src-8ag (612f5c5b01 + the caps fix); queue 8aWIDE; widecheck ok (CPU, meta device); install_wide.ps1', (Stamp))

# 4. Into place: the folder, the card template, then the insert file (the waiter reads it at its next check point).
try { Rename-Item -Path $new -NewName (Split-Path -Leaf $SRCW) -ErrorAction Stop } catch { Fail "could not rename $(Split-Path -Leaf $new) to src-wide: $($_.Exception.Message)" }
$script:made = $null
if (Test-Path "$CIO\wide.template.md") { Copy-Item -Force "$CIO\wide.template.md" "$CIO\wide.template.md.before-$STAMP" }
Copy-Item -Force "$IN\wide.template.md" "$CIO\wide.template.md"
Set-Content -Encoding ascii $INS -Value @('queue: 8aWIDE', 'src: src-wide', "caps: $CAPS", 'card: wide.template.md')
"$(Stamp) install_wide.ps1: src-wide (G1's code + rung 10MW) and WORK\insert\20-wide.txt (test WIDE, B2 10MW s400) installed" | Add-Content -Encoding ascii $LOG
"src-wide: in place; card template wide.template.md; WORK\insert\20-wide.txt written:"
Get-Content $INS | ForEach-Object { "  $_" }
'INSTALL WIDE DONE'
