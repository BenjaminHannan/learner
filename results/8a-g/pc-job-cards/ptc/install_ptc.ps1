# Installs arm PTC (the plain model trained with the calculator; spec design/8a-g-gemma-growth-2026-10-08.md addendum AG, section 38) on BensPC as two
# inserted jobs of the post-G1 chain waiter v3e: WORK\insert\13-ptc3s.txt (queue 8aPTC3S, 3M) and WORK\insert\14-ptc10s.txt (queue 8aPTC10S, 10M), which run
# after 11-at and 12-g2c10s and before 30-g2q and 46-tp. Run from the folder the Mac copied (in-ptc): it needs plain_tf_steps.py, plain_lm.py, configs.py,
# job.py, capcount.py, test_ptc.py, ptccheck.py, 8aPTC3S-pc.txt, 8aPTC10S-pc.txt, ptc3s.template.md and ptc10s.template.md beside it.
# src-b3g2 (group 2's code, custom_io at 74d6e92c75: reader rules + G2f writer) is copied, never changed, to src-ptc.new-<stamp>; the six files PTC replaces are checked against
# 74d6e92c75's sha256 before and after the copy, the overlays are put in, the two queue files go into custom_io\queue_local, and ptccheck.py runs on the CPU
# (no GPU, no EmbeddingGemma weights). Only then is the folder renamed src-ptc, the card templates copied into custom-io and the two insert files written
# (each with the caps: line v3e needs for a src other than src-b3g2 / src-b3). A failed check renames the new folder src-ptc.failed-<stamp> and changes nothing
# else. Only while the waiter is v3e and has not passed its first insert check point (right after G2f). It stops nothing, never touches the chain's runs,
# results, pools or checkpoints, and deletes nothing. Run again after a success: "already installed", INSTALL PTC DONE.
$IN     = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO    = 'C:\Users\benja\custom-io'
$WORK   = "$CIO\work"
$LOG    = "$WORK\q8aPost-waiter.log"
$PY     = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$EGPATH = 'C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages'
$SRCB   = "$CIO\src-b3g2"
$SRCP   = "$CIO\src-ptc"
$INS    = "$WORK\insert"
$CAPS   = '32862AE2D4E6E401FCAD5BB6C5E54B0B8845019202DEA73E2CB4C7EFE5EEA03E'   # g8a\caps.py of src-b3g2 (74d6e92c75); src-ptc keeps it unchanged
# the six files PTC replaces: file here -> path under custom_io, sha256 at 74d6e92c75 (none for the new test), sha256 of the PTC file
$FILES = @(
  @{ f = 'capcount.py';        rel = 'capcount.py';              o = '92E4CE46013CCC67CBAD583AC9EDB52E76F7504CB004FD236255A2EB89F22C3F';        n = 'E3C43AC13DC76420BBE3DD442456489CB998402F07E4413E39EFE6A8EEA0C97F' },
  @{ f = 'plain_tf_steps.py';  rel = 'models\plain_tf_steps.py'; o = 'E3418B45FB339C38F90765CC7929C4B60E97453E28E375102EF15BFF64F76226';  n = 'C39CDF1DC91EDDA7A0F11CF658FAF22148E533759227FC72153DAAFDEAAC4225' },
  @{ f = 'plain_lm.py';        rel = 'models\plain_lm.py';       o = 'E90ACCF2E332D08A1E14CD2B5B537A9BE97BC93C44D48ED14DFE26FA8567AD10';        n = 'F0E5FE42662EADC862E300DADE9470EB4AFA2898AF228A5F8061DA86C4CEF90B' },
  @{ f = 'configs.py';         rel = 'g8a\configs.py';           o = '31287A25A6AD9CBF48973520F1174C788A3DB5CE61F607265AA5EC8FA99BD5DA';         n = '48AA19CCB8B329FE11E45E42A17872D2581298CDBC03C2B11E3E034ADC887ECF' },
  @{ f = 'job.py';             rel = 'g8a\job.py';               o = 'A590E3F176159F531571B1E5AE95BD48D2160238CB999ADD5EB6BE7734FE6A1A';             n = 'EB0CF9DB191A75992F8ED24464D996B7EAABC86538843762B23E1A8C5F3C6888' },
  @{ f = 'test_ptc.py';        rel = 'tests\test_ptc.py';        o = $null;                 n = '152D694A6B5798AA9CC0C352E5BA746E4D61F80F71BE0EB62E062C9BD1F6F972' })
