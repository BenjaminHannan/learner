# Post-G1 chain on BensPC, version 2 (9 Oct 2026, spec addendum O; replaces q8aPost_wait.ps1 while that one still waits for G1).
# After gate G1's last PC queue ends, one queue at a time:
#   1. test GX seed 400 (8aGXs400, src-8gx)                     2. fc100 (8aFC, src-b3)        3. g2c3 seed 400 (8aG2C3, src-b3)
#   4. B3 group 1 at 3M seed 400 (8aB3G1s400, src-b3r), then b3_readout.py (marks B3-1 to B3-6) into its log
#   5. only if GX seed 400 is alive: GX seed 401 (8aGXs401)     6. only if B3 seed 400 is alive: g2c3 s401 (8aG2C3s401), then B3 seed 401 + readout
#   7. g2c10 (8aG2C10, src-b3)                                  8. c30 (8aC30, src-b3) unless WORK\B3-READY.txt exists or c30 already ran in a gap
# Alive: GX = GX minus G-B2 pooled-5 >= +0.5 (X1's bar with the hair rule) and X4 not failed (analyze_gx); B3 = B3-1 >= +1.0 (b3_readout.py exit 0).
# WORK\GX-S401-GO.txt / GX-S401-SKIP.txt and WORK\B3-S401-GO.txt / B3-S401-SKIP.txt override those rules; a score that cannot be read skips seed 401.
# B3 needs src-b3r (PR #56 with the H1 round-cap fix, set up by upgrade_post_g1.ps1). If it is missing when B3 is due, c30 runs in the gap and the
# chain then holds until src-b3r\B3R-SETUP-OK.txt (or WORK\B3-SKIP.txt) exists. WORK\STOP holds the chain (it never removes STOP).
# Started detached by upgrade_post_g1.ps1, so it outlives the ssh session. It stops nothing and deletes nothing.
$CIO    = 'C:\Users\benja\custom-io'
$WORK   = "$CIO\work"
$SRCGX  = "$CIO\src-8gx"
$SRCB3  = "$CIO\src-b3"
$SRCB3R = "$CIO\src-b3r"
$JOBS   = 'C:\Users\benja\pc-jobs'
$PY     = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$CAPS   = '3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78'      # caps.py of the experts code (src-8gx; same as G1's)
$CAPSB3 = 'D276FAC05E1127D9979E9B8EA3A4F4E6CC4D7BAC33C218FA164117B60F1B4AA8'      # caps.py at 71299b1a47 (src-b3)
$LOG    = "$WORK\q8aPost-waiter.log"
$CARDS  = @('gx*.md', 'fc100*.md', 'g2c3*.md', 'b3g1*.md', 'g2c10*.md', 'c30*.md')     # this chain's cards in pc-jobs
$script:c30done = $false
function Now { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') }
function Say($m) { "$(Now) ET $m" | Add-Content -Encoding ascii $LOG }
function Runner { @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -like '*local_runner*' }).Count -gt 0 }
function G1Waiter { @(Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" | Where-Object { $_.CommandLine -like '*q8aG1*_wait.ps1*' }).Count -gt 0 }
function OkResult($glob) {
  foreach ($r in @(Get-ChildItem $glob -ErrorAction SilentlyContinue)) {
    try { if ((Get-Content $r.FullName -Raw | ConvertFrom-Json).status -eq 'ok') { return $true } } catch { }
  }
  return $false
}
# The newest job-level RESULT.json (small: status + box) with status ok, or $null.
function NewestOk($glob) {
  $best = $null
  foreach ($r in @(Get-ChildItem $glob -ErrorAction SilentlyContinue)) {
    try { if ((Get-Content $r.FullName -Raw | ConvertFrom-Json).status -eq 'ok' -and (-not $best -or $r.LastWriteTime -gt $best.LastWriteTime)) { $best = $r } } catch { }
  }
  if ($best) { return $best.FullName } else { return $null }
}
# Free = no queue runner and no WORK\STOP at each of $mins one-minute checks in a row.
function Free($mins) {
  for ($n = 0; $n -lt $mins; $n++) {
    if ((Runner) -or (Test-Path "$WORK\STOP")) { return $false }
    Start-Sleep -Seconds 60
  }
  return $true
}
function WaitFree($why) {
  $k = 0
  while (-not (Free 5)) {
    if ($k % 360 -eq 0) { Say "waiting: $why (a queue runner or WORK\STOP is present)" }
    $k++; Start-Sleep -Seconds 60
  }
}
function Hold($flag, $why) {
  Say "HOLD, NEEDS ATTENTION: $why. The chain goes on when WORK\$flag exists."
  while (-not (Test-Path "$WORK\$flag")) { Start-Sleep -Seconds 60 }
  Say "WORK\$flag found: going on"
}
# Waits until one of the full paths exists; returns it.
function HoldAny($paths, $why) {
  Say "HOLD, NEEDS ATTENTION: $why. The chain goes on when one of these exists: $($paths -join ', ')"
  while ($true) {
    foreach ($p in $paths) { if (Test-Path $p) { Say "$p found: going on"; return $p } }
    Start-Sleep -Seconds 60
  }
}
function MoveDone($pattern, $keep) {
  New-Item -ItemType Directory -Force "$JOBS\done" | Out-Null
  foreach ($c in @(Get-ChildItem "$JOBS\$pattern" -ErrorAction SilentlyContinue)) {
    if ($c.Name -ne $keep) { Move-Item -Force $c.FullName "$JOBS\done\"; Say "moved pc-jobs\$($c.Name) to done" }
  }
}
function Launch($q, $src, $hash) {
  $qf = "$src\custom_io\queue_local\$q-pc.txt"
  if (-not (Test-Path $qf)) { Say "queue file $qf missing: $q NOT started"; return $false }
  if ((Get-FileHash "$src\custom_io\g8a\caps.py").Hash -ne $hash) { Say "caps.py hash wrong in ${src}: $q NOT started"; return $false }
  if ((Runner) -or (Test-Path "$WORK\STOP")) { Say "a runner or STOP appeared: $q NOT started"; return $false }
  $cmd = "$CIO\q${q}_run.cmd"
  Set-Content -Encoding ascii $cmd -Value @(
    '@echo off',
    'set PYTHONUTF8=1',
    'set PYTHONUNBUFFERED=1',
    "cd /d $src",
    "$PY -m custom_io.local_runner run --work $WORK --queue custom_io\queue_local\$q-pc.txt --device cuda --par 1 --busy C:\Users\benja\GPU-BUSY.txt >> $WORK\q$q.log 2>&1")
  $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="cmd.exe /c $cmd"}
  Say "started $q from $src (ReturnValue $($r.ReturnValue), cmd pid $($r.ProcessId)); log WORK\q$q.log"
  return $true
}
# After a launch: wait up to 10 minutes for its runner to appear, then until no runner and no STOP for 5 minutes in a row.
function WaitEnd($q) {
  for ($t = 0; ($t -lt 10) -and -not (Runner); $t++) { Start-Sleep -Seconds 60 }
  if (-not (Runner)) { Say "no queue runner seen 10 minutes after starting $q (see WORK\q$q.log)" }
  WaitFree "$q running"
  Say "$q ended (no queue runner and no STOP for 5 minutes)"
}
# Installs pc-jobs\$name from a card template (moves this chain's other cards to done first). $subs: placeholder -> text.
function NewCard($tpl, $name, $subs) {
  foreach ($p in $CARDS) { MoveDone $p $name }
  if (-not (Test-Path "$CIO\$tpl")) { Say "template $tpl missing: no card"; return }
  $t = (Get-Content "$CIO\$tpl") -replace '@STARTED@', "$(Now) ET"
  if ($subs) { foreach ($k in $subs.Keys) { $t = $t -replace [regex]::Escape($k), $subs[$k] } }
  $t | Set-Content -Encoding ascii "$JOBS\$name"
  Say "installed pc-jobs\$name"
}
# G1 is over when 10M s401 has an ok RESULT.json (any spill letter), or the futility waiter skipped it, or WORK\G1-DONE.txt exists.
function G1Over {
  if (Test-Path "$WORK\G1-DONE.txt") { return $true }
  if (G1Waiter) { return $false }
  if (OkResult "$WORK\results\8aG1s401*-pc\8aG1s401*-10M-s401\RESULT.json") { return $true }
  $wl = "$WORK\q8aG1s401-waiter.log"
  return ((Test-Path $wl) -and [bool](Select-String -Path $wl -Pattern '10M s401 skipped' -SimpleMatch -Quiet))
}
# A GX queue is ok when every g8a job in its queue file has an ok RESULT.json under results\<queue>*-pc\8aGX*-<rung>-<seed>\.
function GXOk($q) {
  $qf = "$SRCGX\custom_io\queue_local\$q-pc.txt"
  $jobs = @(Get-Content $qf -ErrorAction SilentlyContinue | Where-Object { $_ -match '^g8a:\s+\S+' } | ForEach-Object { ($_ -split '\s+')[1] })
  if ($jobs.Count -eq 0) { Say "no g8a jobs found in $qf"; return $false }
  foreach ($j in $jobs) {
    $tail = $j.Substring($j.IndexOf('-') + 1)
    if (-not (OkResult "$WORK\results\$q*-pc\8aGX*-$tail\RESULT.json")) { Say "GX job $j has no ok RESULT.json"; return $false }
  }
  return $true
}
function GXCard($q, $seed) {
  NewCard 'gx.template.md' "gx-s$seed.md" @{'@Q@' = $q; '@SEED@' = "$seed"}
}
# analyze_gx on seed 400 (read-only, CPU): its lines go to this log, its JSON to WORK\gx-s400-readout.json.
function ScoreGX {
  $out = "$WORK\gx-s400-readout.json"
  Push-Location $SRCGX
  try { & $PY -m custom_io.g8a.analyze_gx --results "$WORK\results" --seeds 400 --out $out 2>&1 | ForEach-Object { Say "analyze_gx: $_" } } catch { Say "analyze_gx failed: $_" }
  Pop-Location
}
function GXAlive {
  if (Test-Path "$WORK\GX-S401-GO.txt") { Say 'WORK\GX-S401-GO.txt present: GX seed 401 runs'; return $true }
  if (Test-Path "$WORK\GX-S401-SKIP.txt") { Say 'WORK\GX-S401-SKIP.txt present: GX seed 401 skipped'; return $false }
  $out = "$WORK\gx-s400-readout.json"
  if (-not (Test-Path $out)) { $null = ScoreGX }
  $v = "$(& $PY -c "import json,sys; s=json.load(open(sys.argv[1]))['stage1']; print(s['diff'].get('400'), s['X4'].get('400'))" $out 2>&1)".Trim() -split '\s+'
  $d = 0.0
  if ($v.Count -ne 2 -or -not [double]::TryParse($v[0], [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$d)) {
    Say "GX seed 400 could not be scored ($($v -join ' ')): GX seed 401 NOT started, NEEDS ATTENTION"
    return $false
  }
  $alive = ($d -ge 0.5) -and ($v[1] -ne 'fail')
  Say "GX seed 400: GX minus G-B2 pooled-5 $d, X4 $($v[1]) -> GX seed 401 $(if ($alive) { 'runs' } else { 'skipped (needs at least +0.5 and X4 not failed)' })"
  return $alive
}
# A src-b3 queue (fc100, g2c3, g2c10, c30). A failed or out-of-memory run is reported by its card; the chain goes on either way.
function B3Step($q, $tpl, $card) {
  WaitFree "before $q"
  if (-not (Test-Path "$SRCB3\B3-SETUP-OK.txt")) { Say "src-b3\B3-SETUP-OK.txt missing: $q NOT started, NEEDS ATTENTION"; return }
  if (Launch $q $SRCB3 $CAPSB3) { NewCard $tpl $card $null; WaitEnd $q } else { Say "$q did NOT start: NEEDS ATTENTION" }
}
# c30 runs once: at the end, or earlier in the gap while B3 waits for its code. Never when WORK\B3-READY.txt exists.
function C30($when) {
  if ($script:c30done) { return }
  if (Test-Path "$WORK\B3-READY.txt") { Say "WORK\B3-READY.txt present: c30 NOT started ($when)"; $script:c30done = $true; return }
  Say "c30 starts ($when)"
  B3Step '8aC30' 'c30.template.md' 'c30.md'
  $script:c30done = $true
}
# B3 group 1 at 3M, one seed, then its readout. Returns the readout's exit code (0 alive, 3 dead, 2 cannot tell) or $null if it did not run.
function B3Seed($seed) {
  $q = "8aB3G1s$seed"
  $null = WaitFree "before $q"
  if (-not (Test-Path "$SRCB3R\B3R-SETUP-OK.txt")) {
    Say "src-b3r\B3R-SETUP-OK.txt missing (B3's fixed code is not installed yet): $q waits; c30 uses the gap"
    $null = C30 'gap before B3'
    $w = HoldAny @("$SRCB3R\B3R-SETUP-OK.txt", "$WORK\B3-SKIP.txt") "$q needs B3's fixed code in src-b3r (rerun upgrade_post_g1.ps1 with b3r.zip), or WORK\B3-SKIP.txt to skip B3"
    if ($w -like '*B3-SKIP*') { Say "$q skipped (WORK\B3-SKIP.txt)"; return $null }
    $null = WaitFree "before $q"
  }
  $h = "$(Get-Content "$SRCB3R\B3R-SETUP-OK.txt" -TotalCount 1)" -replace '^caps\.py\s+', ''
  if (-not (Launch $q $SRCB3R $h.Trim())) { Say "$q did NOT start: NEEDS ATTENTION"; return $null }
  $null = NewCard 'b3g1.template.md' "b3g1-s$seed.md" @{'@Q@' = $q; '@SEED@' = "$seed"}
  $null = WaitEnd $q
  return (B3Read $q $seed)
}
# b3_readout.py on the newest ok run of this queue (any spill letter) against g2c3 of the same seed; lines go to WORK\q<Q>.log.
function B3Read($q, $seed) {
  $job = NewestOk "$WORK\results\$q*-pc\$q*-3M-s$seed\RESULT.json"
  if (-not $job) { Say "B3 seed ${seed}: no ok RESULT.json under WORK\results\$q*-pc: no readout, NEEDS ATTENTION"; return 2 }
  $res = Join-Path (Split-Path $job) 'B3\RESULT.json'
  $pj = NewestOk "$WORK\results\8aG2C3*-pc\8aG2C3*-3M-s$seed\RESULT.json"
  $pair = if ($pj) { Join-Path (Split-Path $pj) 'PT\RESULT.json' } else { 'none' }
  $ck = Join-Path (Split-Path $job) 'B3\checkpoint.pt'
  $out = "$WORK\b3g1-s$seed-readout.json"
  $cmd = "$CIO\q${q}_readout.cmd"
  Set-Content -Encoding ascii $cmd -Value @(
    '@echo off',
    'set PYTHONUTF8=1',
    'set PYTHONUNBUFFERED=1',
    'set PYTHONPATH=C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages',
    'set CUSTOM_IO_EG2=C:\Users\benja\eg2',
    "cd /d $SRCB3R",
    "$PY $CIO\b3_readout.py --b3 `"$res`" --pair `"$pair`" --ckpt `"$ck`" --src $SRCB3R --long-dev `"$WORK\b3-inputs\long-dev.jsonl`" --out `"$out`" >> $WORK\q$q.log 2>&1")
  Say "B3 seed ${seed}: readout of $res against $pair (log WORK\q$q.log)"
  $p = Start-Process -FilePath 'cmd.exe' -ArgumentList "/c $cmd" -Wait -PassThru -WindowStyle Hidden
  $rc = $p.ExitCode
  $sum = @(Select-String -Path "$WORK\q$q.log" -Pattern 'B3 readout: summary' -SimpleMatch -ErrorAction SilentlyContinue) | Select-Object -Last 1
  Say "B3 seed ${seed}: readout exit $rc (0 alive, 3 dead, 2 cannot tell). $(if ($sum) { $sum.Line })"
  return $rc
}
function B3Alive($rc) {
  if ($null -eq $rc) { Say 'B3 seed 400 did not run: no seed-401 runs'; return $false }
  if (Test-Path "$WORK\B3-S401-GO.txt") { Say 'WORK\B3-S401-GO.txt present: B3 seed 401 runs'; return $true }
  if (Test-Path "$WORK\B3-S401-SKIP.txt") { Say 'WORK\B3-S401-SKIP.txt present: B3 seed 401 skipped'; return $false }
  if ($rc -eq 0) { return $true }
  if ($rc -eq 3) { Say 'B3 seed 400: B3-1 below +1.0, so no seed 401 (PLAN.md sec. 5)'; return $false }
  Say 'B3 seed 400 could not be read: seed-401 runs NOT started, NEEDS ATTENTION'
  return $false
}

Say "post-G1 chain waiter v2 started (pid $PID): GX s400, fc100, g2c3, B3 3M s400, [GX s401], [g2c3 s401, B3 3M s401], g2c10, c30"

# 1. Gate G1 ends.
$k = 0
while (-not ((G1Over) -and (Free 5))) {
  if ($k % 360 -eq 0) { Say 'waiting for gate G1 to end (10M s401 ok, or its futility skip, or WORK\G1-DONE.txt; then 5 quiet minutes)' }
  $k++; Start-Sleep -Seconds 60
}
Say 'gate G1 has ended'
MoveDone 'g1*.md' ''

# 2. Test GX seed 400 (owner: thread "Many experts, many layers test"), unless it runs on the Mac.
$gxHere = $false
if (Test-Path "$WORK\GX-ON-MAC.txt") {
  Say 'WORK\GX-ON-MAC.txt present: test GX runs on the Mac, skipped here'
} else {
  if (-not (Test-Path "$SRCGX\GX-SETUP-OK.txt")) { Say 'waiting for src-8gx\GX-SETUP-OK.txt (GX setup by install_post_g1.ps1), or WORK\GX-ON-MAC.txt' }
  while (-not (Test-Path "$SRCGX\GX-SETUP-OK.txt") -and -not (Test-Path "$WORK\GX-ON-MAC.txt")) { Start-Sleep -Seconds 60 }
  if (Test-Path "$WORK\GX-ON-MAC.txt") {
    Say 'WORK\GX-ON-MAC.txt present: test GX runs on the Mac, skipped here'
  } else {
    $gxHere = $true
    WaitFree 'before GX seed 400'
    if (Launch '8aGXs400' $SRCGX $CAPS) { GXCard '8aGXs400' 400; WaitEnd '8aGXs400' }
    if (GXOk '8aGXs400') { Say 'GX seed 400: ok'; ScoreGX }
    else { Hold 'GX-DONE.txt' 'GX seed 400 did not finish ok, so the rest of the chain waits (Ben asked for experts first); fix and rerun it (keep the job name 8aGX-3M-s400), then create WORK\GX-DONE.txt' }
  }
}

# 3-4. fc100 and g2c3 (src-b3), then B3 3M seed 400 (src-b3r) and its readout.
B3Step '8aFC' 'fc100.template.md' 'fc100.md'
B3Step '8aG2C3' 'g2c3.template.md' 'g2c3.md'
$rc400 = B3Seed 400

# 5. GX seed 401, only if GX seed 400 is alive.
if ($gxHere -and (GXAlive)) {
  WaitFree 'before GX seed 401'
  if (Launch '8aGXs401' $SRCGX $CAPS) { GXCard '8aGXs401' 401; WaitEnd '8aGXs401' }
  if (GXOk '8aGXs401') { Say 'GX seed 401: ok' } else { Say 'GX seed 401 did not finish ok: NEEDS ATTENTION (the chain goes on)' }
}

# 6. B3 seed 401 and its pair, only if B3 seed 400 is alive.
if (B3Alive $rc400) {
  B3Step '8aG2C3s401' 'g2c3s401.template.md' 'g2c3s401.md'
  $rc401 = B3Seed 401
}

# 7-8. g2c10, then c30 unless it already ran in a gap or the B3 ladder is ready.
B3Step '8aG2C10' 'g2c10.template.md' 'g2c10.md'
WaitFree 'before c30'
C30 'end of the chain'
Say 'chain finished'
