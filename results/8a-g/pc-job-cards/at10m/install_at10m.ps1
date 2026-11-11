# Installs the agent model's 10M run (B3AT, arm AT, rung 10M, seed 400, queue 8aAT10M) on BensPC as two inserted jobs of the post-G1 chain waiter v3e (big-run PLAN.md eighteenth Addendum
# 10-12): WORK\insert\15-at10mgate.txt (cmd: at10m_gate.cmd, reads AT-1 against G2f and g2c3s and, unless "not proved wrong", turns 16 into a no-op) and WORK\insert\16-at10m.txt
# (queue 8aAT10M from src-at10m). Run from the folder the Mac copied (in-at10m), AFTER install_agent.ps1 printed INSTALL AGENT DONE and before the waiter ends G2f (the inserts are listed
# once, at its first check point, right after G2f). It needs src-at (install_agent's, commit 6e72a5fae5, its pinned hashes) and WORK\insert\11-at.txt.
# The 10M run checkpoints every 500 updates and resumes after a restart (--ckpt-every 500 --resume): that needs the changed train.py in overlay\ (the only changed file of
# commit 6e72a5fae5 besides one new test). src-at is the AT-1 3M run's code and is NOT touched: this script builds a separate code folder src-at10m = a copy of src-at's custom_io
# (every file's hash checked equal to src-at's) + the overlay (the original train.py's hash checked, then replaced; test_ckpt.py added) + queue_local\8aAT10M-pc.txt, runs at10mcheck.py
# (the 10M queue, the trained counts of AT and PTS at 10M, the overlay applies; CPU, no GPU, no Gemma weights), runs the new test (custom_io.tests.test_ckpt, CPU, a few minutes: tiny
# plain and agent models, interrupted == uninterrupted bit for bit) and the gate's self-test, and only then writes the files (temp names first, renamed at the end; a failure removes
# what this run made). It copies the gate files and the card template into custom-io. It stops nothing, touches no run, result, pool or checkpoint, and deletes nothing it did not make
# itself in this run. Run again when already installed: it says so and prints INSTALL AT10M DONE.
$IN     = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO    = 'C:\Users\benja\custom-io'
$WORK   = "$CIO\work"
$LOG    = "$WORK\q8aPost-waiter.log"
$PY     = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$EGPATH = 'C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages'
$INS    = "$WORK\insert"
$SRC    = "$CIO\src-at"                 # the AT-1 3M run's code: read only here
$SRC10  = "$CIO\src-at10m"              # this run's code: a copy of src-at's custom_io + the overlay
$QDIR   = "$SRC10\custom_io\queue_local"
$QNAME  = '8aAT10M-pc.txt'
$QHASH  = 'D0D19059F73283DE2AFA831E652703541CA25653CDC3DFD5296E85E7F6BA3F2A'   # this folder's queue file
$CAPS   = '433475405AE7263579EBF4B9633916842567A5B1B1F3A8930311945E504F62D3'   # g8a\caps.py of src-at (install_agent's pin)
$JSONG2 = 'EE551D3AACBF9EC02D2AC7F5E7E6E12F44E15ABA2C39F5F38C3F1E3EC12D7ED4'   # g8a\caps_b3g2.json
$SHAAT  = '6e72a5fae5'
# the overlay (checkpoint + resume): train.py replaces commit 6e72a5fae5's (hash pinned below), tests\test_ckpt.py is new; local_runner.py is NOT changed (a rerun never wipes the run's folder)
$TRAIN0 = 'E05762ECCA1AF18F6260F09E5974E03B884E2F5FF5C21A4B801EED913D16793D'   # custom_io\train.py at 6e72a5fae5
$OVER = [ordered]@{
  'train.py' = 'E75E45FA43C6A6422C0A0E4222E05D8AFC27580EC6551100680ED8F9ECDC5015'
  'tests\test_ckpt.py' = 'CECFDC0C945DD9530FA448E12FEE0D01D6841C8B2C14F239B8864082A725F1E2' }
