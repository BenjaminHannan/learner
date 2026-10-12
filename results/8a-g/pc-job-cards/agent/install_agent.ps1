# Installs AT-1 (the agent-turn model B3AT at 3M, seed 400) on BensPC as two inserted jobs of the post-G1 chain waiter v3e (spec addendum AD,
# 12 Oct 2026). Run from the folder the Mac copied (in-at); it needs at.zip (custom_io of the B3AT commit $SHAAT), atcheck.py, g2f_gate.py,
# g2f_gate.ps1, g2f_gate.cmd, at_skipped.cmd and at.template.md beside it.
#   src-at                      the B3AT code, unpacked as src-at.new-<stamp>, its pinned hashes checked, the queue parsed and the 3M count
#                               checked on the CPU (atcheck.py), two light CPU tests run; only then renamed src-at
#   WORK\insert\10-g2fgate.txt  cmd: g2f_gate.cmd   (reads G2f against the AT-1 gate; on "proved wrong" or "cannot tell" it turns 11 into a no-op)
#   WORK\insert\11-at.txt       queue: 8aAT from src-at, card at.template.md
# The waiter runs both alone at its first insert check point, right after g2c3s and G2f, before WIDE (20-wide.txt) and B3 group 1.
# Only while the waiter is v3e and has not reached that check point. The CPU steps hide the GPU (G1 keeps it) and first need their memory
# estimate plus 2 GB free to commit. It stops nothing, never touches G1's or the chain's runs, results or pools, and deletes nothing.
$IN     = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO    = 'C:\Users\benja\custom-io'
$WORK   = "$CIO\work"
$LOG    = "$WORK\q8aPost-waiter.log"
$PY     = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$EGPATH = 'C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages'
$SRCAT  = "$CIO\src-at"
$SHAAT  = '6e72a5fae5'   # B3AT commit 6e72a5fae514a343c217c4d95cde37bc3b587c8e (Build the talker thread, PR #69; AT-0 passed on its parent 31a078a2ac)
$CAPSAT = '433475405AE7263579EBF4B9633916842567A5B1B1F3A8930311945E504F62D3'   # g8a\caps.py at $SHAAT (G2f's plus custom_io.models.b3at in apply's list)
$JSONAT = @{ 'caps_b3g2.json' = 'EE551D3AACBF9EC02D2AC7F5E7E6E12F44E15ABA2C39F5F38C3F1E3EC12D7ED4' }   # the same file as G2f's
# SHA-256 at $SHAAT (custom_io-relative): proves the zip is that commit. b3g2.py, writer.py and b3.py are byte for byte G2f's (74d6e92c75).
$EXPAT  = @{
  'models\b3at.py'                  = '5B10AAC1F20914BAA72DFEA114379682E6DDFC1DBDEE2F749A546760E7FC1768'
  'models\b3g2.py'                  = 'A4C61F0B567EC7E62B3233549BE63ECA7BCA2A3F35A934DFC217FA49390868CE'
  'models\writer.py'                = 'F3A40AD58749BBC24A964942DC650C79864D6A74442628AAC7D752730E73309E'
  'models\b3.py'                    = 'F3EF34D9F13256CCEE1CA7DD47EFC32CB7EAF51E3A09C4221E3BE4C0858804C8'
  'g8a\configs.py'                  = '343700363AE14CC31DCDBC705A9258B9C8384E48ADAC5D175997D1FBFBCEF875'
  'g8a\job.py'                      = 'D4D422AAB845D0ED36396BDEF7129F74FD6BCA1205AE224FEAC20E324148C662'
  'local_runner.py'                 = '0562A4BB065A02F6C048D919D68BB6D445F36E357518DC8826D9D545323DB4EF'
  'queue_local\8aAT-3M-s400-pc.txt' = '2CC320741260EB522B85C7E647B9CAB235D06903484179CDE1AB9BE9571D475A'
}
$TESTAT = @('test_b3at_core', 'test_b3at_run')       # 31 s / 0.5 GB and 108 s / 0.8 GB on the cloud CPU
$FILES  = @('at.zip', 'atcheck.py', 'g2f_gate.py', 'g2f_gate.ps1', 'g2f_gate.cmd', 'at_skipped.cmd', 'at.template.md')
$INS    = "$WORK\insert"
$STAMP  = (Get-Date).ToString('yyyyMMdd-HHmm')
$script:made = $null
function Stamp { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + ' ET' }
function Fail($m) {
  if ($script:made -and (Test-Path $script:made)) { $n = (Split-Path -Leaf $script:made) -replace '\.new-', '.failed-'; Rename-Item -Path $script:made -NewName $n; "renamed $(Split-Path -Leaf $script:made) to $n (kept)" }
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

# 1. Already installed? Then nothing to do.
if ((Test-Path "$SRCAT\AT-SETUP-OK.txt") -and (Select-String -Path "$SRCAT\AT-SETUP-OK.txt" -Pattern "commit $SHAAT" -SimpleMatch -Quiet) -and
    @(Get-ChildItem "$INS\10-g2fgate.txt*" -ErrorAction SilentlyContinue).Count -and @(Get-ChildItem "$INS\11-at.txt*" -ErrorAction SilentlyContinue).Count) {
  "src-at ($SHAAT) and its two inserts are already installed: $(@(Get-ChildItem "$INS\10-g2fgate.txt*", "$INS\11-at.txt*" | ForEach-Object { $_.Name }) -join ', ')"
  'INSTALL AGENT DONE'
  exit 0
}
foreach ($f in $FILES) { if (-not (Test-Path "$IN\$f")) { Fail "$f missing in $IN" } }
if (Test-Path $SRCAT) { Fail "$SRCAT exists without a finished install of $SHAAT (rename it aside by hand first)" }
if (@(Get-ChildItem "$INS\*g2fgate*", "$INS\*-at.txt*" -ErrorAction SilentlyContinue).Count) { Fail "WORK\insert already holds a gate or AT file: $(@(Get-ChildItem "$INS\*g2fgate*", "$INS\*-at.txt*" | ForEach-Object { $_.Name }) -join ', ')" }
if (-not (Test-Path "$INS\README.txt")) { Fail 'WORK\insert\README.txt missing (is v3e installed?)' }
# The waiter: one q8aPost3_wait.ps1, v3e, and G2f not ended since its last start (its first insert check point comes right after G2f).
$w = @(Waiters 'q8aPost3_wait.ps1')
if ($w.Count -ne 1) { Fail "expected one q8aPost3_wait.ps1 waiter, found $($w.Count)" }
$lines = @(Get-Content $LOG)
$start = -1
for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*chain waiter v3 started*') { $start = $i } }
if ($start -lt 0 -or $lines[$start] -notlike '*(v3e;*') { Fail "the running waiter is not v3e (inserted jobs from another src folder need v3e): $(if ($start -ge 0) { $lines[$start] })" }
for ($i = $start; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*8aB3G2s400* ended*' -or $lines[$i] -like '*inserted job*after group 2*') { Fail "the waiter is already past G2f and its first insert check point: $($lines[$i])" } }
"waiter v3e (pid $($w[0].ProcessId)) is running and has not reached G2f's end; the inserts run at its first check point, right after G2f"

# 2. Unpack the B3AT code and check it is that commit.
$new = "$SRCAT.new-$STAMP"
if (Test-Path $new) { Fail "$new already exists" }
Expand-Archive -Path "$IN\at.zip" -DestinationPath $new
$script:made = $new
if ((Hash "$new\custom_io\g8a\caps.py") -ne $CAPSAT) { Fail "caps.py in at.zip is not the pinned one ($(Hash "$new\custom_io\g8a\caps.py"))" }
foreach ($k in $JSONAT.Keys) { if ((Hash "$new\custom_io\g8a\$k") -ne $JSONAT[$k]) { Fail "$k in at.zip hash wrong" } }
foreach ($k in $EXPAT.Keys) { if ((Hash "$new\custom_io\$k") -ne $EXPAT[$k]) { Fail "$k in at.zip is not commit $SHAAT's" } }
if ((Hash "$WORK\b3-inputs\caps_b3g2.json") -ne $JSONAT['caps_b3g2.json']) { Fail "WORK\b3-inputs\caps_b3g2.json (the file the AT queue line reads) is not G2f's ($(Hash "$WORK\b3-inputs\caps_b3g2.json"))" }
if (-not (Test-Path "$WORK\b3-inputs\cloze_long.py")) { Fail 'WORK\b3-inputs\cloze_long.py missing (the AT queue line reads it)' }
# The queue under the short name 8aAT (job 8aAT-3M-s400; the card's spill rule renames Q-... to 8aATb-...): the same bytes as the commit's file.
Copy-Item "$new\custom_io\queue_local\8aAT-3M-s400-pc.txt" "$new\custom_io\queue_local\8aAT-pc.txt"
if ((Hash "$new\custom_io\queue_local\8aAT-pc.txt") -ne $EXPAT['queue_local\8aAT-3M-s400-pc.txt']) { Fail '8aAT-pc.txt did not copy' }
"src-at: unpacked $SHAAT into $(Split-Path -Leaf $new); caps.py, caps_b3g2.json and $($EXPAT.Count) pinned files match; queue 8aAT-pc.txt = 8aAT-3M-s400-pc.txt"

# 3. CPU checks (GPU hidden): the queue parses and arm AT builds at 4,023,302 trained; then the two light AT tests.
NeedMem 1500 'atcheck (python + torch, 3M B3AT on the CPU)'
$out = CpuPy $new @("$IN\atcheck.py")
$out | Select-Object -Last 2 | ForEach-Object { "  atcheck: $_" }
if ($rc -ne 0 -or -not ("$out" -like '*AT CPU CHECK OK*')) { $out | Select-Object -Last 8; Fail "atcheck failed (rc $rc)" }
foreach ($t in $TESTAT) {
  NeedMem 1500 $t
  $out = CpuPy $new @('-m', "custom_io.tests.$t")
  "  ${t}: $(($out | Select-Object -Last 1))"
  if ($rc -ne 0 -or @($out -match '^FAIL').Count -or -not @($out -match '^(ALL OK|ok\s)').Count) { $out | Select-Object -Last 8; Fail "$t failed (rc $rc)" }
}
Set-Content -Encoding ascii "$new\AT-SETUP-OK.txt" -Value @("caps.py $CAPSAT", "commit $SHAAT (B3AT, agent turns; Build the talker thread, PR #69)",
  "caps_b3g2.json $($JSONAT['caps_b3g2.json'])", "queue 8aAT-pc.txt = 8aAT-3M-s400-pc.txt $($EXPAT['queue_local\8aAT-3M-s400-pc.txt'])",
  "atcheck ok; $($TESTAT -join ', ') ok; CPU; install_agent.ps1", (Stamp))

# 4. Into place: the folder, the gate and card files in custom-io (an older copy kept as .before-<stamp>), then the two inserts.
try { Rename-Item -Path $new -NewName (Split-Path -Leaf $SRCAT) -ErrorAction Stop } catch { Fail "could not rename $(Split-Path -Leaf $new) to src-at: $($_.Exception.Message)" }
$script:made = $null
foreach ($f in @('g2f_gate.py', 'g2f_gate.ps1', 'g2f_gate.cmd', 'at_skipped.cmd', 'at.template.md')) {
  if (Test-Path "$CIO\$f") { Copy-Item -Force "$CIO\$f" "$CIO\$f.before-$STAMP" }
  Copy-Item -Force "$IN\$f" "$CIO\$f"
  if ((Hash "$CIO\$f") -ne (Hash "$IN\$f")) { "FAILED: $f did not copy to custom-io (src-at is in place; no insert written)"; exit 1 }
}
Set-Content -Encoding ascii "$INS\10-g2fgate.txt" -Value @('cmd: g2f_gate.cmd', 'hours: 1')
Set-Content -Encoding ascii "$INS\11-at.txt" -Value @('queue: 8aAT', 'src: src-at', "caps: $CAPSAT", 'card: at.template.md')
"$(Stamp) install_agent.ps1: src-at ($SHAAT, B3AT) and WORK\insert\10-g2fgate.txt + 11-at.txt (AT-1 3M s400, gated on G2f) installed" | Add-Content -Encoding ascii $LOG
'src-at: in place; custom-io: g2f_gate.py/.ps1/.cmd, at_skipped.cmd, at.template.md; WORK\insert:'
foreach ($f in @('10-g2fgate.txt', '11-at.txt')) { "  ${f}: $(@(Get-Content "$INS\$f") -join ' | ')" }
'INSTALL AGENT DONE'
