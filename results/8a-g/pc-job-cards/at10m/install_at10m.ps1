# Installs the agent model's 10M run (B3AT, arm AT, rung 10M, seed 400, queue 8aAT10M) on BensPC as two inserted jobs of the post-G1 chain waiter v3e (big-run PLAN.md eighteenth Addendum
# 10-12): WORK\insert\15-at10mgate.txt (cmd: at10m_gate.cmd, reads AT-1 against G2f and g2c3s and, unless "not proved wrong", turns 16 into a no-op) and WORK\insert\16-at10m.txt
# (queue 8aAT10M from src-at). Run from the folder the Mac copied (in-at10m), AFTER install_agent.ps1 printed INSTALL AGENT DONE and before the waiter ends G2f (the inserts are listed once,
# at its first check point, right after G2f). It needs src-at (install_agent's, commit 6e72a5fae5, its pinned hashes) and WORK\insert\11-at.txt. It adds queue_local\8aAT10M-pc.txt to src-at
# only if absent (no existing src-at file is edited), copies the gate files and the card template into custom-io, runs at10mcheck.py (the 10M queue and the trained counts of AT and PTS at
# 10M, CPU, no GPU, no Gemma weights) and the gate's self-test, and only then writes the files (temp names first, renamed at the end; a failure removes what this run made). It stops nothing,
# touches no run, result, pool or checkpoint, and deletes nothing it did not make itself in this run. Run again when already installed: it says so and prints INSTALL AT10M DONE.
$IN     = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO    = 'C:\Users\benja\custom-io'
$WORK   = "$CIO\work"
$LOG    = "$WORK\q8aPost-waiter.log"
$PY     = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$EGPATH = 'C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages'
$INS    = "$WORK\insert"
$SRC    = "$CIO\src-at"
$QDIR   = "$SRC\custom_io\queue_local"
$QNAME  = '8aAT10M-pc.txt'
$QHASH  = '09A1B69F6BE43F0F3CE1E04BB047EE412CB2FFE1F416B6C2D6826B54E462B6F1'   # this folder's queue file
$CAPS   = '433475405AE7263579EBF4B9633916842567A5B1B1F3A8930311945E504F62D3'   # g8a\caps.py of src-at (install_agent's pin)
$JSONG2 = 'EE551D3AACBF9EC02D2AC7F5E7E6E12F44E15ABA2C39F5F38C3F1E3EC12D7ED4'   # g8a\caps_b3g2.json
$SHAAT  = '6e72a5fae5'
# src-at's pinned files (the same list and hashes install_agent.ps1 checks for the AT piece)
$EXP = [ordered]@{
  'models\b3at.py' = '5B10AAC1F20914BAA72DFEA114379682E6DDFC1DBDEE2F749A546760E7FC1768'
  'models\b3g2.py' = 'A4C61F0B567EC7E62B3233549BE63ECA7BCA2A3F35A934DFC217FA49390868CE'
  'models\writer.py' = 'F3A40AD58749BBC24A964942DC650C79864D6A74442628AAC7D752730E73309E'
  'models\b3.py' = 'F3EF34D9F13256CCEE1CA7DD47EFC32CB7EAF51E3A09C4221E3BE4C0858804C8'
  'g8a\configs.py' = '343700363AE14CC31DCDBC705A9258B9C8384E48ADAC5D175997D1FBFBCEF875'
  'g8a\job.py' = 'D4D422AAB845D0ED36396BDEF7129F74FD6BCA1205AE224FEAC20E324148C662'
  'local_runner.py' = '0562A4BB065A02F6C048D919D68BB6D445F36E357518DC8826D9D545323DB4EF'
  'g8a\caps.py' = $CAPS
  'g8a\caps_b3g2.json' = $JSONG2 }
