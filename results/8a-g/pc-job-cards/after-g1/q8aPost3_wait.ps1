# Post-G1 chain on BensPC, version 3 (10 Oct 2026, spec addendum R; replaces q8aPost2_wait.ps1 while that one still waits for G1).
# v3c (11 Oct 2026, spec addendum S): fc100 is split. Part 1 (8aFC, src-b3) only builds the pool; part 2 (8aFC2, src-b3g2) measures four
# ~100M group 2 shapes (21 x 512, 30 x 432, 37 x 384, 54 x 320; FINISHED-MODEL item 10). Inserted jobs: WORK\insert\*.txt (see RunInserts)
# run alone at the next check point after group 2 at 3M, so another thread can add a job (the 10M depth pair) without a waiter swap.
# GX does not run here: WORK\GX-ON-MAC.txt is set (GX stage 1 ran on rented cards; stage 2 withdrawn).
# v3d (11 Oct 2026, spec addendum T): fc100 part 3 right after part 2 = answer speed of the same four shapes (custom-io\infer_speed.py, read-only,
# alone on the GPU, at most about an hour): questions per second at batch 1, 16 and 128 with 12 and 32 thinking rounds -> WORK\fc100-infer.json.
# v3e (11 Oct 2026, spec addendum U): inserted jobs may come from any src-<name> folder (with its caps.py hash) or be a plain .cmd script
# (for later creative/sleep jobs on new code), and WORK\insert\README.txt is no longer taken for a job. Addendum Y (5:58 PM ET): when
# src-b3g2 holds the reader-rule code (install_rr.ps1), group 2 (g2c3s, then B3 group 2 = G2f, the talker's first run) moves before
# g2c3 and B3 group 1; without it the order below (option A) stays.
# After gate G1's last PC queue ends, one queue at a time:
#   1. test GX seed 400 (8aGXs400, src-8gx), skipped if it already has an ok RESULT.json (it may have run beside G1)
#   2. fc100 part 1 (8aFC, src-b3), then part 2 (8aFC2, src-b3g2), then part 3 (answer speed)  3. g2c3 seed 400 (8aG2C3, src-b3)
#   4. B3 group 1 at 3M seed 400 (8aB3G1s400, src-b3r), then b3_readout.py (marks B3-1 to B3-6) into its log
#   4a. g2c3s (8aG2C3S, src-b3g2), then B3 group 2 at 3M seed 400 (8aB3G2s400, src-b3g2): big-run PLAN.md option A. If group 1 s400 is
#       proved wrong on B3-1, B3-2 or B3-3, group 2 waits for the bisect: it moves to the end and runs only on WORK\G2-GO.txt.
# Before any launch, a job folder whose job-level RESULT.json is not ok is renamed aside (local_runner would skip it otherwise).
#   5. only if GX seed 400 is alive: GX seed 401 (8aGXs401)     6. only if B3 seed 400 is alive: g2c3 s401 (8aG2C3s401), then B3 seed 401 + readout
#   7. g2c10s (8aG2C10S, src-b3g2)                              8. c30s (8aC30S, src-b3g2) unless WORK\B3-READY.txt exists or c30s already ran in a gap
# g2c10s and c30s (arm PTS, worked steps on every row, caps_b3s.json) replace g2c10 and c30 (big-run PLAN.md addendum 10-10, 9:00 PM ET).
# The src-b3g2 jobs need src-b3g2\G2-SETUP-OK.txt (upgrade_post_g1_v3.ps1); without it each one is skipped with a NEEDS ATTENTION line.
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
$SRCG2  = "$CIO\src-b3g2"
$JOBS   = 'C:\Users\benja\pc-jobs'
$PY     = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$CAPS   = '3DA2DFBB0DDDE64F0B4A263CCC025A01E70CA35C7C69FD9E9FDBB9C2D2325F78'      # caps.py of the experts code (src-8gx; same as G1's)
$CAPSB3 = 'D276FAC05E1127D9979E9B8EA3A4F4E6CC4D7BAC33C218FA164117B60F1B4AA8'      # caps.py at 71299b1a47 (src-b3)
$CAPSG2 = '32862AE2D4E6E401FCAD5BB6C5E54B0B8845019202DEA73E2CB4C7EFE5EEA03E'      # caps.py at 1acfde9a73 (src-b3g2, claude/learner-new-g2)
$LOG    = "$WORK\q8aPost-waiter.log"
$CARDS  = @('gx*.md', 'fc100*.md', 'g2c3*.md', 'b3g1*.md', 'b3g2*.md', 'g2c10*.md', 'c30*.md')     # this chain's cards in pc-jobs
$script:c30done = $false
$script:icards = @()      # cards of inserted jobs (moved to done like the chain's own)
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
# local_runner skips a job whose job-level RESULT.json exists, even when its status is not ok. Before a launch (no runner present), such a
# folder is renamed aside (never deleted) so the job really runs.
function ClearFailed($q, $qf) {
  foreach ($j in @(Get-Content $qf -ErrorAction SilentlyContinue | Where-Object { $_ -match '^g8a:\s+\S+' } | ForEach-Object { ($_ -split '\s+')[1] })) {
    $d = "$WORK\results\$q-pc\$j"
    if (-not (Test-Path "$d\RESULT.json")) { continue }
    $st = $null
    try { $st = (Get-Content "$d\RESULT.json" -Raw | ConvertFrom-Json).status } catch { }
    if ($st -ne 'ok') {
      $to = "$j.failed-$((Get-Date).ToString('yyyyMMdd-HHmm'))"
      Rename-Item $d $to
      Say "results\$q-pc\$j had status '$st': renamed to $to, so the runner runs it again"
    }
  }
}
function Launch($q, $src, $hash) {
  $qf = "$src\custom_io\queue_local\$q-pc.txt"
  if (-not (Test-Path $qf)) { Say "queue file $qf missing: $q NOT started"; return $false }
  if ((Get-FileHash "$src\custom_io\g8a\caps.py").Hash -ne $hash) { Say "caps.py hash wrong in ${src}: $q NOT started"; return $false }
  if ((Runner) -or (Test-Path "$WORK\STOP")) { Say "a runner or STOP appeared: $q NOT started"; return $false }
  ClearFailed $q $qf
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
  foreach ($p in @($CARDS + $script:icards)) { MoveDone $p $name }
  if ($CARDS -notcontains $name -and $script:icards -notcontains $name -and @($CARDS | Where-Object { $name -like $_ }).Count -eq 0) { $script:icards += $name }
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
# A src-b3 queue (fc100, g2c3, g2c3 s401). A failed or out-of-memory run is reported by its card; the chain goes on either way.
function B3Step($q, $tpl, $card) {
  WaitFree "before $q"
  if (-not (Test-Path "$SRCB3\B3-SETUP-OK.txt")) { Say "src-b3\B3-SETUP-OK.txt missing: $q NOT started, NEEDS ATTENTION"; return }
  if (Launch $q $SRCB3 $CAPSB3) { NewCard $tpl $card $null; WaitEnd $q } else { Say "$q did NOT start: NEEDS ATTENTION" }
}
# A src-b3g2 queue (g2c3s, B3 group 2, g2c10s, c30s). Returns $true if it was started. A failed run is reported by its card; the chain goes on.
function G2Step($q, $tpl, $card) {
  $null = WaitFree "before $q"
  if (-not (Test-Path "$SRCG2\G2-SETUP-OK.txt")) { Say "src-b3g2\G2-SETUP-OK.txt missing: $q NOT started, NEEDS ATTENTION"; return $false }
  if (Launch $q $SRCG2 $CAPSG2) { $null = NewCard $tpl $card $null; $null = WaitEnd $q; return $true }
  Say "$q did NOT start: NEEDS ATTENTION"; return $false
}
# Inserted jobs: another thread adds a job without a waiter swap by writing WORK\insert\<order>-<name>.txt (README.txt is ignored), either
#   queue: <Q>  +  src: <src folder in custom-io>  [+ caps: <SHA-256 of that src's custom_io\g8a\caps.py>, needed for a src other than
#   src-b3g2 and src-b3]  [+ card: <template in custom-io>]: the queue file <src>\custom_io\queue_local\<Q>-pc.txt runs through Launch
#   (caps.py hash of that src, failed job folders renamed aside), or
#   cmd: <file>.cmd in custom-io  [+ card:]  [+ hours: N, default 48]: that cmd file runs (it must keep its job in the foreground) and the
#   chain waits for it to exit, with a NEEDS ATTENTION line every N hours while it runs (it is never stopped).
# At each check point (after group 2 at 3M, before g2c10s, before c30s, at the end) every such file runs in name order, alone. The file is
# then renamed <name>.txt.done-<stamp>, or .refused-<stamp> / .notstarted-<stamp>; nothing is deleted.
function RunInserts($where) {
  $dir = "$WORK\insert"
  $known = @{ 'src-b3g2' = $CAPSG2; 'src-b3' = $CAPSB3 }
  foreach ($f in @(Get-ChildItem "$dir\*.txt" -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne 'README.txt' } | Sort-Object Name)) {
    $kv = @{}
    foreach ($l in @(Get-Content $f.FullName)) { if ($l -match '^\s*(queue|src|card|caps|cmd|hours)\s*:\s*(\S+)\s*$') { $kv[$Matches[1]] = $Matches[2] } }
    $stamp = (Get-Date).ToString('yyyyMMdd-HHmm')
    $why = $null
    if ($kv['cmd']) {
      if ($kv['queue'] -or $kv['src']) { $why = "'cmd:' goes alone, without 'queue:' or 'src:'" }
      elseif (($kv['cmd'] -notmatch '^[A-Za-z0-9_.-]+\.cmd$') -or -not (Test-Path "$CIO\$($kv['cmd'])")) { $why = "'cmd:' must name a .cmd file in custom-io" }
    }
    elseif (-not $kv['queue'] -or -not $kv['src']) { $why = "needs 'queue: <Q>' and 'src: <folder>', or 'cmd: <file>.cmd'" }
    elseif (($kv['src'] -notmatch '^src-[A-Za-z0-9_-]+$') -or -not (Test-Path "$CIO\$($kv['src'])\custom_io")) { $why = "'src:' must be a src-<name> folder in custom-io that holds custom_io" }
    elseif (-not $known.ContainsKey($kv['src']) -and ($kv['caps'] -notmatch '^[0-9A-Fa-f]{64}$')) { $why = "a src other than src-b3g2 or src-b3 needs 'caps: <SHA-256 of its caps.py>'" }
    if ($why) {
      Say "insert $($f.Name) refused, NEEDS ATTENTION: $why"
      Rename-Item $f.FullName "$($f.Name).refused-$stamp"; continue
    }
    $null = WaitFree "before inserted $($f.Name)"
    $tag = 'notstarted'
    if ($kv['cmd']) {
      $hrs = 48
      if ($kv['hours'] -match '^[1-9][0-9]*$') { $hrs = [int]$kv['hours'] }
      if ((Runner) -or (Test-Path "$WORK\STOP")) { Say "a runner or STOP appeared: inserted $($kv['cmd']) NOT started, NEEDS ATTENTION" }
      else {
        Say "inserted job $($f.Name) ($where): runs custom-io\$($kv['cmd']) alone"
        $p = Start-Process -FilePath 'cmd.exe' -ArgumentList "/c $CIO\$($kv['cmd'])" -PassThru -WindowStyle Hidden
        $null = $p.Handle       # keeps the handle, so ExitCode can be read after it exits
        if ($kv['card']) { $null = NewCard $kv['card'] "$([IO.Path]::GetFileNameWithoutExtension($kv['cmd']).ToLower()).md" $null }
        $m = 0
        while (-not $p.HasExited) {
          Start-Sleep -Seconds 60; $m++
          if ($m % ($hrs * 60) -eq 0) { Say "inserted $($kv['cmd']) still running after $($m / 60) hours: NEEDS ATTENTION (the chain waits for it)" }
        }
        Say "inserted $($kv['cmd']) ended (exit $($p.ExitCode))"
        $tag = 'done'
      }
    } else {
      $q = $kv['queue']
      $h = if ($known.ContainsKey($kv['src'])) { $known[$kv['src']] } else { $kv['caps'] }
      Say "inserted job $($f.Name) ($where): queue $q from $($kv['src'])"
      if (Launch $q "$CIO\$($kv['src'])" $h) {
        if ($kv['card']) { $null = NewCard $kv['card'] "$($q.ToLower()).md" $null }
        $null = WaitEnd $q; $tag = 'done'
      } else { Say "inserted $q did NOT start: NEEDS ATTENTION" }
    }
    Rename-Item $f.FullName "$($f.Name).$tag-$stamp"
  }
}
# fc100 part 3: infer_speed.py from src-b3g2 on the pool and caps fc100 parts 1 and 2 made, alone (no runner for 5 minutes first), card fc100v3.md.
# Lines go to WORK\q8aFCI.log. Stopped after 120 minutes if it is still running (its own cap is 60). A failure is logged; the chain goes on.
function InferStep {
  $null = WaitFree 'before the answer-speed timing'
  $pool = "$WORK\g8a\pools\p10-rung30-s400-a64-L"
  $caps = "$pool.caps-B3G2\caps.json"
  foreach ($f in @("$CIO\infer_speed.py", "$pool\dev\in_dist.jsonl", $caps)) { if (-not (Test-Path $f)) { Say "answer-speed timing NOT run: $f missing, NEEDS ATTENTION"; return } }
  $cmd = "$CIO\q8aFCI_run.cmd"
  Set-Content -Encoding ascii $cmd -Value @(
    '@echo off',
    'set PYTHONUTF8=1',
    'set PYTHONUNBUFFERED=1',
    'set PYTHONPATH=C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages',
    'set CUSTOM_IO_EG2=C:\Users\benja\eg2',
    "cd /d $SRCG2",
    "$PY $CIO\infer_speed.py --src $SRCG2 --pool `"$pool`" --caps `"$caps`" --queue $SRCG2\custom_io\queue_local\8aFC2-pc.txt --out `"$WORK\fc100-infer.json`" --busy C:\Users\benja\GPU-BUSY.txt >> $WORK\q8aFCI.log 2>&1")
  Say 'answer-speed timing of the 100M shapes starts (fc100 part 3; log WORK\q8aFCI.log)'
  $p = Start-Process -FilePath 'cmd.exe' -ArgumentList "/c $cmd" -PassThru -WindowStyle Hidden
  $null = $p.Handle       # keeps the handle, so ExitCode can be read after it exits
  $null = NewCard 'fc100v3.template.md' 'fc100v3.md' $null
  for ($m = 0; ($m -lt 120) -and -not $p.HasExited; $m++) { Start-Sleep -Seconds 60 }
  if (-not $p.HasExited) {
    foreach ($x in @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -like '*infer_speed.py*' })) { Stop-Process -Id $x.ProcessId -Force }
    $bf = 'C:\Users\benja\GPU-BUSY.txt'       # its own line only (as local_runner's Busy does: the file goes when no line is left)
    if (Test-Path $bf) { $keep = @(Get-Content $bf | Where-Object { $_ -notlike '* 8aFCI/*' }); if ($keep.Count) { Set-Content -Encoding ascii $bf -Value $keep } else { Remove-Item $bf } }
    Say 'answer-speed timing still running after 120 minutes: stopped, NEEDS ATTENTION (WORK\fc100-infer.json keeps the cells done)'
    return
  }
  $done = @(Select-String -Path "$WORK\q8aFCI.log" -Pattern 'INFER SPEED DONE' -SimpleMatch -ErrorAction SilentlyContinue).Count -gt 0
  Say "answer-speed timing ended (exit $($p.ExitCode))$(if ($done) { ': WORK\fc100-infer.json' } else { ': no DONE line, NEEDS ATTENTION' })"
}
# c30s runs once: at the end, or earlier in the gap while B3 waits for its code. Never when WORK\B3-READY.txt exists.
function C30($when) {
  if ($script:c30done) { return }
  if (Test-Path "$WORK\B3-READY.txt") { Say "WORK\B3-READY.txt present: c30s NOT started ($when)"; $script:c30done = $true; return }
  Say "c30s starts ($when)"
  if (G2Step '8aC30S' 'c30s.template.md' 'c30s.md') { $script:c30done = $true }
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

Say "post-G1 chain waiter v3 started (v3e; pid $PID): GX s400 (unless done), fc100 part 1 + part 2 (the 100M shapes) + part 3 (their answer speed), then with the reader-rule code g2c3s, B3 group 2 3M s400 (G2f), g2c3, B3 3M s400 (else g2c3, B3 3M s400, g2c3s, B3 group 2 3M s400), [GX s401], [g2c3 s401, B3 3M s401], g2c10s, c30s; inserted jobs from WORK\insert after group 2"

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
    if (GXOk '8aGXs400') { Say 'GX seed 400 already has an ok RESULT.json (it ran beside G1): not run again' }
    elseif (Launch '8aGXs400' $SRCGX $CAPS) { GXCard '8aGXs400' 400; WaitEnd '8aGXs400' }
    if (GXOk '8aGXs400') { Say 'GX seed 400: ok'; ScoreGX }
    else { Hold 'GX-DONE.txt' 'GX seed 400 did not finish ok, so the rest of the chain waits (Ben asked for experts first); fix and rerun it (keep the job name 8aGX-3M-s400), then create WORK\GX-DONE.txt' }
  }
}

