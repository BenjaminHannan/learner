# Installs the talker thread's two 3M runs on BensPC as inserted jobs of the post-G1 chain waiter v3e (spec addendum AD, 12 Oct 2026). Run from
# the folder the Mac copied (in-at). It installs whatever that folder holds, so it can run once with both pieces or once per piece:
#   at.zip + atcheck.py + g2f_gate.py/.ps1/.cmd + at_skipped.cmd + at.template.md  -> AT-1 (B3AT, arm AT, commit $SHAAT)
#       src-at; WORK\insert\10-g2fgate.txt (cmd: g2f_gate.cmd: reads G2f against the AT-1 gate; on "proved wrong" or "cannot tell" it turns
#       11 into a no-op) and WORK\insert\11-at.txt (queue 8aAT, card at.template.md)
#   g2q.zip + g2qcheck.py + g2q.template.md                                        -> G2Q (arm B3G2 with talk_question on, commit $SHAG2Q)
#       src-g2q; WORK\insert\30-g2q.txt (queue 8aB3G2Q, card g2q.template.md), a side run after test WIDE (20-wide.txt)
# The waiter runs them alone, in name order, at its first insert check point, right after g2c3s and G2f (before B3 group 1).
# Each code folder is unpacked as src-<name>.new-<stamp>, its pinned hashes checked, its queue copied under the PC name, parsed and its 3M count
# checked on the CPU, its light CPU tests run; only when every piece passes are the folders renamed and the inserts written. A failed check
# renames the new folders .failed-<stamp>. Only while the waiter is v3e and has not ended G2f. The CPU steps hide the GPU (G1 keeps it) and
# first need their memory estimate plus 2 GB free to commit. It stops nothing, never touches G1's or the chain's runs, results or pools, and
# deletes nothing. Pieces already installed are skipped.
$IN     = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO    = 'C:\Users\benja\custom-io'
$WORK   = "$CIO\work"
$LOG    = "$WORK\q8aPost-waiter.log"
$PY     = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$EGPATH = 'C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages'
$INS    = "$WORK\insert"
$CAPS   = '433475405AE7263579EBF4B9633916842567A5B1B1F3A8930311945E504F62D3'   # g8a\caps.py at both commits (G2f's plus custom_io.models.b3at in apply's list)
$JSONG2 = 'EE551D3AACBF9EC02D2AC7F5E7E6E12F44E15ABA2C39F5F38C3F1E3EC12D7ED4'   # g8a\caps_b3g2.json, G2f's (both queues read WORK\b3-inputs\caps_b3g2.json)
$SHAAT  = '6e72a5fae5'   # B3AT commit 6e72a5fae514a343c217c4d95cde37bc3b587c8e (Build the talker thread, PR #69; AT-0 passed on its parent 31a078a2ac)
$SHAG2Q = '4bdc31118a'   # G2Q commit 4bdc31118a9cf16e76bd48fdba01288ba4e259e4 (descendant of $SHAAT; talk_question off = bit-identical to it)
# Per piece: SHA-256 at its commit (custom_io-relative) proving the zip is that commit, the queue (commit file -> PC name), the check, the tests.
# AT: b3g2.py, writer.py and b3.py are byte for byte G2f's (74d6e92c75).
$PIECES = [ordered]@{
  'AT' = @{ zip = 'at.zip'; dir = "$CIO\src-at"; sha = $SHAAT; marker = 'AT-SETUP-OK.txt'; check = 'atcheck.py'; ok = 'AT CPU CHECK OK'
            qsrc = '8aAT-3M-s400-pc.txt'; q = '8aAT'; tests = @('test_b3at_core', 'test_b3at_run')       # 31 s / 0.5 GB, 108 s / 0.8 GB (cloud CPU)
            ins = @('10-g2fgate.txt', '11-at.txt'); files = @('atcheck.py', 'g2f_gate.py', 'g2f_gate.ps1', 'g2f_gate.cmd', 'at_skipped.cmd', 'at.template.md')
            cio = @('g2f_gate.py', 'g2f_gate.ps1', 'g2f_gate.cmd', 'at_skipped.cmd', 'at.template.md')
            exp = @{
              'models\b3at.py'                  = '5B10AAC1F20914BAA72DFEA114379682E6DDFC1DBDEE2F749A546760E7FC1768'
              'models\b3g2.py'                  = 'A4C61F0B567EC7E62B3233549BE63ECA7BCA2A3F35A934DFC217FA49390868CE'
              'models\writer.py'                = 'F3A40AD58749BBC24A964942DC650C79864D6A74442628AAC7D752730E73309E'
              'models\b3.py'                    = 'F3EF34D9F13256CCEE1CA7DD47EFC32CB7EAF51E3A09C4221E3BE4C0858804C8'
              'g8a\configs.py'                  = '343700363AE14CC31DCDBC705A9258B9C8384E48ADAC5D175997D1FBFBCEF875'
              'g8a\job.py'                      = 'D4D422AAB845D0ED36396BDEF7129F74FD6BCA1205AE224FEAC20E324148C662'
              'local_runner.py'                 = '0562A4BB065A02F6C048D919D68BB6D445F36E357518DC8826D9D545323DB4EF'
              'queue_local\8aAT-3M-s400-pc.txt' = '2CC320741260EB522B85C7E647B9CAB235D06903484179CDE1AB9BE9571D475A' } }
  'G2Q' = @{ zip = 'g2q.zip'; dir = "$CIO\src-g2q"; sha = $SHAG2Q; marker = 'G2Q-SETUP-OK.txt'; check = 'g2qcheck.py'; ok = 'G2Q CPU CHECK OK'
            qsrc = '8aB3G2Q-3M-s400-pc.txt'; q = '8aB3G2Q'; tests = @('test_b3g2_run', 'test_talk_question')   # 25 s / 0.4 GB, 138 s / 1.2 GB (talker thread)
            ins = @('30-g2q.txt'); files = @('g2qcheck.py', 'g2q.template.md'); cio = @('g2q.template.md')
            exp = @{
              'models\b3g2.py'                     = '5DACC11545DFA0A400BAC81E7682E7FC8F7C7D5CC3C598A0260AA3833121426E'
              'models\b3at.py'                     = '6FA8FED7C79D9760A9A2260B6082B305BFDA10A30667BBF620DFB7F5B6665366'
              'models\writer.py'                   = 'F3A40AD58749BBC24A964942DC650C79864D6A74442628AAC7D752730E73309E'
              'models\b3.py'                       = 'F3EF34D9F13256CCEE1CA7DD47EFC32CB7EAF51E3A09C4221E3BE4C0858804C8'
              'g8a\configs.py'                     = '8D1A9115C04D32DF307C4004A97B7E0BE9B0BA4D82A701A4E6162B1635FECD39'
              'g8a\job.py'                         = 'D4D422AAB845D0ED36396BDEF7129F74FD6BCA1205AE224FEAC20E324148C662'
              'evalx.py'                           = '29D95DEC787B769932DE9CA26BB09A8552D7CACB9181A7A5A4B4F17FBF3CBCD6'
              'talker_report.py'                   = 'EA88E7A716A9200F719B78FC2FB8167E90D6C61751E9981313158117206B1596'
              'local_runner.py'                    = '0562A4BB065A02F6C048D919D68BB6D445F36E357518DC8826D9D545323DB4EF'
              'queue_local\8aB3G2Q-3M-s400-pc.txt' = '66A2D37A0A973F28A0A476B4C130CA89CEF875ECB29C3DEDD5A33CFB19E72918' } }
}
$STAMP  = (Get-Date).ToString('yyyyMMdd-HHmm')
$script:made = @()
function Stamp { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + ' ET' }
function Fail($m) {
  foreach ($d in $script:made) { if (Test-Path $d) { $n = (Split-Path -Leaf $d) -replace '\.new-', '.failed-'; Rename-Item -Path $d -NewName $n; "renamed $(Split-Path -Leaf $d) to $n (kept)" } }
  "FAILED: $m (the waiter and WORK\insert were not changed)"
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
function Installed($p) {
  (Test-Path "$($p.dir)\$($p.marker)") -and (Select-String -Path "$($p.dir)\$($p.marker)" -Pattern "commit $($p.sha)" -SimpleMatch -Quiet) -and
    -not @($p.ins | Where-Object { -not @(Get-ChildItem "$INS\$_*" -ErrorAction SilentlyContinue).Count }).Count
}

# 1. Which pieces: the ones whose zip is here and that are not installed yet.
$todo = @()
foreach ($k in $PIECES.Keys) {
  $p = $PIECES[$k]
  if (-not (Test-Path "$IN\$($p.zip)")) { continue }
  if (Installed $p) { "${k}: $(Split-Path -Leaf $p.dir) ($($p.sha)) and $($p.ins -join ', ') are already installed"; continue }
  foreach ($f in $p.files) { if (-not (Test-Path "$IN\$f")) { Fail "$f missing in $IN (needed for $k)" } }
  if (Test-Path $p.dir) { Fail "$($p.dir) exists without a finished install of $($p.sha) (rename it aside by hand first)" }
  foreach ($i in $p.ins) { if (@(Get-ChildItem "$INS\$i*" -ErrorAction SilentlyContinue).Count) { Fail "WORK\insert already holds $(@(Get-ChildItem "$INS\$i*" | ForEach-Object { $_.Name }) -join ', ')" } }
  $todo += $k
}
if (-not $todo.Count) { 'nothing to install'; 'INSTALL AGENT DONE'; exit 0 }
"to install: $($todo -join ', ')"
if (-not (Test-Path "$INS\README.txt")) { Fail 'WORK\insert\README.txt missing (is v3e installed?)' }
if ((Hash "$WORK\b3-inputs\caps_b3g2.json") -ne $JSONG2) { Fail "WORK\b3-inputs\caps_b3g2.json (the file both queue lines read) is not G2f's ($(Hash "$WORK\b3-inputs\caps_b3g2.json"))" }
if (-not (Test-Path "$WORK\b3-inputs\cloze_long.py")) { Fail 'WORK\b3-inputs\cloze_long.py missing (both queue lines read it)' }
# The waiter: v3e (install_rr.ps1 may have started it seconds ago: up to 2 minutes for its start line), one copy, and G2f not ended since then.
for ($t = 0; $t -lt 12; $t++) {
  $lines = @(Get-Content $LOG)
  $start = -1
  for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*chain waiter v3 started*') { $start = $i } }
  if ($start -ge 0 -and $lines[$start] -like '*(v3e;*') { break }
  Start-Sleep -Seconds 10
}
if ($start -lt 0 -or $lines[$start] -notlike '*(v3e;*') { Fail "the running waiter is not v3e (inserted jobs from another src folder need v3e): $(if ($start -ge 0) { $lines[$start] })" }
$w = @(Waiters 'q8aPost3_wait.ps1')
if ($w.Count -ne 1) { Fail "expected one q8aPost3_wait.ps1 waiter, found $($w.Count)" }
# (from the line after the start line: v3e's own start line says "inserted jobs from WORK\insert after group 2"; 12 Oct 10:50 AM ET it matched)
for ($i = $start + 1; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*8aB3G2s400 ended*' -or $lines[$i] -like '*inserted job *(after group 2*') { Fail "the waiter is already past G2f and its first insert check point: $($lines[$i])" } }
"waiter v3e (pid $($w[0].ProcessId)) is running and has not reached G2f's end; the inserts run at its first check point, right after G2f"

# 2. Unpack and check every piece (nothing live changes here).
$new = @{}
foreach ($k in $todo) {
  $p = $PIECES[$k]
  $n = "$($p.dir).new-$STAMP"
  if (Test-Path $n) { Fail "$n already exists" }
  Expand-Archive -Path "$IN\$($p.zip)" -DestinationPath $n
  $script:made += $n; $new[$k] = $n
  if ((Hash "$n\custom_io\g8a\caps.py") -ne $CAPS) { Fail "caps.py in $($p.zip) is not the pinned one ($(Hash "$n\custom_io\g8a\caps.py"))" }
  if ((Hash "$n\custom_io\g8a\caps_b3g2.json") -ne $JSONG2) { Fail "caps_b3g2.json in $($p.zip) hash wrong" }
  foreach ($e in $p.exp.Keys) { if ((Hash "$n\custom_io\$e") -ne $p.exp[$e]) { Fail "$e in $($p.zip) is not commit $($p.sha)'s" } }
  # The queue under its PC name (job <q>-3M-s400, so a card's spill rule renames Q-... to <q>b-...): the same bytes as the commit's file.
  Copy-Item "$n\custom_io\queue_local\$($p.qsrc)" "$n\custom_io\queue_local\$($p.q)-pc.txt"
  if ((Hash "$n\custom_io\queue_local\$($p.q)-pc.txt") -ne $p.exp["queue_local\$($p.qsrc)"]) { Fail "$($p.q)-pc.txt did not copy" }
  "${k}: unpacked $($p.sha) into $(Split-Path -Leaf $n); caps.py, caps_b3g2.json and $($p.exp.Count) pinned files match; queue $($p.q)-pc.txt = $($p.qsrc)"
  NeedMem 1500 "$($p.check) (python + torch, 3M on the CPU)"
  $out = CpuPy $n @("$IN\$($p.check)")
  $out | Select-Object -Last 2 | ForEach-Object { "  $($p.check): $_" }
  if ($rc -ne 0 -or -not ("$out" -like "*$($p.ok)*")) { $out | Select-Object -Last 8; Fail "$($p.check) failed (rc $rc)" }
  foreach ($t in $p.tests) {
    NeedMem 1500 $t
    $out = CpuPy $n @('-m', "custom_io.tests.$t")
    "  ${t}: $(($out | Select-Object -Last 1))"
    if ($rc -ne 0 -or @($out -match '^FAIL').Count -or -not @($out -match '^(ALL OK|ok\s)').Count) { $out | Select-Object -Last 8; Fail "$t failed (rc $rc) in $(Split-Path -Leaf $n)" }
  }
  Set-Content -Encoding ascii "$n\$($p.marker)" -Value @("caps.py $CAPS", "commit $($p.sha) (Build the talker thread, PR #69)", "caps_b3g2.json $JSONG2",
    "queue $($p.q)-pc.txt = $($p.qsrc) $($p.exp["queue_local\$($p.qsrc)"])", "$($p.check) ok; $($p.tests -join ', ') ok; CPU; install_agent.ps1", (Stamp))
}

# 3. Into place: the folders, the gate and card files in custom-io (an older copy kept as .before-<stamp>), then the inserts.
foreach ($k in $todo) {
  $p = $PIECES[$k]
  try { Rename-Item -Path $new[$k] -NewName (Split-Path -Leaf $p.dir) -ErrorAction Stop } catch { Fail "could not rename $(Split-Path -Leaf $new[$k]) to $(Split-Path -Leaf $p.dir): $($_.Exception.Message)" }
  $script:made = @($script:made | Where-Object { $_ -ne $new[$k] })
}
foreach ($k in $todo) {
  foreach ($f in $PIECES[$k].cio) {
    if (Test-Path "$CIO\$f") { Copy-Item -Force "$CIO\$f" "$CIO\$f.before-$STAMP" }
    Copy-Item -Force "$IN\$f" "$CIO\$f"
    if ((Hash "$CIO\$f") -ne (Hash "$IN\$f")) { "FAILED: $f did not copy to custom-io (the src folders are in place; no insert written)"; exit 1 }
  }
}
if ($todo -contains 'AT') {
  Set-Content -Encoding ascii "$INS\10-g2fgate.txt" -Value @('cmd: g2f_gate.cmd', 'hours: 1')
  Set-Content -Encoding ascii "$INS\11-at.txt" -Value @('queue: 8aAT', 'src: src-at', "caps: $CAPS", 'card: at.template.md')
}
if ($todo -contains 'G2Q') { Set-Content -Encoding ascii "$INS\30-g2q.txt" -Value @('queue: 8aB3G2Q', 'src: src-g2q', "caps: $CAPS", 'card: g2q.template.md') }
"$(Stamp) install_agent.ps1:$(if ($todo -contains 'AT') { " src-at ($SHAAT) + 10-g2fgate.txt + 11-at.txt (AT-1 3M s400, gated on G2f);" })$(if ($todo -contains 'G2Q') { " src-g2q ($SHAG2Q) + 30-g2q.txt (G2Q 3M s400, side run after WIDE)" })" | Add-Content -Encoding ascii $LOG
"in place: $($todo -join ', '); WORK\insert:"
foreach ($f in @(Get-ChildItem "$INS\*.txt" | Where-Object { $_.Name -ne 'README.txt' } | Sort-Object Name)) { "  $($f.Name): $(@(Get-Content $f.FullName) -join ' | ')" }
'INSTALL AGENT DONE'