# src-at's pinned files (the same list and hashes install_agent.ps1 checks for the AT piece)
$EXP = [ordered]@{
  'models\b3at.py' = '5B10AAC1F20914BAA72DFEA114379682E6DDFC1DBDEE2F749A546760E7FC1768'
  'models\b3g2.py' = 'A4C61F0B567EC7E62B3233549BE63ECA7BCA2A3F35A934DFC217FA49390868CE'
  'models\writer.py' = 'F3A40AD58749BBC24A964942DC650C79864D6A74442628AAC7D752730E73309E'
  'models\b3.py' = 'F3EF34D9F13256CCEE1CA7DD47EFC32CB7EAF51E3A09C4221E3BE4C0858804C8'
  'g8a\configs.py' = '343700363AE14CC31DCDBC705A9258B9C8384E48ADAC5D175997D1FBFBCEF875'
  'g8a\job.py' = 'D4D422AAB845D0ED36396BDEF7129F74FD6BCA1205AE224FEAC20E324148C662'
  'local_runner.py' = '0562A4BB065A02F6C048D919D68BB6D445F36E357518DC8826D9D545323DB4EF'
  'train.py' = $TRAIN0
  'g8a\caps.py' = $CAPS
  'g8a\caps_b3g2.json' = $JSONG2 }