$QUEUES = @('8aPTC3S', '8aPTC10S')
$INSERTS = @(@{ name = '13-ptc3s.txt'; q = '8aPTC3S'; card = 'ptc3s.template.md' }, @{ name = '14-ptc10s.txt'; q = '8aPTC10S'; card = 'ptc10s.template.md' })
$STAMP  = (Get-Date).ToString('yyyyMMdd-HHmm')
$script:made = $null
function Stamp { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + ' ET' }
function Fail($m) {
  if ($script:made -and (Test-Path $script:made)) { $n = (Split-Path -Leaf $script:made) -replace '\.new-', '.failed-'; Rename-Item -Path $script:made -NewName $n; "renamed $(Split-Path -Leaf $script:made) to $n (kept)" }
  "FAILED: $m (the waiter, src-b3g2 and WORK\insert were not changed)"
  exit 1
}
function Hash($p) { if (Test-Path $p) { (Get-FileHash $p -Algorithm SHA256).Hash } else { 'missing' } }
function Waiters($name) { @(Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" | Where-Object { $_.CommandLine -like "*$name*" }) }
# Free memory (MB) the OS can still commit; a CPU check starts only with its need plus 2 GB to spare.
function NeedMem($mb, $what) {
  $free = [math]::Floor((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1024)
  if ($free -lt $mb + 2048) { Fail "only $free MB free to commit; $what needs about $mb MB plus 2,048 to spare (run again when a run has ended)" }
  "  memory: $free MB free to commit (need $mb + 2048 for $what)"
}

# 1. Already installed? The folder with its marker and both inserts (also once the waiter renamed them .done-...).
if ((Test-Path "$SRCP\PTC-SETUP-OK.txt") -and @(Get-ChildItem "$INS\13-ptc3s.txt*" -ErrorAction SilentlyContinue).Count -and @(Get-ChildItem "$INS\14-ptc10s.txt*" -ErrorAction SilentlyContinue).Count) {
  "src-ptc and its inserts are already installed: $(@(Get-Content "$SRCP\PTC-SETUP-OK.txt") -join ' | ') | $(@(Get-ChildItem "$INS\1[34]-ptc*.txt*" | ForEach-Object { $_.Name }) -join ', ')"
  'INSTALL PTC DONE'
  exit 0
}
foreach ($x in $FILES) { if (-not (Test-Path "$IN\$($x.f)")) { Fail "$($x.f) missing in $IN" } }
foreach ($f in @('ptccheck.py', '8aPTC3S-pc.txt', '8aPTC10S-pc.txt', 'ptc3s.template.md', 'ptc10s.template.md')) { if (-not (Test-Path "$IN\$f")) { Fail "$f missing in $IN" } }
foreach ($x in $FILES) { if ((Hash "$IN\$($x.f)") -ne $x.n) { Fail "$($x.f) here is not the PTC file ($(Hash "$IN\$($x.f)"))" } }
if (Test-Path $SRCP) { Fail "$SRCP exists without a finished install (rename it aside by hand first)" }
foreach ($i in $INSERTS) { if (@(Get-ChildItem "$INS\$($i.name)*" -ErrorAction SilentlyContinue).Count) { Fail "WORK\insert already holds $(@(Get-ChildItem "$INS\$($i.name)*" | ForEach-Object { $_.Name }) -join ', ')" } }
if (-not (Test-Path "$INS\README.txt")) { Fail 'WORK\insert\README.txt missing (is v3e installed?)' }
# The waiter: v3e (give it up to 2 minutes to write its start line), one copy, and not past its first insert check point since that start line.
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
# (from the line after the start line: v3e's own start line says "inserted jobs from WORK\insert after group 2")
for ($i = $start + 1; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*8aB3G2s400 ended*' -or $lines[$i] -like '*inserted job *(after group 2*') { Fail "the waiter is already past G2f and its first insert check point: $($lines[$i])" } }
"waiter v3e (pid $($w[0].ProcessId)) is running and has not reached its first insert check point; 13-ptc3s and 14-ptc10s run there, after 11-at and 12-g2c10s"

# 2. Copy src-b3g2 (never changed) and check it is 74d6e92c75's where PTC replaces or relies on it.
if ((Hash "$SRCB\custom_io\g8a\caps.py") -ne $CAPS) { Fail "$SRCB\custom_io\g8a\caps.py is not group 2's ($(Hash "$SRCB\custom_io\g8a\caps.py"))" }
foreach ($x in $FILES) { if ($x.o -and (Hash "$SRCB\custom_io\$($x.rel)") -ne $x.o) { Fail "$SRCB\custom_io\$($x.rel) is not 74d6e92c75's ($(Hash "$SRCB\custom_io\$($x.rel)"))" } }
$new = "$SRCP.new-$STAMP"
if (Test-Path $new) { Fail "$new already exists" }
New-Item -ItemType Directory $new | Out-Null
$script:made = $new
Copy-Item -Recurse "$SRCB\custom_io" "$new\custom_io"
if ((Hash "$new\custom_io\g8a\caps.py") -ne $CAPS) { Fail 'the copy of caps.py differs from src-b3g2''s' }
foreach ($x in $FILES) { if ($x.o -and (Hash "$new\custom_io\$($x.rel)") -ne $x.o) { Fail "the copy of $($x.rel) differs from src-b3g2's" } }
foreach ($x in $FILES) {
  Copy-Item -Force "$IN\$($x.f)" "$new\custom_io\$($x.rel)"
  if ((Hash "$new\custom_io\$($x.rel)") -ne $x.n) { Fail "$($x.f) did not copy to $($x.rel)" }
}
New-Item -ItemType Directory -Force "$new\custom_io\queue_local" | Out-Null
foreach ($q in $QUEUES) {
  Copy-Item -Force "$IN\$q-pc.txt" "$new\custom_io\queue_local\$q-pc.txt"
  if ((Hash "$new\custom_io\queue_local\$q-pc.txt") -ne (Hash "$IN\$q-pc.txt")) { Fail "$q-pc.txt did not copy" }
}
"src-ptc: copied src-b3g2's custom_io into $(Split-Path -Leaf $new) (caps.py and the 5 replaced files were 74d6e92c75's); the 6 PTC files and the 2 queue files are in"

# 3. CPU check: calc_full, mask == generate, masked loss, counts == PTS at 3M and 10M, calc_train off == the originals, both queues through job.py's parser.
NeedMem 2000 'ptccheck (python + torch, small models and two counted ones on the CPU)'
$env:CUDA_VISIBLE_DEVICES = '-1'; $env:PYTHONUTF8 = '1'; $env:PYTHONPATH = $EGPATH; $env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location $new
$out = @(& $PY "$IN\ptccheck.py" $SRCB 2>&1 | ForEach-Object { "$_" })
$rc = $LASTEXITCODE
Pop-Location
Remove-Item Env:\CUDA_VISIBLE_DEVICES, Env:\PYTHONPATH, Env:\PYTHONDONTWRITEBYTECODE -ErrorAction SilentlyContinue
$out | Select-Object -Last 4 | ForEach-Object { "  ptccheck: $_" }
if ($rc -ne 0 -or -not ("$out" -like '*PTC CPU CHECK OK*')) { $out | Select-Object -Last 12; Fail "ptccheck failed (rc $rc)" }
# src-b3g2 itself must still be 74d6e92c75's (the check ran from the copy)
foreach ($x in $FILES) { if ($x.o -and (Hash "$SRCB\custom_io\$($x.rel)") -ne $x.o) { Fail "$SRCB\custom_io\$($x.rel) changed during the check" } }
$capsNew = Hash "$new\custom_io\g8a\caps.py"
if ($capsNew -ne $CAPS) { Fail "caps.py of the new folder is $capsNew" }
Set-Content -Encoding ascii "$new\PTC-SETUP-OK.txt" -Value @("caps.py $CAPS (src-b3g2's, unchanged)", 'base: src-b3g2 = custom_io at 74d6e92c75',
  (@($FILES | ForEach-Object { "$($_.rel) $($_.n)$(if ($_.o) { " (was $($_.o))" } else { ' (new)' })" })),
  'queues 8aPTC3S and 8aPTC10S in custom_io\queue_local; ptccheck ok (CPU); install_ptc.ps1', (Stamp))

# 4. The insert files as the waiter will read them (its own regex and checks), before anything is moved.
$want = @{}
foreach ($i in $INSERTS) {
  $content = @("queue: $($i.q)", 'src: src-ptc', "caps: $capsNew", "card: $($i.card)")
  $kv = @{}
  foreach ($l in $content) { if ($l -match '^\s*(queue|src|card|caps|cmd|hours)\s*:\s*(\S+)\s*$') { $kv[$Matches[1]] = $Matches[2] } }
  if (-not $kv['queue'] -or -not $kv['src'] -or $kv['src'] -notmatch '^src-[A-Za-z0-9_-]+$' -or $kv['caps'] -notmatch '^[0-9A-Fa-f]{64}$') { Fail "insert $($i.name) would be refused by the waiter: $($content -join ' | ')" }
  if (-not (Test-Path "$new\custom_io\queue_local\$($kv['queue'])-pc.txt")) { Fail "queue file $($kv['queue'])-pc.txt missing in the new folder" }
  $want[$i.name] = $content
}

# 5. Into place: the folder, the card templates (an older copy kept as .before-<stamp>), then the insert files (the waiter lists WORK\insert at its check point).
try { Rename-Item -Path $new -NewName (Split-Path -Leaf $SRCP) -ErrorAction Stop } catch { Fail "could not rename $(Split-Path -Leaf $new) to src-ptc: $($_.Exception.Message)" }
$script:made = $null
foreach ($i in $INSERTS) {
  if (Test-Path "$CIO\$($i.card)") { Copy-Item -Force "$CIO\$($i.card)" "$CIO\$($i.card).before-$STAMP" }
  Copy-Item -Force "$IN\$($i.card)" "$CIO\$($i.card)"
  if ((Hash "$CIO\$($i.card)") -ne (Hash "$IN\$($i.card)")) { "FAILED: $($i.card) did not copy to custom-io (src-ptc is in place; no insert written)"; exit 1 }
}
foreach ($i in $INSERTS) { Set-Content -Encoding ascii "$INS\$($i.name)" -Value $want[$i.name] }
"$(Stamp) install_ptc.ps1: src-ptc (src-b3g2 + the PTC overlay, 74d6e92c75) and WORK\insert\13-ptc3s.txt + 14-ptc10s.txt (arm PTC, seed 400, 3M and 10M) installed" | Add-Content -Encoding ascii $LOG
"src-ptc: in place; card templates ptc3s.template.md and ptc10s.template.md in custom-io; WORK\insert:"
foreach ($i in $INSERTS) { "  $($i.name): $(@(Get-Content "$INS\$($i.name)") -join ' | ')" }
'INSTALL PTC DONE'