# 3. fc100 (part 1 src-b3, part 2 src-b3g2, part 3 the answer timer).
B3Step '8aFC' 'fc100.template.md' 'fc100.md'
$null = G2Step '8aFC2' 'fc100v2.template.md' 'fc100v2.md'
InferStep

# 3a. With the reader-rule code in src-b3g2 (its G2-SETUP-OK.txt says "reader rules", written by install_rr.ps1), group 2 runs first:
# g2c3s, then B3 group 2 3M s400 (= G2f, the talker's first run: answers and calls written from the thinker's state only). Ben asked
# "can you build the talker" (5:51 PM ET 10-11); the agent model's AT-1 gate waits on G2f, not on group 1, which keeps the old copying
# talker (architecture thread, 5:58 PM ET 10-11). The option A hold (group 2 waits if group 1 s400 is proved wrong) then does not apply.
$g2first = [bool](Select-String -Path "$SRCG2\G2-SETUP-OK.txt" -Pattern 'reader rules' -SimpleMatch -Quiet -ErrorAction SilentlyContinue)
$g2held = $false
if ($g2first) {
  Say 'src-b3g2 has the reader-rule code: group 2 (g2c3s, then B3 group 2 = G2f) runs before group 1'
  $null = G2Step '8aG2C3S' 'g2c3s.template.md' 'g2c3s.md'
  $null = G2Step '8aB3G2s400' 'b3g2.template.md' 'b3g2.md'
  RunInserts 'after group 2 at 3M'
} else { Say 'src-b3g2 has no reader-rule code: group 1 first, then group 2 (option A order)' }