$CIOFILES = @('at10m_gate.py', 'at10m_gate.ps1', 'at10m_gate.cmd', 'at10m_skipped.cmd', 'at10m.template.md')
$NEEDED   = $CIOFILES + @(, 'at10mcheck.py')
$STAMP  = (Get-Date).ToString('yyyyMMdd-HHmm')
$script:made = @()       # files this run created (removed again on a failure)
$script:backs = @()      # @(final, backup) of custom-io files this run replaced (put back on a failure)
function Stamp { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + ' ET' }
function Fail($m) {
  foreach ($b in $script:backs) { if (Test-Path $b[1]) { Copy-Item -Force $b[1] $b[0]; Remove-Item $b[1] } }
  foreach ($p in $script:made) { if (Test-Path $p) { Remove-Item $p -Force } }
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
  $env:CUDA_VISIBLE_DEVICES = '-1'; $env:PYTHONUTF8 = '1'; $env:PYTHONPATH = $EGPATH
  Push-Location $dir
  $out = @(& $PY @pyargs 2>&1 | ForEach-Object { "$_" })
  $script:rc = $LASTEXITCODE
  Pop-Location
  Remove-Item Env:\CUDA_VISIBLE_DEVICES, Env:\PYTHONPATH -ErrorAction SilentlyContinue
  return $out
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

# 1. Already installed? (queue file with the pinned hash, the gate files in custom-io, and both inserts, in any state)
$have15 = @(Get-ChildItem "$INS\15-at10mgate.txt*" -ErrorAction SilentlyContinue).Count
$have16 = @(Get-ChildItem "$INS\16-at10m.txt*" -ErrorAction SilentlyContinue).Count
$cioSame = -not @($CIOFILES | Where-Object { (Hash "$CIO\$_") -ne (Hash "$IN\$_") }).Count
if ((Hash "$QDIR\$QNAME") -eq $QHASH -and $cioSame -and $have15 -and $have16) {
  "already installed: src-at\custom_io\queue_local\$QNAME, the gate files in custom-io and WORK\insert: $(@(Get-ChildItem "$INS\1[56]-at10m*" | ForEach-Object { $_.Name }) -join ', ')"
  'INSTALL AT10M DONE'
  exit 0
}
if ($have15 -or $have16) { Fail "WORK\insert already holds $(@(Get-ChildItem "$INS\1[56]-at10m*" | ForEach-Object { $_.Name }) -join ', ') without a finished install (look at it by hand first)" }

# 2. This folder, src-at (install_agent's), the inputs both queue lines read.
foreach ($f in $NEEDED) { if (-not (Test-Path "$IN\$f")) { Fail "$f missing in $IN" } }
if ((Hash "$IN\$QNAME") -ne $QHASH) { Fail "$QNAME in $IN is not the pinned one ($(Hash "$IN\$QNAME"))" }
if (-not (Test-Path "$SRC\AT-SETUP-OK.txt") -or -not (Select-String -Path "$SRC\AT-SETUP-OK.txt" -Pattern "commit $SHAAT" -SimpleMatch -Quiet)) { Fail "src-at is not installed (no $SRC\AT-SETUP-OK.txt for commit $SHAAT): run install_agent.ps1 first" }
foreach ($e in $EXP.Keys) { if ((Hash "$SRC\custom_io\$e") -ne $EXP[$e]) { Fail "$e in src-at is not commit $SHAAT's ($(Hash "$SRC\custom_io\$e"))" } }
$capsNow = Hash "$SRC\custom_io\g8a\caps.py"
if (-not (Test-Path "$INS\README.txt")) { Fail 'WORK\insert\README.txt missing (is v3e installed?)' }
if (-not (Test-Path "$INS\11-at.txt")) { Fail 'WORK\insert\11-at.txt (AT-1) is not there: run install_agent.ps1 first (or AT-1 has already run: this gate would have nothing to read)' }
if ((Hash "$WORK\b3-inputs\caps_b3g2.json") -ne $JSONG2) { Fail "WORK\b3-inputs\caps_b3g2.json (the file the queue line reads) is not G2f's ($(Hash "$WORK\b3-inputs\caps_b3g2.json"))" }
if (-not (Test-Path "$WORK\b3-inputs\cloze_long.py")) { Fail 'WORK\b3-inputs\cloze_long.py missing (the queue line reads it)' }
if ((Test-Path "$QDIR\$QNAME") -and (Hash "$QDIR\$QNAME") -ne $QHASH) { Fail "$QDIR\$QNAME exists and is not this folder's queue ($(Hash "$QDIR\$QNAME")): not replaced" }
$wpid = CheckWaiter 12
"src-at ($SHAAT) and its pinned files match; waiter v3e (pid $wpid) is running and has not reached its first insert check point; 11-at.txt is present"

# 3. CPU checks (nothing live changes here): the 10M queue and the trained counts, the gate's self-test.
NeedMem 1500 'at10mcheck.py (python + torch, 10M on the CPU, no weights)'
$out = CpuPy $SRC @("$IN\at10mcheck.py", "$IN\$QNAME")
$out | Select-Object -Last 4 | ForEach-Object { "  at10mcheck: $_" }
if ($rc -ne 0 -or -not ("$out" -like '*AT10M CPU CHECK OK*')) { $out | Select-Object -Last 8; Fail "at10mcheck.py failed (rc $rc)" }
$out = @(& $PY -I "$IN\at10m_gate.py" --selftest 2>&1 | ForEach-Object { "$_" })
$grc = $LASTEXITCODE
$out | Select-Object -Last 2 | ForEach-Object { "  gate self-test: $_" }
if ($grc -ne 0 -or -not ("$out" -like '*at10m_gate self-test OK*')) { $out | Select-Object -Last 8; Fail "the gate's self-test failed (rc $grc)" }

# 4. Write everything under temp names, then rename (the gate first, the job last).
$new = @()
try {
  if (-not (Test-Path "$QDIR\$QNAME")) {
    $t = "$QDIR\$QNAME.new-$STAMP"; Copy-Item "$IN\$QNAME" $t; $script:made += $t
    if ((Hash $t) -ne $QHASH) { Fail 'the queue file did not copy' }
  }
  foreach ($f in $CIOFILES) {
    $t = "$CIO\$f.new-$STAMP"; Copy-Item "$IN\$f" $t; $script:made += $t
    if ((Hash $t) -ne (Hash "$IN\$f")) { Fail "$f did not copy to custom-io" }
  }
  Set-Content -Encoding ascii "$INS\15-at10mgate.txt.new-$STAMP" -Value @('cmd: at10m_gate.cmd', 'hours: 1'); $script:made += "$INS\15-at10mgate.txt.new-$STAMP"
  Set-Content -Encoding ascii "$INS\16-at10m.txt.new-$STAMP" -Value @('queue: 8aAT10M', 'src: src-at', "caps: $capsNow", 'card: at10m.template.md'); $script:made += "$INS\16-at10m.txt.new-$STAMP"
  $null = CheckWaiter 1     # once more right before the files appear
  if (Test-Path "$QDIR\$QNAME.new-$STAMP") { Rename-Item "$QDIR\$QNAME.new-$STAMP" $QNAME; $script:made = @($script:made | Where-Object { $_ -ne "$QDIR\$QNAME.new-$STAMP" }) + "$QDIR\$QNAME" }
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
"$(Stamp) install_at10m.ps1: queue 8aAT10M-pc.txt in src-at + at10m gate files and card template in custom-io + 15-at10mgate.txt + 16-at10m.txt (agent model at 10M, seed 400, gated on AT-1a/c/d/f)" | Add-Content -Encoding ascii $LOG
"in place: src-at\custom_io\queue_local\$QNAME; custom-io: $($CIOFILES -join ', '); WORK\insert:"
foreach ($f in @(Get-ChildItem "$INS\*.txt" | Where-Object { $_.Name -ne 'README.txt' } | Sort-Object Name)) { "  $($f.Name): $(@(Get-Content $f.FullName) -join ' | ')" }
'INSTALL AT10M DONE'
