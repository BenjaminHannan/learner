# Upgrade the post-G1 chain from v2 to v3 on BensPC (10 Oct 2026, spec addendum R). Run once, from the folder the Mac copied (in-v3).
# v3 adds group 2 (big-run PLAN.md option A: g2c3s, then B3 group 2 at 3M seed 400, after B3 group 1 s400) and replaces g2c10 and c30
# with their all-steps versions g2c10s and c30s (PLAN.md addendum 10-10, 9:00 PM ET). It also skips GX seed 400 if that already has an ok
# RESULT.json (the experts thread runs it beside G1).
# Steps: check that v2 still waits for G1; set up src-b3g2 from g2.zip (custom_io of claude/learner-new-g2 at 1acfde9a73) and check its hashes;
# put caps_b3s.json and caps_b3g2.json in WORK\b3-inputs; add the g2c10s and c30s queue files; parse the four group 2 queues and check
# the PTS size bands on CPU; write src-b3g2\G2-SETUP-OK.txt; copy the card templates and the v3 waiter; stop v2 by PID; start v3 detached.
# It stops nothing else and deletes nothing. On any failure it stops before touching the waiter, so v2 keeps waiting.
$IN     = Split-Path -Parent $MyInvocation.MyCommand.Path
$CIO    = 'C:\Users\benja\custom-io'
$WORK   = "$CIO\work"
$SRCG2  = "$CIO\src-b3g2"
$PY     = 'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe'
$LOG    = "$WORK\q8aPost-waiter.log"
$CAPSG2 = '32862AE2D4E6E401FCAD5BB6C5E54B0B8845019202DEA73E2CB4C7EFE5EEA03E'      # custom_io\g8a\caps.py at 1acfde9a73
$JSONS  = @{ 'caps_b3s.json' = '8CBEA48D300A8A0D38D9A89D950274DF08743326CA3F1E9EAFC2763ADD9CBF31'; 'caps_b3g2.json' = 'EE551D3AACBF9EC02D2AC7F5E7E6E12F44E15ABA2C39F5F38C3F1E3EC12D7ED4' }
$QNEW   = @('8aG2C10S-pc.txt', '8aC30S-pc.txt')
$QALL   = @('8aG2C3S', '8aB3G2s400', '8aG2C10S', '8aC30S')
$TPLS   = @('g2c3s', 'b3g2', 'g2c10s', 'c30s')
function Fail($m) { "FAILED: $m (nothing on the waiter was changed; v2 keeps waiting)"; exit 1 }
function Hash($p) { (Get-FileHash $p).Hash }
function Waiters($name) { @(Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" | Where-Object { $_.CommandLine -like "*$name*" }) }

# 1. v2 must still be waiting for G1.
$v3 = @(Waiters 'q8aPost3_wait.ps1')
if ($v3.Count) { "v3 is already running (pid $($v3[0].ProcessId)): nothing to do"; exit 0 }
$v2 = @(Waiters 'q8aPost2_wait.ps1')
if ($v2.Count -ne 1) { Fail "expected one q8aPost2_wait.ps1 waiter, found $($v2.Count)" }
$lines = @(Get-Content $LOG)
$start = -1
for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*chain waiter v2 started*') { $start = $i } }
if ($start -lt 0) { Fail "no 'chain waiter v2 started' line in $LOG" }
for ($i = $start; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*gate G1 has ended*') { Fail 'v2 is already past gate G1 (swap by hand)' } }
"v2 waiter pid $($v2[0].ProcessId) is still waiting for G1"

# 2. src-b3g2 from g2.zip.
if (Test-Path "$SRCG2\G2-SETUP-OK.txt") {
  'src-b3g2: already set up (G2-SETUP-OK.txt present)'
} else {
  if (Test-Path $SRCG2) { Fail "$SRCG2 exists without G2-SETUP-OK.txt: look at it by hand" }
  if (-not (Test-Path "$IN\g2.zip")) { Fail "$IN\g2.zip missing" }
  Expand-Archive -Path "$IN\g2.zip" -DestinationPath $SRCG2
  if ((Hash "$SRCG2\custom_io\g8a\caps.py") -ne $CAPSG2) { Fail 'src-b3g2 caps.py hash wrong' }
  foreach ($k in $JSONS.Keys) { if ((Hash "$SRCG2\custom_io\g8a\$k") -ne $JSONS[$k]) { Fail "src-b3g2 $k hash wrong" } }
  'src-b3g2: unpacked, caps.py and both caps files match'
}

# 3. WORK\b3-inputs: the two pinned caps files (cloze_long.py is already there from the v2 install).
if (-not (Test-Path "$WORK\b3-inputs\cloze_long.py")) { Fail 'WORK\b3-inputs\cloze_long.py missing' }
foreach ($k in $JSONS.Keys) {
  $dst = "$WORK\b3-inputs\$k"
  if (Test-Path $dst) { if ((Hash $dst) -ne $JSONS[$k]) { Fail "$dst exists with another hash" } else { "b3-inputs\${k}: already there, hash ok" } }
  else { Copy-Item "$SRCG2\custom_io\g8a\$k" $dst; "b3-inputs\${k}: copied" }
}

# 4. Queue files.
foreach ($f in $QNEW) { Copy-Item -Force "$IN\$f" "$SRCG2\custom_io\queue_local\" }
foreach ($q in $QALL) { if (-not (Test-Path "$SRCG2\custom_io\queue_local\$q-pc.txt")) { Fail "queue file $q-pc.txt missing in src-b3g2" } }
"queue files in src-b3g2: $($QALL -join ', ')"

# 5. CPU check: the four queues parse, and the PTS arm passes the size bands at 3M, 10M and 30M with the pinned caps.
$env:PYTHONPATH = 'C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages'
$env:PYTHONUTF8 = '1'
Push-Location $SRCG2
$chk = & $PY "$IN\g2check.py" 2>&1
$rc = $LASTEXITCODE
Pop-Location
$chk
if ($rc -ne 0 -or -not ("$chk" -like '*G2 CPU CHECK OK*')) { Fail "CPU check failed (rc $rc)" }

# 6. Setup marker (line 1 is the caps.py hash the waiter checks).
Set-Content -Encoding ascii "$SRCG2\G2-SETUP-OK.txt" -Value @(
  "caps.py $CAPSG2",
  "custom_io of claude/learner-new-g2 at 1acfde9a73 (custom_io same as 9dbcbb579c)",
  "caps_b3s.json $($JSONS['caps_b3s.json'])",
  "caps_b3g2.json $($JSONS['caps_b3g2.json'])",
  "CPU check ok: four queues parse; PTS size bands at 3M, 10M, 30M",
  "set up $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET by upgrade_post_g1_v3.ps1")
'wrote src-b3g2\G2-SETUP-OK.txt'

# 7. Card templates and the v3 waiter.
foreach ($t in $TPLS) { Copy-Item -Force "$IN\$t.md" "$CIO\$t.template.md" }
Copy-Item -Force "$IN\q8aPost3_wait.ps1" "$CIO\q8aPost3_wait.ps1"
"copied $($TPLS -join ', ') templates and q8aPost3_wait.ps1 to custom-io"

# 8. Swap the waiter: v2 is checked again, stopped by PID, and v3 started detached.
$v2 = @(Waiters 'q8aPost2_wait.ps1')
if ($v2.Count -ne 1) { Fail "expected one q8aPost2_wait.ps1 waiter before the swap, found $($v2.Count)" }
$lines = @(Get-Content $LOG)
for ($i = $start; $i -lt $lines.Count; $i++) { if ($lines[$i] -like '*gate G1 has ended*') { Fail 'v2 passed gate G1 during the upgrade (swap by hand)' } }
Stop-Process -Id $v2[0].ProcessId -Force
"$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) ET waiter v2 (pid $($v2[0].ProcessId)) stopped by upgrade_post_g1_v3.ps1 while waiting for G1" | Add-Content -Encoding ascii $LOG
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="powershell -NoProfile -ExecutionPolicy Bypass -File $CIO\q8aPost3_wait.ps1"}
"started v3 (ReturnValue $($r.ReturnValue), pid $($r.ProcessId))"
Start-Sleep -Seconds 15
"v3 waiters running: $(@(Waiters 'q8aPost3_wait.ps1').Count); v2 waiters running: $(@(Waiters 'q8aPost2_wait.ps1').Count)"
Get-Content $LOG -Tail 4