# 4. g2c3 (src-b3), then B3 3M seed 400 (src-b3r) and its readout.
B3Step '8aG2C3' 'g2c3.template.md' 'g2c3.md'
$rc400 = B3Seed 400

# 4a. Without the reader-rule code: group 2 at 3M seed 400 and its all-steps partner here (big-run PLAN.md option A: after B3 group 1
# s400, before the 10M and 30M controls). Sealed rule: if group 1 s400 is proved wrong on B3-1, B3-2 or B3-3, group 2 waits for that
# bisect. It then moves to the end of the chain and runs there only on WORK\G2-GO.txt (WORK\G2-SKIP.txt drops it); the rest does not wait.
if (-not $g2first) {
  $g2wrong = "$(& $PY -c "import json,sys; m=json.load(open(sys.argv[1]))['marks']; w=[k for k, f in (('B3-1','dead'),('B3-2','wrong'),('B3-3','wrong')) if (m.get(k) or {}).get(f) is True]; print(' '.join(w) or 'none')" "$WORK\b3g1-s400-readout.json" 2>&1)".Trim()
  if ($g2wrong -match '^(B3-\d)( B3-\d)*$' -and -not (Test-Path "$WORK\G2-GO.txt")) {
    $g2held = $true
    Say "group 1 s400 proved wrong on ${g2wrong}: group 2 (g2c3s, B3 group 2) waits for the bisect; it moves to the end of the chain and runs there only on WORK\G2-GO.txt, NEEDS ATTENTION"
  } else {
    Say "group 1 s400 proved-wrong marks: $g2wrong. Group 2 runs now."
    $null = G2Step '8aG2C3S' 'g2c3s.template.md' 'g2c3s.md'
    $null = G2Step '8aB3G2s400' 'b3g2.template.md' 'b3g2.md'
  }
  RunInserts 'after group 2 at 3M'
}

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

# 7-8. g2c10s, then c30s unless it already ran in a gap or the B3 ladder is ready.
RunInserts 'before g2c10s'
$null = G2Step '8aG2C10S' 'g2c10s.template.md' 'g2c10s.md'
RunInserts 'before c30s'
WaitFree 'before c30s'
C30 'end of the chain'
if ($g2held) {
  $w = HoldAny @("$WORK\G2-GO.txt", "$WORK\G2-SKIP.txt") 'group 2 was held (group 1 s400 proved wrong): WORK\G2-GO.txt runs it now, WORK\G2-SKIP.txt drops it'
  if ($w -like '*G2-GO*') {
    $null = G2Step '8aG2C3S' 'g2c3s.template.md' 'g2c3s.md'
    $null = G2Step '8aB3G2s400' 'b3g2.template.md' 'b3g2.md'
  } else { Say 'group 2 dropped (WORK\G2-SKIP.txt)' }
}
RunInserts 'end of the chain'
Say 'chain finished'