$CIOFILES = @('at10m_gate.py', 'at10m_gate.ps1', 'at10m_gate.cmd', 'at10m_skipped.cmd', 'at10m.template.md')
$NEEDED   = $CIOFILES + @('at10mcheck.py') + @($OVER.Keys | ForEach-Object { "overlay\$_" })
$STAMP  = (Get-Date).ToString('yyyyMMdd-HHmm')
$script:made = @()       # files this run created (removed again on a failure)
$script:backs = @()      # @(final, backup) of custom-io files this run replaced (put back on a failure)
function Stamp { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + ' ET' }
function Fail($m) {
  foreach ($b in $script:backs) { if (Test-Path $b[1]) { Copy-Item -Force $b[1] $b[0]; Remove-Item $b[1] } }
  foreach ($p in $script:made) { if (Test-Path $p) { Remove-Item $p -Recurse -Force } }
  "FAILED: $m (nothing from this run is left behind; the waiter, src-at and the other inserts were not changed)"
  exit 1
}
function Hash($p) { if (Test-Path $p) { (Get-FileHash $p).Hash } else { 'missing' } }
function Waiters($name) { @(Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" | Where-Object { $_.CommandLine -like "*$name*" }) }
function NeedMem($mb, $what) {
  $free = [math]::Floor((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1024)
  if ($free -lt $mb + 2048) { Fail "only $free MB free to commit; $what needs about $mb MB plus 2,048 to spare (run again when a G1 run has ended)" }
  "  memory: $free MB free to commit (need $mb + 2048 for $what)"
}
function CpuPy($dir, $pyargs) {
  $env:CUDA_VISIBLE_DEVICES = '-1'; $env:PYTHONUTF8 = '1'; $env:PYTHONPATH = $EGPATH; $env:OMP_NUM_THREADS = '1'; $env:BASE_TREE = $SRC
  Push-Location $dir
  $out = @(& $PY @pyargs 2>&1 | ForEach-Object { "$_" })
  $script:rc = $LASTEXITCODE
  Pop-Location
  Remove-Item Env:\CUDA_VISIBLE_DEVICES, Env:\PYTHONPATH, Env:\OMP_NUM_THREADS, Env:\BASE_TREE -ErrorAction SilentlyContinue
  return $out
}
# every file of a folder (relative path -> sha256), without __pycache__ / .pyc
function TreeHashes($root) {
  $h = @{}
  $n = $root.Length + 1
  foreach ($f in @(Get-ChildItem $root -Recurse -File | Where-Object { $_.FullName -notlike '*__pycache__*' -and $_.Extension -ne '.pyc' })) { $h[$f.FullName.Substring($n)] = (Get-FileHash $f.FullName).Hash }
  return $h
}
# The waiter must be v3e (one copy) and not past its first insert check point. Scans from the line AFTER v3e's start line (that line itself says "inserted jobs from WORK\insert after
# group 2"): any later "inserted job " line or "8aB3G2s400 ended" line means the check point has passed.
function CheckWaiter($wait) {
  for ($t = 0; $t -lt $wait; $t++) {
    $script:lines = @(Get-Content $LOG)
    $script:start = -1
    for ($i = 0; $i -lt $script:lines.Count; $i++) { if ($script:lines[$i] -like '*chain waiter v3 started*') { $script:start = $i } }
    if ($script:start -ge 0 -and $script:lines[$script:start] -like '*(v3e;*') { break }
    Start-Sleep -Seconds 10
  }
  if ($script:start -lt 0 -or $script:lines[$script:start] -notlike '*(v3e;*') { Fail "the running waiter is not v3e: $(if ($script:start -ge 0) { $script:lines[$script:start] } else { 'no start line in the log' })" }
  $w = @(Waiters 'q8aPost3_wait.ps1')
  if ($w.Count -ne 1) { Fail "expected one q8aPost3_wait.ps1 waiter, found $($w.Count)" }
  for ($i = $script:start + 1; $i -lt $script:lines.Count; $i++) {
    if ($script:lines[$i] -like '*inserted job *' -or $script:lines[$i] -like '*8aB3G2s400 ended*') { Fail "the waiter is already past its first insert check point (the inserts are listed once there): $($script:lines[$i])" }
  }
  return $w[0].ProcessId
}

# 1. Already installed? (src-at10m with the overlay and the queue file at their pinned hashes, the gate files in custom-io, and both inserts, in any state)
$have15 = @(Get-ChildItem "$INS\15-at10mgate.txt*" -ErrorAction SilentlyContinue).Count
$have16 = @(Get-ChildItem "$INS\16-at10m.txt*" -ErrorAction SilentlyContinue).Count
$cioSame = -not @($CIOFILES | Where-Object { (Hash "$CIO\$_") -ne (Hash "$IN\$_") }).Count
$overSame = -not @($OVER.Keys | Where-Object { (Hash "$SRC10\custom_io\$_") -ne $OVER[$_] }).Count
if ((Hash "$QDIR\$QNAME") -eq $QHASH -and $overSame -and (Test-Path "$SRC10\AT10M-SETUP-OK.txt") -and $cioSame -and $have15 -and $have16) {
  "already installed: src-at10m (custom_io $SHAAT + overlay train.py, tests\test_ckpt.py; queue_local\$QNAME), the gate files in custom-io and WORK\insert: $(@(Get-ChildItem "$INS\1[56]-at10m*" | ForEach-Object { $_.Name }) -join ', ')"
  'INSTALL AT10M DONE'
  exit 0
}
if ($have15 -or $have16) { Fail "WORK\insert already holds $(@(Get-ChildItem "$INS\1[56]-at10m*" | ForEach-Object { $_.Name }) -join ', ') without a finished install (look at it by hand first)" }
if (Test-Path $SRC10) { Fail "$SRC10 already exists without a finished install (it is not touched: look at it by hand first)" }

# 2. This folder, src-at (install_agent's), the inputs both queue lines read.
foreach ($f in $NEEDED) { if (-not (Test-Path "$IN\$f")) { Fail "$f missing in $IN" } }
if ((Hash "$IN\$QNAME") -ne $QHASH) { Fail "$QNAME in $IN is not the pinned one ($(Hash "$IN\$QNAME"))" }
if (-not (Test-Path "$SRC\AT-SETUP-OK.txt") -or -not (Select-String -Path "$SRC\AT-SETUP-OK.txt" -Pattern "commit $SHAAT" -SimpleMatch -Quiet)) { Fail "src-at is not installed (no $SRC\AT-SETUP-OK.txt for commit $SHAAT): run install_agent.ps1 first" }
foreach ($e in $EXP.Keys) { if ((Hash "$SRC\custom_io\$e") -ne $EXP[$e]) { Fail "$e in src-at is not commit $SHAAT's ($(Hash "$SRC\custom_io\$e"))" } }
if (-not (Test-Path "$INS\README.txt")) { Fail 'WORK\insert\README.txt missing (is v3e installed?)' }
if (-not (Test-Path "$INS\11-at.txt")) { Fail 'WORK\insert\11-at.txt (AT-1) is not there: run install_agent.ps1 first (or AT-1 has already run: this gate would have nothing to read)' }
if ((Hash "$WORK\b3-inputs\caps_b3g2.json") -ne $JSONG2) { Fail "WORK\b3-inputs\caps_b3g2.json (the file the queue line reads) is not G2f's ($(Hash "$WORK\b3-inputs\caps_b3g2.json"))" }
if (-not (Test-Path "$WORK\b3-inputs\cloze_long.py")) { Fail 'WORK\b3-inputs\cloze_long.py missing (the queue line reads it)' }
foreach ($e in $OVER.Keys) { if ((Hash "$IN\overlay\$e") -ne $OVER[$e]) { Fail "overlay\$e in $IN is not the pinned one ($(Hash "$IN\overlay\$e"))" } }
if (Test-Path "$SRC\custom_io\tests\test_ckpt.py") { Fail 'src-at already has tests\test_ckpt.py (the overlay adds it: look at src-at by hand)' }
$wpid = CheckWaiter 12
"src-at ($SHAAT) and its pinned files match (train.py included); the overlay files match their pins; waiter v3e (pid $wpid) is running and has not reached its first insert check point; 11-at.txt is present"

# 3. src-at10m under a temp name: src-at's custom_io copied (every hash equal), the overlay applied, the queue file added; then the CPU checks run IN that folder (nothing live changes here).
NeedMem 1500 'at10mcheck.py and test_ckpt.py (python + torch, 10M counted on the CPU, tiny models trained, no weights)'
$T10 = "$SRC10.new-$STAMP"
try {
  New-Item -ItemType Directory $T10 | Out-Null; $script:made += $T10
  Copy-Item -Recurse "$SRC\custom_io" "$T10\custom_io"
  foreach ($d in @(Get-ChildItem "$T10\custom_io" -Recurse -Directory -Filter __pycache__)) { Remove-Item $d.FullName -Recurse -Force }
  $hs = TreeHashes "$SRC\custom_io"; $ht = TreeHashes "$T10\custom_io"
  $bad = @($hs.Keys | Where-Object { $ht[$_] -ne $hs[$_] }) + @($ht.Keys | Where-Object { -not $hs.ContainsKey($_) })
  if ($bad.Count) { Fail "the copy of src-at\custom_io differs from it: $($bad[0..2] -join ', ')" }
  foreach ($e in $OVER.Keys) {
    $d = "$T10\custom_io\$e"
    if ($e -eq 'train.py' -and (Hash $d) -ne $TRAIN0) { Fail "train.py in the copy is not commit $SHAAT's ($(Hash $d))" }
    if ($e -ne 'train.py' -and (Test-Path $d)) { Fail "$e is already in the copy" }
    Copy-Item -Force "$IN\overlay\$e" $d
    if ((Hash $d) -ne $OVER[$e]) { Fail "overlay file $e did not copy" }
  }
  if (-not (Test-Path "$T10\custom_io\queue_local")) { New-Item -ItemType Directory "$T10\custom_io\queue_local" | Out-Null }
  Copy-Item "$IN\$QNAME" "$T10\custom_io\queue_local\$QNAME"
  if ((Hash "$T10\custom_io\queue_local\$QNAME") -ne $QHASH) { Fail 'the queue file did not copy' }
  Set-Content -Encoding ascii "$T10\AT10M-SETUP-OK.txt" -Value "commit $SHAAT custom_io (a copy of src-at, every file equal) + overlay: train.py $($OVER['train.py']) (original $TRAIN0), tests\test_ckpt.py $($OVER['tests\test_ckpt.py']); queue_local\$QNAME $QHASH ($(Stamp))"
} catch { Fail "building src-at10m: $($_.Exception.Message)" }
"src-at10m (new): $($ht.Count) files of src-at\custom_io copied with equal hashes; overlay train.py and tests\test_ckpt.py applied; queue_local\$QNAME added; src-at itself untouched"
$out = CpuPy $T10 @("$IN\at10mcheck.py", "$IN\$QNAME")
$out | Select-Object -Last 5 | ForEach-Object { "  at10mcheck: $_" }
if ($rc -ne 0 -or -not ("$out" -like '*AT10M CPU CHECK OK*')) { $out | Select-Object -Last 8; Fail "at10mcheck.py failed (rc $rc)" }
"running the checkpoint/resume test on the CPU (tiny plain and agent models, a few minutes) ..."
$out = CpuPy $T10 @('-m', 'custom_io.tests.test_ckpt')
$out | Select-Object -Last 8 | ForEach-Object { "  test_ckpt: $(if ($_.Length -gt 230) { $_.Substring(0, 230) + ' ...' } else { $_ })" }
if ($rc -ne 0 -or -not ("$out" -like '*ALL OK*')) { $out | Select-Object -Last 12; Fail "test_ckpt.py failed (rc $rc)" }
$out = @(& $PY -I "$IN\at10m_gate.py" --selftest 2>&1 | ForEach-Object { "$_" })
$grc = $LASTEXITCODE
$out | Select-Object -Last 2 | ForEach-Object { "  gate self-test: $_" }
if ($grc -ne 0 -or -not ("$out" -like '*at10m_gate self-test OK*')) { $out | Select-Object -Last 8; Fail "the gate's self-test failed (rc $grc)" }
foreach ($d in @(Get-ChildItem "$T10\custom_io" -Recurse -Directory -Filter __pycache__)) { Remove-Item $d.FullName -Recurse -Force }     # the checks' bytecode: src-at10m starts clean
if ((Hash "$T10\custom_io\train.py") -ne $OVER['train.py'] -or (Hash "$T10\custom_io\g8a\caps.py") -ne $CAPS) { Fail 'train.py or g8a\caps.py in the new folder changed during the checks' }

# 4. Write everything under temp names, then rename (src-at10m and the gate first, the job last).
$capsNow = Hash "$T10\custom_io\g8a\caps.py"      # computed: src-at10m's own caps.py (equal to src-at's, checked above)
if ($capsNow -ne $CAPS) { Fail "g8a\caps.py of src-at10m is $capsNow, not the pinned $CAPS" }
try {
  foreach ($f in $CIOFILES) {
    $t = "$CIO\$f.new-$STAMP"; Copy-Item "$IN\$f" $t; $script:made += $t
    if ((Hash $t) -ne (Hash "$IN\$f")) { Fail "$f did not copy to custom-io" }
  }
  Set-Content -Encoding ascii "$INS\15-at10mgate.txt.new-$STAMP" -Value @('cmd: at10m_gate.cmd', 'hours: 1'); $script:made += "$INS\15-at10mgate.txt.new-$STAMP"
  Set-Content -Encoding ascii "$INS\16-at10m.txt.new-$STAMP" -Value @('queue: 8aAT10M', 'src: src-at10m', "caps: $capsNow", 'card: at10m.template.md'); $script:made += "$INS\16-at10m.txt.new-$STAMP"
  $null = CheckWaiter 1     # once more right before the files appear
  Rename-Item $T10 'src-at10m'
  $script:made = @($script:made | Where-Object { $_ -ne $T10 }) + $SRC10
  foreach ($f in $CIOFILES) {
    if (Test-Path "$CIO\$f") { Copy-Item -Force "$CIO\$f" "$CIO\$f.before-$STAMP"; $script:backs += ,@("$CIO\$f", "$CIO\$f.before-$STAMP") }
    Move-Item -Force "$CIO\$f.new-$STAMP" "$CIO\$f"
    $script:made = @($script:made | Where-Object { $_ -ne "$CIO\$f.new-$STAMP" })
    if (-not ($script:backs | Where-Object { $_[0] -eq "$CIO\$f" })) { $script:made += "$CIO\$f" }
  }
  Rename-Item "$INS\15-at10mgate.txt.new-$STAMP" '15-at10mgate.txt'
  $script:made = @($script:made | Where-Object { $_ -ne "$INS\15-at10mgate.txt.new-$STAMP" }) + "$INS\15-at10mgate.txt"
  Rename-Item "$INS\16-at10m.txt.new-$STAMP" '16-at10m.txt'
  $script:made = @($script:made | Where-Object { $_ -ne "$INS\16-at10m.txt.new-$STAMP" }) + "$INS\16-at10m.txt"
} catch { Fail "writing the files: $($_.Exception.Message)" }
"$(Stamp) install_at10m.ps1: src-at10m (custom_io $SHAAT + overlay train.py $($OVER['train.py'].Substring(0, 12)): --ckpt-every / --resume; queue 8aAT10M-pc.txt) + at10m gate files and card template in custom-io + 15-at10mgate.txt + 16-at10m.txt (agent model at 10M, seed 400, gated on AT-1a/c/d/f)" | Add-Content -Encoding ascii $LOG
"in place: src-at10m (src-at untouched); src-at10m\custom_io\queue_local\$QNAME; custom-io: $($CIOFILES -join ', '); WORK\insert:"
foreach ($f in @(Get-ChildItem "$INS\*.txt" | Where-Object { $_.Name -ne 'README.txt' } | Sort-Object Name)) { "  $($f.Name): $(@(Get-Content $f.FullName) -join ' | ')" }
'INSTALL AT10M DONE'
