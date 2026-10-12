# Installs the reader-rule code on BensPC before G1 ends (11 Oct 2026, spec addendum X). Run from the folder the Mac copied (in-rr). It installs
# whatever that folder holds, so it can run once with everything or once per piece:
#   b3r.zip   custom_io of the group 1 reader-rule commit ($SHAB3R)  -> src-b3r   (B3 group 1, 8aB3G1s400/s401)
#   g2.zip    custom_io of the group 2 reader-rule commit ($SHAG2)   -> src-b3g2  (fc100 part 2, B3 group 2, g2c3s, g2c10s, c30s)
#   8aFC2-pc.txt + fc2check.py + infer_speed.py + fc100v2.md          -> the five-shape 100M list (addendum W) and its answer timer
#   q8aPost3_wait.ps1 + swap_v3e.ps1                                  -> waiter v3d -> v3e (addendum U), after the code (skipped if v3e runs)
#   wide\install_wide.ps1 + its files                                 -> test WIDE (addendum AB) as an inserted job, very last (needs v3e)
#   8aC30S-pc.txt (only with g2.zip)                                  -> c30s's queue in the new src-b3g2 (the no-plug c30s, addendum Z)
# A list or c30s queue that reads Gemma's own 512 numbers (no plug: '"eg_pre": true' or --noplug) is gated on `eg check cpu pre` (fp32, CPU).
# Only while the post-G1 waiter still waits for G1. Each new code folder is unpacked beside the old one as <name>.new-<stamp> and checked on the CPU
# (pinned hashes, CPU tests, queue parse, ~100M configs, answer-timer selftest) before anything changes. Then the old folder is renamed
# <name>.before-rr-<stamp> (kept) and the new one takes its name. A failed check renames the new folder <name>.failed-<stamp>; the old code stays.
# The CPU tests hide the GPU, so G1 keeps it. It stops nothing but (for v3e) the idle waiter, never touches G1's runs, and deletes nothing.
# Memory: each CPU step first needs its estimate plus 2 GB free to commit (NeedMem); G1 holds most of the PC's memory, and the 9:20 PM ET
# 11 Oct run ran out in fc2check. A run that stops there changes nothing; run it again when a G1 run has ended. Pieces already installed are skipped.
$IN     = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO    = 'C:\Users\benja\custom-io'
$WORK   = "$CIO\work"
$LOG    = "$WORK\q8aPost-waiter.log"
$PY     = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$EGPATH = 'C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages'
$EG2    = 'C:\Users\benja\eg2'      # local EmbeddingGemma 2 (CUSTOM_IO_EG2, as the queues set it)
$SRCB3R = "$CIO\src-b3r"
$SRCG2  = "$CIO\src-b3g2"
$SHAB3R = 'ca7e1d1b88'   # group 1 reader-rule commit ca7e1d1b8857a72f9c89f376aad20b1f12132fee (on PR #56 8fce7247a8; architecture thread, 7:20 PM ET 11 Oct)
$SHAG2  = '74d6e92c75'   # group 2 commit 74d6e92c75f3a0ed6b3f1e49e13fefc5ed5d29d6: reader rules + G2f's writer (talker thread; holds 73bc563ec0 and no-plug a10b6eacf1)
$CAPSG2 = '32862AE2D4E6E401FCAD5BB6C5E54B0B8845019202DEA73E2CB4C7EFE5EEA03E'      # caps.py the waiter pins for src-b3g2 (unchanged by the reader rules)
$JSONB3 = 'BD81C67F0B6F33686718587A3FBDCD73E939C1FF9CB832DC6D68F34DEE4F7550'      # g8a/caps_b3.json
$JSONG2 = @{ 'caps_b3s.json' = '8CBEA48D300A8A0D38D9A89D950274DF08743326CA3F1E9EAFC2763ADD9CBF31'; 'caps_b3g2.json' = 'EE551D3AACBF9EC02D2AC7F5E7E6E12F44E15ABA2C39F5F38C3F1E3EC12D7ED4' }
# SHA-256 of the files the reader rules change, at each commit (custom_io-relative path -> hash): proves the zip is that commit.
$EXPB3R = @{
  'models\b3.py'              = 'E36C81F778C4CE76DC2CA2DE823137DF2F72A34A945E8513C0509872F7CB9C91'
  'models\eg.py'              = 'A2CF6259E0412582390FD98FD47E681D6999902748F3A822ABE4AA69EE85FAFB'
  'models\ledger.py'          = 'FB922235EF49A044407D3BC03012BFD0C881A9B51D437428478F7A591DD4E5A5'
  'models\tool.py'            = 'B1A062F059645308C04568CD0DE65F03B7B830DCFDF4D57D22602A406202BF65'
  'tests\test_reader_rule.py' = '0ACBE241545704F912261460A7A682E27790B3361E31B0622208D35D455FEF3D'
}
$EXPG2  = @{
  'models\b3g2.py'   = 'A4C61F0B567EC7E62B3233549BE63ECA7BCA2A3F35A934DFC217FA49390868CE'
  'models\writer.py' = 'F3A40AD58749BBC24A964942DC650C79864D6A74442628AAC7D752730E73309E'
  'models\b3.py'     = 'F3EF34D9F13256CCEE1CA7DD47EFC32CB7EAF51E3A09C4221E3BE4C0858804C8'
  'models\eg.py'     = '4F2867F0E2E5F4CC29010484CCF93936086B5B2CFBF06F8047A777FD76ED6B5E'
  'models\ledger.py' = '0B2EE9F494808A1C5B7BDF4824EE4D6E012948374BE466EE25FD6F66F19F140F'
  'models\tool.py'   = '87AF44FD8E23A06E4C412520315A97E573251EAB93DC0EA34936B43B152DB2F9'
  'g8a\configs.py'   = '31287A25A6AD9CBF48973520F1174C788A3DB5CE61F607265AA5EC8FA99BD5DA'
  'g8a\job.py'       = 'A590E3F176159F531571B1E5AE95BD48D2160238CB999ADD5EB6BE7734FE6A1A'
}
# CPU test modules that must pass in each new folder (python -m custom_io.tests.<name>: exit 0, no line starting FAIL, a line starting ALL OK or ok).
$TESTB3R = @('test_reader_rule', 'test_g8a', 'test_b3_run')
$TESTG2  = @('test_reader_rule', 'test_b3g2_run', 'test_talk_rounds', 'test_b3g2')   # each under 0.5 GB on the CPU (test_no_plug, 4.8 GB, left out)
$QB3R   = @('8aB3G1s400', '8aB3G1s401')
$QG2    = @('8aG2C3S', '8aB3G2s400', '8aG2C10S', '8aC30S')
$STAMP  = (Get-Date).ToString('yyyyMMdd-HHmm')
$script:made = @()
$script:swapped = @()
$script:npok = $false
function Stamp { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + ' ET' }
# Before the swap: every new folder made so far is renamed .failed-<stamp>, so the old code stays and a rerun unpacks afresh.
function Fail($m) {
  foreach ($d in $script:made) { if (Test-Path $d) { $n = (Split-Path -Leaf $d) -replace '\.new-', '.failed-'; Rename-Item -Path $d -NewName $n; "renamed $(Split-Path -Leaf $d) to $n (kept)" } }
  if ($script:swapped.Count) { "FAILED: $m (already swapped in this run, and kept: $($script:swapped -join ', '); nothing else was changed)" }
  else { "FAILED: $m (the waiter and the live src folders were not changed)" }
  exit 1
}
# Free memory (MB) the OS can still commit; a CPU step starts only with its estimate plus 2 GB to spare.
function NeedMem($mb, $what) {
  $free = [math]::Floor((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1024)
  if ($free -lt $mb + 2048) { Fail "only $free MB free to commit; $what needs about $mb MB plus 2,048 to spare (run again when a G1 run has ended)" }
  "  memory: $free MB free to commit (need $mb + 2048 for $what)"
}
function Hash($p) { if (Test-Path $p) { (Get-FileHash $p).Hash } else { 'missing' } }
function Waiters($name) { @(Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" | Where-Object { $_.CommandLine -like "*$name*" }) }
function Line1($f) { "$(Get-Content $f -TotalCount 1)".Trim() }
# The waiter must still wait for G1: one q8aPost3_wait.ps1, and no 'gate G1 has ended' since its last start line.
function StillWaiting {
  $w = @(Waiters 'q8aPost3_wait.ps1')
  if ($w.Count -ne 1) { return "expected one q8aPost3_wait.ps1 waiter, found $($w.Count)" }
  $lines = @(Get-Content $LOG)
  $start = -1
  for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*chain waiter v3 started*') { $start = $i } }
  if ($start -lt 0) { return "no 'chain waiter v3 started' line in $LOG" }
  for ($i = $start; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*gate G1 has ended*') { return 'the waiter is already past gate G1 (install by hand, or WORK\STOP first)' } }
  return $null
}
# CPU-only python in a folder ($pp: PYTHONPATH or $null); returns its output lines, exit code in $script:rc.
function CpuPy($dir, $pp, $pyargs) {
  $env:CUDA_VISIBLE_DEVICES = '-1'
  $env:PYTHONUTF8 = '1'
  $keep = $env:PYTHONPATH
  if ($pp) { $env:PYTHONPATH = $pp }
  Push-Location $dir
  $out = @(& $PY @pyargs 2>&1 | ForEach-Object { "$_" })
  $script:rc = $LASTEXITCODE
  Pop-Location
  Remove-Item Env:\CUDA_VISIBLE_DEVICES
  if ($keep) { $env:PYTHONPATH = $keep } else { Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue }
  return $out
}
function Tests($dir, $pp, $mods) {
  foreach ($t in $mods) {
    NeedMem 1500 $t
    $out = CpuPy $dir $pp @('-m', "custom_io.tests.$t")
    "  ${t}: $(($out | Select-Object -Last 1))"
    if ($rc -ne 0 -or @($out -match '^FAIL').Count -or -not @($out -match '^(ALL OK|ok\s)').Count) { $out | Select-Object -Last 8; Fail "$t failed (rc $rc) in $(Split-Path -Leaf $dir)" }
  }
}
# Unpacks $zip into <live>.new-<stamp> (-> $script:unpacked) and checks the pinned hashes. Called as a statement, so a Fail inside prints.
function Unpack($zip, $live, $caps, $jsons, $exp) {
  $new = "$live.new-$STAMP"
  if (Test-Path $new) { Fail "$new already exists" }
  Expand-Archive -Path $zip -DestinationPath $new
  $script:made += $new
  if ((Hash "$new\custom_io\g8a\caps.py") -ne $caps) { Fail "caps.py in $(Split-Path -Leaf $zip) is not the pinned one ($(Hash "$new\custom_io\g8a\caps.py"))" }
  foreach ($k in $jsons.Keys) { if ((Hash "$new\custom_io\g8a\$k") -ne $jsons[$k]) { Fail "$k in $(Split-Path -Leaf $zip) hash wrong" } }
  foreach ($k in $exp.Keys) { if ((Hash "$new\custom_io\$k") -ne $exp[$k]) { Fail "$k in $(Split-Path -Leaf $zip) is not the expected commit's" } }
  $script:unpacked = $new
}
# Queue files the chain needs in the new folder: the new commit's own copy wins; a missing one comes from the live folder.
function Queues($new, $live, $qs) {
  New-Item -ItemType Directory -Force "$new\custom_io\queue_local" | Out-Null
  foreach ($q in $qs) {
    $n = "$new\custom_io\queue_local\$q-pc.txt"; $o = "$live\custom_io\queue_local\$q-pc.txt"
    if (Test-Path $n) { "  queue ${q}: the new commit's copy$(if ((Test-Path $o) -and ((Hash $n) -ne (Hash $o))) { ' (differs from the live one)' })" }
    elseif (Test-Path $o) { Copy-Item $o $n; "  queue ${q}: copied from the live folder" }
    else { Fail "queue $q-pc.txt is in neither the new nor the live folder" }
  }
}
# Old folder -> <name>.before-rr-<stamp>, new folder -> <name>. Undoes the first rename if the second fails.
function Swap($new, $live) {
  $old = (Split-Path -Leaf $live) + ".before-rr-$STAMP"
  try { Rename-Item -Path $live -NewName $old -ErrorAction Stop } catch { Fail "could not rename $live aside (a file in it is open?): $($_.Exception.Message)" }
  try { Rename-Item -Path $new -NewName (Split-Path -Leaf $live) -ErrorAction Stop } catch {
    try { Rename-Item -Path "$CIO\$old" -NewName (Split-Path -Leaf $live) -ErrorAction Stop } catch { "NEEDS ATTENTION: $(Split-Path -Leaf $live) is missing; rename $old back by hand" }
    Fail "could not rename $(Split-Path -Leaf $new) into place; the old folder is back: $($_.Exception.Message)"
  }
  $script:made = @($script:made | Where-Object { $_ -ne $new })
  $script:swapped += (Split-Path -Leaf $live)
  "$(Split-Path -Leaf $live): new code in place; the old code is kept as $old"
}

# 1. What is here, and the waiter still waits for G1.
$doB3R = Test-Path "$IN\b3r.zip"
$doG2  = Test-Path "$IN\g2.zip"
$doFC2 = Test-Path "$IN\8aFC2-pc.txt"
$doV3E = (Test-Path "$IN\swap_v3e.ps1") -and (Test-Path "$IN\q8aPost3_wait.ps1")
$doC30 = Test-Path "$IN\8aC30S-pc.txt"
$doWIDE = Test-Path "$IN\wide\install_wide.ps1"
if ($doV3E -and "$(@(Get-Content $LOG | Where-Object { $_ -like '*chain waiter v3 started*' }) | Select-Object -Last 1)" -like '*(v3e;*') { 'waiter v3e is already running'; $doV3E = $false }
if (-not ($doB3R -or $doG2 -or $doFC2 -or $doV3E -or $doWIDE)) { Fail "nothing to install in $IN" }
if ($doC30 -and -not $doG2) { Fail '8aC30S-pc.txt (c30s) is installed only together with g2.zip' }
if ($doB3R -and $SHAB3R -eq 'TBD') { Fail 'b3r.zip is here but this script has no group 1 commit filled in' }
if ($doG2 -and $SHAG2 -eq 'TBD') { Fail 'g2.zip is here but this script has no group 2 commit filled in' }
foreach ($f in @('fc2check.py', 'infer_speed.py', 'fc100v2.md')) { if ($doFC2 -and -not (Test-Path "$IN\$f")) { Fail "8aFC2-pc.txt needs $f beside it" } }
foreach ($f in @('g2check.py', 'b3_capcheck.py')) { if (-not (Test-Path "$IN\$f")) { Fail "$f missing in $IN" } }
foreach ($f in @("$SRCB3R\B3R-SETUP-OK.txt", "$SRCG2\G2-SETUP-OK.txt", "$WORK\b3-inputs\caps_b3.json")) { if (-not (Test-Path $f)) { Fail "$f missing (is the chain installed?)" } }
$why = StillWaiting
if ($why) { Fail $why }
if ($doB3R -or $doG2 -or $doFC2) { NeedMem $(if ($doG2 -or $doFC2) { 4000 } else { 1500 }) 'the CPU checks (the largest is Gemma in fp32)' }
"to install:$(if ($doB3R) { " src-b3r ($SHAB3R)" })$(if ($doG2) { " src-b3g2 ($SHAG2)" })$(if ($doFC2) { ' the five-shape fc100 list' })$(if ($doC30) { ' the c30s queue' })$(if ($doV3E) { ' waiter v3e' })$(if ($doWIDE) { ' test WIDE' }); the waiter still waits for G1"

# 2. Group 1 code: unpack, hashes (caps.py as pinned in the live B3R-SETUP-OK.txt), queues, CPU checks, marker.
if ($doB3R -and @(Get-Content "$SRCB3R\B3R-SETUP-OK.txt") -match "commit $SHAB3R") { 'src-b3r: this commit is already installed'; $doB3R = $false }
if ($doB3R) {
  $capsr = (Line1 "$SRCB3R\B3R-SETUP-OK.txt") -replace '^caps\.py\s+', ''
  Unpack "$IN\b3r.zip" $SRCB3R $capsr @{ 'caps_b3.json' = $JSONB3 } $EXPB3R
  $nb = $script:unpacked
  "src-b3r: unpacked $SHAB3R into $(Split-Path -Leaf $nb); caps.py and caps_b3.json match"
  Queues $nb $SRCB3R $QB3R
  NeedMem 1500 'b3_capcheck'
  $out = CpuPy $nb $null @("$IN\b3_capcheck.py", $nb, "$WORK\b3-inputs\caps_b3.json")
  "  b3_capcheck: $(($out | Select-Object -Last 1))"
  if ($rc -ne 0) { Fail 'b3_capcheck: B3''s thinking-round cap is not 32 in the new group 1 code' }
  Tests $nb $null $TESTB3R
  $h1r = Hash "$nb\custom_io\models\tool_h1.py"
  Set-Content -Encoding ascii "$nb\B3R-SETUP-OK.txt" -Value @("caps.py $capsr", "tool_h1.py $h1r", "caps_b3.json $JSONB3", "commit $SHAB3R (reader rules, on 8fce7247a8)",
    "b3_capcheck 32; $($TESTB3R -join ', ') ok (CPU); install_rr.ps1", (Stamp))
  'src-b3r: checks ok, marker written in the new folder'
}

# 3. Group 2 code and the fc100 list. The list and the answer timer are checked in the folder that will be live (the new one when g2.zip is here).
if ($doG2 -and @(Get-Content "$SRCG2\G2-SETUP-OK.txt") -match "commit $SHAG2") { 'src-b3g2: this commit is already installed'; $doG2 = $false }
if ($doFC2 -and -not $doG2 -and ((Hash "$SRCG2\custom_io\queue_local\8aFC2-pc.txt") -eq (Hash "$IN\8aFC2-pc.txt")) -and ((Hash "$CIO\infer_speed.py") -eq (Hash "$IN\infer_speed.py"))) {
  'src-b3g2: this fc100 list and answer timer are already installed'; $doFC2 = $false
}
if ($doC30 -and -not $doG2) {
  if ((Hash "$SRCG2\custom_io\queue_local\8aC30S-pc.txt") -eq (Hash "$IN\8aC30S-pc.txt")) { 'src-b3g2: this c30s queue is already installed'; $doC30 = $false }
  else { Fail 'the c30s queue here differs from the live one, but its group 2 commit is already installed (install the queue by hand)' }
}
$g2dir = $SRCG2
if ($doG2) {
  Unpack "$IN\g2.zip" $SRCG2 $CAPSG2 $JSONG2 $EXPG2
  $g2dir = $script:unpacked
  "src-b3g2: unpacked $SHAG2 into $(Split-Path -Leaf $g2dir); caps.py and both caps files match"
  Queues $g2dir $SRCG2 (@($QG2 | Where-Object { -not ($doC30 -and $_ -eq '8aC30S') }) + $(if ($doFC2) { @() } else { @('8aFC2') }))
  if ($doFC2) { Copy-Item -Force "$IN\8aFC2-pc.txt" "$g2dir\custom_io\queue_local\8aFC2-pc.txt"; "  queue 8aFC2: the five-shape list$(if (Select-String -Path "$IN\8aFC2-pc.txt" -Pattern '"eg_pre": true' -SimpleMatch -Quiet) { ' (no plug)' })" }
  if ($doC30) { Copy-Item -Force "$IN\8aC30S-pc.txt" "$g2dir\custom_io\queue_local\8aC30S-pc.txt"; "  queue 8aC30S: the package's copy$(if (Select-String -Path "$IN\8aC30S-pc.txt" -Pattern '--noplug' -SimpleMatch -Quiet) { ' (no plug)' })" }
  NeedMem 1500 'g2check'
  $out = CpuPy $g2dir $EGPATH @("$IN\g2check.py")
  "  g2check: $(($out | Select-Object -Last 1))"
  if ($rc -ne 0 -or -not ("$out" -like '*G2 CPU CHECK OK*')) { $out | Select-Object -Last 8; Fail "g2check failed (rc $rc)" }
  Tests $g2dir $EGPATH $TESTG2
}
if ($doG2 -or $doFC2) {
  if ($doG2) { $fcq = "$g2dir\custom_io\queue_local\8aFC2-pc.txt" } else { $fcq = "$env:TEMP\8aFC2-rr-$STAMP.txt"; Copy-Item -Force "$IN\8aFC2-pc.txt" $fcq }
  if ($doFC2) { $isp = "$IN\infer_speed.py" } else { $isp = "$CIO\infer_speed.py" }
  NeedMem 1500 'fc2check (models on the meta device)'
  $out = CpuPy $g2dir $EGPATH @("$IN\fc2check.py", $fcq)
  "  fc2check: $(($out | Select-Object -Last 1)) ($(@($out -like '8aFC2-*').Count) runs)"
  if ($rc -ne 0 -or -not ("$out" -like '*FC2 CPU CHECK OK*')) { $out | Select-Object -Last 8; Fail "fc2check failed (rc $rc)" }
  NeedMem 1500 'the answer-timer selftest'
  $out = CpuPy $g2dir $EGPATH @($isp, '--src', $g2dir, '--queue', $fcq, '--selftest', "$env:TEMP\infer-selftest-rr-$STAMP")
  "  infer_speed selftest: $(($out | Select-Object -Last 1))"
  if ($rc -ne 0 -or -not ("$out" -like '*INFER SELFTEST OK*')) { $out | Select-Object -Last 8; Fail "infer_speed selftest failed (rc $rc)" }
  # No plug (Ben, 4:12 PM ET 11 Oct): a list or c30s queue that will be live and reads Gemma's own 512 numbers is gated on the fp32 proof that
  # this state is Gemma's (512 wide; its own projection of it equals its 768 output within 1e-4). CPU only: G1 keeps the GPU.
  $npf = @(@($fcq, "$g2dir\custom_io\queue_local\8aC30S-pc.txt") | Where-Object { Test-Path $_ })
  if (@(Select-String -Path $npf -Pattern '"eg_pre": true', '--noplug' -SimpleMatch).Count) {
    NeedMem 4000 'eg check cpu pre (Gemma in fp32 on the CPU)'
    $keepeg = $env:CUSTOM_IO_EG2
    $env:CUSTOM_IO_EG2 = $EG2
    $out = CpuPy $g2dir $EGPATH @('-m', 'custom_io.models.eg', 'check', 'cpu', 'pre')
    if ($keepeg) { $env:CUSTOM_IO_EG2 = $keepeg } else { Remove-Item Env:\CUSTOM_IO_EG2 -ErrorAction SilentlyContinue }
    "  eg check cpu pre (no plug): $(($out | Select-Object -Last 1))"
    if ($rc -ne 0 -or -not ("$out" -like '*"pre_ok": true*')) { $out | Select-Object -Last 8; Fail "the no-plug Gemma proof failed (rc $rc)" }
    $script:npok = $true
  }
}
if ($doG2) {
  Set-Content -Encoding ascii "$g2dir\G2-SETUP-OK.txt" -Value @("caps.py $CAPSG2", "commit $SHAG2 (reader rules + G2f writer, talker thread)",
    "caps_b3s.json $($JSONG2['caps_b3s.json'])", "caps_b3g2.json $($JSONG2['caps_b3g2.json'])",
    "g2check ok; fc2check ok; infer_speed selftest ok; $(if ($script:npok) { 'eg check cpu pre ok (no plug); ' })$(if ($TESTG2.Count) { ($TESTG2 -join ', ') + ' ok; ' })CPU; install_rr.ps1", (Stamp))
  'src-b3g2: checks ok, marker written in the new folder'
}

# 4. Swap, after one more look at the waiter.
$why = StillWaiting
if ($why) { Fail "$why (just before the swap)" }
if ($doB3R) { Swap $nb $SRCB3R }
if ($doG2) { Swap $g2dir $SRCG2 }
if ($doFC2) {
  if (-not $doG2) {
    $q = "$SRCG2\custom_io\queue_local\8aFC2-pc.txt"
    if (Test-Path $q) { Rename-Item $q "8aFC2-pc.txt.before-rr-$STAMP" }
    Copy-Item "$IN\8aFC2-pc.txt" $q
    'src-b3g2: 8aFC2-pc.txt replaced by the five-shape list (old copy kept beside it)'
  }
  if (Test-Path "$CIO\infer_speed.py") { Copy-Item -Force "$CIO\infer_speed.py" "$CIO\infer_speed.py.before-rr-$STAMP" }
  Copy-Item -Force "$IN\infer_speed.py" "$CIO\infer_speed.py"
  Copy-Item -Force "$IN\fc100v2.md" "$CIO\fc100v2.template.md"
  'copied infer_speed.py (old copy kept) and the fc100v2 card template'
}
if ($doB3R -or $doG2 -or $doFC2) { "$(Stamp) install_rr.ps1:$(if ($doB3R) { " src-b3r -> $SHAB3R" })$(if ($doG2) { " src-b3g2 -> $SHAG2" })$(if ($doFC2) { ' fc100 part 2 -> five shapes' }) (old folders kept as *.before-rr-$STAMP)" | Add-Content -Encoding ascii $LOG }

# 5. Waiter v3e after the code (its own script checks and swaps; it refuses on its own if anything is off), then test WIDE (needs v3e).
if ($doV3E) {
  '--- swap_v3e.ps1:'
  & powershell -NoProfile -ExecutionPolicy Bypass -File "$IN\swap_v3e.ps1"
}
if ($doWIDE) {
  '--- wide\install_wide.ps1:'
  & powershell -NoProfile -ExecutionPolicy Bypass -File "$IN\wide\install_wide.ps1"
}
'--- markers and waiter log:'
"src-b3r:  $(@(Get-Content "$SRCB3R\B3R-SETUP-OK.txt") -join ' | ')"
"src-b3g2: $(@(Get-Content "$SRCG2\G2-SETUP-OK.txt") -join ' | ')"
Get-Content $LOG -Tail 3
'INSTALL RR DONE'
